# -*- coding: utf-8 -*-
"""test_research.py —— **研究库门禁**（功能 6/7/8/12/13/15/18 的服务端自检）。

为什么要有它：研究库是一批「写库」接口（本项目此前**全部只读**），写操作最怕三件事——
  ① **重复写**（用户重试/网络重发 → 同一件事记了两行）；
  ② **盖掉历史**（「编辑」把旧记录覆盖了，事后无法回溯）；
  ③ **没痕迹**（改了就改了，不知道谁改的、为什么）。

本门禁逐条对照这三件事，并且按本项目风格做「**护栏的护栏**」：
把旧的错误写法注回去，必须报错（见 C2 / C6 的注释）。

用法：python web/test_research.py
退出码：0 = 全过（比对项为 0 也判 FAIL）；1 = 有问题。
"""
import json
import os
import re
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import research as RS                     # noqa: E402

CMP = [0]
BAD = []


def ok(name, cond, detail=''):
    CMP[0] += 1
    if not cond:
        BAD.append(name + ('：' + detail if detail else ''))


def main():
    tmp = tempfile.mkdtemp(prefix='research_gate_')
    dbp = os.path.join(tmp, 'research.db')
    try:
        conn = RS.connect(dbp)

        # ---------- C1 幂等：同 token 两次 = 一次 ----------
        r1 = RS.add_text_version(conn, 'ci.清.x', '版本一', client_token='tok-1')
        r2 = RS.add_text_version(conn, 'ci.清.x', '版本二', client_token='tok-1')  # 内容不同，但同 token
        n = conn.execute("SELECT COUNT(*) FROM text_versions WHERE pid='ci.清.x'").fetchone()[0]
        ok('C1 同 token 重复提交只写一行', n == 1, '实际 %d 行' % n)
        ok('C1 重复提交返回第一次的结果', r1 == r2,
           'r1=%s r2=%s' % (r1.get('id'), r2.get('id')))
        ok('C1 第二次不产生「版本二」', conn.execute(
            "SELECT COUNT(*) FROM text_versions WHERE content='版本二'").fetchone()[0] == 0)

        # ---------- C2 「护栏的护栏」：去掉唯一约束就会崩 ----------
        # 注回旧错误写法（无 UNIQUE 直接双插）必须报错——证明真表上有唯一约束在把关。
        import sqlite3 as _s
        try:
            conn.execute("INSERT INTO idempotency(token,endpoint,response,created_at)"
                         " VALUES('tok-1','dup','{}','x')")
            ok('C2 idempotency.token 唯一约束存在', False, '重复插入未报错')
        except _s.IntegrityError:
            ok('C2 idempotency.token 唯一约束存在', True)

        # ---------- C3 不同 token = 各自执行 ----------
        r3 = RS.add_text_version(conn, 'ci.清.x', '版本三', client_token='tok-2')
        n = conn.execute("SELECT COUNT(*) FROM text_versions WHERE pid='ci.清.x'").fetchone()[0]
        ok('C3 不同 token 各写一行', n == 2 and r3['id'] != r1['id'])

        # ---------- C4 版本链：父版本成链、sha 稳定、顺序正确 ----------
        v1 = conn.execute("SELECT * FROM text_versions WHERE pid='ci.清.x' ORDER BY id").fetchone()
        v2 = conn.execute("SELECT * FROM text_versions WHERE pid='ci.清.x' ORDER BY id DESC").fetchone()
        ok('C4 首版 parent 为空', v1['parent_id'] is None)
        ok('C4 次版 parent 指向首版', v2['parent_id'] == v1['id'])
        ok('C4 内容 sha 稳定', RS.content_sha('版本一') == v1['content_sha']
           and RS.content_sha('版本三') == v2['content_sha'])
        ok('C4 版本链长度 = 2', len(RS.list_text_versions(conn, 'ci.清.x')) == 2)
        ok('C4 latest 是最后一版', RS.latest_text_version(conn, 'ci.清.x')['content'] == '版本三')

        # ---------- C5 元数据修订：旧值/新值/依据都留痕 ----------
        RS.add_meta_revision(conn, 'ci.清.x', 'author', '王鹏运', old_value='王鹏运（误作 王鵩运）',
                             basis='《半塘定稿》卷三', why='原字形近误录', client_token='tok-m1')
        RS.add_meta_revision(conn, 'ci.清.x', 'cipai', '临江仙', old_value='临江仙慢', basis='逐字平仄比对',
                             why='谱式不符')
        mrs = RS.list_meta_revisions(conn, 'ci.清.x')
        ok('C5 元数据修订 2 条按序返回', len(mrs) == 2 and mrs[0]['field'] == 'author'
           and mrs[1]['field'] == 'cipai')
        ok('C5 旧值未被抹掉', mrs[0]['old_value'] == '王鹏运（误作 王鵩运）')

        # ---------- C6 决策事件：写下、读回、撤回留痕 ----------
        d1 = RS.record_decision(conn, 'pronounce', 'ci.清.x|line=0|pos=2', 'select',
                                payload={'reading': 'sī', 'tone': '平'}, basis='《广韵》',
                                why='“思”作名词读平声', actor='human')
        d2 = RS.record_decision(conn, 'pronounce', 'ci.清.x|line=0|pos=2', 'withdraw',
                                payload={'reading': 'sī'}, basis='重核词意', why='此处作动词，应读去声',
                                actor='human', prev_id=d1['decision_id'])
        ds = RS.list_decisions(conn, kind='pronounce', subject='ci.清.x|line=0|pos=2')
        ok('C6 决策事件按新在前返回', len(ds) == 2 and ds[0]['action'] == 'withdraw')
        ok('C6 撤回指向原决策（prev_id）', ds[0]['prev_id'] == d1['decision_id'])
        ok('C6 撤回本身也留痕', ds[0]['action'] == 'withdraw' and ds[0]['why'])
        # 「护栏的护栏」：撤回若只是 DELETE 掉原行，上面两条断言会各自崩掉——
        # 所以本用例即为「不许物理删除」的常态守卫。
        ok('C6 原决策仍在（不许物理删）', RS.get_decision(conn, d1['decision_id']) is not None)

        # ---------- C7 并发：两线程同 token 只能写一次 ----------
        connA = RS.connect(dbp)
        connB = RS.connect(dbp)
        barrier = threading.Barrier(2)
        got = []
        lock = threading.Lock()

        def worker(c):
            barrier.wait()
            r = RS.add_text_version(c, 'ci.清.conc', '并发内容', client_token='tok-conc')
            with lock:
                got.append(r)

        ths = [threading.Thread(target=worker, args=(connA,)),
               threading.Thread(target=worker, args=(connB,))]
        [t.start() for t in ths]
        [t.join() for t in ths]
        n = connA.execute("SELECT COUNT(*) FROM text_versions WHERE pid='ci.清.conc'").fetchone()[0]
        ok('C7 并发同 token 只写一行', n == 1, '实际 %d 行' % n)
        ok('C7 并发两线程拿到同一结果', len(got) == 2 and got[0] == got[1])
        connA.close()
        connB.close()

        # ---------- C8 事务原子性：回调抛错则整笔回滚 ----------
        before = conn.execute('SELECT COUNT(*) FROM text_versions').fetchone()[0]
        try:
            def boom(c):
                c.execute("INSERT INTO text_versions(pid,scope,version_type,created_at,actor,"
                          "content,content_sha) VALUES('ci.清.boom','corpus','manual','t','h','x','y')")
                raise RuntimeError('模拟中途失败')
            RS._write(conn, boom)
        except RuntimeError:
            pass
        after = conn.execute('SELECT COUNT(*) FROM text_versions').fetchone()[0]
        ok('C8 回调抛错整笔回滚（无半截数据）', before == after,
           '%d -> %d' % (before, after))

        # ---------- C9 概况 ----------
        s = RS.summary(conn)
        ok('C9 summary 覆盖全部表', all(v is not None for v in s.values())
           and s['text_versions'] >= 3)

        # ---------- C10 服务端分发（q_research_write）：校验与路由语义 ----------
        # 先把研究库指到临时目录（环境变量在 import serve 前生效），避免污染真实库。
        os.environ['LVC_RESEARCH_DB'] = os.path.join(tmp, 'serve_research.db')
        sys.path.insert(0, os.path.join(ROOT, 'web'))
        import serve as S                                          # noqa: E402

        r = S.q_research_write('/api/text_versions',
                               {'pid': 'ci.清.h', 'content': 'HTTP 前置', 'client_token': 'tok-h1'})
        ok('C10 分发：写版本到临时库', r.get('id') and r.get('content_sha'))
        r2 = S.q_research_write('/api/text_versions',
                                {'pid': 'ci.清.h', 'content': 'HTTP 前置（重复）',
                                 'client_token': 'tok-h1'})
        ok('C10 分发：同 token 幂等', r2 == r)
        try:
            S.q_research_write('/api/text_versions', {'pid': '', 'content': 'x'})
            ok('C10 分发：缺 pid 必须报错', False)
        except ValueError:
            ok('C10 分发：缺 pid 必须报错', True)
        try:
            S.q_research_write('/api/nope', {})
            ok('C10 分发：未知写路径必须报错', False)
        except LookupError:
            ok('C10 分发：未知写路径必须报错', True)

        # ---------- C11 真 HTTP 冒烟：起临时服务器，POST 走全链路 ----------
        import http.client as _hc
        from http.server import ThreadingHTTPServer as _Srv
        srv = _Srv(('127.0.0.1', 0), S.H)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            c = _hc.HTTPConnection('127.0.0.1', port, timeout=15)
            body = json.dumps({'pid': 'ci.清.http', 'content': 'HTTP 测试版',
                               'client_token': 'tok-http'}, ensure_ascii=False).encode('utf-8')
            c.request('POST', '/api/text_versions', body=body,
                      headers={'Content-Type': 'application/json'})
            resp = c.getresponse()
            d = json.loads(resp.read().decode('utf-8'))
            ok('C11 HTTP POST 成功且带 ok/result', resp.status == 200 and d.get('ok')
               and d['result'].get('id'))
            c.request('POST', '/api/text_versions', body=body,
                      headers={'Content-Type': 'application/json'})
            resp2 = c.getresponse()
            d2 = json.loads(resp2.read().decode('utf-8'))
            ok('C11 HTTP 重复提交返回同一 id', d2['result']['id'] == d['result']['id'])
            c.request('POST', '/api/text_versions', body=b'{bad json',
                      headers={'Content-Type': 'application/json'})
            resp3 = c.getresponse(); resp3.read()
            ok('C11 坏 JSON → 400', resp3.status == 400, '实际 %d' % resp3.status)
            c.request('POST', '/api/nope', body=b'{}',
                      headers={'Content-Type': 'application/json'})
            resp4 = c.getresponse(); resp4.read()
            ok('C11 未知写路径 → 404', resp4.status == 404, '实际 %d' % resp4.status)
            c.request('GET', '/api/text_versions?pid=ci.%E6%B8%85.http')
            resp5 = c.getresponse()
            d5 = json.loads(resp5.read().decode('utf-8'))
            ok('C11 HTTP GET 版本链回查', resp5.status == 200
               and d5.get('ok') and len(d5['result']) == 1
               and d5['result'][0]['content'] == 'HTTP 测试版')
            c.close()
        finally:
            srv.shutdown()
            srv.server_close()

        # ---------- C12 文献摘录库：append-only 四断言 ----------
        m1 = RS.add_material(conn, '《半塘定稿》', '录得词一首，后附题跋。', kind='book',
                             author='王鹏运', year='清', locator='卷三·页 12',
                             client_token='tok-mat1')
        ok('C12 材料创建返回首版 id', m1.get('material_id') and m1.get('revision_id')
           and m1.get('version') == 1)
        m1b = RS.add_material(conn, '《半塘定稿》', '（重复提交）', client_token='tok-mat1')
        ok('C12 同 token 幂等（不产生第二个材料）', m1b == m1 and conn.execute(
            'SELECT COUNT(1) FROM materials').fetchone()[0] == 1)
        m2 = RS.add_material_revision(conn, m1['material_id'], '修订：补录后跋两行。',
                                      locator='卷三·页 13', client_token='tok-mat2')
        ok('C12 修订=追加版本（version=2）', m2['version'] == 2
           and m2['parent_id'] == m1['revision_id'])
        n_rows = conn.execute('SELECT COUNT(1) FROM material_revisions').fetchone()[0]
        ok('C12 「编辑」不覆盖旧行（2 版都在）', n_rows == 2)
        chain = RS.get_material_chain(conn, m1['material_id'])
        ok('C12 版本链可完整回溯', len(chain['revisions']) == 2
           and chain['revisions'][0]['content'].startswith('录得词一首')
           and chain['revisions'][1]['parent_id'] == chain['revisions'][0]['id'])
        wd = RS.withdraw_material(conn, m1['material_id'], why='重复录入', client_token='tok-mat3')
        ok('C12 删除=撤回标记（行保留）', wd['withdrawn'] and conn.execute(
            'SELECT COUNT(1) FROM materials WHERE id=? AND withdrawn=1',
            (m1['material_id'],)).fetchone()[0] == 1)
        ok('C12 撤回留决策事件', RS.get_decision(conn, wd['decision_id'])['action'] == 'withdraw')
        try:
            RS.add_material_revision(conn, m1['material_id'], '试图追加')
            ok('C12 撤回后不许追加版本', False)
        except ValueError:
            ok('C12 撤回后不许追加版本', True)
        ok('C12 默认列表不含撤回', all(x['id'] != m1['material_id']
                                   for x in RS.list_materials(conn)))
        ok('C12 all=1 含撤回', any(x['id'] == m1['material_id']
                                for x in RS.list_materials(conn, include_withdrawn=True)))

        # ---------- C13 研究事实库：出处硬约束 + 引文逐字核验（护栏的护栏） ----------
        import sqlite3 as _s2
        fconn = _s2.connect(os.path.join(tmp, 'corpus_fixture.db'))
        fconn.executescript(
            "CREATE TABLE poems(pid TEXT PRIMARY KEY, raw TEXT);"
            "CREATE TABLE lines(pid TEXT, idx INTEGER, text TEXT, PRIMARY KEY(pid, idx));"
            "INSERT INTO poems VALUES('p1', '白头游子白头妇，记当年。');"
            "INSERT INTO lines VALUES('p1', 0, '白头游子白头妇，');")
        try:
            RS.add_fact(conn, '临江仙一调起于唐。')
            ok('C13 无出处拒收', False)
        except ValueError as e:
            ok('C13 无出处拒收（找不到出处不许入库）', '出处' in str(e))
        f1 = RS.add_fact(conn, '首句七字，以「白头」二字起。', poem_pid='p1', line_idx=0,
                         evidence='白头游子白头妇', corpus_conn=fconn,
                         client_token='tok-fact1')
        ok('C13 引文逐字一致 → verified', f1['verified'] is True)
        try:
            RS.add_fact(conn, '字形有异。', poem_pid='p1', line_idx=0,
                        evidence='白頭游子白頭婦', corpus_conn=fconn)
            ok('C13 引文不逐字 → 拒收（护栏的护栏）', False)
        except ValueError:
            ok('C13 引文不逐字 → 拒收（护栏的护栏）', True)
        try:
            RS.add_fact(conn, '区间错位。', poem_pid='p1', line_idx=0,
                        span_start=0, span_end=3, evidence='白头游子', corpus_conn=fconn)
            ok('C13 区间与引文不符 → 拒收', False)
        except ValueError:
            ok('C13 区间与引文不符 → 拒收', True)
        f2 = RS.add_fact(conn, '区间定位正确。', poem_pid='p1', line_idx=0,
                         span_start=0, span_end=7, evidence='白头游子白头妇', corpus_conn=fconn)
        ok('C13 区间定位逐字一致 → verified', f2['verified'] is True)
        f3 = RS.add_fact(conn, '仅有材料出处也可入库（未核语料，如实记 0）。',
                         material_id=m1['material_id'], locator='卷三·页 12')
        ok('C13 材料出处可入库且不假装核验', f3['verified'] is False
           and '未核对' in (f3.get('verify_detail') or ''))
        facts = RS.list_facts(conn, poem_pid='p1')
        ok('C13 事实可按作品列出', len(facts) == 2)
        RS.withdraw_fact(conn, f1['fact_id'], why='示例清理')
        ok('C13 事实撤回后默认列表不含', len(RS.list_facts(conn, poem_pid='p1')) == 1)

        # ---------- C14 读音裁定：选定→生效→改选→撤回→完整回溯 ----------
        # 校验：reading 与 tone 必须一致；tone 必须 1..4
        try:
            RS.add_pron_decision(conn, 'p2', 0, 2, 'zhang3', 2)
            ok('C14 reading/tone 不一致必须报错', False)
        except ValueError:
            ok('C14 reading/tone 不一致必须报错', True)
        try:
            RS.add_pron_decision(conn, 'p2', 0, 2, 'de5', 5)
            ok('C14 tone 必须 1..4', False)
        except ValueError:
            ok('C14 tone 必须 1..4', True)
        d1 = RS.add_pron_decision(conn, 'p2', 0, 2, 'zhang3', 3, basis='《广韵》',
                                  why='此处作动词', client_token='tok-pron1')
        d1b = RS.add_pron_decision(conn, 'p2', 0, 2, 'zhang3', 3, client_token='tok-pron1')
        ok('C14 同 token 幂等（返回同一决策）', d1 == d1b and conn.execute(
            "SELECT COUNT(1) FROM decisions WHERE kind='pronounce' AND action='select'"
            " AND subject='p2|line=0|pos=2'").fetchone()[0] == 1)
        base_line = {'idx': 0, 'text': '白头游子白头妇，', 'pz': '平平平仄平平仄',
                     'ping': 5, 'ze': 2, 'tail': '妇'}
        lines = [dict(base_line)]
        l2, adj = RS.apply_pron_to_lines(conn, 'p2', lines)
        ok('C14 裁定生效（pz 平→仄）', l2[0]['pz'] == '平平仄仄平平仄'
           and adj and adj[0]['char'] == '游' and adj[0]['before'] == '平'
           and adj[0]['after'] == '仄')
        ok('C14 句级计数同步修正', l2[0]['ping'] == 4 and l2[0]['ze'] == 3)
        # 改选：同字位再 select → 生效值取新（历史两条都在）
        d2 = RS.add_pron_decision(conn, 'p2', 0, 2, 'you2', 2, why='重核后改回平声')
        eff = RS.effective_pron_decisions(conn, 'p2')
        ok('C14 改选后生效值为最新', len(eff) == 1 and eff[0]['decision_id'] == d2['decision_id'])
        # 撤回：撤下当前生效那条 → 回到基线（原样、零修正）
        wd = RS.withdraw_pron_decision(conn, d2['decision_id'], why='撤回重核')
        eff2 = RS.effective_pron_decisions(conn, 'p2')
        l3, adj3 = RS.apply_pron_to_lines(conn, 'p2', [dict(base_line)])
        ok('C14 撤回后回到原状', eff2 == [] and adj3 == []
           and l3[0]['pz'] == '平平平仄平平仄')
        hist = RS.list_pron_decisions(conn, 'p2')
        ok('C14 决策史完整（2 select + 1 withdraw 全在）', len(hist) == 3
           and [h['action'] for h in hist] == ['withdraw', 'select', 'select'])
        ok('C14 撤回指向原裁定（prev_id）', hist[0]['prev_id'] == d2['decision_id'])
        # 「护栏的护栏」：字位越界的裁定 → 安全跳过（不猜、不崩、不改）
        RS.add_pron_decision(conn, 'p2', 0, 99, 'shui2', 2)
        l4, adj4 = RS.apply_pron_to_lines(conn, 'p2', [{'idx': 0, 'text': '白头游子白头妇，',
                                                        'pz': '平平平仄平平仄', 'ping': 5,
                                                        'ze': 2, 'tail': '妇'}])
        ok('C14 越界字位安全跳过', l4[0]['pz'] == '平平平仄平平仄' and adj4 == [])
        # 只能撤回 select；不存在的决策报错
        try:
            RS.withdraw_pron_decision(conn, wd['withdraw_id'])
            ok('C14 只能撤回 select 类', False)
        except ValueError:
            ok('C14 只能撤回 select 类', True)

        # ---------- C15 批量导入：manifest + 幂等 + 对账 + 回滚 ----------
        fA = {'name': 'a.jsonl', 'rows': [
            {'title': '秋思', 'author': '甲', 'content': '秋风起兮白云飞。'},
            {'title': '春望', 'author': '甲', 'content': '春色满园关不住。'}]}
        fB = {'name': 'b.jsonl', 'rows': [
            {'title': '夜坐', 'author': '乙', 'content': '孤灯照壁雨潇潇。'}]}
        r1 = RS.import_rows(conn, '第一批', [fA, fB], note='测试导入')
        ok('C15 首次导入 3 行', r1['inserted'] == 3 and r1['skipped'] == 0
           and not r1['already'])
        ok('C15 作品入 personal_works（默认 draft）', conn.execute(
            "SELECT COUNT(1) FROM personal_works WHERE verification_state='draft'"
        ).fetchone()[0] >= 3)
        r1b = RS.import_rows(conn, '第一批（重试）', [fA, fB])
        ok('C15 同内容重复导入零新增（already）', r1b['already'] is True
           and r1b['inserted'] == 0 and r1b['batch_id'] == r1['batch_id'])
        fB2 = {'name': 'b.jsonl', 'rows': [
            {'title': '夜坐', 'author': '乙', 'content': '孤灯照壁雨潇潇。'},
            {'title': '新晴', 'author': '乙', 'content': '雨过天青云破处。'}]}
        r2 = RS.import_rows(conn, '第二批', [fA, fB2])
        ok('C15 部分重叠：只进新行、旧行跳过', r2['inserted'] == 1 and r2['skipped'] == 3)
        # 「护栏的护栏」：行级唯一键若被去掉，下面第二插必须抛 IntegrityError
        # （batch_id 用 999，避免干扰后面「回滚批次 1」的行数断言）
        try:
            conn.execute("INSERT INTO import_rows(batch_id,file,row_key,row_sha)"
                         " VALUES(999,'zz.jsonl','kr','sr')")
            conn.execute("INSERT INTO import_rows(batch_id,file,row_key,row_sha)"
                         " VALUES(999,'zz.jsonl','kr','sr')")
            ok('C15 行级唯一键存在', False, '重复插入未报错')
        except _s.IntegrityError:
            ok('C15 行级唯一键存在', True)
        bs = RS.list_import_batches(conn)
        b1 = [b for b in bs if b['id'] == r1['batch_id']][0]
        ok('C15 对账：承诺/现存行数一致', b1['n_rows'] == 3 and b1['rows_now'] == 3
           and b1['works_now'] == 3)
        rb = RS.rollback_import_batch(conn, r1['batch_id'], why='录错了')
        ok('C15 回滚撤下行与作品', rb['removed_rows'] == 3 and rb['removed_works'] == 3)
        ok('C15 回滚后批次记录保留（rolled_back）',
           [b for b in RS.list_import_batches(conn) if b['id'] == r1['batch_id']][0]['status']
           == 'rolled_back')
        ok('C15 第二批作品不受影响', conn.execute(
            'SELECT COUNT(1) FROM personal_works').fetchone()[0] >= 1)

        # ---------- C16 来源核验三态 ----------
        w1 = RS.add_personal_work(conn, '秋夜', '梧桐一叶落，天下尽知秋。', author='丙',
                                  client_token='tok-w1')
        ok('C16 新录入默认 draft', w1['verification_state'] == 'draft')
        try:
            RS.add_personal_work(conn, 'x', 'y', verification_state='source_matched')
            ok('C16 source_matched 必须给来源（不许空口自证）', False)
        except ValueError:
            ok('C16 source_matched 必须给来源（不许空口自证）', True)
        w2 = RS.add_personal_work(conn, '题壁', '山外青山楼外楼。', author='丁',
                                  verification_state='source_matched', source='《丁氏诗钞》卷上')
        ok('C16 带来源可入 source_matched', w2['verification_state'] == 'source_matched')
        v1 = RS.set_work_verification(conn, w1['work_id'], 'material_sample',
                                      source_material_id=1, why='与材料样例比对通过',
                                      client_token='tok-v1')
        ok('C16 状态流转留决策事件', v1['from'] == 'draft' and v1['to'] == 'material_sample'
           and RS.get_decision(conn, v1['decision_id'])['action'] == 'set_state')
        try:
            RS.set_work_verification(conn, w1['work_id'], 'source_matched')
            ok('C16 流转到 source_matched 仍需来源', False)
        except ValueError:
            ok('C16 流转到 source_matched 仍需来源', True)
        ok('C16 按状态过滤', len(RS.list_personal_works(conn, state='material_sample')) == 1
           and len(RS.list_personal_works(conn, state='source_matched')) >= 1)

        # ---------- C17 录入体检（功能 11）：只读 + 准报 + 不误伤 ----------
        sys.path.insert(0, os.path.join(ROOT, 'solve'))
        import intake as INK

        r0 = INK.check('', '有正文。', '')
        ok('C17 题名必填报 error', not r0['ok']
           and any(x['code'] == 'TITLE_REQUIRED' for x in r0['issues']))
        r1 = INK.check('清明同诸子集原白斋中', '清明同诸子集原白斋中。相思落花东风明月。', '蝶恋花')
        ok('C17 题名当正文准报（历史 bug 同口径）', any(
            x['code'] == 'TITLE_IN_BODY' and x['level'] == 'warn' for x in r1['issues']))
        # 「不误伤」：正文含常见词「相思/落花/东风/明月」，题名与之无关 → 不得有任何误报
        # （不带词牌：本用例只测「常见词」不触发误报，不引入体式检查）
        r2 = INK.check('二十自述', '相思落花东风明月。乙巳岁除书怀。', '')
        ok('C17 不误伤正文里的常见词', not any(x['level'] in ('warn', 'error')
                                           for x in r2['issues']),
           str([x['code'] for x in r2['issues']]))
        r3 = INK.check('无句读稿', '一二三四五六七八九十', '')
        ok('C17 句读缺失准报', any(x['code'] == 'NO_SENT_PUNCT' for x in r3['issues']))
        tune_sent = ('怨眉梢。恨眉梢。一种痴情未许描。真愁彩笔凋。'
                     '魂儿消。影儿娇。如此温柔要福销。他生谥洞箫。')
        r4 = INK.check('长相思', tune_sent, '长相思')
        ok('C17 词牌体式匹配（36 字 8 句 ↔ 谱式）', any(
            x['code'] == 'TUNE_MATCH' for x in r4['issues']))
        r5 = INK.check('偏短稿', '怨眉梢。恨眉梢。', '长相思')
        ok('C17 与谱式字数差异大准报 warn', any(
            x['code'] == 'TUNE_CHARS_FAR' and x['level'] == 'warn' for x in r5['issues']))
        r6 = INK.check('甲', '春水碧于天。', '金缕曲')
        ok('C17 谱库外词牌如实跳过（info）', any(
            x['code'] == 'TUNE_NOT_IN_CIPU' and x['level'] == 'info' for x in r6['issues']))

        # ---------- C18 冻结快照（功能 1）：冻结/回查/陈旧标注/不重算 ----------
        import snapshot as SNAP
        SNAP._DIR = os.path.join(tmp, 'snapshots')          # 隔离：不写真实 data/snapshots/
        fake_out = {'spec': '朝代=清；词牌=临江仙', 'answer': '原始答案', 'total': 59,
                    'refused': False, 'reason': {'code': 'ok'}, 'blocks': [{'pid': 'p1'}],
                    'verify': {'ok': True, 'problems': []},
                    'set_check': {'status': 'VERIFIED_DERIVED'}, 'understanding_status': 'OK'}
        sid1 = SNAP.capture(fake_out, '清 临江仙 仄声比例高于45%', ['p1', 'p2', 'p3'],
                            spec=None, sid=None, turn_no=1)
        ok('C18 快照 id 形态正确', bool(re.match(r'^snap-\d{8}-\d{6}-[0-9a-f]{6}$', sid1)), sid1)
        lst = SNAP.list_recent(10)
        ok('C18 历史可列出', len(lst) == 1 and lst[0]['snapshot_id'] == sid1)
        snap = SNAP.load(sid1)
        ok('C18 回查内容与当时一致', snap['answer'] == '原始答案'
           and snap['result']['pids'] == ['p1', 'p2', 'p3']
           and snap['result']['pids_sha'])
        ok('C18 口径未变时 stale=False', snap['stale'] is False and snap['stale_fields'] == [])
        # ① 篡改测试（护栏的护栏）：直接改盘上的 answer，load 必须**原样读回**——
        #    若 load 用现在的引擎重算历史，这里就会读回「原始答案」而不是篡改值，测试即崩。
        pth = os.path.join(SNAP._DIR, sid1 + '.json')
        import json as _json
        d = _json.load(open(pth, encoding='utf-8'))
        d['answer'] = '被篡改的答案-原样读回验证'
        d['fingerprint']['corpus'] = 'deadbeefdeadbeef'      # 同时伪造「旧口径」
        _json.dump(d, open(pth, 'w', encoding='utf-8'), ensure_ascii=False)
        snap2 = SNAP.load(sid1)
        ok('C18 回查=读原文，绝不重算覆盖', snap2['answer'] == '被篡改的答案-原样读回验证')
        ok('C18 口径变化标注「依赖已陈旧」', snap2['stale'] is True
           and 'corpus' in snap2['stale_fields']
           and '未经重算' in (snap2.get('stale_note') or ''))
        ok('C18 陈旧也不改旧答案', snap2['answer'] == '被篡改的答案-原样读回验证')
        # ② 路径穿越与不存在
        ok('C18 非法 id 拒绝', SNAP.load('../../etc/passwd') is None
           and SNAP.load('snap-19990101-000000-abcdef') is None)
        # ③ 指纹与独立复算一致（测试自己算一遍 4 个数字，不借 vector_index）
        import sqlite3 as _s3
        cc = _s3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
        n_p = cc.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
        n_l = cc.execute('SELECT COUNT(*) FROM lines').fetchone()[0]
        s_h = cc.execute('SELECT COALESCE(SUM(han_len),0) FROM poems').fetchone()[0]
        mx = cc.execute("SELECT COALESCE(MAX(pid),'') FROM poems").fetchone()[0]
        cc.close()
        import hashlib as _hl
        expect = _hl.sha256(('%d|%d|%s|%s' % (n_p, n_l, s_h, mx)).encode('utf-8')).hexdigest()[:16]
        ok('C18 语料指纹=独立复算（同式同值）', SNAP.fingerprint()['corpus'] == expect)

    finally:
        try:
            conn.close()
        except Exception:                     # noqa: BLE001
            pass
        shutil.rmtree(tmp, ignore_errors=True)

    print('=' * 64)
    print('研究库门禁：比对 %d 项，不符 %d 项' % (CMP[0], len(BAD)))
    for b in BAD:
        print('  ✗', b)
    print('结果：%s' % ('PASS' if not BAD and CMP[0] > 0 else 'FAIL'))
    return 0 if (not BAD and CMP[0] > 0) else 1


if __name__ == '__main__':
    sys.exit(main())

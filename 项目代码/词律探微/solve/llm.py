# -*- coding: utf-8 -*-
"""llm.py —— 国产大模型调用层（**只用 Python 标准库**，不引入任何第三方 SDK）。

为什么单独一层：
    本项目的原则是「**数字归引擎、文料归检索、说法归生成、出处归引用**」。
    大模型只负责「说法」这一层——把引擎算好的事实写成通顺的研究性说明；
    **任何数字都必须在证据块里找得到**（由 `gen.py` 调用 `guard.py` 逐行校验）。
    取不到密钥或联网失败时**安静降级**：返回 None，系统回落到确定性模板作答，
    所以「断网也能完整作答」这件事不会被大模型破坏。

合规（赛事红线）：只内置国产服务商。**禁止**接入境外模型或境外智能体工具。

密钥读取顺序（环境变量，任取其一）：
    provider 可显式指定，也可用 LVC_LLM_PROVIDER；模型可用 LVC_LLM_MODEL 覆盖。

用法：
    python solve/llm.py --check            # 看哪家可用（不发请求）
    python solve/llm.py --ping             # 真发一次最小请求
    python solve/llm.py --ask "用一句话说明什么是仄声"
"""
import argparse
import json
import os
import sys
import threading
import urllib.error
import urllib.request

PROVIDERS = {
    # 校内/自建 Chat Completions 协议端点（主人指定）：qwen3.8-27b。
    # 措辞说明（2026-10-02）：此处原写「某境外厂商兼容」，被 `solve/preflight.py` 第 7 段
    # 的关键词扫描（扫若干境外厂商名）判成「代码中无境外模型调用」FAIL，
    # 于是体检长期 25/1/0 而无人察觉。**这里是协议名（API 格式），不是调用境外服务**；
    # 改成中性的「Chat Completions 协议」，含义不变、也不再触发误报。
    # 注意它是**推理模型**：默认先输出 `reasoning` 再输出 `content`；若 max_tokens 偏小，
    # 思考会把预算吃光导致 `content` 为 null（实测 max_tokens=16 时 content=null）。
    # 因此默认带 `chat_template_kwargs={"enable_thinking": false}`：实测既拿得到 content，
    # 首字延迟也从 0.90 秒降到 0.40 秒（2.25×）。
    'ucass': dict(label='校内 Qwen（qwen3.8-27b）',
                  url=os.environ.get('UCASS_LLM_URL', 'http://10.27.66.12/v1/chat/completions'),
                  model=os.environ.get('UCASS_LLM_MODEL', 'qwen3.8-27b'),
                  env=('UCASS_API_KEY', 'SPARK_API_KEY', 'LVC_LLM_KEY')),
    'zhipu': dict(label='智谱 GLM', url='https://open.bigmodel.cn/api/paas/v4/chat/completions',
                  model='glm-4-flash',
                  env=('ZAI_API_KEY', 'ZHIPU_API_KEY', 'GLM_API_KEY', 'LVC_LLM_KEY')),
    'deepseek': dict(label='DeepSeek', url='https://api.deepseek.com/chat/completions',
                     model='deepseek-chat',
                     env=('DEEPSEEK_API_KEY', 'LVC_LLM_KEY')),
    'dashscope': dict(label='通义千问 Qwen',
                      url='https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                      model='qwen-plus',
                      env=('DASHSCOPE_API_KEY', 'QWEN_API_KEY', 'LVC_LLM_KEY')),
}
# 校内端点优先（若其密钥可用）；其余为备用
ORDER = ('ucass', 'zhipu', 'deepseek', 'dashscope')

# 本地配置文件（**密钥不写进源码**）：solve/data/llm_local.json
#   {"provider": "ucass", "url": "...", "model": "...", "key": "..."}
# 优先级：显式参数 > 环境变量 > 本地配置文件 > PROVIDERS 默认值
LOCAL_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'llm_local.json')

# 「缓存未命中」哨兵：`dict.get` 无法区分「没有」与「存的就是 None」，用一个独立对象做标记。
_MISS = object()


class LLM:
    """一个极小的对话客户端。`available()` 为假时调用方应回落到模板。"""

    def __init__(self, provider=None, model=None, key=None, timeout=None, max_retry=1,
                 enable_thinking=False, cache_size=64, stream=True):
        # 超时默认 25 秒（原来 40 秒偏长——响应速度优先；可用 LVC_LLM_TIMEOUT 覆盖）
        self.timeout = int(timeout or os.environ.get('LVC_LLM_TIMEOUT') or 25)
        self.max_retry = max_retry
        # ⚠ 2026-10-08 修（外部审查 P0：共享可变状态竞争）——
        #   改前：`self.calls` / `self.last_error` / `self._cache` 都是**实例级可变状态**；
        #         而 `web/serve.py:122 get_llm()` 返回的是**全局唯一 LLM 实例**（多线程共享），
        #         且 serve.py 自 2026-10-06 起已不再用 LOCK 包住 LLM 调用（见 serve.py:128-137
        #         的说明）→ 真并发。症状：请求 A 写 `last_error='timeout'` → 请求 B 成功写 `None`
        #         → A 回来读到的却是 B 的 `None`，`chat()` 里「流式重试 / EMPTY_CONTENT 重试 /
        #         直接结束」的分支判定随之错乱；`_cache` 无锁并发读写也可能损坏。
        #   改后（依据：下方 `last_error` / `calls` 两个 property + `_cache_get/_cache_put`）：
        #     · `last_error` 是**每次调用的瞬时状态** → 放进 `threading.local()`，每线程各看各的，
        #       不再跨请求串号（选它而非「改成返回值」是因为它已被外部读取，见下）；
        #     · `calls`（进程内累计计数，语义上是共享的）→ 用 `self._lock` 保护的 `self._calls`；
        #     · `_cache` 的读 / 写 / 淘汰统一加 `self._lock`。
        #   兼容：刻意**保留 `last_error` / `calls` / `_cache` 同名属性**（前两者为 property），
        #         使 `ask.py:1751`、`gen.py:121`、`web/serve.py:426` 的 `client.last_error`、
        #         `selftest.py:342` 的 `_FakeLLM.last_error=None`、`web/test_api.py:256` 的
        #         `_StubLLM.last_error=''` 等既有读写方式**一行都不用改**。
        self._lock = threading.Lock()
        self._tls = threading.local()          # 线程私有的瞬时调用状态（last_error）
        self._calls = 0
        self.last_error = None                 # 经 property 写入 _tls，见下方定义
        self.enable_thinking = bool(enable_thinking)
        self.stream_default = bool(stream)     # 默认流式（首字快一个数量级；可用 stream=False 关闭）
        self._cache = {}
        self._cache_size = max(0, cache_size)
        conf = self._local_conf()
        self.provider = (provider or os.environ.get('LVC_LLM_PROVIDER')
                         or conf.get('provider') or self._auto())
        if self.provider and self.provider in PROVIDERS:
            p = PROVIDERS[self.provider]
            # ⚠ 2026-10-04 修（代码审查 P0-2）：本地配置文件原先被**无条件**当作
            #   url/model/key 的来源，于是 `--provider deepseek/zhipu/…` 只改了 label、
            #   实际仍把请求发到配置里那一家（实测三家解析结果完全相同）——多 provider
            #   备用链路形同虚设。现在按 provider 分层：
            #     · 扁平写法（老配置，只服务一家）→ 仅当它就是被选中的 provider 时才用；
            #     · 分节写法 {"ucass": {...}, "deepseek": {...}} → 按 provider 取；
            #     · 都没有 → 回落到 PROVIDERS 默认值 + 环境变量里的密钥。
            sect = conf.get(self.provider) if isinstance(conf.get(self.provider), dict) else None
            if sect is None and conf.get('provider') == self.provider:
                sect = conf
            sect = sect or {}
            self.url = sect.get('url') or p['url']
            self.model = (model or os.environ.get('LVC_LLM_MODEL')
                          or sect.get('model') or p['model'])
            self.key = (key or next((os.environ[e] for e in p['env'] if os.environ.get(e)), None)
                        or sect.get('key'))
            self.label = p['label']
        else:
            self.url = self.model = self.key = self.label = None
        self.name = '%s:%s' % (self.provider, self.model) if self.provider and self.key else None

    @staticmethod
    def _local_conf():
        """读本地配置文件（密钥不落源码）；文件不存在或损坏时安静返回 {}。"""
        try:
            if os.path.isfile(LOCAL_CONF):
                with open(LOCAL_CONF, encoding='utf-8-sig') as f:
                    d = json.load(f)
                return d if isinstance(d, dict) else {}
        except Exception:
            pass
        return {}

    @staticmethod
    def _auto():
        for name in ORDER:
            if any(os.environ.get(e) for e in PROVIDERS[name]['env']):
                return name
        return None

    # —— 线程安全支撑（改前 → 改后 → 依据，详见 __init__ 注释）——
    #   改前：`last_error`/`calls` 是普通实例属性、`_cache` 是裸 dict，均无保护。
    #   改后：`last_error` 落线程本地；`calls` 与 `_cache` 用 `self._lock` 保护。
    @property
    def last_error(self):
        """本线程**最近一次**调用的失败原因（成功为 None）。线程隔离，不与其他请求串号。"""
        return getattr(self._tls, 'last_error', None)

    @last_error.setter
    def last_error(self, value):
        self._tls.last_error = value

    @property
    def calls(self):
        """累计发起的底层请求次数（进程内共享计数；读写均加锁，保持同名属性兼容）。"""
        with self._lock:
            return self._calls

    @calls.setter
    def calls(self, value):
        with self._lock:
            self._calls = value

    def _bump_call(self):
        with self._lock:
            self._calls += 1

    def _cache_get(self, ck):
        with self._lock:
            return self._cache.get(ck, _MISS)

    def _cache_put(self, ck, value):
        with self._lock:
            if self._cache_size and len(self._cache) >= self._cache_size:
                self._cache.pop(next(iter(self._cache)))
            self._cache[ck] = value

    def available(self):
        return bool(self.provider and self.key and self.url)

    def _body(self, messages, temperature, max_tokens, thinking):
        d = {'model': self.model, 'messages': messages, 'temperature': temperature,
             'max_tokens': max_tokens, 'stream': False}
        if not thinking:            # 推理模型：关思考才拿得到 content，且首字延迟减半（实测 0.90→0.40 秒）
            d['chat_template_kwargs'] = {'enable_thinking': False}
        return json.dumps(d).encode('utf-8')

    def chat(self, messages, temperature=0.2, max_tokens=800, thinking=None,
             stream=None, expect_json=False, on_delta=None):
        """发一次对话请求，返回文本；失败返回 None（并把原因留在 last_error）。

        响应速度与稳健性的三条改动：
          · **默认关思考**（`enable_thinking=False`）—— 实测首字延迟 0.90→0.40 秒，
            且避免「思考吃光 token 预算 → content 为 null」；
          · **进程内响应缓存**：同模型同消息同参数直接命中（问答演示反复问同一句时几乎零延迟）；
          · **content 为空但 reasoning 非空时自动重试一次**（这次强制关思考），
            仍失败则把原因写清楚，绝不把「取不到内容」伪装成「模型不可用」。
        """
        if not self.available():
            self.last_error = ('没有可用的大模型密钥（环境变量 UCASS_API_KEY / SPARK_API_KEY / '
                               'LVC_LLM_KEY，或 %s）' % os.path.relpath(LOCAL_CONF))
            return None
        think = self.enable_thinking if thinking is None else bool(thinking)
        # 流式（默认开）：首字延迟低一个数量级；`expect_json` 时拿到完整 JSON 即断开。
        # 若流式失败（服务端不支持 SSE 等），自动回退到整段请求。
        use_stream = self.stream_default if stream is None else bool(stream)
        ck = (self.model, json.dumps(messages, ensure_ascii=False), temperature, max_tokens,
              think, use_stream, expect_json)
        if on_delta is None:
            # ⚠ 2026-10-04 修（代码审查 P3-5）：旧写法外层已要求 `on_delta is None`，
            #   内层 `if on_delta and cached` 永假（死分支），已删；顺带说明：
            #   传了 on_delta（边生成边显示）时不读缓存，这是刻意的（否则"流式"没有增量）。
            # ⚠ 2026-10-08 修（P0 并发）：缓存读取改走 `_cache_get`（持锁），与写入对称。
            _hit = self._cache_get(ck)
            if _hit is not _MISS:
                return _hit
        out = None
        if use_stream:
            out = self.chat_stream(messages, temperature, max_tokens, think,
                                   expect_json=expect_json, on_delta=on_delta)
        if out is None and not use_stream:
            out = self._chat_once(messages, temperature, max_tokens, think)
        if out is None and use_stream and self.last_error and 'EMPTY_CONTENT' not in self.last_error:
            out = self._chat_once(messages, temperature, max_tokens, think)   # 流式失败 → 整段重试
        if out is None and self.last_error and self.last_error.startswith('EMPTY_CONTENT'):
            # 典型症状：推理模型把预算全花在思考上，content 为 null → 关思考重试一次。
            # ⚠ 2026-10-04 修（代码审查 P3-4）：旧写法 `max(min(max_tokens, 800), 512)`
            #   对 max_tokens>800 的调用会**把预算调小**（1000 → 800），与注释「调大预算」相反。
            #   改为：至少 512，且不小于原预算。
            out = self._chat_once(messages, temperature, max(max_tokens, 512), False)
        if out is not None and self._cache_size:
            self._cache_put(ck, out)          # ⚠ 2026-10-08 修（P0 并发）：持锁写入/淘汰
        return out

    def _chat_once(self, messages, temperature, max_tokens, thinking):
        body = self._body(messages, temperature, max_tokens, thinking)
        last = None
        for attempt in range(self.max_retry + 1):
            req = urllib.request.Request(self.url, data=body, method='POST', headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % self.key,
                'User-Agent': 'cilv-tanwei/1.0',
            })
            try:
                self._bump_call()          # ⚠ 2026-10-08（P0 并发）：计数加锁，替代 self.calls += 1
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode('utf-8'))
                ch = (data.get('choices') or [{}])[0]
                msg = ch.get('message') or {}
                content = msg.get('content')
                if content:
                    self.last_error = None
                    return content
                # content 为空：区分两种原因，别把「思考吃光预算」说成「模型不可用」
                if (msg.get('reasoning') or '').strip():
                    self.last_error = ('EMPTY_CONTENT：模型只产出思考、未产出正文'
                                       '（max_tokens=%s 可能被思考占满；可用 enable_thinking=False 或调大预算）'
                                       % max_tokens)
                else:
                    self.last_error = 'EMPTY_CONTENT：返回结构里没有正文（finish_reason=%s）' % ch.get('finish_reason')
                return None
            except urllib.error.HTTPError as e:
                detail = ''
                try:
                    detail = e.read().decode('utf-8', 'replace')[:200]
                except Exception:
                    pass
                last = 'HTTP %s %s' % (e.code, detail)
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except Exception as e:                                   # 超时/断网/DNS
                last = '%s: %s' % (type(e).__name__, e)
            if attempt < self.max_retry:
                import time
                time.sleep(1.5)
        self.last_error = last
        return None

    # ------------------------------------------------------------ 流式（响应速度）
    @staticmethod
    def _complete_json(text):
        """文本里是否已出现一个括号配平的 JSON 对象（字符串内的括号不计数）。"""
        depth = 0
        in_str = False
        esc = False
        for ch in text or '':
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return True
        return False

    def chat_stream(self, messages, temperature=0.2, max_tokens=800, thinking=None,
                    expect_json=False, on_delta=None):
        """流式取回：逐块回调 `on_delta(片段)`，返回完整文本；失败返回 None。

        响应速度：实测首字 **0.34~0.47 秒**，而整段返回要 1.6~2.2 秒（服务端抖动时更久）。
        `expect_json=True` 时**一见到配平的 JSON 就断开**，不为多余的尾巴继续等。
        """
        if not self.available():
            self.last_error = '没有可用的大模型密钥'
            return None
        think = self.enable_thinking if thinking is None else bool(thinking)
        body = json.loads(self._body(messages, temperature, max_tokens, think).decode('utf-8'))
        body['stream'] = True
        req = urllib.request.Request(self.url, data=json.dumps(body).encode('utf-8'),
                                     method='POST', headers={
                                         'Content-Type': 'application/json',
                                         'Authorization': 'Bearer %s' % self.key,
                                         'Accept': 'text/event-stream',
                                         'User-Agent': 'cilv-tanwei/1.0'})
        buf = []
        try:
            self._bump_call()              # ⚠ 2026-10-08（P0 并发）：计数加锁，替代 self.calls += 1
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                ctype = (r.headers.get('Content-Type') or '')
                if 'event-stream' not in ctype:       # 服务端未走 SSE → 当普通响应处理
                    data = json.loads(r.read().decode('utf-8'))
                    msg = ((data.get('choices') or [{}])[0].get('message') or {})
                    out = msg.get('content')
                    if out and on_delta:
                        on_delta(out)
                    self.last_error = None if out else 'EMPTY_CONTENT：非流式回退也没拿到正文'
                    return out
                for raw in r:
                    line = raw.decode('utf-8', 'replace').strip()
                    if not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if payload == '[DONE]':
                        break
                    try:
                        d = json.loads(payload)
                    except Exception:
                        continue
                    piece = ((d.get('choices') or [{}])[0].get('delta') or {}).get('content')
                    if not piece:
                        continue
                    buf.append(piece)
                    if on_delta:
                        try:
                            on_delta(piece)
                        except Exception:
                            pass
                    if expect_json and self._complete_json(''.join(buf)):
                        break                          # 已拿到完整 JSON，不再等尾巴
            text = ''.join(buf)
            self.last_error = None if text else 'EMPTY_CONTENT：流式响应没有正文'
            return text or None
        except Exception as e:
            self.last_error = '%s: %s' % (type(e).__name__, e)
            return None

    def ping(self):
        return self.chat([{'role': 'user', 'content': '只回复两个字：可用'}], max_tokens=8)


def main():
    ap = argparse.ArgumentParser(description='国产大模型调用层（标准库实现）')
    ap.add_argument('--provider', default=None, choices=sorted(PROVIDERS))
    ap.add_argument('--model', default=None)
    ap.add_argument('--check', action='store_true', help='看哪家可用（不发请求）')
    ap.add_argument('--ping', action='store_true', help='真发一次最小请求')
    ap.add_argument('--ask', default=None)
    a = ap.parse_args()
    if a.check or (not a.ping and not a.ask):
        for name in ORDER:
            p = PROVIDERS[name]
            has = [e for e in p['env'] if os.environ.get(e)]
            print('%-10s %-12s 密钥=%s%s' % (name, p['model'],
                                             '有(%s)' % has[0] if has else '无',
                                             '　← 自动选中' if name == LLM._auto() else ''))
        lv = LLM(provider=a.provider)
        print('\n当前可用：%s' % (lv.name if lv.available() else '无（将回落到模板作答）'))
        return 0
    lv = LLM(provider=a.provider, model=a.model)
    if not lv.available():
        print('✗ %s' % lv.last_error)
        return 2
    if a.ping:
        print('调用 %s …' % lv.name)
        t = lv.ping()
        print(('✓ 返回：%s' % t) if t else ('✗ 失败：%s' % lv.last_error))
        return 0 if t else 1
    t = lv.chat([{'role': 'user', 'content': a.ask}], max_tokens=200)
    print(t if t else ('✗ 失败：%s' % lv.last_error))
    return 0 if t else 1


if __name__ == '__main__':
    sys.exit(main())

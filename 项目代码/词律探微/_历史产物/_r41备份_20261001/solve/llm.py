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
import urllib.error
import urllib.request

PROVIDERS = {
    # 校内/自建 OpenAI 兼容端点（主人指定）：qwen3.8-27b。
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


class LLM:
    """一个极小的对话客户端。`available()` 为假时调用方应回落到模板。"""

    def __init__(self, provider=None, model=None, key=None, timeout=None, max_retry=1,
                 enable_thinking=False, cache_size=64, stream=True):
        # 超时默认 25 秒（原来 40 秒偏长——响应速度优先；可用 LVC_LLM_TIMEOUT 覆盖）
        self.timeout = int(timeout or os.environ.get('LVC_LLM_TIMEOUT') or 25)
        self.max_retry = max_retry
        self.calls = 0
        self.last_error = None
        self.enable_thinking = bool(enable_thinking)
        self.stream_default = bool(stream)     # 默认流式（首字快一个数量级；可用 stream=False 关闭）
        self._cache = {}
        self._cache_size = max(0, cache_size)
        conf = self._local_conf()
        self.provider = (provider or os.environ.get('LVC_LLM_PROVIDER')
                         or conf.get('provider') or self._auto())
        if self.provider and self.provider in PROVIDERS:
            p = PROVIDERS[self.provider]
            self.url = conf.get('url') or p['url']
            self.model = model or os.environ.get('LVC_LLM_MODEL') or conf.get('model') or p['model']
            self.key = (key or next((os.environ[e] for e in p['env'] if os.environ.get(e)), None)
                        or conf.get('key'))
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
        if ck in self._cache and on_delta is None:
            cached = self._cache[ck]
            if on_delta and cached:
                on_delta(cached)
            return cached
        out = None
        if use_stream:
            out = self.chat_stream(messages, temperature, max_tokens, think,
                                   expect_json=expect_json, on_delta=on_delta)
        if out is None and not use_stream:
            out = self._chat_once(messages, temperature, max_tokens, think)
        if out is None and use_stream and self.last_error and 'EMPTY_CONTENT' not in self.last_error:
            out = self._chat_once(messages, temperature, max_tokens, think)   # 流式失败 → 整段重试
        if out is None and self.last_error and self.last_error.startswith('EMPTY_CONTENT'):
            # 典型症状：推理模型把预算全花在思考上，content 为 null → 关思考重试一次
            out = self._chat_once(messages, temperature, max(min(max_tokens, 800), 512), False)
        if out is not None and self._cache_size:
            if len(self._cache) >= self._cache_size:
                self._cache.pop(next(iter(self._cache)))
            self._cache[ck] = out
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
                self.calls += 1
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
            self.calls += 1
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

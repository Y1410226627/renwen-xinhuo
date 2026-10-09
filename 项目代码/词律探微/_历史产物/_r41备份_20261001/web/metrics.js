/* metrics.js —— 声律指标的唯一前端实现（浏览器与 node 共用同一份代码）。
 *
 * 这一份**不是把 Python 结果搬过来展示**，而是按同一套口径用 JavaScript 重算一遍：
 * 评委若把网页上的数字与 Python 引擎的数字对照，两边必须一致（见 web/verify_views.js）。
 *
 * 口径（与 solve/prosody.py 完全一致）：
 *   · 只数汉字（CJK 统一表意 + 扩展 A）；平仄按普通话（1、2 声平，3、4 声仄，轻声记平）；
 *   · 前段 = 前 ⌊n/2⌋ 句；比例 = 100 × 仄 / 汉字数，**银行家舍入**保留一位；
 *   · 变化 = r1(后段原始比例 − 前段原始比例)（原始值相减，不是先舍入再相减）；
 *   · 最长句序 = 最长句的句序（1 起，含并列）；阈值 = ⌈全篇汉字 ÷ 句数⌉。
 *   · 声情转向 = 变化 > 0 上升 / < 0 下降 / = 0 持平。
 */
(function (root) {
  'use strict';
  var HAN = /[\u3400-\u4dbf\u4e00-\u9fff]/;

  function hanOnly(s) { return (s || '').replace(/[^\u3400-\u4dbf\u4e00-\u9fff]/g, ''); }

  function banker1(x) {                     // 银行家舍入：恰为 X.X5 时向偶数取整
    var neg = x < 0, y = Math.abs(x);
    var i = Math.floor(y * 10 + 1e-9);
    var frac = y * 10 - i;
    if (frac > 0.5 + 1e-9) { i += 1; }
    else if (Math.abs(frac - 0.5) <= 1e-9) { if (i % 2 === 1) { i += 1; } }
    var v = i / 10;
    return neg ? -v : v;
  }

  function count(s, ch) { var n = 0, i = 0; for (; i < s.length; i++) { if (s[i] === ch) { n++; } } return n; }

  /* lines: [{text, pz}]（pz 为逐字平仄串，只含 平/仄） */
  function compute(lines) {
    var pzAll = lines.map(function (L) { return L.pz; }).join('');
    var n = lines.length, cut = Math.floor(n / 2);
    var head = lines.slice(0, cut).map(function (L) { return L.pz; }).join('');
    var back = lines.slice(cut).map(function (L) { return L.pz; }).join('');
    var fRaw = head.length ? 100 * count(head, '仄') / head.length : 0;
    var bRaw = back.length ? 100 * count(back, '仄') / back.length : 0;
    var lens = lines.map(function (L) { return L.pz.length; });
    var mx = Math.max.apply(null, lens);
    var seq = [];
    for (var i = 0; i < lens.length; i++) { if (lens[i] === mx) { seq.push(i + 1); } }
    var d = banker1(bRaw - fRaw);
    var hz = pzAll.length;
    return {
      han_len: hz, sent_n: n, ping: count(pzAll, '平'), ze: count(pzAll, '仄'),
      ze_ratio: banker1(hz ? 100 * count(pzAll, '仄') / hz : 0),
      cut: cut, f_ratio: banker1(fRaw), b_ratio: banker1(bRaw),
      change: d, abs_change: Math.abs(d),
      longest_len: mx, longest_seq: seq,
      threshold: hz ? Math.ceil(hz / n) : 0,
      scene: d > 0 ? '后段上升' : (d < 0 ? '后段下降' : '前后持平')
    };
  }

  function hanLen(s) { return hanOnly(s).length; }

  var api = { compute: compute, banker1: banker1, hanOnly: hanOnly, hanLen: hanLen,
              count: count, HAN: HAN };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  root.Metrics = api;
}(typeof window !== 'undefined' ? window : this));

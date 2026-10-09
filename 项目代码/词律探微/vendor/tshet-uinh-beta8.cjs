(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
    typeof define === 'function' && define.amd ? define(['exports'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.TshetUinh = {}));
})(this, (function (exports) { 'use strict';

    function assert(condition, errorMessage) {
        if (!condition) {
            throw new Error(typeof errorMessage === 'function' ? errorMessage() : errorMessage);
        }
    }
    function insertInto(map, key, value) {
        if (!map.has(key)) {
            map.set(key, [value]);
        }
        else {
            map.get(key).push(value);
        }
    }
    function insertValuesInto(map, key, values) {
        if (!map.has(key)) {
            map.set(key, [...values]);
        }
        else {
            map.get(key).push(...values);
        }
    }
    function prependValuesInto(map, key, values) {
        if (!map.has(key)) {
            map.set(key, [...values]);
        }
        else {
            map.get(key).unshift(...values);
        }
    }

    // dprint-ignore
    const 母到清濁 = {
        幫: '全清',
        端: '全清', 知: '全清',
        精: '全清', 心: '全清', 莊: '全清', 生: '全清', 章: '全清', 書: '全清',
        見: '全清', 影: '全清', 曉: '全清',
        滂: '次清',
        透: '次清', 徹: '次清',
        清: '次清', 初: '次清', 昌: '次清',
        溪: '次清',
        並: '全濁',
        定: '全濁', 澄: '全濁',
        從: '全濁', 邪: '全濁', 崇: '全濁', 俟: '全濁', 常: '全濁', 船: '全濁',
        羣: '全濁', 匣: '全濁',
        明: '次濁',
        泥: '次濁', 孃: '次濁', 來: '次濁', 日: '次濁',
        疑: '次濁', 云: '次濁', 以: '次濁',
    };
    // dprint-ignore
    const 母到組 = {
        幫: '幫', 滂: '幫', 並: '幫', 明: '幫',
        端: '端', 透: '端', 定: '端', 泥: '端',
        知: '知', 徹: '知', 澄: '知', 孃: '知',
        精: '精', 清: '精', 從: '精', 心: '精', 邪: '精',
        莊: '莊', 初: '莊', 崇: '莊', 生: '莊', 俟: '莊',
        章: '章', 昌: '章', 船: '章', 書: '章', 常: '章',
        見: '見', 溪: '見', 羣: '見', 疑: '見',
        影: '影', 曉: '影', 匣: '影', 云: '影',
        來: null, 日: null, 以: null,
    };
    // dprint-ignore
    const 母到音 = {
        幫: '脣', 滂: '脣', 並: '脣', 明: '脣',
        端: '舌', 透: '舌', 定: '舌', 泥: '舌',
        知: '舌', 徹: '舌', 澄: '舌', 孃: '舌',
        來: '舌',
        精: '齒', 清: '齒', 從: '齒', 心: '齒', 邪: '齒',
        莊: '齒', 初: '齒', 崇: '齒', 生: '齒', 俟: '齒',
        章: '齒', 昌: '齒', 常: '齒', 書: '齒', 船: '齒',
        日: '齒',
        見: '牙', 溪: '牙', 羣: '牙', 疑: '牙',
        影: '喉', 曉: '喉', 匣: '喉', 云: '喉',
        以: '喉',
    };
    // dprint-ignore
    const 韻到攝 = {
        東: '通', 冬: '通', 鍾: '通',
        江: '江',
        支: '止', 脂: '止', 之: '止', 微: '止',
        魚: '遇', 虞: '遇', 模: '遇',
        齊: '蟹', 佳: '蟹', 皆: '蟹', 灰: '蟹', 咍: '蟹', 祭: '蟹', 泰: '蟹', 夬: '蟹', 廢: '蟹',
        真: '臻', 諄: '臻', 臻: '臻', 文: '臻', 殷: '臻', 魂: '臻', 痕: '臻',
        元: '山', 寒: '山', 桓: '山', 刪: '山', 山: '山', 先: '山', 仙: '山',
        蕭: '效', 宵: '效', 肴: '效', 豪: '效',
        歌: '果', 戈: '果',
        麻: '假',
        唐: '宕', 陽: '宕',
        庚: '梗', 耕: '梗', 清: '梗', 青: '梗',
        登: '曾', 蒸: '曾',
        侯: '流', 尤: '流', 幽: '流',
        侵: '深',
        覃: '咸', 談: '咸', 鹽: '咸', 添: '咸', 咸: '咸', 銜: '咸', 嚴: '咸', 凡: '咸',
    };

    /** 全部六要素之枚舉 */
    const 所有 = {
        母: [...'幫滂並明端透定泥來知徹澄孃精清從心邪莊初崇生俟章昌常書船日見溪羣疑影曉匣云以'],
        呼: [...'開合'],
        等: [...'一二三四'],
        類: [...'ABC'],
        韻: [...'東冬鍾江支脂之微魚虞模齊祭泰佳皆夬灰咍廢真臻文殷元魂痕寒刪山先仙蕭宵肴豪歌麻陽唐庚耕清青蒸登尤侯幽侵覃談鹽添咸銜嚴凡'],
        聲: [...'平上去入'],
    };
    /** 幫見影組聲母，在三等分ABC類 */
    const 鈍音母 = [...'幫滂並明見溪羣疑影曉匣云'];
    const 陰聲韻 = [...'支脂之微魚虞模齊祭泰佳皆夬灰咍廢蕭宵肴豪歌麻侯尤幽'];
    function reverseLookup(搭配表) {
        const res = {};
        for (const [k, vs] of Object.entries(搭配表)) {
            for (const v of vs) {
                assert(!(v in res), () => `duplicate entry: ${v}`);
                res[v] = k === '中立' ? '' : k;
            }
        }
        return res;
    }
    /** 依可搭配的等列出各韻 */
    const 等韻搭配 = {
        一: [...'冬模泰灰咍魂痕寒豪唐登侯覃談'],
        二: [...'江佳皆夬刪山肴耕咸銜'],
        三: [...'鍾支脂之微魚虞祭廢真臻文殷元仙宵陽清蒸尤幽侵鹽嚴凡'],
        四: [...'齊先蕭青添'],
        一三: [...'東歌'],
        二三: [...'麻庚'],
    };
    /** 依韻取得可搭配的所有等 */
    const 韻搭配等 = reverseLookup(等韻搭配);
    /** 依可搭配的呼列出各韻。開合中立韻的索引為 `中立`。 */
    const 呼韻搭配 = {
        開合: [...'支脂微齊祭泰佳皆夬廢真元寒刪山先仙歌麻陽唐庚耕清青蒸登'],
        開: [...'之魚咍臻殷痕蕭宵肴豪幽侵覃談鹽添咸銜嚴'],
        合: [...'虞灰文魂凡'],
        中立: [...'東冬鍾江模尤侯'],
    };
    /** 依韻取得可搭配的所有呼，但中立韻對應的值為空串而非 `中立` */
    const 韻搭配呼 = reverseLookup(呼韻搭配);
    /** 依可搭配的等列出各母，包含邊緣搭配 */
    const 等母搭配 = {
        一二三四: [...'幫滂並明來見溪羣疑影曉匣'],
        二三: [...'知徹澄孃莊初崇生俟'],
        一三四: [...'精清從心邪'],
        三: [...'章昌常書船日云以'],
        一二四: [...'端透定泥'],
    };
    /** 依母取得可搭配的所有等，包含邊緣搭配 */
    const 母搭配等 = reverseLookup(等母搭配);

    const pattern描述 = new RegExp(`^([${所有.母.join('')}])([${所有.呼.join('')}]?)([${所有.等.join('')}]?)`
        + `([${所有.類.join('')}]?)([${所有.韻.join('')}])([${所有.聲.join('')}])$`, 'u');
    // for 音韻地位.屬於
    const 表達式屬性可取值 = {
        ...所有,
        音: [...'脣舌齒牙喉'],
        攝: [...'通江止遇蟹臻山效果假宕梗曾流深咸'],
        組: [...'幫端知精莊章見影'],
    };
    const 已知邊緣地位 = new Set([
        // 嚴格邊緣地位
        // 陽韻A類（無）
        // 端組類隔
        '定開四脂去', // 地
        '端開二庚上', // 打
        '端開二麻上', // 打（麻韻）
        '端開四麻平', // 爹
        '端開四麻上', // 嗲
        '定開二佳上', // 箉
        '端四尤平', // 丟
        // 咍韻脣音（無）
        // 匣母三等（無）
        // 羣邪俟母非三等（無）
        // ----
        // 非嚴格邊緣地位
        // 云母開口
        '云開三C之上', // 矣
        '云開三B仙平', // 焉
    ]);
    const _UNCHECKED = ['@UNCHECKED@'];
    /**
     * 《切韻》音系音韻地位。
     *
     * 可使用字串 (母, 呼, 等, 類, 韻, 聲) 初始化。
     *
     * | 音韻屬性 | 中文名稱 | 英文名稱 | 可能取值 |
     * | :- | :- | :- | :- |
     * | 母<br/>組 | 聲母<br/>組 | initial<br/>group | **幫**滂並明<br/>**端**透定泥<br/>來<br/>**知**徹澄孃<br/>**精**清從心邪<br/>**莊**初崇生俟<br/>**章**昌常書船<br/>日<br/>**見**溪羣疑<br/>**影**曉匣云<br/>以<br/>（粗體字為組，未涵蓋「來日以」） |
     * | 呼 | 呼 | rounding | 開口<br/>合口 |
     * | 等 | 等 | division | 一二三四 |
     * | 類 | 類 | type | ABC |
     * | 韻<br/>攝 | 韻母<br/>攝 | rime<br/>class | 通：東冬鍾<br/>江：江<br/>止：支脂之微<br/>遇：魚虞模<br/>蟹：齊祭泰佳皆夬灰咍廢<br/>臻：真臻文殷魂痕<br/>山：元寒刪山先仙<br/>效：蕭宵肴豪<br/>果：歌<br/>假：麻<br/>宕：陽唐<br/>梗：庚耕清青<br/>曾：蒸登<br/>流：尤侯幽<br/>深：侵<br/>咸：覃談鹽添咸銜嚴凡<br/>（冒號前為攝，後為對應的韻） |
     * | 聲 | 聲調 | tone | 平上去入<br/>仄<br/>舒 |
     *
     * 音韻地位六要素：母、呼、等、類、韻、聲。
     *
     * 「呼」和「類」可為 `null`，其餘四個屬性不可為 `null`。
     *
     * 當聲母為脣音，或韻母為「東冬鍾江模尤侯」（開合中立的韻）之一時，「呼」須為 `null`。
     * 在其他情況下，「呼」須取 `'開'` 或 `'合'`。
     *
     * 當聲母為鈍音（脣牙喉音，不含以母），且為三等韻時，「類」須取 `'A'`、`'B'`、`'C'` 之一。
     * 在其他情況下，「類」須為 `null`。
     *
     * 依切韻韻目，用殷韻不用欣韻；亦不設諄、桓、戈韻，分別併入真、寒、歌韻。
     *
     * 不支援異體字，請自行轉換：
     *
     * * 音 唇 → 脣
     * * 母 娘 → 孃
     * * 母 荘 → 莊
     * * 母 谿 → 溪
     * * 母 群 → 羣
     * * 韻 餚 → 肴
     * * 韻 眞 → 真
     */
    class 音韻地位 {
        /**
         * 聲母
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.母;
         * '幫'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.母;
         * '羣'
         * ```
         */
        母;
        /**
         * 呼
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.呼;
         * null
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.呼;
         * '開'
         * ```
         */
        呼;
        /**
         * 等
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.等;
         * '三'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.等;
         * '三'
         * ```
         */
        等;
        /**
         * 類
         * - AB 類為前元音，在脣牙喉音有最小對立，此情形亦稱「重紐」
         * - C 類為非前元音
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.類;
         * 'C'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.類;
         * 'A'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('章開三支平');
         * > 音韻地位.類;
         * null
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫四先平');
         * > 音韻地位.類;
         * null
         * ```
         */
        類;
        /**
         * 韻（舉平以賅上去入，唯祭、泰、夬、廢例外）
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.韻;
         * '凡'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.韻;
         * '支'
         * ```
         */
        韻;
        /**
         * 聲調
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.聲;
         * '入'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.聲;
         * '平'
         * ```
         */
        聲;
        /**
         * 初始化音韻地位物件。
         * @param 母 聲母：幫, 滂, 並, 明, …
         * @param 呼 呼：`null`, 開, 合
         * @param 等 等：一, 二, 三, 四
         * @param 類 類：`null`, A, B, C
         * @param 韻 韻母（平賅上去入）：東, 冬, 鍾, 江, …, 祭, 泰, 夬, 廢
         * @param 聲 聲調：平, 上, 去, 入
         * @param 邊緣地位種類 建立邊緣地位時，列明該地位的邊緣地位種類
         * @returns 六要素所描述的音韻地位
         * @throws 待建立之音韻地位會透過{@linkcode 驗證}檢驗音節合法性，不合法則拋出異常
         * @example
         * ```typescript
         * > new TshetUinh.音韻地位('幫', null, '三', 'C', '凡', '入');
         * 音韻地位<幫三C凡入>
         * > new TshetUinh.音韻地位('羣', '開', '三', 'A', '支', '平');
         * 音韻地位<羣開三A支平>
         * > new TshetUinh.音韻地位('章', '開', '三', null, '支', '平');
         * 音韻地位<章開三支平>
         * > new TshetUinh.音韻地位('幫', null, '四', null, '先', '平');
         * 音韻地位<幫四先平>
         * ```
         */
        constructor(母, 呼, 等, 類, 韻, 聲, 邊緣地位種類 = []) {
            音韻地位.驗證(母, 呼, 等, 類, 韻, 聲, 邊緣地位種類);
            this.母 = 母;
            this.呼 = 呼;
            this.等 = 等;
            this.類 = 類;
            this.韻 = 韻;
            this.聲 = 聲;
        }
        /**
         * 清濁（全清、次清、全濁、次濁）
         *
         * 曉母為全清，云以來日母為次濁。
         *
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.清濁;
         * '全清'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.清濁;
         * '全濁'
         * ```
         */
        get 清濁() {
            const { 母 } = this;
            return 母到清濁[母];
        }
        /**
         * 音（發音部位：脣、舌、齒、牙、喉）
         *
         * **注意**：
         *
         * * 不設半舌半齒音，來母歸舌音，日母歸齒音
         * * 以母不屬於影組，但屬於喉音
         *
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.音;
         * '脣'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.音;
         * '牙'
         * ```
         */
        get 音() {
            const { 母 } = this;
            return 母到音[母];
        }
        /**
         * 攝
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.攝;
         * '咸'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.攝;
         * '止'
         * ```
         */
        get 攝() {
            const { 韻 } = this;
            return 韻到攝[韻];
        }
        /**
         * 韻別（陰聲韻、陽聲韻、入聲韻）
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.韻別;
         * '入'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.韻別;
         * '陰'
         * ```
         */
        get 韻別() {
            const { 韻, 聲 } = this;
            return 陰聲韻.includes(韻) ? '陰' : 聲 === '入' ? '入' : '陽';
        }
        /**
         * 組
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.組;
         * '幫'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.組;
         * '見'
         * ```
         */
        get 組() {
            const { 母 } = this;
            return 母到組[母];
        }
        /**
         * 描述
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.描述;
         * '幫三C凡入'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.描述;
         * '羣開三A支平'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('章開三支平');
         * > 音韻地位.描述;
         * '章開三支平'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫四先平');
         * > 音韻地位.描述;
         * '幫四先平'
         * ```
         */
        get 描述() {
            const { 母, 呼, 等, 類, 韻, 聲 } = this;
            return 母 + (呼 ?? '') + 等 + (類 ?? '') + 韻 + 聲;
        }
        /**
         * 簡略描述。會省略可由「母」或由「韻」直接確定的「呼」「等」「類」。
         *
         * **注意**：此項尚未成為穩定功能，不要依賴其輸出值。
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.簡略描述;
         * '幫凡入'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.簡略描述;
         * '羣開A支平'
         * ```
         */
        get 簡略描述() {
            const { 母, 韻, 聲 } = this;
            let { 呼, 等, 類 } = this;
            if (類 && 母韻搭配類(母, 韻)[0] === 類) {
                類 = null;
            }
            if (呼 === '合' && 母 === '云') {
                呼 = null;
            }
            else if (呼 && 韻搭配呼[韻].length === 1) {
                呼 = null;
            }
            if (等 === '三' && [...'羣邪俟'].includes(母)) {
                等 = '';
            }
            else if (母搭配等[母].length === 1 || 韻搭配等[韻].length === 1) {
                等 = '';
            }
            return 母 + (呼 ?? '') + 等 + (類 ?? '') + 韻 + 聲;
        }
        /**
         * 表達式，可用於{@linkcode 屬於}函數
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.表達式;
         * '幫母 開合中立 三等 C類 凡韻 入聲'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.表達式;
         * '羣母 開口 三等 A類 支韻 平聲'
         * ```
         */
        get 表達式() {
            const { 母, 呼, 等, 類, 韻, 聲 } = this;
            const 呼字段 = 呼 ? `${呼}口 ` : '開合中立 ';
            const 類字段 = 類 ? `${類}類 ` : '不分類 ';
            return `${母}母 ${呼字段}${等}等 ${類字段}${韻}韻 ${聲}聲`;
        }
        /**
         * 三十六字母
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
         * > 音韻地位.字母;
         * '非'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('常開三清平');
         * > 音韻地位.字母;
         * '禪'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('俟開三之上');
         * > 音韻地位.字等;
         * '禪'
         * ```
         */
        get 字母() {
            const { 母, 等, 類 } = this;
            let index;
            if (等 === '三' && 類 === 'C' && (index = [...'幫滂並明'].indexOf(母)) !== -1) {
                return '非敷奉微'[index];
            }
            else if ((index = [...'莊初崇生俟章昌船書常'].indexOf(母)) !== -1) {
                return '照穿牀審禪'[index % 5];
            }
            else if (['云', '以'].includes(母)) {
                return '喻';
            }
            return 母;
        }
        /**
         * 韻圖等
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > 音韻地位.韻圖等;
         * '四'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('常開三清平');
         * > 音韻地位.韻圖等;
         * '三'
         * > 音韻地位 = TshetUinh.音韻地位.from描述('俟開三之上');
         * > 音韻地位.韻圖等;
         * '二'
         * ```
         */
        get 韻圖等() {
            const { 母, 等, 類 } = this;
            if ([...'莊初崇生俟'].includes(母)) {
                return '二';
            }
            else if (類 === 'A' || (等 === '三' && [...'精清從心邪以'].includes(母))) {
                return '四';
            }
            else {
                return 等;
            }
        }
        /**
         * 調整該音韻地位的屬性，會驗證調整後地位的合法性，回傳新的物件。
         *
         * **注意**：原物件不會被修改。
         *
         * @param 調整屬性 可為以下種類之一：
         * - 物件，其屬性可為六項基本屬性中的若干項，各屬性的值為欲修改成的值。
         *
         *   不含某屬性或某屬性值為 `undefined` 則表示不修改該屬性。
         *
         * - 字串，可寫出若干項屬性，以空白分隔各項。各屬性的寫法如下：
         *   - 母、等、韻、聲：如 `'見母'`、`'三等'`、`'元韻'`、`'平聲'` 等
         *   - 呼：`'開口'`、`'合口'`、`'開合中立'`
         *   - 類：`'A類'`、`'B類'`、`'C類'`、`'不分類'`
         * @param 邊緣地位種類 若調整後為邊緣地位，列明其種類
         * @returns 新的 `音韻地位`，其中會含有指定的修改值
         * @example
         * ```typescript
         * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C元上');
         * > 音韻地位.調整({ 聲: '平' }).描述
         * '幫三C元平'
         * > 音韻地位.調整('平聲').描述
         * '幫三C元平'
         * > 音韻地位.調整({ 母: '見', 呼: '合' }).描述
         * '見合三C元上'
         * > 音韻地位.調整('見母 合口').描述
         * '見合三C元上'
         * ```
         */
        調整(調整屬性, 邊緣地位種類 = []) {
            if (typeof 調整屬性 === 'string') {
                const 屬性object = {};
                const set = (屬性, 值) => {
                    assert(!(屬性 in 屬性object), () => `duplicated assignment of ${屬性}`);
                    屬性object[屬性] = 值;
                };
                for (const token of 調整屬性.trim().split(/\s+/u)) {
                    const match = /^(?<kv>開合中立|不分類)$|^(?<v>.)(?<k>[母口等類韻聲])$/u.exec(token);
                    assert(match !== null, () => `unrecognized expression: ${token}`);
                    const { kv, k, v } = match.groups;
                    if (kv) {
                        if (kv === '開合中立')
                            set('呼', null);
                        else if (kv === '不分類')
                            set('類', null);
                    }
                    else {
                        set(k.replace('口', '呼'), v);
                    }
                }
                調整屬性 = 屬性object;
            }
            const { 母 = this.母, 呼 = this.呼, 等 = this.等, 類 = this.類, 韻 = this.韻, 聲 = this.聲 } = 調整屬性;
            return new 音韻地位(母, 呼, 等, 類, 韻, 聲, 邊緣地位種類);
        }
        屬於(表達式, ...參數) {
            if (typeof 表達式 === 'string')
                表達式 = [表達式];
            /** 普通字串 token 求值 */
            const { 母, 呼, 類, 聲, 清濁, 韻別 } = this;
            const evalToken = (token) => {
                let match = null;
                if ((match = /^(陰|陽|入)聲韻$/.exec(token)))
                    return 韻別 === match[1];
                if (token === '仄聲')
                    return 聲 !== '平';
                if (token === '舒聲')
                    return 聲 !== '入';
                if ((match = /^(開|合)口$/.exec(token)))
                    return 呼 === match[1];
                if (/^開合中立$/.exec(token))
                    return 呼 === null;
                if (/^不分類$/.exec(token))
                    return 類 === null;
                if ((match = /^(清|濁)音$/.exec(token)))
                    return 清濁[1] === match[1];
                if ((match = /^[全次][清濁]$/.exec(token)))
                    return 清濁 === match[0];
                if (token === '鈍音')
                    return 鈍音母.includes(母);
                if (token === '銳音')
                    return !鈍音母.includes(母);
                if ((match = /^(.+?)([母等類韻音攝組聲])$/.exec(token))) {
                    const values = [...match[1]];
                    const key = match[2];
                    const possibleValues = 表達式屬性可取值[key];
                    const invalidValues = values.filter(i => !possibleValues.includes(i));
                    if (invalidValues.length) {
                        throw new Error(`unknown ${key}: ${invalidValues.join(', ')}`);
                    }
                    return values.includes(this[key]);
                }
                throw new Error(`unrecognized test condition: ${token}`);
            };
            const KEYWORDS = ['(', ')', 'not', 'and', 'or'];
            const PATTERNS = [/^\($/, /^\)$/, /^([!~非]|not)$/i, /^(&+|且|and)$/i, /^(\|+|或|or)$/i];
            const tokens = [];
            for (let i = 0; i < 表達式.length; i++) {
                for (const rawToken of 表達式[i].split(/(&+|\|+|[!~()])|\b(and|or|not)\b|\s+/i).filter(i => i)) {
                    const match = PATTERNS.findIndex(pat => pat.test(rawToken));
                    if (match !== -1) {
                        tokens.push([KEYWORDS[match], rawToken]);
                    }
                    else {
                        tokens.push([evalToken(rawToken), rawToken]);
                    }
                }
                if (i < 參數.length) {
                    const arg = LazyParameter.from(參數[i], this);
                    tokens.push([arg, String(arg)]);
                }
            }
            assert(tokens.length, 'empty expression');
            // 句法分析
            // 由於是 LL(1) 文法，可用遞迴下降法
            // 基本成分：元（boolean | LazyParameter）、非、且、或、'('、')'
            // 文法：
            // - 非項：非* ( 元 | 括號項 )
            // - 且項：非項 ( 且? 非項 )*
            // - 或項：且項 ( 或 且項 )*
            // - 括號項：'(' 或項 ')'
            let cursor = 0;
            const END = ['end', 'end of expression'];
            const peek = () => (cursor < tokens.length ? tokens[cursor] : END);
            const read = () => (cursor < tokens.length ? tokens[cursor++] : END);
            function parseOrExpr(required) {
                const firstAndExpr = parseAndExpr(required);
                if (!firstAndExpr) {
                    return null;
                }
                const orExpr = ['or', firstAndExpr];
                for (;;) {
                    // 或 且項 | END | else
                    const [token] = peek();
                    if (token === 'or') {
                        cursor++;
                        orExpr.push(parseAndExpr(true));
                    }
                    else {
                        return orExpr;
                    }
                }
            }
            function parseAndExpr(required) {
                const firstNotExpr = parseNotExpr(required);
                if (!firstNotExpr) {
                    return null;
                }
                const andExpr = ['and', firstNotExpr];
                for (;;) {
                    // 且? 非項 | END | else
                    const [token] = peek();
                    if (token === 'and') {
                        cursor++;
                        andExpr.push(parseNotExpr(true));
                    }
                    else {
                        const notExpr = parseNotExpr(false);
                        if (notExpr) {
                            andExpr.push(notExpr);
                        }
                        else {
                            return andExpr;
                        }
                    }
                }
            }
            function parseNotExpr(required) {
                // 非*
                let seenNotOperator = false;
                let negate = false;
                for (;;) {
                    const [token] = peek();
                    if (token === 'not') {
                        seenNotOperator = true;
                        negate = !negate;
                        cursor++;
                    }
                    else {
                        break;
                    }
                }
                let valExpr = [negate ? 'not' : 'value'];
                // 元 | 括號項 | else
                const [token, rawToken] = peek();
                if (typeof token === 'boolean' || token instanceof LazyParameter) {
                    valExpr.push(token);
                    cursor++;
                    return valExpr;
                }
                else if (token === '(') {
                    cursor++;
                    const parenExpr = parseOrExpr(true);
                    const [rightParen, rawRightParen] = read();
                    if (rightParen !== ')') {
                        throw new Error(`expect ')', got: ${rawRightParen}`);
                    }
                    if (negate) {
                        valExpr.push(parenExpr);
                    }
                    else {
                        valExpr = parenExpr;
                    }
                    return valExpr;
                }
                else if (seenNotOperator || required) {
                    const expected = seenNotOperator ? "operand or '('" : 'expression';
                    throw new Error(`expect ${expected}, got: ${rawToken}`);
                }
                else {
                    return null;
                }
            }
            const expr = parseOrExpr(true);
            const [token, rawToken] = read();
            if (token !== 'end') {
                throw new Error(`unexpected token: ${rawToken}`);
            }
            // 求值
            const evalExpr = (expr) => {
                const [op, ...args] = expr;
                switch (op) {
                    case 'value':
                        return evalOperand(args[0]);
                    case 'not':
                        return !evalOperand(args[0]);
                    case 'and':
                        return args.every(evalOperand);
                    case 'or':
                        return args.some(evalOperand);
                }
            };
            const evalOperand = (operand) => typeof operand === 'boolean' ? operand : operand instanceof LazyParameter ? operand.eval() : evalExpr(operand);
            return evalExpr(expr);
        }
        判斷(規則, throws = false, fallThrough = false) {
            const Exhaustion = Symbol('Exhaustion');
            function is規則列表(obj) {
                return Array.isArray(obj);
            }
            const loop = (所有規則) => {
                for (const 規則 of 所有規則) {
                    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- user-provided value may violate this
                    assert(Array.isArray(規則) && 規則.length === 2, '規則需符合格式');
                    let 表達式 = 規則[0];
                    const 結果 = 規則[1];
                    if (typeof 表達式 === 'function')
                        表達式 = 表達式();
                    if (typeof 表達式 === 'string' && 表達式 ? this.屬於(表達式) : 表達式 !== false) {
                        if (!is規則列表(結果))
                            return 結果;
                        const res = loop(結果);
                        if (res === Exhaustion && fallThrough)
                            continue;
                        return res;
                    }
                }
                return Exhaustion;
            };
            const res = loop(規則);
            if (res === Exhaustion) {
                if (throws === false)
                    return null;
                else
                    throw new Error(typeof throws === 'string' ? throws : '未涵蓋所有條件');
            }
            return res;
        }
        /**
         * 判斷當前音韻地位是否等於另一音韻地位。
         * @param other 另一音韻地位。
         * @returns 若相等，則回傳 `true`；否則回傳 `false`。
         * @example
         * ```typescript
         * > a = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > b = TshetUinh.音韻地位.from描述('羣開三A支平');
         * > a === b;
         * false
         * > a.等於(b);
         * true
         * ```
         */
        等於(other) {
            return this.描述 === other.描述;
        }
        /** 同 {@linkcode 描述} */
        toString() {
            return this.描述;
        }
        /** @ignore 用於 Object.prototype.toString */
        [Symbol.toStringTag] = '音韻地位';
        /** @ignore 僅用於 Node.js 呈現格式 */
        [Symbol.for('nodejs.util.inspect.custom')](...args) {
            const stylize = (...x) => args[1].stylize(...x);
            return `音韻地位<${stylize(this.描述, 'string')}>`;
        }
        /**
         * 驗證給定的音韻地位六要素是否合法。
         *
         * ### 基本取值
         *
         * 母必須為「幫滂並明端透定泥來知徹澄孃精清從心邪莊初崇生俟章昌常書船日見溪羣疑影曉匣云以」之一。
         *
         * 韻必須為「東冬鍾江支脂之微魚虞模齊祭泰佳皆夬灰咍廢真臻文殷元魂痕寒刪山先仙蕭宵肴豪歌麻陽唐庚耕清青蒸登尤侯幽侵覃談鹽添咸銜嚴凡」之一。
         *
         * 當聲母為脣音，或韻母為「東冬鍾江虞模尤幽」（開合中立的韻）時，呼須為 `null`。
         * 在其他情況下，呼須取「開」或「合」。
         *
         * 當聲母為脣牙喉音（不含以母），且為三等韻時，類須取 `A`、`B`、`C` 之一。
         * 在其他情況下，類須為 `null`。
         *
         * ### 搭配
         *
         * 等：
         * - 章組、云以日母：限三等
         * - 羣邪俟母：一般限三等
         * - 匣母：一般限非三等
         * - 端組：限非三等，一般限一四等
         * - 精組（邪母除外）：限一三四等
         * - 知莊組（俟母除外）：限二三等
         * - 此外等當須與韻搭配
         *
         * 呼：
         * - 脣音、或開合中立韻：限 `null`（開合中立）
         * - 云母：除效流深咸四攝外，限非開口
         * - 其餘情形：呼須取「開」或「合」
         *
         * 類：
         * - 限幫見影組三等，其餘情形均須取 `null`（不分類）
         * - 前元音韻（支脂祭真仙宵麻庚清幽侵）：須取 A 或 B，其中清韻限 A 類，庚韻限 B 類
         * - 其餘韻一般須取 C
         * - 蒸韻：須取 C 或 B
         * - 陽韻：限 C 類，但有取 A 類之罕見例外
         * - 云母：限非 A 類
         *
         * 韻：
         * - 凡韻：限脣音
         * - 嚴韻、之魚殷痕韻：限非脣音
         * - 臻韻：限莊組
         * - 真殷韻開口、清韻：限非莊組
         * - 庚韻非二等：銳音限莊組
         *
         * @param 母 聲母：幫, 滂, 並, 明, …
         * @param 呼 呼：`null`, 開, 合
         * @param 等 等：一, 二, 三, 四
         * @param 類 類：`null`, A, B, C
         * @param 韻 韻母（舉平以賅上去入）：東, 冬, 鍾, 江, …, 祭, 泰, 夬, 廢
         * @param 聲 聲調：平, 上, 去, 入
         * @param 邊緣地位種類 若為邊緣地位，列明其種類
         * @throws 若給定的音韻地位六要素不合法，則拋出異常
         */
        static 驗證(母, 呼, 等, 類, 韻, 聲, 邊緣地位種類 = []) {
            const reject = (msg) => {
                throw new Error(`invalid 音韻地位 <${母},${呼 ?? ''},${等},${類 ?? ''},${韻},${聲}>: ` + msg);
            };
            // 驗證取值
            for (const [屬性, 值, nullable] of [
                ['母', 母],
                ['呼', 呼, true],
                ['等', 等],
                ['類', 類, true],
                ['韻', 韻],
                ['聲', 聲],
            ]) {
                if (!((值 === null && !!nullable) || 所有[屬性].includes(值))) {
                    const suggestion = {
                        母: { 娘: '孃', 群: '羣' },
                        韻: { 眞: '真', 欣: '殷' },
                    }[屬性]?.[值];
                    reject(`unrecognized ${屬性}: ${值}` + (suggestion ? ` (did you mean: ${suggestion}?)` : ''));
                }
            }
            // 驗證搭配
            // 順序：搭配規則從基本到精細
            // 聲（僅韻-聲搭配）
            聲 === '入' && 陰聲韻.includes(韻) && reject(`unexpected ${韻}韻入聲`);
            // 等、呼、類（基本）
            // 母-等
            if (!母搭配等[母].includes(等)) {
                reject(`unexpected ${母}母${等}等`);
            }
            // 等-韻
            if (!韻搭配等[韻].includes(等) && !(等 === '四' && [...'端透定泥'].includes(母) && 韻搭配等[韻].includes('三'))) {
                reject(`unexpected ${韻}韻${等}等`);
            }
            // 母-呼（基本）、呼-韻
            if ([...'幫滂並明'].includes(母)) {
                呼 && reject('unexpected 呼 for 脣音');
            }
            else if (韻搭配呼[韻].length === 0) {
                呼 && reject('unexpected 呼 for 開合中立韻');
            }
            else if (韻搭配呼[韻].length > 1) {
                呼 ?? reject('missing 呼');
            }
            else {
                const 應搭配呼 = 韻搭配呼[韻][0];
                if (!呼) {
                    reject(`missing 呼 (should be ${應搭配呼})`);
                }
                else if (呼 !== 應搭配呼) {
                    reject(`unexpected ${韻}韻${呼}口`);
                }
            }
            // 母-類（基本）、等-類、類-韻（基本）
            if (等 !== '三') {
                類 && reject('unexpected 類 for 非三等');
            }
            else if (!鈍音母.includes(母)) {
                類 && reject('unexpected 類 for 銳音聲母');
            }
            else {
                const [典型搭配類, 搭配類] = 母韻搭配類(母, 韻);
                if (!類) {
                    const suggestion = 典型搭配類.length === 1 ? ` (should be ${典型搭配類}${典型搭配類 !== 搭配類 ? ' typically' : ''})` : '';
                    reject(`missing 類${suggestion}`);
                }
                else if (!搭配類.includes(類)) {
                    if (母 === '云' && 類 === 'A') {
                        reject(`unexpected 云母A類`);
                    }
                    reject(`unexpected ${韻}韻${類}類`);
                }
            }
            // 母-韻
            if ([...'幫滂並明'].includes(母)) {
                [...'之魚殷痕嚴'].includes(韻) && reject(`unexpected ${韻}韻脣音`);
            }
            else {
                韻 === '凡' && reject(`unexpected 凡韻非脣音`);
            }
            if ([...'莊初崇生俟'].includes(母)) {
                等 === '三' && 韻 === '清' && reject(`unexpected ${韻}韻莊組`);
                呼 === '開' && ['真', '殷'].includes(韻) && reject(`unexpected ${韻}韻開口莊組`);
            }
            else {
                韻 === '臻' && reject(`unexpected 臻韻非莊組`);
                韻 === '庚' && 等 !== '二' && !鈍音母.includes(母) && reject(`unexpected 庚韻${等}等${母}母`);
            }
            // 邊緣搭配
            // 為已知邊緣地位，或特別指定跳過檢查
            if (邊緣地位種類 === _UNCHECKED || 已知邊緣地位.has(母 + (呼 ?? '') + 等 + (類 ?? '') + 韻 + 聲)) {
                return;
            }
            const 邊緣地位指定集 = new Set(邊緣地位種類);
            assert(邊緣地位種類.length === 邊緣地位指定集.size, 'duplicates in 邊緣地位種類');
            const marginalTests = [
                ['陽韻A類', true, 韻 === '陽' && 類 === 'A', '陽韻A類'],
                [
                    '端組類隔',
                    true,
                    [...'端透定泥'].includes(母) && (等 === '二' || (等 === '四' && !韻搭配等[韻].includes('四'))),
                    `${韻}韻${等}等${母}母`,
                ],
                ['咍韻脣音', true, 韻 === '咍' && [...'幫滂並明'].includes(母), `咍韻脣音`],
                ['匣母三等', true, 母 === '匣' && 等 === '三', `匣母三等`],
                ['羣邪俟母非三等', true, 等 !== '三' && [...'羣邪俟'].includes(母), `${母}母${等}等`],
                ['云母開口', false, 母 === '云' && 呼 === '開' && ![...'宵幽侵鹽嚴'].includes(韻), '云母開口'],
            ];
            const knownKinds = marginalTests.map(([kind]) => kind);
            for (const kind of 邊緣地位種類) {
                if (!knownKinds.includes(kind)) {
                    throw new Error(`unknown type of marginal 音韻地位: ${kind}`);
                }
            }
            for (const [kind, isStrict, condition, errmsg] of marginalTests) {
                if (condition && !邊緣地位指定集.has(kind)) {
                    const suggestion = isStrict ? '' : ` (note: marginal 音韻地位, include '${kind}' in 邊緣地位種類 to allow)`;
                    reject(`unexpected ${errmsg}${suggestion}`);
                }
                else if (isStrict && !condition && 邊緣地位指定集.has(kind)) {
                    reject(`expect marginal 音韻地位: ${kind} (note: don't specify it in 邊緣地位種類 unless it describes this 音韻地位)`);
                }
            }
        }
        /**
         * 將音韻描述或簡略音韻描述轉換為音韻地位。
         * @param 音韻描述 音韻地位的描述
         * @param 簡略描述 為 `true` 則允許簡略描述，否則須為完整描述
         * @returns 給定的音韻描述或最簡描述對應的音韻地位
         * @example
         * ```typescript
         * > TshetUinh.音韻地位.from描述('幫三C凡入');
         * 音韻地位<幫三C凡入>
         *  > TshetUinh.音韻地位.from描述('幫凡入', true);
         * 音韻地位<幫三C凡入>
         * > TshetUinh.音韻地位.from描述('羣開三A支平');
         * 音韻地位<羣開三A支平>
         * ```
         */
        static from描述(音韻描述, 簡略描述 = false, 邊緣地位種類 = []) {
            const match = pattern描述.exec(音韻描述);
            if (!match) {
                throw new Error(`invalid 描述: ${音韻描述}`);
            }
            const 母 = match[1];
            let 呼 = match[2] || null;
            let 等 = match[3] || null;
            let 類 = match[4] || null;
            const 韻 = match[5];
            const 聲 = match[6];
            if (簡略描述) {
                if (!呼 && ![...'幫滂並明'].includes(母)) {
                    if (母 === '云' && 韻搭配呼[韻].length > 1) {
                        呼 = '合';
                    }
                    else {
                        const 可搭配呼 = 韻搭配呼[韻];
                        if (可搭配呼.length === 1) {
                            呼 = 可搭配呼[0];
                        }
                    }
                }
                if (!等) {
                    if (母搭配等[母] === '三' || [...'羣邪俟'].includes(母)) {
                        等 = '三';
                    }
                    else {
                        const 可搭配等 = 韻搭配等[韻];
                        if (可搭配等.length === 1) {
                            const 應搭配等 = 可搭配等[0];
                            if (應搭配等 === '三' && [...'端透定泥'].includes(母)) {
                                等 = '四';
                            }
                            else {
                                等 = 應搭配等;
                            }
                        }
                    }
                }
                if (!類 && 等 === '三' && 鈍音母.includes(母)) {
                    const [典型搭配類] = 母韻搭配類(母, 韻);
                    if (典型搭配類.length === 1) {
                        類 = 典型搭配類;
                    }
                }
            }
            // NOTE type assertion safe because the constructor checks it
            return new 音韻地位(母, 呼, 等, 類, 韻, 聲, 邊緣地位種類);
        }
    }
    /**
     * 取得給定條件下可搭配的類，分為「不含邊緣地位」與「含邊緣地位」兩種。
     * 用於 `音韻地位` 的 `.驗證`、`.from描述`、`.簡略描述`。
     */
    function 母韻搭配類(母, 韻) {
        let 搭配 = null;
        for (const [搭配類, 搭配韻] of [
            ['C', [...'東鍾之微魚虞廢殷元文歌尤嚴凡']],
            ['AB', [...'支脂祭真仙宵麻幽侵鹽']],
            ['A', [...'清']],
            ['B', [...'庚']],
            ['BC', [...'蒸']],
            ['CA', [...'陽']],
        ]) {
            if (搭配韻.includes(韻)) {
                搭配 = [搭配類 === 'CA' ? 'C' : 搭配類, 搭配類];
                break;
            }
        }
        if (搭配 === null) {
            throw new Error(`unknown 韻: ${韻}`);
        }
        if (母 === '云') {
            return 搭配.map(x => x.replace(/A/g, ''));
        }
        return 搭配;
    }
    /**
     * 惰性求值參數，用於 `音韻地位.屬於` 標籤模板形式
     */
    class LazyParameter {
        inner;
        地位;
        constructor(inner, 地位) {
            this.inner = inner;
            this.地位 = 地位;
        }
        static from(param, 地位) {
            switch (typeof param) {
                case 'string':
                    return 地位.屬於(param);
                case 'function':
                    return new LazyParameter(param, 地位);
                default:
                    return !!param;
            }
        }
        eval() {
            if (typeof this.inner === 'function') {
                this.inner = this.inner.call(undefined);
                if (typeof this.inner === 'string') {
                    this.inner = this.地位.屬於(this.inner);
                }
            }
            return (this.inner = !!this.inner);
        }
        toString() {
            return String(this.inner);
        }
    }

    const 編碼表 = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$_'];
    const 韻序表 = [
        ...'東＊冬鍾江支脂之微魚虞模齊祭泰佳皆夬灰咍廢真臻文殷元魂痕寒刪山先仙蕭宵肴豪歌＊麻＊陽唐庚＊耕清青蒸登尤侯幽侵覃談鹽添咸銜嚴凡',
    ];
    function decode音韻編碼raw(編碼) {
        assert(編碼.length === 3, () => `Invalid 編碼: ${JSON.stringify(編碼)}`);
        const [母序, 韻序, 呼類聲序] = [...編碼].map(ch => {
            const index = 編碼表.indexOf(ch);
            assert(index !== -1, () => `Invalid character in 編碼: ${JSON.stringify(ch)}`);
            return index;
        });
        assert(母序 < 所有.母.length, () => `Invalid 母序號: ${母序}`);
        const 母 = 所有.母[母序];
        assert(韻序 < 韻序表.length, () => `Invalid 韻序號: ${韻序}`);
        let 韻 = 韻序表[韻序];
        if (韻 === '＊') {
            韻 = 韻序表[韻序 - 1];
        }
        const 韻可搭配等 = 韻搭配等[韻];
        let 等 = 韻可搭配等[+(韻序表[韻序] === '＊')];
        if (等 === '三' && [...'端透定泥'].includes(母)) {
            等 = '四';
        }
        const 呼序 = 呼類聲序 >> 4;
        assert(呼序 <= 所有.呼.length, () => `Invalid 呼序號: ${呼序}`);
        const 呼 = 呼序 ? 所有.呼[呼序 - 1] : null;
        const 類序 = (呼類聲序 >> 2) & 0b11;
        assert(類序 <= 所有.類.length, () => `Invalid 類序號: ${類序}`);
        const 類 = 類序 ? 所有.類[類序 - 1] : null;
        const 聲序 = 呼類聲序 & 0b11;
        const 聲 = 所有.聲[聲序];
        return { 母, 呼, 等, 類, 韻, 聲 };
    }
    function decode音韻編碼unchecked(編碼) {
        return Object.assign(Object.create(音韻地位.prototype), decode音韻編碼raw(編碼));
    }

    /**
     * 將音韻地位編碼為壓縮格式串。音韻編碼與音韻地位之間存在一一映射關係。
     * @param 地位 待編碼的音韻地位
     * @returns 音韻地位對應的編碼
     * @example
     * ```typescript
     * > 音韻地位 = TshetUinh.音韻地位.from描述('幫三C凡入');
     * > TshetUinh.壓縮表示.encode音韻編碼(音韻地位);
     * 'A9P'
     * > 音韻地位 = TshetUinh.音韻地位.from描述('羣開三A支平');
     * > TshetUinh.壓縮表示.encode音韻編碼(音韻地位);
     * 'fFU'
     * ```
     */
    function encode音韻編碼(地位) {
        const { 母, 呼, 等, 類, 韻, 聲 } = 地位;
        const 母序 = 所有.母.indexOf(母);
        const 韻序 = 韻序表.indexOf(韻) + +([...'東歌麻庚'].includes(韻) && !['一', '二'].includes(等));
        // NOTE the value `-1` is expected when the argument is `null`
        const 呼序 = 所有.呼.indexOf(呼) + 1;
        const 類序 = 所有.類.indexOf(類) + 1;
        const 呼類聲序 = (呼序 << 4) | (類序 << 2) | 所有.聲.indexOf(聲);
        return 編碼表[母序] + 編碼表[韻序] + 編碼表[呼類聲序];
    }
    /**
     * 將音韻編碼解碼回音韻地位。
     * @param 編碼 音韻地位的編碼
     * @returns 給定的音韻編碼對應的音韻地位
     * @example
     * ```typescript
     * > TshetUinh.壓縮表示.decode音韻編碼('A9P');
     * 音韻地位<幫三C凡入>
     * > TshetUinh.壓縮表示.decode音韻編碼('fFU');
     * 音韻地位<羣開三A支平>
     * ```
     */
    function decode音韻編碼(編碼) {
        const { 母, 呼, 等, 類, 韻, 聲 } = decode音韻編碼raw(編碼);
        return new 音韻地位(母, 呼, 等, 類, 韻, 聲, _UNCHECKED);
    }

    var ____ = /*#__PURE__*/Object.freeze({
        __proto__: null,
        decode音韻編碼: decode音韻編碼,
        encode音韻編碼: encode音韻編碼
    });

    /******************************************************************************
    Copyright (c) Microsoft Corporation.

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
    REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
    INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
    LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
    OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
    PERFORMANCE OF THIS SOFTWARE.
    ***************************************************************************** */
    /* global Reflect, Promise, SuppressedError, Symbol, Iterator */


    function __esDecorate(ctor, descriptorIn, decorators, contextIn, initializers, extraInitializers) {
        function accept(f) { if (f !== void 0 && typeof f !== "function") throw new TypeError("Function expected"); return f; }
        var kind = contextIn.kind, key = kind === "getter" ? "get" : kind === "setter" ? "set" : "value";
        var target = !descriptorIn && ctor ? contextIn["static"] ? ctor : ctor.prototype : null;
        var descriptor = descriptorIn || (target ? Object.getOwnPropertyDescriptor(target, contextIn.name) : {});
        var _, done = false;
        for (var i = decorators.length - 1; i >= 0; i--) {
            var context = {};
            for (var p in contextIn) context[p] = p === "access" ? {} : contextIn[p];
            for (var p in contextIn.access) context.access[p] = contextIn.access[p];
            context.addInitializer = function (f) { if (done) throw new TypeError("Cannot add initializers after decoration has completed"); extraInitializers.push(accept(f || null)); };
            var result = (0, decorators[i])(kind === "accessor" ? { get: descriptor.get, set: descriptor.set } : descriptor[key], context);
            if (kind === "accessor") {
                if (result === void 0) continue;
                if (result === null || typeof result !== "object") throw new TypeError("Object expected");
                if (_ = accept(result.get)) descriptor.get = _;
                if (_ = accept(result.set)) descriptor.set = _;
                if (_ = accept(result.init)) initializers.unshift(_);
            }
            else if (_ = accept(result)) {
                if (kind === "field") initializers.unshift(_);
                else descriptor[key] = _;
            }
        }
        if (target) Object.defineProperty(target, contextIn.name, descriptor);
        done = true;
    }
    function __runInitializers(thisArg, initializers, value) {
        var useValue = arguments.length > 2;
        for (var i = 0; i < initializers.length; i++) {
            value = useValue ? initializers[i].call(thisArg, value) : initializers[i].call(thisArg);
        }
        return useValue ? value : void 0;
    }
    typeof SuppressedError === "function" ? SuppressedError : function (error, suppressed, message) {
        var e = new Error(message);
        return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
    };

    function memo(memoKey, areKeysEqual = Object.is) {
        // NOTE `_context` is for type checking
        return function (target, _context) {
            let cache = undefined;
            let cachedKey = undefined;
            let firstRun = true;
            return function (...args) {
                const key = memoKey(this);
                if (!firstRun && areKeysEqual(key, cachedKey)) {
                    return cache;
                }
                firstRun = false;
                cachedKey = key;
                cache = target.call(this, ...args);
                return cache;
            };
        };
    }
    /**
     * Mixin for {@linkcode 資料條目Common} and {@linkcode 上下文條目}.
     *
     * NOTE: Despite that 資料條目Common's API is a superset of 上下文條目's,
     * the former class is logically NOT a subtype of the latter, thus a mixin design for shared functionality is preferable.
     *
     * NOTE: We are not using the [subclass factory style mixin](https://www.typescriptlang.org/docs/handbook/mixins.html#how-does-a-mixin-work),
     * as it would make the code more convoluted than they need to be:
     * - This is only used internally, with controlled use cases, so simplicity (a single class with a flat prototype) is preferred
     *   - There are methods (like `expand釋義上下文`) that create instances of its own class, which makes this flatness more of a concern
     * - Classes with subclass mixins [have to be defined in a particular way](https://github.com/TypeStrong/typedoc/issues/2465) in order for
     *   the docs to be generated correctly
     */
    let Supports字頭詳情 = (() => {
        let _instanceExtraInitializers = [];
        let _get_字頭詳情_decorators;
        return class Supports字頭詳情 {
            static {
                const _metadata = typeof Symbol === "function" && Symbol.metadata ? Object.create(null) : void 0;
                _get_字頭詳情_decorators = [memo(obj => obj.字頭)];
                __esDecorate(this, null, _get_字頭詳情_decorators, { kind: "getter", name: "\u5B57\u982D\u8A73\u60C5", static: false, private: false, access: { has: obj => "\u5B57\u982D\u8A73\u60C5" in obj, get: obj => obj.字頭詳情 }, metadata: _metadata }, null, _instanceExtraInitializers);
                if (_metadata) Object.defineProperty(this, Symbol.metadata, { enumerable: true, configurable: true, writable: true, value: _metadata });
            }
            /**
             * 取得條目的字頭原貌及校正。
             *
             * @returns 格式為 `[原貌, ...校勘]`：
             * - 首項為原貌；若為應補字，則原貌為空串 `''`
             * - 校勘各項（通常沒有或僅一項）為含校勘符號的校正字，可用 `.slice(1, -1)` 取得當中的字；
             *   若為應刪字，則校勘部分僅含一項，為 `'｛｝'`
             *
             * 多次存取時，回傳值均為同一物件。
             *
             * @example
             * ```typescript
             * > let 條目 = TshetUinh.資料.query字頭('結');
             * [ { 字頭: '結', ... }]
             * > 條目[0].字頭詳情;
             * [ '結' ]
             *
             * > TshetUinh.資料.query字頭('嬹').find(({ 音韻地位 }) => 音韻地位.聲 === '平');
             * { 字頭: '［嬹］', ... }
             * > 條目.字頭詳情;
             * [ '', '［嬹］' ]
             *
             * > TshetUinh.資料.query字頭('𤜼');
             * [ { 字頭: '｛𤜼｝', ... }]
             * > 條目[0].字頭詳情;
             * [ '𤜼', '｛｝' ]
             *
             * > TshetUinh.資料.query字頭('𤿎').find({ 小韻號 } => 小韻號 === '141');
             * { 字頭: '𤿎〈𢻹〉', ... }
             * > 條目.字頭詳情;
             * [ '𤿎', '〈𢻹〉' ]
             * ```
             */
            get 字頭詳情() {
                return parse字頭詳情(this.字頭);
            }
            /**
             * 字頭原貌。若條目為應補字（原書底本所無），則為 `null`。
             * @see {@linkcode 字頭詳情}
             */
            get 字頭原貌() {
                return this.字頭詳情[0] || null;
            }
            /**
             * 字頭校正。若條目為應刪字，則為 `null`。
             * @see {@linkcode 字頭詳情}
             */
            get 字頭校正() {
                const 詳情 = this.字頭詳情;
                return 詳情.length === 1 ? 詳情[0] : 詳情[詳情.length - 1].slice(1, -1) || null;
            }
            constructor() {
                __runInitializers(this, _instanceExtraInitializers);
            }
        };
    })();
    function mixin字頭詳情(Class) {
        const { constructor, ...descriptors } = Object.getOwnPropertyDescriptors(Supports字頭詳情.prototype);
        Object.defineProperties(Class.prototype, descriptors);
    }
    /**
     * 各來源之 {@linkcode 資料!資料條目 | 資料條目 } 所共用的屬性
     *
     * 實際查詢所得條目亦會含有 `.來源` 屬性，可利用該屬性判斷型別。
     *
     * @see {@linkcode 切韻條目.來源}
     * @see {@linkcode 廣韻條目.來源}
     */
    let 資料條目Common = (() => {
        let _instanceExtraInitializers = [];
        let _get_小韻號詳情_decorators;
        let _get_小韻字號詳情_decorators;
        let _get_反切詳情_decorators;
        return class 資料條目Common {
            static {
                const _metadata = typeof Symbol === "function" && Symbol.metadata ? Object.create(null) : void 0;
                _get_小韻號詳情_decorators = [memo(x => x.小韻號)];
                _get_小韻字號詳情_decorators = [memo(x => x.小韻字號)];
                _get_反切詳情_decorators = [memo(obj => obj.反切)];
                __esDecorate(this, null, _get_小韻號詳情_decorators, { kind: "getter", name: "\u5C0F\u97FB\u865F\u8A73\u60C5", static: false, private: false, access: { has: obj => "\u5C0F\u97FB\u865F\u8A73\u60C5" in obj, get: obj => obj.小韻號詳情 }, metadata: _metadata }, null, _instanceExtraInitializers);
                __esDecorate(this, null, _get_小韻字號詳情_decorators, { kind: "getter", name: "\u5C0F\u97FB\u5B57\u865F\u8A73\u60C5", static: false, private: false, access: { has: obj => "\u5C0F\u97FB\u5B57\u865F\u8A73\u60C5" in obj, get: obj => obj.小韻字號詳情 }, metadata: _metadata }, null, _instanceExtraInitializers);
                __esDecorate(this, null, _get_反切詳情_decorators, { kind: "getter", name: "\u53CD\u5207\u8A73\u60C5", static: false, private: false, access: { has: obj => "\u53CD\u5207\u8A73\u60C5" in obj, get: obj => obj.反切詳情 }, metadata: _metadata }, null, _instanceExtraInitializers);
                if (_metadata) Object.defineProperty(this, Symbol.metadata, { enumerable: true, configurable: true, writable: true, value: _metadata });
            }
            音韻地位 = __runInitializers(this, _instanceExtraInitializers);
            /**
             * 字頭。
             *
             * 可能含有校勘標記，可用 {@linkcode 字頭詳情}、{@linkcode 字頭原貌}、{@linkcode 字頭校正} 取得原貌及校勘。
             */
            字頭;
            /** 資料中個別字頭的特別說明（如訛字、重出之類） */
            字頭說明;
            /**
             * 小韻號。
             *
             * 部分小韻含多個音韻地位，會依音韻地位拆分，並有細分編號（後綴 -a、-b 等），故為字串格式。
             * @see {@linkcode 廣韻.get小韻}
             */
            小韻號;
            /**
             * 小韻內字頭序號。
             *
             * 部分字頭為增字，字號形如 `<原書字序號>a<增序號>`，如 `1a1`，故為字串格式。
             */
            小韻字號;
            /** 原書韻目。注意與音韻地位不一定對應 */
            韻目;
            /**
             * 反切。若該小韻未用反切注音（如「音某字某聲」）則為 `null`（此時會給出{@linkcode 直音}）。
             *
             * 可能含有校勘標記，可用 {@linkcode 反切詳情}、{@linkcode 反切原貌}、{@linkcode 反切校正} 取得原貌及校勘。
             *
             * 注意有極少數反切的原本意圖用字或訛變過程不詳，其校勘中可能含有「？」（全形問號）。
             */
            反切;
            /** 直音。僅當小韻未給{@linkcode 反切}，以直音注音時有內容，否則為 `null` */
            直音;
            /**
             * 釋義。僅含該單字下的釋義，該單字無釋義（與後字共用釋義）時為 `null`。
             * @see {@linkcode 釋義上下文}
             */
            釋義;
            /** 釋義上下文。包含與該條目相關（如釋義為「上同」「並同」之類時）的若干條目的字頭釋義 */
            釋義上下文;
            /** @ignore */
            constructor(raw) {
                Object.assign(this, raw);
            }
            /**
             * 解析小韻號的組成部分：原書小韻號、細分號。
             *
             * 若為細分小韻，細分號為一個小寫字母（a、b、c 等），否則為空串。
             *
             * @returns 二元組，分別為原書小韻號、細分號。
             *
             * 多次存取時，回傳值均為同一物件。
             */
            get 小韻號詳情() {
                const { 小韻號 } = this;
                if (/[a-z]$/.test(小韻號)) {
                    return [Number(小韻號.slice(0, -1)), 小韻號.slice(-1)];
                }
                else {
                    return [Number(小韻號), ''];
                }
            }
            /** 原書小韻號。即 {@linkcode 小韻號} 去掉結尾字母（細分號） */
            get 原書小韻號() {
                return Number(this.小韻號.replace(/[a-z]$/, ''));
            }
            /**
             * 解析小韻字號的組成部分：原書字號、增字號。
             *
             * 若為增字，則增字號非零，否則為零。
             *
             * @returns 二元組，分別為原書字號、增字號。
             *
             * 多次存取時，回傳值均為同一物件。
             */
            get 小韻字號詳情() {
                const parts = this.小韻字號.split('a');
                if (parts.length === 1) {
                    parts.push('');
                }
                return parts.map(Number);
            }
            /**
             * 取得條目的反切原貌及校正。
             *
             * 注意有個別反切原本意圖用字或訛變過程不詳，故校勘中可能含有「？」（全形問號）。
             *
             * @returns 無反切時為 `null`，否則為兩項的列表，每項表示一個字的原貌及校勘，亦為列表，形如 `[原貌, ...校勘]`：
             * - 首項為原貌；若原書底本中為脫字，則為空串
             * - 其後各項（通常為沒有或僅一項，若分多步改換/訛誤，則為多項）為含校勘標記的校正字；
             *   含校勘標記是為了指明用字變動的性質（同音切替換/近音切替換/訛字），可用 `.slice(1, -1)` 取得其中的字
             *
             * @example
             * ```typescript
             * > let 條目 = TshetUinh.資料.query字頭('淺').find(({ 音韻地位 }) => 音韻地位.聲 === '上');
             * { 字頭: '淺', 反切: '士〈七〉演', ... }
             * > 條目.反切詳情;
             * [ [ '士', '〈七〉' ], [ '演' ] ]
             *
             * > 條目 = TshetUinh.資料.query字頭('豆');
             * [ { 字頭: '豆', 反切: '［徒］候', ... }]
             * > 條目[0].反切詳情;
             * [ [ '', '［徒］' ], [ '候' ] ]
             *
             * > 條目 = TshetUinh.資料.query字頭('鷕');
             * [ { 字頭: '鷕', 反切: '以沼｟小｠〈水〉', ... }]
             * > 條目[0].反切詳情;
             * [ [ '以' ], [ '沼', '｟小｠', '〈水〉' ] ]
             *
             * > 條目 = TshetUinh.資料.query字頭('䅥').find(({ 音韻地位 }) => 音韻地位.等 === '三');
             * { 字頭: '䅥', 反切: '居列〖？〗', ... }
             * > 條目.反切詳情;
             * [ [ '居' ], [ '列', '〖？〗' ] ]
             * ```
             */
            get 反切詳情() {
                return this.反切 ? parse反切詳情(this.反切) : null;
            }
            /**
             * @see {@linkcode 反切詳情}
             */
            get 反切原貌() {
                return this.反切?.replace(/［.］|〈.〉|（.）|〘.〙|〖.〗|｟.｠|｛|｝/ug, '') ?? null;
            }
            /**
             * 反切校正。注意有個別反切原本意圖用字或訛變過程不詳，故可能含有「？」（全形問號）。
             * @see {@linkcode 反切詳情}
             * @example
             * ```typescript
             * > let 條目 = TshetUinh.資料.query字頭('淺').find(({ 音韻地位 }) => 音韻地位.聲 === '上');
             * { 字頭: '淺', 反切: '士〈七〉演', ... }
             * > 條目.反切校正;
             * '七演'
             *
             * > 條目 = TshetUinh.資料.query字頭('䅥').find(({ 音韻地位 }) => 音韻地位.等 === '三');
             * { 字頭: '䅥', 反切: '居列〖？〗', ... }
             * > 條目.反切校正;
             * '居？'
             *
             * > 條目 = TshetUinh.資料.query字頭('𤜼');
             * [ { 字頭: '｛𤜼｝', 反切: '崇〈？〉玄〈？〉', ... }]
             * > 條目[0].反切校正;
             * '？？'
             * ```
             */
            get 反切校正() {
                return this.反切詳情?.map(chs => (chs.length === 1 ? chs[0] : chs[chs.length - 1].slice(1, -1))).join('') ?? null;
            }
            /**
             * 將每項 {@linkcode 釋義上下文} 均展開成完整的 {@linkcode 資料!資料條目 | 資料條目}。
             *
             * 若無釋義上下文，則回傳的列表僅包含一項，為該條目自身。
             */
            expand釋義上下文() {
                function 資料條目withCloned釋義上下文(...[raw]) {
                    const res = new 資料條目Common(raw);
                    if (res.釋義上下文) {
                        res.釋義上下文 = res.釋義上下文.map(x => new 上下文條目(x));
                    }
                    return res;
                }
                if (!this.釋義上下文) {
                    return [資料條目withCloned釋義上下文(this)];
                }
                return this.釋義上下文.map(x => 資料條目withCloned釋義上下文({ ...this, ...x }));
            }
        };
    })();
    mixin字頭詳情(資料條目Common);
    // XXX This is for better presentation in REPLs, and may be subject to change.
    Object.defineProperty(資料條目Common, 'name', { value: '條目' });
    /**
     * 用於 {@linkcode 資料條目Common.釋義上下文 | 釋義上下文} 的條目。僅含必要的欄位，其餘欄位可參照其所在的主條目。
     *
     * 可利用所在主條目的 {@linkcode 資料條目Common.expand釋義上下文 | expand釋義上下文} 轉換為完整條目。
     *
     * @see {@linkcode 資料條目Common}
     */
    class 上下文條目 {
        字頭;
        字頭說明;
        小韻字號;
        釋義;
        /** @ignore */
        constructor(raw) {
            Object.assign(this, raw);
        }
    }
    mixin字頭詳情(上下文條目);
    /* eslint-enable @typescript-eslint/no-unsafe-declaration-merging, @typescript-eslint/no-empty-object-type */
    function parse反切詳情(反切) {
        // NOTE 目前資料中反切無 IDS 字，故可直接用 `...` 折分單字
        return parse詳情([...反切]);
    }
    function parse字頭詳情(字頭) {
        // NOTE 目前資料中字頭有 IDS 字，但必定為單字
        return parse詳情(字頭.split(/([［］｛｝〈〉])/).filter(x => x))[0];
    }
    // NOTE 該版本僅適用於反切詳情與字頭詳情（校訂標註皆為單字），若以後支援正文校訂標註，須重寫
    function parse詳情(chars) {
        const result = [];
        let i = 0;
        while (i < chars.length) {
            const ch = chars[i];
            switch (ch) {
                case '［':
                    result.push(['', chars.slice(i, i + 3).join('')]);
                    i += 3;
                    break;
                case '｛':
                    result.push([chars[i + 1], '｛｝']);
                    i += 3;
                    break;
                case '〈':
                case '（':
                case '〘':
                case '〖':
                case '｟':
                    result[result.length - 1].push(chars.slice(i, i + 3).join(''));
                    i += 3;
                    break;
                default:
                    result.push([ch]);
                    i += 1;
            }
        }
        return result;
    }
    function 條目from內部條目(內部條目) {
        const { 來源, 音韻編碼, 釋義上下文, ...rest } = 內部條目;
        return new 資料條目Common({
            來源,
            音韻地位: decode音韻編碼unchecked(音韻編碼),
            ...rest,
            釋義上下文: 釋義上下文 === null ? null : 釋義上下文.map(x => new 上下文條目(x)),
        });
    }

    var raw資料 = `\
#東
EAA德紅;東:春方也說文曰動也从日在木中亦東風菜廣州記云陸地生莖赤和肉作羹味如酪香似蘭吳都賦云莫則東風扶留又姓舜七友有東不訾又漢複姓十三氏左傳魯鄉東門襄仲後因氏焉齊有大夫東郭偃又有東宮得臣晉有東關嬖五神仙傳有廣陵人東陵聖母適杜氏齊景公時有隱居東陵者乃以爲氏世本宋大夫東鄉爲人賈執英賢傳云今高密有東鄉姓宋有員外郎東陽無疑撰齊諧記七卷昔有東閭子甞富貴後乞於道云吾爲相六年未薦一士夏禹之後東樓公封于杞後以爲氏莊子東野稷漢有平原東方朔曹瞞傳有南陽太守東里昆何氏姓苑有東萊氏德紅切十七|菄:+東風菜義見上注俗加艹|鶇:鶇鵍鳥名美形出廣雅亦作𪂝|䍶:獸名山海經曰秦戲山有獸狀如羊一角一目目在耳後其名曰䍶又音陳音棟|𠍀:儱𠍀儜劣皃出字諟|倲:+上同|𩜍:地理志云東郡館名|𢘐:古文見道經|涷:瀧涷沾漬說文曰水出發鳩山入於河又都貢切|蝀:螮蝀虹也又音董|凍:凍凌又都貢切|鯟:魚名似鯉|𢔅:行皃|崠:崠如山名|埬:上埬地名|𧓕:蛞𧓕科斗蟲也案爾雅曰科斗活東郭璞云蝦蟆子也字俗從䖵|䰤:醜皃
GAA徒紅;同:齊也共也輩也合也律歷有六同亦州春秋時晉夷吾獻其西河地於秦七國時屬魏秦并天下爲內史之地漢武更名馮翊又有九龍泉泉有九源同爲一流因以名之又羌複姓有同蹄氏望在勃海徒紅切四十五|仝:古文出道書|童:童獨也言童子未有室家也又姓出東莞漢有琅邪內史童仲玉|僮:僮僕又頑也癡也又姓漢有交阯刺史僮尹出風俗通|銅:金之一品|桐:木名月令曰清明之日桐始華又桐廬縣在睦州亦姓有桐君藥錄兩卷|峒:崆峒山名|硐:磨也|𦨴:𦨴船|𧱁:獸似豕出泰山|筒:竹筒又竹名射筒吳都賦曰其竹則桂箭射筒|瞳:目瞳|㼧:㼧瓦|𤭁:+上同|罿:車上網又音衝|犝:犝牛無角|筩:竹筩|潼:水名出廣漢郡亦關名又通衝二音|曈:曈曨日欲明也又他孔切|洞:洪洞縣名在晉州北又徒弄切|侗:楊子法言云倥侗顓蒙|橦:木名花可爲布出字書又鍾幢二音|烔:熱氣烔烔出字林|䴀:鸏䴀水鳥黃喙喙長尺餘南人以爲酒器出劉欣期交州記|挏:引也漢官名有挏馬又音動|酮:馬酪又音動|鮦:爾雅云鰹大鮦又直冢直柳二切|㼿:井甓一云甃也|𦏆:無角羊|𦍻:+上同|眮:目眶又徒摠切|蕫:草名又多動切|穜:穜稑先種後熟謂之穜後種先熟謂之稑又音重|衕:通街也|𩍅:靫具飾也|𢈉:地下應聲|䆚:通䆚也|哃:哃𠹔大言|𢏕:弓飾|絧:布名|𨚯:鄉名|𨝯:地名又姓|𪔝〈𪔜〉:鼓聲|𩦶:黑虎|𪒿:黑皃
JBA陟弓;中:平也成也宜也堪也任也和也半也又姓漢少府鄉中京出風俗通又漢複姓有七氏漢有諫議大夫中行彪晉中行偃之後虞有五英之樂掌中英者因以爲氏古有隱者中梁子漢書藝文志有室中周著書十篇賈執英賢傳云路中大夫之後以路中爲氏張晏云姓路爲中大夫何氏姓苑有中壘氏中野氏陟弓切又陟仲切四|衷:善也正也適也中也又衷衣褻衣也|忠:無私也敬也直也厚也亦州名本漢臨江縣屬巴郡後魏置臨州貞觀爲忠州|𦬕:草名又音沖
LBA直弓;蟲:爾雅曰有足曰蟲無足曰豸又姓漢功臣表有曲成侯蟲達直弓切七|沖:和也深也|种:稚也或作沖亦姓後漢司徒河南种暠|盅:器虛也又敕中切|爞:爾雅云爞爞炎炎熏也|𦬕:草名又音中|翀:直上飛也
XBA職戎;終:極也窮也竟也又姓漢有濟南終軍又漢複姓二氏東觀漢記有終利恭何氏姓苑云今下邳人也左傳殷人七族有終葵氏職戎切十五|眾:又之仲切|潀:小水入大水又徂紅在冬二切|𣧩:歿也|螽:螽斯蟲也|𧑄:+上同|鼨:豹文鼠也|蔠:蔠葵蘩露也|柊:木名又齊人謂椎爲柊楑也|𩅧:小雨|䶱:字書云龜名也|鴤:鳥名|䈺:篋䈺戎人呼之|泈:水名在襄陽|䝦:獸如豹
KBA敕中;忡:憂也敕中切三|浺:浺瀜水平遠之皃又音蟲|盅:器虛也又音蟲
UBA鋤（鉏）弓;崇:高也敬也就也聚也又姓鋤弓切四|崈:+上同|㓽:鍤屬|𩞉:饞𩞉貪食也出古今字音
QBA息弓;嵩:山高也又山名又姓史記有嵩極玄子或作崧息弓切九|崧:+上同|𪀚:似鷹而小能捕雀也|娀:有娀氏女簡狄帝嚳次妃吞乙卵生契|菘:菜名|硹:地名在遼|㣝:姓也|𧊕:蟲名|䯷:細毛
cBA如融;戎:戎狄亦助也說文作𢦦兵也又姓漢宣帝戎婕妤生中山哀王竟如融切九|𢦦:+上同|茙:茙葵蜀葵也又虜姓後魏書官氏志云南方有茙眷氏改爲茙氏也|㭜:木名|駥:馬八尺也|𥬪:小竹可爲矢|𠈋:𠈋人身有三角也|狨:細布|絨:+上同
dBM居戎;弓:弓矢釋名曰弓穹也張之穹穹然也其末曰簫又謂之弭以骨爲之滑弭弭也中央田弣弣撫也人所撫持也簫弣之聞曰淵淵宛也言曲宛然也世本曰黃帝臣揮作弓墨子曰羿作弓孫子曰倕作弓又姓魯大夫叔弓之後居戎切六|躳:身也親也又姓出姓苑|躬:+上同|㴦:縣名在酒泉|宮:白虎通曰黃帝作宮室以避寒暑宮之言中也世本曰禹作宮亦官名漢書曰少府官有守宮令主御筆墨紙封書泥也又姓左傳虞有宮之奇|匑:謹敬之皃又音穹
lBA以戎;融:和也朗也說文曰炊气上出也又姓世本云古天子祝融之後以戎切四|融:+上同|肜:祭名又敕林切|瀜:沖瀜大水皃
kBM羽弓;雄:雄雌也亦姓舜友有雄陶羽弓切二|熊:獸名似豕魏略曰大秦之國出玄熊亦姓左傳賢者熊宜僚又漢複姓左傳楚大夫熊率且比
DBM莫中;瞢:目不明莫中切六|夢:說文曰不明也又武仲切|鄸:邑名在曹郡|懜:慙也國語云君使臣懜|𦫰:𦫰𦫰醜皃|𧲎:獸似豕目在耳出崐崘
eBM去宮;穹:高也去宮切七|𢞏:憂也|焪:乾也|芎:芎藭香草根曰芎藭苗曰蘪蕪似蛇牀|𦵡:+上同|匑:謹敬之皃|𥳎:𥳎籠也又去龍切
fBM渠弓;窮:窮極也又窮奇獸名聞人鬬乃助不直者渠弓切三|藭:芎藭|𥨪:羿所封國
CBM房戎;馮:馮翊郡名又姓畢公高之伸食采於馮城因而命氏出杜陵乃長樂房戎切七|堸:蟲室|汎:浮也又孚劒切|芃:草盛也又音蓬|𨝭:姬姓之國|渢:弘大聲也|梵:木得風皃又防泛切
ABM方戎;風:教也佚也告也聲也河圖曰風者天地之使元命包曰陰陽怒而爲風方戎切七|飌:+古文|楓:木名子可爲式爾雅云楓有脂而香孫炎云欇欇生江上有奇生枝高三四尺生毛一名楓子天旱以泥泥之即雨山海經曰黃帝殺蚩尤棄其桎梏變爲楓木脂入地千年化爲虎魄|猦:猦母狀如猿逢人則叩頭小打便死得風還活出異物志|偑:地名|檒:檒梵聲也|𧆉:竹名出南海
BBM敷空;豐:大也多也茂也盛也又酒器豆屬又姓鄭公子豐之後敷空切八|酆:邑名亦姓左傳有狄相酆舒|蘴:蕪菁苗也|灃:水名在咸陽|寷:大屋|麷:煑麥|㒥:偓㒥仙人|㠦:山名
YBA昌終;充:美也塞也行也滿也昌終切七|珫:珫耳玉名詩傳云充耳謂之瑱字俗從玉|茺:茺蔚草也|㤝:心動|䘪:䘪襌衣也|𪎽:黃色又音統|㳘:水聲
IBA力中;隆:盛也豐也大也力中切六|癃:病也亦作𤸇|𪔳:鼓聲俗作𪔴|窿:穹隆天勢俗加穴|霳:豐隆雷師俗加雨|㚅:多㚅礼天
eAA苦紅;空:空虛書曰伯禹作司空又漢複姓有空桐空相二氏苦紅切十四|箜:箜篌樂器釋名云師延所作靡靡之音出桑閒濮上續漢書云靈帝胡服作箜篌也|崆:崆峒|椌:器物朴也又丘江切|硿:硿青色石也|䅝:稻稈|悾:悾悾信也愨也|埪:土埪龕也|倥:倥侗|涳:涳濛小雨又口江切|鵼:怪鳥出字統|𦱇:𦱇心草也|𢃐:衣袂|𧌆:蟬脫𧌆皮
dAA古紅;公:通也父也正也共也官也三公論道又公者無私也從八從厶厶音私八背意也背厶爲公也亦姓漢有主爵都尉公儉又漢複姓八十五氏左傳魯有公冉務人公斂陽公何藐公父歜公賓庚公思展公鉏極公甲叔子費宰公山弗櫌公甲叔公巫召伯衛有公文要戰國策齊威王時有左執法公旗蕃左傳齊悼子公旗之後左傳季武子庶子公沮後以爲氏孟子有公行子著書左傳晉成公以卿之庶子爲公行大夫其後氏焉孔子家語魯有公冶長又公索氏將祭而亡其牲者魯有公慎氏出婬妻又有公罔之裘揚觶者孔子弟子齊人公晳哀陳人公良儒公西赤公祖句兹公肩定漢書藝文志有公檮子著書又有公勝生著書濟南公玉帶上明堂圖功臣表有公師壹晉穆公子成師之後又有公扈滿意後漢有零陵太守公仇稱晉穆公子仇之後又弘農令北海公沙穆山陽公堵恭魏志有公夏浩晉書有征虜長史太山公正羣成都王帳下督公帥蕃本姓公師避晉景帝諱改爲公帥氏前趙錄有大中大夫公帥式子夏門人齊人公羊高作春秋傳列女傳有公乘之姒墨子魯有公輸班衛大夫公叔文子史記有魯相公儀休孔子門人公休哀又有公祈哀禮記魯大夫公明儀何氏姓苑云今高平人衛大夫公南文子魯有公荊皎衛大夫公子荊之後魯大夫公襄昭魯襄公太子野之後魯大夫公伯寮何氏姓苑云彭城人趙平陵太守公休勝魯士官公爲珍魯昭公子公爲之後楚大夫公朱高宋公子子朱之後公車氏秦公子伯車之後淮南子有公牛哀病七日化爲虎齊公子牛之後呂氏春秋有邴大夫公息忘孟子稱公都子有學業楚公子田食采於都邑後氏焉公劉氏后稷公劉之後古今人表有公房皮楚公子房之後郭泰別傳有渤海公族進階衛大夫有公上王世本有魯大夫公之文晉蒲邑大夫公佗世鄉秦公子金之後有公金氏齊公子成之後有公牽氏何氏姓苑云公右氏今琅邪人公左氏今高平人又有公言公孟公獻公留公石公旅公仲等氏又左傳衛有庾公差以善射聞祭公謀父出自姜姓申公子福楚申公巫臣之後衛有尹公佗楚大夫逢公子仲楚白公勝之後有白公氏文字志云魏文侯時有古樂人竇公氏獻古文樂書一篇秦有博士黃公庇古今人表神農之後有公幹仕齊爲大夫其後氏焉世本有大公叔穎又有公紀氏衛有大夫左公子洩右公子職漢四晧有園公先生尚書僕射東郡成公敞古紅切十三|功:功績也說文曰以勞定國曰功又漢複姓何氏姓苑云漢營陵令成功恢禹治水告成功後爲氏俗作㓛|工:官也又工巧也|疘:文字集略云脫疘下部病也|蚣:蜈蚣蟲|玒:王名又音江|釭:車釭說文曰車轂中鐵也又古雙切|魟:䱑魟江蟲形似蟹可食又音烘|攻:攻擊|㓚:銍穫也|愩:憒也|碽:擊聲|篢:篢笠方言
DAA莫紅;蒙:覆也奄也爾雅釋草曰蒙王女也莫紅切二十七|冡:說文覆也|濛:涳濛細雨|𩦺:驢子曰𩦺|艨:艨艟戰船又武用切|䑃:大皃|矇:矇瞽|饛:盛食滿皃|䰒:馬垂鬣也|檬:似槐華黃|𨢊:麴生衣皃|䴿:+上同|𨣘:+亦上同|鸏:鸏䴀鳥也|幪:覆也蓋衣也又幪縠|罞:爾雅曰麋罟謂之罞|𢄐:說文云蓋衣也又莫弄切|髳:爾雅釋詁曰覭髳茀離也|蠓:蠛蠓似蚊又莫孔切|𦿏:草可爲帚|雺:天氣下地不應曰雺又莫侯切|霿:-|霚:+並上同|朦:朦朧月下|䀄:器滿|懜:心悶闇也|靀:小雨
IAA盧紅;籠:西京雜記曰漢制天子以象牙爲火籠盧紅切又力董切二十七|豅:大谷|㰍:說文云房室之疏也亦作櫳|朧:朦朧|𡃡:大聲|龓:馬龓頭|䪊:+上同|瀧:瀧涷沾漬說文曰雨瀧瀧也|聾:耳聾左傳云不聽五聲之和曰聾釋名曰聾籠也如在蒙籠之內不可察也|𨏠:軸頭|礱:磨也|䆍:禾病|𪚗:+上同|嚨:喉嚨|蘢:蘢古草名又音龍|櫳:檻也養獸所也|𤮨:字書云築土𤮨穀|巃:巃嵸山皃嵸祖紅切又音竉摠|襱:襱裙|𧙥:+上同|瓏:玲瓏玉聲|曨:日欲出也|鸗:鳥名|𩟭:𩟭餅|蠪:蠪蛭如狐九尾虎爪音如小兒食人一名䗁蠪又爾雅曰蠪朾螘郭璞云赤駁蚍蜉|㟅:崆㟅山皃|屸:山形
jAA戶公;洪:大也亦姓共工氏之後本姓共氏後改爲洪氏戶公切二十二|鉷:弩牙|訌:潰也詩曰蟊賊內訌|紅:色也又姓|虹:螮蝀也又古巷切|仜:身肥大也|鴻:詩傳云大曰鴻小曰鴈又姓左傳衛大夫鴻聊魋|葒:水草一曰蘢古詩云隰有游龍傳曰龍即紅草也字或從艹|葓:+上同|谼:大壑又谼谷寺在相州|䉺:陳赤米也|烘:字林云燎也又呼紅切|洚:說文曰水不遵道一曰下也又戶冬下江二切|渱:潰渱水沸湧也|𨹁:從𨹁山名在雲南|魟:魟白魚又音烘|䧆:坑也|䪦:大聲|𦏺:飛聲|䫹:大風|䂫:石聲|𨾊:鳥肥大𨾊唯然
PAA徂紅;叢:聚也徂紅切五|藂:+俗|䕺:草䕺生皃|潀:水會也|𥵫:籠𥵫取魚器俗
hAA烏紅;翁:老稱也亦鳥頸毛又姓漢書貨殖傳有翁伯販脂而傾縣邑烏紅切八|螉:蠮螉蟲名細𦝫𧒒也|䱵:魚名|蓊:蓊鬱草木盛皃又烏桶切|䈵:竹盛皃|䩺:吳人靴靿曰䩺|㮬:水㮬子果名出南州|𩔚:頸毛也
OAA倉紅;悤:速也倉紅切十五|忩:+俗|蔥:葷菜|樬:尖頭擔也|䡯:轞車載囚|聰:聞也明也察也聽也殷仲堪父患耳聰聞牀下蟻動謂之牛鬬出晉書|𦇎:色青黃又細絹|璁:石似玉也|驄:馬青白雜色|蟌:蜻蜓淮南子曰蝦蟆爲鶉水蠆爲蟌|囪:竈突|𨣼:𨣼𨢊濁酒|鏓:大鑿平木器|熜:熅也又子孔切|𢊕:屋階中會又子孔切
FAA他紅;通:達也三禮圖曰通天冠一名高山冠上之所服也亦州名本漢宕渠縣內有地萬餘頃因名爲萬州後魏以萬州居四達之路改爲通州又姓出姓苑他紅切九|蓪:蓪草藥名中有小孔通氣|侗:大也|恫:痛也|痌:+上同|曈:曈曨欲明之皃|俑:俑偶人又音勇|𧳆:獸名似豕出泰山又音同|𨀜:走皃
NAA子紅;葼:木細枝也子紅切二十一|鬷:釜屬又姓左傳鄭大夫鬷明|嵕:九嵕山名|猣:犬生三子|豵:豕生三子|鯼:石首魚名|椶:椶櫚一名蒲葵|騣:馬鬣|𩮰:+上同|䗥:螉䗥蟲名|嵸:巃嵸又作孔切|艐:書傳云三艐國名說文云船著沙不行也|蝬:三蝬蛤屬出臨海異物志|堫:種也|𥓻:石也|翪:聳翅上下皃|緵:縷也又作弄切|㚇:飛而斂足又子貢切|㣭:數也|稯:禾束|鬉:毛亂
CAA薄紅;蓬:草名亦州名周割巴州之伏虞郡於此置蓬州因蓬山而名之薄紅切十|𥭗:車軬|篷:織竹夾箬覆舟也|髼:髼䯳髮亂皃|蜂:蟲名出蒼頡篇又音峯|芃:芃芃草盛皃又音馮|𧚋:爾雅曰困衱𧚋亦作袶又音降|韸:鼓聲|䮾:充塞皃又音龍瀧|𩖛:風皃又步留切
iAA呼東;烘:火皃呼東切又音紅六|叿:叿叿市人聲|魟:河魚似鼈|谾:谷空皃出字林|𩐠:𩐠䪦大聲|𩗄:大風
gAA五東;㟅:崆㟅山皃五東切又魚江切一
QAA蘇公;𣞷:小籠蘇公切又先孔切三|𢤄:惺𢤄了慧人也|㬝:白皃出聲譜
#冬
ECA都宗;冬:四時之末尸子曰冬爲信北方爲冬冬終也又姓前燕慕容皝左司馬冬壽都宗切七|𠔙:+古文|苳:草名|鴤:鴤鳥好入水食似鳧形小|笗:竹名|𩂓:雨皃|𧲴:獸如豹有角
GCA徒冬;彤:赤也丹飾也亦姓彤伯爲成王宗伯徒冬切二十二|疼:痛也|佟:姓也北燕錄有遼東佟萬以文章知名|炵:火盛皃又他冬切|䳋:鳥名䳋渠狀如山雞黑身赤足出山海經也|鼕:鼓聲|𢥞:𢥞𢥞憂也出楚詞|𢾮:擊空聲|爞:旱熱|㤏:惶也|痋:動病|䂈:剌矛|鉵:大鉏|𧹝:赤色|𩦶:黑虎|浵:水名亦水皃|䶱:龜名又音終|𠩁:楚云深屋|鉖:鈞鉖|𨜳:古國名|㠽:戎云幡也|赨:赤蟲
PCA藏宗;賨:戎稅說文曰南蠻賦也藏宗切十一|琮:說文云琮瑞玉大八寸似車釭周禮曰以黃琮禮地|悰:慮也一曰樂也|潀:小水入大水也又徂紅職戎二切|淙:水聲又士江切|慒:謀也又似由切|鬃:高髻又士江切|㼻:甖屬又士江切|孮:爲族盛孮鄉|誴:謀誴樂也|𢃏:帛𢃏又布名
HCA奴冬;農:田農也說文作農耕也亦官名漢書曰治粟內史秦官也景帝更名大司農又姓風俗通云神農之後又羌複姓有蘇農氏奴冬切十二|䢉:+上同|辳:+古文|𨑋:+籀文|𩟊:䭢𩟊強食䭢女耕切|噥:多言不中|𩅽:露多|憹:㦀憹悅也|㺜:多毛犬也又乃刀切|儂:我也|𧗕:說文曰腫血也|膿:+上同
dCA古冬;攻:治也作也擊也伐也古冬切二|釭:燈也又音江
jCA戶冬;䃔:䃔䃧石落聲戶冬切四|洚:說文曰水不遵道一曰下也孟子曰洚水警子|㗢:歌也又胡宋徒送二切|𩘎:大風
ICA力冬;䃧:力冬切三|䥢〈𪔢〉:鼓聲|𣫣:聲也
NCA作冬;宗:眾也本也尊也亦官名漢書宗正秦官也掌親屬亦姓周鄉宗伯之後出南陽又漢複姓二氏前漢有宗伯鳳南燕錄有宗正謙善卜相作冬切二|倧:上古神人
QCA私宗;鬆:髼鬆髮亂皃私宗切三|䯳:+上同
FCA他冬;炵:火色他冬切一
#鍾
XDA職容;鍾:當也酒器也又量名左傳曰釜十則鍾亦姓出潁川又漢複姓有鍾離氏世本云與秦同祖其後因封爲姓職容切十八|鐘:樂器也呂氏春秋云黃帝命伶倫鑄寸二器世本曰垂作鐘|蚣:䘀螽蟲|忪:心動皃|䇗:長節竹也|蹱:躘蹱小兒行皃|彸:征彸行皃|衳:小褌也|伀:志及眾也|橦:字㨾云本音同今借爲木橦字|籦:籠籦竹名廣志云可爲笛|妐:夫之兄也|㕬:眾口也|𧢸:舉角也|炂:熱化也|𦬘:草名|𨳗:門外開𨳗|鈆:鐵鈆
IDA力鍾;龍:通也和也寵也鱗蟲之長也易曰雲從龍又姓舜納言龍之後力鍾切九|𪚝:圭爲龍文|躘:躘蹱|鸗:鳥名|驡:野馬|𪚠:巫也|籠:𥳎籠竹車軬亦籦籠竹又力東力董二切|𦪽:小船上安蓋者|蘢:蘢古草
aDA書容;舂:世本曰雍父作舂呂氏春秋曰赤冀作舂書容切六|𧐍:蜙蝑俗呼𧐍𧑓|摏:撞也|蹖:蹋也|𪄻:𪇆𪄻鳥名|憃:愚也
RDA祥容;松:木名玄中記曰松脂淪入地千歲爲茯苓亦州名舜竄三苗於三危河關之西南羌是也後魏末始統其城改置州焉祥容切四|㮤:+古文|淞〈凇〉:凍落皃又先恭切|訟:爭獄又徐用切
YDA尺容;𧘂:當也向也突也說文曰通道也尺容切十一|衝:+上同|罿:網也又音童|憧:憧憧往來皃|䡴:陷陣車|艟:艨艟戰船|潼:河潼又音同|褈:褈褣衣也|𠟍:剌也|𠝤:+同上|䂌:短矛也
lDA餘封;容:盛也儀也受也爾雅曰容謂之防郭璞云形如今牀頭小曲屏風唱䠶者所以自防隱司馬法云軍容不入國國容不入軍是也又州名又姓入凱仲容之後禮記有徐大夫容居餘封切三十五|溶:水皃又音勇|滽:水名出宜蘇山|庸:常也用也功也和也次也易也又姓漢有庸光|𦤘:+古文|𧴄:獸似牛領有肉也|㺎:-|𤛑:+並上同|墉:城也垣也|鎔:鎔鑄|鏞:大鐘|銿:+上同說文與鐘同|鄘:國名|傭:傭賃又丑凶切|𪅟:𪅟𪆫鳥名似鴨雞足也|㼸:甖也|𤮇:+同上|鱅:魚名又音慵|蓉:芙蓉|䗤:𧌁䗤色如黃蛇有羽|傛:傛華縣也又漢書婦官有傛華|褣:𧝎褣|搈:不安|瑢:瑽瑢佩玉行也|䈶:䈶䇯又矢|嵱:山名在容州山下有鬼市|頌:形頌又似用切|㝐:㝐盛也說文云古文容|䡆:車行皃|㟾:㟾山在建州|𨲟:餝𨲟|𪃾:𪃾鸀|槦:㮧槦木中箭笴|㣑:重影一曰形㣑|𢧳:𢧳戣兵器
ADM府容;封:大也國也厚也爵也亦姓望出渤海本姜姓炎帝之後封鉅爲黃帝師又望出河南後魏官氏志云是賁氏後改爲封氏府容切五|𡉚:+古文|犎:野牛|葑:菜名詩云采葑采菲|崶:山名一名龍門山在封州大魚上化爲龍上不得點額流血水謂丹色也
iDM許容;胷:膺也亦作匈𦙄許容切十|凶:凶禍|𣧑:+古文|銎:懼也又斤斧柄孔又曲恭切|洶:水勢也|恟:懼也|𧧗:訟也|兇:惡也|訩:眾語|匈:匈奴
gDM魚容;顒:仰也爾雅云顒顒邛邛君之德也說文云大頭也魚容切四|𩤛:+上同見廣蒼|鰅:魚名說文曰皮有文出樂浪又音隅|喁:噞喁
hDM於容;邕:說文曰四方有水自邕成池者是也於容切十六|雍:和也與邕略同又雍奴縣名在幽州水經云四方有水曰雍不流曰奴亦姓左傳有雍糾又於用切|噰:鳥聲|嗈:+上同|郺:郺𨑊多皃|澭:水名在宋|灉:+上同爾雅曰水自河出爲灉|癰:癰癤|罋:汲器|廱:辟廱天子教宮|饔:熟食|壅:塞又音擁|雝:爾雅曰䳭鴒雝渠|𪄉:+上同|㻾:玉器|𧴗:獸似猨也
MDA女容;醲:厚酒女容切八|𨑊:郺𨑊|濃:厚也|襛:襛華又衣厚皃又而容切|穠:花木厚又而容切|檂:木名|𪒬:𪒒𪒬|𨲳:多也
LDA直容;重:複也曡也直容切又直勇直用二切六|穜:先種晚熟曰穜|緟:說文云增益也|褈:複也|䳯:䳯𪄹鳥名|蝩:蠶晚生者
PDA疾容;從:就也又姓漢有將軍從公何氏姓苑云今東莞人疾容切又即容七恭秦用三切三|从:+古文說文曰相聽也|𩀰:方言云南楚人謂雞
KDA丑凶;蹱:躘蹱丑凶切七|傭:均也直也又音容|𦟛:+上同|𨙔:馬不行也|䝑:土精如㹠在地下也|𨤩:地名又直容切|𪒒:深穴中𪒒黑也
CDM符容;逢:值也迎也符容切八|縫:紩又音俸|漨:水名|䩼:鼓聲|𥎌:𥎌𥎂矛也|夆:掣曳也又敷恭切|𥛝:大黃負山神能動天地氣昔孔甲遇之|捀:說文曰奉也又符用切
BDM敷容;峯:山峯也敷容切十六|鋒:劒刃鋒也|丰:丰茸美好說文本作𡴀草盛𡴀也從生上下達也|𡴀:+上同|𢓱:使也|妦:好也|蠭:說文曰螫人飛蟲也孝經援神契曰蠭䘍垂芒爲其毒在後|蜂:+上同|𧒒:+古文|蘴:菜名又音豐|桻:木上|㷭:㷭火夜曰㷭晝曰燧|烽:+上同|莑:草牙始生出音譜|仹:仙人|㸼:㸼牛
NDA即容;縱:縱橫也即容切又子用切九|𣯨:毾㲪也|蹤:蹤跡|䡮:車跡|樅:木名又七恭切|磫:磫𥗫礪石|豵:豕生三子|熧:火行穴中|𧺣:急行也又此從切
cDA而容;茸:草生皃而容切十|䩸:毳飾|髶〈𩮙〉:髮多亂皃|䇯:竹頭有文|襛:華皃又厚衣皃又女容切|穠:花木厚也又女容切|搑:擣也|𥎂:𥍮𥎂矛也|榵:木名似檀|穁:禾梋
fDM渠容;蛩:蛩蛩巨虛獸也說文云一曰秦謂蟬蛻曰蛩渠容切十六|邛:勞也病也又臨邛縣亦邛僰又姓列仙傳有周封史邛疏|舼:舼船|𦨰:+上同|筇:竹名可爲杖張鶱至大宛得之|輁:輁軸所以支棺也又音拱|𦭭:蓂莢實也|𥳎:𥳎籠|䂬:水㠀石也又居勇切|蛬:蟋蟀又音拱|𠌖:𠌖倯可憎之皃|𩬰:𩬰鬆髮亂也|桏:柜柳|䅃:稰也又巨壠切|𤤶:𤤶佩|𩢽:獸如馬而青一走千里也
ZDA蜀庸;鱅:魚名似牛音如豕蜀庸切又音庸三|慵:嬾也|𩌨:通俗文云牽乾也
dDM九容;恭:恭敬也說文本作𢙄肅也又姓晉太子申生號恭君其後氏焉出國語九容切陸以恭蜙樅等入冬韻非也十|龔:姓也漢有龔遂|供:奉也具也設也給也進也又居用切|珙:璧也又音拱|䢼:邑名出異苑又亭名出晉書|共:共城縣在衛州又渠用切|𤱨:㽤也|廾:竦手也說文本居竦切|髸:髸䯳|䳍:鳥似雉鳴自呼
QDA息恭;蜙:蜙蝑蟲名息恭切六|淞:水名在吳又音松|凇:凍落之皃|鬆:髮亂皃亦作䯳|倯:倯恭怯皃|𢔋:小行恐皃
ODA七恭;樅:木名松葉栢身七恭切又音蹤十二|鏦:短矛又音窻|從:從容又疾容秦用二切|暰:光也張景陽七命云怒目電暰是也|䗥:螉䗥小蜂生牛馬皮中也|瑽:瑽瑢佩玉行皃|摐:打也又音窻|䐫:肥病|𥡬:治禾𥡬移|𧺣:急行也又音蹤|鬆:髮亂又息恭切|𨑪:𨑪遷
eDM曲恭;銎:斤斧受柄處也曲恭切又許容切二|𥳎:𥳎籠
#江
dEA古雙;江:江海書有九江尋陽記云烏江蚌江烏白江嘉靡江畎江沔江𥐙江提江菌江亦姓出陳留本顓頊玄孫伯益之後爵封於江陵爲楚所滅後以國爲氏古雙切十一|扛:舉鼎說文云扛橫關對舉也秦武王與孟說扛龍文之鼎脫臏而死|杠:旌旗飾一曰牀前橫木|茳:茳蘺香草|釭:燈又音工|矼:石矼石橋也爾雅曰石杠謂之徛字俗從石|豇:豇豆蔓生白色|肛:胮肛脹大又許江切|玒:玉名又音工|𧢸:舉角|䜫:䜫谷在南郡
DEA莫江;厖:厚也大也莫江切十四|駹:黑馬白面|狵:犬多毛亦作尨|尨:+上同|浝:水名|哤:語雜亂曰哤|牻:牛白黑雜|娏:女神名|䵨:陰私事也|㟌:五帋山名在蜀|蛖:蛖螻螻蛄類|𥆙:目不明|痝:病困|𠈵:不媚
MEA女江;𦗳:耳中聲也女江切八|𣰊:髮多|涳:姓出纂文又音羫|噥:噥嗔語出字林|𩟊:強食|鬞:亂髮|䁸:目不明|𪆯:鴻𪆯
TEA楚江;囪:說文曰在牆曰牖在屋曰囪楚江切九|窻:說文作窗通孔也釋名曰窻聰也於內見外之聰明也|牕:+上同|窓:+俗|䎫:種也|堫:+上同|摐:打鐘鼓也|鏦:短矛也|𥎋:+上同
AEA博江;邦:國也又姓出何氏姓苑博江切四|𤰫:+古文|梆:木名|垹:土精如手在地中食之無病
jEA下江;栙:降䉶帆未張下江切八|䜶:䜶䝄胡豆|降:降伏又古巷切|缸:甖缸|缻〈瓨〉:+上同|洚:說文曰水不遵道一曰下也又古巷切|夅:服也|跭:跭𨇯豎立也
BEA匹江;胮:胮脹匹江切又音龐五|𤵸:+上同|𩐨:鼓聲|𪔔:+上同|𪐿:黑皃
IEA呂江;瀧:南人名湍亦州在嶺南呂江切又音雙二|䮾:充塞之皃
VEA所江;雙:偶也兩隻也又姓出姓苑後魏有將軍雙仕洛所江切七|艭:舽艭船名|䉶:帆也|𢥠:懼也左傳云駟氏𢥠|䝄:豆也|瀧:水名在郴州界|𨇯:跭𨇯立也
CEA薄江;龐:姓也出南安南陽二望本周文王子畢公高後封於龐因氏焉魏有龐涓薄江切五|逄:姓也出北海左傳齊有逄丑父|胮:胮肛脹大皃|𩐨:鼓聲|舽:舽舡船名
iEA許江;肛:許江切四|啌:啌瞋語出聲譜|谾:空谷皃|舡:舽舡船皃名
hEA握江;胦:胦肛不伏人握江切一
eEA苦江;腔:羊腔也苦江切十二|𤟄:+上同|羫:+古文|控:打也又苦貢切|椌:椌楬|悾:信也愨也又音空|跫:蹋地聲|涳:直流|崆:崆㟅山皃又音空|𩩝:𩪘𩩝尻骨|㾤:喉中病|㼹:㼹甎𤮇也
LEA宅江;幢:旛幢釋名曰幢幢也其皃幢幢然也宅江切六|撞:撞突也學記曰善待問者如撞鐘撞擊也|橦:木名又音鍾童|𣃘:旌旗杠皃出說文又丑善切|噇:喫皃|𩪘:𩪘𩩝尻骨
KEA丑江;憃:愚也丑江切又丑龍切又抽用切五|䚎:視不明也一曰直視又丑巷切|𥡟:黍𥡟不實也|䄝:祠不敬也|𧜧:短敝衣也
JEA都江;樁:橛也都江切二|𣻛:深水立𣻛
gEA五江;㟅:五江切一
UEA士江;淙:水流皃士江切又才宗切四|鬃:髻高皃|㼻:甖也出方言|𩞐:饞𩞐愛食
#支
XFQ章移;支:支度也支持也亦姓何氏姓苑云琅邪人後趙錄有司空支雄又漢複姓莊子有支離益善屠龍章移切二十九|𥾣:縴𥾣挽船繩也|只:專辝又之爾切|汥:水都名|㲍:㲔㲍者輕毛皃|巵:酒器|梔:梔子木實可染黃|枝:枝柯又漢複姓左傳楚大夫枝如子弓|衹:適也又巨支切|㽻:疾也|衼:衹衼尼法衣也衹音歧|肢:肢體|胑:-|𨈛:+並上同|禔:福也又是支切|馶:馬強|氏:月氏國名又閼氏匈奴皇后也又精是二音|疻:毁傷|㩼:多也又音寘|鳷:鳥名漢武帝造鳷鵲觀在雲陽甘泉宮外|䧴:+上同|觶:本音寘今作奉觶字|榰:爾雅曰榰柱也謂相榰柱也|㯄:玉篇云木盛|𪂅:土精如鴈一足黃色毁之殺人|𧌔:蟲名似蜥蜴能吞人|眵:目汁凝尺支切|䡋:䡋軝長轂|𩍲:皮鞁
lFQ弋支;移:遷也遺也延也徙也易也說文曰禾相倚移也又官曹公府不相臨敬則爲移書箋表之類也亦姓風俗通云漢有弘農太守移良弋支切三十二|䄬:+上同|迻:說文遷也|𠩗:說文歠也|杝:木名|鉹:方言云涼州呼甑又音侈|袲:宋地名又音侈|箷:衣架|𥠥:上同又榻前几|㥴:忯㥴不憂事|詑:詑詑自得皃又淺意也|簃:樓閣邊小屋又音池|䔟:萎䔟草|熪:燫熪火不絕皃|扅:扊扅戶扃|衪:衣袖|暆:東暆縣在樂浪|迆:逶迆又移爾切|𤝻:獸名似犬尾白目喙赤出則大兵|栘:扶栘木名又成兮切|歋:歋𢋅手相弄人亦作擨又以遮切|酏:酒也又羊氏切|匜:杯匜似桸可以注水又羊氏切|拸:加也|謻:埤蒼云冰室門名|𠗺:+上同|蛇:蜲蛇莊子所謂紫衣而朱冠又蛇丘縣名又神遮切|虵:+俗|螔:爾雅曰蚹蠃螔蝓注謂即蝸牛也|𠐀:𠐀𢋅|𣣢:笑𣣢|䬁:小旋風咸陽有之小䬁於地也
kFo薳支;爲:爾雅曰作造爲也說文曰母猴也又姓風俗通云漢有南郡太守爲昆薳支切又王僞切六|為:+俗|潙:水名在新陽|䧦:阪名在鄭又王詭切|鄬:地名|𩻟:大魚又許爲切
dFo居爲;嬀:水名亦州春秋時屬燕秦爲上谷郡漢爲潘縣武德初置北燕州貞觀改爲嬀州因木爲名又姓文士傳有嬀覽居爲切二|潙:水名又音爲
iFo許爲;𪎮:說文曰旌旗所以指𪎮也亦作麾許爲切六|麾:+上同|噅:口不言正|撝:說文曰裂也易曰撝謙注謂指撝皆謙也|𩻟:大魚又音爲|䧦:鄭地
hFo於爲;逶:逶迆於爲切十一|𣨙:枯死|萎:蔫也|㮃:田器|覣:好視|蜲:蜲蛇|痿:痹濕病也|倭:順皃|委:委委佗佗美也|䴧:鹿肉|蟡:涸水精一身兩頭似蛇以名呼之可取魚鼈
DFI靡爲;糜:糜粥靡爲切九|縻:繫也又縻爵易作靡|㸏:㸏爛|𪎕:散也|蘼:薔蘼虋冬也又世彼切|䊳:䊳碎|𪎭:𪎭穄別名|𦗕:乘輿金耳|醿:酴醿酒也
iFk許規;隓:毀也說文曰敗城𨸏曰隓許規切九|墮:+上同|隳:+俗|眭:眭盱健皃又息爲切盱音吁|觿:角錐童子佩之說文曰觿角銳耑可以解結也又戶圭切|睢:仰目也|䜐:相毀之言|鑴:大鍾又戶圭切|蘳:華黃也又果實也
LFg直垂;鬌:髮落直垂切又大果切三|錘:八銖又馳僞切|甀:甖也
ZFg是爲;𡍮:幾也疆也說文曰遠邊也是爲切十|垂:+上同|陲:邊也說文危也|倕:重也黃帝時巧人名倕|𦈼:小口甖也|𨿠:鴟鳥|圌:山名在吳都又市緣切|篅:盛榖圓𥫱|𥳙:+上同|𠃀:草木華葉縣
IFg力爲;羸:瘦也力爲切二|𡰠:膝病
YFg昌垂;吹:吹噓昌垂切又尺僞切三|炊:炊爨|䶴:習管古文作龡又尺僞切
BFI敷羈;鈹:大針也又劒如刀裝者敷羈切十二|帔:又芳髮切|鮍:魚鮍|披:又作翍開也分也散也|𤱍:耕也|耚:+上同|狓:狓猖皃出新字林|翍:羽張之皃|旇:旗靡|秛:禾租|𤿎:器破而未離又皮美切|㱟:開肉又匹靡切
AFI彼爲;陂:書傳云澤障曰陂彼爲切十一|詖:辯辝又音祕|碑:釋名曰本葬時所設臣子追述君父之功美以書其上|羆:爾雅曰羆如熊黃白文孝經援神契曰赤羆見則姦宄自遠也|𥀍:+古文|𨰟:玉篇云耜屬也|𤜑:牛名又音皮|𨧦:鋸鉏也|𥶓:竹名|襬:關東人呼裙也|藣:草名又彼義切
RFg旬爲;隨:從也順也又姓風俗通云隨侯之後漢有博土隨何後漢有扶風隨蕃旬爲切三|隋:國名本作隨左傳曰漢東之國隨爲大漢初爲縣後魏爲郡又改爲州隋文帝去辵|𥶻:𥶻籠
eFo去爲;虧:缺也俗作𧇾去爲切一
eFk去隨;闚:小視去隨切二|窺:+上同
fFY渠羈;奇:異也說文作奇又虜複姓後魏書奇斤氏後改爲奇氏渠羈切又居宜切十|琦:玉名|騎:說文曰跨馬也又其寄切|鵸:鵸䳜鳥似烏三首六尾自爲牝牡善笑䳜音余出山海經|弜:強也又其丈切|鬾:小兒鬼|碕:曲岸又巨支切|𢺷:木別生也|㩽:+上同又橫首枝皃|錡:釜屬又魚綺切
fFU巨支;祇:地祇神也巨支切二十五|示:+上同見周禮本又時至切|衹:衹衼尼法衣|岐:山名亦州春秋及戰國時爲秦都漢爲右扶風後魏置雍城鎮又改爲岐州因山而名又姓黃帝時有岐伯|歧:歧路|𨙸:邑名在扶風|馶:勁皃|疧:病也詩云俾我疧兮|蚑:蚑蚑蟲行皃又長蚑蠨蛸別名出崔豹古今注|忯:爾雅云忯忯惕惕愛也|䞚:說文曰緣大木也一曰行皃|翄:翄翄飛皃|𢻚:弓硬皃|軝:說文曰長轂之軝以朱約之詩曰約軝錯衡|𩉬:+上同|芪:藥草說文曰芪母也|汥:說文曰水都也又音支|跂:行皃又音企|䲬:雞又云鴈|蚔:蟲也|䉻:赤米|𦭲:繰絲鉤緒|伎:舒散又音技|𨱜:長𨱜國名髮長於身|𠁭:參差也
iFY許羈;犧:犧牲書傳曰色純曰犧許羈切十八|羲:姓風俗通云堯鄉羲仲之後|焁:焁欨貪者欲食皃|桸:枸也|巇:巇嶮|羛:地名在魏|戲:於戲歎辝又姓虙戲氏之後又喜義切|𤃪:水名在新豐|曦:日光|𢹍:擊也|𧕆:蠡名|䚙:角匕又火元切|䖒:古陶器也|㺣:獸名又曰豕也|𣤴:吹嚱口聲|𢨛:相笑之皃|㚀:毁也|隵:+上同
eFY去奇;㩻:不正也去奇切十一|觭:角一俯一仰也|踦:腳跛又腒綺切|㱦:死也說文棄也俗語謂死曰大㱦|崎:崎嶇|𦖊:一隻|碕:石橋|𤘌:虎牙|㥓:𢜩㥓儉意|䗁:長腳鼅鼄|攲:宗廟宥座之器說文又居宜切持去也
gFY魚羈;宜:說文本作𡧗所安也俗作宜亦姓出姓苑魚羈切十一|宐:+上同|𠣨:-|㝖:+並古文|儀:儀容又義也正也亦州名本漢涅縣地秦爲上黨郡武德爲遼州又爲箕州今爲儀州亦姓左傳徐大夫儀楚|𥫃:+上同|䣡:地名在徐|䴊:鵕䴊神鳥|轙:車上環轡所貫也又音蟻|涯:水畔也又五佳切|崖:崖岸又五佳切
CFI符羈;皮:皮膚也釋名曰皮被也被覆體也亦姓出下邳符羈切六|疲:勞也乏也|郫:郫縣名在蜀|罷:倦也亦止也又音矲|㯅:木下交支皃又符支切|犤:下小牛也
ZFQ是支;提:羣飛皃是支切又弟泥切十二|𦑡:+上同|㖷:鳥鳴|匙:匕也|䈕:說文曰簧屬|堤:堤封頃畝漢書作提顏師古曰提封者大舉其封疆也提音題|禔:福也亦安也喜也又音支|𦳚:𦳚母即知母草出字林|忯:愛也|姼:姼母也又尺氏切|眂:眂眂役目|𣏚:碓衡
cFQ汝移;兒:嬰兒又虜姓官氏志云賀兒氏後改爲兒氏汝移切四|𠒆:+上同|唲:曲從皃楚詞云喔咿嚅唲|婼:前漢西域傳有婼羌
IFQ呂支;離:近曰離遠曰別說文曰離黃倉庚鳴則蠶生今用鸝爲鸝黃借離爲離別也又姓孟軻門人有離婁呂支切三十七|籬:笊籬又爾雅曰樊藩也郭璞云謂藩籬也|醨:酒薄|罹:心憂|璃:琉璃|酈:魯地名又音歷|𣀷:陳也又力米切|驪:馬深黑色又姓驪戎國之後|𪖂:𪖂𪕭小鼠相銜行也|樆:山梨|鸝:鸝黃|鵹:+上同|𪅆:+上同又𪂈𪅆自爲牝牡|縭:婦人香纓|褵:玉篇云衣帶也|蘺:江蘺蘪蕪別名|䕻:草木附地生也|麗:東夷國名又盧計切|离:明也又卦名案易本作離又丑知切|䍦:接䍦白帽|㰚:柴㰚也|蠡:匈奴傳有谷蠡也谷音鹿|䅻:長沙人謂禾二把爲䅻|孋:孋姬本亦作驪|漓:水滲入地|灕:淋灕秋雨也|𧕯:蚰蜒別名|㷰:帷中火也又丑知切|𧕮:螹𧕮蟲名|攡:太玄經云張也|黐:黏也又丑知切|矖:矖瞜也|穲:穲穲黍稷行列|𢟢:多端又思之也|𢥗:+上同|謧:弄言|劙:分破也
PFQ疾移;疵:黑病疾移切八|骴:殘骨又音自|玼:玉病又七禮切|茈:𦽏茈草|𣐑:無𣐑木一名棆|胔:人子腸名|飺:嫌食皃|鴜:𪇳鴜水鳥似魚虎蒼黑色又即知切
NFQ即移;貲:貨也財也即移切十六|頿:說文云口上須俗作髭|鴜:𪇳鴜又疾移切|𪕊:鼠名似雞|鮆:魚名又才禮切|訾:思也又姓何氏姓苑云今齊人本姓蔡氏漢元帝功臣表有樓虛侯訾順|鄑:鄑城名海在北|㠿:布名|媊:說文云甘氏星經曰太白上公妻曰女媊居南斗食厲天下祭之曰明星又音翦|𨚖:谷名|㰣:歐也又子賜切|鈭:鈭錍斧也又千支切|姕:婦人皃又疾支此移二切|𦺱:菜名|䖪:蟲似蟬|觜:觜星爾雅曰娵觜之口營室東壁也又遵誅切
dFY居宜;羈:馬絆也又馬絡也居宜切九|畸:殘田|羇:寄也|掎:掎角又居綺切|攲:以箸取物也說文曰持去也又起宜切|奇:不偶也又虧也又渠羈切|㱦:棄也又丘奇切|妓:妓姕態皃又渠綺切|躸:躸身單皃
AFE府移;卑:下也賤也亦姓蔡邕胡太傅碑有太傅掾鴈門卑整府移切十一|鵯:鵯鶋鳥又音匹|椑:木名似柹荊州記曰宜都出大椑潘岳閑居賦云烏椑之柹|箄:取魚竹器|裨:裨補也增也與也附也助也又音陴|鞞:牛鞞縣在蜀又薄迷脯鼎二切|𩔹:須髮半白|痺〈庳〉:下也又音婢|渒:水名|錍:鈭錍斧也|𢃍:冕也
CFE符支;陴:城上女牆也符支切十五|𩫫:+籀文|焷:缹也|脾:說文曰土藏也釋名曰脾裨也在胃下裨助胃氣主化榖也|䴽:麴餅|埤:附也增也又音婢|裨:副將又姓鄭有大夫裨竈|蜱:爾雅曰蟷蠰其子蜱蛸郭璞云蟷蠰螗螂別名|𧓎:+上同|螷:爾雅曰蜌蠯螷即蚌屬也又薄佳切又薄猛切|蠯:+上同|㯅:木下枝也|郫:郫邵晉邑亦姓出姓苑|𪌈:𪌈䴻麥麵|紕:飾緣邊也
aFQ式支;䌳:繒似布說文曰粗緒也式支切十二|絁:+俗|施:施設亦姓左傳魯大夫施伯何氏姓苑云今沛人又式豉以寘二切|葹:卷葹草名拔心不死|䙾:𧠪䙾面柔也本亦作戚施|鍦:短矛|鉈:+上同說文本食遮切|鸍:似鴨而小又音彌|𪓿:𪓰𪓿蟾蜍別名|䗐:米榖中蟲|𧠜:誘𧠜|𢻫:說文敷也
QFQ息移;斯:此也說文曰析也詩曰斧以斯之又姓吳志賀齊傳有剡縣史斯從息移切二十六|虒:似虎有角能行水中|𩆵:小雨|榹:榹桃山桃|㴲:涯也又水名出趙國|廝:廝養也役也使也|㒋:+上同|凘:凌凘|磃:館名|㾷:痠㾷疼痛又斯齊切|傂:傂祁地名在絳西臨汾水本亦作虒|謕:數諫也諒也|鼶:鼠名又音啼|𪆁:鸒𪆁雅烏|蟴:爾雅曰蟔蛅蟴郭璞曰蛓屬也今青州人呼蛓爲蛅蟴蛓音剌|㽄:甕破|螔:守宮別名|䫢:𩓨䫢頭不正也𩓨音精|䌳:經緯不同又式支切|䔮:草名生水中其花可食|菥:葴菥草似燕麥|𥕶:𥕶磨|蜤:爾雅曰蜤螽蜙蝑郭璞云蜙䗥也俗呼𧐍𧑓|燍:火焦臭也|禠:福也|鐁:平木器名
TFQ楚宜;差:次也不齊等也楚宜切又楚佳楚懈二切四|嵯:㠁嵯山不齊又在河切|齹:齒參差|縒:參縒也
KFQ丑知;摛:舒也丑知切九|螭:螭無角如龍而黃北方謂之地螻|誺:不知又洛代切|魑:魑魅|黐:所以粘鳥又呂支切|㷰:火焱|离:猛獸說文作𡴥山神獸也又呂知切|𡴥:+上同|彲:獸名文王卜獵于渭陽所獲非龍非彲
DFE武移;彌:益也長也久也亦姓三輔決錄有新豐彌升又羌複姓後秦將軍彌姐婆觸武移切十七|𢏏:+上同|鸍:鴆鳥名又名沈鳧似鴨而小也又式支切|镾:長久|䍘:罟也|𥹄:+上同|𥉓:𥉓汙面皃又莫結切|瓕:玉名|獼:獼猴|𥸀:竹篾亦作籩|擟〈檷〉:檷枸山名|麊:縣名在交趾|冞:深入也冒也周行也|㜷:齊人呼母|䥸:青州人云鐮|𥎖:矛也|瀰:渺瀰大水皃
OFQ此移;雌:牝也說文曰鳥母也此移切五|胔:小腸|姕:婦人皃又即移疾移二切|鈭:鈭錍斧也又即移切|𦍧:說文曰羊名蹏皮可以割黍
JFQ陟離;知:覺也欲也陟離切六|䵹:說文曰䵹鼄蟊也|鼅:+上同|蜘:亦同|䣽:酒也|䝷:質當也亦作𧸅
hFY於離;漪:於離切水文也十一|猗:長也倚也施也又犗犬出字林或作犄|椅:木名校實桐皮|旖:旖旎旗舒皃又音上聲|禕:美也珍也|陭:陭氏縣名|欹:歎辝|㾨:身急又弱也|犄:犗也|𩕲:美容皃也|檹:說文曰木檹施也賈侍中說檹即椅木可作琴
LFQ直離;馳:馳騖也疾驅也又姓出姓苑直離切十三|趍:說文曰趍趙夊也|池:停水曰池廣雅曰沼也又姓漢有中牟令池瑗出風俗通又有池仲魚城門失火仲魚燒死故諺曰城門失火殃及池魚|簃:連閣又音移|篪:樂器以竹爲之長尺四寸小者尺二寸七孔世本曰蘇成公所作也|䶵:+上同|踟:踟躕|褫:蓐衣又曰褫氈說文曰奪衣也又敕爾直爾二切|䪧:咸䪧黃帝樂名樂記作池|䶔:齒齗|誃:別也亦作謻|傂:佌傂參差也又息移除爾二切|䞾:輕薄皃
QFg息爲;眭:姓也出趙郡息爲切一
gFo魚爲;危:疾也隤也不正也不安也魚爲切四|㕒:厜㕒|洈:水名在南郡|峗:三峗山名
iFU香支;詑:自多皃俗作訑香支切又湯何切二|焁:焁欨乞人見食皃
VFQ所宜;釃:下酒所宜切又山爾切七|簁:下物竹器又所綺切|欐:梁棟別名又禮麗二音|襹:𧞬襹毛羽衣皃|褷:+上同|𧕯:蚰蜒別名|籭:𥂖也又山佳切
VFg山垂;䪎:鞍鞘一曰垂皃山垂切二|䭨:小餟之皃
cFg人垂;痿:濕病一曰兩足不能相及人垂切又於隹切二|䬐:風緩之皃
NFg姊宜〘規〙;厜:厜㕒山巔狀姊宜切六|觜:星名|纗:細繩|惢:善也說文曰心疑也又桑果才捶二切|嫢:盈姿皃|㭰:鳥喙
dFk居隋;𩓸:說文曰小頭𩓸𩓸也居隋切七|𩓡:+上同|槻:木名堪作弓材|規:圓也字統云丈夫識用必合規矩故規從夫也|鬹:三足釜有柄也|𨾚:鷤䳏鳥名|摫:裁摫方言曰梁益閒裂帛爲衣曰摫
NFg遵爲;劑:券也遵爲切又在細切六|㭰:廣雅云石針也|𦸺:地䓴|臇:臇𦞦也又子兗切|𤎱:-|㷷:+並上同
TFg楚危;衰:小也減也殺也楚危切又所危切二|夊:夊行遟皃
JFg竹垂;腄:瘢胝竹垂切三|箠:節也又之累切|㩾:𢻆㩾不齊
XFg子｟？｠〈之〉垂;䮔:馬小皃子垂切又之累切一
YFQ叱支;眵:目汁凝也叱支切二|䌳:粗緒又式支息移二切
SFQ側宜;齜:開口見齒側宜切一
BGE匹支〖之〗;𤿎〈𢻹〉:器破也匹支切一
lFg悅吹;䔺:悅吹切藍蓼莠又羊箠切六|𩁌:說文云飛也|蠵:觜蠵大龜|欈:觜欈木名實可食也|𧲚:小豶也|䝐:+上同
UFQ士宜;齹:士宜切齒參差亦作𪙉又楚宜切一
#脂
XGQ旨夷;脂:脂膏也釋名曰脂砥也著面軟滑如砥石也說文云戴角者脂無角者膏又姓魏略有中大夫京兆脂習字元升旨夷切十|祗:敬也俗從互餘同|汦〈泜〉:水名又音遲|砥:石細於礪又音旨|栺:栺栭木名亦栺栭柱|鴲:小青雀也|㴯:水名|疻:積血腫皃|䓜:䓜菹也|𥁼:+上同
lGQ以脂;姨:母之姊妹又爾雅曰妻之姊妹同出爲姨以脂切二十六|彝:常也法也亦酒樽也|寅:敬也亦辰名爾雅云太歲在寅曰攝提格又引人切|夷:夷猶等也滅也易也說文平也从大弓又曰南蠻從虫北狄從犬西羌從羊唯東夷從大大人也俗仁而壽有君子不死之國亦姓齊大夫夷仲年又漢複姓六氏史記范蠡適齊爲鴟夷子左傳宋公子目夷之後以目夷爲氏祝融後董父之胤其後以融夷爲氏淮夷虎夷皆國名後並爲氏秦末虎夷渠帥助番君攻秦世本云宋襄公子墨夷須爲大司馬其後有墨夷皋|峓:嵎峓山名書作嵎夷傳云東表之地|恞:悅樂|眱:熟視不言|㰘:木名|珆:石似玉也|蔩:菟瓜又羊善弋仁二切|𡰥:陽𡰥地名本古文夷字|痍:瘡痍|䧅:隇䧅險阻|荑:莁荑|桋:木名|蛦:𧏿蛦蟲名又𧒀蛦山雞也|胰:夾脊肉也|鮧:鱁鮧鹽藏魚腸又魚名也|羠:廣雅云犍羊也|羨:沙羨邑名在江夏出地理志又羊箭祥面二切|鏔:戟之無刃者出方言|𢓡:說文曰行平易也|鴺:鴺𪀕一名飛生|𡱐:𡱐踞|跠:+上同|洟:易曰齎咨涕洟又他計切
VGQ疏夷;師:師範也眾也亦官名大戴禮曰昔者周成王幼在繈褓之中太公爲太師也又姓晉有師曠又漢複姓十二氏左傳衛大夫褚師圃馬師頡鄭有鄉校子產云是吾師也其後以校師爲氏陳悼太子偃師其後以王父字爲氏扶風傳有范師利蔓世本云鄭有子師僕殷時掌樂有太師摯少師陽宋有樂人師延世掌樂職後有宋大夫師延宜風俗通云有牧師氏春秋釋例楚有師祁黎後漢末有南陽師宜官善篆疏夷切六|鰤:老魚|蒒:草名出玉篇|篩:篩竹一名太極長百丈南方以爲船出神異經又竹器也|獅:大生二子|螄:螄螺
CGE房脂;𣬈:說文曰人臍也今作毗通爲𣬈輔之毗房脂切二十三|毗:+義見上注|比:和也並也又匕鼻邲三音|琵:琵琶釋名曰推手爲琵引手爲琶取其鼓時以爲之名也|㮰:楣又方奚切|芘:蔾芘荊蕃藩|沘:水名在楚|貔:獸名|豼:+上同|膍:牛百葉也又鳥膍胵也又步迷切|肶:+上同|蚍:蚍蜉大螘|𧖈:+上同|枇:枇杷果木冬花夏熟|仳:仳倠醜女|𨈚:䠸𨈚體柔|魮:文魮魚名狀如覆銚鳥首而翼魚尾音如磬生珠出山海經|鈚:犁錧別名|𦳈:蒿也|𦊁:篝筌|阰:山名在楚南|𧑜:蟲名|鵧:鳥名
NGQ即夷;咨:嗟也謀也即夷切十五|資:助也機也貨也又姓陳留風俗傳云黃帝之後|粢:祭飯|𪗉:+上同|𪗋:𪗋縗經典通用齊|𧞓:+上同|諮:諮謀|姿:姿態|齍:黍稷在器|澬:水名在邵陵又音茨|𣳩:具𣳩山在滎陽出山海經|齎:齎持也又子兮切|蒫:蒫薺實也|𩆂:雨聲|𩄚:+上同
dGY居夷;飢:飢餓也又姓左傳殷人七族有飢氏居夷切四|机:木名似榆又音几|肌:肌膚|虮:密虮蟲名
YGQ處脂;鴟:一名鳶也處脂切七|𨾦:+上同|𪀒:亦同|胵:膍胵鳥藏|𩶅:魚名|𧪡:怒也|𨒬:走皃
KGQ丑飢;絺:細葛也丑飢切七|辴:笑皃又敕辰抽敏二切|郗:邑名又姓出高乎|𥭘:竹器|脪:𦚈脪牛馬子腸|瓻:酒器大者一石小者五斗古之借書盛酒瓶|訵:陰知也出字林
OGQ取私;郪:縣名在梓州取私切又七西切九|趑:趑趄趨不進也|𨌅:說文作䡨連車也一曰郤車抵堂又士佳疾資二切|趀:說文云倉卒也|𧾒:+上同|𧠵〈𧠥〉:盜視|𡰾:+上同亦此也|𡳠:此也|蠀:蝎化也
PGQ疾資;茨:茅茨又姓後漢有茨充亦漢複姓晉有茨芘仲疾資切十三|薋:蒺蔾詩作茨說文又作薺|薺:+上同又才禮切|餈:飯餅也|𩜴:+上同|垐:以土增道|䆅:積禾|蠐:蠐螬又疾兮切|瓷:瓦器|澬:水名在常山郡又涔澬久雨又音資|𥿆:𥿆補|𨌅:連車又七茨切又士佳切|𩆂:涔𩆂久雨
MGQ女夷;尼:和也女夷切八|柅:木名又女履切|怩:忸怩心慙也|蚭:字林云北燕人謂蚰蜒爲䖡蚭也|跜:躨跜虯龍動皃見文選|呢:言不了呢喃也|𩚯:餌𩚯|䝚:獸名
LGQ直尼;墀:說文云墀塗地也禮天子有赤墀漢典職曰以丹漆地故稱丹墀漢書曰王根作赤墀直尼切十五|𡎰:+上同|坻:小渚俗從互餘同|泜:水名在常山陳餘死處也又旨夷切|遲:徐也久也緩也亦姓晉湘東太守遲超又虜姓後魏書尉遲氏後改爲尉氏又音稺|遟:+上同|蚳:蟻卵|岻:山名|彽:彽徊猶徘徊也|阺:字統云秦謂陵阪爲阺也|荎:爾雅云櫙荎今之刺榆也|菭:水衣也又徒來切|謘:語諄謘也|莉:姓也出淮南|貾:貝之黃質有曰白點者
QGQ息夷;私:不公也說文曰禾也息夷切五|鋖:平木器也亦作鐁|厶:自營爲厶也說文曰姦衺也|𦮺:說文曰茅秀也|㺨:石似玉者
aGQ式之〖脂〗;尸:主也陳也利也又姓秦有尸佼爲商君師著書式之切四|鳲:鳲鳩鴶鵴今布穀也詩疏云鳩之養其子朝從上下暮從下上食之平均如一也|屍:禮記曰在牀曰屍在棺曰柩|蓍:蒿屬筮者以爲策說文云蓍生千歲三百莖易以爲數天子蓍九尺諸侯七尺大夫五尺士三尺
fGU渠脂;鬐:馬項上鬐也渠脂切十一|𦓀:方言云長也說文云老也左傳云強也禮記音義云至也言至老境也|耆:+上同|愭:畏也敬也|𧡺:視也|𥉙:+上同|䅲:麥下種也|祁:盛也縣名在太原左傳晉大夫祁奚之邑因以名之又姓出太原黃帝二十五子之一也何氏姓苑云今扶風人|𨪌:衛軸鐵也|鰭:魚脊上骨|鮨:鮓也
hGU於脂;伊:惟也因也侯也亦水名又州本伊吾廬地在燉煌之北大磧之外秦末有之漢爲伊吾屯隋爲郡貞觀初慕化內附置伊州焉又姓伊尹之後今山陽人於脂切五|咿:喔咿|蛜:蛜蝛𧑓負蟲也|黝:縣名屬歙州又於九切|黟:+上同
IGQ力脂;棃:果名魏文詔云真定御棃大如拳甘如蜜力脂切十四|梨:+上同|𠠍:直破|秜:稻死來年更生|蜊:蛤蜊|蔾:蒺蔾|犂:牛駁又郎奚切|刕:姓也出蜀刀逵之後避難改爲刕氏也出字書|𢤂:說文恨也一曰怠也|鯬:魚名|鑗:金屬|䴻:𪌈䴻餅也|蟍:螏蟍蝍蛆蜈蚣|𨟀:國名
fGk渠追;葵:說文曰菜也常傾葉向日不令照其根渠追切八|鄈:鄈丘地在陳留又在河東漢祭后土處|楑:柊楑|𩹍:魚名|𢜽:悚也又祇癸切|𦝢:䑏𦝢醜也|䳫:䳫鳩鳥|𧍜:蟲名
JGg陟隹;追:逐也隨也陟隹切三|䨨:雷也出韓詩|娺:疾也
dGo居追;龜:說苑曰靈龜五色似玉似金背陰向陽上高象天下平法地易号爲龜大戴禮曰甲蟲三百六十而神龜爲之長居追切六|𪚦:+上同|𠃾:+古文|䟸:曲脛|螝:爾雅云蠶蛹|騩:馬淺黑色
cGg儒隹;蕤:葳蕤草木華垂皃又蕤賓五月律儒隹切七|甤:說文曰草木實甤甤也|緌:緌纓|擩:染也又而樹切|桵:白桵木也|䅑:禾四把也又息遺切|捼:摧也又奴禾切俗作挼
VGg所追;衰:微也所追切三|榱:屋橑說文曰秦名爲屋椽周謂之榱齊魯謂之桷|𤸬:病也說文減也一曰耗也
lGg以追;惟:謀也思也以追切十二|𣄧:旌也|維:豈也隅也持也繫也說文曰車蓋維也|遺:失也亡也贈也加也又姓急就章有遺餘又以醉切|濰:水在琅邪|壝:埒也壇也又以癸切|𥌰:目病|蓶:菜名似韮而黃|䜅:就也又十隹切|琟:石似玉也|唯:獨也又以癸切|𧔥:蜰𧔥神蛇一首兩身六足四翼見則其國大旱湯時見於陽山出山海經
IGg力追;㶟:水名在鴈門力追切十三|纍:纍索也亦作縲又姓晉七輿大夫纍虎|虆:蔓草|欙:山行乘欙亦作樏|𤜖:求子牛|𡿔:㟪𡿔又力罪切|㠥:+上同|𡤯:𡤯祖黃帝妃亦作嫘|瓃:玉器|𥍔:視皃|鸓:飛生鳥也又力水切|儽:嬾懈皃亦作傫又力罪切|纝:網絡論語注云黑索也亦作縲
QGg息遺;綏:安也說文曰車中靶也又州名春秋時爲白翟所居秦并天下爲上郡後魏廢郡置州取綏德縣以爲名息遺切十二|雖:語助也本蟲名似蜥蜴而有文|荾:明荾香菜博物志曰張騫西域得胡荾石虎鄴中記曰石勒改胡荾爲香荾|荽:+上同|䒘:亦同|葰:亦同說文曰薑屬可以香口|浽:浽溦小雨|奞:說文曰鳥張毛羽自奮奞也又戌閏切|夊:行遲皃又楚危切|睢:水名在梁郡又許葵切|濉:+上同|䅑:禾四把長沙云又儒隹切
fGo渠追;逵:隱也爾雅曰九達謂之逵渠追切十九|夔:夔龍亦州名春秋時魚國漢爲魚復縣梁隋皆爲巴東郡唐初改爲信州又改爲夔州取夔國名之又獸名似牛一足無角其音如雷皮可以冒鼓|𣦞:+俗|馗:說文曰九達道也與逵同又鍾馗俗以辟惡|戣:兵器戟屬|鍨:+上同|騤:強也盛也又馬行皃|犪:犪牛出岷山肉重數千斤出山海經|躨:躨跜見文選|𦝢:䑏𦝢醜也|艽:埤蒼云遠荒又音求|䟸:左脛曲也|𠊾:左右視也|𨾎:顧皃|頯:小頭|𠐽:使也|𧢦:淫視又丘韋切|𢌳:持也|頄:面顴也又音求
DGI武悲;眉:說文作睂目上毛也武悲切二十|睂:+見上注|嵋:山形|湄:釋名曰湄眉也臨水如眉也爾雅曰水草交爲湄|𤃱:+上同|鶥:鳥名爾雅曰鶬麋鴰今呼鶬鴰字林作鶥|楣:戶楣釋名云楣近前各兩若面之有眉|瑂:石似玉也|矀:伺視|覹:+上同|䉠:竹名又音微|黴:黴黧垢腐皃又莫背切|麋:鹿屬冬至解其角又姓蜀將東海麋竺也|蘪:蘪蕪香草即江蘺也|郿:縣名在岐州|㵟:爾雅曰谷者㵟郭璞云通於谷也|薇:爾雅曰薇垂水謂生於水邊|𦗕:金飾馬耳又武卑切|葿:䒲葿草|攗:水芰名也
AGI府眉;悲:痛也府眉切一
XGg職追;錐:說文銳也職追切八|隹:說文曰鳥之短尾者總名|𪋇:鹿一歲|騅:馬蒼白雜毛又姓左傳晉七輿大夫騅㪜也|㮅:木名似桂|䶆:鼠名|萑:萑蓷茺蔚又名益母|鵻:鳥名
ZGg視隹;誰:何也視隹切三|䜅:就也又以隹切|脽:說文𡱂也亦汾脽巨靈所坐也
kGo洧悲;帷:說文曰在旁曰帷釋名曰帷圍也所以自障圍也洧悲切一
CGI符悲;邳:下邳縣名在泗州又姓風俗通云奚仲爲夏車正自薛封邳其後爲氏後漢有信都邳彤符悲切六|鉟:刃戈又音丕|䲹:鶚也|岯:山再成也|魾:大鱯也又音丕|䫠:說文云短須髮皃又音丕
BGI敷悲;丕:大也亦姓左傳晉大夫丕鄭敷悲切十二|㔻:+上同|伾:有力|秠:黑黍一稃二米又匹几切|䪹:大面|駓:桃花色馬|怌:怌怌恐也|䫠:短須髮皃|豾:貍子|髬:髬髵猛獸奮鬣皃|魾:大鱯|鉟:刃戈
iGk許維;倠:仳倠醜面許維切六|婎:+上同|睢:睢盱視皃|眭:眭盱健皃|𢊄:姿𢊄|𢊿:+上同
LGg直追;鎚:金鎚又權也文字音義云從垂亦通直追切五|椎:椎鈍不曲橈亦棒椎也又椎髻|槌:+上同又直累切|桘:+俗|顀:項顀
YGg叉〈尺〉隹;推:排也叉隹切又尺湯回切二|蓷:萑蓷又湯回切
JGQ丁尼;胝:皮厚也俗作𦙁丁尼切四|疷:+上同|秪:穀始熟也|氐:氐池縣名又音低
BGE匹夷;紕:繒欲壞也匹夷切六|㩺〈𢻹〉:-|𦀘:+二同|𧧺:謬也|悂:+上同|𢞗:惡性也
NGg醉綏;嶉:高皃醉綏切二|檇:以木有所擣又地名左傳越敗吳於檇李又音醉
eGo丘追;巋:小山而眾丘追切又丘誄切二|蘬:蘢古大者曰蘬
gGY牛肌;狋:犬怒皃牛肌切又巨圓切一
iGU喜夷;咦:笑皃喜夷切五|忾:廣雅云喜皃|䐅:臀之別名|𣢂:呻吟聲|屎:+上同
#之
XHQ止而;之:適也往也閒也亦姓出姓苑止而切四|臸:到也又如一切|芝:芝草論衡曰芝生於土土氣和故芝草生古瑞命記曰王者慈仁則芝草生也|㞢:篆文象芝草形蚩從此也
lHQ與之;飴:𩛿也與之切二十七|𩛛:+籀文|䬮:+古文|怡:和也悅也又姓周書怡峯傳云本姓默台避難改焉|弬:弓名出韻略|媐:說文云悅樂也|异:已也又音異|㼢:㽃㼢甎也|𣐵:船欿水斗|鏔:戟無刃也|圯:土橋名在泗州|貽:貺也遺也|巸:長也美也廣𦣞也|洍:水名詩云江有洍又音似毛詩作汜|𦣞:說文曰顄也|𩠢:+籀文|頤:+頤養也說文亦上同|詒:贈言|㺿:玉名|沶:水名|宧:室東北隅|𦚟:豕息肉今謂之豬𦚟|䱌:鯸䱌魚也|姬:王妻別名本又音基|台:我也又姓出姓苑又音胎|眙:盱眙縣在楚州|瓵:爾雅云甌瓿也
ZHQ市之;時:辰也廣雅曰時伺也又善也中也是也又姓良吏傳有時苗何氏姓苑云今鉅鹿人市之切七|旹:+古文|塒:穿垣棲雞|鼭:鼠名|榯:樹木立也|蒔:蒔蘿子又音示|鰣:魚名似魴肥美江東四月有之
gHc語其;疑:不定也恐也惑也嫌也語其切三|嶷:九嶷山名亦作疑又魚力切|觺:觺觺獸角皃又魚力切
QHQ息兹;思:思念也息兹切又息吏切十五|恖:+上同|司:主也亦姓左傳鄭有司臣又漢複姓八氏司馬氏本自重黎程伯休甫之後出河內世本士丏弟佗爲晉司功因官爲氏及司徒司寇司空並以官爲氏漢有朝議郎司國吉諫議大夫司鴻儀左傳宋大夫司城子䍐其後氏焉|罳:罘罳屏也崔豹古今注云罘罳復思也謂臣來朝君行至內屏外復思惟故曰罘罳也|伺:伺候又息吏切|絲:說文云蠶所吐也又一蠶爲忽十忽爲絲淮南子曰蠶餌絲則商弦絕|緦:緦麻|𥯨:竹名有毒傷人即死|禗:不安欲去|覗:覰也|㺇:辯獄相察|𥄶:姦視|蕬:菟蕬草名案爾雅云女蘿菟絲字不从艹|偲:論語曰朋友切切偲偲|楒:相楒木
THQ楚持;輜:楚持切又側持切義見下文二|颸:風也
fHc渠之;其:辝也亦姓陽阿侯其石是也又漢複姓六氏左傳邾庶其之後以庶其爲氏世本楚大夫涉其帑漢清河都尉祝其承先王僧孺百家譜蘭陵蕭休緒娶高密侍其義叔女何氏姓苑有行其氏今其氏渠之切又音基三十|期:期信也會也限也要也又姓風俗通有期思國又漢複姓二氏後漢梁鴻改姓運期氏古仙人有安期生賈執英賢傳云今琅邪人|旗:旌旗釋名曰熊虎爲旗將軍所建象其猛如虎與眾期之於下也戰國策曰建七星之旗天子之位也又姓齊卿子旗之後漢有九江太守旗光|綦:履飾又蒼白色巾也詩曰縞衣綦巾又姓何氏姓苑云義興人|綨:+上同|𢃛:+俗|萁:豆萁|𧯯:+上同|蜝:蟛蜝似蟹而小晉蔡謨食之殆死也|琪:玉也|麒:麒麟|騏:騏驥|淇:水名出沮洳之山說文曰淇水出河內共北山東入河|䳢:鳥名|錤:鎡錤鋤別名也|藄:紫藄似蕨菜|棊:博物志曰舜造圍棊丹朱善之|櫀:+上同|碁:亦同|𤪌:弁飾|璂:+上同|鯕:鯿魚|蘄:州名漢蘄春縣也晉孝武鄭后諱春改爲蘄陽周平淮南改爲州因蘄水以爲名又姓也|祺:祥也吉也|禥:+籀文|踑:踑馴跡也|𦪆:𦪆艃舟名|䑴:+上同|𢍁:舉也|䶞:齧也
aHQ書之;詩:說文曰志也詩序云發言爲詩釋名曰詩之也志之所之也書之切六|邿:地名|齝:說文曰吐而噍也又敕釐切|𪗪:-|呞:+並上同|䀢:䀢的也見聲類
cHQ如之;而:語助說文曰頰毛也如之切二十一|栭:木名子似栗而小一曰梁上柱也|𣚊:木耳別名|𨼏:地名又夔險也|陾:+上同又音仍|陑:+上同|髵:須也髬髵也|峏:山名|𨎪:喪車|輀:+上同|𦠌:煑熟|胹:-|𦓒:+並上同|𩰴:+籀文|洏:漣洏涕流皃|鮞:魚子|耏:獸多毛亦作髵又姓左傳宋有耏班|咡:吻又音餌|䎠:丸之熟也又音丸|誀:誘也又音餌|鴯:莊子云鳥莫智於鷾鴯鷾鴯玄鳥也
eHc去其;欺:詐也去其切十一|娸:姓一曰醜也|䫥:大頭|䫏:方相說文曰醜也今逐疫有䫏頭|𠐾:+上同|魌:亦同|僛:醉舞皃|𪅾:鵋𪅾鵂鶹鳥亦作䳢|𪀩〈𡖾〉:廣雅云多|䶞:齧也|抾:把挹也又丘之切
dHc居之;姬:周姓也居之切十二|朞:周年又復時也|稘:+上同|基:經也業也址也始也設也|箕:箕帚也世本曰箕帚少康作也又姓左傳晉有大夫箕鄭|萁:菜似蕨又音期|䇫:可以取蟣也|諅:謀也說文忌也本渠記切|其:不其邑名在琅邪又人名漢有酈食其|錤:鎡錤大鉏|居:語助見禮|諆:謀也說文欺也本去其切
RHQ似兹;詞:請也說也告也說文曰意內而言外也似兹切七|祠:祭名|柌:鎌柄|辭:辭訟說文曰辭說也|辤:+上同說文曰不受也受辛宜辤之|辝:+籀文|𥿆:補也
IHQ里之;釐:理也一曰福也里之切二十|貍:野猫|狸:+俗|氂:十豪|嫠:無夫|剺:剝也|梩:徙土轝出六韜又都皆切|犛:犛牛又音茅|𣁟:字統云微畫也|倈:倈來見楚詞|艃:䑴艃船名|𣮉:毛起也又音來|孷:孷孳雙生子也|𢟤:愁憂之皃|𩭇:髬𩭇髮起|㾖:病也又音里|筣:竹名|斄:說文曰強曲毛也可以著起衣|𠩬:+古文|𠭰:引也
SHQ側持;菑:說文曰不耕田也爾雅曰田一歲曰菑側持切又音栽十五|甾:+上同又說文曰東楚名缶曰甾|𦸜:+亦同|淄:水名亦州名春秋時屬齊漢爲濟南郡宋文帝改清河郡隋置淄州因水以名焉古通用菑|𥀜〈㿳〉:手足生皮堅也|茬:茬丘名案漢書地理志泰山郡有茬縣顏師古曰又士疑切亦姓|輜:輜軿車|錙:錙銖|鶅:東方雉也|緇:黑色繒也|䊷:+上同|椔:木立死|鯔:魚名|䎩:耕也|䣎:鄉名
iHc許其;僖:樂也又姓姓苑云彭城人許其切十五|歖:卒喜|熙:和也廣也長也|嬉:美也一曰游也|禧:福也吉也|媐:善也悅也|譆:痛聲|𠩺:坼也|瞦:目睛|㶼:火盛|熹:盛也博也熱也熾也或作熺|嘻:噫嘻歎也|𣢑:喜笑|娭:婦人賤稱出蒼頡篇|誒:說文云可惡之詞也
hHc於其;醫:醫療也亦官名漢太常屬官有太醫令續漢書曰秩六百石有藥丞主藥方說文曰巫彭初作醫於其切五|毉:+上同|譩:忿也|㿄:羸也又乙賣切|噫:恨聲
KHQ丑之;癡:不慧也丑之切四|齝:牛吐食而復嚼也|笞:捶擊|痴:痴㾻不達之皃
LHQ直之;治:水名出東萊亦理也直之切三|持:執持|莉:姓也姓苑云淮南人
YHQ赤之;蚩:蟲名亦輕侮字從㞢赤之切七|嗤:笑也俗又作𣣷|妛:輕侮|媸:媸妍|𦐉:羽盛|𣍆:告也又乃經切|𥉍:目汁凝
PHQ疾之;慈:愛也亦州名春秋時晉之屈邑夷吾所居西魏改爲汾州開皇初爲耿州武德改爲慈州因慈氏縣名之疾之切五|礠:礠石可引針也|鶿:鸕鶿鳥亦作鷀不卵生口吐其鶵又子之切|濨:澗水名也|兹:龜兹國名龜音丘
NHQ子之;兹:此也又姓左傳魯大夫兹無還子之切十四|孳:孳息|嵫:崦嵫山名日所入劇|孜:處也力篤愛也|滋:水名出高麗山又旨也蒔也多也蕃也液也|嗞:嗞嗟憂聲也|𪑿:染黑|鎡:鎡錤|孖:雙生子也|鼒:小鼎|鰦:魚名|仔:克也|鶿:鸕鶿鳥|稵:禾生皃
UHQ士之;茬:說文曰草皃濟北有茬平縣俗作茌士之切一
WHQ俟甾;漦:涎沫也又順流也俟甾切一
e8f丘之〈乏〉;抾:挹也丘之切一
aHQ式其;䀵:眴也式其切一
#微
DIM無非;微:妙也細也少也說文曰隱行也無非切八|𢼸:說文曰妙也|㵟:浽㵟小雨|薇:菜也|䉠:竹名又武悲切|䥩:埤蒼云懸物鉤|癓:三蒼云足上瘡|矀:伺視又武悲切
iIs許歸;揮:揮霍亦奮也灑也振也動也許歸切十三|煇:光也|輝:+上同|暉:亦同又日色|徽:美也又三糾繩也|翬:飛皃又雉五色備也|褘:后祭服也|鰴:魚有力也|楎:橛也在牆曰楎又犁頭也|幑:幡也|瀈:竭也|㫎:動旗|𤟤:山𤟤獸名似犬見人則笑行疾如風又胡昆切
kIs雨非;幃:香囊也一說單帳也雨非切又許歸切十五|韋:柔皮也又姓出自顓頊大彭之後夏封於豕韋苗裔以國爲氏因家彭城至楚太傅韋孟遷于魯孟玄孫賢爲漢丞相始遷京兆之杜陵也|闈:宮中門也|圍:守也圜也遶也|䙟:重衣|𩎯:束也|違:背也|湋:水名|囗:文字音義云回也象圍帀之形也|鍏:方言云宋魏呼臿也|潿:水不流濁皃|婔:江婔神女|𧝕:裹也|𠆎:衺也|𢾁:戾𢾁
BIM芳非;霏:雪皃芳非切九|䬠:+上同|妃:嘉偶曰妃說文匹也又音配|菲:芳菲又芳尾切|䩁:細毛|婓:婓婓往來皃一曰醜|騑:騑騑馬行皃|裶:衣長皃|𥇖:大目又方巾切
AIM甫微;猆:姓左傳晉有猆豹甫微切十二|飛:飛翔亦漢複姓史記有飛廉氏古通用蜚|扉:戶扉|緋:絳色|𩙲:獸如牛白首一目|非:不是也責也違也亦姓風俗通有非子伯益之後|馡:香也|𩹉:魚名|騛:騛兔馬而兔足|騑:驂旁馬也又音菲|誹:誹謗又方未切|餥:糇也又方尾切
CIM符非;肥:肥腯說文曰多肉也亦姓戰國策有肥義符非切十一|腓:腳腨腸也|䈈:竹名|淝:水名在廬江本作肥|𤷂:風𤷂病也|痱:+上同|蜰:蟲名即負盤蟲|𩇯〈䨽〉:蠹䨽鳥名如梟人面一足冬見夏蟄著其毛令人不畏雷出山海經|蟦:蠐螬|賁:姓也出姓苑又布昆彼義符文三切|裴:即裴縣名案漢書地理志在魏郡應劭音非本又音陪
hIs於非;威:威儀又姓風俗通云齊威王之後於非切八|葳:葳蕤|隇:隇䧅險也|嵔:嵔㠥也又於鬼烏罪二切|蝛:蛜蝛蟲也一名𧑓蝜|鰄:魚名|媁:美也|楲:決塘木也又楲窬褻器也
fIc渠希;祈:求也報也告也渠希切十九|頎:長皃|旂:爾雅曰有鈴曰旂釋名曰交龍曰旂旂倚也畫作兩龍相依倚也通以赤爲之無文彩諸侯所建也|𩴆:鬼俗|畿:王畿|㙨:+上同|崎:曲岸|碕:+上同|圻:+亦上同又書傳爲京圻字又魚斤切|刏:以血塗門又居依古對二切|𧰙:危也說文曰訖事之樂也又公哀切|𦠄:頰肉|俟:虜複姓北齊有特進万俟普万音墨|幾:近也又居依居豈二切|蚚:蟲也爾雅云強蚚|玂:犬生一子|蟣:爾雅云蛭蟣又居豈切|岓:山傍石也|𪙧:齒危
dIc居依;機:會也萬機也說文云主發謂之機書曰若虞機張傳云機弩牙也居依切十六|譏:諫也誹也譴也問也|蘄:縣名在徐州亦草名又音其芹|嘰:口醜說文云小食也|𦺬:菹𦺬草|磯:大石激水|鞿:繫馬|饑:穀不熟|禨:祥也|幾:庶幾又祈蟣二音|䟇:走也|鐖:鉤逆鋩淮南子曰無鐖之鉤不可以得魚|僟:精也明堂月令曰歲將僟終|璣:珠不圓也|刏:斷切也剌也刲傷也|𧗇:血祭
iIc香衣;希:止也望也散也施也爾雅罕也又姓三輔決錄有希海字子江香衣切十二|晞:日氣乾也|莃:菟葵|鵗:北方名雉|睎:視也眄也望也|稀:稀疎|豨:豬也又虛豈切|𧻶:走皃|桸:木名汁可食|悕:願也又悲也|俙:依俙|欷:說文曰歔也又喜既切
hIc於希;依:倚也祿也於希切八|郼:殷國名也|衣:上曰衣下曰裳世本曰胡曹作衣白虎通云衣者隱也裳者障也所以隱形自障蔽也又姓出姓苑|譩:痛聲|㛄:女字|㐆:說文曰歸也从反身|䧇:天䧇縣在酒泉|㥋:念痛聲也
gIc魚衣;沂:水名出泰山魚衣切二|溰〈凒〉:凒凒霜皃
gIs語韋;巍:高大皃語韋切二|犩:爾雅云犩牛郭璞曰即犪牛也如牛而大肉數千斤
dIs舉韋;歸:還也公羊傳曰婦人謂嫁曰歸亦州名古夔子國武德初割夔州之秭歸巴東二縣置州取歸國爲名也舉韋切三|㱕:+籀文|騩:大騩山
eIs丘韋;蘬:馬蓼似蓼而大也丘韋切又丘追丘誄二切二|𧢦:視也
#魚
gJc語居;魚:說文曰水蟲也亦姓出馮翊風俗通云宋公子魚賢而有謀以字爲族又漢複姓二氏左傳晉有長魚矯史記有修魚氏語居切十|𩺰:說文曰二魚也|漁:說文云捕魚也尸了曰燧人之世天下多水故教民以漁也又水名在漁陽|𩼪:+上同|䰻:+上同|䱷:+䱷獵亦上同|齬:齒不相值又魚舉切|鋙:鋤屬又音語|䁩:爾雅曰馬二目白魚字或從目|衙:說文曰衙衙行皃又音牙
TJQ楚居;初:舒也始也從刀衣蓋裁衣之初楚居切二|𠿝:呵叱人也
aJQ傷魚;書:世本曰沮誦蒼頡作書釋名曰書庶也紀庶物也亦言著也著之簡紙水不滅也傷魚切七|鵨:鳥似鳧也|瑹:美玉名案禮記注云笏也本亦作荼|舒:緩也遟也伸也徐也敘也亦州名春秋時晥國晉於皖縣置懷寧縣武德改爲舒州亦姓何氏姓苑云廬江人|𦺗:魚薺|紓:緩也|𨛭:地名在廬江
dJc九魚;居:當也處也安也九魚切十四|𡨢:𡨢儲|据:手病詩云予手拮据毛萇曰拮据撠挶也|裾:衣裾|琚:玉名|䝻:貯也|鶋:鶢鶋海鳥|車:車輅又昌遮切|蜛:蜛蠩|崌:崌崍山也|椐:木名|涺:水名|𦱅:苴𦱅草也|腒:鳥腊又音渠
fJc強魚;渠:溝渠也亦州名宋置宕渠郡周仍爲郡武德初改置州亦有宕渠山又姓左傳衛有渠孔御戎強魚切二十六|𨎶:車輞|𦄽:履飾|璩:玉也|磲:硨磲美石次玉|蕖:芙蕖|籧:籧篨|𥴧:飤牛筐|淭:淭挐方言云杷宋魏之閒謂之淭挐|醵:合錢飲酒又巨略切|腒:鳥腊|𪆫:𪄉𪆂鳥|螶:說文云螶𧎾也一曰蜉蝣朝生暮死者爾雅作渠略|蟝:+上同|䝣:䝣獀獸名食猛獸出山海經|豦:獸名說文曰鬬相丮不解也从豕虍豕虍之鬬不相捨司馬相如說豦封豕之屬一曰虎兩足舉又音據|蘧:蘧麥又姓|鐻:鐻耳之傑|璖:耳環|𨞙:聚名|㯫:㯫栫藩籬名|䟊:小走皃|𦼫:𦼫菜似蘇又音巨|䆽:穴類|𧝔:繫𧝔|懅:怯也又音遽
lJQ以諸;余:我也又姓風俗通云秦由余之後何氏姓苑云今新安人以諸切三十|蜍:蜘蛛又常魚切|藇:芞藇香草|㶛:水名|餘:殘也賸也皆也饒也又姓晉有餘頠又漢複姓三氏晉卿韓宣子之後有名餘子者奔於齊號韓餘氏又傳餘氏本自傅說說既爲相其後有留於傅巖者因號傅餘氏秦亂自清河入吳漢興還本郡餘不還者曰傅氏今吳郡有之風俗通云吳公子夫摡奔楚其子在國以夫餘爲氏今百濟王夫餘氏也|輿:車輿又多也又權輿始也續漢書輿服志曰上古聖人觀轉蓬始以爲輪輪行不可載因物生智後爲之輿又姓周大夫伯輿之後|旟:周禮曰鳥隼曰旟州里所建也爾雅曰錯革鳥曰旟郭璞云此謂合剝鳥皮毛置之竿頭|鵌:鳥名與鼠同穴又大都切|璵:魯之寶玉|艅:艅艎吳王船名|畬:田三歲也|𤰩:+上同|｛㶛｝【本紐重出當刪】:水名|歟:說文云安气也又語末之辝亦作與|與:+上同本又餘佇切|譽:稱也又音預|嬩:女字|舁:對舉|擧:+上同|妤:婕妤婦人官也亦作倢伃|伃:+上同|㦛:恭敬|𪋮:說文云似鹿而大又弋庶切|予:我也又餘佇切|㺞:獸名|𩦡:馬行皃|𧾚:𧾚𧾚安行皃|狳:獸名山海經云餘我之山有獸如兔鳥喙鴟目蛇尾遇人則眠名曰犰徐見則有螽蝗爲害也|鸒:爾雅云鸒斯雅烏又羊庶切|雓:爾雅曰鷄大者蜀蜀子雓
QJQ相居;胥:相也說文曰蟹醢也又姓晉有大夫胥童何氏姓苑云琅邪人也俗作𦙃相居切又息呂切十一|䱬:魚名|䈝:竹名|稰:落也|楈:木名|藇:姓出纂文本又音序|諝:有才智之稱又息呂切|㥠:+上同|湑:露皃又息呂切|蝑:蜙蝑蟲|揟:取水具也
OJQ七余;疽:癰疽也七余切十六|岨:石山戴土|砠:+上同|䢸:鄉名在鄠縣又子余切|趄:趑趄|苴:履中藉又子魚切|沮:止也非也又水名在房陵所謂沮漳書云漆沮既從並在北地又子魚側魚疾與子預四切|狙:猿也又七預切|䏣:蟲在肉中|蛆:+俗|雎:雎鳩鳥|蒩:苞蒩又則吾切|𣻐:說文云水出北地直路西東入洛|伹:拙人|坥:螾場又七預切|𡳆:此也
UJQ士魚;鉏:誅也又田器釋名曰鉏助也去穢助苗也說文曰立薅斫也又姓左傳有鉏麑士魚切六|鋤:+上同|耡:周禮曰以興耡利氓又音助|豠:豕屬|𧱑:+上同|𪆷:𪅖𪆷鳥白鷺也爾雅作舂鉏
KJQ丑居;攄:舒也丑居切四|㯉:惡木|筡:竹篾名也|摴:摴蒱戲又姓史記秦相摴里疾
VJQ所葅（菹）;疏:通也除也分也遠也窻也又姓漢有太子太傅東海疏廣或作𤕟俗作疎所葅切又所助切十一|梳:梳櫛說文曰理髮也|綀:綀葛|蔬:菜蔬|疎:稀疎|𥿇:𥿇繼|釃:下酒|𦌿:+上同|𤕟:通也|㽰:青疏|疋:足也古爲雅字
iJc朽居;虛:空虛也亦姓出何氏姓苑朽居切又音袪六|驉:駏驉畜似騾也|歔:歔欷|噓:吹噓|魖:魖耗鬼又夔魖罔象才石之怪也|𥛳:+上同出字書
RJQ似魚;徐:緩也說文安行也亦州名古之彭國禹爲徐州秦屬泗水郡漢爲郡復置徐州又姓自顓頊之後春秋時徐偃王行仁義爲楚文王所滅其後氏焉出東海高平東莞琅邪濮陽五望似魚切四|䣄:地名又音徒|䍱:野羊|俆:說文緩也
hJc央居;於:居也代也語辝也又商於地名亦姓今淮南有之央居切又音烏五|扵:+俗|箊:竹名|淤:淤泥又依倨切|唹:笑皃
JJQ陟魚;豬:爾雅曰豕子豬陟魚切六|䐗:+上同|猪:+俗|瀦:水所停也|櫫:楬櫫有所表識|藸:藸蒘草又音除
IJQ力居;臚:皮臚腹前曰臚又鴻臚寺漢書曰典客秦官武帝更名大鴻臚韋昭曰鴻大也臚陳序也欲以禮大陳序賓客也力居切十七|閭:侶也居也又閭閻周禮曰五家爲比使之相保五比爲閭使之相受也又姓出衛國頓丘二望又漢複姓四氏凡閭氏出自晉唐叔賈執英賢傳云今東莞有之林間氏出自嬴姓文字志云後漢有蜀郡林閭翁孺博學善書藝文志云古有將閭子名菟好學著書晉有寧州剌史樂安辟閭彬|䰕:毛也說文鬣也|廬:寄也舍也周禮曰凡國十里有廬廬有飲食亦州名春秋時舒地秦爲合肥縣梁以爲合州隋爲廬州又山名廬山記云周威王時有匡俗廬君故山取其號|蘆:漏蘆草又音盧|櫚:栟櫚木名有葉無枝博雅曰栟櫚椶也|驢:畜也|藘:蕠藘草|䕡:菴䕡草|爈:火燒山界|𤁵:浘𤁵海水洩處案莊子作尾閭|㠠:玉篇云山名|櫖:諸攄山櫐爾雅作慮|璷:字林云玉名|䮉:傳馬名|𥶆:𥶆䈝竹名|𢣻:𢣻憂也
XJQ章魚;諸:之也旃也辯也非一也又姓漢有洛陽令諸於出風俗通又漢複姓有諸葛氏吳書曰其先葛氏本琅邪諸縣人徙陽都先姓葛時人謂徙居者爲諸葛氏因爲氏焉風俗通云葛嬰爲陳涉將有功而誅孝文追錄封其孫諸縣侯因并氏焉章魚切七|櫧:木名|㶆:水名在北嶽|藷:藷蔗甘蔗|𧄔:薯蕷別名|䃴:礛䃴青礪也|蠩:蜛蠩一頭數尾長二三尺左右有腳狀如蠶可食也
LJQ直魚;除:階也又去也直魚切十三|躇:躊躇|儲:儲副又姓後漢有儲太伯|涂:水名在堂邑又直胡切|篨:籧篨蘆䕠也|𦿀:籌𦿀蔥名|宁:門屏閒又音佇|㾻:瘢也|著:爾雅云太歲在戊曰著雍又直略陟慮陟略三切|滁:水名出簸箕山入海亦州春秋時楚地梁爲南譙州齊改爲臨滁郡開皇改爲滁州|蒢:草名可染又蕖蒢口柔也|屠:匈奴傳有休屠王又音徒|藸:爾雅曰菋荎藸郭璞云五味也蔓生子叢在莖頭
cJQ人諸;如:而也均也似也謀也往也若也又姓晉中經部魏有陳郡丞馮翊如淳注漢書又虜姓後魏書如羅氏後改爲如氏人諸切八|蕠:蕠藘草也亦作茹|𨚴:地名|洳:水名在南郡又人慮切|鴽:䳺也|𨾵:+上同|𥨲〈𡫽〉:假寐也又如與切|茹:恣也相牽引皃也易曰拔茅連茹又虜複姓後魏書普陋茹氏後改爲茹氏又如慮切又而與切
NJQ子魚;且:語辝也說文薦也子魚切又七也切四|蛆:蝍蛆食蛇蟲蜈蚣是也爾雅曰蒺藜蝍蛆郭璞云似蝗大腹長角能食蛇腦|苴:苞苴亦姓漢書貨殖傳有平陵苴氏又音疽|沮:虜複姓有沮渠氏其先世爲匈奴左沮渠遂以官爲氏沮渠蒙遜以後魏天興四年僭號於張掖稱北涼
eJc去魚;虛:說文曰大丘也去魚切又許魚切十二|墟:+上同|𥬔:飯器|袪:袖也舉也|阹:依山谷爲牛馬之圈|椐:木名又音居|胠:腋下又胠篋莊子篇名|魼:比目魚他合切|㠊:㠊崎山路|𢴮:擊也|㭕:板置驢上負物|䒧:草器
SJQ側魚;菹:說文曰酢菜也亦作葅側魚切四|𧄗〈𧗘〉:+上同|䶥:齒不齊皃|沮:人姓世本云沮誦蒼頡作書並黃帝時史官
ZJQ署魚;蜍:蟾蜍也署魚切又音余二|𧄔:似薯蕷而大或作稌
MJQ女余;袽:易曰繻有衣袽女余切又音如六|帤:幡巾|𣭠:犬多毛也|蒘:藸蒘草名|𣖹:藸𣖹杷名|挐:牽引
#虞
gKs遇俱;虞:度也說文曰騶虞仁獸白虎黑文尾長於身不食生物俗作𩦢又周禮有山虞澤虞掌山澤之官也亦姓出會稽濟陽二望風俗通云凡氏之興九事一氏於號唐虞夏殷是也遇俱切二十|𩦢:+俗見上注|愚:愚惷說文曰戇也从心禺禺母猴屬獸之愚者|娛:娛樂|湡:齊藪名亦作隅爾雅曰齊有海湡又水名在襄國|堣:堣夷日所出處書亦作嵎|𪃍:鳥名狀如梟人面四目而有耳見則天下大旱出山海經|嵎:山名在吳|髃:骨名在膊前又五苟切|禺:番禺縣在南海亦姓出姓苑本又音遇母猴屬也|隅:角也陬也|䴁:鳥似禿鶖|鰅:魚名有文出樂浪|鍝:鋸也|澞:爾雅曰山來水澗陵夾水澞|𧍪:搜神記曰𧑒𧍪似蟬而長味辛美可食一名青蚨異物志云𧑒𧍪子如蠶子著草葉得其子母自飛來就之|㷒:拔器煑食|齵:齵齒重生|鸆:鸅鸆一名婟澤|𨜖:地名
TKg測隅;芻:芻豢說文云刈草也俗作蒭亦姓出何氏姓苑測隅切二|犓:養牛曰犓
DKM武夫;無:有無也亦漢複姓二氏楚熊渠之後號無庸其後爲氏又有無鉤氏出自楚姓武夫切二十一|毋:止之辝亦姓母丘或爲母氏又漢複姓八氏漢書貨殖傳有母鹽氏巨富齊母鹽邑大夫之後漢有執金吾東海母將隆將作大匠母兵興風俗通有樂安母車伯奇爲下邳相有主簿步邵南時人稱母車府君步主簿何氏姓苑有母終氏左傳魯大夫兹母還晉大夫綦母張漢書有巨母霸王莽改爲巨母氏|瞴:瞴瞜又亡撫切|膴:無骨腊又荒烏亡甫二切|蕪:荒蕪|誣:誣枉|巫:巫覡周禮春官曰司巫掌羣巫之政令若國大旱則帥巫而舞雩亦山名又姓風俗通云氏於事巫卜陶匠是也漢有冀州刺史巫捷|莁:莁荑|璑:三采玉|𨼊:地名在弘農|䉑:黑皮竹也|鷡:鷡鴽鳥名|𦌬:罟屬又音武|蝥:爾雅云鼅鼄鼄蝥又音牟|𢜮:爾雅云愛也又音武|无:虛无之道又漢複姓左傳莒有大夫无婁修胡|𢃀:嵌空之皃|譕:譕誘詞也|墲:冢也|鵐:鳥名雀屬|憮:空也又音武|䍢:雉網也
kKs羽俱;于:曰也於也說文本作亏凡從于者作亏同又姓周武王子邘叔子孫以國爲氏其後去邑單爲于漢有丞相東海于定國又望出河南者即後魏書万忸于氏後改爲于氏凡諸姓望在後而稱河南者皆虜姓後魏孝文詔南遷者死不得還北即葬洛陽故虜姓皆稱河南焉又漢複姓五氏後漢特進漁陽鮮于輔袁紹大將軍淳于瓊劉元海太史令宣于修之何氏姓苑有多于氏鬬于氏羽俱切二十|迂:遠也曲也又憂俱切|盂:盤盂說文曰飯器也又姓左傳晉有盂丙|邘:地名在河內又姓漢有邘侯爲上谷太守|雩:請雨祭名又況于切|𦏴:+飛皃說文曰雩羽舞也或从羽同上|竽:笙竽世本曰隨作竽|玗:玉名|芋:草盛皃又王遇切|汙:水名又屋孤烏故二切|䣿:宴也|杅:因杅匈奴地名|釪:錞釪形如鐘以和鼓|𧘘:袌衣|骬:𩩲骭缺盆骨也|𠌶:說文云草木華也本音吁|謣:妄言|䩒:車環靼也|䢓:窻䢓牀也|𦱃:葅𦱃似韭
iKs況于;訏:大也況于切二十|吁:歎也|雩:雩婁古縣名在廬江|欨:焁欨一曰笑意又況字切|㽳:病也|盱:舉目又盱眙縣在楚州|𧙆:大袑衣也|𥈈:𥈈瞜笑皃|姁:姁媮美態|𦀒:殷冠名又音詡|扜:說文云指麾也又憶俱切|𠌶:草木華也|荂:+上同又音敷|𢖳:憂也|䣿:宴也|旴:日始出皃|䩒:䩒靼|㰭:㰭樂|虖:虎吼又虎乎切|𣚏:臿屬又矩于切
fKs其俱;衢:街衢爾雅曰四達謂之衢其俱切三十六|劬:勞也|軥:車軶|氍:聲類曰氍毹毛席也風俗文云織毛褥謂之氍毹亦作𣰠|眗〈胊〉:䀯也一曰屈也亦山名在東海又姓出姓苑|䧁:地名在河東|臞:瘠也|癯:+上同|鴝:鴝鵒亦作鸜周禮曰鸜鵒不踰濟|鸜:+上同亦鸜鵲又漢複姓莊子有鸜鵲子|灈:水名在汝南|躣:行皃楚詞曰右蒼龍之躣躣|忂:+上同|𩢳:馬左足白爾雅云馬後足皆白本作翑|鼩:鼱鼩小鼠|蘧:蘧麥又巨居切|斪:鉏屬|句:冤句縣名在曹州又九遇古侯二切|蠷:蠷螋蟲|瞿:鷹隼視也又姓王僧孺百家譜曰裴桃兒取蒼梧瞿寶女又有瞿曇氏西國姓又九遇切|欋:釋名曰齊魯閒謂四齒杷爲欋|葋:爾雅云葋艼熒|翵:鳥羽|𦐛:+上同|蚼:蚼蛘蚍蜉|𪓞:𪓷屬說文云頭有兩角出遼東亦作𪓟𪓷音奚|𧾱:走顧之皃|䞤:+上同|𠣪:脯名|絇:履頭飾也|𡱺:+上同|𥃔:聲類云樹種也|𥗫:磫𥗫青礪|戵:戟屬|鑺:+上同|姁:姁然樂也又況羽切
cKg人朱;儒:柔也人朱切十六|獳:朱獳獸名似狐而魚翼出則國有恐又女侯切|濡:水名出涿郡又霑濡|襦:說文云短衣也俗作𧝄|懦:弱也又乃亂切|嚅:囁嚅多言|鱬:朱鱬魚名魚身人面|𪋯:鹿子又相俞切|嬬:妻名|繻:易曰繻有衣袽亦見周禮注又音須|顬:顳顬耳前動|䞕:火色|臑:嫩耎皃|醹:厚酒又音乳|㼱:柔皮又而兗切|䰰:鬼魅聲䰰䰰不止又乃侯切
QKg相俞;須:意所欲也說文曰面毛也俗作鬚又姓風俗通云太昊之後史記魏有須賈又漢複姓左傳遂人四族有須遂氏又虜複姓匈奴貴姓有須卜氏相俞切十四|鬚:+俗|嬃:女字|𩓣:待也|𥪥:+上同|繻:傳符帛|𢄼:頭𢄼|𪋯:鹿子也又音儒|需:卦名|娶:荀卿子曰閭娶子奢莫之媒也又七句切|緰:衫緰帛也|蕦:蕵蕪別名|鑐:鎖中鑐也|隃:北陵名又式注式朱二切
JKg陟輸;株:木根也陟輸切十一|誅:責也釋名曰罪及餘曰誅如誅大樹枝葉盡落|邾:國名|鼄:鼅鼄網蟲亦作蜘蛛|蛛:+上同|跦:行皃|袾:字統云朱衣曰袾又昌朱切|列:殊殺字從歹歹五割切|㦵:+上同|鴸:鳥名似鴟人首|𪏿:黏皃
KKg敕俱;貙:獸名似貍敕俱切二|𤠾:+俗
ZKg市朱;殊:異也死也市朱切十二|銖:錙銖八銖爲錙二十四銖爲兩|洙:水名在魯|茱:茱萸|㼡:小甖|殳:兵器釋名曰殳殊也長一丈二尺無刃有所撞挃於車上使殊離也詩云伯也執殳又姓舜典有殳折|𢎦:+上同出道書|㸡:㸡𤗬所以遏水|𦤂:八觚杖也|陎:陎𨻻縣名|𠘧:說文云鳥之短羽飛𠘧𠘧也象形|杸:說文曰軍中士所持殳也司馬法曰執羽從杸
lKg羊朱;逾:越也羊朱切四十五|踰:+上同|窬:門邊小竇又穿窬也|臾:善也亦須臾又姓左傳晉大夫臾駢|楰:木名又音庾|腴:肥腴|諛:諂諛|隃:隃麋古縣在扶風|鄃:地名在涿郡又音輸|覦:覬覦欲得|𨵦:窺也|俞:然也荅也說文作俞空中木爲舟也又姓又恥呪切|歈:巴歈歌也|愉:悅也和也樂也|𢋅:邪𢋅舉手相弄或作歋歈|揄:揄揚詭言也又動也說文引也|褕:褕狄后衣又由昭切|瑜:玉名|崳:崳次山在鴈門|㥚:憂也|羭:黑羝|蝓:𧓗蝓蝸牛|榆:木名說文曰白枌也春秋元命包曰三月榆莢落|萸:茱萸|堬:方言云墳堬培塿埰埌塋壟皆冢別名|牏:築垣短版|渝:渝變也亦州名本巴國漢爲巴郡之江州縣梁於巴郡置楚州隋改爲渝州因渝水爲名|媮:靡也又音偷|𤜹:𤜹𤜹呼犬子也|㳛:汙㳛|𤧙:美石次玉|瘉:病也|螸:爾雅云蠭醜螸|蕍:澤蕮|𦺮:草也|䩱:䩱餘也出字林|䜽:變色豆也|萮:䓵萮花皃|𧃠〈蘛〉:+上同|舀:曰也又音由又代兆切|㼶:瓶也|騟:紫馬|𢔢:行皃|𥯮:黑竹|𥔢:石次玉也
eKs豈俱;區:具區吳藪名又禮曰草木茂區萌達注云屈生曰區亦姓後漢末有長沙區星豈俱切八|鰸:魚名出遼東似蝦無足|驅:驅馳也|敺:+古文|嶇:崎嶇|軀:身也|摳:褰裳又苦侯切|䧢:䧢隅不安皃
XKg章俱;朱:赤也說文曰赤心木松柏屬也又姓出沛國義陽吳郡河南四望本自高陽後周封于邾後爲楚所滅子孫乃去邑氏朱焉亦漢複姓莊子有朱泙漫郭象注云朱泙姓也章俱切十|珠:珠玉白虎通曰德至深淵則海出明珠|侏:侏儒短人|絑:繒純赤色|秼〈祩〉:詛也又音注|咮:讋咮多言皃|鴸:鳥名似鴟人首|鮢:似蝦無足|𤝹:𤝹獳|硃:硃研朱砂
OKg七逾;趨:走也七逾切三|趍:俗本音池|鯫:淺鯫小人不耐事皃又士后切
IKg力朱;慺:悅也力朱切又落侯切十六|蔞:蔞蒿又虜姓官氏志云一那蔞氏後改爲蔞氏|氀:毛布|瞜:瞴瞜又落侯切|䱾:魚名|嶁:山頂|䝏:求子豬也又落侯切|㺏:+上同|摟:曳也|鷜:鵱鷜野鵝又落侯切|鏤:屬鏤劒名又盧豆切|䣚:鄉名又落侯切|婁:詩曰弗曳弗婁傳曰婁亦曳也又落侯切|瘻:痀瘻曲脊|𤗬:㸡𤗬所以遏水|膢:飲食祭也冀州八月楚俗二月
CKM防無;扶:扶持也佐也漢三輔有扶風郡扶助也風化也魏爲岐州又扶州在隴右元魏置管同昌怡夷二縣又姓漢有廷尉扶嘉防無切二十六|𢺻〈𢻳〉:+古文|芙:芙蓉|符:符契河圖曰玄女出兵符與黃帝戰蚩尤說文曰符信也漢制以竹長六寸分而相合又姓魯頃公之孫雅仕秦爲符璽令因而氏焉琅邪人也|颫:颫風大風|鳧:野鴨|榑:榑桑海外大桑日所出也|苻:苻鬼目草又姓晉有苻洪武都氐人本姓蒲氏因其孫堅背文有草付之祥改姓苻氏洪子健以晉穆帝永和七年僭号於長安稱秦|蚨:青蚨蟲子母不相離|夫:語助又府符切|𦽏:𦽏茈草也案爾雅曰芍鳧茈不從艹|𣿆:水名|枹:枹罕縣名在河州罕音漢|瓿:甌瓿瓶也|𧥱:𧥱詞|枎:枎疏盛也|坿:白石英也|泭:水上泭漚說文曰編木以渡也本音孚或作𣻜|𣻜:+見上注|𤱽:小畚器也|𣘧:草木子房|𣻥:水名其中有神古人|𢞦:心明|𦑹:飛皃|𦔾〈𥄑〉:望也|玸:玉名
UKg仕于;䅳:稷穰仕于切四|雛:鵷鶵爾雅曰生噣雛謂鳥子能自食俗作𨿊噣音卓|鶵:+籀文|媰:崔子玉清河王誄云惠於媰孀說文曰婦人姙娠也本側鳩切
SKg莊俱;㑳:纂文云偛㑳小人皃莊俱切偛側洽切二|搊:解也
BKM芳無;敷:散也說文从尃施也芳無切三十六|麩:麥皮也|麱:+上同|孚:信也|𣞒:木名|郛:郛郭|鄜:鄜州漢鄜縣今鄜城是隋改作鄜州|鋪:又普胡切|筟:織緯者|俘:囚也|痡:病也|殍:餓死|怤:思也悅也|䎔:翮下羽也|𧀮:花葉布也|孵:卵化|豧:豕息|尃:布也|䱐:魚名|罦:車上網以捕鳥|稃:穀皮|𥹃:+上同|莩:漢書云非有葭莩之親張晏云莩者葭中白皮|泭:小木栰也說文云編木以渡也|郙:鄉名又云亭名在汝南又方矩切|㕊:石閒見也|桴:屋棟又音浮|䒀:䒀艇船也|㩤:張也|姇:姇悅|荂:華榮之皃又音吁|紨:布也又細紬也|䓵:䓵萮花皃|㲗:毛解|䓏:花盛|秿:禾穳也又扶甫切
NKg子于;諏:謀也子于切又子侯切七|㖩:𡄑㖩不廉|𡸨:𡸨嵎|娵:娵觜星名|陬:陬隅又子侯切|嗺〈嶉〉:高皃|掫:擊也又子侯切
AKM甫無;跗:足上也甫無切二十一|趺:+上同又跏趺大坐|膚:皮膚又美也傅也|肤:+上同|邞:古縣名在琅邪|鈇:鈇鉞|衭:衣前襟|㠸:+上同|玞:珷玞美石次玉|𩿧:䳤𩿧鳥名三首六足六目三翼|𧀴:地𧀴藥名|簠:簠簋祭器又方羽切|夫:丈夫又羌複姓後秦建威將軍夫蒙大羌|鳺:䳕鳩鳥|柎:攔足|扶:公羊傳云扶寸而合注云側手曰扶案指曰寸|𩬙:𩬙髻本也|𩵩:𩵩鯕魚名|䄮:里䄮玉篇云再生稻也|䃿:祭名|妋:玉篇云貪皃
hKs憶俱;紆:縈也曲也詘也勞也又姓後秦有肥鄉侯始平紆邈憶俱切十二|䩒:鞶革又音于|陓:陽陓澤名|扜:說文云指麾也|䩽:鞬也|䙔:編枲頭衣又烏侯切|蓲:草名又去鳩烏侯二切|迂:曲也又音于|䣿:能者飲不能者止也又音于|㝼:盤旋|虶:蚰蜓別名|䨕:䨕注雨皃
aKg式朱;輸:盡也寫也墮也說文曰委輸也式朱切又式注切三|鄃:縣名在貝州|隃:北陵名又相俞式注二切
YKg昌朱;樞:本也爾雅曰樞謂之椳郭璞云門戶扉樞也昌朱切五|姝:美好|𩪍:𩪍骨|袾:朱衣|䇬:䇬策
LKg直誅;廚:說文曰庖屋也俗作廚直誅切五|躕:踟躕行不進皃|趎:人名莊子有南榮趎|幮:帳也似廚形也出陸該字林|裯:襌衣也又直休切
dKs舉朱;拘:執也舉朱切十四|駒:馬駒|䀠:左右視也|眗:+上同|岣:岣嶁衡山別名|㪺:挹也酌也|𨞜:+上同|捄:盛土詩云捄之陾陾|跔:手足寒也|鮈:𩶭鮈魚名|俱:皆也具也又姓南涼錄有將軍俱延|痀:曲脊|𥇛:說文目邪也|𥗫:磫𥗫礪石
VKg山芻;毹:氍毹也山芻切四|㡏:裂繒|橾:說文曰車轂中空也|螋:蠷螋蟲又所留切
#模
DLA莫胡;模:法也形也規也莫胡切十二|橅:+上同出漢書|摸:以手摸也亦作摹又音莫|嫫:嫫母黃帝妻皃甚醜亦作𡠜|㡔:車衡上衣|𨡭:𨡭䤅榆子醬也䤅大胡切|謨:謀也亦作謩|𠻚:+古文|墲:規墓度地曰墲|无:南无出釋典又音無|䉑:竹名|膜:膜拜胡禮拜也
CLA薄胡;酺:大酺飲酒作樂周禮注云蓋亦爲壇位如雩禜云族長無飲酒之禮因祭酺而與其民以長幼相獻酬焉又漢律禁三人以上羣飲酒故賜酺得會聚飲食也薄胡切十|匍:匍匐|蜅:蛤蜅|荹:荹攎收亂草也|樸:樸𠟼縣名在武威𠟼音還|菩:梵言菩提漢言王道|䔕:膊魚亦雉有䔕𠟼也|蒲:草名似藺可以爲席亦州名舜所都蒲坂秦爲河東郡後魏爲雍州又改爲秦州周改爲蒲州因蒲坂以爲名又姓風俗通漢有詹事蒲昌又苻洪之先家池中蒲生長五丈如竹形時咸謂之蒲家因以爲氏又漢複姓有蒲姑蒲城蒲圃三氏出何氏姓苑|蒱:摴蒱戲也博物志曰老子入胡作摴蒱|䈻:竹笪沈水取魚之具
jLA戶吳;胡:何也又胡虜說文曰牛頷垂也亦姓出安定新蔡二望又漢複姓二氏齊宣王母弟別封母鄉遠本胡公近娶母邑故爲胡母氏又胡公之後有公子非因以胡非爲氏又虜複姓南涼錄禿髮壽闐之母姓胡掖氏戶吳切三十|𩑶:牛頷垂也|𠴱:+上同|壺:酒器也禮記投壺篇云壺頸脩七寸腹脩五寸口徑三寸半容斗五升亦姓風俗通云漢有諫議大夫壺遂|狐:狐狢說文曰妖獸也鬼所乘有三德其色中和小前豐後死則首丘又姓左傳晉有狐氏代爲卿大夫|瓳:㽃瓳博雅曰㼾甎也|餬:寄食又糜也使餬其口於四方是也或作𩚩|瑚:瑚璉|湖:江湖廣曰湖也|鶘:鵜鶘鳥名|猢:獑獸名似猨|醐:醍醐酥屬|𪏻:黏也|䊀:+上同|𪍒:-|糊:+並俗|弧:弓也|乎:極也辝也|𠂞:+古文|𪕱:𪖎𪕱似猨身白𦝫手有長白毛善超坂絕巖也亦作𪕮|瓠:瓠𤬜瓢也又音護|葫:葫瓜又草名|㾰:㾰𤻙物在喉中|魱:當魱魚名|箶:箶簏箭室又竹名|䉉:稜也|𥶜:𥶜被也出韻略|𧛞:𧛞䘸|㯛:棗名也大而銳上者本作壺見爾雅|虖:歎也
dLA古胡;孤:孤子又虜複姓有獨孤溫孤步鹿孤步六孤乙速孤氏古胡切二十八|苽:說文曰雕苽一名蔣也|菰:+上同|胍:胍𦘴大腹|𡗷:大皃|姑:舅姑又父之姊妹也|辜:罪也|呱:啼聲|泒:水在鴈門|酤:酤酒又胡五昆互二切|觚:酒爵|蛄:螻蛄蟲|箛:竹名|鴣:鷓鴣鳥|橭:木名|𠷞:漢書越王巫𠷞祠在雲陽亦小兒病鬼也|沽:水名在高密|柧:枛棱|𨬟:字林曰𨮓𨬟魯矢左傳作僕姑|䉉:方也本亦作觚|𧇡:𧇡息禮記作姑|盬:陳楚人謂鹽池爲盬出方言又音古|嫴:說文曰保任也|罛:魚罟|軱:大骨也出莊子又盤骨|箍:以篾束物出異字苑|䐻:䐻脯|㼋:瓜也
GLA同都;徒:黨也又步行也空也隷也同都切三十一|𨑒:+上同|屠:殺也裂也刳也尸子曰屠者割𠟼知牛之長少史記樊噲少屠狗亦姓左傳晉有屠岸賈又音除|瘏:病也|塗:塗泥也路也亦姓風俗通云漢諫議大夫塗惲|途:道也|酴:酒名|駼:騊駼馬山海經曰北海有獸狀如馬名曰騊駼|𤙛:黃牛虎文|鵌:鳥名與鼠同穴|涂:水名在益州|梌:木名|㭸:+上同|荼:苦菜|圖:爾雅曰謀也說文曰畫計難也|啚:+俗本音鄙|廜:廜㢝草菴通俗文曰屋平曰廜㢝|䣝:鄉名|菟:菟丘地名又音吐|捈:捈引|䣄:邾下邑地名|䅷:穗也|嵞:嵞山古國名禹所娶也說文云會稽山也一曰九江當嵞也亦作峹又書作塗|峹:+上同|𣘻:楸木別名|鍍:以金飾物又音度|䤅:𨡭䤅醬也|蒤:虎杖|䖘:烏䖘楚謂虎也左傳作於菟|鷵:爾雅曰鸄鶶鷵郭璞云似烏蒼白色|筡:爾雅曰簢筡中言其中空竹類
HLA乃都;奴:人之下也乃都切七|㚢:+古文|砮:礪也|駑:体馬字林曰駘也|帑:說文曰金幣所藏也又他朗切|孥:妻孥書傳云孥子也|笯:鳥籠
iLA荒烏;呼:喚也說文曰外息也又姓列仙傳有仙人呼子先又虜複姓二氏前趙錄匈奴貴姓有呼延氏後漢書匈奴四姓有呼衍氏荒烏切又火故切十七|嘑:哮嘑周禮曰雞人掌大祭祀夜嘑旦以嘂百官|虖:姓也說文曰哮虖也|𧦝:亦喚也|歑:溫吹氣息也|戲:+古文呼字|謼:大叫又火故切|膴:無骨腊又音無|幠:大也|葫:大蒜也張騫使大宛所得之食之損人目|恗:怯也|軤:姓也|虍:字林云虎文也|苸:草多|雐:鳥名|䰧:鬼皃|滹:滹池水名周禮作虖池
gLA五乎;吾:我也漢改中尉爲執金吾吾御也執金革以御非常亦姓漢有廣陵令吾扈又漢複姓五氏鄭公子有食采於徐吾之鄉後以爲氏左傳有鍾吾子其後氏焉昆吾氏昆吾國之後由吾氏秦相由余之後古有肩吾子隱者五乎切二十一|鼯:似鼠一曰飛生亦作𪁙𧋋|𪁙:-|𧋋:+並上同|吳:吳越又姓本自太伯之後始封於吳因以命氏後季札避國子孫家于魯衛之閒今望在濮陽|浯:水名|䓊:草名似艾|㹳:猿屬|㻍:琨㻍美石|珸:+上同|蜈:蜈蚣|郚:鄉名在東莞|齬:齟齬又音語|鯃:魚名|娪:美女|鋘:錕鋘山名出金色赤如火作刀可切玉出越絕書|梧:梧桐木名又姓|峿:區峿山名|麌:牝麕也又音俁|𦨼:船名|祦:福也
NLA則吾;租:積也稅也則吾切二|蒩:茅藉封諸侯蒩以茅又子余切
ILA落胡;盧:說文曰飯器也亦姓姜姓之後封於盧以國爲氏出范陽又漢複姓八氏列子有長盧子孟子有屋盧子著書古尊盧氏後氏焉古蒲盧胥善弋亦姜姓左傳齊大夫盧蒲嫳後漢諫議大夫東郡索盧放何氏姓苑云盧妃氏濟陽人又有湛盧氏亦虜複姓五氏周書豆盧寧傳云其先慕容氏支庶後魏書有吐盧沓盧呼盧東盧等氏又三字姓有吐伏盧奚計盧莫胡盧三氏俗作盧落胡切三十四|鑪:酒盆又鑪冶也|壚:土黑而疏|籚:籚西竹出會稽|蘆:蘆葦之未秀者又蘆菔菜名亦虜姓後魏書莫蘆氏後改爲蘆氏|顱:頭顱|髗:+上同|鱸:魚名|攎:攎斂|櫨:𣝍櫨柱也又木名|轤:𨏔轤圓轉木也|黸:黑甚|獹:韓獹犬名|鸕:鸕鶿|艫:舟後|纑:布縷|瀘:水名亦州名在蜀|瓐:玉名|爐:火牀出玉篇漢官典職曰尚書郎給女史二人著潔衣服執香爐燒熏|玈:黑弓也|𢐸:+俗|㢚:廡也又力古切|𤮧:酒器|嚧:呼豬聲也|矑:目童子也|㿖:集略云癰類|㭔:黃㭔木可染也|䰕:䰕鬣|𧇄:飯器說文曰缻也|𧆨:+上同|罏:+籀文|蠦:蠦蜰一名蜚又名蝜蠜|㪭:㪆也㪆音邸|𦿊:𦿊會藥名
QLA素姑;蘇:紫蘇草也蘇木也滿也悞也又姓出扶風武邑二望素姑切四|穌:息也舒悅也死而更生也|㢝:廜㢝草菴又廜㢝酒元日飲之可除瘟氣|酥:酥酪
PLA昨胡;徂:往也昨胡切四|䢐:+上同|殂:死也|𣨐:+古文
hLA哀都;烏:安也語辝也說文曰孝烏小也爾雅曰純黑而返哺者謂之烏小而不返哺者謂之鵶又姓左傳齊大夫烏枝鳴又虜姓周上開府烏丸泥又虜三字姓北齊有烏那羅愛後魏書有烏石蘭氏烏落蘭氏哀都切二十一|嗚:嗚呼|洿:說文曰濁水不流者|汚:+上同又一故切|杇:泥鏝|圬:-|釫:+並上同|鰞:鰞鰂魚月令云九月有寒烏入水化爲烏鰂魚|歍:口相就也|鎢:鎢錥溫器|𢎰:滿挽弓有所向|於:古作於戲今作嗚呼|瑦:美石|鄔:縣名又音塢|盓:盤盓旋流也又憂俱切|螐:蚅螐蠋蟲也大如指白色|惡:安也|扝:引也|𦶀:𦶀蓲荻也|㮧:㮧椑青柹|鴮:鴮鸅鵜鶘別名俗謂之掏河也
ALA博孤;逋:逋懸也博孤切十三|餔:說文云申時食也音步|𥂈:+籀文|晡:申時|庯:屋上平|陠:+上同|鵏:鵏敊鳥名|𧻷:䞮𧻷伏地|峬:峬峭好形皃出字林|誧:諫也|秿:刈禾治秿|鯆:鯆䱐魚名亦作𩶉|抪:展舒也又布也
eLA苦胡;枯:枯朽也苦胡切十一|刳:剖破又判也屠也|扝:揚也|郀:地名|軲:車也又山名亦姓出字統|㱠:㱠瘁說文枯也|跍:跍蹲皃|挎:空也坼也|𢎰:又汙乎切|橭:木四布也|鮬:婢妾魚名
OLA倉胡;麤:說文云行超遠也又字統云警防也鹿之性相背而食慮人獸之害也故從三鹿倉胡切六|麁:疎也大也物不精也本亦作麤|𧆓:說文云草履也|𥼡:米不精也|觕:公羊傳曰觕者曰侵精者曰伐|𤿚:皮皵惡也
FLA他胡;㻌:美玉他胡切十二|稌:稻也又他古切|悇:廣雅云懷憂皃|嶀:山名|㻯:玉名|𡸂:山名|庩:庯庩屋不平也|䞮:𧻷䞮伏地|梌:銳也|㻬:㻬琈玉名|捈:臥引|䩣:𩍿䩣屧
ELA當孤;都:都猶摠也尚書大傳十邑爲都帝王世紀曰天子所宮曰都又姓蔡有臨漢侯都稽何氏姓苑云今吳興人當孤切七|𥳉:竹名|闍:闉闍城上重門又市遮切|𦘴:𦘴胍大腹|𧷿:賭勝出新字林|醏:𨣱醏醬也|䩲:折皮具牛牽船出通俗文
BLA普胡;𥠵:豆𥠵也普胡切十二|鋪:鋪設也陳也布又音孚|鯆:魚名又江豚別名天欲風則見|𩹲:+上同|𨁏:馬蹀跡也|痡:病也又音孚|誧:諫也又音普|𧱹:豕名|陠:衺也|墲:規墓地也|䮒:馬名|𢼹:𢾱𢼹屋壞
#齊
PMQ徂奚;齊:整也中也莊也好也疾也等也亦州名春秋時齊國秦爲郡後魏置州因齊地以名之又姓風俗通氏姓篇序曰四氏於國齊魯宋衛是也徂奚切九|臍:膍臍說文作𣬈𪗇|麡:麡狼似麋而角向前入林則挂其角故常在淺草中逐入林則搏之出異物志又隮豺二音|蠐:蠐螬蟲|𪗍:等也|懠:詩云天之方懠懠怒也又音劑|䶒:好皃又子兮側皆二切|癠:病也又音劑|𨥦:利也又子兮切
IMQ郎奚;黎:眾也又姓黎侯國之後郎奚切二十一|犁:墾田器亦耕也山海經曰后稷之孫叔均所作魏略曰皇甫隆爲燉煌太守教民作樓犁也|𤛿:+上同|莉:芘莉織荊|黧:黑而黃也|藜:藜藿|鯬:鯬鯠|𦃇:縴𦃇惡絮|盠:以瓢爲飲器也|邌:徐行皃|𨛫:亭名在上黨|廲:廲廔綺窻|蔾:蔾蘆藥名|筣:竹名|驪:穆天子駿馬名盜驪綠耳又力知切|瓈:玻瓈寶玉|𥌛:𥌛視|𩧋:馬屬亦作𩥴|㦒:㦒忚欺慢之語出方言|謧:弄言又力支切|𨿯:𨿯黃鳥
OMQ七稽;妻:齊也七稽切又七計切十|萋:草盛皃|淒:雲皃又千弟切|凄:寒也|悽:悲也痛也|鶈:鳥名|郪:縣名在梓州|緀:緀裴文章相錯皃|齌:說文云炊餔疾本子兮切又才細切|霋:說文云霽謂之霋
EMQ都奚;低:低昂也俛也重也都奚切俗作仾二十三|氐:氐羌說文至也|袛:袛裯短衣|磾:漢有金日磾說文云染繒黑石出琅邪山|鞮:革履|腣:腣胿胅腹胿音奚|羝:羝羊|眡:視也|隄:防也|堤:+上同|岻:山名|䧑:纂文云姓也|奃:大也|趆:趨也|𡰖:說文云㝿不能行爲人所引曰𡰖𡰢|鍉:歃血器|柢:木根也又音帝|䐎:𦠓䐎強脂|䚣:獸角不正|𥿄:絲滓|揥:指也|㓳:剅㓳以刀解物|䬫:䬫餬
GMQ杜奚;嗁:泣也說文曰號也杜奚切六十|啼:-|㖒:+並上同|蹏:足也|蹄:+上同|𥶛:竹名|提:提攜|詆:訶也又音底|瑅:玉名|隄:隄封漢書作提|桋:樹之長條|題:書題說文頟也|媞:美好皃爾雅云媞媞安也說文又時尒切諦也一曰妍黠|𧡨:視也說文顯也|綈:厚繒也|罤:兔網|𣹲:研米槌也|𣖅:+上同|締:結又音悌|蕛:爾雅曰蕛苵也郭璞云蕛似稗布地生穢草也或作稊|稊:易曰枯楊生稊稊楊之秀也|𦯔:草也|䬾:餹䬾|醍:醍醐|褆:衣服好皃又是豸二音|鵜:鵜鶘|荑:荑秀|禔:福也|䱱:魚黑色|崹:崥崹山皃|緹:周禮注緹衣古兵服之遺色又音禮|鷤:鷤䳏鳥又音遰|鼶:爾雅曰鼶鼠夏小正曰鼶鼬則穴又音斯|騠:駃騠馬名又丁奚切|折:禮記云吉事欲其折折爾謂安舒貌|䨑:霽雲出字林|銕:字林云鐵名又說文云古鐵字|䱱:魚四足者|䖙:臥也又音梯|𥉘:𥉘視困皃|䬫:字木云寄食|䚣:獸角不正又音低|𢔭:久待|謕:轉語又他兮切|𡰄:㝿行皃|厗:磄厗石也|𪂿:𪂿鴂鳥春三月鳴也|鶙:鶙鵳鳥|𡰖:又音低|蝭:蝭蟧又音帝|𨪉:器也|鴺:鷩鴺山雞名|㡗:㡗帷|銻:鎕銻火齊|鮷:大鱧|趧:趧鞻四夷樂也|𧋘:螗𧋘小蟬|鮧:鮎也|鯷:+上同|䐎〈睼〉:近視也又坐見
AMA邊兮;豍:豆名邊兮切十六|㡙:車㡙|螕:牛蝨|㯅:㯅㯕小樹又樹裁也|𦱔:𦱔麻|蓖:+上同|𦀘:謬也又芳脂切|篦:眉篦|梐:門外行馬又防啓切|𥏠:𥏠𥎬短皃|𨻼:說文曰牢也所以拘罪也|狴:+上同又狴犴獸也|箄:冠飾|鎞:鎞釵|悂:誤也|䚜:橫角牛名
dMQ古奚;雞:說文曰知時畜也易曰巽爲雞古奚切十|鷄:+籀文|稽:考也同也當也留止也又山名亦姓呂氏春秋有秦賢者稽黃|枅:承衡木也|笄:女十有五而笄也|㮷:㮷風扶枃木也|䗗:螢火|卟:字書云問卜也|𥝌:木不長也又音礙|𨪴:堅也
jMQ胡雞;奚:何也說文曰大腹也又東北夷名亦姓夏車正奚仲又虜複姓後魏書有達奚薄奚紇奚吐奚等四氏胡雞切十八|豯:豕生三月|徯:有所望也又胡禮切|㜎:女奴|蹊:徑路|螇:螇螰似蟬|榽:榽蘇木名似檀|騱:馬前足白又驒騱野馬名驒音壇|胿:腣胿|𡗞:獸跡亦邑名在洛陽|郋:里名|𪓷:水蟲|傒:東北夷名|嵇:山名亦姓出譙郡河南二望|兮:語助|鼷:鼠名一名甘口鼠食人及鳥獸至盡皆不痛|蒵:草名|貕:幽州藪澤曰貕養出周禮
hMQ烏奚;鷖:鳧屬烏奚切十二|翳:蔽也又烏計切|𧫦:相然應辝|嫛:人始生曰嫛婗出釋名|黳:小黑|𦎣:黑羊|㙠:塵埃|䃜:美石黑色|黟:說文黑木也丹陽有黟縣|繄:是也辝也又赤黑繒亦戟衣也|䚷:誠也又於米切|𣕁:𣕁㯕弩楔木也
gMQ五稽;倪:莊子云天倪自然之分亦姓後漢有楊州刺史倪諺五稽切十八|蜺:似蟬而小|霓:雌虹又五結五繫二切|郳:郳城在東海|齯:老人齒落復生|婗:嫛婗|輗:車轅端持衡木|棿:+上同|猊:狻猊師子屬一走五百里|麑:+上同|貎:亦同|鯢:雌鯨|兒:姓也漢御史大夫兒寬千乘人|䘽:衣裗謂之䘽也又妍啓切|𠆵:𠆵㑮佯不知皃|觬:角不正皃又研啓切|𣕁:𣕁㯕弩楔|㪒:㪏㪒毀又五禮切
iMQ呼雞;醯:酢味也俗作䤈呼雞切六|䒊:痛聲|𦫬:黃病色也|㡗:𢅰㡗赤紙出埤蒼|橀:橀木名|忚:欺慢之皃
QMQ先稽;西:秋方說文曰鳥在巢上也日在西方而鳥西故因以爲東西之西篆文作㢴象形亦州名本漢車師國之地至貞觀討平以其地爲西州亦姓又漢複姓十一氏左傳秦帥西乞術宋大夫西鉏吾西鄉錯出世本又黃帝娶西陵氏爲妃名纍祖史記魏文侯鄴令西門豹周末分爲東西二周武公庶子西周爲氏晉有北海西郭陽何承天以爲西朝名士慕容廆以北平西方虔爲股肱何氏姓苑有西野氏西宮氏王符潛夫論姓氏志曰如有東門西郭南宮北郭皆是因居也先稽切十六|卤:+籀文|𠧪〈𠧧〉:+古文|棲:鳥棲說文曰或从木妻|栖:+上同|㽄:瓦破聲|犀:犀牛似豕角生鼻上又姓秦有犀首|嘶:馬嘶|撕:提撕|㾷:痠㾷疼痛亦作廝|𤺊:+上同|㯕:椑㯕|屖:瓠屖說文遟也|𧬊:悲聲|粞:碎米|𠞂:𠞮𠞂
FMQ土雞;梯:說文云木階也土雞切九|睇:視也又徒計切|鷈:𪇊鷈似鳧而小|𠥸:臥也|䖙:+上同|㔸:匾㔸薄也|𨁃:𨁃蹋|謕:轉相誘語|𩤽:匾㔸
CMA部迷;鼙:騎上鼓釋名曰鼙裨也裨助鼓節也呂氏春秋曰帝嚳令人作鼙鼓之樂也部迷切七|鞞:+上同|椑:圓榼漢書云美酒一椑|膍:膍臍說文曰牛百葉也一曰鳥膍胵也亦作肶又音毗|崥:崥崹|㼰:瓦器|笓:取蝦竹器
BMA匹迷;磇:磇霜石藥出道書匹迷切七|𨻼:牢也所以拘罪人也|𠜱:𠜱斫|𪄆:𪄆鵊鳥名|錍:錍斧又方支切|批:擊也推也轉也示也|鈚:鈚箭
NMQ祖稽;齎:持也付也遺也裝也送也祖稽切十五|賷:+俗|𩐒〈䪡〉:薑蒜爲之|齏:+上同|𧆌:𧆌菜俗|𨥦:利也又徂兮切|櫅:櫅榆堪作車轂爾雅云白棗也|䂑:𥏠䂑|擠:排擠|齌:炊餔疾也又才細切|躋:登也升也又音霽|隮:+上同|麡:又音齊音豺義見齊字中|𢥎:𢥎疑人方言云吳人云之|啙:弱也又此比切
DMA莫兮;迷:惑也莫兮切六|𡝡:齊人呼母|䤍:醭䤍醬上白也|麛:鹿子|𧠠:病人視皃|𪓬:𪓬𪓹似龜堪啖多膏
HMQ奴低;泥:水和土也說文云水出北地郁郅北蠻中詩疏云泥中衛之小邑又姓出姓苑奴低切又奴計切四|埿:塗也俗|屔:受水丘也爾雅曰水潦所止爲屔丘郭璞云頂上汚下者亦作泥|臡:雜骨醬也
eMQ苦奚;谿:爾雅曰水注川曰谿苦奚切八|嵠:-|溪:-|磎:+並上同|鸂:鸂鷘水鳥|檕:爾雅云朹檕梅子如小柰也|螇:土螽似蝗|𤳤:小畚
dMg古攜;圭:圭璧說文曰瑞玉也上圜下方公執桓圭九寸侯執信圭伯執躬圭皆七寸子執穀璧男執蒲璧皆五寸周禮以青圭禮東方又孟子曰六十四黍爲一王十圭爲一合古攜切十五|珪:+古文|邽:下邽縣在馮翊上邽縣在隴西|閨:閨閤|袿:釋名曰婦人上服曰袿廣雅曰袿長襦也|窐:甑下孔楚詞云珪璋雜於甑窐又音攜亦作𤮰|鮭:魚名又音奎|𪊧:鹿屬|洼:姓也漢有大鴻臚洼丹又音哇|𨾴:𨾴谷名|𡌲:𡌲𧯠裂也|胿:腣胿|𦓯:田器|㰪:邪也又紆佳切|茥:缺盆草也又音睽
eMg苦圭;睽:異也乖也外也說文云目少睛苦圭切十五|奎:星名|湀:泉水通川又古比切|刲:割剌又作𠝥|𠝥:+上同|茥:缺盆草|䯓:肩骨|聧:說文云耳不相聽方言云聾之甚者秦晉之閒謂之聧|鮭:漢複姓漢有博士鮭陽鴻|䖯:蠆也|蝰:蛹也|㨒:中鉤|楏:橿也|藈:藈𤬏亦作𤬉|𡐠:說文曰盾握也
jMg戶圭;攜:提也離也又姓出何氏姓苑戶圭切二十三|携:+俗|蠵:大龜|鑴:大鑊|窐:甑下孔|𩰳:+上同|畦:菜畦|驨:似馬一角|｛𪈥｝【澤存堂本衍字】:-子𪈥鳥出蜀中|巂:+上同又子巂鳥出蜀中|酅:地名在東安平|𢥘:離心也|𦋅:姓也梁四公子𦋅闖之後|𣫴:姓也|𡸔:姓出纂文|纗:說文曰維綱中繩也|讗:說文曰自是也|㔒:廣雅云挑剜刲㔒剈|䙵:姓出說文|黊:說文云鮮明黃也|𡰢:𡰖𡰢也|眭:目深惡視|觿:角錐童子所佩又儇規切|䀘:䀘能視也
cNQ人兮;臡:有骨醢也人兮切又音泥一
ZNQ成臡;栘:棠栘木也成臡切又余一以支二切一
hMg烏攜;烓:說文曰行竈也爾雅曰煁烓郭璞云今之三隅竈烏攜切三|𧟼:+上同|𤮰:甑下孔
iMg呼攜;睳:目瞢呼攜切一
#佳
dPQ古膎;佳:善也大也好也古膎切二|街:道也說文云街四通道也風俗通云街攜也離也四出之路攜離而別也
jPQ戶佳;㥟:心不平又恨也戶佳切八|鮭:魚名出吳志|膎:脯也𠟼食肴也|鞵:屩也|鞋:+上同|㨙:挾物|䙎:袖也|榽:榽橀
CPA薄佳;牌:牌牓也薄佳切七|䱝:魚名廣雅云黑鯉謂之䱝|𥱼:大桴曰𥱼|郫:縣名在蜀又音皮|蠯:江東呼蚌長而狹者爲蠯|棑:棑筏又音敗|犤:牛也
dPg古蛙;媧:女媧伏羲之妹古蛙切七|緺:青緺綬也|𧬭:𧬭惰|腡:手理也|蝸:蝸牛小螺|騧:馬淺黃色|歄:歄𣢉
hPg烏媧;蛙:蝦蟆屬烏媧切二|鼃:+上同又戶媧切
ePg苦緺;咼:口戾也苦緺切六|喎:+上同|絓:惡絲|䓙:䓙雜離斜絕|𦹬:𦹬斜|䦱:斜開門國語云䦱門而與之言又王詭切
UPQ士佳;柴:薪也又姓高柴之後士佳切八|祡:祭天燔柴|𪗶:𪗶𪘲齒不正也|茈:茈葫藥名|㧘:積也詩云助我舉㧘|㾹:瘦也|𨌅:連車也一曰卻車抵堂也|查:查郎又士瑕切
TPQ楚佳;釵:婦人岐笄也楚佳切九|靫:鞴靫盛箭室鞴音步|𩑐:頷𩑐頤傍|叉:兩枝也說文曰手指相錯也|芆:鬼芆草名|䐤:䐤腵脯腊|㼮:㼮㼽屑瓦洗器|差:差殊又不齊|𠞊:小矛又㔆𠞊也
iPg火媧;竵:物不正火媧切四|𦶎:舛雜之皃|𠿎:口偏|𩝨:𩝨消食
MPQ㚷佳;䍲:羺䍲胡羊㚷佳切三|掜:掜搦皃|誽:言不正也
gPQ五佳;崖:高崖也五佳切七|涯:水際|啀:犬鬬|𪘲:𪗶𪘲|猚:說文云鳥名又水名在睢陽|厓:山邊|𩂢:雨聲
hPQ於佳;娃:美女皃於佳切五|洼:水名|哇:淫聲|㰪:邪皃又音圭|𠴺〈唲〉:唲嘔小兒言也
VPQ山佳;崽:呼彼之稱山佳切又山皆切三|籭:竹器|諰:語失也又思耳切
iPQ火佳;㗨:笑皃火佳切二|㰨:㰰㰨氣逆病㰰昏狹切
KPQ丑佳;扠:以拳加人亦作搋丑佳切一
DPA莫佳;䁲:視皃莫佳切二|𩍃:𩍃鞵履也
jPg戶媧;鼃:蛙屬戶媧切一
#皆
dQQ古諧;皆:說文作皆俱詞也古諧切十九|偕:俱也|䕸:麻稈|稭:+上同又古八切|喈:鳥聲|階:階級也說文曰階陛釋名曰階梯也如梯之有等差也|𦝨:瘦也|薢:薢茩藥名決明子是也又音懈|荄:草根|痎:瘧疾二日一發|堦:堦砌|楷:說文云木名孔子冢蓋樹也廣志云孔子冢上特多楷樹|鶛:爾雅云鷯鶉其雄鶛|湝:水流皃又戶皆切|街:又音佳|𤭧:牡瓦|𩘅:疾風|蝔:蟲名淮南子曰蝔知雨至蝔蟲大如筆管長三寸代謂之猥彴知天雨則於草木下藏其身又音諧|鍇:䥫也
hQQ乙諧;𢰇:推也亦背負皃乙諧切一
jQQ戶皆;諧:和也合也調也偶也戶皆切九|𩤠:馬性和也|骸:骸骨|瑎:黑石|湝:風雨不止|龤:說文曰樂和龤也|蝔:又音皆|鞋:履也又音膎|䓳:䓳菔草
CQA步皆;排:推排釋名曰彭排軍器也彭帝也在旁排敵御攻也步皆切六|俳:俳優|輫:車箱|牌:又薄佳切|猈:短頭狗也|𩑢:曲頤皃
dQg古懷;乖:睽也離也戾也背也古懷切四|𦮃:+上同|𠦬:說文曰背呂也𦟝字從此|㾩:惡瘡
jQg戶乖;懷:抱也和也來也思也亦州名春秋時野王邑漢爲河內郡武德初於桐崖城置懷州又姓吳志顧雍傳有尚書郎懷敘戶乖切十二|褱:俠也苞也歸也|櫰:爾雅云槐大葉而黑曰櫰|槐:木名又音回|㜳:和也|𪊉:戎狄鹽|㠢:崴㠢不平皃|𤜄:似牛四角人目|淮:水名出桐栢又姓也|褢:說文藏也|𧞷:+上同|瀤:北方水名
eQg苦淮;匯:澤名苦淮切又胡罪切三|㨤:揩摩|㔞:劥㔞人有力也
UQQ士皆;豺:狼屬禮記云仲秋之月豺乃祭獸士皆切四|儕:等也輩也類也|麡:又音齊音隮義見齊字中|𡺵:山名在平林
TQQ楚皆;差:簡也楚皆切又楚宜楚牙楚懈三切二|䞗:起去也
iQg呼懷;虺:虺尵馬病呼懷切又灰毁二音一
LQg杜懷;尵:杜懷切二|𩓬:頭胅也出聲類
DQA莫皆;埋:瘞也藏也莫皆切四|薶:+上同|霾:爾雅曰風而雨土爲霾釋名曰霾晦也如物塵晦之色也|㦟:慧也
SQQ側皆;齋:齋潔也亦莊也敬也經典通用齊也側皆切一
hQg乙皆〖乖〗;崴:崴㠢乙皆切四|碨:碨䃁不平也䃁音鴉|䴜:鹽也亦作𪊉|溾:溾涹穢濁
JQQ卓皆;𪘨:齧也卓皆切二|榸:枯木根出聲類
ITQ賴諧;唻:唱歌聲賴諧切一
eQQ口皆;揩:揩搱摩拭口皆切四|𦂄:木絲|𢔡:俳𢔡行惡|𥻄:米之別名
MQQ諧〈諾〉皆;搱:諧皆切一
VQQ山皆;崽:方言云江湘閒凡言是子謂之崽自高而侮人也山皆切又山佳切二|𥳧:𥳧籮古以玉爲柱故字從玉今俗作簁
gQQ擬皆;𩂢:雨聲擬皆切二|娾:醜女皃
KQQ丑皆;搋:以拳加物丑皆切一
iQQ喜皆;𢓬〈俙〉:訟也喜皆切一
IQg力懷;䐯:䐯膗形皃惡力懷切一
UQg仕懷;膗:仕懷切二|𢶀:𢶀倒損出方言
#灰
iSg呼恢;灰:說文曰死火也淮南子云女媧積蘆灰而止淫水呼恢切六|䖶:豕掘地也|鼿:+上同|豗:相豗擊|㾯:馬病|虺:虺尵
eSg苦回;恢:大也苦回切八|詼:詼調|悝:病也憂也一曰悲也亦大也又音里|魁:魁帥一曰北斗星|𥲖〈䈛〉:箭竹|㷇:多也|顝:大頭|盔:盔器盂盛者也
hSg烏恢;隈:水曲也烏恢切十一|煨:煻煨火|䋿:五色絲飾|渨:渨沒|椳:戶樞|偎:愛也亦國名|䬐:風低皃|揋:揋掎|𧤖:角曲中也|葨:山草|鰃:魚也
jSg戶恢;回:違也轉也邪也又回中地名亦姓古賢者方回之後戶恢切十三|洄:逆流|迴:還也|槐:木名五經通義曰士之冢樹槐春秋說題辝曰槐木者虛星之精也又姓魯大夫富槐之後|徊:徘徊|瑰:玟瑰火齊珠也又古回切|蚘:人腹中長蟲|蛕:+上同|佪:玉篇云佪佪惛也|烠:光色|𤜡:鄉名在睢陽|𩢱:馬名|茴:茴香草名
DSA莫杯;枚:枝也亦姓漢有淮南枚乘莫杯切十五|梅:果名又姓出汝南本自子姓殷有梅伯爲紂所醢漢有梅鋗|媒:媒衒說文曰謀也謀合二姓也|玟:玟瑰|煤:炱煤灰集屋也炱杜來切|脢:脊側之𠟼又亡代切|脄:+上同|腜:孕始兆也|禖:郊禖求子祭也|䍙:雉網|莓:莓莓美田也|塺:塵也|鋂:大鐶詩傳云一環貫二|䊈:酒母|䤂:醋之別名
dSg公回;傀:大皃又美也盛也偉也亦怪異公回切十|𤪿:+上同|𠐤:亦同|瑰:瓊瑰石次玉又音回|瓌:+上同|鞼:說文云韋繡也又求位切|櫰:山海經云中曲山有木如棠而圓葉赤實如木瓜食之多力又音懷|膭:肥皃|䐩:畜胎|䕇:菜名又乎罪切
ISg魯回;雷:說文作靁云陰陽薄動靁雨生物者也又姓後漢有雷義魯回切十三|𩂩:+古文|儡:儡同|㔣:勉也又盧對切|瓃:玉器|櫑:說文曰龜目酒尊刻木作雲雷之象象施不窮也|罍:+上同|鑘:劒首飾也亦作櫑|𦌵:百囊魚網|鐳:瓶也壼也|𤮚:屋楝瓦也|畾:田閒|轠:轠轤不絕
GSg杜回;穨:暴風也杜回切十三|頹:禿|㿉:陰病|隤:下墜也|墤:+上同|㢈:壓也|魋:獸似熊而小又人名|尵:虺尵|蘈:爾雅曰藬牛蘈郭璞云高尺餘許方莖葉長而銳有穗穗閒有華紫縹色|𧮓:譟也|𧝋:棺覆|蹪:躓仆|𤗴:𤗯𤗴屋破狀
OSg倉回;崔:姓也齊丁公之子食采於崔因以爲氏出清河博陵二望倉回切六|催:迫也|縗:喪衣長六寸博四寸亦作衰|𨻵:𨻵崩隤也|𢕘:行急皃|𧽠:逼也
ESg都回;磓:落也亦作塠都回切十五|塠:+上同|頧:母頧夏冠名禮記作追|䭔:餅也|堆:聚土|鴭:雀屬|𢈹:𢈹撲物也亦作𢮒|鎚:治玉也周禮作追|搥:摘也|䜃:+上同|嵟:高也|𩈜:䩇𩈜醜面|𠂤:說文曰小阜也|敦:詩曰敦彼獨宿|𡏩:𡏩坐皃出聲譜
QSg素回;𤗯:𤗯𤗴素回切六|挼:擊也|䪎:鞍邊帶也|毸:毰毸鳳舞出楚詞|嗺:嗺送歌|蓑:蓑蓑蘂下垂皃本又音莎
PSg昨回;摧:折也阻也昨回切五|崔:崔嵬又音催|慛:傷也憂也|槯:木名堪作杖|檇:木有所擣也
CSA薄回;裴:衣長皃又姓伯益之後封于𨛬鄉因以爲氏後徙封解邑乃去邑從衣至燉煌太守裴遵始自雲中徙居河東本亦作裵薄回切十二|徘:徘徊|培:益也隄也助也治也隨也重也|陪:陪廁也|𨛬:鄉名在聞喜|䣙:鄉名在扶風|婄:婦人皃|棓:姓也前漢爰盎之棓生所問占又龐項切|毰:毰毸鳳舞|𤗏:版也|𩑢:曲頤也又音牌|輫:車箱
ASA布回;桮:說文曰㔶也布回切三|杯:+上同|盃:+俗
BSA芳杯;肧:懷胎一月芳杯切八|坯:未燒瓦也|㾦:弱也|醅:酒未漉也|衃:說文曰凝血也|𩵣:魚名|𤬃:瓜𤬃|抔:披抔
gSg五灰;鮠:魚名似鮎五灰切五|桅:小船上檣竿也|嵬:崔嵬|磑:磨也又五內切|峞:高皃
FSg他回;𨌴:車盛皃他回切七|𨋱:+上同|㷟:㷟燖毛出字林|蓷:草名|推:又昌隹切|藬:牛蘈草也|㞜:履屬有頸曰㞜
HSg乃回;𢅼〈𢆃〉:古之善塗者乃回切三|捼:手摩物也又如和切|𨡌:一𨡌飯出字林
NSg臧回;嗺:字書云口嗺頹臧回切四|脧:赤子陰也|䘒:+上同見老子|𡱥:+上同出聲類
#咍
iTQ呼來;咍:笑也呼來切三|㾂:病也|𨸜:㱾𨸜笑聲也
eTQ苦哀;開:開解亦州名本漢胊䏰縣地蜀置漢豐縣後魏置開州領東關東岡二郡又姓呂氏春秋云衛公子開方衛公說文作開經典亦作闓苦哀切五|㱾:㱾𨸜|侅:奇侅非常又古哀切|奒:大皃|㚊:多也
hTQ烏開;哀:悲哀也又姓漢有哀章烏開切六|埃:塵埃|唉:慢譍又於其切|㶼:熱甚|欸:歎也|毐:說文云人無行也本又烏改切
GTQ徒哀;臺:土高四方曰臺又姓漢有侍中臺崇徒哀切十五|擡:擡舉|菭:魚衣濕者曰濡菭亦作苔說文曰菭水衣|苔:+上同又蘚也|炱:炱煤|嬯:鈍劣|薹:蕓薹|䈚:竹萌|儓:輿儓|檯:木名|駘:駑馬|𪒴:𪑚𪒴大黑之皃又都來切|籉:可禦雨也|跆:蹋跆連手唱歌|𩿡:鳥名
dTQ古哀;該:備也咸也兼也皆也又軍中約也古哀切二十|豥:豕四蹄白|垓:八極又垓下隄名沛在郡項羽敗處也|荄:草根又古諧切|郂:鄉名在陳留|㱯:羊胎又音敳|剴:大鎌一曰摩也又五哀切|陔:殿階次之序|姟:數也十冓曰姟|絯:挂也出淮南子|晐:備也兼也|峐:爾雅云山無草木峐|祴:祴夏樂章名|侅:奇侅|賅:+上同又贍也|㨟:㨟觸也|胲:足大指毛𠟼也|䬵:飴也|䶣:牙也|䐩:肥也
PTQ昨哉;裁:裁衣昨哉切九|纔:僅也又藏代切|財:貨也賄也|才:用也質也力也文才也說文作才艸木之初也|材:木梃也|䴭:麴也|溨:水名|鼒:爾雅注鼎斂上而小口又音兹|𦬁:蔽前草箭
ITQ落哀;來:至也及也還也又姓後漢來歙光武姑子蜀志云荊楚名族有黃門侍郎來桓俗作来洛哀切二十五|萊:藜草亦州名漢掖縣屬東萊郡秦屬齊郡後魏分青州置光州取界內光水爲名隋改爲萊州又姓左傳晉與秦戰于郩萊駒爲右|郲:地名|騋:馬高七尺|崍:崍嵦山也|斄:鄉名在扶風又力之切|𤦃:說文云瓄玉也亦作琜|𧳟:貍也|猍:+上同|淶:水名出涿郡|鯠:魚名|鶆:鶆鳩鷹出埤蒼|䅘:䅘麰之麥一麥二稃周受此瑞麥出埤蒼|𣮉:毛起|䋱:+上同|庲:舍也|㾢:惡病|棶:棶椋木名|犛:關西有長氂牛又音釐音茅|逨:至也又力代切|𪎂:小麥|麳:+上同|𤲓:耕外舊場|𪑚:𪑚𪒴大黑|徠:還也又力代切
NTQ祖才;烖:天火曰烖祖才切十二|灾:+上同|災:+籀文|𤆎:+古文|栽:種也|哉:語助|𡿧:說文曰害也|𦸜〈菑〉:+上同亦作菑見經典|𢦏:說文曰傷也烖字類從之省文|𦳦:𦳦蒔|渽:水名出蜀|睵:睽也或作𥅰
OTQ倉才;猜:疑也恨也倉才切四|偲:多才能也|睵:睽也|䞗:說文曰疑之等䞗而去也
CSA扶來;𤗏:版也扶來切二|㯁:姓出姓苑
FTQ土來;胎:始也說文曰婦孕三月也土來切七|孡:+上同|鮐:魚也|台:三台星又天台山名|邰:地名后稷所封在始平或作斄|𧉟:說文云黑貝亦珠𧉟|𩬠:𩬠𩬳婦人僞髻出證俗文
jTQ戶來;孩:始生小兒戶來切八|咳:小兒笑皃|頦:頤下|㨟:觸也|𧻲:留意|䠽:長身|䱺:𩷕䱺雄蟹也|豥:豕四蹄白
QTQ蘇來;鰓:魚頰蘇來切八|揌:擡揌|粞:碎米|䚡:角中骨|顋:顋頷俗又作腮|愢:意不合也|𪃄:鳥名|毢:毰也
gTQ五來;皚:霜雪白皃五來切七|嵦:崍嵦|敳:有所理又隤敳八元名|㱯:殺羊出胎|隑:企立|剴:又音垓|獃:獃癡象犬小時未有分別
HTQ奴來;能:爾雅謂三足鼈也又獸名禹父所化也奴來切又奴登切二|㾍:病也
ETQ丁來;𪒴:𪑚𪒴大黑皃丁來切二|懛:懛獃失志皃
YyA昌來〈求〉;㹗:昌來切牛羊無子一
ByM普才｟來｠〈求〉;𡜊:好色皃普才切一
#真
XVQ側〖職〗鄰;真:真僞也又姓風俗通云漢有太尉長史真祐俗作真側鄰切十六|甄:姓也陳留風俗傳云舜陶甄河濱其後爲氏出中山河南二望又舉延切|振:又之刃切|禛:以真受福|稹:說文云穜穊也又之忍切|磌:柱下石也|畛:田界又之忍切|籈:爾雅云所以鼓敔|侲:字林云養馬者|桭:屋梠|蒖:茆也|唇:驚也|㖘:+上同|帪:馬篼囊也|薽:茢薽豕首草也|㲀:擊也又音辰
KVQ丑人;𤣆:犬走草狀丑人切三|胂:申也|縝:縝紛
hVU於真;因:託也仍也緣也就也亦姓左傳遂人四族有因氏俗作囙於真切二十三|茵:茵褥說文曰車重席也詩曰文茵暢轂文茵虎皮也|鞇:+上同|禋:祭也敬也𥛛籀文|𥛛:+籀文|闉:闉闍城上重門|駰:白馬黑陰又於巾切|湮:落也沈也|烟:烟熅天地氣易作絪縕|氤:氤氳元氣盛也|絪:絪縕麻臬|垔:塞也|陻:-|㘻:+並上同|堙:+亦上同又土山也|洇:水名|姻:婚姻白虎通曰婦人因人而成故曰姻也字林云婚婦家姻壻家|婣:+古文出周禮|諲:敬也|裀:玉篇云衣身|𦎣:黑羊|歅:秦穆公時有九方歅一名皋善相馬也或作諲|㧢:就也
QVQ息鄰;新:新故也亦姓國語晉大夫新穆子又複姓二氏何氏姓苑有新和氏陳留風俗傳云畢公封於新垣後因氏焉魏將新垣衍改爲梁垣氏息鄰切三|辛:薑味也爾雅云太歲在辛曰重光又姓夏啓封支子于莘莘辛聲相近遂爲辛氏漢初辛蒲爲趙魏名將及徙家隴西便爲隴西人|薪:柴也周禮委人掌祭祀之薪詩云翹翹錯薪
ZVQ植鄰;辰:辰象也又辰時也爾雅曰太歲在辰曰執徐植鄰切十三|晨:早也明也|䢅:+古文|敐:擊聲|宸:屋宇天子所居|鷐:鷐風鸇也|麎:牝麋|桭:兩楹閒又音真|茞:草名|屒:重脣|臣:伏也男子賤稱春秋說曰正氣爲帝閒氣爲臣孝經說曰臣者堅也|䢻:地名|䣅:姓也
cVQ如鄰;仁:仁賢莊子曰愛人利物謂之仁釋名曰仁忍也好生惡殺善惡含忍也又姓姓苑云彭城人也如鄰切三|朲:屋上閒朲|人:天地人爲三才亦漢複姓十氏左傳有寺人披齊有徒人費周有王人子突魯有雍人高宋有廚人僕鄭有大夫子人九國語吳有行人儀孔子弟子左人郢漢司空掾封人嬰後漢司徒聞人襲
bVQ食鄰;神:靈也易繫辭曰陰陽不測之謂神亦姓風俗通云神農之後漢有騎都尉神曜何氏姓苑云今琅邪人食鄰切二|晨:又植鄰切
OVQ七人;親:愛也近也說文至也七人切三|寴:-|𡪔:+並古文
jfR下珍〈殄〉;礥:鞭也下珍切又下憐切三|𧥺:誑也|㘋:難也
aVQ失人;申:身也伸也重也容也篆文作申又辰名太歲在申曰涒灘亦州名春秋時屬楚秦南陽郡後魏爲郢州周爲申州又姓出魏郡亦漢複姓四氏莊子有申徒狄漢丞相申屠嘉長沙太傳申章昌左傳齊有申鮮虞失人切十六|伸:舒也理也直也信也|紳:大帶|娠:孕也又脂刃切|呻:呻吟|𣢘:-|𠲳:+並上同|眒:鳥獸驚皃|胂:脢也|㑗:說文曰神也又姓出姓苑|𩉼:革帶|𠭙:引也|身:親也躬也|柛:爾雅木自𡚁曰柛謂𡚁踣也|䰠:山海經云青要山䰠也說文曰神也|訷:訷說信也
AVE必鄰;賓:敬也迎也列也遵也服也說文作賓所敬也又姓左傳齊有大夫賓須無必鄰切十|𧶉:+古文|濱:水際|檳:檳榔|䚔:䚔𧢜暫見|顮:頭憤懣也|儐:敬也又音殯|鑌:鑌鐵爲刀甚利|矉:說文曰恨張目也|𩴱:鬼皃
IVQ力珍;㷠:鬼火說文曰兵死及牛馬之血爲㷠今作粦同力珍切又力刃切二十三|燐:+上同|鄰:近也親也說文曰五家爲鄰俗作隣|轔:車聲|嶙:嶙峋深崖狀也|粼:水在石閒亦作磷又力刃切|磷:+上同|疄:田壟|麟:仁獸爾雅云麕身牛尾一角|麐:+上同|鱗:魚甲又姓左傳宋大夫鱗朱|璘:璘㻞文皃|駗:馬色|翷:翷𦐈飛皃|𧲂:獸名似豕黃身白首出埤蒼|瞵:視皃|獜:獜獜犬健也出說文|驎:騏驎白馬黑脊|壣:菜畦|𩻜:魚名|鏻:健皃又力丁切|繗:紹也|潾:水名
fVY巨巾;𥎊:矛柄也又鉏耰也古作矜巨巾切五|㨷:拭也|堇:黏土|墐:+上同|魿:蟲魚連行又力丁切
JVQ陟鄰;珍:貴也重也寶也俗作珎陟鄰切三|鎮:戍也又陟刃切|填:壓也又音田
LVQ直珍;陳:陳列也張也眾也布也故也亦州名本太昊之墟畫八卦之所周武王封舜後胡公滿於陳楚滅陳爲縣漢爲淮陽國隋爲陳州又姓胡公滿之後子孫以國爲氏出潁川汝南下邳廣陵東海河南六望又虜三字姓後魏書有侯莫陳氏直珍切又直刃切五|敶:+古文說文本直刃切𠛱也|䍶:獸名似羊目在耳後|趁:越履|塵:說文本作𪋻鹿行揚土也
NVQ將鄰;津:說文作𣸁水渡也將鄰切五|𦪉:+古文|璡:美石次玉|濜:氣之液也本亦作𧗁|𦘔:飾也
YVQ昌真;瞋:怒也說文曰張目也又作嗔昌真切六|嗔:+上同本又音填|謓:+亦上同說文恚也|䐜:𠟼脹起也|𣞟:纑也|縝:+上同
PVQ匠鄰;秦:州名古西戎地春秋時爲秦國後并天下爲隴西郡漢武分置天水郡後魏改爲秦州因邑以爲名又姓秦自顓頊後子嬰既滅支庶以爲秦氏也匠鄰切三|螓:螓蜻似蟬而小|𤚩:牛名
lVQ翼真;寅:辰名說文作𡩟翼真切又以之切六|夤:夤緣連也又敬惕也|𦟘:脊𦟘|蔩:蔩菟瓜|螾:寒蟬|𡐔:𡐔場
MVQ女鄰;紉:單繩女鄰切一
BVE匹賓;繽:繽紛匹賓切五|䎙:飛皃|𩴱:說文云鬼皃又音頻|𢣐:敬也|𨷚〈𩰝〉:𩰝爭說文作𩰝鬬也
CVE符真;頻:數也急也比也說文作𩔤水厓人所賓附𩔤蹙不前而止又姓風俗通云漢有酒泉太守頻暢符真切十四|蘋:大萍也又作薲|薲:+上同|嬪:婦也一曰妻死曰嬪|㰋:木名|玭:珠也又步田切|蠙:珠母又步田切|獱:獺之別名|顰:顰眉蹙也|𧭹:多言|嚬:笑也|𩴱:鬼皃|𦇖:擣衣|𡤉:𡤉姿
gVY語巾;銀:周禮荊州其利銀爾雅曰白金謂之銀鍾山之寶有銀燭謂有精光如燭銀重八兩爲一流也語巾切十六|㹞:犬聲|狺:+上同|䖜:兩虎爭聲|檭:木名色白|鄞:縣名在會稽又音齗|圁:圁陽縣名在西河|誾:和也又誾誾中正之皃又姓何氏姓苑云今廣平人|訔:+上同|嚚:愚也|䓄:亭名在江夏|珢:說文云石之似玉者|䴦:獸名似貉而八目出山海經|垠:垠岸也|𪛊:大篪|泿:水名
dVY居銀;巾:釋名曰巾謹也二十成人士冠庶人巾當自謹修於四教居銀切一
dVo居筠;麏:鹿屬居筠切六|麇:-|麕:+並上同|頵:大頭|莙:爾雅云莙牛薻似薻而葉大又渠殞切|汮:水名
kVo爲贇;筠:竹皮之美質也爲贇切四|囩:田十二頃說文回也|縜:綱細|荺:藕根小者
eVo去倫;囷:倉圓曰囷去倫切又咎倫渠殞二切七|箘:桂又竹名又渠殞切|箟:箭竹|輑:車軸相逢|蜠:大貝又渠殞切|峮:嶙峮山相連皃|𡈋:說文曰宮中道又苦本切
DVI武巾;珉:美石次玉亦作玟琘琘武巾切十九|岷:山名江水所出亦州名秦隴西郡之臨洮縣也後魏置岷州因山以爲名|罠:彘網|閩:閩越蛇種也又音文|緍:錢貫亦絲緒釣魚綸也又姓出何氏姓苑|䪸:強也|笢:竹膚又亡忍切|旻:仁覆愍下謂之旻天|旼:和也|痻:病也|闅:亭名在汝南|汶:汶山郡又音問|捪:撫也|忞:自勉強也|盿:視皃|睧:+上同|錉:筭稅也|𪂆:鳥似翠而赤喙|鈱:鈱稅
CVI符巾;貧:乏也少也符巾切二|𡧋:+古文
hVY於巾;𪔗:鼓聲於巾切三|鼘:+上同又烏玄切|駰:馬陰淺黑色又音因
hVo於倫;贇:美好也於倫切四|奫:泉水|頵:說文曰頭頵頵大也|蝹:蝹蝹龍皃
AVI府巾;彬:文質雜半說文云古文份也府巾切十三|斌:+上同|份:說文曰文質備也|玢:文采狀也|豳:地名本豳國之地又有豳城公劉所邑蓋此地也因以名州亦作邠又姓出姓苑|邠:州名|汃:西方極遠之國|霦:璘霦玉光色|㻞:+上同|𥇖:大目皃|攽:說文分也博雅減也|虨:虎文俗作𧈇又普巾方閑二切|砏:水名又石
DVE彌鄰;民:說文曰眾萌也彌鄰切五|闅:低目視也|睧:視皃又音旻|泯:沒也又亡忍切|怋:亂也
#諄
XVg章倫;諄:至也誠懇皃也章倫切五|惇:心實也又音敦|𥇜:鈍目也又音稕|肫:鳥藏|訰:亂言之皃
KVg丑倫;椿:木名丑倫切八|楯:木名|輴:載柩車也|䡅:+上同|鶞:爾雅云春鳸鳻鶞鳻音汾|杶:書曰杶榦栝柏|櫄:+說文同上|瑃:玉名
LVg直倫;䣩:純美酒也直倫切又常倫切二|㡒:布貯曰㡒
QVg相倫;荀:草名又姓本姓郇後去邑爲荀今出潁川相倫切十四|郇:地名在河東解縣周文王子封於郇後以爲氏王莽時有郇越|詢:咨也|眴:眩又音舜|峋:嶙峋|珣:玉名|𣖼:說文曰大木也可以爲鉏柄又祥勻切|洵:水名在晉陽|恂:信也|畇:爾雅曰畇畇田也謂墾辟也又音勻音旬|檈:承食案也|槆:杶木別也|姰:狂也又音縣|㰬:氣逆也又信也
ZVg常倫;純:篤也至也好也文也大也常倫切十三|蓴:蒲秀|蒓:水葵|醇:厚也醲也|鶉:䳺鶉也莊子曰田鼠化爲鶉淮南子曰蝦蟆化爲鶉字林作𨿡|𦎫:說文曰孰也凡從𦎫者今作享同|陙:小阜名也|𢗋:憂悶|錞:樂器鳴之所以和鼓|淳:清也朴也又姓何氏姓苑云今吳人|𡗥:大也|焞:明也又他昆切|䣩:美也
cVg如勻;犉:黃牛黑脣如勻切四|𩀋:鷚鷄晚生者|瞤:目動|眴:+上同
bVg食倫;脣:口脣食倫切五|漘:水際|䔚:牛䔚草似蘭青黑色|㸪:牛行遟也又音巡|紃:環綵絛也又音巡
IVg力迍;淪:沒也力迍切十五|倫:等也比也道也理也又姓風俗通曰黃帝樂人伶倫氏之後|論:言有理出字書又盧昆切|䑳:船䑳|輪:車輪周禮曰軫之方以象地蓋之圜以象天輪輻三十以象日月|陯:山阜陷也|鯩:魚名|蜦:神蛇能興雲雨文字集略云蝦蟆大如屨能食蛇也又力計切|棆:木名|綸:絲綸又姓魏志公孫文懿臣綸直又音鰥|惀:欲曉知也|侖:說文思也|踚:行也|掄:擇也周禮曰凡邦工入山林材而掄不禁又力昆切|䈁:䈁子船具
JVg陟綸;屯:難也厚也陟綸切又徒渾切四|窀:窀穸下棺|迍:迍邅本亦作屯易曰屯如邅如|㡒:布貯
OVg七倫;逡:逡巡退也七倫切十|竣:止也倨也一曰改也|皴:皮細起也|㕙:東郭㕙古之狡兔也又音俊|壿:舞皃|捘:推也左傳云捘衛侯之手又子寸切|竴:喜也|踆:退也|𠣟:+上同|夋:倨也
NVg將倫;遵:循也率也行也習也將倫切五|跧:蹙也又阻圓切|僎:鄉飲酒禮僎者降席而遵法也或作遵又音撰|嶟:山皃|鷷:西方雉名
YVg昌脣;春:四時之首尚書大傳曰春出也萬物之出也春秋說題辭曰春蠢也蠢興也春秋繁露曰春喜氣又姓何氏姓苑云春申君黃歇之後昌脣切一
PVg昨旬;鷷:西方雉名昨旬切一
lVg羊倫;勻:徧也齊也說文少也从勹二羊倫切二|畇:詩曰畇畇原隰又音荀音旬
RVg詳遵;旬:十日曰旬詳遵切十七|𠣙:+古文|巡:逡巡說文曰視行也|馴:擾也從也善也|循:善也|揗:手相安慰|㸪:牛行遟又音脣|紃:環綵絛又食綸切|䋸:縫也|𪀠:𪀠䳦小鳥出字統|洵:均也龕也|楯:楯闌檻也|灥:三泉相通|㽦:均也|𧾩:說文曰走皃也|畇:墾田|䖲:蟲名
dVk居勻;均:平也又學曰成均亦州名春秋及戰國時並屬楚秦屬南陽郡隋爲均州取汮水以名之居勻切四|鈞:二三十斤也又姓風俗通云楚大夫元鈞之後漢有侍中鈞喜|袀:戎衣也左傳曰均服振振字書從衣|汮:水名出析縣北山入沔今作均
fVU渠人;𧼒:行也渠人切又去忍切一
BVI普巾;砏:砏磤大雷普巾切又布巾切二|虨:虎文也俗作𧈇
#臻
SWQ側詵;臻:至也乃也側詵切十一|蓁:草盛皃|搸:聚也又琴瑟音|溱:水名在河南|潧:水名在鄭國出說文此水南入洧詩作溱洧誤|𣓀:𣓀栗|榛:+上同|樼:+亦同|瀙:字林云水名在豫州|𨬖:埤蒼云小鑿|轃:說文曰大車簀也
VWQ所臻;莘:地名在虢又姓所臻切二十|㜪:有㜪國名|扟:從上擇取物也|駪:馬多|籸:粉滓|䯂:眾盛皃|甡:眾多皃|兟:進也|詵:眾人言也|侁:行皃詩云侁侁征夫|𩺵:魚尾長也詩云有莘其尾字書從魚|屾:說文云二山也|𨐔:多也|燊:熾也|𦐹:羽多|𢓠:往來之皃|𣘘:方言云杠東齊海岱之閒謂之𣘘杠牀前橫也|阠:八陵東名阠又息進切|姺:女字|㾕:寒病
UWQ士臻;𦿒:木叢生士臻切三|㲀:呂氏春秋注云㲀㲀動而喜皃又音真|帘:幕也又音廉
#文
DXM無分;文:文章也又美也善也兆也亦州名禹貢梁州之域自戰國時宋及齊梁皆諸羌所據後魏平蜀始置州亦姓漢有廬江文翁無分切十六|聞:說文曰知聲也又音問|𦖞:+古文|彣:青與赤雜|紋:綾也|雯:雲文|馼:馬赤鬣縞身目如黃金文王以獻紂|蟁:爾雅曰鷏蟁母郭璞云似烏𪇰而大黃白雜文鳴如鴿今江東呼爲蚊母俗說此鳥常吐蚊因名云說文曰齧人飛蟲也|蚊:+上同|䘇:亦同出漢書|䰚:摩也|鳼:鳥也爾雅曰鶉子鳼|闅:俗作閿說文曰低目視也弘農湖縣有闅鄉汝南西平有闅亭|汶:黏唾又音旻問|鼤:班鼠|閩:閩越也又音旻
kXs王分;雲:說文云山川气也从雨云象雲回轉形河圖曰雲者天地之本傅子曰以雲母飾車謂之雲母車臣不得乘之又姓縉雲氏之後又後魏書宥連氏後改爲雲氏王分切二十二|芸:香草也說文云似目宿淮南王說芸草可以死復生雜禮圖曰芸蒿也葉似邪蒿香美可食也|蕓:蕓薹菜名|𦔐:說文曰除苗閒穢也|𦓷:+上同|耘:亦同|鄖:國名|妘:女字又姓|紜:紛紜|溳:水名在南陽一云在美蔡陽|澐:江水大波|云:辝也言也說文古文雲字亦姓出自祝融之後|篔:篔簹竹名|䢵:邑名|員:益也說文作員物數也又音圓又音運姓也|𪔅:+籀文|愪:憂也|沄:說文云轉流也|𧶊:亂也|耺:耳中聲|橒:木名|䉙:竹名
hXs於云;熅:烟熅天地氣也易作絪縕於云切十|氳:氤氳元氣|縕:亂麻又於粉切|馧:香也|蒕:葐蒕盛皃|𥠺:+上同|䡝:轒䡝兵車又於粉切|蘊:蘊積也又於粉切|蝹:龍皃|㚃:鬱也
CXM符分;汾:水名在太原本漢兹氏縣地屬西河郡魏於兹氏縣置西河郡今州城是也符分切三十七|墳:墳籍又墓也|氛:氛氳祥氣|𣱦:+俗|鼖:大鼓周禮鼓人掌六鼓以鼖鼓鼓軍事|䩿:+上同|𪔵:亦同|濆:水際也又水名|焚:焚燒|燌:+上同|羒:白羝羊也|豶:豕也|頒:魚大首亦眾皃又布還切|羵:土中怪羊|䴅:似鵠白身三目赤尾六足|枌:白榆木名|鳻:春鳸鳻鶞亦作𩿈又說文曰鳥聚皃一曰飛皃|蕡:草木多實|𦶁〈萉〉:+古文|橨:枰仲木別名出埤蒼|棼:複屋棟也|賁:三足龜|葐:葐蒕|魵:魚名|𧮱:谷名在臨汾|妢:周禮考工記云妢胡之笴|棻:香木名也|梤:+上同|肦:大首皃|䫶:醜皃|鐼:飾也說文曰鐵類讀若薰又音訓|馩:馩馧香氣|馚:+上同|㞣:草初生香分布也又音芬|鼢:田中鼠又音憤|蚡:+上同|轒:轒䡝兵車
AXM府文;分:賦也施也與也說文別也府文切六|饙:一蒸飯也|餴:+上同|扮:握也|𡊅:埽棄之也又方問切|𣯻:𣯻毭罽也
fXs渠云;羣:羣隊也說文輩也亦作群渠云切五|帬:說文曰下裳也釋名曰帬羣也連接羣幅也|裠:+上同亦作裙|宭:羣居也又音君|𤸷:𤹝也
iXs許云;薰:香草韻略曰薰陸香出大秦國亦姓出何氏姓苑許云切十二|曛:日入也又黃昏時|勳:功勳也|勛:+古文|熏:火氣盛皃|燻:+上同|獯:北方胡名夏曰獯鬻周曰獫狁漢曰匈奴|纁:三染絳|醺:著酒|葷:臭菜|焄:禮曰焄蒿悽愴鄭玄云焄謂香臭也|臐:儀禮鄭玄注云羊曰臐豕曰膮皆香美之名膮呼堯切
dXs舉云;君:白虎通曰君者羣也羣下之所歸心也荀卿子曰君者儀也民者影也儀正則影正君者盤也民者水也盤圓則水圓又君者民之源也源清則流清源濁則流濁舉云切八|軍:軍旅也周禮夏官司馬曰凡制軍萬有二千五百人爲軍王六軍大國三軍次國二軍小國一軍軍將皆命卿又漢複姓二氏禮記有將軍文子晉有太傅參軍襄城冠軍夷|皸:足拆|桾:桾櫏木也|䇹:竹名|莙:牛藻菜也|宭:羣居|鮶:蟲名水鮶如魚乘焉
BXM府〖撫〗文;芬:芬芳又姓戰國策晉有大夫芬質府文切十三|紛:紛紜眾也亂也|𢁥:巾也亦作帉|𣬩:毛落|衯:說文曰長衣皃|𦐈:翻翷𦐈飛皃|棻:說文云香木也|砏:砏汃水石|㞣:草木初生香分布也|氛:氛侵妖氣|雰:+上同又霧氣也|𨷹〈𩰟〉:𩰝𩰟之皃|錀:埤蒼云兔奄錀
#欣
iYc許斤;欣:喜也亦州名本漢陽曲縣地隋置欣州因欣口爲名許斤切六|忻:+上同|昕:日欲出也|訢:喜也|炘:熱皃|邤:邤鄰地名
hYc於斤;殷:眾也正也大也中也說文从㐆殳作樂之盛稱殷亦姓武王剋紂子孫分散以殷爲氏出陳郡於斤切四|慇:慇懃|㶏:水名在潁川|溵:+上同
fYc巨斤;勤:勞也盡也巨斤切八|芹:水菜食之宜丈夫呂氏春秋曰菜之美者雲夢之芹|懃:慇懃|慬:憂哀|懄:+上同|瘽:病也|𥎊:矛柄古作矜|蘄:草也又巨希切
dYc舉欣;斤:十六兩也說文曰斫木也又虜複姓二氏後魏書去斤氏後改爲艾氏奇斤氏後改爲奇氏舉欣切四|筋:筋骨也說文曰𠟼之力也从力𠟼竹竹物之多筋者又姓出姓苑|䈥:+俗|釿:說文云劑斷也本宜引切
gYc語斤;䖐:虎聲語斤切十二|㹜:犬相吠也|圻:圻堮又岸也|垠:+上同|齗:齒根𠟼也|齦:+上同|䴦:獸似貉也|斦:二斤|𪛊:大篪|䓄:亭名在江夏郡|狺:犬爭|鄞:縣名在會稽郡
#元
gZs愚袁;元:大也始也長也氣也又姓左傳衛大夫元咺又後魏孝文改拓拔爲元氏望在河南愚袁切二十二|原:廣平曰原亦州名漢高平縣後魏爲鎮州又改原州蓋取高平曰原爲名又姓孔子弟子有原憲說文本作𨙅原即與𠫐同|𨙅:周禮有𨙅師注云𨙅地之廣平者|源:水原曰源又姓禿髮傉檀之子賀入後魏魏太武謂之曰與鄉同源可爲源氏說文本作𠫐篆文省作原後人加水|厵:+上同|杬:木名出豫章煎汁藏果及卵不壞|嫄:姜嫄帝嚳元妃|沅:水名在武陵郡鐔成西亦云在牂牁|騵:赤馬白腹|黿:似鼈而大紀年曰穆王三十七年起師至九江以黿爲梁|羱:羱羊角大者可爲器又五丸切|蚖:蠑蚖蜥蜴也一名守宮字林云在壁曰蝘蜓在洲曰蜥蜴|𧔞:晚蠶周禮禁原蠶鄭注云原再也俗從䖵|芫:草名有毒可爲藥也|邧:地名|榞:實如甘蕉而皮可食|謜:徐語孟子云故謜謜而來|㹉:獸如牛也|䬧:䬧餌又五丸切|獂:豕屬又音桓|阮:五阮郡出史記又元遠切|蒝:莖葉布也
kZs雨元;袁:姓出陳郡汝南彭城三望本自胡公之後雨元切十六|爰:於也行也爲也哀也引也亦姓出濮陽亦舜裔胡公之後袁或作爰|垣:垣墉也又姓漢西河太守洛陽垣恭也|𩫧:+籀文|園:園圃亦姓|援:援引也又爲眷切|榬:絡絲籰|轅:車轅方言云轅楚衛謂之輈又姓左傳陳大夫轅濤塗之後又漢複姓有軒轅氏|鶢:鶢鶋海鳥|媛:嬋媛枝相連引又爲眷切|洹:水名亦縣名在相州又音桓|溒:纂文云姓也玉篇云水流皃|𧻚:易田名也|蝯:蝯猴五百歲化爲玃爾雅曰猱蝯善援|猨:+上同|猿:+俗
CZM附袁;煩:勞也說文曰熱頭痛也附袁切三十八|番:說文曰獸足謂之番經典作番又翻盤潘三音書亦音波|𨆌:+足有文也說文同上|蹯:+亦同上見左傳|繁:穊也多也|蘩:皤蒿|薠:似蘋而大|樊:樊籠亦姓周宣王封仲山甫於樊後因氏焉今在南陽|𢶃:𢶃捼也|繙:繙㠾亂取㠾於元切|燔:炙也|膰:祭餘熟𠟼|瀿:水名玉篇云水暴溢也|羳:羊黃腹也|𩐏:百合蒜也|鷭:鷭䳇鳥|蟠:𧑓負又扶干切|蕃:茂也息也滋也又音藩|蠜:䘀螽|礬:礬石|𪖇:鼠名|𨟄:鄉名在京兆杜陵|鐇:廣刃斧|璠:璠璵魯之寶玉|笲:竹器禮記云婦執笲|𥢌:稻也出齊人種術|㺕:犬鬬也|襎:襎裷幭也|袢:絺綌詩云是紲袢也|棥:藩屏|䋣:馬飾名也|𥿋:+上同|墦:冢也|𢐲:生養也|䮳:+上同|旛:旐也|𧢜:䚔𧢜|藩:𧂇䒞葉如韭又音翻
BZM孚袁;飜:覆也飛也孚袁切十|翻:+上同|旛:旌旐摠名|番:數也遞也又盤潘煩三音|幡:說文曰書兒拭觚布俗通爲幡|𤄫:大波|𤄜:米汁|轓:車大箱也|繙:繽繙風吹旗皃|反:斷獄平反又方晚切
iZs況袁;暄:溫也況袁切十九|煖:+上同|喛:恐懼|萱:忘憂草說文又作藼蕿|䁔:大目|諼:詐也|塤:說文作壎樂器也以土爲之六孔釋名曰塤宣也聲濁喧然世本曰暴辛公作塤|壎:+上同|䳦:䳦鴝鳥名|吅:喚聲又私全切|貆:獸名詩云有縣貆兮又丸歡二音|喧:大語也|諠:諠譁亦作喧讙|愋:恨也|讙:讙囂皃也|翧:飛來|䚭:揮角|䚙:角匕又許羈切|蝖:蠀螬
hZs於袁;鴛:鴛鴦匹鳥於袁切十八|冤:屈也枉也曲也又冤句縣在曹州句音劬|㠾:繙㠾|鵷:鵷鶵似鳳|𣹠:水名|惌:惌枉|䥉:鋤頭曲鐵|宛:屈草自覆又宛縣在南陽又音苑|蜿:蜿蜿龍狀也又音苑|𩝸:貪也|蒬:棘蒬草名|怨:怨讎又於願切|𡟰:𡟰𡟰美也|葾:敗也|䡝:兵車|䩩:量物之具又於阮切|裷:襎裷|眢:目空皃又一丸切
gZc語軒;言:言語也字林云直言曰言荅難曰語釋名曰言宣也宣彼之意也又姓孔子弟子有言偃語軒切五|琂:石似玉|甗:無底甑也又語戰切|䇾:大簫|䓂:草名
eZc丘言;攑:舉也丘言切二|䞿:走皃又虛言切
iZc虛言;軒:軒車又姓軒轅之後漢有諫大夫軒和虛言切六|掀:以手高舉|鶱:飛舉皃|䡣:車前輕也|蓒:蓒芋草名|䞿:走皃
dZc居言;𢳚:𢳚子摴蒱采名居言切十二|𣘖:+上同|靬:乾革又驪靬縣在張掖又下憚切又口旦切|鞬:馬上盛弓矢器|𩎀:+上同|㓺:以刀去牛勢或作犍|犍:犗牛名又犍爲郡|腱:筋也一曰筋頭|騝:騮馬黃脊曰騝|䭈:粥也亦作飦|𩱡:+上同|𩱤:+籀文
hZc謁言;蔫:蔫菸也謁言切二|焉:安也又不言也
AZM甫煩;蕃:蕃屏甫煩切六|藩:籬也亦藩屏也|轓:車箱又音幡|鱕:魚有橫骨在鼻前如斤斧|籓:大箕一曰蔽也|鐇:廣刃斧也
fZc巨言;𥴤:筋鳴也巨言切二|赶:獸舉尾走
DZM武元;樠:松心又木名也武元切又莫昆切一
#魂
jag戶昆;䰟:魂魄也白虎通曰魂者沄也猶沄沄行不休也魄者迫也猶迫迫然著於人也淮南子曰天氣爲䰟地氣爲魄又反魂樹名在西海中聚窟洲上花葉香聞數百里狀如楓香煎其汁可爲丸名曰震靈丸亦名反生香又名卻死香死屍在地聞氣乃活出十洲記戶昆切二十四|㮯:大木未剖|䮝:獸名|𤟤:似犬人面見人則笑行疾如風|餛:餛飩|餫:+上同|䴷:不破麥也|鼲:鼠名|楎:三爪犁曰楎一曰犁上曲木也|渾:渾濁益部耆舊傳曰漢武時洛下閎明曉天文於地中轉渾天定時節亦姓左傳鄭大夫渾罕又胡本切|沄:水流皃|忶:埤蒼云心悶也|𦸌〈𦺊〉:蒲也又胡官切|俒:全也|㑮:女字又五昆切|䡣:還也車相避也|𡍦:里名在洛陽|𢣒:𢣒悶|𣝂:𣝂榾|㨡:㨡推|煇:赤色|顐:𩒱顐禿也|𧡡:𧡡視|琿:玉名
dag古渾;昆:兄也後也同也又姓夏諸侯昆吾之後戰國策有齊賢者昆辨古渾切二十|晜:+上同|𥊽:+上同說文云周人謂兄曰𥊽|菎:香草|㡓:褻衣說文幒也|褌:+上同|崐:崐崘山名|琨:琨㻍玉名|鵾:鵾雞|鶤:+上同|鯤:北溟大魚|䖵:說文曰蟲之總名也|蜫:+上同|惃:亂也|㱎:㱎干不可知也|錕:錕鋙鐵赤色可爲劒|瑻:同琨|𪋆:鹿屬|猑:獸名|騉:騉駼馬名牛蹄能升高山
hag烏渾;𥁕:說文曰仁也从皿以食囚也今作昷同烏渾切十三|溫:水名出犍爲又和也善也良也柔也暖也又姓唐叔虞之後受封於河內溫因以命氏又卻至食采於溫亦号溫季因以爲族出大原又漢複姓二氏莊子有溫伯雪子姓苑又有溫稽氏|轀:轀輬車也|薀:薀藻節中生葉又於殞切|𩥈:𩥈驪駿馬|殟:病也|鴛:鴛鴦匹鳥又音冤|𨜵:鄉名出蜀志|豱:豕名|縕:禮曰一命縕韍|韞:赤色又於粉切|㼔:瓜名|𪉸:戎狄云鹽
DaA莫奔;門:問也聞也字從兩戶亦姓周禮云公卿之子入王端之左教以六藝謂之門子其後氏焉又漢複姓十四氏左傳魯卿東門襄仲宋樂大心爲右師居桐門後因氏焉伍子胥抉眼吳門因謂子胥門子孫乃以胥門爲氏吳有胥門巢世本晉大夫下門牕齊臨淄大夫車門遽陳有鬬門氏戰國策有雍門周魏侯嬴爲夷門抱關者後姓夷門氏呂氏春秋有陽門介夫後以陽門爲氏古今人表有逢門子豹宋諸公子食采於木門者後遂爲氏漢書儒林傳有闕門慶忌何氏姓苑云弋門氏今漁陽人又有剌門氏莫奔切十三|捫:以手撫持|樠:木名|虋:赤粱粟也俗作𧄸|璊:玉色赤也|亹:浩亹地名出漢書地理志云浩音鴿|𤅣:+上同|怋:怋怋不明又亂也|䫒:頭多殟䫒|𣯩:赤色罽名|䟂:行遟|䊟:粥凝|𪈿:比翼鳥也
Qag思渾;孫:爾雅釋親曰凡子之子爲孫孫之子爲曾孫曾孫之子爲玄孫玄孫之子爲來孫來孫之子爲晜孫晜孫之子爲仍孫仍孫之子爲雲孫又岱謂之天孫又姓周文王子康叔封于衛至武公子惠孫曾耳爲衛上卿因氏焉後有孫武孫臏俱善兵法各撰書凡太原東莞吳郡安樂四望又漢複姓二十三氏左傳秦大夫逢孫氏魯卿有臧孫辰仲孫何忌魯桓公之子慶父之後有孟孫氏叔孫氏季孫氏同出桓公号爲三桓子孫代爲魯之上卿秦下大夫楊孫氏齊大夫長孫修世本云食邑於唐其孫仕晉後号唐孫氏衛有王孫賈出自周頃王之後王孫賈之子自以去王室久改爲賈孫氏晉濟南太守魚孫瑋出自宋魚石奔楚其孫在國者因以魚孫爲氏漢有烏孫昆彌後漢有士孫瑞古封公之後自皆稱公孫故其姓多非一族也孔子弟子有顓孫師國語晉公子利孫夫之後以利孫爲氏何氏姓苑有經孫新孫古孫牟孫室孫長孫叔孫等氏望稱河南之者是虜姓也思渾切六|蓀:香草|飧:說文餔也|蕵:烏蕵草又蕵蕪酸可食也|猻:猴猻|搎:捫搎摸𢱢也
Nag祖昆;尊:尊卑又重也高也貴也敬也君父之稱也說文曰酒器也本又作𢍜周禮有司尊彝從土從缶從木後人所加亦姓風俗通云尊盧氏之後祖昆切五|罇:-|樽:+並見上注|嶟:山皃|繜:衣也
Pag徂尊;存:在也察也恤問也徂尊切五|蹲:坐也說文踞也|拵:据也|𨚲:𨚲䣕縣在戎州|袸:爾雅云衿謂之袸袸小帶也又音荐
Eag都昆;敦:迫也亦厚也又姓敦洽衛之醜人也都昆切七|惇:厚也|弴:畫弓也天子弴弓又丁僚切|㢯〈弤〉:+上同|驐:去畜勢出字林|墩:平地有堆|𤭞:器似甌瓿
Fag他昆;暾:日出皃他昆切七|燉:火色|涒:涒灘歲在申也|𪏆:禮記孺子𪏆之喪也魯公子名亦黃色也|噋:詩云大車噋噋噋噋重遟皃|𧑒:𧑒𧍪蟲名|黗:黃黑色也
Gag徒渾;屯:聚也又姓後蜀錄有法部尚書屯度徒渾切二十二|豚:豕子|㹠:-|豘:+並上同|窀:火見穴中又音迍|臀:廣雅云臀謂之脽亦謂之臎也說文作尻髀也|𡱂:-|𦞠:-|𩪡:+並同上見說文|軘:兵車|飩:餛飩|𥴫:榜也|坉:以草裹土築城及填水也|沌:水勢|邨:地名亦音村|燉:火熾又燉煌郡燉大煌盛也|忳:悶也|啍:口氣|芚:菜似莧也|庉:風與火爲庉又徒損切|𪎶:黃色|𤫭:㼔𤫭瓜名
Oag此尊;村:墅也此尊切一
gag牛昆;㑮:女字又姓出纂文牛昆切又戶昆切四|瘒:癡皃|顐:𩒱顐禿無髮也|梱:爾雅釋木曰髡梱
CaA蒲奔;盆:瓦器亦作瓫爾雅曰盆謂之缶說文曰盎也又姓風俗通云盆成括仕齊孟軻知其必死其子逃難改氏成焉蒲奔切四|葐:覆葐草|𪂽:𪂽鳩鳥|湓:水名在尋陽一曰水涌也
AaA博昆;奔:奔走也說文作奔博昆切四|賁:勇也周禮有虎賁氏掌先後王而趨以卒伍軍旅會同亦如之舍則守王閑閑梐枑也書云武王伐紂戎車三百兩虎賁三百人亦姓古有勇士賁育又肥祕墳三音|䴅:䴅如鵲三目六足白身|犇:牛驚出文字集略
Iag盧昆;論:說也議也思也盧昆切又力旬盧鈍二切四|崘:崐崘|掄:說文擇也一曰貫也|菕:菕虂草也
eag苦昆;坤:乾坤苦昆切七|𡿦:+古文|髡:去髮|𩒱:𩒱顐|臗:體也臀也|髖:+上同|豤:齧也
iag呼昆;昏:說文曰日冥也亦作昬呼昆切七|惛:不明|婚:婚姻嫁也禮娶以昏時婦人陰也故曰婚|棔:合棔木名朝舒夕斂|閽:守門人也|殙:病也又未立名而死|𣣏:不可知也
BaA普魂;濆:潠也普魂切三|噴:+上同|歕:吐也又吹氣也
Hag奴昆;黁:香也亦人名姚興太史令郭黁奴昆切一
#痕
jbQ戶恩;痕:瘢也戶恩切四|鞎:車革前飾|拫:急引|㯊:所以平量斗斛
dbQ古痕;根:根柢也亦姓根牟子古賢者著書出風俗通古痕切四|跟:足後踵也|𣥦:+上同|珢:石次玉又音銀
hbQ烏痕;恩:恩澤也惠也愛也隱也亦姓前燕慕容皝東庠祭酒恩茂風俗通云陳大夫成仲不恩之後烏痕切三|𤇯:說文炮炙也以微火溫𠟼|煾:+上同
FbQ吐根;吞:咽也吐根切又音天一
gbQ五根;垠:垠㓵五根切又語斤切三|圻:+上同|泿:水名
#寒
jcQ胡安;寒:寒暑也釋名曰寒捍也捍格也亦姓後漢博士魯國寒朗武王子寒侯之後也胡安切十二|𩏑:亦作韓井垣也亦國名又姓出自唐叔虞之後曲沃桓叔之子萬食邑於韓因以爲氏代爲晉卿後分晉爲國韓爲秦滅復以國爲氏出潁川後韓騫避王莽亂移居南陽故有潁川南陽二望|𦺦:𦺦蔣草也|翰:天雞羽有五色又音扞|鶾:+上同|邯:邯鄲縣名又漢複姓漢有衛尉邯鄲義風俗通云因國爲姓也|邗:邗溝水名在廣陵|虷:虷蟹一名蜎蟲|汗:可汗蕃王稱又音犴|𧃙:白𧃙草也又何旦切|䮧:䮂䮧蕃大馬出異字苑
gcQ俄寒;豻:胡地野狗似狐而小或作犴俄寒切又音岸四|犴:+上同|雃:雃䲽鳥一名雝𪆂䲽音石|𡽜:山形也
EcQ都寒;單:單複也又大也亦虜姓阿單氏後改爲單氏都寒切又常演切十|襌:襌衣|鄲:邯鄲|丹:赤也說文曰巴越之赤石也亦州名春秋時白翟所居後魏置汾州廢帝三年以河東汾州同乃改爲丹州亦姓晉有大夫丹木出風俗通|殫:盡也|簞:簞笥小篋|匰:宗廟盛主器出字書|㠆:㠆孤山名|癉:火癉小兒病也|䐷:大腹
hcQ烏寒;安:安徐也寧也止也平也亦州名春秋時鄖國漢屬江夏郡宋分江夏郡爲安陸郡武德四年討平王世充改爲安州有鄖水亦姓風俗通云漢有安成爲太守廬山記有安息國王子安高又漢複姓有安都氏烏寒切五|䀂:䀂𥂫大盂|鞌:鞌韉|䢿:地名在當陽|侒:說文宴也
HcQ那干;難:艱也不易稱也又木難珠名其色黃生東夷曹植樂府詩曰珊瑚閒木難又姓百濟人說文作𪇠鳥也本又作𩁘那干切又奴汗切四|𪇼:+見上注|𩁢:-|𩁚:+並古文
OcQ七安;餐:說文吞也七安切三|湌:+上同俗作飡|䉔:䉔笒出異字苑
FcQ他干;灘:水灘爾雅云太歲在申曰涒灘他干切十|嘽:馬喘|嘆:長息與歎同又音炭|擹:擹蒱賭博|譠:譠慢欺慢言也|痑:力極|攤:開也亦緩也|𦧴:𦧴𦧝言不正也|嬗:緩也|㨏:搫㨏婉轉
QcQ蘇干;𦙱:脂肪蘇干切五|跚:蹣跚跛行皃|珊:珊瑚廣雅曰珊瑚珠也說文曰珊瑚生海中而色赤也|姍:誹也|䈀:竹器
GcQ徒干;壇:封土祭處徒干切十五|檀:木名亦州名春秋時及戰國並爲燕地漢屬漁陽郡隋置檀州取白檀縣爲名又姓太公爲灌檀宰後氏焉禮記魯有檀弓今檀城在瑕丘瑕丘屬山陽晉改山陽爲高平郡檀氏望在高平也|鷤:鸛鷤如鵲短尾射之銜矢射人說文爾雅並作鸛鷒|癉:風在手足病又都彈切|撣:觸也太玄經云揮繫其名|彈:糾也射也亦彈棊梁冀傳云冀好彈棊也又徒案切|驒:連錢驄一曰青驪白文又丁年切驒騱匈奴畜似馬而小|驙:白馬黑脊又知連切|但:語辝亦姓何氏姓苑云漢有但巴爲濟陰太守又徒旱切又徒旦切|胆:胆口脂澤出證俗文|繟:寬緩|儃:態也又市連切|聅:軍法以矢貫耳曰聅|唌:歎也|貚:貙屬
PcQ昨干;殘:餘也說文賊也昨干切七|䏼:禽獸食餘又徂贊切|㱚:+上同|戔:傷也又戔戔束帛皃易曰束帛戔戔|𥂫:䀂𥂫大盂|𣦼:穿也|帴:帗也
dcQ古寒;干:求也犯也觸也亦姓左傳宋有干犨又漢複姓何氏姓苑漢有干己衍爲京兆尹古寒切十六|乾:字樣云本音虔今借爲乾濕字又姓出何氏姓苑|漧:+古文|竿:竹竿|肝:木藏|奸:以淫犯也|鳱:鳱鵲鳥名知未來事噪則行人至鵲字或作䧼䧼古沃切|玕:琅玕美石次玉|邗:越別名又音寒江名也|汗:餘汗縣名又寒翰二音|迀:進也|㿻:盤也又大盌名|𢧀:𢧀盾|忓:說文極也|𨝌:地名|𡯋:𡯋股
IcQ落干;蘭:香草亦州名古西羌地隋文帝置蘭州取皋蘭山爲名又姓漢有武陵太守蘭廣落干切十二|瀾:大波|闌:晚也牢也遮也希也又飲酒半罷曰闌|讕:逸言又力誕切|攔:階際木句攔亦作闌|𨷻:妄入宮門|籣:盛弩矢人所負也|䪍:+上同|欄:木名|躝:踰也|幱:幱衫幱裙|㘓:㘓哰𠍽挐語不可解
ecQ苦寒;看:視也苦寒切七|𥉏:+古文|栞:槎木也|𣓁:+上同|靬:弓衣|臤:堅也又口閒口耕二切|刊:削也剟也
icQ許干;頇:顢頇大面皃許干切二|鼾:臥氣激聲
Hcg乃官;濡:水名出涿郡乃官切一
#桓
jcg胡官;桓:桓桓武也又姓本自姜姓齊桓公後因諡爲氏望出譙郡後漢有太子太傅桓榮胡官切二十九|完:全也|䴟:鹿一歲|𩾞:𩾞䳜鳥烏喙蛇尾也|丸:彈丸|瓛:圭名說文曰桓圭公所執|紈:紈素|𦻃:𦻃葦易亦作萑俗作雚雚本自音灌|雈:木兔鳥也|洹:水名在鄴又干元切|汍:汍瀾泣淚|絙:緩也|芄:芄蘭草名|豲:豕屬又豲道縣在夫水亦作獂|梡:木名出蒼梧子可食|荁:堇類|莞:似藺而圓可爲席又音官|綄:船上候風羽楚謂之五兩|𦏊:山羊細角而形大也|萈:+上同見說文|貆:說文曰貉之類又音歡|狟:大犬也周書曰尚狟狟|峘:爾雅云小山岌大山曰峘又戶登切|㿪:皮病|䎠:丸屬|垸:漆加骨灰上也|寏:周垣|院:+上同|捖:揳刮摩也
gcg五丸;岏:巑岏五丸切十|刓:圓削|园:+上同|忨:貪也|蚖:毒蛇|䯈:䯊䯈|羱:羱野羊角大又語袁切|黿:黿似鼈又音元|抏:挫也|𠒢:𠒢䨲
Ecg多官;端:正也直也緒也等也亦姓出姓苑又漢複姓孔子弟子端木賜也多官切十一|褍:衣長也又衣正幅也|剬:齊也|𧤗:角𧤗獸名狀如豕角善爲弓李陵以此遺蘇武|耑:說文曰物初生之題也上象生形下象其根也|鍴:鑽也|𥵣:竹名出南嶺|竱:齊也又之耎切|𦾸:草名|𥠄:禾垂皃又丁果切|偳:抄偳又音湍
hcg一丸;剜:刻削也一丸切六|眢:井無水一曰目無精|豌:豆也|蜿:蟠蜿龍皃|帵:帵子裁餘|婠:德好皃又古旦切
Fcg他端;湍:急瀨也他端切又音專六|貒:似豕而肥又他畔切|䵎:黃黑色|𪏆:黃色又湯門切|煓:火盛|偳:人名又多丸切
Qcg素官;酸:醋也素官切五|狻:狻猊師也猛獸|䝜:+上同|痠:痠疼|𩆑:小雨
Gcg度官;團:團圓度官切十二|慱:詩云勞心慱慱|篿:竹器|剸:截也|鄟:邾䣚之邑|𧐕:魚似鮒而豕尾|敦:詩云有敦瓜苦又都昆切|漙:詩云零露漙兮|鷒:爾雅曰鸛鷒鶝鶔如鵲短尾射之銜矢射人|𪆃:鳶之別名詩亦作鶉傳云雕也|摶:說文曰圜也禮云無搏飯|𩅂:露皃
Pcg在丸;欑:木叢也在丸切九|巑:巑岏小山皃|𩎈:車縛軏也又借官切|菆:菆塗見禮|禶〈襸〉:襸補|酇:酇聚也又音纂音贊|穳:秿也又刈禾積也|𥣚:+上同|劗:剃髮也又子欑切
dcg古丸;官:官宦左傳曰黃帝以雲紀官炎帝以火紀官大暤以龍紀官少暤以鳥紀官又君也法也事也又複姓三氏左傳晉王官無地御戎魯先賢傳云孔子妻并官氏楚莊王少子爲上官大夫以上官爲氏古丸切十|悹:憂也又古玩切|莞:草名可以爲席亦云東莞郡名又姓姓苑云今吳人又胡官切|棺:棺椁禮記曰有虞氏瓦棺夏后氏堲周殷人棺椁說文曰關也所以掩屍也|觀:視也又音灌|貫:穿也又音灌|冠:首飾說文曰絭也所以絭髮弁冕之總名也亦姓風俗通云古賢者鶡冠子之後又音灌|涫:樂涫縣在酒泉|倌:倌人主駕說文曰小臣也詩云命彼倌人|毌:穿物持也
Icg落官;鑾:鑾鈴崔豹古今注云五輅衡上金雀者朱鳥也口銜鈴鈴謂之鑾也或謂朱鳥鸞也鸞口銜鈴故謂之鑾落官切十四|鸞:春秋元命包曰离爲鸞孫氏瑞應圖曰鸞者赤神之精鳳皇之佐也山海經曰女牀山有鳥狀如翟而五采文名曰鸞見則天下太平安寧|巒:小山而銳|欒:木名說文曰木似欄禮天子樹松諸侯柏大夫欒士楊又曲枅亦姓代爲晉卿出左傳|羉:彘罟|𧄶:𦽏葵一曰茆也|䜌:南䜌縣在鉅鹿|㱍:迷惑不解理一曰欠皃|臠:臠臠病瘠皃|灤:水名|灓:說文曰漏流也水沃也漬也|𤼙:病也瘦也|圝:團圝圓也|曫:日夕昬時
icg呼官;歡:喜也呼官切十三|懽:+上同又音貫|驩:馬名|貆:貉屬|貛:牡狼|𪈩:𪈩鷤鳥射之則銜矢射人說文爾雅並云𪈩鷒|鴅:鳥名人面鳥喙|酄:魯郡邑名|獾:野豚|犿:+上同|𡚊:化也始也出方言|讙:讙諠|𠂄:𠂄兜四凶名古文尚書作𦝲
ecg苦官;寬:愛也裕也緩也苦官切二|髖:髖兩股閒也
Ncg借官;鑽:刺也借官切又借玩切六|𩎑:說文曰車衡三束也曲轅𩎈縛直轅𨏮縳|𩎈:-|䡽:+並上同|𣀶:姓出姓苑|劗:剃髮
CcA薄官;槃:器名薄官切二十二|盤:+籀文|鎜:+古文|柈:+俗|瘢:瘡痕|磻:磻溪太公釣處|幋:大巾|磐:大石|䰉:䰉頭屈髮爲之又臥髻也又音班|般:樂也又博干切釋典又音鉢|蹣:蹣跚跛行皃|搫:搫㨏婉轉|鞶:鞶革說文曰大帶也|繁:繁纓馬飾見左傳|𪄀:𪄀𪃑異鳥人面出山海經|𥈼:轉目視也|媻:奢也一曰小妻又媻媻來往皃|縏:番和縣名在涼州|蟠:鼠負蟲又龍蟠也|𪒀:下色|䈲:篾也|𤠍:𤠍狐大也
DcA母官;瞞:目不明也說文曰平目也曹操一名瞞又姓風俗通云瞞氏荊蠻之後本姓蠻其枝裔隨音變改爲瞞氏母官切二十四|顢:顢頇大面皃|謾:欺也慢也|蹣:踰牆|䊡:䊡頭餅也|饅:+俗|慲:忘也|鏝:泥鏝|槾:-|墁:+並上同|㒼:無穿孔狀|鞔:鞔鞋履|樠:木名松心|鰻:鰻䱊魚也|曼:路遠|蔓:蔓菁菜也|䜱:䜱䜪亭名在上艾䜪音求|𤡁:獸似狸也|䟂:行遟皃|𦔔:種遍皃|芇:相當也又亡殄武仙二切|悗:惑也|鬗:長髮|絻:連也
BcA普官;潘:淅米汁又姓周文王子畢公之子季孫食采於潘因氏焉出廣宗河南二望普官切六|㽃:㽃瓳大甎|番:番禺縣在廣州|拌:弃也俗作𢬵|㢖:峙居也|𤺏:弃𤺏
AcA北潘;𤳖:部黨北潘切四|般:般運|䈲:捕魚笱其門可入不可出|𠦒:弃糞器名又姓出姓譜
#刪
VdQ所姦;刪:除削也又定也所姦切又所晏切五|訕:謗也|潸:出涕皃|𣧱:單于別名|狦:說文曰惡健大也又所晏切
ddg古還;關:說文曰以木橫持門戶也聲類曰關所以閉也又姓風俗通云關令尹喜之後蜀有前將軍關羽河東解人古還切六|関:+俗|癏:病也|擐:貫也又音患出文字指歸|𠴨:二鳥和鳴|𢇇:織貫杼也
hdg烏關;彎:說文曰持弓關矢也烏關切五|灣:水曲|䘎:䗡䘎蟲名|𩅦:吳主孫休長子名見吳志|潫:奫潫
Vdg數還;𣠯〈𣟴〉:關門機出通俗文數還切一
jdg戶關;還:反也退也顧也復也戶關切又音旋二十|環:玉環爾雅曰𠟼好若一謂之環又姓古有楚賢者環淵後有環濟撰要略一部|𠟼:樸𠟼縣名在武威樸音蒲|鬟:髻鬟|寰:王者封畿內縣又玄甸切|闤:闤闠崔豹古今注云闤市垣也闠市門也|糫:膏糫粔籹|鍰:六兩曰鍰鍰黃鐵也一曰錢也|圜:圜圍又王權切|鐶:指鐶|轘:轘轅又地名也|𡍦:里名在洛陽|䍺:獸名似羊而黑色無口不可殺也|𦏖:+上同|郇:姓出絳州又音荀|澴:水名|𩙽:𩙽飛遶皃|䭴:馬一歲又音弦|㡲:屋牡瓦名|𦣴:堅𦣴
AdA布還;班:說文曰分瑞玉俗作𤦦亦姓出扶風風俗通云楚令尹鬬班之後布還切十三|頒:布也賜也又音汾|鳻:大鳩|肦:大首又音汾|螌:螌蝥毒蟲|斑:駮也文也|辬:+上同見說文|䰉:髮半白又音盤|般:還師亦作班師又盤𤳖鉢三音|斒:斕斒|鯿:魚名又音編|扳:挽也公羊傳云扳隱而立又音攀|𠔯:賦事之皃
DdA莫還;蠻:南夷名亦姓莫還切七|𪈮:似鳧一目一足一翼相得乃飛即比翼鳥也|獌:狼屬又莫干晚販二切|鬘:衣出釋典|謾:方言曰謾台脅鬩懼也燕代之閒曰謾台齊楚之閒曰脅鬩台音怡|䅼:赤䅼稻名|𪑪:畫車輪也
gdQ五姦;顏:顏容亦顏額又姓出琅邪本自魯伯禽支庶有食采顏邑者因而著族又邾武公名夷字曰顏故公羊傳稱顏公後遂爲氏五姦切二|楌:木名似橦
ddQ古顏;姦:私也詐也古顏切俗作姧四|菅:草名又姓出趙郡或作蕳|葌:香草|䔵:+上同
BdA普班;攀:引也普班切三|扳:+上同又音班|眅:目多白皃
Mdg奴還;奻:訟也奴還切一
gdg五還;𤸷:𤸷痺五還切二|頑:頑愚
edQ丘姦;馯:姓也漢書有江東馯臂字子弓傳易丘姦切一
edQ可顏;豻:胡地野犬似狐而小黑喙可顏切又我悍俄寒二切二|鬜:鬢禿皃
Sdg阻頑;跧:跧伏阻頑切一
#山
VeQ所閒;山:廣雅曰山產萬物說文曰山宣也宣气散生萬物又姓周有山師之官掌山林後以官爲氏或云古烈山氏之後望出河內所閒切三|疝:腹疝痂病山|邖:地名出地理志
deg古頑;鰥:鰥寡鄭氏云六十無妻曰鰥五十無夫曰寡又魚名古頑切三|䤽:䤽犁釬也|綸:爾雅釋草曰綸似綸東海有之說文曰青絲綬也又音倫
deQ古閑;閒:隙也近也又中閒亦姓出何氏姓苑古閑切又閑澗二音六|艱:艱難|囏:+古文|靬:黎靬國名在西域其人善眩幻又犍看二音|蕳:蘭也|覸:視皃
jeQ戶閒;閑:闌也防也禦也大也法也習也暇也戶閒切九|嫺:嫺雅|癇:小兒瘨|𩦂:馬一目白|蛝:蟲名|瞯:人目多白又姓史記濟南瞯氏|鷴:白鷴似雉而尾長四五尺|藖:莖莝餘又音莧|憪:心靜說文愉也
eeQ苦閑;慳:悋也苦閑切八|𧢞:人名出孟子齊景公勇臣成𧢞說文曰很視也|顅:頭髮少皃|掔:爾雅云固也莊子注牢也|鬜:鬢禿皃又苦八切|羥:羊名|臤:堅也又口耕切|𩋆:堅破聲
UeQ士山;虥:虎淺毛皃士山切又音棧又昨閑切七|潺:潺湲水流又士連切|孱:孱劣皃又士連切|僝:僝惡罵也|䡲:䡲輞又士連切|𨬖:小鑿名又士連切|𡎻:𡎻門聚又昨閑切
ieQ許閒;羴:羊臭許閒切又失然切一
geQ五閑;訮:爭也五閑切四|𤡥:犬鬬聲也亦作狠|㗴:訟詞|虤:虎怒
heQ烏閑;黰:染色黑也烏閑切五|𦎣:黑羊|殷:赤黑色也左傳云左輪朱殷|㸶:牛尾色也|黫:黑色出字林
AeA方閑;斒:斒斕色不純也方閑切二|虨:虎文又甫巾切
IeQ力閑;斕:斒斕力閑切四|𢿻〈𣁣〉:+上同|𢛓:地名出玉篇|潾:水皃又力人切
MeQ女閑;嘫:語聲女閑切二|㬮:暍㬮煖狀
YgQ充山;㺗:噬也充山切一
heg委鰥;𡣬:媚容也委鰥切一
Leg墜頑;窀:穴中見火墜頑切又陟倫切一
IFg力頑〈規〉;𡰠:𡰠𡰝𦝫膝痛也力頑切一
fgo跪頑;𡰝:跪頑切一
JeQ陟山;譠:謾也陟山切又他單切二|㣶:廣蒼云走也藏也
LeQ直閑;𤣆:獸走皃直閑切又丑連切一
jeg獲頑;湲:水流皃獲頑切一
UeQ昨閑;虥:虎淺毛皃昨閑切二|𡎻:𡎻門聚
#先
QfQ蘇前;先:先後也又姓左傳晉有先軫蘇前切又蘇薦切四|躚:蹁躚旋行皃|蹮:+上同|𥑻:石次玉也
PfQ昨先;前:先也昨先切六|歬:+古文|騚:馬四蹄皆白也|湔:湔葫藥名|𥮒:說文曰蔽絮簀也或作𥮓𥷰上同|𥷰:+上同
OfQ蒼先;千:十百也又漢複姓有千乘氏出何氏姓苑蒼先切九|圱:三里爲圱|阡:阡陌南北爲阡東西爲陌|汘:水名|仟:千人之長也又仟眠廣遠也|芊:草盛|谸:說文曰望山谷之谸青也|迁:伺候也進也又迁葬又標記也|杄:木名
NfQ則前;箋:說文曰表識書也則前切十五|牋:+上同|㮍:+古文|瀳:水名說文曰水至也又才薦切|帴:小兒藉也|韉:鞍韉|淺:淺淺流疾皃又倉翦切|湔:水名出蜀郡玉壘山|𢃬:旛幟|𣚙:小栗名趙魏閒語也|轃:大車簀也|濺:濺疾流皃又子賤切|籛:楚人革馬簻鞍韉又彭祖姓|𣝕:香木|𨕨〈𨔥〉:埤蒼云至也說文云自進極也
FfQ他前;天:上玄也說文曰顛也至高無上从一大也爾雅曰春爲蒼天夏爲昊天秋爲旻天冬爲上天他前切六|𠀘:-|䒶:+並古文|𦧝:𦧝𦧴語不正也|吞:姓也漢有吞景雲又湯門切|訮:訮訶皃
dfQ古賢;堅:固也長也強也又姓漢二十八將有揚化將軍潁川堅鐔古賢切十七|鋻:剛也又古宴切|𢮂:縣名在東萊又音弦|㡉:布名|幵:說文曰平也兩干對舉又羌名今作开同又音牽|肩:項下又任也克也作也媵也又姓出姓苑|鳽:鵁鶄鳥名又五革五堅二切|豜:大豕也一曰豕三歲|𧱚:+上同|猏:+俗|菺:茙葵也今蜀葵|𪊑:鹿有力又音牽|麉:+上同|鵳:鶙鵳鷂屬|鰹:鮦大曰鰹小曰鮵鮵音奪|䶬:說文曰龍鬐脊上䶬䶬|䌑:緊也
jfQ胡田;賢:善也能也大也亦姓胡田切十七|臤:+古文又口閒切|弦:弓弦五經文字曰其琴瑟弦亦用此字作絃者非說文作𢎺又姓風俗通云弦子後左傳鄭有商人弦高晉有弦超|絃:+俗見上注|舷:船舷|胘:肚胘牛百葉也|蚿:馬蚿蟲一名百足|𢛆:亭名在密縣說文云急也|𠛑:自刎頸也|伭:說文作𠆺泿也|𢮂:縣名又音堅|𦱁:草名|婱:婦人守志|𧼏:疾走|礥:艱險又剛強也|痃:痃癖病|㘋:難也
hfQ烏前;煙:火氣也烏前切十二|烟:+上同|𡨾:+古文|𤎟:+籀文|燕:國名亦州又姓邵公奭封燕爲秦所滅子孫以國爲氏漢有燕倉又於薦切|咽:咽喉|橪:橪支香草|驠:馬竅白|湮:爾雅云落也又音因|胭:胭項|𥷀:竹名|閼:閼氏單于適妻也氏音支
IfQ落賢;蓮:爾雅云荷芙蕖其實蓮落賢切八|憐:愛也又哀矜也|怜:+俗|嗹:連嘍言語繁挐皃|縺:縺縷寒具|𪍴:𪍴𪍣餅也|𨏩:𨏩𨻻縣在交趾|零:漢書云先零西羌也本力不切
GfQ徒年;田:釋名曰土已耕者曰田田填也五稼填滿其中也又姓出北平敬仲自陳適齊後改田氏九代遂有齊國徒年切十九|佃:作田也說文云中也春秋傳曰乘中佃一轅車古輕車也又音甸|畋:取禽獸也又音甸|畇:地名在絳|填:塞也加也滿也又陟陳切|窴:+上同字統云窴顏府在北州|闐:轟轟闐闐盛皃|䟧:蹋地聲|𦧴:𦧴𦧝語不正也又他丹切|鈿:金花又音甸|䡘:䡘䡘眾車聲|沺:字林云沺沺水勢廣大無際之皃|磌:柱礎|鷏:蚊母鳥也|嗔:說文曰盛气也|𨌈:呂氏春秋云天子𨌈𨌈敐敐莫不載悅敐音軫|滇:滇㴐大水皃又都年切|貚:貙屬|搷:擊也
HfQ奴顛;秊:穀熟曰秊奴顛切三|年:+上同|𨚶:鄉名在馮翊
EfQ都年;顛:頂也又姓左傳晉有顛頡都年切十五|㒹:+上同|齻:牙齻儀禮曰右齻左齻鄭玄云齒堅也|𩥄:馬額白今戴星馬|槙:木上|瘨:病也|癲:+上同|滇:滇池在建寧|𧽍:走頓|巔:山頂也|驒:驒騱野馬|𠑘:𠑘隕也又倒也|傎:+同上|蹎:蹎仆說文跋也|厧:厧家
efQ苦堅;牽:引也挽也連也亦姓晉有牽秀何氏姓苑云武邑人苦堅切九|縴:縴𦃇惡絮|邢:地名在河內|汧:水名在安定說文曰水出扶風西北入渭爾雅云汧出不流又苦薦切|蚈:螢火又古奚切|𪊑:鹿之絕有力者亦作麉|掔:固也厚也持也又音慳|岍:山名在京兆書曰導岍及岐|雃:說文曰石鳥一名雝𪆂一曰精𠛱又秦公子名士鳽
gfQ五堅;妍:淨也美也好也五堅切八|鳽:鵁鶄也又古賢五革二切|研:磨也|𥓋:+上同|揅:揧破|㿼:醆也|趼:獸跡|俓:急也又牛耕切
DfA莫賢;眠:寐也莫賢切七|瞑:+上同說文曰翕目也又音麵|䏃:埤蒼云注意而聽也|矏:爾雅曰密也|𥌂:+上同|䰓:燒煙畫眉|㝰:不見
CfA部田;蹁:蹁蹮旋行皃部田切十二|蠙:蠙珠|骿:并肋|軿:四面屏蔽婦人車又房丁切|駢:并駕二馬|㼐:黃瓜名|胼:胼胝皮上堅也|跰:+上同|楄:木名食不噎又杜預云楄部棺中露牀也|賆:益也|玭:蚌珠或與蠙同|琕:+上同
hfg烏玄;淵:深也管子曰水出而不流曰淵又姓世本有齊大夫淵湫烏玄切十|𠝃:+上同|囦:+古文|㾓:骨節疼也|弲:弓勢|剈:曲翦|鼘:鼓聲|𨓯:行皃|䨊:鳥羣|蜎:蜎蠉入毆泫切
dfg古玄;涓:說文曰小流也又姓列仙傳有齊人涓子古玄切八|睊:視皃|蠲:除也潔也明也說文曰馬蠲蟲明堂月令曰腐草爲蠲|𦮻:草名|䅌:麥莖|鵑:杜鵑鳥|焆:明也|鞙:鞙馬尾也又胡犬切
ifg火玄;鋗:銅銚火玄切五|駽:爾雅曰青驪駽郭璞云今之鐵驄|㘣:規也又辭沿切|梋:椀屬|矎:直視
AfA布玄;邊:畔也又邊陲也近也厓也方也又姓出陳留北平二望陳留風俗傳云祖于宋平公布玄切十四|籩:竹器|𤄺:水名出番侯山|甂:小盆|蝙:蝙蝠仙鼠又名伏翼|猵:獺屬|𥣰:籬上豆也又北典切|編:次也又方泫切|萹:萹竹草又北泫切|𨇱:足趾不正|𠑟:身不正也|牑:牀上版也|䟍:說文走意|蹁:行不正皃又薄邊切
jfg胡涓;玄:黑也寂也幽遠也又姓列仙傳有玄俗河閒人無影胡涓切十三|縣:說文云繫也相承借爲州縣字|懸:+俗今通用|眩:亂也又胡練切|䮄:馬一歲|玹:石次玉|玆:說文曰黑也春秋傳曰何故使吾水玆本亦音滋按本經只作滋|𧟨:吳王次子名|𥌭:自童子也|伭:說文很也|盷:目大皃|胘:牛百葉又音弦|訇:說文云漢中西城有訇鄉
ifQ呼煙;祆:胡神官品令有祆正呼煙切二|訮:訶也怒也
XpT崇〈？〉玄〈？〉;｛𤜼｝【「犳」（章開三陽入）之訛字】:獸似豹而少文崇玄切一
#仙
QgQ相然;仙:神仙釋名曰老而不死曰仙仙遷也遷入山也故字從人旁山相然切十二|僊:+上同又僊僊舞皃|𠑗:+古文|㲔:㲔㲍罽也|䉳:竹名又音癬|苮:草名似莞|躚:舞皃|秈:秈稻|鮮:鮮潔也善也又鮮卑山因爲國号亦水名水經曰北鮮之山鮮水出焉又姓後蜀錄李壽司空鮮思明又漢複姓鮮于氏|硟:衧繒石也|鱻:說文曰新魚精也|廯:倉廩
PgQ昨仙;錢:周禮注云錢泉也其藏曰泉其行曰布取名於水泉其流行無不徧也又姓晉有歷陽太守錢鳳昨仙切二|𧔢:方言云鳴蟬也
OgQ七然;遷:去下之高也詩云遷于喬不七然切八|𨙙:+古文|𠨧:+上同|𨝍:地名|櫏:桾櫏木名|䉦:䇹䉦竹名|韆:鞦韆繩戲|㿊:痛也
NgQ子仙;煎:熟煑子仙切四|湔:洗也一曰水名出蜀玉壘山|葏:草茂皃出字林|鬋:女鬢垂皃
cgQ如延;然:語助又如也是也說文曰燒也俗作燃又姓左傳楚有然丹何氏姓苑云今蒼梧人如延切九|燃:+俗見上注|𤡮:猓𤡮獸名似猿白質黑文|㜣:姓也|肰:犬𠟼|繎:絲勞皃|𥳚:竹名|䕼:草名|𤓉:陸佐公石闕銘云刑酷𤓉炭
lgQ以然;延:稅也遠也進也長也陳也言也亦州漢高奴縣隋改延川爲延安郡又姓漢有延篤南陽人爲京兆尹殺梁冀使者以然切十三|埏:際也地也又墓道亦地有八極八埏又音羶|筵:席也鋪陳曰筵藉之曰席|狿:獌狿大獸名|郔:地名在鄭|綖:冠上覆也|蜒:蚰蜒|䘰:㠾䘰牛領上衣|鋋:小矛又市連切|䀽:相顧視也|𨕐〈𢌨〉:+上同|䢭:行皃|莚:草名
XgQ諸延;𩜾:厚粥也諸延切八|饘:+上同|旃:之也爾雅曰因章爲旃郭璞云以帛練爲旒因其文章不復畫之也世本曰黃帝作旃亦曲柄旗以招士眾也或作旜又姓出姓苑|旜:+上同|栴:栴檀香木|氈:席也周禮曰秋斂皮冬斂革供其毳毛爲氈|鸇:晨風鳥|𩔣:江湘閒人謂額也
dgU居延;甄:察也一曰免也居延切又章鄰切三|薽:草名一曰豕首又名彘盧|籈:竹器
JgQ張連;邅:迍邅也又移也張連切又直連雉戰二切五|𧾍:+同上行難也說文曰趁也又直然切|驙:馬載重行難又白馬黑脊曰驙又徒安切|鱣:詩云鱣鮪發發江東呼爲黃魚|𩼼:+上同
UgQ士連;潺:潺湲水流皃士連切五|孱:不肖也漢書曰吾王孱王也|𨬖:小鑿|䡲:軒輞|𡎻:門聚
agQ式連;羶:羊臭也式連切八|埏:打瓦也老子注云和也|挻:柔也繫也和也取也長也或作煽|扇:扇涼又式戰切|煽:火盛也又式戰切|鯅:魚醬|脠:生𠟼醬又丑延切|䘰:㠾䘰牛領上衣又音延
KgQ丑延;脠:魚醢也說文云𠟼醬丑延切四|梴:木長|鏈:鉛礦也又力延切|㢟:說文曰安步㢟㢟也
ZgQ市連;鋋:小矛方言曰五湖之閒謂矛爲鋋市連切又以然切九|單:單于又丹善二音|蟬:蜩也禮記仲夏之月蟬始鳴孟秋之月寒蟬鳴援神契曰蟬無力故不食也|撣:撣援牽引|儃:態也|僤:+上同|禪:靜也又市戰切|澶:杜預云澶淵地名在頓丘縣南又音纏|嬋:嬋娟好皃
LgQ直連;纏:繞也又姓漢書藝文志有纏子著書直連切十|緾:+俗餘皆倣此|躔:日月行也說文曰踐也|瀍:水名在河南|鄽:市鄽|𨷭:市門|𧾍:移也又張連切|𧔊:守宮別名|廛:居也說文曰一畮半也一家之居也|㙻:+上同
igY許延;嘕:笑皃許延切四|仚:輕舉皃說文曰人在山上也|嫣:長皃好皃又於建於遠二切|𦒜:飛皃
IgQ力延;連:合也續也還也又姓左傳齊有連稱又虜複姓六氏西秦丞相出連乞都後魏書官氏志云南方宥連氏後改爲雲氏是連氏改爲連氏費連氏改爲費氏綦連氏改爲綦氏又有赫連氏力延切十三|聮:聮綿不絕說文作䏈|漣:漣漪風動水皃|翴:翴翩飛相及皃|鰱:魚名|𤣆:𤣆猭兔走皃|令:漢書云金城郡有令居縣顏師古又音零|鏈:鉛礦又丑延切|䃛:+上同|㦁:說文曰泣下也|槤:簃也又橫關柱又木名|𪚀:齒露也|㶌:㶌水名出王屋山
BgE芳連;篇:篇什也又姓周大夫史篇之後芳連切七|偏:不正也鄙也衺也又姓急就章有偏呂張|翩:飛皃|媥:身輕便皃|㾫:身枯|扁:小舟|萹:萹茿可食又補殄切
CgE房連;便:辯也僻也安也又姓漢有少府便樂成房連切又去聲九|緶:縫也|楩:木名|平:書傳云平平辨治也又皮明切|諞:巧言又符蹇切|㛹:㛹娟美好|箯:竹輿|𧍲:𧍲䗠沙蝨也亦作𧍻|楄:木名食之不咽
DgE武延;緜:精曰緜麤曰絮說文曰䏈微也又姓晉張方以綿思爲腹心武延切十七|綿:+上同|棉:屋聮棉又木棉樹名吳錄云其實如酒杯中有綿如蠶綿可作布又名曰緤羅浮山記曰正月花如芙蓉結子方生葉子內綿至蠶成即熟廣州記云枝似桐枝葉如胡桃葉而稍大也|謾:欺也|矊:瞳子黑又矊眇遠視|蝒:馬蜩蟬中最大者|𧉄:+上同說文曰𧉅蚗蟬屬|矏:密緻皃|𢣔:忘也|芇:說文曰相當也今人賭物相折謂之芇|宀:深屋|䫵:雙生|櫋:說文曰屋聮櫋也|𣏜:木名|臱:視遠之皃|㮌:木名|𣡠:𣡠密也
Pgg疾緣;全:完也具也又姓吳有大司馬全琮疾緣切七|㒰:+上同見說文|泉:水源也又錢別名|𧍭:貝也白質黃文|牷:牛全色書傳云體完曰牷|䀬:目眇視皃|葲:𦭵葲草也
Qgg須緣;宣:布也明也徧也通也緩也散也須緣切九|揎:手發衣也|㩊:+上同|䳦:𪀠䳦小鳥𪀠音旬|愃:吳人語快說文曰寬嫺心腹皃|𡈣:面圓也|𩕖:頭圓也|瑄:爾雅曰璧大六寸謂之瑄郭璞曰漢書所云瑄玉是也|𩤡:𩤡額
Ngg子泉;鐫:鑽也斲也子泉切四|鋑:+古文|脧:縮肭|剶:𠜖也又丑全切
igk許緣;翾:小飛許緣切九|儇:智也疾也利也慧也又舞皃|弲:角弓皃|蠉:蟲行皃|𧾎:疾走皃|嬛:便嬛輕麗皃又音娟音瓊|譞:智也|頨:頨妍美頭|𥌭:目童子也
cgg而緣;堧:江河邊地又廟垣或從需餘同而緣切六|䙇:促衣縫也|𤲬:城下田也|瑌:瑌珉也玉佩也|撋:摧物也|繎:繎絲難理
Ygg昌緣;穿:通也孔也昌緣切三|川:山川也蔡邕月令章句曰眾流注海曰川釋名曰川者穿也穿地而流也|灥:三泉
lgg與專;沿:從流而下也與專切十二|㳂:+上同|鉛:說文曰青金也一曰錫之類也|鈆:+上同|櫞:枸櫞樹皮可作粽埤蒼云果名似橘|捐:弃也|鳶:鴟類也|蝝:蝗子一曰蟻子|緣:緣由又羊絹切|䱲:魚名|𦿂:郭璞云𦿂尾草一名射干|𦛔:短也
Rgg似宣;旋:還也疾也似宣切十七|檈:圜案|璿:玉名|𤩅:+上同|𤫀:+籀文|䗠:𧍲䗠沙蝨|㳬:回㳬|琁:美石次玉|璇:+上同|𣟳:說文曰𣟳味稔棗也|蜁:蜁蝸蝸螺也|㔯:漉米竹器|還:還返|㘣:規也又火玄切|䁢:好皃|嫙:+上同|鏇:圓轆轤也
hgk於緣;娟:便娟舞皃嬋娟好姿態皃於緣切七|嬛:身輕便皃|悁:悁憂悒也|蜎:蠋皃又狂兗切|𡷡:山曲|潫:水深|𡣬:娥眉說文曰好也
bgg食川;船:方言曰關西謂之船關東謂之舟又姓出姓苑食川切二|舩:+上同
AgE卑連;鞭:馬策也卑連切六|鯾:魚名|鯿:+上同|編:次也又布千方典二切|箯:竹輿|揙:揙擊
RgQ夕連;㳄:口液也夕連切二|涎:+上同
Ogg此緣;詮:平也說文具也此緣切十九|銓:銓衡也又量也次也度也|硂:+上同|痊:病瘳|佺:偓佺仙人|悛:改也止也|駩:白馬黑脣|筌:取魚竹器|絟:細布|譔:善言|謜:言語和悅|縓:爾雅曰一染謂之縓今之紅也又采選切|恮:謹皃|荃:香草|𠛮:剔也|峑:山巔|𠥙:簙也又竹器名|鐉:說文曰所以鉤門戶樞也一曰治門戶器也|拴:+揀也俗
Xgg職緣;專:擅也單也政也誠也獨也自是也亦姓吳刺客專諸職緣切十二|甎:甎瓦古史考曰烏曹作甎|顓:顓頊又姓神仙傳有太玄女姓顓頊名和|篿:楚詞云索瓊茅以筳篿兮王逸云折竹卜曰篿又音團|嫥:可愛之皃|諯:說文曰數也一曰相讓又尺絹市專二切|湍:水名在鄧州又音煓|膞:膞鳥胃也|鱄:魚名專諸吳刺客或作鱄|鷒:鳥名又徒端切|𩠹:𩠹斷首出玉篇|鄟:邾䣚邑名
Zgg市緣;遄:速也疾也市緣切八|篅:說文曰以判竹圜以盛穀也|圌:+上同|諯:又職緣尺絹二切|輲:無輪車名|輇:+上同|椯:木名|歂:字林云口氣引也又姓史記有歂師
kgo王權;員:說文作員物數也王權切又云運二音四|圜:天體|圓:+上同|湲:潺湲
Sgg莊緣;恮:曲卷也莊緣切四|跧:屈也伏也蹴也|䀬:目眇視也|蟤:蜿蟤蛇名
Vgg山員;栓:木丁也山員切二|𨏉:𨏉車軸也
Kgg丑緣;猭:𤣆猭兔走皃丑緣切二|剶:去木枝也
fgY渠焉;乾:天也君也堅也渠焉切又音干九|虔:恭也固也殺也說文曰虎行皃又姓陳留風俗傳云虔氏祖於黃帝|犍:犍爲縣在嘉州|鰬:魚名|𨜻:聚名在河東聞喜也|騝:騮馬黃脊|榩:廩也構木爲之|鍵:鑰也又音件|揵:舉也
egY去乾;愆:過也去乾切十|䇂:+古文|諐:+籀文|𠎝〈𠍴〉:+俗|褰:褰衣|騫:虧少一曰馬腹縶亦姓風俗通云閔子騫之後吐谷渾視熊博士金城騫包|䙭:齊魯言袴又己偃切|𧽐:蹇足跟也|攐:縮也|㗔:方言曰㗔㗔歡皃
fgo巨員;權:權變也反常合道又宜也秉也平也稱錘也又爾雅曰權黃華又姓出天水本顓頊之後楚武王使鬭緍尹權後因氏俗作槯巨員切二十三|拳:屈手也廣雅云拳拳憂也又拳拳奉持之皃又姓衛大夫拳彌|狋:狋氏縣在代郡氏音精|觠:曲角|顴:頰骨|踡:踡跼不行|婘:美皃|孉:+上同|䠰:曲脊行也|𤷄:手屈病也|犈:牛黑耳又音卷|蠸:食瓜葉黃甲蟲|齤:齒曲|卷:曲也又九免九院二切|𪈻:𪈻鵒也|𥆗:大視皃又音倦|𥁠:盌也|𢑆:弓曲|鬈:髮好也又胡人髮也又音棬|䟒:曲走皃|䑏:䑏𦝢醜皃|蜷:蟲形詰屈|捲:說文云气勢也國語曰予有捲勇
Lgg直攣;椽:屋桷也直攣切二|傳:轉也又持戀切又丁戀切
Igg呂員;攣:攣綴呂員切三|𤼙:病也亦作𤼣|䜌:南䜌縣在鉅鹿
ego丘圓;弮:古縣名在滎陽丘圓切五|㒽:小幘|棬:器似升屈木作|鬈:髮好皃|𨟠:鄉名在聞喜
hgY於乾;焉:何也又鳥雜毛說文曰鳥黃色出江淮閒於乾切五|閼:閼氏單于妻又音遏|蔫:物不鮮也|嫣:長皃又人名|鄢:人姓又鄢陵縣名又於晚切亦作傿
kgY有乾;漹:水名出西河也有乾切三|䗡:䗡䘎蟲名|焉:語助也又於乾切
hgo於權;𡣬:娥眉皃於權切二|潫:水深皃
YgQ尺延;燀:火起皃尺延切一
EMQ丁全〈兮〉;𡰝〈𡰖〉:行不正皃丁全切一
dgo居員;勬:強健也居員切一
#蕭
QhQ蘇彫;蕭:蒿也詩云采蕭穫菽亦縣名在沛郡新語云蕭斧名又姓出蘭陵廣陵二望本自宋支子食采於蕭後因爲氏漢侍中蕭彪始居蘭陵彪玄孫望之居杜陵望之孫紹復還蘭陵紹十一代孫整始過江爲廣陵人風俗通云宋樂叔以討南宮萬立御說之功受封於蕭列附庸之國漢相國蕭何即其後氏也蘇彫切十六|簫:樂器風俗通云舜作簫其形參差以象鳳翼|彇:弓弭|蟰:蟰蛸蟲一名長蚑出崔豹古今注|橚:橚槮樹長皃|潚:水名|𩙚:涼風|踃:跳踃|㩋:擊也又把也|箾:舞箾說文云以竿擊人也又音朔|𦐺:羽翼敝皃|㲖:+上同|艘:船摠名又音騷|瞍:目無眸子曰瞍又音藪|翛:翛翛飛羽聲|撨:擇也
FhQ吐彫;祧:遠祖廟也吐彫切十一|佻:輕佻爾雅曰佻偷也|挑:挑撥|朓:月見西方又吐了切|恌:輕薄|𣂁:斗旁耳又爾雅云𣂁謂之疀古田器也郭音鍫|庣:不滿之皃|銚:田器|趒:雀行又他弔切|聎:耳疾|蓧:苗也
EhQ都聊;貂:鼠屬出東北夷又姓出姓苑都聊切二十二|䯾:小兒留髮|𠚥:斷穗|刁:軍器纂文曰刁斗持時鈴也又姓出渤海風俗通云齊大夫豎刁之後俗作刀|琱:琱琢|凋:凋落|鯛:魚名|䂏:短尾犬也|雕:鶚屬又姓漢武帝功臣表有雕延年|鵰:+籀文|蛁:蛁蟟茆中小蟲|彫:彫刻亦作雕|𧜣:說文云短衣也|𧘨:死人衣|䒒〈芀〉:葦華也又音調|𦶌:𦶌葫茭實|𦨣:吳船|𩾗:𩾗鷯剖葦求蟲食似雀青班色|㚋:大也多也|奝:+上同|弴:天子弓也說文曰畫弓也詩又作敦又丁昆切|瞗:熟視
GhQ徒聊;迢:迢遰徒聊切二十二|條:小枝也貫也教也爾雅云柚條似橙而實酸又姓左傳殷人七族有條氏後趙錄冉閔司空條攸姓苑云安定人|樤:柚條或從木|髫:小兒髮俗作齠|跳:躍也|鋚:紖頭銅飾|𧌁:𧌁䗤狀如黃蛇魚翼出入有光見則大旱出山海經|蜩:大蟬|佻:獨行皃詩曰佻佻公子|趒:說文曰雀行也|苕:苕菜詩云邛有旨苕|芀:葦華|調:和也又姓周禮有調人其後氏焉又徒料切|鮡:魚名|岧:岧嶤山高皃|䯾:多髮皃又音凋音綢|䩦:革轡詩云䩦革沖沖|嬥:聲類云細腰皃|𠤼:田器|𣬸:𣬸㲖毛皃|𠧪:草木實垂𠧪𠧪然也|鰷:白鰷魚名
dhQ古堯;驍:驍武也古堯切九|梟:說文云不孝鳥也故日至捕梟磔之从鳥頭在木上又姓隋煬帝誅楊玄感改其姓爲梟氏|𥄉:到懸首漢書曰三族令先黥劓斬左右趾𥄉首葅其骨謂之具五刑|澆:沃也薄也|憿:憿幸或作儌又作僥倖|釗:覿也遠也亦弩關一云周康王名又作䙼又指遙切|邀:遮也又於宵切|蟂:水蟲似蛇四足能害人也|徼:求也抄也又音叫
IhQ落蕭;聊:語助也亦姓風俗通有聊倉爲漢侍中著子書又有聊氏爲潁川太守著萬姓譜落蕭切四十二|𦗖:耳中鳴也又力刀切|膋:腸閒脂也|膫:+上同|飉:風也|遼:遠也又水名|憀:無憀賴也|竂:穿也|寥:空也又寂寥也寥廓也|料:料理也量也又郎弔切|㙩:周垣|橑:蓋骨亦椽也又力道切|撩:取物又理也|摷:擊也又側交切|廖:人名左傳有辛伯廖又力救切|僚:同官爲僚又姓左傳晉陽氏大夫僚安|寮:+上同|鐐:有孔鑪又紫磨金也爾雅曰白金曰銀其美謂之鐐|簝:宗廟盛𠟼方竹器|豂:空谷|鷯:鷦鷯|𥲊:竹名|璙:玉名|嫽:相嫽戲也又力弔切|漻:水清也|蟟:蛁蟟|瞭:目明也|䜮:谷名|𧂏:草木疎莖|𩯊:細長|嶚:嶚𡻝山皃|翏:高飛皃|繚:繚綾經絲出字林|憭:空皃|獠:夜獵也又知卯盧皓二切|髎:臗骨名|𡽐:崖虛|蟧:馬蟧大蟬|𦿌:草器力戈切|敹:揀擇|嘹:嘹亮聞遠聲又力弔切|熮:說文曰火皃
ghQ五聊;堯:至高之皃謚法曰翊善傳聖曰堯五聊切五|嶢:嶕嶢山危|僥:僬僥國名人長一尺五寸一云三尺|垚:土高皃|顤:頭高長皃
ihQ許幺;膮:豕羹也許幺切七|嘵:懼聲詩曰予維音之嘵嘵|憢:憢憢懼也|㚠:長大皃|𦞵:𦠎𦞵腫欲潰也|䎄:䎄㲖毛皃|䫞:大額又去遙切
hhQ於堯;幺:幺麼小也於堯切五|怮:怮怮憂也又一虯切|葽:草盛皃|䱂:魚名|㫐:望遠也
ehQ苦幺;鄡:鄡陽縣名在鄱陽又姓出何氏姓苑苦幺切五|郻:縣名在鉅鹿郡|𢿣:玉篇云擊也|墽:地名說文磽也|𡩇:𡩇寥空也
#宵
QiQ相邀;宵:夜也相邀切二十|消:滅也盡也息也|霄:近天氣也|捎:搖捎動也又使交切|逍:逍遙|痟:痟渴病也司馬相如所患|綃:生絲繒也|銷:鑠也|焇:+上同|硝:硭硝藥名|蛸:螵蛸蟲也爾雅注云一名䗚蟭亦姓南齊武帝改其子巴東主子響爲蛸氏又所交切|莦:草名又使交切|哨:口不正也又七笑切|𦐺:鳥毛羽也|鮹:魚名又所交切|𤞚:狂也出文字集略|䴛:煎鹽|揱:長臂又交色角二切|奞:張羽又先準切|魈:山魈出汀州獨足鬼
KiQ敕宵;超:說文曰跳也又姓漢有太僕超喜敕宵切六|怊:悵恨|欩:健也|𢁾:細絲|𠰉:鳴也|䫿:涼風
JiQ陟遙;朝:早也又旦至食時爲終朝又朝鮮國名亦姓左傳有蔡大夫朝吳陟遙切又直遙切二|𦩻:+古文
LiQ直遙;鼂:蒼頡篇云蟲名亦姓風俗通云衛大夫史𪓙之後漢有𪓙錯直遙切又陟遙切五|晁:+上同|鼂:+古文|朝:朝廷也禮記曰諸侯於天子五年一朝又姓唐有拾遺朝衛|潮:潮水
iiY許嬌;囂:喧也許嬌切又五刀切十|枵:玄枵虛危之次|歊:熱氣說文曰歊歊氣出皃|毊:大磬也爾雅注云形如犁錧以玉石爲之又音喬|獢:猲獢短喙犬也|㺧:犬黃白色|藃:草皃又火交切|呺:呺然大皃|𩱴:炊氣|䖀:白芷別名
PiQ昨焦;樵:柴也說文木也昨焦切十五|𦿕:+上同|劁:刈草|憔:憔悴瘦也|顦:+上同|䏆:耳中聲又音曹|譙:國名又姓蜀有譙周|嶕:嶕嶢|𡻝:嶚𡻝山高皃又音巢|鐎:又音焦|𨝱:縣名|僬:又音焦|䩌:面枯皃又音焦|撨:取也|菬:草名
diY舉喬;驕:馬高六尺舉喬切九|嬌:女字亦態|憍:憐也恣也本亦作驕|穚:禾秀|鷮:鷮似雉而小走鳴長尾|蕎:藥名一名大戟|喬:爾雅云句如羽喬郭璞曰樹枝曲卷似鳥毛羽|簥:大管名也|撟:舉手
NiQ即消;焦:傷火也又姓周武王封神農之後於焦後以國爲氏出南安即消切十七|𤓪:+籀文|㲬:兜鍪上毛飾|蕉:芭蕉|膲:人之三膲|鷦:鷦鵬南方神鳥似鳳又鷦鷯小鳥|𩾗:+上同|椒:木名爾雅云檓大椒又椒榝醜莍莍實也應劭漢官儀曰皇后稱椒房以椒塗壁取其溫也又山巔亦姓楚有大夫椒舉|茮:+上同|噍:啁噍聲|鐎:刁斗也溫器三足而有柄|蟭:䗚蟭螗蜋卵也|䩌:面䩌枯也|𪚱:灼龜不兆也亦作𪚰|僬:義見僥字|燋:傷火說文曰所以然持火也|䌭:生枲也
ciQ如招;饒:益也飽也餘也又姓風俗通云漢有饒斌爲漁陽太守如招切六|橈:楫也又女教切|襓:劒衣|㹛:牛馴伏又而沼切|蟯:人腹中蟲|蕘:芻蕘
aiQ式招;燒:火也然也式招切又式照切二|𤬖:瓜名
liQ餘昭;遙:遠也行也餘昭切三十六|媱:美好|傜:使也役也又喜也或作㑾|繇:於也由也喜也詩云我歌且繇|颻:飄颻|𣣳:氣出皃|窯:燒瓦窯也|窰:+上同|䔄:蒲葉也又草也|𦾺:𦾺芅萇楚今羊桃也爾雅作銚|珧:玉珧蜃甲|鰩:文鰩魚鳥翼能飛白首赤喙常游西海夜飛向北海|銚:燒器亦古田器又姓後漢衛尉潁川銚期又徒弔切|姚:姚悅美好皃又舜姓今出吳興南安二望左傳有鄭大夫姚句耳|搖:動也作也又姓東越王搖句踐之後|謠:謠歌也爾雅云徒歌謂之謠|軺:說文曰小車也又音韶|愮:憂也悸也邪也惑也|恌:+上同|𨙂:疾行又音由或作繇|陶:皋陶舜臣又徒刀切|蘨:草茂也又音由|𤬖:瓜也|鷂:大雉名爾雅云青質五彩皆備成章曰鷂又音曜|洮:五湖名風土記云陽羨縣西有洮湖別名長塘湖義興記曰太湖射湖貴湖陽湖洮湖是爲五湖|烑:光也|𢋇〈㿁〉:痤也|𢑄:弓利|㫍:旗旒|榣:木名|嗂:樂也說文喜也|䠛:跳䠛行步皃|瑤:美玉|猺:獸名又獏猺狗種也|餆:餆餌食|褕:褕狄后衣亦作揄
ZiQ市昭;韶:舜樂也紹也市昭切十|㲈:+上同|佋:廟佋穆也或作昭父昭子穆孝經疏云昭明也穆敬也故昭南向穆北向孫從父坐又市沼切|𦯐:草名|𠧙:十問|玿:美玉|𢃳:擊也|軺:使車又音遙|柖:說文曰樹搖皃又射的也|㸛:㸛牀別名
XiQ止遙;昭:明也光也著也覿也又姓楚詞昭屈景三族戰國策楚有昭奚恤止遙切七|鵃:鶻鵃鳥也又竹交切|鉊:淮南人呼鎌|招:招呼也來也又姓漢有大鴻臚招猛|釗:遠也見也勉也亦弩牙又周康王名|盄:玉篇器也|皽:皮上𦞙膜
AiE甫遙;飆:風也俗作飈甫遙切十五|標:舉也又木杪也又必小切|猋:群犬走皃|杓:北斗柄星天文志云一至四爲魁五至七爲杓又音漂|瘭:瘭疸病名|幖:頭上幟也|熛:飛火|㠒:山峯|𧽤:輕行|蔈:爾雅曰黃華蔈郭璞云苕華色異名亦不同也|驫:眾馬走皃|𦠎:𦠎𦞵腫欲潰也|𣄠:旌旗飛揚皃|贆:貝居陸也|髟:髮長皃又所銜切
AiI甫嬌;鑣:馬銜甫嬌切七|𧥍:+上同|臕:脂臕肥皃|儦:行皃詩云行人儦儦|瀌:雪皃詩云雨雪瀌瀌|𦔩:除田薉也亦作穮|藨:萑葦秀爾雅云猋藨芀
CiE符霄;瓢:瓠也方言云蠡或謂之瓢論語曰一瓢飲符霄切六|飄:老子曰飄風不終朝注云疾風也|剽:爾雅云中鏞謂之剽又小輕也或作𠠧|薸:方言云江東謂浮萍爲薸|𣞈〈㯱〉:橐也又公混切|螵:螵蛸蟲名又撫招切
DiE彌遙;蜱:蟲名彌遙切五|䖢:蠶初生也|篻:竹名|㠺:玉篇云細網也|𪃦:工雀
DiI武瀌;苗:田苗亦夏獵曰苗又求也眾也禾秀也亦姓風俗通云楚大夫伯棼之後賁皇奔晉食采於苗因而氏焉武瀌切五|描:描畫也又音茅|緢:說文曰旄絲也|貓:獸捕鼠又爾雅曰虎竊毛謂之虦貓又武交切|猫:+俗
hiU於霄;要:俗言要勒說文曰身中也象人要自臼之形今作腰又姓吳人要離之後漢有河南令要兢於霄切又一笑切九|腰:+見上注亦作𦝫|葽:秀葽草也|喓:蟲聲|𧍔:蛇名|䙅:䙅襻|邀:邀遮又音梟|䳩:鳥名似山鷄而長尾|蟯:腹中蟲又如消切
kiY于嬌;鴞:鴟鴞于嬌切二|𨚙:鄉名在淯
fiY巨嬌;喬:高也說文曰高而曲也又虜姓前代錄云匈奴貴姓喬氏代爲輔相巨嬌切十六|橋:水梁也又姓出梁國後漢有太尉橋玄|趫:善走又去遙切|僑:寄也客也|㝯:+上同|鐈:似鼎長足|鷮:雉名又音驕|嶠:亦作㠐山銳而高又其廟切|毊:大磬又虛驕切|轎:小車|嬌:廣雅云禹妃之名又音驕|蕎:蕎麥又音驕|蟜:蠪蟜螘也蠪音龍|蹻:驕也慢也又巨虐切|䎗:飛皃|䀉:盂也
OiQ七遙;鍫:臿也亦作𣂁七遙切十|鐰:+上同|篍:吹竹筩又音秋|幧:斂髮謂之幧頭亦作幓|㡑:+上同|𣟼:生麻|𣖄:抄飯匙也
hiY於喬;妖:妖豔也說文作𡝩巧也今從夭餘同於喬切五|祅:祅災|枖:說文云木盛皃詩云桃之枖枖本亦作夭|訞:巧言皃|夭:和舒之皃又乙矯切
eiU去遙;蹻:舉足高去遙切又其略切六|繑:說文云絝紐也|趬:行輕皃|蹺:揭足|䫞:額大皃又火幺切|㚠:長大皃又火條切
YiQ尺招;怊:奢也尺招切又敕朝切二|弨:弓弛皃詩云彤弓弨兮
BiE撫招;𤐫:說文曰火飛也周禮注云輕𤐫土地之輕脃也今作票同撫招切二十一|漂:浮也亦作𣿖|杓:北斗柄星|𩙒:𩙒𩙂風吹皃|嫖:身輕便皃|旚:旌旗動皃|犥:牛黃白色也又敷沼切|鏢:刀劒鞘下飾也|僄:輕也又匹妙切|𪅃:鳥飛|飄:飄颻|慓:急也|彯:彯彯長組之皃|摽:字統云擊也|𧽤:說文曰輕行也|𨄏:+上同|翲:高飛|瞟:瞟睽明視|螵:螵蛸|嘌:疾吹之皃|𦠎:𦠎𦞵腫欲潰也
fiU渠遙;翹:舉也懸也危也又鳥尾也渠遙切六|荍:草名今荊葵也|𧄍:蓮𧄍草也|嘺:不知|䎗:側飛|𤖻:几也
IiQ力昭;燎:庭火也力昭切又力照切二|髎:髖骨也又音聊
eiY起囂;趫:善走又緣木也起囂切又巨憍切四|憍〈𢄹〉:絝也|橇:蹋樀行又禹所乘也|鞽:+上同
#肴
jjQ胡茅;肴:骨體也又葅也凡非穀而食曰肴亦啖也胡茅切十九|餚:+上同|崤:崤函山名在弘農|𦺔:茅根|殽:溷殽雜也和也亂也|洨:水名出常山又縣名在沛郡|筊:竹索|姣:姣婬|猇:虎聲又縣名在濟南又直支切|㮁:㮁桃梔子|爻:易卦六爻|淆:混淆濁水|笅:小簫一十六管|㬵:字書云胶聲也|𨠦:沽也|䋂:黃色|倄:痛聲|㤊:快也|䂚:石名
djQ古肴;交:戾也共也合也領也古肴切二十二|蛟:龍屬漢書曰武帝元封五年自於尋陽浮江親射蛟江中獲之|茭:說文曰乾芻也又爾雅曰茭牛蘄郭璞云今馬蘄葉細銳似芹亦可食|鵁:鵁鶄鳥|膠:膠漆亦太學也又姓史記紂臣膠鬲|鮫:魚名皮有文可飾刀|咬:鳥聲|郊:邑外曰郊|䍊:樂器以土爲之雙相黏爲䍊也|轇:轇轕戟形|㶀:㶀㵧水皃|䢒:說文會也|教:效也又古孝切|䉰:竹圍索名|𥹜:𥹜𥺝米餅|摎:束也撓也又音留|鉸:鉸刀又古卯切|佼:交也又古卯切|芁〈𦫶〉:秦𦫶藥名|詨:誇語也又音哮|嘐:詩云雞鳴嘐嘐|𩎔:囊也
UjQ鉏交;巢:說文曰鳥在木上曰巢在穴曰窠爾雅曰大笙謂之巢又縣名在廬江亦姓有巢氏之後左傳楚有巢牛臣鉏交切八|轈:兵車高若巢以望敵也|勦:輕捷也又子小切|𡻝:山高皃|𣝞:蒜束|樔:說文曰澤中守艸樓|𡏮:地名在聊城|鄛:鄉名在南陽
MjQ女交;鐃:鐃似鈴無舌女交切九|呶:喧呶|譊:爭也又恚呼也|怓:心亂|䴃:鳭䴃鳥名也鳭音嘲|𣲿:𣲿沙藥名|䃩:+上同|𡽧:𡽧崒也|㺜:犬多毛又奴刀切
VjQ所交;梢:船舵尾也又枝梢也所交切十七|捎:蒲捎良馬名也亦芟也又音宵|髾:髮尾|輎:兵車|旓:旌旗旒也|弰:弓弰|䈰:飯帚|筲:斗筲竹器|鞘:鞭鞘|蛸:蠨蛸喜子|鮹:海魚形如鞕鞘|䘯:衣袵|綃:帆維又音宵|颵:風聲|莦:說文惡草皃又音消|娋:小娋偷也|𡡏:齊人呼姊
DjA莫交;茅:草名左氏傳曰前茅慮無明又姓史記秦有茅焦莫交切八|蝥:螌蝥蟲名|貓:又武瀌切|犛:牛名又力之切|罞:麋罟也|鶜:鶜鴟鳥也|描:打也出玉篇|媌:美好皃
ijQ許交;虓:虎聲許交切十六|猇:+上同|髇:髇箭|藃:禾傷肥又音嚻|穘:+上同|窙:高氣|嗃:嗃謈恚也|䬘:風䬘䬘也|哮:哮闞|庨:庨豁宮殿形狀|灱:乾也又熱也|涍:水名在河南郡|嘐:誇語也|顤:䫜顤胡人面也|𩾾:鴟𩾾似鳧腳近後不能行|㹲:豕驚
AjA布交;包:包裹亦姓楚大夫申包胥之後後漢有大鴻臚包咸布交切五|胞:胞胎又匹交切|枹:爾雅注曰樹木叢生枝節盤結詩云枹有三枿又楊枹菜|苞:叢生也豐也茂也又苞筍又姓|勹:包也象曲身皃
BjA匹交;胞:胞胎匹交切九|𨚔:邑名說文布交切地名|䍖:覆車網也又縛謀切|脬:腹中水府|拋:拋擲|泡:水上浮漚說文曰水出山陽平樂東北入泗又音庖|𠐋:盛也|𢿏:擊也|𦫶:藥名
ejQ口交;敲:擊頭也口交切十一|跤:脛骨近足細處|骹:+上同|膠〈𥉾〉:面不平也|㤍:㤍㤉伏態皃|磽:石地|䂭:䂭磝城戍名今濟州是也出音譜|礉:+上同|鄗:邑名又杜預云山名在滎陽縣西北又音郝|墝:墝埆瘠土|頝:頝䫜頭不媚也
gjQ五交;聱:不聽也五交切又五勞語彪二切四|謷:不肖也又五勞切|磝:䂭磝|𢿣:蒼頡篇云擊也
SjQ側交;𦗔:耳中聲側交切五|罺:抄網|抓:抓掐|𠿈:小兒聲|摷:擊也
JjQ陟交;嘲:言相調也陟交切五|䞴:䞴趟跳躍趟竹窅切|啁:說文曰啁嘐也|鳭:鳭䴃黃鳥|鵃:鶻鵃似山鵲而小短尾至春多聲
TjQ楚交;䜈:代人說也楚交切六|抄:略也又初教切|鈔:+上同|𦾱:𦾱取|訬:健也|䰫:疾皃
CjA薄交;庖:食廚也薄交切十七|咆:咆虓熊虎聲|匏:瓠也可爲笙竽|炮:合毛炙肉也一曰裹物燒|炰:+上同|鉋:鉋刷|瓟:似瓠可爲飲器|麃:獸名似鹿|掊:手掊|颮:風聲|鞄:鞄皮說文云柔革工也|狍:獸名羊身人面目在腋下|跑:足跑地也|捊:引取亦作抱|尥:牛脛相交也又力釣切|泡:水名又匹交切|㯡:赤黑之漆
hjQ於交;䫜:頭凹也於交切九|㕭:㕭咋多聲|坳:地不平也|窅:深目皃又烏了切|軪:軪軋奇皃又車聲也|眑:面目不平又於糾切|咬:淫聲|梎:梎柌鐮柄|𠣑:目深
KjQ敕交;䫸:熱風敕交切二|嘮:嘮呶讙也
IjQ力嘲;顟:顤顟胡人面狀力嘲切四|𠐋:盛也|窌:深空之皃|賿:謎語云錢又力絞切
LjQ直交;䄻:禾穭生直交切穭音呂一
#豪
jkQ胡刀;豪:豪俠說文曰豕鬣如筆管者亦州名屬九江郡古鍾離國與吳爭桑而滅隋改爲州山海經云渠猪之山多豪魚赤尾赤喙有羽胡刀切十三|號:大呼也又哭也詩云或號或呼易云先號咷而後笑又乎到切|毫:長毛|嗥:熊虎聲|獆:+上同|濠:城濠又水名|壕:+上同|䫧:𩕯䫧大面皃𩕯音刀|𣘫:木名|崤:山名在弘農又胡交切|𨚙:鄉名在南陽|𠢕:俊健|𨼍:𨼍壑
dkQ古勞;高:上也崇也遠也敬也又姓齊太公之後食采於高因氏焉出渤海漁陽遼東廣陵河南五望又漢複姓高堂氏出泰山古勞切二十一|膏:脂也元命包曰膏者神之液也又澤也肥也|皐:高也局也澤也詩云鶴鳴九皋言九折澤也又姓皋陶之後左傳有越大夫皋如|皋:+上同|羔:羊子|餻:餻糜|㟸:㟸㟉古亭|櫜:韜也一曰車上囊|咎:皋陶舜臣古作咎繇|鼛:役事車鼓長丈二尺詩曰鼓鐘伐鼛傳云鼛大鼓也|鷎:𪁜鷎鳥名|篙:進船竿|槔:桔槔|䚌:見也|䔌:葛之白花|㤒:局知也|䆁:今之餹䬾曰𥡅|𣓌:木名|倃:毀也|䓘:白䓘草食之不飢|䣗:鄉名在范陽
IkQ魯刀;勞:倦也勤也病也又姓後漢有琅邪勞丙魯刀切二十二|澇:水名在京兆又郎到切|牢:養牛馬圈亦堅也固也又蒲牢獸名又姓孔子弟子琴牢之後漢石顯之黨有牢梁|窂:+上同|簩:竹名一枝百葉有毒|䝁:野豆|𧰉:+上同|蟧:小蟬一曰虭蟧蟪蛄也|醪:濁酒|撈:取也|㟉:㟸㟉|㗦:㗦嘈聲也|髝:髝髞高皃|憥:苦心皃|𦗖:耳鳴又力彫切|䜮:䜰䜮深谷皃|𨦭:𨦭鑪錍也|𤩂:玉名|嫪:妬也又力報切|哰:囒哰撦挐|𣘪:木名|簝:宗廟盛𠟼竹器又音寮
ikQ呼毛;蒿:蓬蒿又姓出姓苑呼毛切七|䜰:䜰䜮深谷皃|撓:攪也又奴巧切|薧:死人里又音考|薅:除田草也|茠:-|𣐾:+並上同
DkA莫袍;毛:說文曰眉髮之屬及獸毛也亦姓本自周武王母弟毛公後以爲氏本居鉅鹿避讎滎陽也莫袍切一十|髦:髦鬣也髦俊也|芼:菜也又音耄|𣹪:水名出諸與山|旄:旄鉞書曰武王右秉白旄史記曰昴星曰旄頭星徐爰釋疑曰乘輿黃麾內羽仗班弓箭左罼右䍐執罼者冠熊皮冠謂之髦頭也|氂:犛牛尾也犛音猫|㮘:冬桃|枆:+上同|酕:酕醄醉也|堥:前高後下丘名
FkQ土刀;饕:貪財曰饕土刀切二十八|洮:水名出西羌又清汰也|韜:藏也寬也說文曰劒衣也|縚:+上同|謟:疑也|滔:漫也又水流皃|叨:叨濫|弢:弓衣|𩥓:馬行皃|㹗:牛羊無子又昌來切|𤘸:牛行遟皃|慆:悅樂|絛:編絲繩也|幍:+上同|𠌪:目通白也|槄:木名爾雅云槄山榎今山楸也|蜪:爾雅曰蝝蝮蜪郭璞曰蝗子未有翅者又音陶|夲:說文曰進趣也从大十大十者猶兼十人也|𠦂:+上同|綢:爾雅曰素錦綢杠郭璞曰以白地錦韜旗之竿又音紬|搯:搯捾周書云師乃搯捾捾烏活切|翢:羽葆幢又徒刀切|瑫:玉名|𠬢:𠬢滑也又𦝫鼓大頭名|䈱:牛𥴧|𠚡:古器|詜:詜䛬言不節|挑:挑達往來相見皃詩曰挑兮達兮又條了切
EkQ都牢;刀:釋名曰刀到也以斬伐到其所也說文云兵也都牢切七|魛:魚名|忉:憂心皃|裯:說文曰祗裯短衣又直流切襌被也|舠:小船|𩕯:𩕯䫧大面皃|朷:木心
QkQ蘇遭;騷:愁也蘇遭切十三|搔:瓟刮|繅:繹繭爲絲|繰:+上同俗又作縿縿本音衫|臊:腥臊|鰠:魚名|溞:淅米|颾:風聲|鱢:鯹臭|㮴:說文曰船總名也亦作𣔱|艘:+上同亦作䑹|𠋺:驕也|慅:恐懼
CkA薄襃;袍:長襦也薄襃切三|袌:+上同|軳:戾也又車軫也
AkA博毛;襃:進揚美也說文作𧛙衣博裾也又姓禹後因國爲氏博毛切四|褒:+俗|𠅬:吳主四子字名盟也|𨚔:地名
GkQ徒刀;陶:陶甄尸子曰夏桀臣昆吾作陶周書神農作瓦器又陶正官名齊職儀曰左右甄官署掌塼瓦之作也又喜也正也化也亦姓陶唐之後今出丹陽徒刀切二十五|䛬:詜䛬言不節說文曰往來言也一曰小兒未能正言也一曰祝也|䛌:+上同|咷:號咷|桃:果木名鄴中記石虎苑中有句鼻桃重二斤又姓何氏姓苑云今西陽人後趙石勒將有桃豹|綯:爾雅曰綯絞也謂糾絞繩索也|燾:覆燾也又徒到切|逃:去也避也亡也|鼗:大者謂之麻小者謂之料又小鼓著柄者|鞀:-|鞉:+並上同|濤:波濤|掏:掏擇|檮:春秋傳云檮杌杜預曰凶頑無儔匹之皃|騊:說文曰騊駼北野之良馬又山海經曰北海有獸狀如馬名騊駼|萄:蒲萄|翿:纛也亦作翢舞者所執也又音導|䬞:大風|匋:養也|啕:多言|翢:羽葆幢六音𠬢|錭:錭鈍也|駣:馬四歲也|蜪:蝗子|裪:𧝃裪衣袖
NkQ作曹;糟:粕也作曹切九|𦵩:+上同|醩:+俗|遭:遭逢|㷮:火餘木也|槽:果華實相半也又才刀切|傮:終也|𣩒:+上同|㡟:藉也
gkQ五勞;敖:游也說文作𢾕亦姓顓頊大敖之後或作遨五勞切二十五|遨:+上同|翱:翱翔|聱:不聽又五交切|驁:駿馬|熬:煎也|嶅:山多小石|獒:犬高四尺|滶:水名出南陽魯陽縣|蔜:繁縷蔓生或曰雞腸草也|鷔:不祥鳥白身赤口也|鼇:海中大鼈|螯:蟹屬|謷:不肖語也又哭不止悲|嗸:眾口愁也|嗷:+上同|䫨:高頭也|𢧴:戟鋒|摮:擊皃|嫯:慢也|䦋:長大皃|𣘢:船接頭木|𦪈:+上同|𩪋:蟹大腳也|鰲:魚名
PkQ昨勞;曹:曹局也又輩也眾也群也亦州名蓋取古國以名之又姓本自顓頊玄孫陸終之子六安是爲曹姓周武王封曹挾於邾故邾曹姓也魏武作家傳自云曹叔振鐸之後周武王封母弟振鐸於曹後以國爲氏出譙國彭城高平鉅鹿四望昨勞切十四|𣍘:+古文|槽:馬槽|螬:蠐螬蟲|嘈:喧嘈|鐰:鐵剛折也|䄚:祭豕先也|艚:船艚|䏆:耳鳴|𩫥:高也|䐬:䐬脃|蓸:草名|漕:衛邑名又水運曰漕又昨到切|褿:帬也
hkQ於刀;𤏶:埋物灰中令熟於刀切三|䥝:銅瓫說文云溫器也|鏖:+上同
HkQ奴刀;猱:猴也奴刀切八|㺜:長毛犬又音鐃|𤣜:+上同|巎:山名|嶩:平嶩山名在齊出地理志|峱:+上同|𤫕:玉名|獿:獸名
ekQ苦刀;尻:說文𦞠也苦刀切二|訄:戲言
OkQ七刀;操:操持七刀切又七到切四|幧:所以裹髻又七搖切|𢻥〈𢿾〉:平持|㡟:藉也
BkA普袍;㯱:囊張大皃普袍切四|藨:醋莓可食|䫽:輕皃|㲏:毛起皃出聲譜
#歌
dlQ古俄;歌:禮記曰舜作五弦之琴以歌南風釋名曰人聲曰歌歌者柯也以聲吟詠上有下如草木之有柯葉兗冀言歌聲如柯古俄切十一|謌:+上同|柯:枝柯又斧柯又姓吳公子柯盧之後何氏姓苑云吳人也又虜姓後魏書柯拔氏後改爲柯氏望在河南|妿:女師以教女子|㤎:法也楷也|菏〈渮〉:澤水在山陽湖陵縣|牁:所以繫舟又牂牁郡名|戕:+陸云上同|滒:多汁|哥:古作歌字今呼爲兄也|鴚:鴚鵝
OlQ七何;蹉:蹉跌也七何切七|瑳:玉色鮮白也又七可切|搓:手搓碎也|磋:治象牙曰磋|溠:水名在義陽|傞:舞不止皃又素何切|𪘓:齒𪘓跌出字統
ElQ得何;多:眾也重也又貝多樹名葉如枇杷葉得何切三|𦰿:姓也漢有𦰿宗|𦷛:+上同
QlQ素何;娑:婆娑舞者之容素何切十一|挱:摩挱|挲:+上同|傞:舞不止皃又千何切|𩊮:𩊮鞄樂器亦謂馬尾|獻:獻罇見禮記亦作犧|䓾:䓾蔢草木盛皃|𠈱:行也又舞不止|桫:桫欏木名出崐崘山|䤬:䤬鑼銅器|𥆝:偷視也
GlQ徒河;駝:駱駝外國圖云大秦國人長一丈五尺好騎駱駝俗從也餘同徒河切二十三|駞:+俗|鼉:說文曰水蟲也似蜥蜴而長大|𡩆:𡩆負|紽:絲數詩云素絲五紽|鮀:魚名|陀:陂陀不平之皃陂普河切|驒:連錢驄說文曰驒騱野馬也又丁年切|䍫:似羊四耳九尾|沱:滂沱大雨也詩云月離于畢俾滂沱矣又爾雅云江爲沱謂江水出別爲沱也|跎:蹉跎|詑:欺也|池:虖池水名在并州界出周禮又音馳|酡:飲酒朱顏皃|㼠:瓦盌|䭾〈馱〉:馱騎也|迱:逶迱行皃|鼧:鼠名又託何切|袉:裾也又達可切|𩉺:𩉺緧|䡐:疾馳|𧕛:如人羊角虎爪|佗:委委佗佗美也又託何切
PlQ昨何;醝:白酒也昨何切十九|㽨:殘薉田也|瘥:病也又初介切|䣜:䣜縣名在譙郡或作酇酇本音贊|𣩈:小疫病也|鹺:禮云鹽曰鹹鹺|嵯:嵯峨|蒫:薺實又子邪切|𥰭:籠屬|艖:小舸|蔖:爾雅曰蓾蔖郭璞曰作履苴草又采古切蓾音魯|䴾:穀麥淨也|䑘:擣也|䠡:蹋也|躦:+上同|虘:虎不柔也又才都切|𪘓:齒跌|齹:齒本|䰈:髮多皃
glQ五何;莪:草名似䔑蒿詩云蓼蓼者莪五何切十三|哦:吟哦|娥:美好也又姓後魏將軍娥清|䄉:+上同|峨:嵯峨|鵝:說文曰鴚鵝也|俄:俄頃速也|𩒰:齊也|蛾:蠶蛾又姓左傳晉大夫蛾析禮記又音蟻|睋:視也|涐:水名在出汶江|誐:嘉善也詩云誐以謐我|硪:說文曰石巖也
FlQ託何;佗:非我也亦虜三字姓後魏書佗駱拔氏後改爲駱氏託何切七|他:+俗今通用|拕:曳也俗作拖|它:說文曰虫也从虫而長象冤曲垂尾形上古艸居患它故相問無它乎|蛇:+說文同上今市遮切|痑:馬病又力極也又叨丹切|鼧:鼠名
IlQ魯何;羅:羅綺也古者芒氏初作羅爾雅鳥罟謂之羅又姓出長沙本自顓頊末胤受封於羅國今房州也爲楚所滅子孫以爲氏魯何切十|蘿:女蘿|籮:篩籮|儸:儸出玉篇|饠:饆饠|𤄷:汨𤄷水名屈原沈處|欏:桫欏木名出崐崘山|囉:囉歌詞又嘍囉也亦小兒語也|鑼:䤬鑼器也|剆:擊也
HlQ諾何;那:何也都也於也盡也詩云受福不那那多也亦朝那縣名在安定又姓西魏揚州刺史那椿諾何切九|㔮:獸名似鼠班頭食之明目|𤘟:似牛白尾|挪:搓挪|儺:驅疫|𠹈:+上同|𡖔:多也|𩴓:纂文云人值鬼驚聲|臡:麋鹿骨醬
jlQ胡歌;何:辝也說文儋也又姓出自周成王母弟唐叔虞後封於韓韓滅子孫分散江淮閒音以韓爲何字隨音變遂爲何氏出廬江東海陳郡三望胡歌切七|河:水名出積石山海經云河出崐崘西北隅發源注海亦州取水以名之爾雅有九河徒駭太史馬頰覆釜胡蘇簡絜鉤盤鬲津|荷:爾雅曰荷芙蕖又胡哿切|菏:菏菔草也|苛:政煩也怒也說文曰小艸也|蚵:蜉蠪|魺:魚名
ilQ虎何;訶:責也怒也虎何切五|呵:+上同|𩑸:傾頭|㱒:止也|抲:擔抲俗
elQ苦何;珂:馬腦苦何切四|𠳌:開口聲|䯊:膝骨|軻:又苦賀切
hlQ烏何;阿:曲也近也倚也爾雅云大陵曰阿亦姓風俗通云阿衡伊尹号其後氏焉又虜三字姓四氏後魏書云阿伏于氏後改爲阿氏阿鹿桓氏後改爲鹿氏又有阿史那氏阿史德氏烏何切七|娿:媕娿不決媕音庵|痾:亦作疴病也|妸:女字|妿:女師又音哥|䋪:繒之細者|鈳:鈳䥈小釜
#戈
dlg古禾;戈:干戈說文云平頭戟也天授年置司戈八品武職古禾切十五|過:經也又過所也釋名曰過所至關津以示之也或曰傳過也移所在識以爲信也亦姓風俗通云過國夏諸侯後因爲氏漢有兗州刺史過栩|渦:亦作濄水名出淮陽扶溝浪蕩渠又姓三輔決錄有扶風太守渦尚|鍋:溫器|𨍋:車盛膏器|楇:+上同一曰紡車收絲具|瘑:瘡也|㽿:+上同|𩰫:說文曰秦名土釜曰𩰫|𩰬:+上同|㗻:小兒相應也又音禾|緺:綬名|堝:甘堝|𩾷:鳥名|𧒖:螗蜋別名
Olg七戈;遳:脃也七戈切一
Elg丁戈;𨹄:𨹄堆丁戈切二|𣑫:木𣑫也
Qlg蘇禾;莎:草名亦樹似桄榔其樹出麪蘇禾切十二|魦:魚名|莏:手挼莏也|𢘿:𢘿題縣名在涿郡|趖:趖疾|蓑:草名可爲雨衣|唆:㗻唆小兒相應|𧨀:佞也|髿:鬖髿髮皃|梭:織具晉書陶侃少時漁於雷澤嘗網得一梭以挂於壁上須臾雷雨暴至乃化爲龍而去|𣜤:+上同|㛗:女字穆天子傳云盛姫喪天子三女叔㛗爲主也
ClA薄波;婆:老母稱也薄波切九|媻:說文曰奢也|鄱:鄱陽縣名在饒州|皤:老人白也|𩕏:+𩕏𩕏勇舞皃說文同上|繁:姓也左傳殷人七族有繁氏漢有御史大夫繁延壽又音煩|搫:除也潘岳射雉賦云搫場拄翳又披散也亦音盤|蔢:蔢䓾草木盛皃|碆:纜繳石又音盤
Glg徒和;㸰:牛無角也徒和切三|碢:碾碢|堶:飛塼戲也
DlA莫婆;摩:研摩又滅也隱也迫也莫婆切十一|𩞁:𩞁食也出異字苑|𥂓:杯也又莫加切|𡡉:𡡉尼|魔:鬼魔|䯢:偏病|磨:磨礪爾雅曰石謂之磨|劘:削也|𦟟:漏病|𦣆:+上同|䭩:哺皃
Plg昨禾;矬:短也昨禾切五|痤:癤也|銼:銼𨰠小釜|㭫:爾雅云座椄慮李今麥李也或從木|睉:小目
glg五禾;訛:謬也化也動也五禾切七|譌:-|吪:+並上同|鈋:刓也去角也|囮:網鳥者媒|魤:魚名|𠂬:木節
Flg土禾;詑:欺也說文曰兗州謂欺曰詑土禾切五|𧦭:+俗|涶:水在西河|䛢:䛢詆|䜏:退言
Ilg落戈;𩼊:獸名魚身鳥翼落戈切十六|摞:理也|騾:騾馬也蜀志云後主乘騾車降鄧艾也|驘:+上同|𦿌:盛土草器|鸁:桑飛鳥也|𣜄:木名可爲箭笴|螺:蜯屬|蠃:+上同|𥢵:穀積也或作𥡜|𥡜:+上同|𧄿:草名生水中|𨰠:銼𨰠小釜也或作鏍|覼:覼縷委曲|腡:手指文也|蠡:瓠瓢也又禮鹿二音
Hlg奴禾;捼:捼莏說文曰摧也一曰兩手相切摩也俗作挼奴禾切二|䎠:丸熟
AlA博禾;波:波浪博禾切六|皤:老人白皃又音婆|紴:錦類又絛屬也|嶓:嶓冢山名|番:書曰番番良士爾雅曰番番矯矯勇也|碆:石可爲矢鏃也
BlA滂禾;頗:說文曰頭偏也滂禾切又匹我切四|坡:坡坂|𨸭:𨸭陀不平|玻:玻瓈玉西國寶
jlg戶戈;和:爾雅云笙之小者謂之和和順也諧也不堅不柔也亦州名在淮南漢九江都尉居之屬九江郡齊爲和州又姓出汝南河南二望本自羲和之後一云卞和之後晉有和嶠又虜複姓和稽氏後改爲緩氏戶戈切九|咊:+古文|𤖱:棺頭|禾:粟苗|龢:諧也合也或曰古和字|鉌:鉌鑾亦作和|䒩:草名|㗻:小兒相應|盉:調五味器
elg苦禾;科:程也條也本也品也科斷也苦禾切又苦臥切十四|窠:窠窟又巢|薖:草名又寬大皃|稞:青稞麥名|萪:萪藤生海邊葉肕可爲篾也|蝌:蝌蚪蟲名爾雅曰科斗活東蝦蟆子也字林從虫|㸰:牛無角也|犐:+上同|課:課差又苦臥切|簻:簻軸又陟爪切|䈖:竹名|㽿:禿瘡又古禾切|髁:膝骨說文口臥切髀骨也|𠏀:美也
hlg烏禾;倭:東海中國烏禾切七|濄:水回|渦:水坳|涹:濁也|𡑟:地𡑟窟也|踒:躅也|𥟿:燕人云多
ims許𦚢;鞾:鞾鞋釋名曰鞾本胡服趙武靈王所服許𦚢切四|靴:+上同|𢪎:撝也|㗾:道經疏云吐氣聲也
hms於靴;𦚢:𦚢𩨭手足曲病於靴切二|𠏃:𠏃𠋧癡皃出釋典
ems去靴;𩨷:手足疾皃去靴切二|𩨭:+上同
fmc求迦;伽:伽藍求迦切三|茄:茄子菜可食又音加|枷:刑具又音加
emc丘伽;佉:丘伽切四|呿:張口皃|㰦:欠去|𠋧:𠏃𠋧
dmc居伽;迦:釋迦出釋典居伽切又音加一
Olg醋伽;脞:脃也醋伽切二|㛗:訬疾
Nlg子𩨷;侳:安也子𩨷切二|𩛠:骨𩛠出異字苑
fms巨靴;瘸:腳手病巨靴切一
Img縷𩨷;𦣛:驢腸胃也縷𩨷切一
#麻
DnA莫霞;麻:麻紵亦姓風俗通云齊大夫麻嬰之後漢有麻達注論語莫霞切八|犘:犘牛重千斤出巴中|蟆:蝦蟆亦作蟇|𪓹:𪓬𪓹似𪓟鼊生海邊沙中肉甚美多膏|𩔶:𩔶䫗難語出陸善經字林|痲:痳風熱病|𥂓:杯也又莫何切|㦄:㦄愍
YoQ尺遮;車:古史考曰黃帝作車引重致遠少昊時加牛禹時奚仲加馬周公作指南車又姓出魯國南平淮南河南四望本自舜後陳敬仲奔齊爲田氏至漢丞相田千秋以年老得乘小車出入省中時人謂之車丞相子孫因以爲氏漢末避地於魯又複姓二氏世本有齊臨淄大夫車遽氏又有車成氏亦虜複姓魏獻帝命疎屬車焜氏後改爲車氏尺遮切又音居二|硨:硨磲
aoQ式車;奢:張也侈也勝也式車切三|賒:不交也|畬:燒榛種田又音余
loQ以遮;邪:琅邪郡名俗作耶瑘亦語助以遮切又似嗟切十三|耶:-|瑘:+並見上注|釾:鏌釾|鎁:+上同|椰:椰子木名出交州其葉背面相似|擨:擨歈舉手相弄|斜:斜谷在武功西南入谷百里而至說文抒也又似嗟切|䓉:草名|𦰳:木名皮可爲索|䔑:穗也|𦭿:枲屬|𥯘:竹名生臨海
XoQ正奢;遮:斷也正奢切四|𠌮:𠌮儸健而不德|㸙:吳人呼父|諸:姓也漢有洛陽令諸於何氏姓苑云吳人又職余切
NoQ子邪;嗟:咨也子邪切十二|𧨁:+上同|罝:兔罟也詩有兔罝篇|蒫:薺實又昨何切|謯:說文𧨹也|瘥:爾雅云病也又在何切|𨲠:長歎|袓:縣名似與切|㜘:憍也|怚:+上同|𣩈:小疫|䦈:䦈丘山在東海
boQ食遮;蛇:毒蟲又姓後秦錄姚萇后蛇氏也南安人食遮切又音它三|虵:+俗|荼:爾雅云蔈荂荼即芀也又音徒荂音吁
jng戶花;華:草盛也色也說文作䔢榮也崔豹古今注曰堯設誹謗木今之華表也西京記謂交午柱戶花切又呼瓜戶化二切十|驊:驊騮周穆王馬|鷨:鳥名似雉|𧑍:蟲名似蛇字林云𧑍大蛇也出魏興啖小蛇及蝮但張口小蛇自入也|鋘:鋘鍫|鏵:+上同|釫:+亦同上|樺:木名又戶化切|崋:西嶽名也又戶化切|划:太撥進船也
dng古華;瓜:說文蓏也廣雅云龍蹄虎掌羊骹兔頭桂髓蜜筩小青大班皆瓜名亦州名本古西戎地左傳范宣子數戎子駒支曰昔秦人迫逐乃祖吾離于瓜州又漢複姓王莽傳有盜賊臨淮瓜田儀古華切七|騧:黃馬黑喙|緺:青緺綬也|婐:女侍又於果切|蝸:蝸牛小螺|媧:古女后也|㧓:引也擊也
ing呼瓜;華:爾雅云華荂也呼瓜切四|花:+俗今通用|譁:諠譁|𧪮:+上同
eng苦瓜;誇:大言也苦瓜切八|䠸:䠸𨈚體柔也爾雅作夸毗|夸:奢也|姱:姱奢皃|跨:吳人云坐|胯:兩股閒也|𠇗:𠇗邪離絕之皃|䯞:額上骨也
MnQ女加;拏:牽也女加切九|詉:𧬅詉語皃𧬅張加切|挐:絲絮相牽又女書切|摣:取也|蒘:藸蒘草|𧘽:衣敝|𧦮:絲𧦮語不解也|𤓷:爬𤓷以收除也|笯:鳥籠又乃胡切
dnQ古牙;嘉:善也美也又姓左傳晉大夫嘉父古牙切二十六|家:居也爾雅云扆內謂之家又姓風俗通漢有家羨爲劇令|加:增也上也陵也|葭:葭蘆也說文曰葦之未秀者又音遐|笳:笳簫卷蘆葉吹之也|麚:牡鹿|䴥:+上同|豭:豕也子路佩豭說文曰牡豕也|猳:+俗|痂:瘡痂|鴐:鴐鵞鳥|枷:枷鎖又連枷打穀具|袈:袈裟|𣮫:𣮫㲚毛衣|跏:跏趺坐也|𨔣:不得進也|𤠙:𤠙玃|𧉪:米中黑蟲|茄:荷莖又漢複姓有茄羅氏|迦:漢複姓有迦葉氏又居伽切|珈:婦人首飾|瘕:病也|犌:牛絕有力|幏:說文曰南郡蠻夷賨布|貑:貑羆又貑貜也並見爾雅注|蟼:爾雅云蟼蟆蛙類也又音荊
jnQ胡加;遐:遠也胡加切十四|蝦:蝦蟆|鍜:錏鍜|霞:赤氣騰爲雲又漢複姓有霞露氏|瑕:玉病也過也又姓左傳周大夫瑕禽又漢複姓有瑕呂氏|騢:馬赤白雜色|鰕:大鯢|䠍:腳下|䫗:䫛䫗言語無度|碬:礪石也春秋傳曰鄭公孫碬字子石|䪗:履跟後帖|𩋥:+上同|赮:日朝赤色|蕸:荷葉
BnA普巴;葩:花也又草花白亦作皅普巴切七|鈀:方言云江東呼鎞箭|妑:字林云女字也|蚆:貝也爾雅曰蚆博而頯郭璞云頯者中央廣兩頭銳|吧:吧呀大口皃|舥:舥腳船也|𧣃:牛角闊也
hnQ於加;鴉:烏別名於加切八|鵶:+上同|錏:錏鍜|㝞:㝞𡨀作姿態皃𡨀音宅加切|椏:方言云江東言樹枝爲椏杈也|丫:象物開之形|䃁:碨䃁地形不平|𠜲:自刎
AnA伯加;巴:巴蜀又州取國以名焉三巴記云閬白水東南流曲折三迴如巴字亦蟲名又姓後漢有楊州刺史巴祗伯加切八|鈀:兵車又音葩|笆:有刺竹籬|豝:豕也|芭:芭蕉|㿬:㿬皻鼻病|蚆:又匹加切義見上文|吧:吧呀小兒忿爭
TnQ初牙;叉:交手初牙切九|杈:杈杷田器說文曰杈枝也|差:擇也又差舛也|靫:靫鞴弓箭室也|鎈:錢異名出字諟|䐤:腵䐤脯也|𠞊:㔆物|䑡:小船名|艖:+上同
VnQ所加;鯊:魚名今之吹沙小魚是也所加切十一|魦:+上同|沙:沙汰說文曰水散石也爾雅曰潁爲沙謂大水溢出別爲小水之名亦州取沙角山爲名即三秦記鳴沙山也又姓何氏姓苑云東莞人又漢複姓二氏左傳齊有夙沙衛神農時夙沙氏之後漢書功臣表有昭沙掉尾又百濟有沙吒氏|砂:+俗|裟:袈裟|㲚:𣮫㲚毛衣|桬:桬棠木名出崐崘山|紗:絹屬一曰紡纑也|髿:髮髿垂皃|𩊮:𩌍𩊮𩌈𩍜履也|硰:硰石地名見漢書
gnQ五加;牙:牙齒又牙旗吳志曰孫權因瑞作黃龍大牙常在軍中諸軍進退視其所向又姓風俗通云周大司徒君牙之後五加切七|衙:縣名在馮翊亦衙府又姓秦穆公子食采於衙因氏焉蜀志有晉督護衙傳又音語音魚|芽:萌芽|齖:䶥齖齒不平正|呀:吧呀|枒:杈枒|吾:漢書金城郡有允吾縣允音鉛
SnQ側加;樝:似梨而酸或作柤側加切十二|柤:+上同又煎藥滓|𦳏:芹楚葵生水中|㪥:以指按也|䶥:䶥齖|皻:皰鼻|抯:說文挹也|溠:水名出義陽又側稼切|渣:+上同|𤹡:瘡痂甲也|𥡧:赤𥡧稻名|浾:棠汁
LnQ宅加;𡨀:㝞𡨀宅加切十五|䠧:䠧跱行難皃|荼:苦菜又音徒|䣝:亭名在郃陽|𣘻:春藏草葉可以爲飲巴南人曰葭𣘻|茶:+俗|秅:說文曰秭也周禮云聘禮曰十斗曰斛十六斗曰籔十籔曰秉四秉曰筥十筥曰稯十稯曰秅|𡝐:美也|𤶠:瘢𤶠瘡痕|𦛝:含舌皃|𥥸:窊𥥸深皃|塗:塗飾又音徒|𨼑:丘名|梌:吳人云刺木曰梌也|䅊:開張屋也又縣名說文作㢉
RoQ似嗟;衺:不正也似嗟切四|斜:+上同|邪:鬼病亦不正也論語曰思無邪|䔑:䔑蒿
ZoQ視遮;闍:闉闍城上重門也視遮切又德胡切五|余:姓也見姓苑出南昌郡|鉈:短矛又音夷|鍦:-|𥍸:+並上同
hng烏瓜;窊:凹也說文曰汚衺下也烏瓜切六|洼:深也亦渥洼水名又於佳切|畖:畖留地名在絳州|蛙:蝦蟆屬也|窪:深也說文曰清水也一曰窊也又水名|哇:婬聲
Sng莊華;髽:婦人喪髻莊華切一
Jng陟瓜;檛:棰也左氏傳曰繞朝贈之以策杜預云馬檛也或作簻陟瓜切四|簻:+上同|𥬲:亦同|膼:膇也
CnA蒲巴;爬:搔也或作把又姓本杞東樓公之後避難改焉西魏襄州刺史把秀蒲巴切三|杷:枇杷木名說文曰收麥器也|琶:琵琶樂器
UnQ鉏加;楂:水中浮木又姓出何氏姓苑鉏加切六|查:-|槎:+二同|䶥:䶥齖又音樝|㢒:壞也淮南子云㢒屋之下不可坐也|苴:詩傳云水中浮草也
KnQ敕加;侘:侘傺失意敕加切傺丑例切四|哆:張口也|𤵾:𤵾癡皃也|㗬:緩口又厚脣也
JnQ陟加;奓:張也陟加切八|𧬅:𧬅詉語不正也|觰:角上廣也|䅊:開張屋也又縣名|𤶠:瘡痕|咤:達利咤出釋典本音去聲|𪗭:噍聲|䐒:不密又黏也
inQ許加;煆:火氣猛也許加切又呼嫁切六|呀:唅呀張口皃又呀呷也|谺:字統云谽谺谷中大空皃|疨:疨病|岈:㟏岈山深之狀|颬:吐氣又風皃
enQ苦加;䶗:大齧也苦加切三|㤉:㤍㤉伏態之皃㤍苦交切|𡤫:㝞𡤫女作姿態
PoQ才邪;㚗:大口皃才邪切一
coQ人賒;若:蜀地名出巴中記人賒切又惹弱二音二|婼:婼羌西域國名
QoQ寫邪;些:少也寫邪切一
EoQ陟邪;爹:羌人呼父也陟邪切一
gng五瓜;𣢉:歄𣢉猶歄姽也五瓜切二|𩨾:䯞𩨾髂骨
enQ乞加;𣘟:乞加切一
#陽
lpQ與章;陽:陰陽說文曰高明也爾雅云山東曰朝陽山西曰夕陽又姓出右北平本自周景王封少子於陽樊後裔避周之亂適燕家於無終因邑命氏秦置右北平子孫仍屬焉又漢複姓二十二氏歐陽氏越王句踐之後封于烏程歐陽亭後因爲氏望出長沙呂氏春秋有辯士高陽魋帝顓頊高陽氏之後漢有東海王中尉青陽精少昊青陽氏之後又有御史孫陽放秦穆公時孫陽伯樂之後魯之公族有名子陽者及衛公子趙陽之後並以名爲氏漢有周陽由淮南王舅周陽侯趙兼之後又駙馬都尉涇陽準秦涇陽君之後世本云偪陽妘姓國爲晉所滅子孫因氏焉左傳晉有梗陽巫皋衛有戲陽速漢有博士中山鮭陽鴻又有葉陽氏秦葉陽君之後列仙傳有沛國陵陽子明止陵陽山得仙其後因山爲氏漢有揚州刺史鮮陽戩後漢有櫟陽侯景丹曾孫汾避亂隴西因封爲氏又長沙太守濮陽逸陳留人也神仙傳有太陽子白日升天春秋釋例周有老陽子修黃老術漢有安陽護軍河東成陽恢何氏姓苑有朱陽氏索陽氏與章切三十二|暘:日出暘谷|楊:赤莖柳爾雅曰楊蒲柳又姓出弘農天水二望本自周宣王子尚父幽王邑諸楊号曰楊侯後并於晉因爲氏也|揚:舉也說也導也明也又州名禹貢曰淮海惟揚州李巡曰江南之氣躁勁厥性輕揚故曰揚州|颺:風所飛颺|昜:飛也又曲昜縣在交阯|羊:牛羊禮記凡祭羊曰柔毛崔豹古今注云羊一名髯須主簿又姓出泰山本自羊舌大夫之後戰國策有羊千者著書顯名又漢複姓二氏列士傳有羊角哀左傳晉大夫有羊舌職|样:廣雅云样槌也方言曰懸蠶柱齊謂之样|眻:美目又餘亮切|佯:詐也或作詳|詳:+上同本音祥|徉:忀徉徙倚|洋:水流皃又海名又音祥|烊:焇烊出陸善經字林|煬:釋金又音恙|鍚:兵名又馬額飾|𩋬:馬額上靻|輰:輰䡵車也|敭:明敭|瘍:瘍傷也說文云瘍頭瘡也周禮療瘍以五毒攻之|鴹:𪄲鴹一足鳥舞則天下雨出字統|鰑:赤鱺|鸉:白鷢|蛘:蟲名|禓:道上祭一曰道神又舒羊切|崵:說文曰崵山在遼西|諹:讙也又音恙|瑒:玉名|𥂸:杯也|𦭵:𦭵葲藥名|𦍹:多也
RpQ似羊;詳:審也論也諟也似羊切八|洋:水名出齊郡臨胊縣北亦州名本漢成固縣秦爲漢中郡魏置洋州|翔:翱翔|庠:說文曰禮官養老夏曰校商曰庠周曰序|祥:吉也善也|𨀘:趨行|𦍙:女鬼古作祥禫字|痒:病也
IpQ呂張;良:賢也善也首也長也又姓左傳鄭大夫良霄鄭穆公之子子良之後呂張切十八|梁:梁棟又州名書曰華陽黑水惟梁州晉太康記云梁者言西方金剛之氣強梁故因名之舜置也秦爲漢中郡後其地入蜀魏末克蜀分廣漢三巴涪陵以北七郡爲梁州梁大同年復移在南鄭亦姓出安定天水河南三望本自秦仲平王封其少子康於夏陽梁山是爲梁伯後爲秦并子孫奔晉以國爲氏又漢複姓十二氏左傳有梁其踁魯伯禽庶子梁其之後又魯有仲梁懷晉有梁餘子養梁由靡秦有強梁皋莊子有卜梁倚楚文王庶子有食邑諸梁者其後爲氏魯有穀梁赤治春秋史記有將梁氏漢光武時有侍御史梁垣烈新垣衍之後漢明帝時有梁成恢善歷數|粱:稻粱廣志曰遼東有赤粱魏武以爲粥也俗作梁|粮:粮食|糧:+上同|涼:薄也亦寒涼也又州名禹貢雍州之域古西戎地也六國時至秦屬戎狄月氏居焉秦置三十六郡西北唯有隴西北地二郡於漢屬涼州部至武帝改雍州爲涼州後獻帝分渭川河西四郡爲雍州建安十八年復改爲涼州又姓魏志有太子太傅山陽涼茂|凉:+俗|𩗬:北風也又力向切|量:量度又力向切|蜋:蜣蜋蟲一名蛣蜣又音郎|踉:跳踉也又音郎|椋:木名|䝶:賦也|綡:冠纚|𣄴:薄也又力尚切|㹁:牻牛駁色|䣼:漿水|輬:轀輬車名
ipc許良;香:說文作𪏰芳也漢書云尚書郎懷香握蘭許良切五|皀:稻香|薌:穀氣|鄉:鄉黨釋名曰萬二千五百家爲鄉鄉向也眾所向也又姓出姓苑|膷:牛羹
apQ式羊;商:金音度也張也降也常也亦州名即古商國後魏置洛州周爲商州取商於地爲名又姓家語有商瞿式羊切十八|𧶜:說文曰行賈也典籍通用商漢書曰通財鬻貨曰商白虎通云居賣曰賈通物曰商俗作𧷞|傷:傷損|𥏻:傷也又且羊切|殤:殤夭|慯:憂皃|觴:酒器俗作𨢩|湯:湯湯流皃本他郎切|蔏:蔏陸草也|𪄲:𪄲鶊又𪄲鴹也|螪:螪羊蟲|㲽:水名|䵮:說文云赤黑色又餘諒切|禓:道上祭也又以章切|饟:饋也又式尚切|䵼:煑也亦作𩰱|塲:耕塲|𤳈:+上同
CpM符方;房:房室亦州名即春秋時防渚也秦爲房陵郡唐武德爲房州又姓出清河濟南河南三望本自堯子丹朱舜封爲房邑侯子陵以父封爲氏陵四十八代孫雅王莽末爲清河太守始居清河雅十九代孫諶隨慕容德南遷因居濟南郡生四子豫坦邃熙号四龍今稱四祖房氏符方切七|防:防禦也隄防也|坊:+上同見禮又音方|魴:魚名|方:方與縣名又府良切|肪:脂肪又音方|鴋:澤鸆也又音方
XpQ諸良;章:篇章又章甫殷冠名禮記曰孔子長居宋冠章甫之冠又明也采也程也又姓秦將有章邯諸良切十五|漳:水名山海經曰漳水出荊山南注于沮水|樟:豫樟木名|慞:懼也|璋:半珪曰璋詩云乃生男子載弄之璋|彰:明也|墇:壅也又之尚切|障:隔也又丘山頂上平又音去聲|麞:鹿屬|獐:+上同|鄣:邑名在紀|蔁:蔁柳當陸別名|𪅂:吳人呼水雞爲𪅂渠|𩌬:𩌬泥鞍飾|暲:日明
YpQ尺良;昌:盛也說文曰美言也一曰日光也又姓後漢有東海相昌稀尺良切八|裮:衣披不帶|倡:樂也優也又音唱|猖:猖狂|閶:閶闔|琩:耳璫|鯧:鯧鯸魚名|菖:菖蒲藥也
epc去羊;羌:章也強也發語端也說文云西戎牧羊人字从人羊又姓晉有石冰將羌迪去羊切四|猐:+上同或從犬|𡸓:+古文|蜣:蜣蜋
dpc居良;薑:菜名說文云御濕之菜史記云千畦薑韭與千戶侯等居良切十五|𧅁:+上同|畺:說文界也|疆:+上同|壃:+俗|畕:說文曰比田也|㹔:牛長脊一曰白脊牛|繮:馬組|韁:+上同|殭:死不朽也|礓:礓石|橿:一名檍萬年木又云鋤橿鋤柄也|姜:姓也出天水齊姓本自炎帝居於姜水因爲氏漢初以豪族徙關中遂居天水也|䗵:蠶白死|僵:仆也
LpQ直良;長:久也遠也常也永也直良切又直向丁丈二切八|萇:萇楚蔓生如桃又姓左傳周有大夫萇弘|腸:腸胃釋名曰腸暢也通暢胃氣也|場:祭神道處又治穀地也|䠆:䠆跪方言曰東齊北燕之閒謂跪曰䠆|㙊:道也|䗅:蚰蜒別名|瓺:瓶也又除向切
JpQ陟良;張:張施也又姓出清河南陽吳郡安定燉煌武威范陽犍爲沛國梁國中山汲郡河內高平十四望本自軒轅第五子揮始造弦寔張網羅世掌其職後因氏焉風俗傳云張王李趙黃帝賜姓也陟良切四|餦:餦餭餳也|粻:食米|漲:水大皃又音帳
cpQ汝陽;穰:禾莖也又姓齊將穰苴之後何氏姓苑云今高乎人汝陽切十七|禳:除殃祭也|攘:以手禦又竊也除也逐也止也揎袂出臂曰攘又音讓|𣀮:盜也|鑲:鉤鑲兵器又息羊切|𨟚:縣名在南陽|躟:疾行|瀼:露濃皃|𩆶:+上同|獽:戎屬|儴:爾雅曰因也|蘘:蘘荷|䉴:䉴䉛𥂖米竹器|鬤:𩬹鬤亂毛|勷:劻勷迫皃|瓤:瓜實也又女良切|孃:亂也又女良切
ApM府良;方:四方也正也道也比也類也法術也亦官名續漢書曰尚方令掌上手工巧作御刀劒諸好器物也又姓史記周大夫方叔之後府良切十三|汸:併船也說文本作方或從水|坊:坊巷亦州名本上郡地周於今州界置馬坊武德初置坊州因馬坊爲名漢官宮有太子坊坊亦省名又音房|蚄:虸蚄蟲名|肪:脂肪|邡:什邡縣在漢州|鴋:鷝鴋鳥名人面鳥身|枋:木名可以作車又蜀以木偃魚爲枋|鈁:鑊屬|牥:牛名|趽:研也說文曰曲脛馬也|䄱:禾名|匚:受物之器又一斗曰匚也
QpQ息良;襄:除也上也駕也返也亦州名本楚之西津魏武置襄陽郡西魏改爲襄州因水立名又姓魯莊公子襄仲之後子孫以諡爲氏後漢有襄楷息良切十三|廂:廊也亦曰東西室|湘:水名在零陵|相:共供也瞻視也崔豹古今注云相風烏夏禹作亦相思木名又姓出姓苑又息亮切|緗:淺黃|纕:馬腹帶國語云懷挾纓纕|忀:忀徉|驤:馬騰躍又速也低昂也馳駕也|鑲:兵器又女羊切|瓖:馬帶飾東京賦曰鉤膺玉瓖|欀:欀木皮中有如白米屑擣之可爲麵|箱:箱籠|葙:青葙子也
NpQ即良;將:送也行也大也助也辝也又姓後趙錄有常山太守將容即良切又子諒切六|漿:漿水|鱂:鰪鱂魚名鰪烏盍切|蔣:菰蔣草又音獎|螿:寒螿蟬屬|𢪇:說文云扶也字林又作摪
TpQ初良;創:說文曰傷也禮曰頭有創則沐今作瘡初良切又初亮切三|瘡:+上同|𠛂:+俗
DpM武方;亡:無也滅也逃也說文正作亾武方切十一|芒:草端也|莣:爾雅曰莣杜榮郭璞云今莣草似茅可以爲繩索履屩|鋩:刃端|硭:硭硝|杗:屋梁又莫郎切|朚:惡也又莫郎切|邙:縣名在沛郡又洛北山名又音忙|𨛌:郡名也又鄉名|望:看望又音妄|朢:弦朢又音妄
MpQ女良;孃:母稱女良切四|娘:少女之号|瓤:瓜實也又音穰|鑲:兵器
UpQ士莊;牀:簀也易曰遜于牀下士莊切三|床:+俗|疒:病也又女戹切
SpQ側羊;莊:嚴也又莊田爾雅曰六達謂之莊亦姓莊周著書也側羊切五|㽵:+俗|妝:女字又飾也|裝:裝束又側亮切|䊋:粉飾也
ZpQ市羊;常:倍尋曰常又官名漢書曰奉常秦官掌宗廟禮儀景帝六年更名太常也釋名曰九旂之名日月爲常謂畫日月於其端天子所建言常明也亦姓出河內漢有常惠市羊切十|尚:尚書官名又時仗切|裳:上曰衣下曰裳|甞:試也曾也說文本作嘗口味之也又姓風俗通云齊孟甞君之後|嘗:+上同|鋿:車鋿輪鐵|𩼝:魚名|償:報也還也當也復也又音尚|𪄹:䳯𪄹鳥名|徜:徜徉猶徘徊也
VpQ色莊;霜:凝露也又姓色莊切七|鸘:鷫鸘|鷞:+上同|孀:寡婦|驦:驌驦良馬|騻:+上同|蠰:爾雅云齧桑蝎也又傷餉二音
PpQ在良;牆:垣牆爾雅云牆謂之墉說文曰牆垣蔽也在良切十|廧:+上同|墻:+俗|佯:弱也|嬙:嬪嬙婦人官名|檣:船檣|薔:薔薇又東薔子十月熟可食出河西子虛賦云東薔彫胡|蘠:+上同|戕:殺也又他國臣來殺君也|𤞛:妄強犬也又徂朗切
OpQ七羊;鏘:鏗鏘七羊切十二|瑲:玉聲|槍:矟也通俗文云剡葦傷盜謂之槍說文曰歫也|蹌:說文曰動也詩曰巧趨蹌兮|蹡:行皃|𨄚:+上同|斨:斧斨說文云方銎斧也|牄:說文云鳥獸來食聲|嶈:山高皃|𨶆:門聲和也|𥏻:傷也又式羊切|搶:拒也突也
eps去王;匡:輔助也正也又姓風俗通云匡魯邑也句須爲之宰其後氏焉漢有匡衡去王切十三|邼:邑名說文曰河東聞喜鄉也|筐:筐籠|䖱:海中大蝦|框:棺門|恇:怯也|劻:劻勷|𩬹:𩬹鬤|洭:水名出桂陽含洭縣|軭:車戾|眶:目眶|䒰:草名|𩢼:耳曲
kps雨方;王:大也君也字林云三者天地人一貫三爲王天下所法又姓出太原琅邪周靈王太子晉之後北海陳留齊王田和之後東海出自姫姓高平京兆魏信陵君之後天水東平新蔡新野山陽中山章武東萊河東者殷王子比千爲紂所害子孫以王者之後号曰王氏金城廣漢長沙堂邑河南共二十一望又漢複姓五氏左傳晉有樂王鮒小王桃甲賈執英賢傳云東莞有五王氏史記云出齊威王至建王五王之後風俗通云漢有中郎威王弼出自楚威王後漢有新豐令王史音雨方切又雨誑切四|蚟:虴孫蟲名又蜻蛚即今促織也|𩵭:𩵭鮹魚名|彺:急行
hpc於良;央:中央一曰久也於良切九|鴦:鴛鴦匹鳥又烏郎切|殃:禍也咎也罰也敗也|䄃:+上同|鉠:鈴聲又音英|秧:蒔秧又於丈切|霙:霙霙白雲皃又音英|胦:脖胦|泱:水流皃又烏朗切
fpc巨良;強:健也暴也說文曰蚚也又姓後漢有強華奉赤伏符巨良切四|彊:與強通用說文曰弓有力也|䲔:鯨魚別名又其京切|勥:迫也
KpQ褚羊;𦳝:草名褚羊切三|倀:失道皃又狂也|鼚:鼓聲
BpM敷方;芳:芬芳亦州地多芳草故以名之置在常芳縣又姓風俗通云漢幽州刺史芳乘敷方切三|妨:妨害|淓:水名
fps巨王;狂:病也韓子曰心不能審得失之地則謂之狂也巨王切五|軖:紡車也|軭:說文曰車戾也又去王切|鵟:鴟屬|㞷:草木妄生狂匡往皆從此
#唐
GqQ徒郎;唐:說文曰大言也又州春秋時楚地戰國時屬晉後入於韓秦屬南陽郡後魏爲淮州隋爲顯州貞觀改爲唐州因唐城山爲名即高鳳隱所亦姓唐堯之後子孫氏焉出晉昌北海魯國三望徒郎切四十|啺:-|𥏬:+並古文|煻:煻煨火|糖:飴也|糛:+上同|堂:堂除亦屋白虎通曰夭子之堂高九尺天子尊故極陽之數九尺也堂之爲言明也所以明禮義也禮記曰天子之堂九尺諸侯七尺大夫五尺士三尺又姓風俗通云堂楚邑大夫五尚爲之宰其後氏焉|坣:+古文|𪕹:䶈𪕹鼠一月三易腸|棠:棠棃又桬棠木生崐崘山黃色赤實味如李食之使人不溺亦姓左傳齊大夫棠無咎又漢複姓吳王闔閭弟夫溉奔楚爲棠谿氏|搪:搪揬|蓎:蓎蒙女蘿案爾雅作唐蒙不從艹|瑭:玉名|餹:餹䬾黍膏䬾杜兮切|篖:筕篖竹笪|螗:蜩螗|𤚫:𤚫牛|𤛋:+上同|螳:螳蜋禮記仲夏月螳蜋生|塘:陂塘|碭:芒碭山名又音宕|鶶:鶶鷵鳥名似烏蒼白色|𩹶:魚名|踼:碭跌頓伏皃又吐郎切|闛:說文曰闛闛盛皃又他郎切|赯:赯赤色|磄:磄厗石也|溏:池也|䣘:地名|傏:傏𠊲不遜|隚:殿基|䧜:隄䧜|𨶈:高門也|鎕:鎕銻火齊|䉎:罩也|𨍴:𨍴䡙軘軨|橖:車橖|榶:榶棣木名案爾雅曰唐棣栘不從木|㲥:㲥毦罽也|㼺:瓷器
IqQ魯當;郎:官名又魯邑又姓出中山魏郡二望魯當切三十|蓈:說文曰禾粟之穗生而不成者謂之蕫蓈|稂:+草名似莠說文同上|桹:桄桹木名|廊:廡也文穎曰廊殿下外屋也|榔:檳榔|鋃:鋃鐺鎖頭一曰鍾聲|硠:硠磕石聲|𪁜:𪁜鷎鳥名|浪:滄浪水名又盧宕切|䯖:䯑䯖股肉䯑苦光切|蜋:螳蜋|𩷕:魚脂|琅:琅玕玉名爾雅曰西北之美者有崐崘璆琳琅玕焉又琅邪郡名今沂州也又姓齊有大夫琅過|瑯:琅邪郡名俗作瑯瑘|㝗:㝩㝗宮室空皃|狼:犲狼說文曰犲似犬銳頭而白頰高前廣後帝王世紀曰有神牽白狼銜鉤入殷朝又姓左傳晉有大夫狼瞫|欴:欴㰠貪皃|𦵧:𦵧毒藥名|踉:踉䠙行皃|莨:草名|㟍:峻㟍山名冬日所入|䡙:𨍴䡙軘軨|艆:海中大船|駺:馬尾白|躴:躴躿身長皃|筤:車籃一名𥫵𥫵音替|𥍫:短矛|閬:高門又盧宕切|哴:哴吭吹皃
EqQ都郎;當:敵也直也主也值也亦州本羌地周置同昌郡隋改爲嘉城鎮貞觀中改爲當州蓋取燒當羌以名之又姓也都郎切十一|鐺:鋃鐺|簹:篔簹竹名|襠:兩襠衣|璫:耳珠|𨎴:車𨎴|檔:木名出文字音義|儅:止也又丁宕切|𦡁:耳𦡁耳下|㼕:㼕瓤瓜中|蟷:蟷蠰螗蜋別名亦作𧒾
OqQ七岡;倉:倉庾也亦官名齊職儀曰大倉令周司徒屬官有廩人倉人則其職也釋名曰倉藏也藏穀物也漢書曰耿壽昌奏設常平倉又姓黃帝史官倉頡之後七岡切七|蒼:蒼色也又姓漢江夏太守蒼英|鶬:鶬鶊鳥名|𩀞:+𩀞鴰說文同上|滄:滄浪亦州後魏所置蓋取滄海爲名|凔:寒皃|𠥐:古器也出說文
dqQ古郎;岡:爾雅曰山脊岡古郎切十六|崗:+又作堽並俗|剛:強也|㓻:+俗|掆:舉也|笐:說文曰竹列也又爾雅曰仲無笐竹類也|鋼:鋼鐵|綱:綱紀說文曰維紘繩也|亢:星名一曰亢父縣說文人頸也|犅:特牛|堈:甕也|𤭛:+上同|牨:水牛|苀:爾雅釋草曰苀東蠡又音杭|魧:魚名爾雅云大貝本杭沆二音|迒:獸跡又音杭
QqQ息郎;桑:木名史記曰齊魯千畝桑麻其人與千戶侯等又姓秦大夫子桑之後漢有御史大夫桑弘羊息郎切六|桒:+俗|𠸶:亡也死𠸶也又姓楚大夫𠸶左又息浪切|喪:+上同|𦅇:淺黃|𩦌:馬色
eqQ苦岡;康:和也樂也又姓衛康叔之後亦西胡姓苦岡切十四|穅:穀皮|糠:+俗|㱂:穀不升謂之㱂|㝩:㝩㝗|槺:槺梁虛梁也見文選長門賦|𨻷:爾雅云虛也本亦作漮|䗧:眏𧉅蜻蛉|𥉽:䀹𥉽目皃|邟:邟城在陽翟|漮:說文云水虛也|𤮊:瓦也|㼹:+上同|躿:躿躴身長
iqg呼光;荒:荒蕪又姓呼光切十四|𥡃:果蓏不熟又說文曰虛無食也|肓:心上鬲下|衁:血也|𩣐:馬奔|鄺:人姓何氏姓苑云今廬江人|𥿼:絲曼延也|㠵:幭也|𧧢:夢言|䀮:目不明又狼䀮南夷國名人能夜市金|𣆖:旱熱|㡆:蒙掩|巟:說文曰水廣也|𣺬:+上同
jqg胡光;黃:中央色也亦官名有乘黃令晉官主乘輿金根車也又州名古邾國地秦屬南郡漢西陵縣也隋爲黃州取古黃城爲名亦姓出江夏陸終之後受封於黃後爲楚所滅因以爲氏漢末有黃霸胡光切三十二|皇:君也美也天也說文作皇大也又姓左傳鄭大夫皇頡|璜:說文曰半璧也周禮以玄璜禮北方|惶:懼也恐也遽也|遑:急也|潢:說文云積水池也|堭:堂堭合殿|煌:火狀|餭:餦餭餳也|騜:馬黃白色|艎:艅艎吳王舟名|簧:笙簧|隍:城池也有水曰池無水曰隍|癀:病也|𨝴:古國名|湟:水名出金城|徨:彷徨|篁:竹名|鱑:魚名|蝗:蟲蝗爲災|凰:鳳凰本作皇詩傳云雄曰鳳雌曰皇|偟:偟暇|媓:女媓堯妻|獚:犬名|蟥:蛂蟥蛢甲蟲也|韹:韹樂鐘聲也又音橫|𨜔:古縣名|䍿:羽舞名|䅣:䅭䅣穄名|𤯷:榮也|葟:+上同|趪:趪趪武皃又張設皃
dqg古黃;光:明也亦州名漢西陽縣地屬江夏郡梁置光州因浮光山爲名又姓田光之後秦末子孫避地以光爲氏晉有樂安光逸古黃切十四|灮:+上同|洸:水名又烏光切|桄:桄桹木名|胱:膀胱水府|垙:垙陌|𨎩:車下橫木|輄:+上同|橫:長安門名又戶觥切|𩧉:決𩧉馬旋毛在脊也|恍:武也|茪:𦯊茪草名|僙:僙僙武皃|侊:盛皃
FqQ吐郎;湯:熱水又姓宋有沙門湯休有文集吐郎切十一|簜:水名在鄴今簜陰縣單作湯|鏜:以鐵貫物說文曰鼓鐘聲也|闛:盛皃又音唐|𧼮:𧼮走皃|踼:踼跌又杜郎切|盪:盪突又徒朗切|蝪:蛈蝪蟲名|鼞:鼓聲|薚:蓫薚馬尾|𦳝:+上同
BqA普郎;滂:滂沱普郎切七|鎊:鎊削|霶:霶霈大雨|雱:雨雪盛皃詩曰雨雪其雱|䨦:+上同|磅:石聲|𣂆:量溢也
hqg烏光;汪:水深廣又姓汪芒氏之胤姓苑云新安人也烏光切五|尢:曲脛俗作尢|尪:+尪弱說文同上|洸:水名又音光|𪁘:雉鳴
hqQ烏郎;鴦:鴛鴦匹鳥烏郎切又一良切七|佒:體不申也|咉:噟聲|𧲱:貉屬|㹧:+上同|眏:眏𥉽目皃|姎:女人自稱又烏朗切
iqQ呼郎;炕:煑胘呼郎切又苦朗切四|㰠:欴㰠|䐠:狼䐠南夷國名|忼:咉忼很戾
jqQ胡郎;航:船也胡郎切十八|筕:筕篖|桁:械也|行:伍也列也又戶庚戶浪戶孟三切|迒:獸迹又古郎切|𨁈:+上同|頏:頡頏詩傳云飛而上曰頡飛而下曰頏說文音剛與亢同|𦐄:飛高下也|魧:魚名又大貝|胻:脛也|邟:餘邟縣名在吳興又音伉|杭:州名古於潛餘邟皆別名今餘杭於潛縣並在杭州|沆:渡也又胡朗切|蚢:爾雅蚢蕭繭郭璞曰食蕭葉者皆蠶類|肮:肮犬大脈也|苀:東蠡草名|抗:舉也又苦浪切|吭:鳥喉又下浪切
DqA莫郎;茫:滄茫莫郎切十四|吂:不知也|䀮:目不明也|汒:谷名在京兆|恾:怖也|忙:+上同|朚:遽也|邙:北邙山名又武方切|芒:草端亦姓史記有魏相芒卯又音亡|𥐞:𥐞碭山名史記本只作芒|杗:大梁又武方切|蘉:勉也|𡩩:寐語|𨛌:鄉名在藍田
NqQ則郎;臧:善也厚也又姓出東莞本自魯孝公子臧僖伯之後則郎切六|匨:+古文|䍧〈牂〉:牝羊|戕:戕牁亦作牂|贓:納賄曰贓|样:槌也出廣雅
HqQ奴當;囊:袋也說文曰囊橐也又姓楚莊王子子囊之後以王父字爲氏奴當切二|蠰:蟷蠰即螗蜋也
CqA步光;傍:亦作旁側也說文曰近也又羌姓步光切十三|彷:彷徨|膀:膀胱|髈:+上同|䠙:踉䠙急行|趽:腳脛曲皃|房:阿房宮名|旁:爾雅曰上達謂之歧旁謂歧道旁出也說文曰溥也|篣:竹箕又薄庚切|𨜷:亭名在汝南|螃:螃蟹本只名蟹俗加螃字|䅭:䅭䅣穄名|騯:馬盛皃又甫盲簿庚二切
gqQ五剛;卬:高也我也又姓漢有御史大夫卬祗五剛切又魚兩切七|䭹:千里駒說文又五浪切䭹䭹馬怒皃|枊:繫馬柱也劉備縛督郵者又五浪切|昂:舉也|䒢:昌蒲別名又魚兩切|㭿:飛㭿斜桷|䩕:履頭
PqQ昨郎;藏:隱也匿也昨郎切又徂浪切一
eqg苦光;䯑:䯑䯖苦光切一
AqA博旁;幫:衣治鞋履出文字集略博旁切五|縍:+上同|㨍:捍也衛也|𨢐:加杯上酒|鞤:鞋革皮也
#庚
drQ古行;庚:更也償也爾雅云太歲在庚曰上章又姓唐有太常博士庚季良又漢複姓莊子有庚桑楚古行切十二|鶊:鶬鶊|更:代也償也改也又古孟切|䢚:兔徑|秔:秔稻|稉:+上同|粳:+俗|賡:續也經也償也|羹:羹𦞦爾雅曰肉謂之羹|𩱧:+古文|埂:秦人謂坑也|浭:水名出北平
erQ客庚;阬:爾雅曰虛也郭璞云阬壍也客庚切六|坑:+上同|硎:亦同|𥉸:𥉸𥌯視不分明|砊:砊硠石聲|劥:劥㔞有力
DrA武庚;盲:目無童子武庚切八|蝱:蟲也|鄳:縣名在江夏|𥋝:𥋝盯直視|莔:貝母草|𨞚:古縣名在義陽|䥰:䥰銷|𥭮:竹名
jrg戶盲;橫:縱橫也又姓風俗通云韓王子成號橫陽君其後爲氏戶盲切十六|黌:學也|蝗:蟲又音皇|鐄:大鐘|瑝:玉聲說文音皇|喤:泣聲|鍠:和也樂也又鐘聲說文音皇|䬝:䬝䫻暴風|㶇:方舟也一曰荊州人呼渡津舫爲㶇或作𦪗|䄓:䄘䄓祭名|𧝒:𧝒褡小被|𤮏:瓦也|𪏓:織也|𢘌:憕𢘌|韹:聲也|彋:弸彋帷帳起皃
ArA甫盲;閍:宮中門也一曰巷門甫盲切六|祊:廟門傍祭|𥛱:+上同|騯:騯騯馬行又音傍音彭|嗙:喝聲|㔙:大也
irg虎橫;諻:語聲虎橫切五|䎕:䎕然飛聲|謍:謍謍小聲|嚝:鼓鐘聲|喤:喤呷也又音橫
drg古橫;觵:兕角爲酒器受七升罰失禮者古橫切六|觥:+上同|侊:小皃春秋國語曰侊飯不及壼湌|𩃙:吳主孫休二子名|䍔:網滿|𣘯:+上同
CrA薄庚;彭:行也道也盛也說文曰鼓聲也又姓大彭之後左傳楚有令尹彭仲爽漢有大司空彭宣薄庚切十七|澎:地名又擊水勢又撫庚切|膨:膨脝脹皃|蟚:蟚螖似蟹而小|䰃:䰃鬤亂髮皃鬤乃庚切|棚:棧也閣也|榜:說文曰所以輔弓弩也又甫孟切|䄘:䄘䄓祭名|搒:笞打說文又北孟切掩也|蒡:菜一名隱荵似蘇可爲葅|篣:籠又音旁|𩡕:𩡕馞大香|騯:馬行盛皃|憉:憉惇自強|𣂆:量溢|輣:兵車又樓車也|𨍩:+上同
irQ許庚;脝:膨脝脹也許庚切三|悙:憉悙自強|亨:通也或作亯又匹庚許兩二切
KrQ丑庚;瞠:直視皃丑庚切五|橕:撥也又橕柱也|樘:+上同說文曰衺柱也|䟓:字書跉䟓行遟皃|竀:正視
TrQ楚庚;鎗:鼎類楚庚切四|鐺:俗本音當|槍:欃槍祅星|琤:玉聲
UrQ助庚;傖:楚人別種也助庚切五|䚘:角長皃|𩫿:𩫿鬡亂髮皃|鬇:+上同|崢:崢嶸山皃
hsY於驚;霙:雨雪雜也於驚切十|鉠:鈴聲|韺:五韺高陽氏樂亦作英|渶:水名出青丘山|鶧:繼鶧鳥名|英:華也榮而不實曰英也又英俊亦姓漢有英布|瑛:玉光|㿮:青皃|媖:女人美稱|楧:楧梅今之雀梅
BrA撫庚;磅:小石落聲撫庚切四|恲:滿也|亨:煑也俗作烹又許庚許兩二切|澎:澎滜水皃又音彭
CsI符兵;平:正也和也易也亦州名古山戎孤竹白狄肥子二國之地秦爲遼西郡隨爲北平郡武德初爲平州有盧龍塞又姓齊相晏平仲之後漢有丞相平當又漢複姓何氏姓苑云有平陵乎寧二氏符兵切八|評:評量亦評事大理寺官唐初置十二員又音病|苹:葭一曰蒲白又曰萍別名又云藾蕭也|枰:枰仲木名又博局也|泙:水名說文谷也|坪:地平|胓:牛羊脂也|蚲:蚌蚲
dsY舉卿;驚:懼也說文曰馬駭也舉卿切七|京:大也廣雅曰四起曰京風俗通曰京非人力所成天地性自然也京師義亦取此公羊曰京者大也師者眾也天子之居必以眾大之辝言之又姓風俗通云鄭武公子段封於京號京城大叔其後氏焉漢有京房|荊:荊楚亦木名可染又州名夏及周並爲州秦爲南郡即郢都之渚宮又姓燕刺客荊軻|麠:獸名一角似麃牛尾|麖:+上同|鶁:羌鶁鳥|蟼:蟼蛙
DsI武兵;明:光也昭也通也發也又姓出平原河南山公集有平原明普武兵切五|盟:盟約殺牲歃血也周禮有司盟|𥁰:+上同|䳟:鷦䳟似鳳南方神鳥|鳴:嘶鳴又姓出姓苑
LrQ直庚;棖:門兩旁木直庚切七|盯:𥋝盯視皃|澄:水清定又音懲|掁:掁觸|䟫〈𣥺〉:距也周禮曰唯角𣥺之|挰:舉也|憕:憕𢘌失志又音懲
JrQ竹盲;趟:䞴趟躍跳竹盲切䞴陟交切二|𩘽:䬝𩘽狂風
kso永兵;榮:榮華又姓漢有榮啓期永兵切六|禜:祭名又音詠|蠑:蠑螈蜥蝪別名|瑩:玉色詩云充耳秀瑩母烏定切|揘:拔也|嶸:崢嶸又戶萌切
AsI甫明;兵:戎也周禮有司兵掌五兵五盾世本曰蚩尤以金作兵器也甫明切一
iso許榮;兄:爾雅男子先生曰兄說文長也許榮切一
esY去京;卿:說文章也公卿春秋漢含孳曰三公象五岳九卿法河海三公法三台九卿法北斗釋名曰漢置十二卿正卿九太常光祿衛尉太僕廷尉鴻臚宗正司農少府又姓風俗通云趙相虞卿之後去京切一
VsQ所庚;生:生長也易曰天地之大德曰生又姓出姓苑所庚切十|笙:樂器也禮記女媧造笙簧釋名曰笙生也象物貫地而生也又簟也吳都賦曰桃笙象簟|牲:犧牲|猩:猩猩能言似猿聲如小兒也|狌:+上同|鉎:鐵鉎|甥:外甥又姓風俗通云晉大夫呂甥之後|䴤:獸名大如兔也|鼪:鼪鼬鼠也|珄:金色
fsY渠京;擎:舉也渠京切十一|勍:強|黥:黑刑在面|䵞:-|剠:+並上同|䲔:大魚雄曰䲔雌曰鯢|鯨:+上同|檠:所以正弓|樈:鑿柄|葝:山薤|䫆:頸也
gsY語京;迎:逢也語京切一
jrQ戶庚;行:行步也適也往也去也又姓周有大行人之官其後氏焉戶庚切又戶剛戶浪下孟三切十|衡:橫也平也又姓風俗通云阿衡伊尹之後又云公衡魯公子後乃氏焉|䯒:牛脊後骨|胻:牛勢胻也|洐:溝水也|筕:筕篖竹笪|珩:佩上玉|桁:屋桁|蘅:杜蘅香草大者曰杜若也爾雅注曰杜衡似葵而香字不從艹|𦣍:熟肉
MrQ乃庚;鬤:䰃鬤亂髮皃乃庚切六|㲰:犬多毛皃|𤕦:說文云亂也一曰窒𤕦|獰:惡也|𥣗:穀芒長也|𧂘:說文曰牂𧂘可以作縻綆
#耕
dtQ古莖;耕:犁也周書曰神農之時天雨粟神農耕田而種之古莖切一
etQ口莖;鏗:鏗鏘金石聲也口莖切十五|銵:+上同|䡰:車鞕又車堅牢|鳽:雝渠鳥名|誙:莊子曰誙誙如也|牼:牛膝骨又人名宋有司馬牼|𡷨:或作硎谷名在麗山昔秦密種瓜處|硻:說文云餘堅也|殸:敵也|㧶:琴聲|䡩:車聲|硜:硜硜小人皃|摼:撞也|㰢:㰠㰢|羥:羊名
DtA莫耕;甍:屋棟也莫耕切十一|𣞑:+上同|䉚:竹筒|萌:萌牙|氓:民也|甿:+上同|嫇:嫈嫇新婦皃|蕄:爾雅云存存蕄蕄在也又莫登切本亦作萌又作𢡗|𥋝:𥋝盯|𧂛:苕可爲帚|𥌯:𥉸𥌯視不分明
AtA布耕;浜:布耕切安船溝又布耿切二|捠〈㙃〉:冢口穴也
jtg戶萌;宏:大也戶萌切十六|紘:冠卷也又八紘|紭:網紭|閎:爾雅曰衖門謂之閎郭璞云閎衖頭門又曰所以止扉謂之閎郭璞云門辟旁長橛也又姓漢有閎孺|嶸:崢嶸山峻|嵤:+上同|𧮯:谷中響一曰谷名也|耾:耳語|翃:蟲飛|浤:浤浤汨汨水波之勢|竑:量度周禮考工曰故竑其輻|宖:屋響又烏宏切|鈜:金聲|吰:噌吰鐘音|𥐪:玉篇云石聲也|彋:弸彋開張也
jtQ戶耕;莖:草木榦也戶耕切三|䪫:樂名亦作莖|牼:牛膝下骨又苦耕切
JtQ中莖;朾:伐木聲也中莖切七|丁:+上同詩曰伐木丁丁|玎:玎玲玉聲又齊太公子伋諡玎公出說文也|𠑅:𠑅𠊰不仁也出聲譜|𧯫:𧯫設幕出字林|䟓:跉䟓腳細長也|䆸:䆸宏闊大皃
htQ烏莖;甖:瓦器烏莖切十三|罌:+上同|罃:說文曰備火長頸缾也|鶯:鳥羽文也|嚶:鳥聲|櫻:含桃|嫈:嫈嫇又於營切又乙諍切|鸚:鸚鵡能言之鳥|譻:譻𧭈小聲|鸎:黃鸎|褮:鬼衣|𠠜:芟除林木也出齊人要術|莖:爾雅釋草云姚莖涂薺
UtQ士耕;崢:崢嶸士耕切六|𦱊:𦱊薴草亂皃|鬇:鬇鬡毛髮亂皃|埩:魯城北門池也說文作淨|鏳:鏳鎗玉聲|崝:淮南子云崝陗也
TtQ楚耕;琤:玉聲楚耕切五|錚:金聲|凈:冷也出字書|棦:木束|噌:噌吰鐘音
MtQ女耕;儜:困也弱也女耕切七|薴:𦱊薴|鬡:鬇鬡|𧭈:譻𧭈|鑏:鐵鑏|䭢:充食|嬣:嬣体
BtA普耕;怦:心急又中直皃普耕切十一|姘:齊與女交罰金四兩曰姘蒼頡篇曰男女私合曰姘|閛:門扉聲|𤘾:牛色駁如星也|伻:使人|弸:弸彋也|䍬:使羊|㛁:急也|匉:匉訇大聲|抨:撣也|砰:砰磕如雷之聲
itg呼宏;轟:群車聲呼宏切十|輷:+上同|䎕:群鳥弄翅|揈:擊聲|訇:匉訇大聲又姓蜀錄關中流人訇琦訇廣|鍧:鏗鍧鐘鼓聲相雜也|渹:水石聲又大也|𦑟:飛聲|𥕗:石落聲|𢝁:㥊𢝁好嗔皃
AtA北萌;繃:束兒衣墨子云禹葬會稽桐棺三寸葛以繃束也北萌切五|絣:振繩墨也|𢆸:+上同|拼:爾雅云使也又從也|䑫:艣䑫舟具
LtQ宅耕;橙:柚屬宅耕切十二|揨:撞也觸也|𢾊:-|𢿦:+並上同|湞:水名出南海|朾:爾雅曰蠪朾螘郭璞云赤駁蚍蜉|虰:+上同|憕:失志皃又音澄|瞪:直視皃|䆵:䆵𥥈響也|䁎:安審視也|䆑:小突
htg烏宏;泓:水深也烏宏切四|謍:謍𧭈|宖:屋響又戶萌切|𨳮〈𩰎〉:試力士錘
CtA薄萌;輣:兵車薄萌切五|棚:棧也|弸:弓弱皃|㥊:㥊𢝁好嗔皃|庄:平也亦作□
gtQ五莖;娙:身長好皃漢書曰娙娥婦官也武帝邢夫人號娙娥五莖切二|俓:急也
StQ側莖;爭:競也引也側莖切七|箏:樂器秦蒙恬所造|埩:理也治也|綪:禮云齊則綪結佩|䋫:縈也|猙:獸名似豹一角五尾又音淨|䱢:魚名
#清
OuQ七情;清:山海經曰太畤之山清水出焉釋名曰清青也去濁遠穢色如青也又靜也澄也潔也七情切二|圊:廁也
PuQ疾盈;情:靜也說文曰人之陰气有所欲也疾盈切五|晴:天晴|請:受也又在性七井二切|夝:說文曰雨而夜除見星也|䝼:䝼受賜也
NuQ子盈;精:明也正也善也好也說文曰擇也易曰純粹精也子盈切十五|氏:狋氏縣名狋音權|菁:蕪菁菜也|鶄:鵁鶄鳥也|蜻:蜻𧊿蟋䗿也|晶:光也|鼱:鼱鼩小鼠|婧:竦立也又慈性切|睛:目珠子也|𣻒:水名在南郡|旌:旌旗周禮曰析羽爲旌爾雅注云曰注旄首曰旌|旍:+上同見禮|箐:笭箐小籠|𩓨:䫢𩓨頭不正也|聙:聰聽也
luQ以成;盈:充也滿也又姓出姓苑以成切十二|嬴:秦姓|㜲:美好皃|瀛:大海亦州名漢河閒王國後魏於此立瀛州蓋以瀛海爲名|籝:籠也說文笭也漢書曰遺子黃金滿籝不如教子一經亦作籝|楹:柱也孔子曰夢奠於兩楹|贏:利也益也有餘也財長也|𤟣:似狐色黃|䕦:菊花一名帝女花|𨜏:姓也出姓苑|𦝚:魯大夫名|攍:擔也
lug余傾;營:造也度也說文曰市居也亦州名舜分青州爲營州爾雅曰齊曰營州今青州也又姓風俗通云周成王卿士營伯之後漢有京兆尹營郃余傾切六|鎣:采鐵又音瑩|塋:墓域|䁝:惑也又戶扃切|濴:波勢回皃|謍:說文曰小聲也引詩云謍謍青蠅
huU於盈;嬰:蒼頡篇云女曰嬰男曰兒又姓風俗通云晉大夫季嬰之後於盈切七|瓔:瓔珞|纓:冠纓禮記玉藻曰玄冠朱組纓|攖:亂也|𨟙:地名又一井切|賏:貝飾|蘡:蘡薁藤也
JuQ陟盈;貞:正也陟盈切六|楨:楨榦題曰楨旁曰榦又女楨冬不凋木也|禎:善也祥也|𨜓:地名又直貞切|湞:湞陽縣名湞水所出|𨺟:丘名
KuQ丑貞;檉:木名說文云河柳也丑貞切八|偵:偵候又丑鄭切|赬:赤色俗作頳|䞓:+上同|䟓:跉䟓行不正|竀:正視|蟶:蚌屬|虰:螘也
ZuQ是征;成:畢也就也平也善也亦州名古西戎地州南八十里有仇池山晉改爲仇池郡後爲南秦州梁廢帝改爲成州又姓出上谷東郡二望本自周文王子成伯之後又漢複姓十五氏莊子有務成子廣成子顏成子游伯成子高韓子有容成子列子有考成子國語晉郤犫食采苦成後因以爲氏世本曰宋有大夫老成方盆成括仕於齊晉有英成僖子漢有廣漢太守古成雲古音枯高祖功臣有陽成延後漢有密縣上成公白曰升天晉戊己校尉燉煌車成將古成氏之後史記有形成氏是征切十|𢦩:+古文|城:城郭崔豹古今注云城者盛也所以盛受民物也又淮南子曰鮌作城亦姓風俗通云氏於事者城郭園池是也|誠:審也敬也信也|宬:屋容所受也|郕:地名也在東平|筬:筬筐織具|盛:盛受也黍稷在器也又時正切|珹:珠類|䫆:頸也
LuQ直貞;呈:示也平也見也直貞切七|程:期也式也限也品也又姓出廣平安定二望本自顓頊重黎之後周宣王時程伯休父入爲大司馬封于程後遂爲氏與司馬氏同|酲:酒病|𨜓:地名又音貞|珵:玉名|䇸:筵也|裎:佩帶又恥領切
auQ書盈;聲:聲音又姓左傳蔡太夫聲子書盈切一
XuQ諸盈;征:行也諸盈切十三|𨒌:+上同|鯖:煑魚煎食曰五侯鯖又倉經切|𨢹:-|𦙫:+並上同|鉦:鐃也似鈴|怔:怔忪懼皃|正:正朔本音政|鴊:方言云齊魯閒謂題肩爲鴊鳥|䋊:乘輿馬飾|眐:獨視皃|𧘿:𧘿衳小兒衣出字林|佂:佂伀遽行皃
euU去盈;輕:輕重去盈切三|𨆪:一足跳行|鑋:說文曰金聲也
DuE武并;名:名字春秋說題辭曰名成也大也功也号也說文曰自命也从夕口夕者冥不相見故以口自名也又姓左傳楚大夫彭名之後武并切二|洺:水名在易陽亦州名春秋時爲赤狄之地後屬晉秦爲邯鄲郡周於此置名州以洺水爲名
IuQ呂貞;跉:跉䟓呂貞切二|令:使也又呂鄭郎丁二切
AuE府盈;并:合也亦州名舜分冀州爲幽州并州春秋時爲晉國後屬趙秦爲太原郡魏復置并州又姓出姓苑府盈切四|栟:栟櫚木名|箳:箳篂車轓|屏:屏盈徬徨又餅萍二音
euk去營;傾:側也伏也敧也去營切二|頃:西頃地名出地理志說文曰頭不正也又去潁切
RuQ徐盈;𩛿:飴也徐盈切一
huk於營;縈:繞也於營切五|褮:說文云鬼衣也|嫈:小心態又烏莖切|䪯:聲也|𢄋:覆也
fuk渠營;瓊:玉名渠營切十七|璚:+上同|煢:獨也一曰迴飛也|焭:+上同|睘:驚視|惸:無弟兄也|𢶇:博𢶇子一名投子|藑:藑茅草也|嬛:好也|𡞦:+上同|赹:獨行皃|憌:憂也|𢗋:+上同|𦽓:草旋|𦾵:+上同|𨍶:車輮規一曰輪車也|㒌:特也
Qug息營;騂:馬赤色也息營切四|𤙡:+上同|垶:赤土|觪:角弓
fuU巨成;頸:項也頸在前項在後巨成切又居郢切四|𩷏:魚名|葝:鼠尾草又山薤又音擎|𦳲:+上同
iuk火營;𧵣:𧵣貨也火營切一
#青
OvQ倉經;青:東方色也亦州名九州之一禹貢曰海岱惟青州又男青女青皆木名出羅浮山記亦姓出何氏姓苑又漢複姓三氏風俗通云漢有青烏子善數術又有青牛氏青陽氏倉經切五|鶄:鶄鶴鳥也出南海又音精|鯖:魚名又諸盈切|蜻:蜻蜓蟲方言曰蜻蛉謂蝍蛉也六足四翼又音精|靘:䒌靘無色
dvQ古靈;經:常也絞也徑也亦經緯又姓出何氏姓苑古靈切又音徑四|涇:水名淮南子云涇水出薄落之山|鵛:鸒鵛鷋也|巠:直波爲巠說文曰水脈也
jvQ戶經;𠛼〈㓝〉:說文曰罰辠也今只用下文刑戶經切十七|刑:法也禮曰刑者侀也侀者成也一成而不可變故君子盡心焉說文剄也|形:容也常也|邢:地名在鄭亦州名古邢侯國也項羽爲襄國隋爲邢州取國以名之又姓出河閒也本周之胤邢侯爲衛所滅後遂爲氏漢有侍中邢辟直道忤時讁爲河閒鄚令因家焉|𤬐:小瓜|䣆:鄉名在密|桯:牀前長几又音廳|鉶:祭器|型:鑄鐵模也又作𠜚|陘:連山中絕又姓陘晉邑也其大夫氏焉今有井陘縣|侀:成也|硎:砥石|娙:女長皃又五莖切|鈃:酒器似鐘而長頸也|㼛:-|𤭓:+並同上|鋞:說文曰溫器也圜而直上
GvQ特丁;庭:門庭又直也亦州名即漢車師後王庭之地本烏孫國土也其前王庭即交河縣是也特丁切二十一|停:息也定也止也|鼮:鼮鼠豹文漢武帝得此鼠孝廉郎終軍識之賜絹百匹|莛:草莖|葶:葶藶|筳:竹筳|亭:今亭子名釋名曰亭停也人所停集也漢典職曰洛陽二十街街一亭十二城門門一亭也|聤:耳出惡水|霆:雷霆|渟:水止|𩹇:魚名|綎:綬也|娗:好皃|㼗:甎也|𧖧:定息|挺:縣名在膠東又徒頂切|楟:山棃木名|蜓:蜻蜓亦蟪蛄別名|廷:風俗通云廷者平也又正也國家朝廷也釋名曰廷停也人所停集之處漢書曰廷尉秦官也應劭曰古官也|㹶:猱㹶猨屬|𧓴:埤蒼云蠶二眠
EvQ當經;丁:當也亦辰名爾雅云太歲在下曰強圉又姓本自姜姓齊太公子伋諡丁公因以命族出濟陽濟陰二望當經切八|釘:又都定切|玎:玉聲|䦺:丘名|靪:補履下也|虰:爾雅曰虰蛵負勞郭璞云或曰即蜻蛉也|仃:伶仃獨也|叮:叮嚀
ivQ呼刑;馨:香也呼刑切三|𠷓:說文聲也|蛵:虰蛵
QvQ桑經;星:星宿說文曰萬物之精上爲列星淮南子曰日月之淫氣精者爲星辰也又姓羊氏家傳曰南陽太守羊續娶濟北星重女桑經切十二|曐:+上同出說文|腥:豕息肉又先定切|胜:犬膏臭也|鮏:說文云魚臭也|鯹:+上同|𥠀:稀程|醒:酒醒又思挺先定二切|鉎:鐵鉎|篂:箳篂別駕車轓|猩:說文曰猩猩犬吠聲又音生|惺:惺𢤄了慧皃出聲類
BvA普丁;竮:竛竮行不正亦作伶俜普丁切八|俜:+見上注又匹正切|甹:甹夆掣曳說文曰亟詞也或曰甹俠也三輔謂輕財者爲甹|𢖊:使也|艵:縹色|頩:面色又普冷切|姘:男女會合|覮:淮南子云覮然能聽
IvQ郎丁;靈:神也善也巫也寵也福也亦州名漢北郡富平縣地赫連勃勃之果園也後魏置靈州取靈武縣名爲之又姓風俗通云齊靈公之後或云宋公子靈圍龜之後晉有餓者靈輒郎丁切八十七|霛:-|𩆈:+並古文|𩆜:廣雅曰玉名說文曰巫以玉事神也與靈同|舲:舟上有窻|齡:年也|麢:大羊|𦏰:+上同|囹:囹圄|鴒:䳭鴒|䉁:竹名|蛉:蜻蛉|鈴:似鐘而小|霝:落也墮也說文曰雨𩂣也从雨𠱠象雨𩂣形或作零|醽:淥酒|苓:茯苓|櫺:窻櫺又櫺檻階際欄|柃:說文木也|𩆚:空也|伶:樂人|泠:清泠水也又水名出丹陽又姓左傳周大夫泠州鳩|瓴:瓴甋一曰似甖有耳|𧕅:說文曰螟𧕅桑蟲也或作蛉|拎:手懸捻物|刢:刢利使性人也|𧆺:似虎而小出南海|𤣘:通俗文云猪糞曰𤣘|𤫲:小瓜名出安南|玲:玲瓏玉聲|𦉢:似瓶有耳|𩖊:瘦也|㾉:+上同|聆:以耳取聲|竛:竛竮|𠄖:字類撞𠄖|蘦:菜名似葵可食|軨:車闌|䡼:+上同|笭:笭箐小籠|零:落也說文曰徐雨也又姓出姓苑|孁:女字|令:漢複姓有令狐氏本自畢萬之後國語云晉大夫令狐文子即魏顆也自漢已後世本太原至邁爲王莽所誅邁少子始居燉煌也|𪕌:𪕍𪕌班鼠|灵:字類云小熱皃|𩟃:食飽|𩵀:山海經曰神名人面獸身或作龗一曰龍名|龗:說文龍也|翎:鳥羽|閝:門上小窻出崔浩女儀|鹷:壃鹷|䴇:䴇鳥鶴別名也|昤:昑曨日光出道書|駖:駖蓋車騎聲|𧖜:螢也|𩆮:器名又人名也|蕶:草蕶落也|酃:地名在湘東|詅:詅音相次出異字音|彾:彾𢓳行皃|䯍:𩨾骨|呤:埤蒼云呤呤語也|跉:徐行不正皃出異字音|狑:犬名|𤣤:+上同|爧:火光皃|冷:冷凙吳人云冰凌又力頂切|怜:心了黠皃|𠱠:眾鳥也從三口|𦫊:𦫊艦有屋舟名|𢺰:插空又力定切|澪:水名|鏻:健也|𥤞:草莖疎也|秢:穗熟玉篇云年也|䕘:鼠耳草也本亦作苓|獜:玉篇云獜獜犬聲又力仁切|岭:山深皃|魿:魚連行皃|𣬹:毛結不理玉篇云長毛也|𩚹:餌也|紷:綼絲一百升又絮名|䉹:竹名|砱:石砱|阾:阪名|羚:羊子|姈:女字|㸳:牛名
HvQ奴丁;寧:安也說文曰願詞也亦州名禹貢古西戎地秦爲北地郡亦爲豳州又爲寧州奴丁切九|寍:說文曰安也从宀心在皿上皿人之食飲器所以安人也|鸋:爾雅曰鴟鴞鸋鴂又曰鴽子鸋|䆨:天也|𣍆:告也又乃定切|𨚶:鄉名在馮翊谷口又奴顛切|𧕝:螻蛄|嚀:叮嚀|聹:耳垢又乃鼎切
FvQ他丁;汀:水際平沙也他丁切十四|訂:平議也又徒頂他頂二切|桯:碓桯|綎:絲綬帶綎|聽:聆也又湯定切|廳:廳屋|町:田處又徒頂切|艼:草名|𦉬:罟也|䩠:皮帶䩠也|鞓:+上同|䋼:縚屬說文緩也|𦀚:+上同|庁:平庁
DvA莫經;冥:暗也幽也又姓禹後因國爲氏風俗通云漢有冥都爲丞相史莫經切十五|榠:榠樝果木|銘:銘記釋名曰銘名也記名其功也|鄍:晉邑|溟:溟濛小雨又溟海也|䫤:眉目閒也|螟:螟蛉桑蟲說文曰蟲食穀葉者吏冥冥犯法即生螟|𧱴:小豚|猽:+上同|蓂:蓂莢堯時生於庭隨月彫榮|瞑:合目瞑瞑又亡千切|𥹆:潰米|嫇:好皃|覭:小見也又爾雅曰覭髳茀離也又莫的切|暝:晦暝也
CvA薄經;瓶:汲水器也又姓風俗通云漢有太子少傅瓶守後趙錄有北海瓶子然二姓蓋別薄經切十五|缾:+上同|蛢:以翼鳴蟲|䶄:鼠子說文云䶄令鼠|屏:三禮圖曰扆從廣八尺畫斧文今之屏風則遺象也又必郢切|荓:荓馬帚以蓍又荓翳雨師名也|䈂:竹名|軿:輜軿兵車|萍:水上浮萍|蓱:+上同|竮:竛竮又普經切|郱:郱城在東莞|𤲒〈𤳊〉:織蒲爲器|洴:莊子曰有洴澼絖造絮者也|箳:箳篂別駕車名
jvg戶扃;熒:光也明也戶扃切六|褮:衣開孔也又音縈鬼衣也|螢:螢火禮記云季夏月腐草爲螢一名丹良又名蚈|滎:小水也又水名在鄭州|䁝:䁝惑也又余傾切|𧵣:貨也
dvg古螢;扃:戶外閉關古螢切八|駉:駿馬也詩曰駉駉牡馬傳云良馬腹幹肥張也|駫:馬肥盛也|坰:野外曰林林外曰坰|冋:+古文|𪕍:𪕍𪕌班鼠|絅:引急也|𣕄:木名
#蒸
XwQ煑仍;蒸:眾也進也君也又麁曰薪細曰蒸說文曰析麻中幹也又爾雅曰冬祭曰蒸經典亦作烝煑仍切七|䒱:+說文同上|烝:說文曰火氣上行也|𦚦:熟也|䕄:葅也|篜:玉篇云竹也|脀:癡皃
ZwQ署陵;承:次也奉也受也又姓後漢有承宮署陵切三|丞:佐也翊也物理論曰高祖定天下置丞相以統文德立大司馬以整武事爲二府也|𨋬:軺車後登也出字林
LwQ直陵;澂:清也直陵切五|澄:+上同|瞪:直視也又直庚切|憕:平也又竹萌切|懲:戒也上也
IwQ力膺;陵:大阜曰陵釋名曰陵崇也體崇高也又犯也侮也侵也遟也又漢複姓六氏吳延陵季子之後有延陵氏高士傳有於陵子仲戰國策有安陵丑呂氏春秋有鉛陵卓子漢有高陵顯秦昭王弟高陵君之後楚有公子食采於鄧陵後以爲氏力膺切十八|淩:歷也又水名出臨淮亦姓吳將有淩統|夌:說文越也|綾:綾紈|凌:冰凌|𠗲:+上同|蔆:芰也|菱:-|䔖:+並同|㥄:怜也|鯪:臨海風土記曰鯪魚腹背皆有刺如三角蔆也|崚:崚嶒山皃|㱥:㱥殑鬼出皃|𡕮:去也|𩜁:說文曰馬食穀多氣流四下也本力甑切|掕:止也又力證切|祾:祭名神靈之福|𣣋:欺𣣋俗
hwc於陵;膺:胷也親也於陵切四|應:當也又姓出南頓本自周武王後左傳曰邘晉應韓武之穆也漢有應曜隱於淮陽山中與四皓俱徵曜獨不至時人語之曰南山四皓不如淮陽一老八代孫劭集解漢書|𧕄:寒蟬|鷹:鳥名月令曰驚蟄之日鷹化爲鳩
CwI扶冰;凭:依几也扶冰切五|馮:周禮馮相氏鄭玄云馮乘也相視也世登高臺以視天文又防戎切|憑:憑託|淜:說文曰無舟渡河也|㵗:水聲
AwI筆陵;冫:水凍也說文本作仌筆陵切三|冰:+上同說文本魚陵切|掤:說文曰所以覆矢也詩云抑釋掤忌
lwQ余陵;蠅:蟲也詩云營營青蠅余陵切一
bwQ食陵;繩:直也又繩索俗作䋲食陵切十二|譝:稱舉|憴:+上同|鱦:小魚|乘:駕也勝也登也守也說文作椉覆也又姓漢有乘昌爲煑棗侯|椉:+上同|𠅞:+古文|澠:水名在齊在傳云有酒如澠又泯緬二音|溗:波前後相淩也|塍:稻田畦也畔也|塖:+上同|騬:犗馬
awQ識蒸;升:十合也成也又布八十縷爲升識蒸切五|昇:日上本亦作升詩曰如日之升升出也俗加日|陞:登也躋也|勝:任也舉也說文本从舟經典省作月他皆倣此又漢複姓何氏姓苑有勝屠公爲河東太守又書證切|抍:上舉易曰抍馬壯吉說文音蒸上聲
cwQ如乘;仍:因也就也重也頻也又姓出何氏姓苑如乘切七|艿:草名謂陳根草不芟新草又生相因艿也所謂燒火艿者也|䚮:厚也|辸:往也|礽:福也|扔:引也|㭁:木名
dwc居陵;兢:兢兢戒慎居陵切二|矜:本矛柄也巨巾切字㨾借爲矜憐字
JwQ陟陵;徵:召也明也成也證也經典省作徵又姓吳太子率更令河南徵崇陟陵切四|𨟃:古國名|癥:腹病|𣃘:旌旗柱說文本丑善切旌旗杠皃
PwQ疾陵;繒:繒帛又姓漢功臣表有繒賀疾陵切六|鄫:國名也在琅邪|驓:馬名四骹皆白|橧:豕所寢也|竲:高皃|嶒:崚嶒山皃
gwc魚陵;凝:水結也又成也魚陵切一
iwc虛陵;興:盛也舉也善也說文曰起也从舁从同同力也亦州名戰國時爲白馬氐之地漢置武都郡魏立東益州梁爲興州因武興山而名虛陵切又許應切三|［嬹］:女字|𨞾:說文曰地名也
YwQ處陵;稱:知輕重也說文曰銓也又姓漢功臣表有新山侯稱忠處陵切又昌證切三|爯:并舉也|偁:宣揚美事又言也好也揚也舉也足也
fwc其矜;殑:殑㱡欲死狀其矜切又其拯切二|䔷:草名根可緣竹器又音琴
VwQ山矜;㱡:殑㱡山矜切一
ewY綺兢;硱:硱磳石皃綺兢切又苦本切一
KwQ丑升;僜:醉行皃丑升切三|庱:亭名在吳興孫權射虎處又丑拯切|睖:睖瞪直視
UwQ仕兢;磳:硱磳仕兢切一
BwI披冰;砅〈砯〉:水擊山巖聲披冰切一
#登
ExQ都滕;登:成也升也進也眾也說文曰上車也亦州名漢文帝封悼惠王子爲牟平侯即此地也周爲登州取文登山而名又姓蜀有關中流人始平登定都滕切八|璒:石似玉也|燈:燈火|簦:長柄笠也|㲪:毾㲪|䔲:金䔲草|㽅:瓦器|䳾:䳾鶛鳥也
IxQ魯登;楞:四方木也魯登切六|棱:+上同又威棱又柧棱木也|稜:+俗|輘:車聲|倰:倰儯長皃|祾:祭也福也靈也
QxQ蘇增;僧:沙門也梵音云僧伽蘇增切三|鬙:鬅鬙髮短|䒏:䒐䒏神不爽也
AxA北滕;崩:說文云山壞也北滕切一
NxQ作滕;增:益也加也重也又埋幣曰增作滕切十二|憎:憎疾|磳:硱磳石皃又士殑切|曾:則也亦姓曾參之後漢有尚書曾偉古作曾又音層|矰:弋射矢也|罾:魚網|熷:蜀人取生𠟼於竹中炙|䎖:舉也又飛鳥皃|竲:巢高|橧:禮運曰夏則居橧巢|譄:加言也|𦼏:菎草
DxA武登;瞢:目不明武登切四|蕄:爾雅云存存蕄蕄在也|䒐:䒐䒏神不爽也|𦱟:穢也
PxQ昨棱;層:重屋也昨棱切又作滕切三|曾:經也又作滕切|䁬:目小作態瞢䁬也
CxA步崩;朋:朋黨也五貝曰朋書云武王悅箕子之對賜十朋也步崩切六|堋:射堋|鵬:大鳥|棚:棚閣又薄庚切|倗:輔也又姓漢書王尊傳云南山羣盜倗宗等又匹等切|鬅:鬅鬙被髮
jxg胡肱;弘:大也又姓衛有弘演胡肱切三|鞃:𩉦鞃軾中靶也|苰:藤苰胡麻也
dxg古弘;肱:臂也古弘切二|𩉦:軾中靶也
ixg呼肱;薨:說文云公侯卒也呼肱切五|𠐿:說文曰惛也|𩖎:惛迷也|𩙛:𩙛𩙛大風也|𤃫:水聲
HxQ奴登;能:工善也又獸名熊屬足似鹿亦賢能也奴登切又奴代奴來二切一
GxQ徒登;騰:馳也躍也說文曰傳也一曰犗馬也徒登切十二|滕:國名亦姓滕侯之後以國爲氏|縢:行縢|幐:囊可帶者|螣:螣蛇或曰食禾蟲|藤:藤苰又藤蘿|謄:移書謄上|𧈜:黑虎也|儯:倰儯長也|𤻴:𤻴痛|鰧:魚名蒼身赤尾|𥉋:美目皃
jxQ胡登;恆:常也久也亦州名春秋時鮮虞國地漢爲恆山郡周武帝置恆州因山以爲名爾雅曰恆山爲北嶽又姓楚有大夫恆思公胡登切三|𢛢:+古文|峘:爾雅曰小山岌大山峘郭璞云岌謂高過
dxQ古恆;揯:急也淮南子云大弦揯則小弦絕也古恆切三|緪:大索|絙:+上同
FxQ他登;鼟:鼟鼟鼓聲他登切四|膯:飽也吳人云出方言|𤃶:小水相添益皃|𧰥:+上同
BxA普朋;漰:漰渤水擊聲普朋切二|堋:堋振動皃
#尤
kyM羽求;尤:過也甚也怨也多也說文異也又姓出姓苑羽求切九|𣏞:木名|腄:縣名在東萊|疣:結病也釋名曰疣丘也出皮上聚高如地之有丘也|肬:+上同|𪐤:+籀文|沋:水名在高密|郵:境上舍亦督郵古官号釋名曰督郵主諸縣罰負郵殿糾攝之又姓西京雜記有郵長倩|訧:過也博雅曰惡也
hyM於求;憂:愁也又姓出姓苑於求切十七|優:饒也亦優倡又姓史記楚賢臣優孟|瀀:瀀渥|𢖒:𢖒游本亦作優詩云慎爾優游|麀:牝鹿|𪋎:+上同|櫌:鉏也又打塊槌|鄾:邑名在鄧|𢆶:微小|怮:含怒不言|嚘:欭嚘歎也|耰:覆種出玉篇|獶:獶獀犬名|𧀥:菜名|纋:笄中|㱊:氣逆|妋:鼻目閒恨
IyA力求;劉:剋也陳也殺也亦劉子木名實如棃核堅味酸美出交阯又姓出彭城沛國弘農河閒中山梁郡頓丘南陽東平高平東莞平原廣陵臨淮琅邪蘭陵東海丹陽宣城南郡高堂高密竟陵長沙河南等二十五望並自陶唐氏既衰其後劉累學擾龍事孔甲范氏其後也唯河南一望即虜姓也後魏書官氏志獨孤氏後改爲劉氏力求切四十四|留:住也止也說文作畱亦姓出會稽本自衛大夫留封人之後後漢末避地會稽遂居東陽爲郡豪族吳志有左將留贊|蒥:蒥荑藥名|勠:并力也又力逐切|摎:絞縛殺也又姓魏有河內太守摎尚|鶹:鶹離鳥名少美長醜亦作流|騮:驊騮周穆王馬|駠:赤馬黑髦尾|疁:田不耕而火種|𥹷:粰𥹷饊也|流:演也求也覃也放也說文曰水行也|㳅:+古文|飂:高風也|飀:+上同|瘤:𠟼起疾也釋名曰瘤流也流聚而生腫也|榴:石榴果名博物志云張騫使西域迴所得|瑬:美金說文曰垂玉也冕飾今典籍用下文旒|旒:旗旒廣雅天子十二旒至地諸侯九旒至軫大夫七旒至轂士三旒至肩|瑠:瑠璃|𪕋:食竹根鼠又音柳|𤠑:+上同|䉧:說文云竹聲也又音柳|𥰣:竹名出玉篇|瀏:水清又音柳|䬟:風行聲又音柳|䱖:魚名|鰡:+同上|嵧:岣嵧羅君山峯|𣠚:扶𣠚藤名緣木生其味辛可食其花實似蒟醬|鎦:殺也|𦃓:綺別名也|𢷶:斬刺|𨶪〈䰘〉:殺也|懰:㤠也|餾:飯氣蒸也又力救切|䖻:蜉䖻蟲本作蜉蝣蝣音游|裗:爾雅曰衣裗謂之䘽郭璞云衣縷也齊人謂之攣或曰袿衣之飾|𪆱:飛鸓鳥名|𪎣:麻也|硫:石硫黃藥名|遛:逗遛|䚧:觩䚧角皃|憀:悲恨也又音聊|鏐:美金曰鏐即紫磨金也
OyA七由;秋:春秋說文曰禾穀熟也又姓宋中書舍人秋當七由切十七|秌:+古文|鞧:車鞧|緧:+上同說文曰馬紂也|𦃈:+上同周禮曰必𦃈其牛後|鞦:+亦上同又鞦韆繩戲古今蓺術圖曰鞦韆北方山戎戲以習輕趫者|湫:水池名北人呼|鶖:禿鶖鳥亦作𪀖|鰍:魚屬亦作鰌|楸:木名|萩:蕭似蒿也|𪓰:爾雅曰鼁𪓰蟾諸郭璞云似蝦蟆居陸地淮南謂之去蚥|䵸:+上同|蟗:爾雅曰次蟗鼅鼄|䨂:雞雛|篍:說文云吹筩也玉篇云吹簫也|趥:說文曰行皃
lyA以周;猷:謀也已也圖也若也道也說文曰玃屬一曰隴西謂犬子爲猷以周切四十五|猶:+上同又尚也似也|悠:遠也遐也思也憂也|油:水名出武陵又油脂|由:從也經也用也行也又姓史記有由余|攸:所也又姓北燕尚書攸邁|蕕:水蕕草又臭草|浟:水流皃|𠧴:氣行皃或作逌|𢋅:歋𢋅以手相弄|冘:冘豫不定|𨙂:行也|輶:輶車又易受移授二切|蘨:草盛也|秞:禾盛皃|蚰:蚰蜒|蝣:蜉蝣朝生夕死|櫾:木名出崐崘山|楢:積也又音酉|𦳷:水草一名軒于|斿:旌旗之末垂者|游:浮也放也又姓出馮翊廣平前燕慕容廆以廣平游邃爲股肱|遊:+上同|𨒰:+古文|卣:中樽樽有三品上曰彝中曰卣下曰罍|䚻:從也|鮋:鮂鮋小魚|鯈:+上同|抌:抒臼出周禮|揄:+上同又音俞|舀:+上同又以沼切|偤:侍也出文字辨疑|䍃:瓦器|𤪎:遺玉又弋九切|邮:亭名在高陵|繇:猶也|㳛:皁也|㾞:病也又息惡𠟼|囮:鳥媒|㘥:+上同|庮:久屋木周禮曰牛夜鳴則庮鄭司農云庮朽木臭也又弋久切|甹〈㕀〉:空也說文云木生條也引書云若顛木之有㕀枿又胡感切|𣔴:+上同|𧡹:下視深也|𦵵:說文草也
gyM語求;牛:大牲也世本曰黃帝臣胲作服牛史記曰紂倒曳九牛又姓出隴西本自殷周封微子於宋其裔司寇牛父帥師敗狄長丘死之子孫以王父字爲氏風俗通云漢有牛崇爲隴西主簿馬文淵爲太守羊喜爲功曹涼部云三牲備具語求切一
NyA即由;遒:盡也即由切又自秋切十一|鮂:烏化爲魚頂上有細骨如禽毛|䎿:耳鳴聲|蝤:蝤蛑似蟹而大生海邊也又自秋切|啾:啾唧小聲|逎:縣名在燕又迫也促也|𩭓:接髮|揂:聚也|揫:束也聚也|湫:水名又子小切|𣟼:聚也又束枲也
PyA自秋;酋:長也說文曰繹酒也禮有大酋掌酒官也自秋切十|㥢:慠也|遒:盡也又即由切|䎿:耳中聲也又即由切|崷:崷崪山峻皃|鰌:魚名二月有之|蝤:蝤蠐蝎也|煪:煪熮|𧤕:隿射收繳角也|𦵩:𦵩液周禮音糟
QyA息流;脩:脯也又長也又姓漢有屯騎校尉脩炳姓苑云今臨川人息流切七|修:理也說文飾也|羞:恥也進也又致滋味爲羞|𩛢:𩛢饙|𩝧:+上同|䡭:䡭䡜載喪車|樇:木名
KyA丑鳩;抽:拔也引也或作紬紬引其端緒也丑鳩切八|𢭆:+上同|㨨:+上同見說文|婤:好皃又音周|𥈌:失意視皃|惆:惆悵|瘳:病愈|妯:詩曰憂心且妯妯動也悼也
e0Y去秋;恘〈𠁫〉:戾也去秋切三|惆:+上同|𣪘:𣪘屈
YyA赤周;犫:白色牛說文曰牛息聲也又姓風俗通云晉大夫郤犫之後呂氏春秋云陳有惡人焉曰敦洽犫糜狹顙廣額顏色如漆陳侯悅之赤周切二|犨:+上同
XyA職流;周:周帀也又至也備也徧也密也又姓出汝南廬江尋陽臨川陳留沛國泰山河南等八望本自周平王子別封汝川人謂之周家因氏焉一云赧王爲秦所滅黜爲庶人百姓稱爲周家因而氏焉魏官氏志獻帝次兄普氏後改爲周氏又漢複姓魏初徵士燉煌周生烈晉武帝中經簿云周生姓烈名職流切十|州:州郡周禮曰五黨爲州又姓左傳晉大夫州綽|𥺝:𥹜𥺝米粉餅出字林|輖:重載也|洲:洲渚也爾雅曰水中可居曰洲|賙:贍也|喌:呼雞聲又音祝|舟:舟船墨子曰工倕作舟呂氏春秋曰虞姁作舟世本曰共鼓貨狄作舟二人並黃帝臣又姓左傳晉大夫舟之僑|郮:黃帝後所封國|婤:女字左傳衛襄公有嬖人婤姶又音抽
ZyA市流;讎:匹也仇也市流切十|𣫐:懸擊也|𣀓:+上同說文棄也|鮋:魚名又直留切|酬:周也報也以財貨曰酬又酬酢|醻:+上同說文本作𨢫主人進客也|詶:以言荅之又之又切|雔:說文曰雙鳥也又爾雅曰雔由樗繭郭璞云食樗葉俗作㘜|魗:惡也棄也又音醜|𨞪:蜀江原地又音儔
cyA耳由;柔:順也說文曰木曲直也耳由切十六|鍒:鐵之耎也|㽥:良田|騥:馬青驪也|蝚:爾雅云蛭蝚至掌又云蝚蛖螻蛭音質|蹂:踐穀又而九切|葇:香葇菜|鞣:熟皮|鰇:魚名|瑈:玉名也見聲類|腬:肥皃|鶔:鶝鶔鳥|揉:捻也又順也詩曰揉此萬邦又汝又切|䰆:馬之繁鬣|𨛶:鄉名|䐓:面和
ayA式州;收:斂也捕也又夏冕名史記曰堯黃收純衣俗作収式州切一
eyM去鳩;丘:聚也空也大也又丘陵爾雅非人爲之曰丘郭璞云地自然生說文作丠亦姓出吳興河南二望風俗通曰魯左丘明之後又云齊太公封於營丘支孫以地爲氏代居扶風漢末丘俊持節江淮屬王莽篡位遂留江左居吳興也又漢複姓四十四氏左傳齊有藉丘子鉏梁丘據閭丘嬰莒有著丘公渠丘公後並因邑爲氏晉有虞丘書爲乘馬御祖氏家記有太中大夫東安於丘淵史記有狐丘子林楚有苞丘先生齊桓公至麥丘麥丘人年八十三祝桓公封於麥丘其後氏焉孟子齊有曼丘不擇又有咸丘蒙隱居列仙傳有浮丘公梁州刺史莊丘黑魯莊公庶子食采於瑕丘其後氏焉齊有勇士葘丘訢神仙傳漢有稷丘子又有廩丘充隱居齊魯之閒楚有列威將軍何丘寄楚文王庶子食采於軒丘其後爲氏周宣王支庶食采於謝丘其後爲氏漢有趙人吾丘壽王又有曹丘先生侍御史余丘炳鉅鹿太守莊丘勝以勇力聞安丘望之注老子列仙傳有高邑人商丘子胥藝文志有桑丘公漢有吳人龍丘萇隱居不屈濟北蛇丘惑爲河內太守魏有幽豫二州刺史母丘儉吳有平原陶丘洪晉有雍丘洛以武力聞何氏姓苑云漢有司隷校尉水丘岑古有蔡丘欣喪馬淮陽東海北丘氏又有羌丘常丘崎丘獻丘陽丘逢丘厚丘泥丘等氏又虜複姓二氏後魏獻帝次弟丘敦氏後改爲丘氏丘林氏後改爲林氏去鳩切六|丠:+古文|蓲:烏蓲草名|蚯:蚯蚓蟲名禮記孟夏月蚯蚓出|邱:地名|訄:迫也
ByM匹尤;䬌:風吹皃匹尤切七|秠:一稃二米又芳鄙切|𡫺:寐作聲|衃:凝血|肧:孕一月又普回普來二切|紑:說文云白鮮衣皃又甫鳩切|醅:醉飽又普裴切
dyM居求;鳩:鳥名又聚也居求切十|𦫶:秦𦫶藥名又居由切|𠠳:大力|朻:高木又居虯切|䡂:車軫長也|㽱:腹中急痛又古巧切|𨷺〈鬮〉:鬮取也又音糾|丩:相糾繚也|龜:又居危切|勼:說文聚也
AyM甫鳩;不:弗也又姓晉書有汲郡人不準盜發六國時魏王冢得古文竹書今之汲冢記也甫鳩切又甫九甫救二切五|哹:吹氣|紑:詩傳云潔鮮貌|䍍:未燒瓦器|鴀:鴀鳩鳥也
VyA所鳩;𢯱:索也求也聚也所鳩切十七|搜:+上同凡從叜者作叟同|餿:飯壞|颼:颼飋風皃|溲:小便|鎪:馬金耳飾|廋:匿也論語曰人焉廋哉|蒐:茅蒐草又春獵曰蒐|䕅:鷄腸草也|獀:獶獀南越人名犬|䐹:乾魚|鄋:北方國名|螋:蛷螋蟲亦名蠷螋|騪:𩢸騪蕃中大馬|犙:牛三歲也又息含切|醙:白酒|𧽏:𧻖𧽏不進
TyA楚鳩;搊:手搊楚鳩切七|𢬆:俗餘倣此|篘:酒篘|醔:+上同|㮲:板木不正|𥻤:𥻤粉|謅:謅䜉陰私小言
SyA側鳩;鄒:縣名屬兗州又姓漢有鄒陽側鳩切十四|鄹:+上同|郰:說文云孔子之鄉也論語作鄹|騶:廏御亦騶虞仁獸又姓越王之後|齱:齱齵齒偏|陬:鄉名一曰隅也|緅:青赤色也又子侯切|䑼:艆䑼海船名|𨃘:獸足也|菆:草名又矢之善者說文曰麻蒸也一曰蓐也|棷:薪之別名又叉茍切|箃:竹柴別名|𠿈:小兒聲|黀:聚麻
UyA士尤;愁:憂也悲也苦也士尤切二|㵞:腹中有水氣也
iyM許尤;休:美也善也慶也息也又木名許尤切十三|貅:貔貅猛獸|㹯:+上同|鵂:鵂鶹鳥也|𩢮:馬名|㾋:下病|庥:爾雅曰庇庥廕也郭璞曰今俗呼樹蔭爲庥|脙:瘠也俗作䏫又音求|𦜵:+上同|髤:周禮駹車有髤飾注謂髤漆赤多黑少也或作髹|䰍:+上同|咻:口病聲也|㵻:汗面或作膄
RyA似由;囚:拘也繫也似由切六|泅:人浮水上|汓:+古文|苬:苬芝瑞草一歲三華又音由|慒:慮也又在冬切|鮂:白鯈
LyA直由;儔:儔侶也直由切二十七|檮:剛木也|躊:躊躇|幬:說文作𢅂襌帳也|𢃖:+上同|裯:襌被|𠷎:咨也說文誰也又作𠾉|疇:誰也等也壅也田疇也又疇昔說文作𤲮耕治之田也|紬:大絲繒又音抽|綢:綢繆猶纏綿也|稠:穊也多也|燽:著也|薵:薵藸蔥名|鯈:魚子又魚名也|籌:籌筭|𪆇:雉爾雅云南方曰𠷎字或從鳥|𪇘:+上同|棸:字統云姓也又側鳩切|椆:木名不凋|怞:朗也|𦡴:𦡴腊脯也|懤:愁毒皃|鮋:魚名又音由|䬞:風颸|菗:荼菜|𨞪:蜀江原地又上牛切|𥲅:說文云籌箸也
JyA張流;輈:車轅也張流切十一|盩:盩厔縣在京兆府水曲曰盩山曲曰厔又云引擊也|啁:啁噍鳥聲|譸:譸張誑也爾雅亦作侜|侜:壅蔽也|𩢸:𩢸騪蕃中大馬|調:朝也詩云惄如調飢本又音條|咮:曲喙又張救切|𧻖:𧻖𧽏行不進也|𥎻:射鳥箭也|矪:+上同
fyM巨鳩;𧚍:皮衣詩云取彼狐狸爲公子𧚍又姓本作仇避讎改作𧚍巨鳩切四十四|裘:+上同|仇:讎也又姓左傳宋大夫仇牧之後又漢複姓有章仇仇尼二氏隋有章仇大翼善天文|叴:漢書地理志叴猶縣屬臨淮郡又詩曰叴矛鋈錞傳云叴三隅矛又說文曰氣高也|厹:+上同|求:索也又姓三輔決錄云漢有求伸|𡨃:+上同|頄:頰閒骨也又求龜切|蛷:蛷螋蟲|𧒔:+上同說文云多足蟲也|逑:匹也|球:美玉說文曰玉磬也|璆:+上同又渠幽切|艽:遠荒之地詩云至于艽野又獸蓐也|鼽:月令云人多鼽嚏說文云病寒鼻寒也|莍:椒也|䣇:地名|賕:財賄|殏:𣧩也|梂:說文曰櫟實也一曰鑿首|朹:爾雅曰朹檕梅郭璞云朹樹狀似梅子如指頭赤色似小㮈可食|㭝:荊㭝亭名|俅:戴也|脙:瘠也又音休|𦜵:+上同|馗:爾雅曰中馗菌今土菌可食又音逵|䊵:急引也|絿:+上同|䜪:䜱䜪亭名|扏:緩也|銶:鑿屬|𩒮:廣蒼云戴也|𥭑:籠也|毬:毛毬打者|䟵:䟵蹋也|犰:犰狳獸似魚蛇尾豕目見人則佯死|𧻱:違也|訅:安也謀也|釚:弩牙|捄:長麕皃詩曰有捄棘麕傳云捄長皃|肍:乾𠟼醬也|𢛃:怨仇也又其九切|𦬖:白荳|訄:迫也又去牛切
CyM縛謀;浮:汎也縛謀切二十四|哹:吹氣又拂謀切|桴:齊人云屋棟曰桴也|枹:鼓槌|𥰛:竹有文者|罦:覆車綱也|䍖:+上同|琈:玉名|粰:粰𥹷|䳕:䳕鳩|罘:兔罟|䱐:魚名|涪:水名在巴西|芣:芣苢車前也江東謂之蝦蟆衣|蜉:蚍蜉大螘|烰:火氣爾雅曰烰烰烝也郭璞云氣出盛|鉜:鉜鏂大釘|𡦄:多也|𦮹:姓也出纂文|艀:舟也|棓:杖也又音棒|掊:把也|䍌:小缶|䨗:雨雪皃
DyM莫浮;謀:謀計也又姓風俗通云周卿士祭公謀父之後莫浮切二十四|䱕:魚名|雺:天氣下地不應又莫貢切又莫紅切|眸:目童子|牟:說文曰牛鳴又過也陪也進也大也亦牟平縣屬登州又姓風俗通云牟子國祝融之後後因氏焉漢有太尉牟融又漢複姓三氏東萊先賢傳有兗州刺史平昌曹牟君卿禮記云魯有賓牟賈何氏姓苑有彌牟氏|侔:等也均也齊也|矛:戈矛說文曰酋矛也建於兵車長二丈象形吳越春秋曰越王以屈盧之矛步光之劒獻於吳王|𢦧:+古文|鍪:兜鍪首鎧說文曰鍑屬也|鞪:+上同漢書云鞮鞪|麰:大麥又短粒麥|𦭷:+上同|堥:堆堥小隴|劺:勉也|𨡭:𨡭䤅榆人醬|蝥:食穀蟲說文本又作蟊蟲食艸根者吏抵冒取民財則生|蟊:+上同說文曰𧖀蟊也|鷚:鷚鸙鳥也|𩭾:髮至眉或作髳|䋷:縛也|恈:愛也|鴾:鶉之別名|蛑:蝤蛑似蟹而大|繆:絲干累
#侯
jzA戶鉤;侯:候也何也美也辝也爾雅曰公侯君也又乃也又周禮司裘氏王大射則共虎侯熊侯豹侯諸侯則共熊侯豹侯卿大夫則共麋侯皆設其鵠鄭司農云方十尺曰侯四尺曰鵠說文本作矦从人从厂象張布之狀矢在其下又姓出上谷河南二望亦漢複姓八氏夏侯氏出自夏禹之後杞簡公爲楚所滅其弟佗奔魯魯悼公以佗出自夏后氏受爵爲侯謂之夏侯國而命氏後有去魯之沛者分沛立譙遂有譙魯二望羅國爲楚所滅其後号羅侯氏韓詩外傳云周宣王大夫韓侯子有賢德史記魏有屈侯鮒左傳曹有豎侯獳漢有尚書郎桓侯儁吳有張昭師白侯子安又虜三字姓二氏周書有侯莫陳氏侯崇傳云其先魏之別部也又周有大將軍伏侯龍氏名恩戶鉤切二十四|矦:+見上注|𥎦:+古文|帿:射侯見上注俗從巾|鄇:地名|䫛:䫛䫘大言|鍭:箭鏃|銗:鏂銗錏鍜|猴:獼猴猱也|糇:糇粮|翭:說文曰羽本也一曰羽初生皃|翵:+上同|餱:乾食|喉:咽喉|篌:箜篌|鯸:鯸䱌魚名|㮢:㮢桃又㮢櫟木也|𧮶:谷名在成皋亦作𧯁|瘊:疣癭|䗔:蟲名|葔:葔莎草|骺:骨骺|睺:半盲又胡遘切|䙈:䙈褕小衫
hzA烏侯;謳:吟也歌也烏侯切十六|嘔:嘔唲小兒語也|歐:歐陽複姓出長沙郡|甌:瓦器亦甌閩又姓出姓苑|區:姓也古善劒區冶子之後今郴州有之|漚:浮漚|鷗:水鳥說文云水鴞也|䁱:深目皃又䒓侯切|瞘:+上同|櫙:木名爾雅曰櫙荎今之刺榆|蓲:+上同|醧:酒甘|剾:剾㓱又恪侯切|䙔:小兒涎衣|鏂:鏂銗|膒:久脂
HzA奴鉤;羺:羺䍲胡羊奴鉤切四|獳:犬怒|䨲:兔子|䰰:鬼鬽聲䰰䰰不止也出說文
IzA落侯;樓:亦作婁重屋也亦姓夏少康之裔周封爲東樓公子孫因氏焉漢末樓秦自譙徙居會稽因以東陽爲望也又虜複姓有蓋樓氏賀樓氏落侯切二十九|婁:空也又星名亦姓邾婁國之後漢有婁敬又漢複姓五氏左傳齊大夫工婁灑漢書藝文志有齊隱士贛婁子著書何氏姓苑云母婁氏今琅邪人又有精婁氏邾婁氏又虜複姓二氏後魏獻帝次弟爲伊婁氏又有匹婁氏後並改爲婁氏說文作婁今作婁並同|䣚:鄉名又力于切|𨻻:縣名|𧁾:𦸈𧁾士瓜|蔞:爾雅曰購蔏蔞蔞蒿也生下田初出可啖詩云言采其蔞又力朱切|𠞭:剅𠞭小穿|䝏:求子豬也|𦎹:土𦎹似羊四角其銳難當觸物則斃食人出山海經|僂:傴僂又力主切|艛:舟名|耬:種具|髏:髑髏|膢:八月祭名又力于切|𤬏:𤫱𤬏苦𤬏|廔:廲廔綺窻|剅:小穿又音兜|摟:探取|嘍:嘍唳鳥聲|瞜:視皃|螻:螻蛄一名仙蛄一名石鼠爾雅曰螜天螻又曰蝚蛖螻|簍:籠也|鞻:鞮鞻氏掌四夷之樂|慺:慺慺謹敬之皃|鷜:爾雅曰鵱鷜鵞即今之野鵞|䱾:魚名|褸:衣襟又力主切|遱:說文曰連遱也|謱:說文云謰謱也
QzA速侯;涑:澣也速侯切八|鏉:刻鏤|䩳:軟皮|𩌱:+上同|𩮶:𩮷𩮶白頭人也|摗:摟摗取也出陸氏字林|𠘂:冷𠘂|𡠼:女字
ezA恪侯;彄:弓彄恪侯切八|摳:摳衣挈衣也|剾:剜裏也又乙侯切|韝:射韝臂捍也又古侯切|𢂁:指𢂁|滱:水名在北地又音寇|夠:多也|䁱:目深瞘䁱
izA呼侯;齁:齁䶎鼻息也呼侯切二|𪅺:𪅺鳥青色似䳕鳩也
NzA子侯;𣠏:麻幹也子侯切五|緅:青赤色也再染曰緅三入成纁|陬:隅也又聚居|棷:薪別名|掫:說文云夜戒守有所擊也
FzA託侯;偷:盜也爾雅云佻偷也謂苟且託侯切四|鍮:鍮石似金陶之則分|鋀:+上同|媮:薄也又巧黠也
GzA度侯;頭:說文云頭首也釋名云頭獨也於體高而獨也度侯切十五|㓱:剾㓱足節又刀剜物|投:託也弃也合也說文擿也亦姓郇伯周畿內侯桓王伐鄭投先驅以策其後氏焉漢有光祿投調又漢複姓有投壺氏風俗通云晉中行穆子相投壺因以氏焉姓苑云東莞人也|𪎨:字書云麻一絜說文云檾屬或作䵉|骰:骰子博陸采具出聲譜|𣪌:遙擊皃|坄:陶窻|牏:築垣短版又羊朱切|䤅:𨡭䤅醬也|㢏:㢏行圊廁|揄:引也又欲朱切|窬:穿也又羊朱切|緰:布也|歈:歌也又羊朱切|𪁞:鴢頭鵁似鳧腳近尾
gzA五婁;齵:齱齵五婁切又牛俱切一
dzA古侯;鉤:曲也又劒屬字㨾句之類並無著厶者古侯切十八|𠛎:說文云關西呼鎌爲𠛎也|溝:溝渠爾雅云水注谷曰溝釋名曰田閒之水曰溝溝搆也縱橫相交構也|褠:襌衣|韝:臂捍又苦侯切|緱:緱氏縣屬河南府又姓孝子傳陳留緱氏女名玉亦刀劒頭纏絲爲緱|篝:燻籠|𥴴:𥴴𥵣桃枝竹名|𪓞:𪓟鼊似龜說文其俱切𪓷屬頭有兩角出遼東亦作𪓞|㗕:唱㗕|𤫱:𤫱𤬏|䑦:䑦𦪇船名|冓:數名十秭曰冓|枸:曲木又木名也|句:說文曲也又高句驪遼東國名又句龍社神名亦姓史記有句疆又九遇古候二切|軥:車軥心木又夏后之輅曰軥也|夠:多也|鴝:鴝鵒鳥又音衢
EzA當侯;兜:兜鍪首鎧也當侯切十|侸:佔侸垂下皃佔丁兼切|吺:輕出言也|篼:飼馬籠也|𥆖:眵目汁凝眵赤支切|剅:小穿又音婁或作𧯠|𧡸:說文云目蔽垢也|𧯠:小裂皃|郖:說文云弘農縣庾地|𩮷:𩮷𩮶白頭
PzA徂鉤;㔌:細斷徂鉤切二|鯫:魚名又七士苟切又小人之皃也
CzA薄侯;裒:聚也薄侯切九|䯽:說文云髮皃|捊:說文云引取也|抔:手掬物也|掊:詩曰曾是掊克謂聚斂也|䏽:豕𠟼醬也|𩚭:𩚭饇曰食也|䍌:說文云小缶也|箁:說文云竹箁也
OGg千侯〈隹〉;䜅:就也千侯切一
DzA亡侯;呣:慮也亡侯切一
#幽
h0U於虯;幽:深也微也隱也亦州名釋名曰幽州在北幽昧之地故曰幽禹貢冀州之域舜以冀州南北廣大分燕北爲幽州又北方曰幽都又姓出姓苑於虯切七|泑:澤在崐崘山下|呦:鹿鳴|𣢜:+上同|𧍘:𧍘蟉龍皃又一糾切|怮:說文憂皃|𢆶:微也
f0U渠幽;虯:無角龍也渠幽切又居幽切七|觩:匕曲皃|璆:玉名|觓:角爵皃|鷚:爾雅云鷚天鸙郭璞云大如鷃雀色似鶉好高飛作聲又音繆|蟉:𧍘蟉龍皃|𤙠:角皃
A0I甫烋;彪:虎文也甫烋切三|髟:髮垂皃又標彡二音|驫:馬走皃又音標
I0Q力幽;鏐:紫磨金也力幽切二|蟉:𧍘蟉又翹糾切
d0U居虯;樛:說文曰下句曰樛詩曰南有樛木傳云木下曲也居虯切五|𠃚:說文曰相糾繚也今作丩同|𦭺〈𦱠〉:草之相糾繚也|朻:說文云高木也|㽱:腹急病也
C0I皮彪;淲:水流皃亦作滮皮彪切三|瀌:雨雪皃又音鑣|𩖛:風皃
NHQ子幽〈絲〉;稵:禾生也子幽切一
V6Q山幽〈函〉;犙:牛三歲山幽切一
g0U語虯;聱:聱耴魚鳥狀語虯切又五苞切一
i0U香幽|i0Y香｟許｠幽〖彪〗;飍:a驚風香幽切又風幽切二|烋:b美也福祿也慶善也出玉篇又火交切
D0I武彪;繆:詩傳云綢繆猶纏緜也說文曰枲十絜也武彪切又目謬二音三|鷚:天鸙鳥也又音虯|䋷:縛也
#侵
O1Q七林;侵:漸進也說文作㑴又姓三輔決錄有侵恭七林切七|𢔀:+上同|駸:馬行疾也|浸:浸淫也又子鴆切|䜷:野生豆也|𥍯:錐也|綅:說文曰絳綫也詩曰貝冑朱綅又子心息廉二切
R1Q徐林;尋:長也又尋常六尺曰尋倍尋曰常山海經曰尋木長千里生河邊又姓晉有尋曾字子貢徐林切十六|𢒫:+上同出說文|鐔:劒鼻又姓漢有鐔顯又覃淫二音|潯:傍深又水涯也|鱏:魚名口在腹下又音淫|樳:木名似槐|鄩:地名在鞏又姓左傳有周大夫鄩肸|𨼔:小堆阜也|𣎟:姓也出纂文|𩖣:姓也姓苑云汝南人|襑:衣博大也|枔:木葉|撏:取也|灊:水名出巴郡又才心昨鹽二切|鬵:鼎大上小下又才心昨鹽二切|𦅀:續也
I1Q力尋;林:林木爾雅曰野外謂之林說文曰平土有䕺木曰林又姓風俗通曰林放之後力尋切八|琳:玉名|淋:以水沃也|臨:莅也大也監也又姓後趙錄有秦州刺史臨深也|痳:痳病|箖:箖箊竹名|瀶:水出皃說文云谷也一曰寒也|霖:久雨
K1Q丑林;琛:琛寶也丑林切七|棽:木枝長又林森二音|䑣:船行|𥉨〈𧡬〉:私出頭視也又丑鴆切|綝:繕也|郴:縣名在桂陽又姓陶偘別傳有江夏郴寶|賝:賝賮也
X1Q職深;斟:斟酌也益也又姓國語云祝融之後侯伯八姓斟姓無後賈逵注云斟姓是曹姓之後又漢複姓有斟弋氏出史記職深切九|針:針線|鍼:+上同說文曰所以縫也|𪈁:𪈁鴜鳥名|箴:箴規也又姓風俗通云有衛大夫箴莊子|葴:酸蔣草也|瑊:廣雅曰瑊石次玉也郭璞云瑊玏似玉之石司馬相如子虛賦曰其石則瑊玏玄礪|鱵:魚名|㘰:㘰鄩古國名
L1Q直深;沈:沒也說文曰陵上滈水也又漢複姓魯有沈猶氏常朝飲其羊何氏姓苑云今泰山人直深切又尸甚切九|沉:+俗|𤘣:水牛|莐:爾雅曰𧂇莐藩郭璞云生山上葉如韭|䒞:+上同又羊針都敢二切|霃:久陰|湛:漢書曰且從俗浮湛又徒減切|枕:繫牛杙也|鈂:鍤屬
J1Q知林;碪:擣衣石也知林切五|砧:+上同|椹:鈇椹斫木質文字指歸俗用爲桑椹字非|枮:+上同|坫:權安厝也
Z1Q氏任;諶:誠也爾雅云信也氏任切七|愖:+上同|訦:+上同說文曰燕代東齊謂信曰訦|忱:+上同|煁:煁烓行竈烓烏珪切|瘎:腹內故病|㽸:+上同
c1Q如林;任:堪也保也當也又姓出樂安黃帝二十五子十二人各以德爲姓第一七爲任氏如林切七|鵀:戴勝鳥也頭上毛似勝又女今切|恁:信也又音荏|壬:佞也又辰名爾雅曰太歲在壬曰玄黓|紝:織紝亦作䋕|銋:銋濡廣雅韏也|䛘:信也念也
a1Q式針;深:遠也又水名出桂陽南平式針切二|𦸂:蒲蒻
l1Q餘針;淫:久雨曰淫書曰罔淫于樂傳云淫過也餘針切十五|霪:久雨|婬:婬蕩|𥮍:竹名|蟫:白魚蟲|鷣:鷂之別名|䒞:熱也|冘:行皃|𢓕:+上同|䤁:熟麴又昨淫切|撢:探也|𨟏:地名|㸒:貪也又延求切|鐔:劒鼻又尋覃二音|鱏:魚名又徐林切
Q1Q息林;心:火藏釋名曰心纖也所識纖微無不貫也息林切四|𦁍:久緩皃|𨊳:車軥𨊳木|杺:木名其心黃
h1U挹淫;愔:靖也挹淫切二|韾:聲和靖也
N1Q子心;祲:曰傍氣也子心切又子禁切九|梫:木名|兓:銳意|埐:說文地也又昨淫切|𩀿:雞之別名|𪖼:高鼻|綅:縫線|𥍯:錐也|𩻛:魚名
P1Q昨淫;𩷒:大魚曰鮓小魚曰𩷒一曰北方曰鮓南方曰𩷒昨淫切十|䰼:+上同見說文|鬵:說文曰大釜也一曰鼎大上小下若甑曰鬵|嶜:嶜喦|梣:木名|埐:地名又子心切|𣜣:掘也|鈂:+上同又直林切|灊:水名出巴郡|䤁:熟麴又餘針切
M1Q女心;䛘:䛘詉喉聲女心切三|䋻:䋻織也齊也或作紝|鵀:戴勝
f1Y巨金;琴:樂器神農作之本五弦周加文武二弦白虎通曰琴禁也以禁止淫邪正人心也又姓左傳琴張也巨金切二十二|㩒:急持|捦:+上同|擒:亦同|黔:黑而黃亦姓齊有黔熬又巨炎切|禽:二足而羽者曰禽又姓高士傳有禽慶|芩:黃芩藥名|𨙽:亭名|檎:林檎果名|㕋:說文云石地也|鵭:鶨鳥亦作鳹|䔷:草名根可緣竹器出玉篇|澿:水名|凜:寒狀又力甚切|庈:人名庈父|雂:鳥名又巨炎切|㪁:持也|㱽:禁也又竹甚切|黚:黃黑色又巨炎切|䅾:禾欲秀也|耹:音也|靲:靲鞻四夷樂也
e1Y去金;欽:敬也又姓何氏姓苑云吳人也去金切五|菳:草名似蒿|衾:被也|嶔:嶔崟|顉:曲頤又五感切
g1Y魚金;吟:歎也說文云呻吟也魚金切十|訡:+上同|䪩:+古文|唫:亦古吟字說文又巨錦切|崟:嶔崟|荶:水菜似蒜|碞:僭差|𩂢:霖雨又牛皆切|乑:眾立皃|𠪚:崟𠪚山崖狀也又口敢切
i1Y許金;歆:神食氣也許金切四|廞:爾雅曰興也亦陳車服也亦廞巇山險皃又許錦切|嬜:愛也又火甘切|㽎:火盛皃
d1Y居吟;金:金寶說文曰五色金也黃爲之長久薶不生衣百鍊不輕从革不違西方之行生於土亦州名周爲附庸國魏於安康縣置東梁州後周改金州又金鼓釋名曰金禁也爲進退之禁也又姓古天子金天氏之後也又漢複姓有金留氏出姓苑居吟切九|今:對古之稱說文云是時也|黅:黃色|衿:衣小帶也又其禁切|襟:袍襦前袂|䘳:+上同|禁:力所加也勝也又居蔭切|㦗:心㦗皃|𪑙:淺黃色說文云黃黑也又古咸切
h1Y於金;音:說文曰聲也生於心有節於外謂之音宮商角徵羽聲也絲竹金石匏土革木音也於金切八|陰:陰陽也說文作陰闇也水之南山之北也又姓出武威風俗通云管修自齊適楚爲陰大夫其後氏焉|隌:爾雅云闇也注謂隌然冥貌又烏感切|瘖:瘖瘂文子曰皋陶瘖|霠:雲覆日又姓出纂文|䜾:䜷豆|喑:極啼無聲又於含切|䤃:醉聲又於南切
V1Q所今;森:長木皃所今切十|參:參星亦姓世本云祝融之後又蒼含切|曑:+上同|蔘:人蔘藥也|薓:+古文|槮:樹長皃|襳:襳襹毛羽衣皃|𥥿〈𥥍〉:突也|穼:+上同|棽:木枝長也又丑林切
U1Q鋤（鉏）針;岑:山小而高又姓出南陽風俗通云古岑子國之後後漢有岑彭鋤針切九|涔:涔陽地名又管涔山名又蹄涔不容尺鯉蹄牛馬跡|㞥:入山深皃|梣:青皮木名又子心切|𣠟:+上同|𩅨:雨聲|𩻛:魚名|䅾:禾欲秀|笒:竹名
S1Q側吟;兂:說文曰首笄也側吟切四|簪:+上同|㻸:石似玉也|撍:速也
T1Q楚簪;嵾:嵾差不齊皃亦作參楚簪切六|參:+上同|梫:梫桂木花白也又音寢|𥤇:字書云禾長皃|駸:馬行疾皃|槮:木長皃
Y1Q充針;𧡪:說文云內視也充針切一
#覃
G2Q徒含;覃:及也延也又姓梁東寧州刺史覃元先徒含切二十|𨝸:𨝸城縣名|潭:水名出武陵郡鐔成縣東入鬱林又深水皃|曇:雲布|藫:水衣|橝:木名灰可染也|蟫:白魚蟲又音淫|譚:大也又姓漢有河南尹譚閎|𧽼:䟃𧽼走皃|燂:火爇|壜:甒屬|鐔:劒口又音尋|眈:視近而志遠又音耽|㽎:㽎㽎室深皃|𦗡:聒也|𩡝:馣𩡝香氣|𧂇:草名爾雅曰𧂇莐藩|蕁:+上同|䊤:糝也|㽑:長味又徒紞切
O2Q倉含;參:參承參覲也俗作叅倉含切五|驂:驂馬|䟃:䟃𧽼|傪:好皃|㜗:玉篇云婪㜗也
H2Q那含;南:火方亦果名臨海異物志云多南子大如指紫色味甘似梅又姓魯大夫南遺也又漢複姓九氏左傳齊有南史氏其後爲姓又魯有南宮敬叔晉國高士全隱於南鄉因以爲氏六國時有南公子著書言五行陰陽事莊子有南郭子綦又有南榮趎古有善暴背於南榮之者獻之於君其後爲氏又有南伯子蔡姓苑有南野氏又有南門氏那含切七|男:男子也又所封爵也環濟要略曰男任詔事受王命爲君|柟:木名又人詹切|楠:+俗|抩:併持也又他含切|䶲:龜有距也又如詹切|𤱣:+上同
h2Q烏含;諳:記也憶也烏含切十二|䳺:䳺鶉字林作䳺𨿡|媕:媕娿不決|庵:小草舍也|腤:煑魚肉也|菴:菴䕡草又菴羅果也|㞄:蹇跛之皃|馣:香也|嬜:貪愛|韽:聲小又於林切|盦:說文曰覆蓋也|喑:啼泣無聲
j2Q胡男;含:說文銜也胡男切二十二|涵:涵泳|䈄:實中竹名|筨:+上同|梒:梒桃禮亦作含|䤴:鎧別名孟子云矢人豈不仁於䤴人哉矢人唯恐不傷人䤴人唯恐傷人|函:容也禮云席閒函丈|顄:顄頤|𩔞:+上同|蜬:爾雅云蠃小者曰蜬|頷:說文曰面黃也又胡感切|𣹢:水澤多皃|鋡:受也|𤭙:似瓶有耳|𠥴:船沒|䶃:鼠屬又古南切|圅:銜也說文舌也|肣:+排囊柄也說文同上|䨡:久雨|𩄙:+上同|𢎘:說文曰嘾也艸木之華未發圅然象形又下感切|𠗴:寒皃
I2Q盧含;婪:貪也盧含切六|惏:+上同|燣:焦色|嵐:州名近太原因岢嵐山爲名有渥洼池出良馬亦山氣也|葻:草得風皃|啉:酒巡匝曰啉出酒律亦作𠵂
P2Q昨含;蠶:吐絲蟲俗作蚕非昨含切四|撏:取也|䣟:亭名|𨅔:上也
N2Q作含;簪:作含切又側岑切七|撍:盡也|篸:所以綴衣又作憾切|𥸢:𥸢𥯖|䐶:腤䐶|䍼:羊腌|鐕:無蓋釘也
F2Q他含;探:取也說文作𢲘遠取之也他含切三|撢:周禮有撢人|貪:貪婪也𥼶名曰貪探也探入他分也
E2Q丁含;耽:說文曰耳大垂也又耽樂也詩曰無與士耽或作躭丁含切九|湛:湛樂亦見詩|眈:視近而志遠也|酖:嗜酒|妉:妉樂|甔:大甖可受一石|媅:婬過說文樂也|𧡪:內視又大含切|𡖓:多也
e2Q口含;龕:塔也亦一曰龍皃又云塔下室口含切十|𢦟:殺也刺也|𩑟:醜皃|堪:任也勝也克也說文曰地突也又姓風俗通云八元仲堪之後|戡:勝也克也|𤯎〈𤯍〉:和也又紅談古三二切|嵁:嵁崿又五男切|𤬪:瓦器|撖:柱也|㪁:敧多也
i2Q火含;㟏:大谷也火含切八|𩈣:面紅|馠:小香|𣢺:含笑皃|谽:谽谺谷空|唅:唅呀|𡬖:不脫冠帶而寐也|𡪶:+上同
Q2Q蘇含;毿:長毛皃蘇含切三|蔘:蔘綏垂皃|犙:牛也
d2Q古南;弇:同也蓋覆也後漢有耿弇古南切又音掩五|䶃:鼠名|淦:水入船中又最也泥也汲也又甘暗切吉州有新淦縣水淦所出入湖或作汵|䌠:持意也又呼兼切|蜬:蠃小者又貝居水者肉如科斗但有頭尾
g2Q五含;䜙:不惠也又謔弄言五含切三|𡪁:寐中言語|嵁:嵁㟧又苦男切
#談
G3Q徒甘;談:談話又言論也戲調也又姓蜀錄云晉有征東將軍談巴徒甘切十一|郯:國名其後以國爲姓春秋時郯子入魯辨古官與孔子相遇姓苑云沛人|惔:憂也|錟:長矛|淡:水皃又徒覽徒濫二切|痰:胷上水病|澹:漢複姓孔子弟子有澹臺滅明又徒覽徒濫二切|倓:恬也安也靜也又徒濫徒坎二切|餤:進也詩曰亂是用餤又徒濫切|𥰨:刮馬篦也|㶣:小熱
d3Q古三;甘:說文作目美也又隴右州本月支國漢匈奴觻得王所居後魏爲張掖郡又改爲州取甘峻山名之界有弱水祁連山上有松栢五木美水茂草冬溫夏涼又有仙樹人行山中飢即食之輒飽不得持去平居時亦不可見也又姓武丁臣甘盤之後又漢複姓有甘莊甘士甘先三氏古三切七|柑:木名似橘|䇞:䇞竹|苷:苷草藥出洮州|泔:米汁|𤯎〈𤯍〉:和也|媣:媣媞也
E3Q都甘;擔:擔負釋名曰擔任也任力所勝也都甘切五|儋:說文何也亦姓左傳周有大夫儋翩|聸:說文曰垂耳也南方有聸耳之國|頕:頰緩|甔:小甖
Q3Q蘇甘;三:數名又漢複姓五氏三閭氏三閭大夫屈原之後也沛上計三烏群三烏大夫之後也三飯尞之後有三飯氏三州孝子之後有三州氏後單姓州蜀志有三丘務蘇甘切五|參:+上同又七南所今二切俗作叄|弎:+古文|𢁘:衣破襤𢁘|鬖:䰐鬖毛垂
I3Q魯甘;藍:染草又姓戰國策有中山大夫藍諸魯甘切十一|襤:襤褸|䰐:鬢髮疎皃|擥:㩜持|籃:籃籠|𩈵:𩈵𩈻長面|𪇖:𪇖鷜鳥名今俗呼郭公也|懢:懢貪皃|䆾:䆾䆱薄大|儖:儖儳形皃惡也|蘫:瓜葅
e3Q苦甘;坩:坩甒苦甘切一
F3Q他酣;舑:吐舌也他酣切九|聃:耳漫無輪又老氏名又姓左傳周大夫聃啓|𨈭:+俗|緂:色鮮|㘱:水衝岸壞|䔜:蔥別名|䆱:䆾䆱薄大|㴂:㴥㴂峻波也|𦸁:蘫𦸁瓜葅
P3Q昨甘;慙:愧也昨甘切五|慚:+上同|鏨:小鑿|䳻:鶚別名|㨻:說文暫也
j3Q胡甘;酣:酣飲應劭曰洽也張晏曰中酒曰酣又樂也胡甘切八|甝:白虎|䗣:桑蟲|魽:蛤也|𤯎〈𤯍〉:和也又口含古三二切|煔:火上行皃|炶:+上同|邯:江湘人言也又音寒
D3A武酣;姏:老女稱武酣切一
N3Q昨〈作〉三;𩈻:長面皃昨三切一
i3Q呼談;蚶:蚌屬爾雅曰魁陸本草云魁狀如海蛤員而厚外有文縱橫即今蚶也亦作魽呼談切五|𧵊:戲乞人物亦作歛|嬜:貪妄又一含切|歛:欲也|憨:癡也
#鹽
l4Q余廉;鹽:說文曰鹹也古者宿沙初作煑海爲鹽亦州近北鹽池因以名之又姓魯國先賢傳有北海相鹽津余廉切十五|塩:+俗|𣡶:木名|閻:里中門又姓出天水河南二望|壛:+壛榻也說文同上|阽:臨危|檐:屋檐說文曰檐㮰也|簷:+上同|櫩:亦同|𣡞:步𣡞長廊也|㶄:說文云海岱之閒謂相汙曰㶄|𪂈:𪂈離鳥自爲牝牡也|䦲:語林云大夫向䦲而立說文曰䦲謂之樀樀廟門也|㿕:病走|𤅸:進也
I4Q力鹽;廉:廉儉也釋名曰廉斂也自檢斂也亦姓趙有廉頗力鹽切二十|鐮:刀鐮也釋名曰鐮廉也薄其所刈似廉也|鎌:+上同|𩄡:久雨|㡘:㡙㡘帷也|簾:簾箔釋名曰簾廉也自障蔽爲廉恥也三秦記曰明光宮以金玉珠璣爲簾箔|薕:薑也說文蒹也|薟:白薟藥又音斂|蘞:+蔓草說文同上又音斂|匳:盛香器也又鏡匳也俗作奩|籢:+上同|𥖝:赤礪石|獫:犬長喙又力劒切又音險獫狁也|蠊:蜚蠊蟲名說文作螊海蟲也長寸而白可食|䆂:禾名|𨎷:車輞|𣀃:𣀃鼓鼓初打也|帘:青帘酒家望子|鬑:鬋也一曰長皃|覝:察也
A4I府廉;砭:以石刺病府廉切又方驗切二|𥑁〈𥐗〉:+古文
Q4Q息廉;銛:銛利也說文曰臿屬纂文曰鐵有距施竹頭以擲魚爲銛也息廉切十三|暹:日光進也|枮:木名|綅:白經黑緯|𦃌:+上同|韱:韱細又山韭也今通作韱凡從韱者倣此|襳:小襦|纖:細也微也|憸:利口|孅:銳也細也|䯹:髮也|彡:毛飾又所銜切|𢘁:疾利口也
O4Q七廉;籤:說文驗也一曰銳也貫也七廉切十|臉:臉𦞦也|䑎:+上同|鹼:水和鹽又工斬切|槧:削皮又才敢七豔二切|憸:㤿憸詖也㤿音猒|僉:咸也皆也|𠠃:𠠃切割也|㡨:幖㡨記出字林|譣:譣詖
X4Q職廉;詹:至也應劭漢官曰詹事秦官也又姓楚詞有詹尹俗作𦧕職廉切六|瞻:瞻視|占:視兆也亦姓陳大夫子占之後又章豔切|蟾:蟾蠩蝦蟆也張衡靈憲曰羿請不死之藥於西王母桓娥竊之奔月宮遂託身於月是爲蟾蠩抱朴子云蟾蠩壽三千歲者頭上有角頷下有丹書八字玄中記云蟾蠩頭生角者食之壽千歲也|噡:噡言語也|厃:說文云仰也一曰屋怊也秦謂之桷齊謂之厃本魚毀切
Z4Q視占;棎:果名似柰而酸視占切三|撏:撏取也|蟾:蟾光月彩又職廉切
a4Q失廉;苫:草覆屋又凶服者以爲覆席也又姓左傳魯季氏家臣苫夷失廉切三|痁:病又音店|𡝫:𡝫妗善笑皃又丑廉切
Y4Q處占;䪜:屏也處占切十一|㚲:㚲姼輕薄皃又尺涉切|幨:幨幃釋名曰牀前帷曰幨|襜:襜褕蔽膝|裧:+上同|𤎥:𤎥𤎥衣動皃|㾆:皮剝也|緂:衣色鮮|妗:妗𡝫善笑皃又許兼切|𢛈:𢛈懘音不和也禮記作怗|𢃔:㡙也
c4Q汝鹽;𩓾:說文曰頰須也汝鹽切十二|髯:+上同|蚺:大蛇|呥:噍皃|柟:梅也子如杏而醋|𧦦:多言|蛅:爾雅曰蟔蛅蟴郭璞云蛓屬也今青州人呼蛓爲蛅蟴|冉:說文云毛冉冉也亦作月|袡:衣緣|䶲:有距龜|㾆:皮剝又處占切|舑:舚舑長舌
M4Q女廉;黏:黏麴女廉切三|粘:+俗|䬯:南楚呼食麥粥
k4Y于廉;炎:熱也說文曰火光上也于廉切一
J4Q張廉;霑:霑濕也又濡也漬也張廉切三|沾:水名在上黨說文他兼切|𪏉:黃也
K4Q丑廉;覘:闚視也丑廉切又丑豔切二|𡝫:𡝫妗喜皃
h4Y央炎;淹:漬也滯也久留也敗也央炎切六|菴:菴䕡草又音諳|崦:崦嵫山下有虞泉日所入又於檢切|醃:鹽醃又葅也|䣍:邑名|閹:男無勢精閉者
e4Y丘廉;𢜩:𢜩㥓意不安也丘廉切二|𨦄:𨦄曲頭鑿
g4Y語廉;𪙊:齒差語廉切一
N4Q子廉;尖:銳也子廉切十三|殲:盡也滅也|瀸:漬也沒也洽也又泉水出微皃|㡨:拭也|𡄑:𡄑㖩不廉又將豔切㖩子俱切|漸:入也漬也又慈染切|虃:百足草|熸:火滅|㦰:刺也銳意也又持戈說文絕也|𩅼:小雨又霑也|鑯:說文曰鐵器也一曰鐫也|鋟:以爪刻櫃版也|𩃔:漬也或作𩃔又所咸切
P4Q昨鹽;潛:水伏流又藏也亦水名又姓姓苑云臨川人昨鹽切九|朁:於朁縣名屬杭州今作潛|鬵:甑也又才林切|𥮒:漂絮簀又音前|灊:水名在巴郡宕渠又古縣名在廬江又才林切|䁮:閉目內思|燂:周禮注云炙爛也|𤎢:+古文|螹:螹𧕮蟲名
f4Y巨淹;箝:鎖頭亦作鉗晉律曰鉗重二斤翹長一尺五寸又羌複姓有鉗耳氏說文籋也巨淹切十二|鉗:+上同說文曰以鐵有所劫束也|𢁮:絹𢁮|鉆:持鐵者說文又敕淹切鐵銸也一曰膏車鐵鉆|黚:淺黃黑色又古黚陽縣在武陵又巨今切|拑:脅持也|黔:黑黃色說文曰黎也秦謂民爲黔首謂黑色也周謂之黎民又音琴|羬:羊六尺爲羬|鳹:白喙鳥|雂:+上同|鍼:鍼虎人名又之林切|鈐:兵鈐以閉房神府以備非常又鉤鈐星名說文曰鈐𨬍大犁也
h4U一鹽;懕:安也一鹽切七|猒:飽也又於豔切|饜:+上同|嬮:和靜|㤿:㤿憸|䅧:䅧䅧苗美也|𨣻:含怒也又魚檢切
R4Q徐鹽;燅:說文曰湯中爚肉也徐鹽切九|𤍙:+說文同上|燖:-|爓:-|𦢨:+並同上|䕭:山菜|𢸧:摰摘物出字諟及聲類|㰊:木細葉也|𢅮:小巾
V4Q史炎;襳:襳褷毛羽衣史炎切一
L4Q直廉;㶣:字林云小熱也直廉切三|𪏂:埤蒼云赤黃色|誗:言利美也又人名字書無
f4U巨鹽;鍼:巨鹽切又音針一
#添
F5Q他兼;添:益也他兼切四|沾:說文曰水出壼關東入淇一曰沾益也|黇:黃色|舚:舚舑吐舌
E5Q丁兼;𩬑:𩬑鬑鬢髮疎薄皃丁兼切八|敁:敁敠稱量|佔:佔侸輕薄也|詀:轉語|㤴〈㡇〉:衣領又丁頰切|𧚊:+上同|𦕒:耳小垂|䀡:目垂又丁念切
G5Q徒兼;甜:甘也徒兼切五|恬:靖也|湉:水靖|菾:菜名|𦳇:藥名
I5Q勒兼;鬑:𩬑鬑勒兼切六|薕:薕蒹未秀荻草|熑:煣軔說文曰火煣車網絕也|溓:大水中絕小水出也說文曰薄水也一曰中絕小水|濂:薄也|燫:火不絕皃
e5Q苦兼;謙:敬也讓也苦兼切二|䌠:堅持意又呼廉切
d5Q古甜;兼:說文曰并也兼持二禾秉持一禾又姓衛公子兼之後古甜切七|縑:絹也說文曰并絲繒也|鶼:比翼鳥|𥻧:青稻白米|蒹:荻未秀|𦋰:絲網|鰜:比目魚
j5Q戶兼;嫌:說文曰不平於心一曰疑也戶兼切二|稴:稻不黏者又力兼切
H5Q奴兼;鮎:魚名奴兼切三|䬯:說文曰相謁食麥也|拈:指取物也
i5Q許兼;馦:香氣許兼切七|㾾:㾰㾾病也|䵌:赤黃色|㽐:香美|欦:貪慾也又笑也|䌠:堅持意又契兼切|妗:美也
#咸
j6Q胡讒;咸:皆也同也悉也亦姓姓苑云巫咸之後今東海有之胡讒切十一|鹹:不淡|醎:+俗|函:函谷關名又函書亦姓漢有豫章太守函熙又漢複姓漢末有黃門侍郎函治子覺又音含|𩤥:𩤥驩古縣名漢書只作咸|諴:和也|鰜:魚名|稴:不黏稻也|椷:杯也|㮭:+上同|輱:車聲
d6Q古咸;緘:減封古咸切七|䌠:慳悋文堅持意口閉也|瑊:美石次玉|玪:+上同|尲:尲尬行不正也|黬:釜底黑也|𪒹:說文曰雖晳而黑也古人名𪒹字晳
V6Q所咸;攕:女手皃所咸切十一|摻:+上同詩曰摻摻女手又所減切|檆:木名似松爾雅又作煔|杉:+上同|櫼:+上同說文音尖楔也|𩃔:雨皃說文曰微雨也或作𩆷又子廉切|𩁺:微雨|䀐:瞻視又所儳切|𨏪:車聲|𩌰:鞍𩌰垂皃|㺑:犬容頭進也
h6Q乙咸;𤟟:犬吠聲乙咸切又乙陷切三|淊:淊沒|黯:深黑也又乙減切
g6Q五咸;嵒:巖也又嶃喦山高皃亦地名五咸切十|䫡:面長皃又丘檻切|黬:釜底黑也又音緘|羬:山羊|𧇱:熊虎絕有力也|麙:+上同|𪙊:齒皃|碞:僣差又牛金切|㺂:羊有力也|𧬌:和也又戲言也
i6Q許咸;㰹:笑皃許咸切五|𧍧:似蛤出海中也|妗:喜皃又香兼切|𧮰:𧮰谺谷空皃|䩂:出頭皃
J6Q竹咸;詀:詀諵語聲竹咸切又尺涉切四|䩇:䩇䩂出頭皃|鵮:鳥啄物也又苦咸切|𪉜:鹹味
M6Q女咸;諵:詀諵也女咸切二|喃:+上同
U6Q士咸;讒:譖也士咸切又士銜切十三|獑:獑猢似猿而曰又士銜切|鏨:小鑿又才三切|饞:不廉|毚:狡兔|㺥:+上同|𪗂:鼻高皃|欃:檀木別名|攙:刺也又楚銜切|𪖎:鼠名又埤蒼云鼠皃|𢽝:鳥𢽝物也|儳:儖儳皃惡也又仕陷切|酁:宋地名
e6Q苦咸;鵮:鳥鵮物苦咸切五|𢽣:+上同|嵁:嵁巖不平正皃|厱:山崖空穴閒皃|𠔺:𠔺䫡長面
#銜
j7Q戶監;銜:說文曰馬勒口中从金从行銜行馬者戶監切二|甉:乾瓦屋也
U7Q鋤（鉏）銜;巉:險也鋤銜切八|嶃:嶃嵒山皃|劖:刺也說文曰斷也一曰剽也|艬:合木船|鑱:吳人云犁鐵說文銳也又士懺切|獑:獑猢又士咸切|毚:又士咸切|嚵:嚵氣說文曰小𠻜也一曰喙也又音懺
g7Q五銜;巖:峯也險也峻廊也五銜切三|礹:+上同|𡆑:呻吟
T7Q楚銜;攙:攙搶祅星爾雅作欃槍楚銜切又士咸切一
V7Q所銜;衫:衫衣所銜切八|纔:帛青色又音裁|髟:屋翼也又長髮皃|縿:絳帛說文曰旌旗游也|彡:毛長|芟:刈草|穇:稴穇穗不實見齊人要術|𩌰:又所咸切
d7Q古銜;監:領也察也說文云臨下也古銜切又古懺切五|礛:礛䃴青礪|𥌈:視也|鑑:鑑諸以取月中水又明也|㔋:細切
C7A白銜;𨂝:步渡水白銜切一
e7Q口銜;嵌:嵌巖山也口銜切一
#嚴
g8c語𩏩;嚴:嚴毅也威也敬也說文曰教令急也亦姓本姓莊避漢明帝諱改姓嚴語𩏩切二|䉷:射翳
i8c虛嚴;𩏩:胡被也虛嚴切五|杴:鍬屬古作𣞘或作㸝方言云青齊呼意所好爲杴|㿌:㿌𤻙物在喉也|𥟕:禾傷肥也|蘞:芋之辛味曰蘞
h8c於嚴;醃:鹽漬魚也於嚴切二|腌:+上同
e8c丘嚴;㪁:㪁欹不齊丘嚴切又丘广切二|厱:山側空處也
#凡
C9M符咸〖䒦〗;凡:常也皆也輕也非一也又姓周公子凡伯之後姓苑云晉陵人符咸切七|帆:船上幔也亦作颿又扶汎切|𠆩:輕也又孚劒切|𦨲:船舷|氾:國名又姓出燉煌濟北二望皇甫謐云本姓凡氏遭秦亂避地於氾水因改焉漢有氾勝之撰書言種植之事子輯爲燉煌太守子孫因家焉又音汎|颿:馬疾步|柉:木皮可以爲索
B9M匹凡;䒦:草浮水皃匹凡切二|𣢲:多智慧也丘凡切
#董
EAB多動;董:督也正也固也又姓飂叔安裔子董父實甚好龍帝舜嘉焉賜姓曰董出隴西濟陰二望多動切七|蝀:螮蝀虹也又音東|箽:亦姓又竹器也|𢤦:懵𢤦心亂|蕫:薡蕫草似蒲而細又藕根|䵔:攏䵔不上|𧄓:𧄓𧄓鼓鳴也
DAB莫孔;蠓:列子曰蠛蠓生朽壤之上因雨而生覩陽而死莊子謂之醯雞莫孔切七|𤾬:物上白醭|鸏:水鳥又音蒙|濛:濛澒大水又莫紅切|䑃:大皃|曚:暡曚日未明也|懵:心亂皃
eAB康董;孔:孔穴也又空也甚也亦姓殷湯之後本自帝嚳次妃簡狄吞乙卵生契賜姓子氏至成湯以其祖吞乙卵而生故名履字太天乙後代以子加乙始爲孔氏至宋孔父嘉遭華父督之難其子奔魯故孔子生於魯康董切二|倥:倥傯事多
QAB先孔;㪌:搏擊先孔切三|䉥:箸桶|𣞷:+上同又蘇公切
FAB他孔;侗:直也一曰長大他孔切四|桶:木桶又音動|曈:曈曨欲曙又音童聾|捅:捅進前也
NAB作孔;總:聚束也合也皆也眾也作孔切十五|摠:+上同|𢝰:+俗|嵸:巃嵸山皃|㢔:眾立|𩮰:𩮰角本亦作總|蓯:菶蓯草皃|鬷:爾雅云軌鬷一名素華|猣:犬生三子|翪:鳥飛竦翅上下也所謂鵲鶪醜其飛也翪|䁓:方言云南人竊視|熜:熅也說文曰然麻蒸也又青公切|𢊕:屋階中會又且公切|𨍈:關西呼輪曰𨍈|傯:倥傯
jAB胡孔;澒:說文曰丹沙所化爲水銀也又濛澒大水胡孔切五|鴻:鴻濛又音紅|𧋔:𧋔蟲甲類|𠳃:鳴聲𠳃𠳃也|汞:水銀滓
hAB烏孔;蓊:蓊鬱烏孔切九|滃:大水皃|暡:氣盛皃|郺:郺𨑊多皃又音邕濃|勜:勜劜屈強皃劜音軋|䈵:竹盛又音翁|䐥:䐥臭皃出字林|塕:塕埲塵起|𤌏:𤌏然煙氣
HAB奴動;𨑊:奴動切一
AAB邊孔;琫:佩刀飾也邊孔切四|菶:草盛|𦂌:小皃皮屨又巴講切|俸:屏俸又扶用切
IAB力董;曨:曈曨力董切九|襱:袴也又直隴切|巃:巃嵸|竉:孔竉|籠:竹器又龍聾二音|攏:攏略又拗攏籌也出酒律|𢤱:𢤱悷不調|儱:儱侗未成器也|龓:乘馬又牽也說文兼有也
iAB呼孔;嗊:羅嗊歌曲出告幼童文呼孔切二|𢦅:𢦅𢦅心神恍忽皃
GAB徒摠;動:躁也出也作也搖也徒摠切九|𨔝:+古文|酮:酒壞又音同|姛:項直皃|眮:瞋目|詷:訂詷訂音挺|桶:木器又他孔切|挏:推引也漢有挏馬官作酒又音同|硐:安硐鏓硐見馬融長笛賦
CAB蒲蠓;菶:蒲蠓切草盛皃又方孔切三|唪:大笑也|埲:塕埲塵起
#腫
XDB之隴;腫:疾也說文癰也釋名曰腫鍾也寒熱氣鍾聚也之隴切六|種:種類也又之用切|踵:足後又繼也趾也頻也說文追也一曰往來皃|歱:說文跟也|㣫:相跡也|喠:喠𠹍欲吐
KDB丑隴;寵:寵愛也丑隴切三|𧼙:小皃行皃|埫:埫塎不安
IDB力踵;隴:說文云天水大坂也亦州漢汧縣後魏置東秦州又改爲隴州因山名之力踵切三|壠:說文曰丘壠也方言曰秦晉之閒家謂之壠亦作壟書傳曰畝壟也|㙙:塗也
hDN於隴;擁:手擁說文作𢹬抱也又擁劒蟲形似蟹崔豹古今注云一名執火其螯赤故謂之執火於隴切三|𢶜:+上同|壅:壅堨亦塞也障也又音邕
cDB而隴;宂:宂散也亦官名續漢志曰先臘一日大儺逐疫鬼宂從僕射將之逐鬼于禁中俗作冗而隴切十二|𡦼:+上同|穁:稻穁䅌|䢇:不肖也一曰傝䢇劣也或作㩉茸又作㲩𣯏|𣭲:鳥細毛也|氄:+上同|軵:推車或作搑|𤘺:水牛|𪕎:𪕎鼠|𢫨:拒也亦作軵|𨍷:輕也|搑:推擣皃也又而容切
LDB直隴;重:多也厚也善也慎也直隴切又直龍直用二切四|𢝆:遟也|襱:袴也又來公力董二切又作𧙥|鮦:魚名又直柳切
JDB知隴;冢:大也周禮天官冢宰說文曰高墳也釋名曰冢腫也象山頂之高腫起知隴切二|塚:+俗
CDN扶隴;奉:與也獻也祿也說文承也扶隴切二|唪:口高皃出埤蒼
BDN敷奉;捧:兩手承也敷奉切一
lDB余隴;勇:猛也說文作勈气也余隴切十五|恿:+古文|涌:涌泉說文曰滕也一曰涌水在楚國|甬:草花欲發皃亦甬道周禮云舞上謂之甬甬鐘柄也|踊:跳也又踊刖者以之接足晏子曰踊貴屨賤|慂:方言云慫慂勸也|𧻹:說文曰喪躃𧻹也經典作踊同|塎:埫塎不安|悀:心喜也又出也|埇:地名在淮泗|溶:水皃又音容|蛹:蠶化爲之|傛:說文曰不安也又音容|俑:木人送葬設關而能跳踊故名之出埤蒼|𧗴:巷道出蒼頡篇
eDN丘隴;恐:懼也丘隴切又丘用切三|𢖶:+古文|𦶐:䕞𦿆也
ZDB時宂;尰:足腫病亦作𡰒時宂切三|𤺄:+上同出說文|𢡹:自要𢡹出聲譜
dDN居悚;拱:手抱也又斂手也居悚切十八|拲:兩手共械周禮曰上罪梏拲而桎|䂬:水邊大石|鞏:以皮束物又縣名在河南亦姓左傳晉大夫鞏朔|蛬:蟋蟀又巨容切|孒:孑孒井中小蟲|珙:璧也|廾:說文曰竦手也篆文作𠬞弄具奐丞字並从此篆同而隷異也|𢪒:說文曰楊雄說廾从兩手也|㤨:戰慄也又戶工切|𢸁:姓也|㼦:缻也|㧬:抱持說文𢹬也|䡗:輞也|䱋:鯤魚子也|巩:抱也說文作㧬恐鞏類並从此|栱:爾雅云杙大者謂之栱|輁:輁軸所以支棺
QDB息拱;悚:怖也息拱切十|竦:敬也國語云竦善抑惡|慫:驚也|聳:高也說文曰生而聾曰聳|𦄼:絆前兩足|㩳:執也|駷:何休云馬搖銜走也|愯:懼也亦作𢥠|傱:傱傱走意又先項切|䙕:禪衣
iDN許拱;洶:洶溶水皃許拱切三|詾:詾嚇也又音凶|兇:恐懼說文曰擾恐也左傳曰曹人兇懼又音凶
ADN方勇;覂:覆也或作𢇫又作泛此覂駕之馬非良者說文曰反覆也方勇切二|𢇫:+上同
ECB都𪁪;湩:都𪁪切濁多也此是冬字上聲一
DCB莫湩;𪁪:莫湩切𪁪鴟鳥又莫項切二|䏵:豐大
fDN渠隴;䅃:穫也渠隴切又渠恭切一
YDB充隴;𨿿:小鳥飛也充隴切二|喠:氣急之皃
ODB職〘且〙勇;幒:說文曰㡓也職勇切二|𢃓:+上同又且勇切
NDB子冢;䙕:子冢切襌衣又息拱切一
#講
dEB古項;講:告也謀也論也說文曰和解也古項切四|港:水派|傋:𠈵傋不媚皃又虛項切|耩:耕也
CEB步項;㭋:杖也打也步項切八|棒:+上同|棓:+上同魏志云曹操爲北部尉門左右縣五色棓各十枚|玤:周邑地名又珠次玉|𢗒:𢗒慃很戾|蚌:蛤也|蜯:+上同|䎧:䎧䥯器出埤蒼
hEB烏項;慃:𢗒慃很戾烏項切一
DEB武項;𠈵:𠈵傋武項切二|𪁪:𪁪鴟鳥
jEB胡講;項:頸項說文曰頭後也釋名曰項确也堅硧受枕之處又姓本姬姓國公羊曰爲齊桓公所滅子孫以國爲氏項燕爲楚將生梁梁兄子籍號霸王胡講切二|缿:說文云受錢器古以瓦今以竹又大口切
AEB巴講;𦂌:小兒皮屨巴講切又補孔切一
iEB虛慃;傋:虛慃切𠈵傋二|𢞡:慃𢞡
#紙
XFR諸氏;紙:釋名曰紙砥也平滑如砥石也後漢蔡倫以魚網木皮爲紙又姓後魏書官氏志云渴侯氏後改爲紙氏諸氏切十六|帋:+上同|只:語辤|坻:隴坂也又直尼當禮二切|軹:縣名在河內又字書云車輪之穿爲道絏子嬰於軹途是也|枳:木名周禮曰橘踰淮北而爲枳又居帋切|咫:咫尺賈逵云八寸曰咫|扺:扺掌說文云側手擊也|𣲵:水名出枸扶山|砥:平也直也均也礪石也書傳云砥細於礪皆磨石也|坻〈坁〉:說文云坁著也|汦:著止|抧:開也|恀:怙也又音是|䅩:曲枝果也|䳅:䳅䳜鳥如烏赤足可以禦火見山海經
ZFR承紙;是:是非也說文曰直也又姓吳志云是儀本姓氏孔融嘲之曰氏字民無上乃改爲是焉又虜複姓四氏西魏有開府是云寶後魏書又有是連是婁是賁三氏承紙切十|氏:氏族又支精二音|媞:江淮呼母也又音啼|諟:理也正也諦也審也|恀:爾雅曰恀怙恃也一云恃事曰恀|徥:行皃又池爾切|𤜣:𤜣狼|褆:衣服端正|姼:方言云南楚人謂婦妣曰母姼也|䟗:䟗尌也謂立也積聚也
DFJ文彼;靡:無也偃也又靡曼美色也說文曰披靡也文彼切七|𨇻:行皃|𪎓:𪎓𪎓猶遟遟也|骳:骳屈曲也|𦗕:乘輿金耳又美爲切|𡬍:熟寐也又莫禮切|蘼:薔蘼藥名又亡爲切
AFJ甫委;彼:對此之稱甫委切五|㗗:相分解也|柀:木名爾雅云柀煔|佊:埤蒼云佊邪也|𠐌:停𠐌
CFJ皮彼;被:寢衣也又姓呂氏春秋有大夫被瞻皮彼切又皮義切二|罷:遣有罪又平陂薄解二切
iFp許委;毀:壞也破也缺也虧也許委切十|燬:火盛|檓:爾雅云檓大椒|毇:說文曰米一斛舂爲八斗|𥶵:+上同|𠷏:又於詭切義見下文|譭:謗也譖也|㩓:手擊傷也|烜:周禮有司烜氏以陽燧取火於日以鑒取水於月|𡢕:說文曰惡也一曰人皃
hFp於詭;委:委曲也亦委積又屬也棄也隨也任也又姓漢有太原太守委進出風俗通於詭切五|骫:骨曲又姓出纂文|𠷏:說文曰鷙鳥食已吐其皮毛如丸又許委切|蜲:黍負爾雅云蛜威委黍字或從虫|䍴:羊相䍴𦎸
eFp去委;跪:拜也去委切又渠委切二|𣄲:刖一足
dFp過委;詭:詐也又橫財物爲詭遇也過委切十九|垝:垝垣毁垣也又作陒|陒:+上同|䣀:陸䣀山名出山海經|攱:枕也|䤥:戾鋸齒也說文曰臿屬一曰瑩鐵也|觤:羊角不齊|恑:變也悔也|蛫:蟹也|祪:毁廟之祖|庪:爾雅云祭山曰庪縣|䃽:-|庋:+並上同|洈:水名出南郡東洈山至華容縣入江也|蟡:長八尺一首二身似蛇以名呼之可取魚鼈|𪀗:子規玉篇云布榖也|姽:宋玉神女賦曰既姽嫿於幽靜說文曰閑體行姽姽也|桅:短矛或作𥍨說文曰桅黃木可染|佹:戾也
QFh息委;髓:說文作𩪦骨中脂也息委切五|嶲:越嶲郡|靃:靃靡草木弱皃|䭉:餹䬾方言云餅|𣿂:滑也
IFh力委;絫:說文曰增也十黍之重也力委切六|累:+上同又良僞切|樏:似盤中有隔也又音縲|䉂:法者䉂可以網人心|厽:說文曰絫坺土爲牆壁|垒:說文曰垒墼也
fFZ渠綺;技:藝也說文巧也渠綺切六|妓:女樂|徛:立也|伎:侶也|錡:釜也又魚綺切|䗁:蟬也
hFZ於綺;倚:依倚也又姓楚左史倚相於綺切五|猗:猗狔猶窈窕也又於羈切|椅:椅柅又於宜切|旖:旖旎旌旗從風皃|輢:車輢
dFZ居綺;掎:牽一脚說文云偏引也居綺切七|剞:剞劂曲刀|庋:食閣又音詭|㞆:一足又作踦|踦:公羊傳曰相與踦閭而語閉一扇開一扇一人在內一人在外|㱦:弃也又丘知九奇二切|攲:持去也又居宜切
eFZ墟彼;綺:文繒又姓漢四皓有綺里季墟彼切七|婍:皃好|碕:碕礒石皃又起宜巨支二切|䞚:行皃|㥓:𢜩㥓又去奇切儉意也|觭:牛角又丘奇切|㾨:痤也喪也又於蟹切
gFZ魚倚;螘:爾雅曰蚍蜉大螘小者螘魚倚切十二|蟻:+上同|蛾:+上同見禮|錡:三足釜一曰蘭錡兵藏又姓武王分殷人六族有錡氏後漢有錡嵩|礒:碕礒|齮:齧也|艤:整舟向岸|檥:+上同說文魚羈切榦也|㠖:岌㠖山高皃|轙:說文曰車衡載轡者|羛:羛陽鄉名在魏郡|䰙:釜也亦作鈘說文曰三足鍑也一曰滫米器也
kFp韋委;蔿:草也又姓左傳晉大夫蔿伯韋委切九|鄬:地名|儰:不安也|䧦:地名|蘤:花也榮也|𤺉:口咼|䦱:闢也國語曰䦱門與之言又姓|薳:草又姓左傳楚有薳氏代爲大夫|寪:說文云屋皃
NFh即委;觜:喙也即委切二|㭰:+上同說文識也一曰藏也
cFh如累;蘂:花外曰萼花內曰蘂如累切四|蕊:草木叢生皃|甤:說文曰草木實甤甤也又人隹切|繠:茸也垂也又佩垂皃
OFR雌氏;此:止也雌氏切九|跐:蹈也又阻買切|佌:小舞皃|玼:玉色鮮又千禮切|泚:水清又千禮切|𩢑:馬名|𠈈:小皃|𧺼:淺渡也|𡘌:直大也說文火介切瞋大聲也
LFR池爾;豸:蟲豸爾雅云有足曰蟲無足曰豸說文云獸長𦟝行豸豸然欲有所伺殺形池爾切十二|褫:奪衣易曰以訟受服終朝三褫之|陊:山崩也說文大可切落也|䊓:黏也|踶:踶跂用心力皃莊子曰踶跂爲義|傂:佌傂參差皃|杝:析薪又敕氏切|阤:落也說文云小崩也|䚦:角端不正說文敕豕切角傾也|廌:解廌又宅買切又作𧣭|褆:好衣|徥:行皃朝鮮語也
QFR斯氏;徙:移也斯氏切五|壐:說文曰王者印也所以主土从土爾聲|璽:+籀文|𠈈:𠈈小皃詩云𠈈𠈈彼有屋本亦作佌佌又音此|𢇌:小皃又千禮切
lFR移爾;酏:酏酒移爾切九|迆:邐迆連接|匜:杯匜有柄可以注水又音移|衪:衣中袖也|肔:引腸莊子云萇弘肔崔譔注云肔裂也又敕紙切|崺:峛崺沙丘狀峛音邐|扡:加也又離也又弋支切或作拸|㥴:不憂事也又弋支切|孈:多態
IFR力紙;邐:邐迆力紙切三|峛:峛崺|㸚:㸚尒布明白象形也
VFR所綺;躧:躧步也又作蹝說文曰舞履也所綺切十|𩎉:+上同|灑:灑埽又所買切|纚:韜髮者又颯纚長紳皃|縰:+上同|釃:分也見漢書溝洫志說文曰下酒也一曰醇也|𩌦:鞮屬|屣:履不躡跟|矖:視也|簁:籮也說文曰簁箄竹器也
AFF并弭;𢔌:使也從也職也并弭切十|俾:+上同說文曰益也一曰俾門侍人|鞞:刀鞞又蒲迷補茗二切|箄:竹器又卑篦二音|𪐄:黍屬又蒲賣切|髀:股也又步米切|崥:山足|𦸣:爾雅曰𦸣鼠莞郭璞曰亦莞屬纖細似龍須可以爲席|𠬈:客|𢳋:扶持
cFR兒氏;爾:汝也說文作爾云麗爾猶靡麗也兒氏切四|尒:義與爾同說文曰詞之必然也又虜姓二氏尒朱氏本北秀容人也居尒朱川因以爲氏後魏書官氏志尒綿氏後改爲綿氏也|邇:近也|𨒛:+上同
DFF綿婢;渳:水皃說文㱃也綿婢切十一|弭:弓末又息也亦無緣弓也|濔:水流皃|瀰:詩曰河水瀰瀰水盛皃也|羋:羊鳴一曰楚姓|敉:撫也愛也安也|侎:+上同|葞:爾雅云葞春草本草云芒草也|䖹:爾雅注云今米榖中蠹小黑蟲是也|䦵〈𩰞〉:力褊又乃禮切|㥝:止也
CFF便俾;婢:女之下也便俾切二|庳:下也或作埤又音卑說文曰中伏舍也一曰屋庳
YFR尺氏;侈:奢也泰也大也尺氏切十五|姼:㚲姼輕薄皃又美也㚲吐涉切|𡚼:+上同|鉹:甑也|誃:說文曰離別也|㢋:廣也國語曰俠溝而㢋我|㢁:+上同|垑:恃土地也|懘:又昌厲切|㶴:盛也|袳:衣張亦作袲又宋地名|袲:+上同|𧰲:豕也|恀:恃也又音帋|哆:張口又丑加昌者二切
aFR施是;弛:釋也說文云弓解也施是切三|豕:豬也|阤:壞也又音豸
NFR將此;紫:閒色也又姓出何氏姓苑將此切九|訿:訿毁|訾:+上同|啙:窳也又子西切|𣸆:水名在長沙|跐:行皃|茈:茈薑又茈草也|呰:口毁說文苛也|㧗:捽也又子禮側買二切
XFh之累;捶:擊也之累切五|箠:策也|𦓝:小巵出說文|䮔:馬小皃又子垂切|沝:二水又音資
TFh初委;揣:度也試也量也除也初委切又丁果切二|㪜:試也
RFh隨婢;𤢍:牸豚或作𤡪隨婢切一
bFR神帋（紙）;舓:以舌取物神帋切四|𦧇:+上同|舐:+俗|𤜣:獸名似狐出則有兵
SFR側氏;㧗:拳加人也側氏切又音紫二|跐:蹈也又音紫
BFJ匹靡;㱟:披析匹靡切三|紴:水波錦文又補柯切|披:開也又偏羈切
BFF匹婢;諀:諀訾惡言匹婢切六|庀:具也|疕:瘡上甲亦頭瘍又卑履切|仳:仳離別之意|䚹:具也|吡:訾也出莊子
lFh羊捶;䓈:雞頭也北燕謂之䓈羊捶切六|䔺:草木葉初出皃|芛:爾雅云蕍芛葟華榮|撱:撱棄又撞也|䝐:小豶亦作𧱞|𤼒:瘡裂
PFh才捶;惢:疑也才捶切一
eFl丘弭;跬:舉一足丘弭切四|䞨:+上同|頍:弁皃又舉頭皃|䠑:䠑踽開足之皃
MFR女氏;狔:猗狔從風皃女氏切三|旎:旖旎|抳〈柅〉:椅柅
gFp魚毀;硊:磈硊石皃魚毀切四|頠:閑習容止|姽:好皃又過委切|𪀗:布榖鳥
fFp渠委;跪:䠆跪亦作𧻜渠委切又去委切一
KFR敕豸;褫:敕豸切衣絮偏也又池豸二音一
JFR陟侈;㨖:指也說文刺也陟侈切二|𧛢:䘢𧛢
iFZ興倚;𪖥:去涕也興倚切一
eFV丘弭;企:企望也丘弭切又去智切二|跂:踶跂山海經云有跂踵國人行腳跟不著地如人之跂足也又去智巨支二切
ZFh時髓;菙:周禮有菙氏燋焌用荊菙之類時髓切二|㥨:㜇不悅也
dFV居帋（紙）;枳:木名似橘居帋切又諸氏切一
#旨
XGR職雉;旨:說文云美也从匕甘又志也亦作𣅀見經典職雉切八|指:手指也又示也斥也|恉:意也|祁:地名|䛗:訐發人之惡|厎:平也致也說文云柔石也|砥:+砥礪也說文同上|茋:茋蒻小苹
ZGR承矢;視:比也瞻也效也承矢切三|眡:-|眎:+並古文
DGJ無鄙;美:好色說文曰甘也从羊从大羊在六畜主給膳也美与善同意無鄙切五|媺:+上同周禮地官云一曰媺宮室|𤛎:獸似牛|渼:渼陂在京兆鄠縣|媄:字㨾云顏色姝好也
AGJ方美;鄙:陋也又邊鄙也方美切四|啚:說文嗇也|娝:姓出何承天纂文|痞:病也又音否
RGR徐姊;兕:爾雅曰兕似牛郭璞曰一角青色重千斤徐姊切七|𧰽:+上同|𠒅:+古文|𠒃:+俗|羠:犍羊又以脂切|薙:燒草又直履他計二切|䒨:蒿也
dGZ居履;几:案屬周禮司几筵掌五几凡朝覲大饗射封國命諸侯設左右玉几祀先王亦如之諸侯祭祀右彫几筵國賓于牖前左彤几甸役右漆几喪事右素几吉事變几凶事仍几或作机居履切九|𪊨:爾雅云𪊨大麕旄毛狗足|麂:+上同|㞦:女㞦山名弱水所出|机:說文曰木也山海經曰族蔨之山多松栢机桓|䢳:地名|𤜝:獸名如兔喙蛇尾是則有蝗災|㞛:赤𩍆㞛也|䂹:石墮聲也
NGR將几;姊:爾雅曰男子謂女子先生爲姊將几切二|秭:千億也亦秭歸縣在歸州袁山松云屈原此縣人被放姊來因名其地姊與秭同音風俗通云千生万万生億億生兆兆生京京生秭秭生垓垓生壤壤生溝溝生澗澗生正正生載載地不能載也
AGF卑履;匕:匕匙通俗文曰匕首劒屬其頭類匕短而便用故曰匕首卑履切十|妣:爾雅曰父曰考母曰妣又甫至切|秕:穅秕|比:校也並也爾雅曰北方有比肩民焉迭食而迭望蓋半體人也又毗鼻邲三音|䃾:以豚祀司命也|沘:水名出廬江灊縣入芍陂今謂之渒淠水也|枇:禮記注云所以載牲體|朼:+上同|疕:頭瘍|髀:股外又旁禮切
dGp居洧;軌:法也車跡也說文曰車轍也居洧切十二|簋:簠簋祭器受斗二升內圓外方曰簋|朹:+古文|晷:日影也又規也|厬:厬泉或作𣷾爾雅云水醮曰厬謂水醮盡也|𣷾:+上同|宄:內盜也|匭:匣也唐垂拱元年置匭於朝令上表者投之有延恩通玄招諫申冤等四匭也|𠥗:古文說文云匭𠥗皆古文簋字|頯:小頭又巨追切|氿:水涯枯土爾雅曰氿泉穴出穴出仄出也|𧗝:𧗝跡
kGp榮美;洧:水名在鄭榮美切四|鮪:魚名|痏:瘡痏|䵋:黃色
aGR式視;矢:陳也誓也正也直也說文曰弓弩矢也古者夷牟初作矢式視切四|𠂕:+又作𥬘並俗|𦳊:說文曰糞也本亦作矢俗作屎|屎:俗本許伊切
LGR直几;雉:爾雅曰雉絕有力奮謂最健鬬也又陳也度也王肅云城高一丈曰堵三堵曰雉直几切三|滍:水名在魯陽|薙:芟草又辛薙辛夷別名又音替
QGR息姊;死:說文曰澌也人所離也息姊切一
CGF扶履;牝:扶履切又毗忍切一
IGR力几;履:踐也祿也幸也福也字書云草曰屝麻曰屨皮曰履黃帝臣於則所造又姓出姓苑力几切一
aGh式軌;水:說文曰準也北方之行也釋名曰水準也準平物也式軌切一
IGh力軌;壘:說文曰軍壁也又重壘亦姓後趙錄有壘澄本姓裴氏力軌切十四|蜼:似猴仰鼻而尾長尾端有歧說文惟季切又音柚|猚:+上同|櫐:藤爾雅曰諸慮山櫐|蘽:+上同|㶟:水出鴈門|𡻭:𡻭㠑山皃|轠:轠轤車屬|鸓:飛生鳥名飛且乳一曰鼯鼠毛紫赤色似蝙蝠而長|藟:葛藟葉似艾或作虆|誄:銘誄誄壘也壘述前人之功德周禮曰小史掌卿大夫之喪讀誄也說文曰誄諡也|耒:田器又盧對切|讄:禱也|𤢹:飛𤢹獸
fGl求癸;揆:度也求癸切五|楑:木名又音葵|𢜽:悸也又巨隹切|嫢:細也又聚惟切|湀:泉出也說文曰湀辟深水處也
OGh千水;趡:走也又魯地名千水切三|踓:蹵|𨿐:細頸
MGR女履;柅:絡絲柎易曰繫于金柅女履切又音尼一
dGl居誄;癸:辰名爾雅太歲在癸曰昭陽古作癸又姓姓苑云出齊癸公後居誄切二|湀:通流
CGJ符鄙;否:塞也符鄙切又方久切八|痞:腹內結痛|圯〈圮〉:岸毀又覆也|仳:離也又芳比切|殍:草木枯落也又音孚|𢁦:㡜裂|䤏:覆也或作𡺮|𢻹:方言云器破而未離南楚之閒謂之𢻹又匹支芳鄙二切
PGh徂累〖壘〗;㠑:𡻭㠑山皃徂累切一
BGJ匹鄙;嚭:大也匹鄙切五|秠:一稃二米又孚悲切|疕:頭瘍|𡺮:崩也|𢻹:又匹支符鄙二切
cGh如壘;蕊:草木實節生如壘切三|甤:說文曰草木實甤甤也|繠:垂也
lGh以水;唯:諾也以水切又音惟八|蓶:草似馬韭而黃可食|䲊:蟹子又他果切|壝:埒也又音遺|瀢:魚盛皃|孈:愚戇多態又尤卦切|撱:棄也|踓:走也又千水切
hGZ於几;㰻:㰻㰳驢鳴於几切一
NGh遵誄;濢:汁漬也遵誄切四|噿:鳥噿|嗺〈嶉〉:山狀|臎:肥皃
JGR豬几;黹:鍼縷所紩周禮祭社稷五祀則用黹冕也豬几切四|𢾫:剌|夂:後至也|㨖:挃也
KGR楮几;𡳭:移蠶就寬楮几切一
SHR止姊;𧿲:止姊切一
iGl火癸;䁤:恚視火癸切又火季切一
fGp暨軌;䣀:山名暨軌切一
fGZ暨几;跽:䠆跽暨几切一
eGp丘軌;巋:巋然高峻皃又小山而眾曰巋丘軌切二|蘬:蘢古大者曰蘬
#止
XHR諸市;止:停也足也禮也息也待也留也諸市切十|畤:說文云天地五帝所基止祭地右扶風有五畤又時止切|沚:釋名曰沚止也小可以止息其上說文曰小渚曰沚|洔:+上同說文曰水暫益且止未減也|茝:香草字林云蘪蕪別名又昌待切|趾:足也|址:基址|阯:交阯郡劉欣期交州記云交阯之人出南定縣足骨無節身有毛臥者更扶始得起山海經云交脛國爲人交脛郭璞曰腳脛曲戾相交所以謂雕題交阯也|芷:白芷藥名又芷陽縣名|厎:定也又厎柱也
ZHR時止;市:說文云買賣所之也周禮曰司市掌市之治教政刑量度禁令大市日側而市百族爲主朝市朝時而市商賈爲主夕市夕時而市販夫販婦爲主古史考曰神農作市世本曰祝融作市時止切三|恃:依也賴也|畤:又諸市切
JHR陟里;徵:五音配夏亦作徵見經典省陟里切又竹凌切三|𧩼:𧩼言也出方言|㨖:指也
iHd虛里;喜:喜樂又聞喜縣在絳州漢武帝幸左邑聞南越破遂改爲聞喜縣禮記曰人喜則斯陶陶斯咏虛里切又香忌切三|憙:悅也又許忌切|蟢:蟢子蟲名
dHd居理;紀:極也會也事也理也識也亦經紀又十二年曰紀又姓出丹陽居理切四|己:身己爾雅曰太歲在己曰屠維|妀:說文云女字也|𠮯:說也
lHR羊己;以:用也與也爲也古作㠯羊己切七|㠯:+古文|已:止也此也甚也訖也又音似|苡:薏苡蓮實也又芣苡馬蕮也又名車前亦名當道好生道閒故曰當道江東呼爲蝦蟆衣山東謂之牛舌|苢:+上同|佁:癡也說文讀若騃又夷在切|攺:大堅說文曰㱾攺大剛卯以逐鬼鬽也
RHR詳里;似:嗣也類也象也詳里切十五|佀:+上同|祀:年也又祭祀|𥘰:-|禩:+並上同|姒:夏姓一曰娣姒長婦曰姒幼婦曰娣|巳:辰名爾雅曰太歲在巳曰大荒落|耜:耒耜世本曰倕作耜古史考曰神農作耜|𦓨:+上同|汜:水名在河南成皋縣說文曰水別復入水也一曰汜窮瀆也詩曰江有汜|洍:說文曰水也一曰詩曰江有洍|泤:+上同|攺:又羊己切|鈶:鋌鈶|𪊍:鹿一歲曰𪋇二歲曰𪊍
VHR疎士;史:史籍說文作㕜記事者也亦姓周卿史佚之後出建康又漢複姓五氏世本衛有史朝朱駒漢書藝文志有青史氏著書又有新豐令王史音吳有東萊太守太史慈晉有東萊侯史光疎士切四|使:役也令也又疎事切|駛:疾也又音去聲|𩰢:香之美者
cHR而止;耳:辝也說文云主聽也而止切五|洱:水名出罷谷山又而志切|駬:騄駬周穆王馬名|䋙:䋙䋙轡盛皃|𪕔:鼠名
IHR良士;里:周禮五家爲鄰五鄰爲里風俗通云五家爲軌十軌爲里里者止也五十家共居止也又姓左傳晉大夫里克又漢複姓有相里氏良士切十|裏:中裏說文曰衣內也|鯉:魚名|悝:憂也詩云悠悠我悝又口回切|李:果名亦行李又姓風俗通云李伯陽之後出隴西趙郡頓丘渤海中山襄城江夏梓潼范陽廣漢梁國南陽十二望|㾖:病也|理:料理義理又正也文也說文曰治玉也亦姓皋陶爲大理因官氏焉殷有理徵|娌:妯娌|俚:賴也聊也又南人蠻屬也|𨛋:亭名在西鄂一曰邑名
QHR胥里;枲:麻有子曰枲無子曰苴也胥里切七|萆〈𦱓〉:胡𦱓|𤟧:不安皃又作偲|䈚:竹萌也又音待|葸:質愨皃又畏懼也|諰:言且思之|𠪙:說文曰石利也
aHR詩止;始:初也詩止切一
LHR直里;歭:說文䠧也歭䠧不前也直里切九|跱:+上同|峙:具也又峻峙|痔:病也|㣥〈偫〉:待也儲也具也又看所望而往|洔:水中高土又音止|畤:儲|秲:稻名秲𥣬|庤:詩曰庤乃錢鎛庤具也亦作𤲵
eHd墟里;起:興也作也立也發也又姓出何氏姓苑墟里切六|邔:縣名在南郡又渠記切|杞:木名又苟杞春名天精子夏名苟杞葉秋名卻老枝冬名地骨根又國名夏之後也亦姓杞梁是也|屺:山無草木|玘:佩玉|芑:白梁粟也
UHR鉏里;士:說文曰事也數始於一終於十从一十孔子曰推十合一爲士又姓左傳晉大夫士蔿又漢複姓二氏古今人表有士思癸又士貞氏晉康公庶子士貞之後鉏里切五|仕:仕官|柹:果名|𢨪:砌也閾也|戺:+上同
WHR牀史;俟:待也亦作竢又姓風俗通云有俟子古賢人著書又虜複姓二氏後魏書云俟畿氏後改爲畿氏俟奴氏後改爲俟氏又虜三字姓三氏俟力伐氏後改爲鮑氏俟伏斤氏後改爲伏氏周書太祖賜韓襃姓俟呂陵氏牀史切又音祈七|竢:+上同|涘:水岸涯也|騃:趨行皃西京賦曰羣獸駓騃又吾駭切|𥾩:繩履|𥏳:不來也說文引詩曰不𥏳不來从來矣聲|𢓪:+說文同上
NHR即里;子:子息環濟要略曰子猶孳也孳恤下之稱也亦辰名爾雅云太歲在子曰困敦又殷姓又漢複姓十一氏左傳鄭大夫子人九魯大夫子服氏子家羈莊子有子桑扈皇子告敖何氏姓苑有子乾子仲子工子革子臧子師等氏即里切八|㜽:+古文|仔:說文克也本又音兹|虸:虸蚄蟲|耔:擁苗本也|秄:+上同|梓:木名楸屬|杍:工木匠或作梓
kHd于紀;矣:說文云語已詞也于紀切二|𦮸:蒿也
gHd魚紀;擬:度也魚紀切六|儗:僭也|薿:草盛皃又魚力切|孴:盛也|譺:議也欺也調也又魚記切|𥣖:禾盛
YHR昌里;齒:齒錄也年也又牙齒昌里切二|紕〈䊼〉:績苧一䊼出新字林
KHR敕里;恥:慙也敕里切三|祉:福也祿也|褫:徹衣又奪衣又直追池耳二切
TWT初紀｟己｠〈乙〉|TRi初紀｟史｠〈夬〉;㓼:a割聲初紀切三|欼:b齧也|㱀:b+上同
SHR阻史;滓:澱也阻史切五|笫:牀簀又側几切|胏:脯有骨曰胏易曰食乾胏|䔂:說文云羹菜也|𠂔:止也從市一橫止之出文字音義說文即里切
hHd於擬;譩:恨也又噟也於擬切又於其切二|醷:梅漿
MHR乃里;伱:秦人呼傍人之稱乃里切二|聻:指物皃也
#尾
DIN無匪;尾:首尾也易曰履虎尾又姓史記有尾生無匪切八|亹:美也爾雅亹亹勉也|斖:+俗|浘:水流皃又浘𤁵海水洩處案莊子作尾閭字不从水|娓:美也說文順也又音美音媚|䞔:人名鄭大夫蔡䞔也|䅏:饘也|䬿:微也
hId於豈;扆:戶牖閒也禮疏云如綈素屏風畫斧文也於豈切六|㥋:痛聲|偯:哭餘聲|庡〈㕈〉:藏也|僾:僾俙看不了皃又烏代切|靉:靉霼不明皃出海賦又烏代切
eId袪狶（豨）;豈:安也焉也曾也袪狶切二|䔇:菜似蕨生水中
dId居狶（豨）;蟣:蟣蝨居狶切四|幾:幾何又既稀切|穖:禾穖|𩴆:鬼俗吳人曰鬼越人曰𩴆又音祈
BIN敷尾;斐:文章皃敷尾切七|菲:薄也微也又菜名又音妃|朏:月三日明生之名|悱:口悱悱也|𩦎:馬名|奜:大也|䨽:鳥如梟也說文別也又平利切
AIN府尾;匪:非也易曰匪寇婚媾說文曰器如竹篋今從竹爲筐篚字府尾切八|篚:竹器方曰筐圓曰篚|棐:輔也|餥:餱也一曰相請食|榧:木名子可食療白蟲|蜰:爾雅云蜚蠦蜰即負盤臭蟲又音肥|䕁:草也|蜚:蟲名咸蜚又扶沸切
kIt于鬼;韙:是也于鬼切十三|煒:光煒|暐:暐曄|偉:大也|瑋:玉名|葦:蘆葦|椲:木名可屈爲盂|韡:華盛皃|𩘚:大風皃|媁:醜也|愇:字書云恨也|鍏:方言云臿宋魏之閒或謂之鍏|𢯷:逆追
dIt居偉;鬼:鬼之爲言歸也居偉切一
iIt許偉;虺:蛇虺許偉切五|𤈦:齊人云火|𩄁:震雷也|虫:鱗介摠名|卉:百草摠名又音諱
gId魚豈;顗:靖也樂也說文曰謹莊皃魚豈切二|螘:螘子蟲
iId虛豈;豨:楚人呼猪亦作狶虛豈切五|俙:僾俙|𪖥:𪖥鼻又虛几切|霼:靉霼|唏:哀而不泣
hIt於鬼;磈:磈硊石山皃又危也於鬼切二|嵔:嵔崔山高曲下
CIN浮鬼;膹:𦞦多汁浮鬼切六|䆏:稻紫莖不黏也又扶畏切|橨:船邊木也|蟦:蠀螬別名又符沸切|陫:陋也又作厞又符沸切|䒈:船䒁釘鐼
#語
gJd魚巨;語:說文論也魚巨切十二|篽:說文曰禁苑也|籞:+上同又池水中編竹籬養魚|圉:養馬又姓左傳有大夫圉公陽|敔:柷敔樂器釋名曰敔衙也衙止也所以止樂也|圄:囹圄周獄名又守也|衙:行皃楚詞云導飛廉之衙衙又音牙|齬:齟齬不相當也或作鉏鋙說文曰齬齒不相值也|鋙:鉏鋙不相當也|䥏:+上同|禦:禁也止也應也當也說文祠也|蘌:蘌翳
IJR力舉;呂:字林云脊骨也說文作呂又作膂亦姓太嶽爲禹心呂之臣故封呂侯後因爲氏出東平力舉切十三|膂:+上同|旅:師旅說文曰軍五百人也亦姓漢功臣表有旅卿封昌平侯俗作𢬜|𥰠:筲器|祣:祭山川名案論語只作旅|穭:自生稻也|梠:桷端連綿木名說文楣也|儢:儢拒心不欲爲也出文字指歸|侶:伴侶|㭚:木名可爲箭笴|郘:亭名|絽:絣也|𢈚:晉大夫名
LJR直呂;佇:久立也直呂切九|竚:+上同|芧:草也可以爲繩|苧:+上同|紵:麻紵|杼:說文曰機之持緯者又神與切|羜:生羔五月|宁:門屏之閒禮云天子當宁而立|眝:說文曰長眙也一曰張眼也
lJR余呂;與:善也待也說文曰黨與也余呂切又余譽二音七|与:+上同|𢌱:+古文|歟:歎也又音余|予:郭璞云予猶與也又弋諸切|藇:蕃蕪亦作穥又徐呂切|㦛:說文曰趣步㦛㦛也
XJR章与（與）;䰞:說文曰亨也章与切亨普庚切四|煑:+上同|陼:丘也說文曰如渚者陼丘水中高者也|渚:沚也釋名曰小洲曰渚渚遮也能遮水使旁迴也又水名出常山
cJR人渚;汝:尒也亦水名山海經曰汝水出天息山亦州名春秋時爲王畿及鄭楚之地左傳楚襲梁及霍漢爲梁縣後魏屬汝北郡隋移伊州於陸渾縣北遂改爲汝州又姓左傳晉有汝寬人渚切六|肗:魚不鮮|茹:乾菜也臭也貪也雜糅也又而恕切|㼋:乾菜|𪏮:𪏮黏也|𡫽:楚人呼寐
aJR舒呂;暑:熱也舒呂切五|鼠:小獸名善爲盜說文曰穴蟲之總名也|黍:說文云禾屬而黏也引孔子曰黍可爲酒故从禾入水也|𧑓:𧑓蝜|癙:癙病
YJR昌與;杵:世本曰雍父作杵臼昌與切二|處:居也止也制也息也留也定也說文又作処亦姓風俗通云漢有北海太守處興
JJR丁呂;貯:居也積也丁呂切九|𡪄:+上同|𢁼:棺衣|褚:裝衣|𤲑:說文曰㡒也所載以盛米也|䍆:+上同|著:著任又張慮直略二切|詝:有所知也|䘢:敝衣
QJR私呂;諝:才智之稱私呂切九|胥:+上同又思余切|㥠:+上同|稰:熟穫|醑:簏酒|湑:露皃|糈:說文云糧也又音所|楈:木也|𥚩:祭具
KJR丑呂;楮:木名丑呂切三|柠:+上同|褚:姓出河南本自殷後宋恭公子石食采於褚其德可師号曰褚師因而命氏也又張呂切
MJR尼呂;女:禮記曰女者如也如男子之教尼呂切又尼慮切二|籹:粔籹
iJd虛呂;許:許可也與也聽也亦州名本爲許國大嶽之胤周武王伐紂所封漢爲潁川郡周爲許州又姓出高陽汝南本自姜姓炎帝之後大嶽之胤其後因封爲氏虛呂切二|鄦:地名也出史記
fJd其呂;巨:大也亦姓漢有巨武爲荊州刺史其呂切十八|拒:拒捍也又格也違也|秬:秬黑黍也|距:鷄距|𧣒:+上同|炬:火炬|粔:新字解訓曰粔籹膏糫|𧇽:飛𧇽天上神獸鹿頭龍身說文曰鍾鼓之柎也飾爲猛獸釋名曰橫曰栒縱曰𧇽|虡:+上同俗作簴|鐻:+上同|鉅:澤名又大也|苣:苣蕂胡麻|駏:駏驉|𦼫:苦𦼫江東呼爲苦蕒|𦊐:罟也|詎:豈也又音遽|歫:書傳云至也|䶙:齗腫
VJR疎舉;所:說文云伐木聲也詩曰伐木所所又處所也詩曰獻于公所亦姓漢有諫議大夫所忠疎舉切七|𠩄:+俗|糈:祭神米也|齭:齒傷醋也說文音楚|疋:記也又山於切|盨:說文曰㯯盨負戴器也|䝪:齎財問卜
TJR創舉;楚:萇楚亦荊楚又州本漢射陽縣地春秋時屬吳秦屬九江郡晉爲山陽縣武德初改爲楚州又姓左傳趙襄子家臣楚隆創舉切八|礎:柱下石也|齭:齒傷醋也|齼:+上同|𪓐:說文曰會五綵鮮皃引詩云衣裳𪓐𪓐|䙘:埤蒼云鮮也一曰美好皃|憷:痛也出音譜|濋:水名
SJR側呂;阻:隔也憂也側呂切二|爼〈俎〉:俎豆
UJR牀呂;齟:齟齬牀呂切二|鉏:鉏鋙不相當也
PJR慈呂;咀:咀嚼慈呂切六|沮:止也又七余子預二切|怚:憍也又子據切|袓:㜺也說文曰事好也又子邪切|跙:行不進皃|𧽟:邪出前也又前結切
hJd於許;𢮁:擊也於許切二|𩩘:肩骨
dJd居許;舉:擎也又立也言也動也說文本作擧又姓出姓苑居許切十|莒:草名亦國名又姓嬴姓之後漢有緱氏令莒誦|櫸:木名|筥:筐筥|𥴧:飤牛筐|𧺹:行皃|弆:藏也|柜:柜柳|䢹:亭名在長沙郡|𠢈:共舉皃
RJR徐呂;敘:次弟爾雅曰敘緒也又姓徐呂切十一|緒:基緒說文曰絲耑也亦姓|藇:姓也已上三字並出何氏姓苑|序:庠序又爾雅曰東西牆謂之序|漵:水浦也|抒:渫水俗作汿又神呂切|嶼:海中洲也|鱮:魚名|𨣦:酒之美也本亦作藇詩云釃酒有藇|𥎗:矛也|𡱣:履屬
eJd羌舉;去:除也說文从大口也羌舉切又丘據切五|麮:麥粥汁|弆:藏也又音莒|𧉧:𧉧蚥|𥿇:繼入也又音疎
bJR神與;紓:緩也神與切又音舒三|抒:左傳云難必抒矣抒除也又音序|杼:橡也
ZJR承與;野:田野承與切又與者切二|墅:田廬
OJR七與;𥅗〈𤿚〉:皴𤿚皮裂七與切一
NJR子與;苴:履中草子與切又子余切三|咀:㕮咀漬藥也又慈呂切㕮音甫|䃊:𥒰䃊場外名也
#麌
gKt虞矩;麌:牡鹿又麌麌羣聚皃虞矩切三|俁:俁俁容皃大也詩曰碩人俁俁|噳:噳噳笑皃
kKt王矩;羽:舒也聚也亦鳥長毛也又官名羽林監應劭漢官儀曰羽林者言其爲國羽翼如林盛也皆冠鶡冠亦姓左傳鄭大夫羽頡又虜姓後魏書羽弗氏後改爲羽氏又音芋王矩切十五|禹:舒也字林云蟲名又姓夏禹之後王僧孺百家譜云蘭陵蕭道遊娶禹氏女|雨:元命包曰陰陽和爲雨大戴禮云天地之氣和則雨說文云水从雲下也一象天冂象雲水霝其閒也|宇:宇宙也又大也說文曰屋邊也易曰上棟下宇亦姓出何氏姓苑又虜複姓宇文氏出自炎帝其後以有甞草之功鮮卑呼草爲俟汾遂号爲俟汾氏後世通稱宇文蓋音訛也代爲鮮卑單于|㝢:+上同|瑀:石似玉也|祤:祋祤縣名在馮翊又況羽切|栩:栩陽地名又況羽切|鄅:鄅子國在琅耶其後以國爲姓|頨:孔子頭反頨也說文云頭妍也又讀若翩|楀:木名又矩|萭:說文艸也|䣁:亭名在南陽|聥:張耳有所聞又音矩|䨞:雨皃
PKh慈庾;聚:眾也共也斂也說文會也邑落云聚慈庾切二|鄹:亭名在新豐
AKN方矩;甫:始也大也我也眾也說文曰男子之美稱也字从父用又姓風俗通云甫侯之後方矩切十九|脯:乾脯東方朔云乾肉爲脯禮記曰牛脩鹿脯田豕脯|斧:斧鉞周書曰神農作陶冶斤斧|頫:說文低頭也太史公書頫仰字如此|俯:+上同漢書又作俛今音免|府:官府說文曰府文書藏也風俗通曰府聚也公卿牧守道德之所聚也又舍也亦姓風俗通云漢有司徒掾府悝|腑:藏腑本作府俗加月|簠:簠簋又音膚|黼:白黑文也爾雅曰斧謂之黼謂畫斧形因名云|蜅:小蟹|莆:萐莆堯之瑞草|𧉊:爾雅曰蠸輿父守瓜郭璞云今瓜中黃甲小蟲喜食瓜葉故曰守瓜字或从虫|俌:俌輔也出埤蒼|㕮:㕮咀|父:尼父尚父皆男子之美稱又漢複姓三氏孔子弟子有罕父黑漢有臨淄主父偃左傳宋有皇父充石宋之公族也漢初有皇父鸞自魯徙居茂陵改父爲甫後漢安定太守儁始居安定朝那代爲西州著姓又徙居京兆又音釜|𥒰:𥒰䃊|蚥:蜛蚥螳蜋別名|鯆:大魚|郙:亭名也在上蔡
DKN文甫;武:止戈爲武又迹也曲禮曰堂上接武又州名本自白馬玄氏地魏文徙武都郡於美陽今好畤縣界武都古城是也後魏平仇池山築城置武都鎮即今州是也亦姓風俗通云宋武功之後漢有武臣又漢複姓六氏漢有乘黃令武安恭出自武安君白起之後風俗通云漢武強侯王梁其後因封爲氏世本云夏時有武羅國其後氏焉何氏姓苑有廣武氏出自陳餘之後又武成氏武仲氏又虜複姓西秦錄有武都氏文甫切二十四|舞:歌舞左傳曰舞所以節八音而行八風也周禮曰樂師掌國學之政以教國子小舞也山海經曰帝後俊八子始爲舞又姓出何氏姓苑|儛:+上同|嫵:嫵媚|侮:侮慢也侵也輕也|𦌬:牕中網也|憮:憮然失意皃說文愛也一曰不動也|㒇:+上同|珷:珷玞石次玉|碔:+上同|廡:堂下也|𢋑:+籀文|甒:甖甒|潕:水名在南陽|鵡:鸚鵡鳥名能言|䳇:+上同|𢜮:愛也說文撫也|膴:土地腴美膴膴然也|瞴:微視之皃|娬:好也|敄:彊也|䒉:長艇船也|䍙:雉網|𣞤:蕃滋生長說文豐也隷省作無今借爲有無字
CKN扶雨;父:說文曰父矩也家長率教者扶雨切十五|輔:毗輔又助也弼也亦姓左傳晉大夫輔躒又智果以智伯必亡其宗改爲輔氏|䩉:頰骨|𩒺:+上同|腐:朽也敗也說文爛也|𩾿:𩾿鳼越鳥|滏:水名在鄴山海經云神箘之山釜水出焉|䭸:牡馬|㕮:㕮咀嚼也又音甫|蚥:蟾蜍別名|㾈:病腫也說文俛病也|秿:禾穳積也|鬴:說文鍑屬又覆鬴九河之一名|釜:+上同古史考云黃帝始造釜|䪔:尻衣
BKN芳武;撫:安存也又持也循也芳武切十三|𢻬:+上同|弣:弓把中也|𠛺:+上同說文又方九切刀握也|拊:拍也說文揗也|殕:食上生白毛|䋨:䋨綿|俌:輔也又音甫|剖:判也又普厚切|䌗:絲|䯽:說文云髮皃又步侯切|𠟌〈𦵿〉:𦵿草|䞤:健也亦作𠹪
LKh直主;柱:廣雅曰楹謂之柱又姓出何氏姓苑直主切三|跓:停足|嵀:天嵀案爾雅曰霍山爲南嶽郭璞云即天柱山字俗從山
iKt況羽;詡:和也普也遍也大也禮云詡謂敏而有勇況羽切十二|𦀒:殷冠名|冔:+上同|姁:呂氏春秋云姁姁然相樂也又漢高后字娥姁說文嫗也|栩:柞木名說文云杼也其實皁一曰樣樣音象|珝:玉名|欨:說文吹也一曰笑意本火于切|祤:祋祤縣在馮翊|咻:噢咻病聲|喣:呈示|䧁:鄉名在安邑|煦:溫也又香句切
ZKh臣庾;豎:立也又童僕之未冠者又姓左傳鄭有大夫豎拊臣庾切四|竪:+俗|樹:扶樹|裋:敝布襦也
lKh以主;庾:倉庾又姓出潁川新野二望本自堯時爲掌庾大夫因氏焉以主切十二|窳:器中空亦病也|𥦠:+上同|抌:刺也|㥚:懼也|𦺮:百𦺮草|愈:差也賢也勝也|瘉:病也說文曰病瘳也|㼌:微弱本不勝末|貐:獸名龍首食人說文曰䝟貐似貙虎爪食人迅走也|楰:鼠梓似山楸而黑也|斞:說文量也
XKh之庾;主:掌也領也典也守也君也說文曰鐙中火主又姓出姓苑之庾切五|麈:鹿屬華陽國志曰郪縣宜君山出麈尾|枓:斟水器也|宔:說文曰宗廟宔祏或作砫|炷:燈炷又音注
hKt於武;傴:不伸也尪也荀卿子曰周公傴背於武切三|噢:噢咻病聲|迂:曲迴皃
eKt驅雨;齲:齒病後漢梁冀妻能爲愁眉帝䊋齲齒笑折𦝫步驅雨切三|踽:䠑踽又獨行皃|竘:巧也又音口
JKh知庾;拄:拄從旁指知庾切四|柱:柱夫草一名搖車也|丶:說文曰有所絕止而識之也|𪐴:+𪐴點義與上同
cKh而主;乳:柔也而主切三|擩:擩取物也|醹:厚酒
fKt其矩;窶:貧無禮也其矩切二|貗:爾雅云貒子貗
VKh所矩;數:說文計也所矩切又所句所角二切二|籔:簍籔四足几也
dKt俱雨;矩:法也常也俱雨切十一|榘:+上同說文又其呂切|踽:獨行又驅雨切|枸:木名出蜀子可食江南謂之木蜜其木近酒能薄酒味也|萭:姓漢有萭章又音禹|聥:張耳有所聞|䅓:曲枝果也|𦐛:曲羽又求俱切|楀:楀氏木名又音禹|蒟:蒟醬出蜀其葉似桑實似椹又音句|椇:枳椇
OKh七庾;取:收也受也七庾切一
IKh力主;縷:絲縷力主切十三|𨻻:𨏩𨻻縣名在交阯|僂:僂傴疾也|褸:襤褸衣敝說文衽也|簍:小筐|嶁:岣嶁衡山別名|謱:覼謱委曲|慺:姓出纂文|漊:說文曰雨漊漊也一曰汝南人謂㱃酒習之不醉爲漊|𪈜:𪇖𪈜鳥今云郭公也|㜢:女人惡稱|𦳭〈𦭯〉:小蒿草|蔞:草可亨魚又力俱切
QKh相庾;𦄼:絆前兩足相庾切二|䅡:草名
UKh鶵（雛）禹;䝒:小母豬也鶵禹切二|𧱛:+上同
#姥
DLB莫補;姥:老母或作姆女師也亦天姥山也又姓出何承天纂文莫補切六|莽:宿草又音蟒|䥈:鈷䥈又音蟒|媽:母也|峔:慈母山名在丹陽亦作姥俗從山|𢜮:愛也又音武
FLB他魯;土:釋名曰土吐也吐萬物也文字指歸無點他魯切四|吐:口吐亦虜複姓三氏後魏書有吐奚吐難吐萬氏又虜三字姓三二氏慕容廆庶長兄吐谷渾後將所部居西零以西甘松之南極乎白蘭數千里其孫葉延曰禮云孫子得以王父字爲氏遂以吐谷渾爲氏又後魏書吐伏盧氏|稌:稌稻|芏:草名似莞生海邊可爲席
GLB徒古;杜:甘棠子似棃又塞也澀也又杜仲藥名亦姓本自帝堯劉累之後出京兆濮陽襄陽三望漢有御史大夫杜周以南陽豪族徙茂陵始居京兆徒古切九|靯:韝靫別名一云靯𩍿|𤬪:瓶也|𡍨:填也|𢾅:塞也閉也|肚:腹肚又當古切|𥀁:桑皮|荰:杜衡香草似葵山海經云可以治癭帶之令人便馬馬亦善走根葉都而氣小異字俗從廾|土:土田地主也本音吐
ILB郎古;魯:鈍也又國名伯禽之後以國爲姓出扶風又羌複姓有魯步氏郎古切十七|櫓:城上守禦望樓釋名曰櫓露也露上無覆屋也說文云大盾也|滷:鹹滷|虜:虜掠又獲也服也|擄:虜掠或從手|㢚:庵舍|𢲸:搖動|樐:彭排|艣:所以進船|鐪:釜屬|蓾:杜衡別名|𧀦:+上同|鹵:鹵簿令|㔪:匐也|鏀:鏀以木爲刀柄|㭩〈㭔〉:木名可染繒|䲐:魚名
OLB采古;蔖:草死爾雅曰蓾蔖郭璞云作履苴草采古切二|𧆓:草履
ELB當古;覩:見也當古切十一|睹:+上同|暏:詰朝欲明|賭:戲賭|堵:垣堵又姓左傳鄭有堵叔又音者|肚:腹肚又徒古切|帾:幡也標記物之處也|㕆:美石又音怙|楮:木名又音褚|𥀁:桑皮又音杜|䁈:梁公子名仉䁈
dLB公戶;古:故也又姓周太王去邠適岐稱古公其後氏焉蜀志有廣漢功曹古牧又漢複姓晏子春秋有齊勇士古冶子又虜三字姓後漢書有古口引氏公戶切二十一|皷〈鼓〉:說文曰郭也春分之音萬物郭皮甲而出故謂之鼓周禮六鼓靁鼓靈鼓路鼓鼖鼓鼛鼓晉鼓亦作𡔷|鼔:說文曰擊鼓也|瞽:無目|股:髀股|𦙶:+上同|罟:網罟|蠱:疑也又蠱毒也又卦名蠱事也|估:市稅|盬:鹽池又左傳曰盬其腦杜預云盬𠯗也又詩傳云盬不固也|鈷:鈷䥈|羖:羖䍽羊說文曰夏羊牡曰羖|𦍩:+俗|詁:詁訓|牯:牯牛|賈:商賈又古下切|夃:多貨利也又古乎切|沽:屠沽|焸:人名出漢書|𠒂〈𠑹〉:壅蔽|𥂩:器也說文作䀇
gLB疑古;五:數也又姓左傳有五奢亦漢複姓四氏漢有五鹿充宗風俗通云氏於職焉三烏五鹿是也趙有將軍五鳩盧國語云楚昭王時有五參蹇姓苑有五里氏疑古切五|午:交也又辰名爾雅云太歲在午曰敦牂|旿:明也|伍:行伍說文曰相參伍也周禮曰五人爲伍|仵:偶敵又伍仵皆姓出姓苑
CLB裴古;簿:簿籍又車駕次第爲鹵簿裴古切二|部:部伍又部曲
PLB徂古;粗:麤也略也徂古切又千胡切五|麆:大也|駔:駿馬又祖朗切|伹:淺也|觕:牛角直下
NLB則古;祖:祖禰又始也法也本也上也又姓祖巳之後出范陽則古切六|珇:珪上起又美好|組:瑑組綬又綸組東海中草名|蒩:茅藉|䔃:說文菜也|靻:靻勒名
iLB呼古;虎:獸名說文曰虎山獸之君淮南子曰虎嘯谷風至又姓風俗通曰漢有合浦太守虎旗其先八元伯虎之後呼古切七|琥:發兵符有虎文周禮云白琥禮西方|戽:戽斗舟中渫水器又音戶|滸:水岸|𨛵:地名|萀:虎豆名俗加艹|䗂:蠅虎蟲俗加虫
hLB安古;隖:村隖亦壁壘說文曰小障也一曰庳城也安古切十|塢:+上同通俗文曰營居曰塢戴延西征記曰蠡城川南有金門塢|鄔:縣名又姓晉大夫司馬彌牟之後因以爲氏|瑦:石似玉也|䃖:小障也出埤蒼|𢄓:頭巾|溩:水溩|䛩:相毀皃|𧽋:走輕|䡧:車頭中骨
eLB康杜;苦:麤也勤也患也說文曰大苦苓也康杜切二|𥯶:竹名
HLB奴古;怒:恚也奴古切又奴故切五|弩:弓弩古史考曰黃帝作弩|砮:石可爲矢鏃又乃胡切|努:努力|𧉭:水弩蟲俗從虫
jLB侯古;戶:說文云戶護也半門爲戶侯古切二十三|楛:木名堪爲矢榦書云荊州所貢詩疏云東夷之所貢|扈:跋扈猶強梁也又有扈國名亦姓風俗通云趙有扈輒又虜三字姓有扈地干氏|怙:恃怙|鄠:縣名在京兆府本夏之扈國秦爲鄠縣也|帍:巾也|祜:福也|昈:文彩狀又明也|𡻮:山卑而大曰𡻮|岵:山多草木|芐:地黃|雇:說文曰九雇農桑候鳥扈民不婬者也春雇鳻鶞夏雇竊玄秋雇竊藍冬雇竊黃棘雇竊丹行雇唶唶宵雇嘖嘖桑雇竊脂老雇鴳也|𩿇:+上同亦作鳸|𪄮:亦冂|𨛸:西京賦云枹杜含鄠|婟:婟惜又音互|戽:抒也|㕆:美石又丁古切|洿:洿深皃|𡜂:貪也|酤:一宿酒又音姑|滬:靈龜負書出玄滬水|簄:海中取魚竹罔曰簄
BLB滂古;普:博也大也徧也又姓後魏十姓獻帝次兄爲普氏亦虜複姓周書辛威賜姓普屯氏又虜三字姓周書楊忠賜姓普六如氏後魏書有普陋如氏滂古切五|溥:大也廣也|誧:文字音義云大也助也|浦:風土記云大水有小口別通曰浦說文濱也又姓晉起居注有浦選|烳:火行皃
ALB博古;補:補綴說文曰完衣也博古切三|譜:籍錄|圃:園圃說文種菜曰圃亦姓又博故切
#薺
PMR徂禮;薺:甘菜徂禮切五|鮆:魚名常以春時出九江|鱭:+上同|癠:病也方言曰生而不長也|啙:弱也又子西兹此二切
IMR盧啓;禮:說文曰履也所以事神致福也釋名曰禮體也得其事體也又姓左傳有衛大夫禮孔盧啓切十六|礼:+古文|𥴡:竹名|蠡:蠡吾縣名在涿郡又彭蠡澤名|𦫈:大舟也|澧:水名在武陵又水名出衡山亦姓出何氏姓苑|醴:醴酒亦醴泉縣屬京兆府本漢谷口縣也屬馮翊至後魏置寧夷縣隋改醴泉因周醴泉宮名也|鱧:說文鱯也|鱺:+上同|𩽵:說文鮦也|欚:江中大船名亦作𦫈|盠:簞也|劙:刀刺又力移切|豊:行禮之器|𣀷:布也說文數也又音離|欐:小船又力計切
FMR他禮;體:體身也又生也他禮切八|軆:+俗|醍:醍酒又音啼|涕:目汁|䪆:䪆𩋪輭皃|挮:去淚|緹:纁又音啼|𣈡:橫首杖名
BMB匹米;䫌:傾頭匹米切一
NMR子禮;濟:定也止也齊也亦濟濟多威儀皃又水名出王屋亦州本齊地秦屬東郡宋於此置碻磝戍後魏於此置濟北郡周武帝置肥城郡武德改爲濟州或作泲又姓出姓苑襄城人也子禮切又音霽五|㧗:殺也又側買切|䍤:手搦酒又作擠|癠:生而不長|𠨍:事之制也說文音卿
EMR都禮;邸:舍也所姓風俗通云漢上郡太守邸杜俗從互餘同都禮切十三|底:下也止也作底非也|詆:呰也訶也|䏄:耳膿|坻:隴阪又支氏切|抵:擠也擲也|牴:角觸|觝:+上同|柢:本也根也|弤:埤蒼云舜弓名|㪆:隱也|堤:滯也|軧:大車後也
GMR徒禮;弟:兄弟爾雅曰男子先生爲兄後生爲弟徒禮切又特計切七|娣:娣姒|悌:愷悌詩作豈弟毛萇云豈樂也弟易也|䑯:䑯船|遞:更代也又亭繼切|㼵:小瓫|媞:好人安詳之容皃又啼是二音
HMR奴禮;禰:祖禰亦姓出平原魏有禰衡亦作𥙄餘同奴禮切十三|嬭:楚人呼母又奴蟹切|䦵〈𩰞〉:智少力劣|苨:薺苨|𩋪:䪆𩋪輭皃|𦰫:𦰫𦰫濃露也亦作泥|瀰:水流也|坭:地名|𩯨:髮皃|薾:華茂也|檷:絡絲柎也|鑈:+上同|𩍦:轡垂也
QMR先禮;洗:洗浴又姓先禮切又音銑二|洒:+上同又所賣切
OMR千禮;泚:水清也千禮切四|玼:玉色|緀:帛文皃|皉:白色
eMR康禮;啓:開也發也別也刻也說文教也俗作啓康禮切十二|棨:兵欄說文曰傳信也|綮:戟支一曰戟衣|卟:問卜也又工兮切|䭬:首至地也|稽:+上同又古兮切|晵:說文云雨而晝晴也又姓後燕有將軍晵倫或作啓|闙:埤蒼與啓亦同|启:說文開也|䏿:腓腸又口系切|㒅:開衣領也|䡔:至也礙也
jMR胡禮;徯:待也胡禮切八|謑:恥辱|𥰥:所以安重船又音系|𦩶:+上同|涀:水名在高陵|𧧹:說文待也|匸:有所藏也|𥉐:目動
DMB莫禮;米:穀實說文作米又胡姓莫禮切七|眯:物入目中|䋛:繡文如聚米出說文|洣:水名在荼陵|蔝:蔝子菜|𡬍:寐不覺|䱊:魚子
CMB傍禮;陛:階陛也傍禮切八|梐:梐枑行馬|髀:髀股|䯗:+上同|㙄:下也|𦸣:𦸣鼠莞見爾雅可爲席又必鼻切|𤙞:𤙞𤙞牛馬行|𠈺:㒅開腳行也
hMR烏弟;𠯋:可也尒也烏弟切二|䚷:噟聲
gMR研啓;堄:埤堄女墻研啓切六|㪒:㪏㪒擊聲|掜:不從也|觬:角曲|䘽:裗䘽袿衣飾也|晲:明也亦作𣅸
AMB補米;㪏:補米切二|𤽊:明白
#蟹
jPR胡買;蟹:水蟲仙方云投於漆中化爲水服之長生以黑犬血灌之三日燒之諸鼠畢至胡買切七|䲒:+說文上同|解:曉也又解廌仁獸似牛一角亦姓自唐叔虞食邑於解今解縣也晉有解狐解楊出鴈門又虜複姓魏書有解批氏又佳買古賣二切|獬:字林字樣俱作解廌廣雅作𧳊𧳋陸作獬豸也|澥:渤澥|嶰:山澗閒又嶰谷名案漢書只作解谷|𨼬:小谿
DPB莫蟹;買:說文市也莫蟹切五|嘪:羊聲|蕒:吳人呼苦𦼫|㵋:水名|鷶:鷶𪀗鳥名
ePR苦蟹;䒓:戾也苦蟹切三|𡢖:意難|𦝨:瘦皃
LPR宅買;廌:解廌宅買切三|豸:-|𧳋:+上同
MPR奴蟹;嬭:乳也奴蟹切二|㚷:+上同
CPB薄蟹;罷:止也休也薄蟹切六|矲:矲𥏪短也|猈:犬短脛一曰案下狗也|䥯:太鐵杖|𢞎:疲劣|㔥:㔥𠢲惡怒
hPR烏蟹;矮:短皃烏蟹切三|㢊:坐倚皃又作躷|躷:+上同
APB北買;擺:擺撥北買切二|捭:+上同鬼谷子有捭闔篇
dPR佳買;解:講也說也脫也散也佳買切三|薢:爾雅曰薢茩芵茪|檞:松樠
VPR所蟹;灑:灑水爾雅云大瑟謂之灑長八尺一寸廣一尺八寸二十七弦所蟹切又所綺切三|𩌦:履屬|躧:颯躧
dPh乖買;𠁥:𠁥𠁥羊角開皃乖買切又工瓦切三|𡐠:𡐠盾屬也說文苦圭切盾握也|枴:老人拄杖也
deT丈〈？〉夥〈黠〉;㧳:攙㧳㧳物出聲譜丈夥切一
jPh懷𠁥;夥:多也懷𠁥切又胡果切一
deT花〈？〉夥〈黠〉;扮:亂扮也花夥切一
GPR求〈？〉蟹|dPh求〈乖〉蟹;箉:a竹具用之魚笱竹器也求蟹切二|拐:b手腳之物枝也
#駭
jQR侯楷;駭:驚也又九河名一曰徒駭出爾雅孫炎云禹疏九河功眾懼不成故曰徒駭侯楷切四|絯:大絲又音該|侅:無侅人名又音該|駴:駴擊
eQR苦駭;楷:模也式也法也說文曰木也孔子冢蓋樹之者又姓苦駭切四|𠢲:㔥𠢲|𥏪:矲𥏪|鍇:鐵好
gQR五駭;騃:癡也五駭切又音俟四|𤶗:𤶗疾|娾:喜樂|𧡋:笑視
hQR於駭;挨:打也於駭切二|唉:飽聲又於來切
#賄
iSh呼罪;賄:財也又贈送也呼罪切七|𧶅:+上同|䏨:𦞙䏨大腫皃𦞙都罪切|燘:熟皃又亡罪切|悔:悔吝|蛕:土蛕毒蟲|㷄:南人呼火也
hSh烏賄;猥:犬聲又鄙也烏賄切十|腲:腲脮肥皃|嵔:嵔𡾋|鍡:鍡鑘不平|㛱:㛱娞好皃|碨:碨磊石皃|𥓔:+上同|㱬:㱬𣨙不知人也|㞇:㞇㞂行病|𨝀:𨝀郲不平
ISh落猥;磥:眾石皃落猥切十六|磊:+上同|癗:痱癗皮外小起|𡾋:𡾋峞山狀|礧:礧硌大石|䣂:䣂陽縣名在桂陽|鑘:鍡鑘|㵽:水名在右北平|郲:𨝀郲不平|𡼊:𡼊㠑山狀又力水切|蕾:蓓蓓蕾花綻皃|儡:傀儡戲|𨻾:𨻾𡑈果實垂又力追切|𦢏:𦢏𦞙腫皃|頛:頭不正皃|櫑:櫑劒古木劒也
GSh徒猥;錞:矛戟下銅鐏或作鐓徒猥切又徒對切五|瀢:瀢沱水汎沙動皃|陮:陮隗不平狀|𨯝:鍊𨯝車轄|𦶏:草名
PSh徂賄;辠:文字音義云辠從自辛也言辠人蹙鼻辛苦之憂始皇以辠字似皇乃改爲罪也徂賄切三|罪:+上同|㠑:𡼊㠑山皃
DSB武罪;浼:水流平皃武罪切六|潣:+上同|每:雖也辝也頻也說文作𡴋艸盛上出也|挴:貪也|燘:燘爛也又呼猥切|䜸:豆碎萁也
FSh吐猥;骽:骽股也吐猥切八|腿:+俗|聉:聉顡癡瘨皃說文五滑切無知意也顡音隗|僓:長好皃|脮:腲脮|㟎:㟎㠑山高皃|㱣:㱬㱣|㞂:㞇㞂行病
jSh胡罪;瘣:木病無枝胡罪切九|溾:溾浽穢濁也|㱱:㱱㱣|䜋:列也玉篇云譯也說文胡對切中止也|匯:回也|廆:晉有大單于遼東郡公慕容廆|䕇:爾雅云䕇懷羊又音瑰|輠:車轉之皃|𨝀:𨝀郲不平
eSh口猥;䫥:大頭說文曰頭不正也口猥切五|㚍:㚍㚍多皃|傀:俗作傀儡子也|顝:首大骨又口兀切|磈:磈礧石也
ESh都罪;𦞙:𦢏𦞙亦作䏨都罪切五|䇏:木實垂皃|𡑈:𨻾𡑈重皃|頧:頭不正皃|謉:謉諢謔言出聲譜
HSh奴罪;餧:飢也一曰魚敗曰餧奴罪切八|餒:+上同|浽:溾浽|娞:㛱娞|𩗔:風動皃|鮾:魚敗|脮:+上同|㼏:傷瓜
ESh陟賄;𩬳:陟賄切假髮髻也一
gSh五罪;頠:頭也一曰閑習五罪切又五毀切七|顡:聉顡說文音聵癡顡不聰明也|隗:陮隗高也亦姓出天水後漢有隗嚻|峞:峞𡾋山皃|嵬:山皃又玉回切|䫥:頭不正也又口猥切|䃬:眾石皃
OSh七罪;皠:霜雪白狀七罪切八|𣿒:新水狀也|𣿓:+上同|漼:水深皃|璀:玉名|𥼺:物粗也|䊫:赤米|鏙:鏙錯鱗甲皃
CSB蒲罪;琲:珠五百枚蒲罪切三|痱:痱癗|𢳁:𢳁起令虛
NSh子罪;嶊:山林崇積皃子罪切二|洅:說文云雷震洅洅本作代切
kUt于罪;倄:痛而叫也于罪切一
#海
iTR呼改;海:說文曰天池也以納百川者亦州禹項徐州之域七國時屬楚秦爲薛郡漢爲東海郡後魏爲海州亦姓呼改切三|醢:肉醬亦作醯|橀:榽橀木名似檀齊人諺云上山斫檀榽橀先殫
eTR苦亥;愷:樂也康也左氏傳云八愷苦亥切九|凱:+上同|颽:南風亦作凱|塏:爽塏高地爽明塏燥也|暟:美|鎧:甲之別名|闓:開也亦音開|䐩:肉美|輆:輆軩不平
NTR作亥;宰:冢宰又制也亦姓孔子弟子宰予作亥切四|縡:載也|䏁:半聾字林云秦晉聽而不聰聞而不達曰䏁|載:年也出方言又音再
GTR徒亥;駘:疲也鈍也駘蕩春色皃亦宮名徒亥切又音臺十一|殆:危也近也|待:待擬也俟也|怠:懈怠|迨:及也|𨽿:+上同|紿:欺言詐見又絲勞也|䈚:竹筍|詒:相欺|軩:輆軩不平|𠷂:言不止
HTR奴亥;乃:語辭也汝也奴亥切三|迺:+古文|鼐:鼎大者曰鼐又奴代切
dTR古亥;改:更也又姓秦有大夫改產古亥切三|頦:頰頦又戶垓切|絠:解繩說文云彈彄也
jTR胡改;亥:辰名爾雅云太歲在亥曰大淵獻亦姓孟子有亥唐胡改切四|侅:奇侅非常|㧡:動也|𥩲:豎𥩲神人
BSB匹愷;啡:出唾聲匹愷切一
OTR倉宰;采:事也又取也亦姓風俗通云漢有度遼將軍采晧倉宰切七|採:+取也俗|綵:綾綵|寀:寮寀官也|彩:光彩|䰂:髮䰂又七代切|㥒:恨也
YUR昌紿;茝:香草也昌紿切一
ETR多改;等:齊也多改切又多肯切一
DSB莫亥;䆀:禾傷雨也莫亥切又莫代切二|𢮇〈挴〉:貪
PTR昨宰;在:居也存也昨宰切一
BSB普乃;俖:不肯也普乃切二|朏:說文云月未盛之明又音斐
hTR於改;欸:相然譍也於改切四|㕈:藏也|毐:嫪毐秦人名又音哀|挨:擊也
lUR夷在;佁:癡也夷在切一
FTR他亥;㘆:㘆𠷂言不止他亥切一
HTR如亥;疓:病也見尸子如亥切一
ITR來改;𨦂:連絲釣曰𨦂出字苑來改切二|唻:囉唻歌聲又力諧切
lUR與改;䑂:肥也與改切二|𦚪:+上同
CSB薄亥;倍:子本等也薄亥切三|菩:說文曰草也|蓓:黃蓓草也
#軫
XVR章忍;軫:動也車後橫木也又姓今吳縣有之俗從尒餘同章忍切二十三|縝:結也單也又丑珍切|胗:𤻘胗皮外小起說文曰脣瘍也又音緊|疹:+籀文|畛:田閒道又音真|賑:隱賑說文富也又之刃切|㐱:說文曰稠髮也引詩曰㐱髮如雲亦作鬒|鬒:+上同|槙:木密又丁堅切|紾:單衣或作縝|縝:+上同|𦕑:告也|診:候脈又視也驗也|袗:說文云玄服也亦作裖|裖:+上同|敐:𨌈𨌈敐敐喜悅皃𨌈音田|眕:目有所恨而止又厚重也|䪾:顏色䪾䫰慎事也|黰:黑皃|駗:馬色也|𣞟:纑也|稹:緻也又聚物|𠘱:新生羽而飛也
KVR丑忍;辴:大笑丑忍切一
ZVR時忍;腎:五藏之一也時忍切六|蜃:大蛤說文曰雉入水所化又時刃切|祳:祭餘肉說文云社肉盛之以蜃故謂之裖天子所以親遺同姓|脤:+上同|㰮:指而笑也|鋠:玉篇云圓鐵
cVR而軫;忍:強也有所含忍而軫切三|荵:說文曰荵冬草也爾雅曰蒡隱荵郭璞云似蘇有毛|涊:水名在上黨
aVR式忍;矤:說文曰況也詞也从矢取詞之所之如矢也式忍切六|矧:-|訠:+並上同|哂:笑也|弞:笑不壞顏|頣:舉眉視人
IVR良忍;嶙:嶾嶙山高皃良忍切五|僯:慙恥|𩕔:少髮皃|橉:門限也又牛車絕橉又力進切|撛:扶也
LVR直引;紖:牛紖直引切四|䏖:杖痕腫處說文音酳瘢也一曰遽也|䀕:瞋怒目皃|眹:目童子也又吉凶形兆謂之兆眹
dVV居忍;緊:紉急也居忍切四|胗:脣瘍也又之忍切|𦜌:-|𤷌:+並俗
PVR慈忍;盡:竭也終也慈忍切又即忍切二|濜:濜溳水流急皃
NVR即忍;㯸:埤蒼云盂也即忍切二|盡:曲禮曰虛坐盡前虛坐盡後虛坐盡前又慈忍切
CVF毗忍;牝:牝牡毗忍切又扶履切四|髕:去膝蓋骨刑名|臏:+上同|猵:獺屬又音邊
gVZ宜引;釿:齊也說文曰劑斷也宜引切五|磭:大脣|𪙤:齒齊|齗:犬爭皃|听:口大皃
kVp士〈于〉忍;笉:笑皃士忍切一
fVp渠殞;窘:急迫也渠殞切十|僒:+上同|莙:牛藻也|㖥:吐皃|㻒:玉名|箘:竹名|菌:地菌又姓出姓苑|䐃:腸中脂也|蔨:爾雅曰蔨鹿𧆑郭璞云今鹿豆也葉似大豆根黃而香蔓延生|蜠:爾雅曰貝大而險者曰蜠又音囷
lVR余忍;引:爾雅曰長也說文曰開弓也余忍切又餘刃切十四|𢎢:+上同玉篇云挽弓也|蚓:蚯蚓又余刃切|螾:+螾衍蚰蜒又餘刃切說文上同|弞:笑不壞顏|𠻤:大笑又音衍|𢯼:申布也又布也|䏖:當脊肉也|濥:水門又引水也說文曰水脈行地中濥濥也|廴:長行之皃|戭:長槍也又弋淺切|縯:齊武王名|鈏:爾雅曰錫謂之鈏|靷:說文曰引軸也又餘刃切
DVJ眉殞;愍:悲也憐也眉殞切十四|慜:聰也|憫:憫默亦憂也|閔:傷也病也又姓孔子弟子閔損|敏:疾也敬也聰也達也|敃:說文強也|𢽹:+上同|潣:水流浼浼皃|簢:竹名可以爲席爾雅曰簢筡中言其中空筡音塗或作𥴲|𥴲:+上同|𤛎:獸如牛也|𦌡:細罔|𨏵:車𨋩兔下革也|鰵:海魚
DVF武盡;泯:水皃亦滅也盡也武盡切又彌鄰切十|𤿕:細理|僶:僶俛|笢:竹膚|黽:黽池縣在河南府俗作黾又音緬|澠:+上同又音繩|䟨:蹄甲|刡:刡削|𨌲:車𨋩兔下軶也|䐇〈脗〉:脗合
kVp于敏;殞:歿也于敏切七|溳:濜溳波相次也|磒:石落|隕:墜也落也|霣:說文雨也齊人謂靁爲霣一曰雲轉起也|愪:憂也|荺:爾雅云荺茭蔈葦根可食者曰茭茭胡狡切
#準
XVh之尹;準:均也平也度也又樂器名狀如瑟長丈而十三弦隱九尺以應黃鐘之律之尹切又音拙四|准:+俗|埻:射的周禮或作準|純:緣也又音淳
lVh余準;尹:正也誠也進也說文治也又姓出天水河閒周有尹吉甫又漢複姓齊定王時有尹文子著書又漢書百官表曰內史周官秦因之掌治京師武帝更名曰京兆尹應劭曰河南尹所以治周地秦兼天下置三川守河洛伊地漢更名河南太守也世祖徙都雒陽改爲尹余準切八|䪳:面斜|允:信也|狁:獫狁|馻:馬毛逆|玧:充耳王|𡴞:進也|𧉃:蟲名
QVh思尹;筍:竹萌思尹切九|笋:+俗|𠣬:驚詞|鵻:說文曰祝鳩也|隼:+鷙鳥也說文同上|箰:箰箻以捕鳥|簨:簨虡釋名曰所以懸鐘鼓者橫曰簨簨峻也在上高峻也縱曰虡虡舉也在旁舉簨也|𥯗:+上同|𣕍:+亦同又作栒
cgh而允〈兗〉;蝡:淮南子曰蠉飛蝡動或作蠕而允切又而兗切一
YVh尺尹;蠢:出也爾雅云作也動也蠢不愻也尺尹切九|𢧨:+古文|䐏:肥也|踳:踳駮相乖舛也|惷:惷惷擾動皃|𦚧:漢𦚧䏰縣名在巴東郡地下濕多𦚧䏰蟲䏰音閏|偆:厚也富也又癡準切|僢:相背|𢾎:亂也
bVh食尹;盾:于盾也食尹切四|揗:摩也|吮:吮舐也|楯:欄檻
KVh癡準;偆:厚也富也癡準切一
IVh力準;耣:束也力準切二|𦓾:+上同
cVh而尹;𣯍:毛聚而尹切一
eVp丘尹;𦃢:束縛丘尹切一
eVV弃忍;螼:蚯蚓也爾雅曰螼蚓蜸蚕弃忍切三|𤿳:皮厚皃|𧼒:行皃又去刃切
aVh式允;賰:賱賰富有式允切一
iVZ興腎;脪:腫起興腎切二|㾙:+上同
UWR鉏紖;濜:濜溳水勢鉏紖切一
JVR珍忍;屒:重脣黏好說文伏皃一曰屋宇珍忍切一
#吻
DXN武粉;吻:口吻武粉切七|𦝮:+上同|刎:刎頸|抆:拭也|伆:離也又武弗切|勽:覆也|𦮶:蘠𦮶
AXN方吻;粉:博物志曰燒鉛成胡粉又曰紂作粉方吻切三|黺:黺綵文|扮:扮動又握也又房吻切
CXN房吻;憤:懣也房吻切十四|𢤬:+上同|扮:握也|㿎:病悶|鼢:字林云地中行鼠百勞所化亦作蚡|蚡:+上同|墳:土膏肥也|魵:鰕又音忿|鱝:鱝魚圓如盤口在腹下尾上有毒|弅:莊子有隱弅之丘也|轒:轒䡝車名|膹:切熟肉也|𢅯:盛穀囊滿而裂也|坌:說文曰塵也一曰大防也又步寸切
BXN敷粉;忿:怒也敷粉切又敷問切二|魵:鰕別名
hXt於粉;惲:謀也議也亦厚重也於粉切十|薀:藏也說文曰積也春秋傳曰薀利生孽俗作蘊|蘊:+俗|韞:韞櫝|縕:枲麻|褞:褞袿|䡝:轒䡝車名|賱:賱賰富也|醞:釀也又於問切|搵:沒也
gXt魚吻;齳:無齒魚吻切五|𪘩:+上同|夽:大也|喗:大口|𧼐:走皃又丘粉切
kXt云粉;抎:有所失云粉切四|䫟:說文曰面色顛䫟皃|𪏚:+上同|𤸫:病也
eXt丘粉;𧼐:走皃丘粉切二|𦄐:左傳云羅無勇𦄐之束縛也
#隱
hYd於謹;隱:藏也痛也私也安也定也又微也又姓吳志有廷尉左監隱蕃於謹切十一|磤:雷聲|𤻘:𤻘胗皮外小起|䌥:縫衣相著|㥯:謹也|櫽:說文括也|嶾:嶾嶙山皃|𠃊:匿也|㶏:水名|㐆:歸依也又於機切|𨏈:車聲
dYd居隱;謹:絜也慎也居隱切十一|𪏴:黏皃|㹏:牛馴也|槿:木槿櫬也又名蕣一曰朝華一曰日及亦曰王蒸又曰赤堇|堇:菜也說文作𡏳黏土也又音芹|𡏳:+上同|漌:清也|慬:愨也|卺〈巹〉:以瓢爲酒器婚禮用之也|𧯷:+上同|菦:菜名
SWR仄謹;𧤛:角齊多皃仄謹切二|𣓀:草木眾齊本又音臻
eYd丘謹;赾:跛行皃丘謹切一
fYd其謹;近:迫也幾也其謹切又其靳切二|瘽:病也
TWR初謹;齔:毀齒俗作齔初謹切又初靳切一
gYd牛謹;听:笑皃牛謹切一
iYd休謹;䘆:蚯蚓也吳楚呼爲寒䘆休謹切又虛偃切一
#阮
gZt虞遠;阮:姓出陳留虞遠切三|𡯱:小皃|邧:秦邑名說文云鄭邑也
kZt雲阮;遠:遙遠也雲阮切二|𩔃:面不正
hZd於幰;偃:偃仰又息也說文僵也又姓左傳舒庸舒鳩並偃姓於幰切十二|㫃:旗旌之旒|䞁:物相當也|鶠:鳳也|郾:縣名|褗:衣領|堰:壅水也又於建切|匽:隱也|鄢:鄭楚地名左傳曰晉侯鄭伯戰于鄢陵|鼴:鼴鼠似鼠形大如牛好偃河而飲水也|蝘:蜩螗別名又爾雅云蝘蜓守宮也|鰋:魚名
dZd居偃;湕:水名居偃切五|𥍹:矛|㔓:㔓吃語也|揵:難也舉也|蹇:跛也屯難也亦封名又居免切
fZd其偃;寋:女字亦姓今蜀人有之其偃切四|楗:關楗|鍵:+上同|𠐻:倨也
eZd去偃;𧥛:言言脣急皃去偃切一
gZd語偃;𧥜:語偃切四|巘:山形如甑|𪗛:露齒說文作𪗙|屵:屵磭又大脣皃磭音綽
iZd虛偃;幰:蒼頡篇云帛張車上爲幰虛偃切四|攇:手約物|䘆:寒䘆又休謹切|䜢:䜢摶很戾
DZN無遠;晚:暮也無遠切七|娩:婉娩媚也又忙件切|挽:引也|輓:+上同|㿸:皮脫也又無願切|㝃:子母相解又音免|脕:色肥澤又音曼
AZN府遠;反:反覆又不順也府遠切六|䡊:車耳曰䡊|阪:大陂不平|坂:+上同|返:還也|橎:木名
fZt求晚;𧯦:黃豆求晚切四|圈:獸闌又姓後漢末圈稱字幼舉撰陳留風俗傳圈氏本氏於其國又其卷切|菌:蕈也又求敏切|卷:風俗傳云陳留太守琅邪徐焉改圈姓卷氏字異音同
hZt於阮;婉:順也美也於阮切二十|菀:紫菀藥名又菀茂木也又姓左傳齊大夫菀何忌|苑:園苑白虎通云苑囿所以在東方者謂養萬物東方物所生也|踠:體屈|蜿:蜿蟺蚯蚓也亦作䖤|䖤:+上同|畹:田三十畝王逸云十二畝也|琬:珪也|宛:宛然說文曰屈艸自覆也又姓左傳有宛春|惌:+說文同上又周禮注云惌小孔貌|倇:歡樂|䩩:䩩量物之䩩也|𩌑:+上同|䘼:襪也又安院切|夗:臥轉皃|𩎺:䩩底履名|晼:晼晚|睕:乖也又無嫵媚也|𤗍:船𤗍木|䛄:慰也又於万切
eZt去阮;䅚:相近皃去阮切六|綣:繾綣謹慎|虇:蘆筍|裷:幭也|䊎:粉也|𪐂:黏𪐂
iZt況晚;暅:日氣況晚切又古鄧切七|䁔:大目|咺:兒啼不止朝鮮云也|烜:光明|愃:寬心又音宣|𧡩:大視|諼:詐也
CZN扶晚;飯:餐飯禮云三飯是扶晚切又扶万切四|軬:車軬|笲:竹器所以盛棗脩|䪻:無髮
#混
jah胡本;混:混流一曰混沌陰陽未分胡本切十六|鯶:魚名|渾:渾元又戶昆切|緷:大束|焜:火光說文煌也|倱:倱伅四凶之一春秋作混沌|棍:木名|䫟:頭面形圓也|睔:大目又古悶切|㮯:木未破也|䚠:角圓皃亦上司|𨡫:醨酒相沃|䧰:大阜|掍:掍同|睴:視皃|煇:煇煌光又音揮
BaB普本;翉:飛起又走也普本切一
Oah倉本;忖:思也倉本切三|𢩭:截也|刌:細切又割也
AaB布忖;本:本末又始也下也舊也說文曰木下曰本从木一在其下俗作夲夲自音叨布忖切六|畚:草器|𤲙:+上同|笨:竹裏又蒲本切|㡷:戎姓|苯:苯䔿草叢生也
Qah蘇本;損:減也傷也蘇本切四|㾕:㾕㾊惡寒|䐣:臏屬|𦠆:切熟肉更煑也
Nah兹損;𠟃:𠟃減也兹損切六|撙:挫趨禮曰恭敬撙節鄭玄云撙猶趨也|噂:噂𠴲|譐:+上同|䔿:草叢生皃|僔:眾也
hah烏本;穩:治穀聚亦安穩烏本切三|𡁋:𡁋喗小口|㒚:㒚隱
Gah徒損;囤:小廩也徒損切九|𥫱:籧也說文篅也|盾:趙盾人名|沌:混沌|坉:+上同|庉:樓牆|遁:遁逃又音鈍|遯:+上同|㡒:貯也又張倫丈旬二切
Pah才本;鱒:說文曰赤目魚也才本切一
dah古本;𩩌:禹父名亦作𩨬尚書本作鯀古本切十二|㯻:大束|袞:天子服也|緄:帶也|鯀:說文曰魚也亦作鮌|輥:車轂齊等皃|緷:爾雅云百羽也|蔉:穮蔉壅養苗|惃:惃亂|丨:上下相通|䃂:高聲聲|錕:車釭
Fah他袞;畽:畽㤻行無廉隅他袞切四|𤊯:𤊯肉|吨:氣相衝也|黗:黑狀
eah苦本;閫:閫門限也苦本切十|壼:居也廣也又宮中道|𡈋:篆文|稛〈稇〉:成熟又縛衣也|裍:成就|悃:至誠|𩑔:禿頭又口沒切|梱:樴弋門橛|齫:齫齦齒起皃|硱:硱碖石落皃
Iah盧本;㤻:畽㤻行無廉隅盧本切四|惀:心思求曉事|睔:睔目皃|碖:碅碖石落皃
CaB蒲本;獖:守犬蒲本切四|笨:竹裏又晉書有兗州四伯豫章太守史疇以大肥爲笨伯|㨧〈㮥〉:車弓|体:麤皃又劣也
DaB模本;懣:愁悶也模本切又亡頓莫旱二切一
Hah乃本;㶧:㶧熱也乃本切一
iah虛本;𦃕:結也虛本切二|惛:惛懣忽疾皃也
#很
jbR胡墾;很:佷戾也俗作狠胡墾切二|䓳:䓳似蓍花青白
ebR康很;墾:力也耕也治也康很切四|懇:懇惻至誠也又信也|齦:齧也|豤:豕食皃
dbR古很;䫀:頰後古很切二|詪:難語皃
#旱
jcR胡笴;旱:不雨胡笴切五|𡷛:山名在南鄭|皔:白皃|䓍:草名|䛞:大言
EcR多旱;亶:信也厚也大也多穀也穀也俗作亶多旱切又遮連切八|𤺺:病也|嬗:媛也|笪:持也笞也又都達切|疸:黃病又音旦|觛:小觶又音但|狚:獦狚獸|担:笞也
FcR他但;坦:平也安也明也寬也他但切二|䦔:闑也門傍之橛所以止扉
QcR蘇旱;散:散誕說文作𢽳分離也又作𢿱雜肉也今通作散又姓史記文王四犮散宜生蘇旱切又蘇汗切十一|𢽳:-|𢿱:+並見上注|饊:饊飯|糤:+上同|鏾:弩牙緩也|繖:繖絲綾今作繖蓋字|䉈:䈓䉈桃支竹名|傘:傘蓋|𩀼:鳥形又思盰切|𢄻:𢄻扇
GcR徒旱;但:語辝又空也徒也徒旱切十一|蜑:南方夷|袒:袒裼又除鴈切|襢:+上同又陟扇切|誕:大也育也欺也信也|潬:水中沙出爲潬今河陽縣南有中潬城|䩥:馬帶|繵:束𦝫大帶|膻:說文云肉膻也|僤:疾也本音去聲|觛:小觶
PcR藏旱;瓚:圭瓚秬鬯宗廟之盛禮周禮云祼圭有瓚以肆先王藏旱切三|趲:散走又則捍切|禶:祭
dcR古旱;笴:箭笴古旱切又音哿十二|簳:+上同|皯:面黑又工旦切|䵟:+上同|𤿊:亦同|稈:禾莖|秆:+上同|仠:仠長|𦼮:眾草莖也|矸:矸擊|衦:摩展衣也又音幹|𥾍:+上同
IcR落旱;嬾:惰也落旱切五|懶:+俗|𥽭:飯相著也|𥻂:+上同|讕:謾讕
ecR空旱;侃:強直也又侃侃和樂皃空旱切二|衎:信言又苦汗切
icR呼旱;䍐:希也亦鳥網又姓左傳鄭有䍐氏出自穆公以王父字爲氏代爲卿大夫又羌複姓有䍐幵氏說文作䍐或作罕呼旱切七|蔊:菜味辛也|厂:說文云山石之崖巖|灘:水濡而乾說文呼旰他丹二切|暵:日乾也又呼旴切|焊:火乾也|熯:+上同又呼旰人善二切
NcR作旱;䰖:髮皃作旱切一
#緩
jch胡管;緩:舒也又虜姓緩稽氏後改爲緩氏胡管切十四|澣:濯也|浣:+上同|綄:候風羽出淮南子又音桓|㬊:玉篇云㬊明也又姓晉有西中郎將㬊清|䁔:目𦙼說文火晚切大目也|𧡩:大視|梡:木名又束薪又苦管切|棵:斷木|𧶲:䝹𧶲小有財也|鰀:魚名|嵈:山名|晥:縣名|䈠:𥮩䈠簡也
Ech都管;短:促也不長也都管切四|𢭃:+上同|斷:斷絕俗作𣂾断又徒管切|𢷖:轉籰
hch烏管;椀:器物烏管切三|盌:+上同|䝹:䝹𧶲小有財
Fch吐緩;疃:說文曰禽獸所踐處也詩曰町疃鹿場毛萇云町疃鹿迹也亦作畽吐緩切四|𤲫:+上同|瘓:痶瘓皃|䠪:行速
Qch蘇管;算:物之數也蘇管切三|匴:器也冠箱也|篹:籮屬
dch古滿;管:樂器也主當也又姓出平原周文王子管叔之後古滿切十二|筦:+上同|脘:胃府|輨:車轂端鐵|盥:洗也又公玩切|琯:玉管又姓|痯:病也郭璞云賢人失志懷憂病也|悹:悹悹憂無告也詩傳云悹悹無所依又音灌|䩪:車鞁具也|錧:車具|䗆:雨下蟲名|䘾:袴襱也
Ich盧管;卵:說文曰凡物無乳者卵生盧管切一
ech苦管;款:誠也叩也至也重也愛也苦管切八|歀:+上同|欵:+俗|窾:空也|䥗:䥗縫|梡:虞俎名形有足如案|棵:斷木也|䲌:魚名
Hch乃管;煗:說文曰溫也乃管切七|㬉:+上同|暖:亦同|煖:+火氣亦上同又音暄|餪:女嫁三日送食曰餪|渜:湯也|稬:方言云沛國呼稻也
Nch作管;纂:集也作管切八|䂎:鋋也又子筭切|纘:繼也|儹:聚也|籫:竹器|酇:五百家也又五鄉爲酇周禮曰四里爲酇五酇爲鄙又子旰切|繤:繤組本亦作纂|𦆈:+古文
CcB蒲旱;伴:侶也依也蒲旱切三|㚘:說文云並行也从兩夫輦字从此|拌:弃也又音潘
DcB莫旱;滿:盈也充也亦姓出山陽風俗通荊蠻有瞞氏音舛變爲滿魏有滿寵莫旱切五|懣:煩悶|𢟮:+古文|𥲈:竹器|鏋:金精
AcB博管;粄:屑米餅也博管切五|䉽:-|䬳:+並上同|瓪:牝瓦也又音板|昄:均大也又扶板布綰二切
PKh辝（辭）纂｟短｠〈矩〉;鄹:字林云亭名在新豐辝纂切一
Gch徒管;斷:絕也徒管切三|𩏇:履後帖也|緞:+上同
HcR奴但;攤:按也奴但切一
BcB普伴;坢:平坦坢也普伴切二|𧺾:走皃
#潸
VdR數板;潸:淚下皃數板切又音刪一
hdh烏板;綰:繫也烏板切一
AdB布綰;版:說文判也布綰切六|板:+上同|蝂:蝂蝜蟲|瓪:瓪瓦|昄:大也又扶板切|鈑:鉼金
SdR側板;䩆:䩆𩈶面皺側板切三|拃:拃摸|䎒:鷙飛
MdR奴板;赧:慙而面赤俗作𧹞奴板切四|𩈶:䩆𩈶|㫱:溫濕|戁:悚懼又音蹨
jdR下赧;僩:武猛皃一曰寬大下赧切又音簡五|憪:寬大|𤡥:猛也|捍:捍摌搖動|橌:大木也
jdh戶板;睆:大目也戶板切七|睅:目出皃|𪍺:黃蒸子玉篇餅也|鯇:魚名又胡本切|䴷:䴷子麥麴類|皖:明星|莞:莞爾而笑
CdB扶板;阪:破別名扶板切又音返三|昄:大也又音板|魬:魚名
DdB武板;矕:視皃武板切二|𦺖:草可染子可食
UdR士板;𪘪:𪘪𪗙齒不正士板切二|䗃:蟲名
gdR五板;𪗙:五板切一
TdR初板;㹽:齧也初板切一
BdB普板;眅:目中白皃普板切一
Udh雛鯇;撰:撰述雛鯇切二|饌:盤饌
#產
VeR所簡;產:生也又大籥似笛三孔而短又姓何氏姓苑云彭城人所簡切十|簅:大籥或從竹|摌:以手㧡物|㹌:畜㹌畜牲|嵼:𡾰嵼|汕:魚浮水上|滻:水名在京兆|㦃:全德又音剗|䊲:粟䊲|𩥮:馬名
jeR胡簡;限:度也齊也界也胡簡切五|硍:石聲|䁂:𥇅䁂無畏視也|㹂:牛㹂很不從牽|䦘:門閾又作𢩆𣐻並俗本只作限
DeB武簡;𥇅:武簡切一
deR古限;簡:札也牒也略也釋名曰簡閒也編之扁扁有閒也又姓左氏傳魯大夫簡叔蜀志簡雍傳云本幽州人姓耿後音訛改爲簡古限切七|㶕:洗米|僩:武猛皃|𧟉:帬襵|柬:分別也一曰縣名在新寧說文本从束八八分也|暕:陰旦日明|揀:揀擇
TeR初限;剗:剗削初限切六|鏟:平木器也|丳:炙肉丳也|羼:說文曰羊相廁也从羴在尸下尸屋也一曰相出前也|㦃:全德|䐮:皮䐮
UeR士限;棧:閣也亦姓魏有任城棧潛士限切八|㟞:山皃也|嶘:+上同|轏:車名士所乘也|孱:孱陵古縣名在武陵又士連切|𠊩:書傳云見也說文云具也|輚:埤蒼云臥車也亦兵車又儀禮注云載柩車也|虥:虎竊毛謂之虥
geR五限;眼:眼目也五限切一
SeR阻限;醆:酒濁微清阻限切四|琖:玉琖小杯|盞:-|𧣴:+並上同
Teh初綰;㦃:全德初綰切二|䊲:䃺粟
eeR起限;齦:齒聲起限切一
#銑
QfR蘇典;銑:說文曰金之澤者一曰小鑿一曰鐘兩角謂之銑蘇典切十一|洗:姑洗律名|跣:跣足|毨:書曰鳥獸毛毨傳云毨理也毛更生整理|姺:古國名|燹:字統云野火也|箲:洗帚飯具|筅:+上同|㭠:棗木|𦭶:草名|𩶤:魚名
FfR他典;腆:厚也善也忘也至也他典切十五|痶:痶瘓病也|圢:坦也|淟:淟涊熱風|町:町疃鹿迹|𤲖:+上同|錪:小釜|靦:面慙|㥏:說文曰青徐謂慙曰㥏|琠:玉名|蚕:爾雅曰螼蚓蜸蚕郭璞云即䖤蟺也江東呼寒蚓|䠄:行跡|𨆁:行皃|賟:賟富|晪:玉篇云明也
EfR多殄;典:主也常也法也經也又姓魏志有典韋多殄切五|蕇:葶藶|䫀:頰後也又古很切|錪:小釜又他典切|𥮏:大篋
hfR於殄;蝘:蝘蜓於殄切五|躽:身向前也|𥈔:視也|宴:安也又烏見切|嬿:嬿婉又烏見切
GfR徒典;殄:絕也俗作𣧠徒典切三|蜓:蝘蜓一名守宮博物志云以器養之食以朱沙體盡赤重七斤擣萬杵以點女人體終身不滅婬則點滅故号守宮漢武試之驗也又音廷|跈:蹈也
dfR古典;繭:蠶繭古典切十三|絸:+古文|蠒:+俗|𥀹:皮起|趼:+上同|𢆞:小束|𡘸:+俗|垷:塗泥又大坂在隴西|筧:以竹通水|襺:纊著衣也|𢺃:拭面|挸:+上同|𢹕:+古文
jfR胡典;峴:峻嶺胡典切十三|臔:肉急|哯:小兒歐乳也又不顧而吐|晛:日出好皃又乃見切|垷:又古典切|蜆:爾雅曰蜆縊女郭璞云小黑蟲赤頭喜自經死故曰縊女|俔:譬喻又苦甸切|顈:顈綴|䵤:黑皃|睍:小目皃|詪:爭語|㦓:意難|嫢:細𦝫皃
ifR呼典;顯:明也著也光也覿也又姓風俗通云有顯甫爲周卿呼典切五|韅:在背曰韅在胷曰靷在腹曰鞅在足曰絆|蜆:小蛤|抮:引戾|𣊡:眾明也微妙也從日中見絲今作㬎又五合切
DfB彌殄;㨠:塗也彌殄切四|芇:相當也又亡弦切|丏:不見也|眄:斜視又亡見切
HfR乃殄;撚:以指撚物乃殄切四|涊:淟涊|蹨:蹂蹨又而善切|跈:蹈也
AfB方典;編:編綃方典切一曰次第也又卑連切十一|匾:匾㔸薄也㔸湯奚切|緶:褰裳|𦄒:+上同|萹:萹茿草|𥣰:豆名|𥤓:+上同|惼:愝惼性狹|碥:乘車石也|扁:扁署門戶|糄:燒稻作米
jfh胡畎;泫:露光又泫然涕流皃胡畎切十四|鉉:鼎耳說文云舉鼎也|琄:玉皃|贙:獸名似犬多力出西海一曰對爭也到一虎者非也|埍:女牢也亦作妶又姑泫切|繯:韋昭云繯繫也|䀏:說文云目搖也|𥌭:目童子又胡涓切|鞙:䪎鞙刀鞘也說文曰大車縛軶靼也|䩙:+上同|䧎:坑也|𨊼:車𨊼|𩉥:+上同|䭴:馬一歲也
dfh姑泫;𡿨:水小流也深尺廣尺曰𡿨姑泫切八|畎:+上同|𤰝:+古文|詃:誘也|埍:女牢|罥:挂也|羂:+上同|汱:爾雅云墜也又伏水也
CfB薄泫;辮:說文交也薄泫切七|艑:吳船|𪉱:蜀人呼鹽|扁:姓也盧醫扁鵲是也又方典切|㲢:㲢㲫毛領|𤻶:骨風病也|𩩯:骨𩩯生皃
efh苦泫;犬:狗有懸蹄者曰犬廣雅云殷虞晉獒楚獚韓獹宋㹱並良犬苦泫切一
efR牽繭;𥧬:不動牽繭切四|豤:齧也|䵖:穄別名也|蜸:蜸蚕蚯蚓
gfR研峴;齞:開口見齒研峴切一
#獮
QgR息淺;獮:秋獵曰獮獮殺也息淺切十三|𤣗:-|𥙮:+並上同見說文|鮮:少也|尠:+俗|尟:寡也|癬:癬疥|燹:字林云逆燒又音銑|𤐨:+上同|䉳:𥳐䉳今人戶版籍也𥳐音牽上聲|廯:屋廩|𧕇:𧕇蛇|蘚:苔蘚
lgR以淺;演:廣也亦水長流皃以淺切八|衍:達也亦姓字統云水朝宗於海故從水行|縯:長也|蔩:土瓜|𠻤:大笑|戭:長槍又檮戭八元名|𧍢:螾𧍢蟲|𧊔:+上同
PgR慈演;踐:蹋踐慈演切七|諓:諂也|餞:酒食送人又疾箭切|俴:淺也|𤷃:小痒|𧗸:蹈也|㣤:跡也
JgR知演;展:舒也整也審也適也說文作㞡轉也又姓魯孝公之子子展之後知演切十|㞡:+上同|搌:束縛又丑善切|皽:皮寬|輾:輾轉又虜複姓後魏輾遟氏改爲展氏|紾:轉繩也又音軫|㠭:極巧視之又視戰切|㜊:㜊奵好皃|𧎰:蟲名|襢:襢衣皃
XgR旨善;𦗢:耳門旨善切十七|𠟉:以槌去牛勢|樿:木名禮記用之爲杓|𩕊:說文曰倨視人也|饘:饘粥又音氊|醆:杯又側限切|皽:皮寬又知善切|燀:又昌善切義見下文|䆄:束也|䡀:裸形無可蔽也|䁴:說文曰視而不止|𥊳:+上同|橏:木瘤|䎒:武也又鷙鳥擊勢也|㔊:擊也|𨭖:+上同|嫸:偏忮
MgR尼展;趁:踐也亦作蹍尼展切三|𨋚:車轢物或作碾|㞋:柔弱
OgR士〈七〉演;淺:不深也士演切一
YgR昌善;闡:大也明也開也昌善切九|燀:說文曰炊也春秋傳曰燀之以薪又然也又章善切|繟:寬綽|䵐:黃色|幝:車敝詩曰檀車幝幝|𨼒:魯邑名|灛:汶水爲灛|嘽:寬綽名也樂記曰其聲嘽以緩|𦆀:偏緩又徐翦切
egV去演;遣:送也縱也去演切八|繾:繾綣不相離皃又黏也|䭤:乾麪餅也|𥳐:𥳐䉳戶籍|㹂:牛很不從引也|𠳋:小塊說文作𨺫|𨺫:+見上注|𩝡:黏也
dgZ九輦|dgV九輦〖善〗;蹇:a跛也屯難也又姓秦有蹇叔九輦切十一|謇:a吃又止言|搴:a取也|𢷘:a+上同|𠐻:a偃𠐻傲也|𢵈:b𢵈搌醜長皃搌丑輦切|𦂇:a𦂇縮|𡾰:a𡾰嵼山屈曲也|藆:a爾雅釋草云藆藅|𩽜:a魚名|䙭:a䙭袴
ZgR常演;善:良也大也佳也說文作譱吉也又姓呂氏春秋云善卷堯師常演切十一|譱:+見上注篆文又作善|墠:除地曰墠|鱓:魚名異苑云死人髮化也|蟺:䖤蟺蚯蚓|單:單父縣名亦姓出周卿士單襄公之後又丹禪二音|僐:說文云作姿也|鄯:州名本漢之破羌縣地屬金城郡後魏孝昌二年置鄯州又鄯善西域國也本名樓蘭又音擅|墡:白土|磰:+上同|𪍶:大麥新熟作𪍶𪍦也
NgR即淺;翦:截也齊也殺也勤也俗作剪即淺切十四|剪:+俗|揃:揃搣|戩:福祥也|錢:錢銚田器|媊:明星又子離切|俴:淺也|帴:狹也|𦺍:王蔧草名|鬋:髮垂|𥰸:𥰸䉳|𥳟:竹名|籛:竹名又姓|㨵:切也俗
cgR人善;蹨:踐也續也執也緊也人善切五|橪:橪棗木名|戁:懼也又音赧|熯:乾皃又音漢又音䍐|㒄:意脃也又式善切
RgR徐翦;𦆀:緩也徐翦切一
IgR力展;輦:人步挽車又姓出何氏姓苑力展切九|𪍦:大麥𪍶𪍦|𤑿:小然火也|璉:瑚璉|鄻:地名在周|僆:畜雙生子|摙:擔運物也|蓮:蓮芍縣名在馮翊又音憐|膦:膦輭無力
ggZ魚蹇;齴:齒露魚蹇切七|巘:山峯|遃:行皃|嵃:㟞嵃山形|讞:議獄|𤫣:玉甑|甗:器也周禮曰陶人爲甗甗無底甑也
fgZ其輦;件:分次也其輦切四|𡾰:𡾰嵼又音蹇|鍵:管籥|鑳:+上同
CgJ符蹇;辯:別也理也慧也說文治也符蹇切五|𧦪:+俗|辡:罪人相訟又方免切|辨:別也說文判也又蒲莧切|諞:巧佞言也又符沔切
DgF彌兗;緬:遠也說文曰微絲也彌兗切十|沔:漢水別名亦州名春秋鄖國之地戰國時屬楚秦屬南郡武德初平朱粲置沔州|汅:+俗|湎:沈湎|愐:思也|黽:黽池縣名在河南府俗作澠又忘忍切|𩋠:靼靻名也|偭:背也|勔:勉也|𢃮:幕出玉篇
AgF方緬;褊:衣急方緬切二|㦚:憂也亦曰急也
Ngh子兗;臇:𦞦少汁也子兗切三|𤎱:+上同|𧕣:蟲食
Pgh徂兗;雋:鳥肥也又姓漢有雋不疑徂兗切五|隽:+俗|𤺻:大痒|吮:欶也又徐兗切|𦼱:葍𦼱菜名
AgJ方免;辡:罪人相訟方免切又符蹇切四|䁵:蔽目說文曰兒初生蔽目者|覸:視皃|鴘:埤蒼云鷹鷂二年色又云人姓
lgh以轉;兗:州名尚書禹貢曰濟河惟兗州武王封周公於曲阜爲魯公秦爲薛郡後魏置南兗州於譙城又置西兗州於定陶城隋改爲魯州武德初平徐圓朗復爲兗州又姓出姓苑以轉切十|渷:濟水別名出王屋山|沇:+上同|𢯻:動也|抁:+上同|𦳆:草名|馻:馬逆毛|㕣:山澗泥也|𦁙:紖𦁙|𩘍:小風
Igh力兗;臠:肉臠說文曰臞也一曰切肉也力兗切四|孌:美好|𡡗:從也|脟:割也
Jgh陟兗;轉:動也運也陟兗切二|𣓧:乘𣓧
dgp居轉;卷:卷舒說文曰膝曲也居轉切六|菤:菤耳苓耳|韏:爾雅曰革中辨謂之韏車上所用皮也辨音片|𨹵:河東安邑聚名|捲:捲衣|埢:冢土
fgp渠篆;圈:說文曰養畜閑也渠篆切又求晚切三|蔨:爾雅曰蔨鹿𧆑|𦳆:耎也
cgh而兗;輭:柔也或从需餘同而兗切十七|軟:+俗|蝡:蟲動|㮕:紅藍又㮕棗也|䓴:木耳|碝:碝石次玉|瑌:+上同|愞:愞弱又奴亂反|腝:脚疾|䞂:䞂小有財物也|耎:說文曰稍前大也|𢘎:弱皃|㞋:弱也又尼展切|偄:敬也亦弱也|㼱:柔韋又作𠤦見經典|𤲬:城下田也|緛:衣縫也
Ygh昌兗;舛:剝也說文曰對臥也從夂㐄相背夂中几切㐄口瓦切昌兗切四|喘:喘息說文曰疾息也|荈:茗草名|㪜:揣也又初委切
Zgh市兗;膞:切肉市兗切七|腨:腨腸|鄟:地名|𡭐:說文曰小巵有蓋也|歂:口氣引皃|踹:腳跟|𦺲:草名生處無魚
Lgh持兗;篆:篆書持兗切七|瑑:璧上文也|沌:水名在江夏又徒混切|摶:周禮百羽爲摶十摶爲緷緷音渾又音鮌|𦁆:+上同亦作縳|䧘:道邊埤也|堟:耕土卷也
Xgh旨兗;剸:細割旨兗切九|剬:+上同|孨:孤露可憐說文曰謹也又莊眷切|鱄:魚名美也出洞庭湖|竱:等也|膞:切肉又市兗切|𨷱:開閉門利|𡇰:囚刑固出古今音字|𦓝:小巵也又之累切
Qgh思兗;選:擇也思兗切又思絹切又思管切三|𦌔:罟也|𥶷:竹緣
Ugh士免;撰:述也定也持也士免切五|僎:具也數也持也又子倫切|𩔊:具也見也|𩻝:魚名|譔:專教也又音詮
fgl狂兗;蜎:爾雅曰蜎蠉郭璞云井中小蛣蟩赤蟲一名孑孒又姓漢藝文志有老子弟子楚人蜎淵著蜎子十三篇狂兗切一
igl香兗;蠉:香兗切二|𧾣:走皃
CgF符善;楩:木名符善切又父綿切四|㦚:急也|諞:巧言|扁:又辮篇二音
DgJ亡辨;免:止也黜也脫也去也亦姓左傳衛大夫免餘亡辨切八|娩:婉娩媚也又音挽|勉:勖也勸也強也|俛:俯俛|鮸:魚名|㝃:生子㝃身|冕:冠冕|絻:+上同又音問
KgR丑善;搌:搌𢵈丑善切七|𨩪:𨩪物令長|𣃘:旌旗柱又幢徵二音|蕆:備也一曰去貨|𧈪:伸行|㢟:安步行也又丑延切|䩶:驂具又丑井切
BgJ被〈披〉免;鴘:埤蒼云鷹鷂二年色被免切一
agR式善;㒄:說文曰意膬也式善切三|㜣:女恣態又奴見切|䁴:視面色變也
hgZ於蹇;㫃:旌旗之皃於蹇切三|䟍:走也|嫣:長皃
LgR除善;邅:移行除善切一
UgR士免;棧:士免切棚也一
#篠
QhR先鳥;篠:細竹也先鳥切七|筱:+上同|𩵌:魚名|𧩮:誘爲善也又小也|謏:+上同|䃤:黑砥石也又思六切|㩋:打也
dhR古了;皎:月光詩云月出皎兮古了切十二|璬:佩玉|𢅎:行縢𢅎脛布也|䥵:鐵文又呼了切|㿟:白也又匹白切|皦:明也皎也又珠玉白皃|恔:恔憭慧也|繳:纏也又音酌|𨶪〈䰘〉:喪之降殺|晈:光明|䘨:小袴|儌:儌抄
EhR都了;鳥:說文曰長尾禽總名也象形都了切九|𢁕:絹布頭也|㣿:垂心|蔦:樹上寄生|釕:釕鈌帶頭飾出聲譜|扚:扚擊|𧜣:短衣|䄪:禾穗垂皃|𠄏:懸皃
IhR盧鳥;了:慧也訖也盧鳥切十四|蓼:辛菜|瞭:目睛明也|镽:镽𨲭長皃𨲭臣夭切|鄝:地名|繚:繚繞纏也|憭:照察|䑠:玉篇云小船也|爒:火炙|𢄺:拭也|𥗀:𥗀𢁕石垂皃|撩:抉也又力凋切|𤁸:水清又小水也|𧘈:袴也
FhR土了;朓:月行疾出西方土了切三|窱:窈窱深遠皃|䠷:身長皃
ihR馨皛;䥵:鐵文馨皛切四|曉:曙也明也慧也知也|皢:白也|膮:豕羹
hhR烏晈;杳:冥也深也寬也烏晈切十五|窅:深目皃|窈:窈窱深也靜也|偠:偠㒟好皃|騕:騕褭神馬日行千里|𩡻:+上同|𨱧:𨱧䦊長而不勁|葽:爾雅云遠志也|㫏:旗類|鴢:爾雅曰鴢頭鵁郭璞云似鳧腳近尾略不能行又音拗|婹:婹㜵細弱|㫐:合也|䆞:遠也隱也說文冥也|𡧮:說文曰戶樞聲也室之東南隅也|苭:草長
HhR奴鳥;嬲:戲相擾奴鳥切九|嫋:長弱皃|𨲂〈䦊〉:𨱧䦊|㒟:偠㒟|褭:騕褭|嬈:苛酷也又擾戲弄也又音遶|㜵:婹㜵|䃵:䃵䂪|𢸣:摘也
jhR胡了;皛:明也胡了切五|㵿:水渺㵿皃|芍:鳧茈草又市若切|𦯪:+上同|𠄔:修續譜云相誑也玉篇音患
GhR徒了;窕:美色曰窕詩注云窈窕幽閒也徒了切八|𤕷:𤕷牀子|𤱩:疁田中穴|誂:弄也俗作挑說文曰相呼誘也|掉:搖尾又動|嬥:嬥嬥往來皃韓詩云嬥歌巴人歌也|挑:挑戰亦弄也輕也|䂽:磽䂽
ehR苦皎;磽:山田亦作䂪苦皎切二|䂪:+上同
NhR子了;湫:湫隘子了切又子攸切五|劋:截也說文絕也|㭂:木忽高也|㡑:凶首飾|𧂈:似薺菜
#小
QiR私兆;小:微也私兆切三|𩵖:魚名|䒕:䒕草遠志也
LiR治小;肈:始也正也敏也長也治小切十一|肁:開也又姓戰國策趙有大夫肁賈|兆:十億曰兆說文分也又姓|趙:少也久也字林云趍也亦州名春秋屬晉秦屬邯鄲郡後魏以廣阿城置殷州至齊改爲趙州又姓本自伯益孫造父善御幸於周穆王賜以趙城因封爲氏簡襄始大列爲諸侯今出天水南陽金城下邳潁川五望|旐:旗旐爾雅曰長尋曰旐郭璞云帛全幅長八尺𥼶名曰龜蛇爲旐旐兆也龜知氣兆之吉凶建之於後察事宜之形兆也|狣:犬有力也|䍮:羊子|鮡:魚名似鮎而大|駣:馬四歲|垗:葬地|𠧞:灼龜坼出文字指歸
XiR之少;沼:池沼之少切三|菬:菬子草|䈃:竹緣
hiZ於兆;夭:屈也於兆切四|殀:歿也|芺:爾雅曰鉤芺郭璞云大如拇指中空莖頭有臺似薊初生可食|仸:仸僑不伸又尪弱皃
KiR丑小;巐:意氣息皃丑小切一
aiR書沼;少:不多也書沼切又式照切三|䒚:草名|𨙹:說文地名
ciR而沼;擾:亂也順也說文作𢹎煩也而沼切七|𢹎:+上同|繞:纏繞又姓左傳秦大夫繞朝|遶:圍遶|嬈:亂也|𤛾:牛馴說文作㹛牛柔謹也|𧳨:爾雅注云即蒙貴也狀如蜼而小紫黑色可畜之健捕鼠亦作猱又諾高切
CiF符少;摽:落也又拊心也字統云合此𦭼符少切八|𢹰:+上同見說文今從票餘同|鰾:魚鰾可作膠|慓:急性|顠:髮白又孚小切|𩮳:+上同|膘:脅前又孚小切|𦭼:𦭼草又零落也
YiR尺沼;𪍑:糗也尺沼切五|麨:+上同|弨:弓反曲又昌招切|楢:赤木名又音猶音酉|眧:弄人眧目也
BiF敷沼;縹:青黃色也敷沼切八|醥:清酒|犥:牛黃白色|顠:髮白|皫:鳥變色也|篻:實中竹名|瞟:埤蒼云一目病|膘:脅前又音𦭼
DiF亡沼;眇:說文曰一目小也亡沼切十|渺:渺㵿水皃|訬:耰也一曰訬獪|𦳥:草細|淼:大水|杪:梢也木末也|秒:禾芒|藐:字書藐遠又亡角切|吵:雉聲|篎:笙管
ZiR市沼;紹:繼也又姓出何氏姓苑市沼切五|綤:+古文|佋:佋介|袑:袴上|䙼:玉篇云見也
diZ居夭;矯:詐也說文曰揉箭箝也又姓左傳晉大夫矯文居夭切十二|鱎:白魚別名|䚩:角長|敽:繫盾也|撟:說文曰舉手也一曰撟擅也|嬌:女字又居喬切|𥃧:目重瞼也|蟜:山海經云野人身有獸文說文曰蟲也又姓後漢有蟜慎字彥仲|譑:多言|𨝰:國名|孂:竦身|蹻:驕也又其虐切
AiJ陂矯;表:明也亦牋表釋名云下言於上曰表說文作𧘝上衣也古者衣裘以毛爲表也又姓出姓苑陂矯切四|𧘝:+上同|𧞧:+古文|䔸:草名
AiF方小;褾:袖端方小切四|𧢄:字林云目有所察|標:標杪木末|㟽:峯頭
CiJ平表;藨:草名可爲席平表切八|𦳤:+上同|殍:餓死又音孚|莩:+上同又音孚|𠬪:物落皃|㰶:歐吐|㹾:獪也|𧴎:似狐善睡
lGh以沼｟小｠〈水〉|liR以沼;鷕:a雉鳴也以沼切又羊水切七|溔:b浩溔大水皃|舀:b說文曰抒臼也|𦥨:b-|抭:b+並上同|𩨴:b肩骨|䁘:b眇䁘目皃
OiR親小;悄:悄悄憂皃親小切三|愀:容色變也|釥:好也又淨
NiR子小;剿:絕也子小切八|劋:+上同出說文|勦:勞也又音巢|漅:水名|𨙹:魯地|𤃭:𥂖酒|膘:又符小切|𢄺:拭也
fiZ巨夭;𨲭:镽𨲭長皃巨夭切一
IiR力小;繚:繚繞力小切九|燎:說文曰放火也左傳曰若火之燎于原|𢻢:長皃|璙:好皃|憭:慧也又音聊|爒:爒炙也|僚:朋也又音平聲|䩍:䩍䩍面白|嫽:嫽嫽好皃
BiJ滂表;麃:蒼頡篇云鳥毛變色本作皫滂表切又經典釋文云徐房表切劉普保切一
hiV於小;闄:隔也於小切一
#巧
ejR苦絞;巧:好也能也善也苦絞切又巧僞苦教切二|䲾:䲾婦鳥案爾雅注云鷦𪃧桃雀也俗呼爲巧婦字俗從鳥
jjR下巧;澩:動水聲下巧切說文音學六|㺒:事露又奴巧切說文音哮|䕧:草根亦竹筍也或作茭又音狡|佼:庸人之敏說文交也又古巧切|䀊:溫器又公巧切|䉰:竹筍
AjB博巧;飽:食多也博巧切三|𩜿:-|𩛁:+並古文
MjR奴巧;㺒:擾亂奴巧切三|撓:撓亂又音蒿|獿:犬驚說文又奴交切
DjB莫飽;卯:辰名爾雅曰太歲在卯曰單閼晉書樂志云正月之辰謂之寅寅津也謂物之津塗二月卯卯茂也言陽氣生而孳茂三月辰辰震也謂時物盡震而長四月巳已起也物至此時畢盡而起五月午午長也大也言物皆長大六月未未味也言時物向成有滋味七月申申身也言時物身體皆成就八月酉酉緧也謂時物皆緧縮也九月戌戌滅也謂時物皆衰滅十月亥亥劾也言陰氣劾殺萬物十一月子子孳也謂陽氣至此更孳生十二月丑丑紐也謂終始之際故以結紐爲名也莫飽切七|戼:篆文|緢:旄也又絲名|泖:水名在吳華亭縣|媌:好皃又莫交切|昴:星名|茆:鳧葵說文作𦯄音柳
djR古巧;絞:縛也又姓出何氏姓苑古巧切十五|狡:狂也猾也疾也健也說文曰少狗也匈奴地有狡犬巨口黑身|佼:女字|攪:手動說文亂也|䕧:郭璞云江東呼藕根亦作茭又下巧切|筊:竹索也又音爻|𢯴:𢯴接物也|鉸:鉸刀|𥂔:器也|姣:妖媚|烄:烄交木然也|𢽻〈𤉧〉:+上同|䀊:濁也說文器也又胡巧切|䉰:竹筍|㽱:腹中急痛俗作㽲
SjR側絞;爪:說文曰丮也覆手曰爪象形丮音戟側絞切八|㕚:+古文說文曰手足甲也|䝖:䝖獠|瑵:玉名說文曰車蓋玉瑵|笊:笊籬|𢁬:𢁬頭|抓:亂搔搯也|𦬔:草也
hjR於絞;拗:手拉於絞切五|鴢:鴢頭鵁似鳧而腳近尾|𢂊:靴韈𢂊亦從革|𥃺〈𥄀〉:深目|狕:獸名
CjB薄巧;鮑:鮑魚又姓出東海泰山河南三望本自夏禹之裔因封爲氏薄巧切四|骲:骨鏃|𡂟:臿地|鞄:柔革名
gjR五巧;齩:齧也五巧切一
UjR士絞;䰫:黠也士絞切二|㑿:㑿㑿長皃出聲譜
TjR初爪;煼:熬也初爪切七|𩱦:-|𤌉:-|炒:+並上同|謅:相弄|𩱈:乾也|吵:聲也本音眇
JjR張絞;䝤:夷別名張絞切又盧晧切二|獠:+上同
VjR山巧;㪢:擊也一云攪也亦作𢾐山巧切一
#晧
jkR胡老;晧:光也明也日出皃也胡老切十六|昊:昊天說文作昦|昦:+上同|暤:明也旰也曜也亦太暤又姓本出武落鍾離山黑穴中者見蜀錄|鎬:鎬京|浩:浩汗大水皃又姓漢青州剌史浩賞又漢複姓魯人浩星公治榖梁|顥:大也又天邊氣說文曰白皃楚詞曰天白顥顥商山四顥白首人也今或作晧|灝:灝溔水勢遠也|鰝:大鰕|夰:說文放也昦奡字從此本音杲|薃:薃侯莎|鄗:光武立處邑名|𨛴:+上同|𧇼:土釜亦作㙱|𥢑:網綴|滈:水名在京兆
CkB薄浩;抱:持也說文曰引取也薄浩切一
IkR盧晧;老:耆老亦姓左傳宋有老佐盧晧切十四|䝤:西南夷名|獠:+上同|轑:車軸|橑:屋橑簷前木一曰蓋骨一曰欄也說文曰椽也|潦:雨水|䕩:乾梅|栳:栲栳柳器也|𣠼:木名|𩔇:廣大皃|恅:愺恅心亂|𡂕:𠹊𡂕無人|䵏:黃色|澇:水名又力到切
FkR他浩;討:治也誅也他浩切三|套:長也|槄:山楸又他刀切
GkR徒晧;道:理也路也直也眾妙皆道也說文曰所行道也一達謂之道徒晧切七|衟:-|𡬹:+並古文|稻:秔稻禮記曰凡祭宗廟之禮稻曰嘉蔬又姓何氏姓苑云今晉陵人|駣:馬四歲又音兆|䆃:禾一莖六穗也出字林|𨱵:镺𨱵長皃又奴晧切
HkR奴晧;堖:頭堖奴晧切九|腦:+上同或從□餘同|𠜶:亦同出同禮|惱:懊惱|碯:碼碯寶石|𨱵:镺𨱵長皃|㺁:雌狢|𧳦:+上同|㛴:相㛴亂也說文曰有所恨痛也
QkR蘇老;㛮:兄㛮蘇老切七|嫂:+上同|㛐:+俗|燥:乾燥|埽:埽除|掃:+上同|䕅:蔜䕅草
EkR都晧;倒:仆也都晧切十一|擣:擣築|㨶:+俗|島:說文曰海中往往有山可依止也又音鳥|禂:牲馬祭也|䮻:+上同|檮:說文曰斷木也又音陶|禱:請也求福也|㿒:病也|壔:高土|懤:憂也
OkR采老;草:說文作艸百卉也經典相承作草采老切七|艸:篆文隷變作艹|懆:憂心|慅:+上同|騲:牝馬曰騲|𠹊:𠹊𡂕無人|愺:愺恅心亂
NkR子晧;早:晨也子晧切十二|澡:澡洗|藻:文藻說文同下|薻:水草也|𧎮:齧人跳蟲抱朴子曰𧎮蝨攻君臥不獲安|蚤:+上同又古借爲早暮字|䲃:魚名似鯉雞足|璪:玉名|璅:石次玉者|棗:果名史記曰楚莊王時有所愛馬啖以脯棗漢書曰安邑千樹棗等千戶侯又姓出潁川文士傳云棗氏本姓棘避難改焉|繰:紺色曰繰|繅:雜五綵文
PkR昨早;皁:皁隷又槽屬亦黑繒俗作皂昨早切四|𦯑:𦯑斗櫟子|造:造作又七到切|艁:+艁舟以舟爲橋說文云古文造
dkR古老;暠:明白也古老切十一|𣓌:木名|杲:日出又明白也|稾:禾稈又稾本草刱之本|藁:+俗|夰:說文放也|縞:素也又音告|槀:槀本藥|㚖:大白澤也|菒:乾草|𥓖:女𥓖石似玉
ikR呼晧;好:善也美也呼晧切又呼号切二|𡚽:人姓
DkB武道;蓩:毒草武道切又地名又亡毒切四|䓮:細草叢生|媢:夫妬婦也說文音冒|𠔼:重覆
AkB博抱;寶:珍寶又瑞也符也道也禮記曰地不藏其寶又天寶晉灼云天寶雞頭人身又姓出何氏姓苑博抱切十五|珤:+古文|保:任也安也守也說文作𠈃養也亦姓呂氏春秋云楚有保申爲文王傅|𡥀:+古文|堢:堢障小城|堡:+上同|褓:襁褓|緥:說文曰小兒衣|鴇:鳥名亦作䳈𪁣䳰|葆:草盛皃又羽葆|駂:郭璞云今烏驄|䎂:彩羽|宲:藏也|賲:有也|𠤏:相次也
hkR烏晧;襖:袍襖烏晧切十四|镺:镺𨱵長也|懊:懊惱|䐿:藏肉又烏到切|芺:苦芺|䴠:麋子|媼:女老稱|燠:甚熱又音郁|夭:禮曰不殀夭本又於矯切|㤇:㤇正之皃|郩:邑名|蝹:蟲名如猿常地下食人腦|䯠:藏骨|𪁾:鳥名
ekR苦浩;考:校也成也引也亦瑕釁淮南子云夏后氏之璜不能無考是也又姓出何氏姓苑苦浩切十|攷:+古文|栲:木名山樗也|槀:木枯也說文作槀|祰:禱也說文曰告祭也|洘:水乾|燺:火乾|丂:氣欲舒皃|䯪:䯪𩑤大頭|薧:乾魚周禮曰辨魚物爲鱻薧注云薧乾也亦作槁又薧里字音蒿
gkR五老;𦽀:瓜蔓苗頭五老切二|𩑤:䯪𩑤大頭
#哿
dlR古我;哿:嘉也古我切四|舸:楚以大船曰舸|笴:箭莖也又公旱切|𥰮:筍𥰮出南中
OlR千可;瑳:王色鮮白千可切三|䰈:髮好皃也又昨何切|硰:硰石地名
ElR丁可;嚲:垂下皃丁可切五|䯬:+古文|哆:語聲又昌者切下脣垂皃|癉:勞也又怒也|䫂:醜皃
QlR蘇可;縒:鮮潔皃也蘇可切又楚宜切三|娑:馺娑殿名又蘇哥切|褨:衣長皃
GlR徒可;爹:北方人呼父徒可切九|柁:正舟木也俗從㐌餘同|舵:+上同|陊:下坂皃又落也|袉:裾也|拕:引也|沱:瀢沱沙水往來皃又徒河切|𣵻:+上同|詑:輕也
glR五可;我:己稱又姓我子古賢者著書五可切五|騀:駊騀馬搖頭皃|𩒰:側弁也|㧴:差也|硪:砐硪山高皃
FlR吐可;袉:長舒皃吐可切又徒可切一
IlR來可;㰁:㰁椏樹斜來可切九|𩝢〈𨬅〉:𨬅鈞出異字苑|欏〈攞〉:裂也|砢:磊砢石皃|㦬:㦬𢣗慙也玉篇又作𩉙𩉌|曪:色光明出釋典|𣂞:相擊也亦斫也|剆:+上同|𠻡:𠻡哆脣垂皃
HlR奴可;橠:𣘨橠木盛皃奴可切六|娜:妸娜美皃|㡅:宬也|𢄴:+上同|那:俗言那事本音儺|袲:𧙃袲衣好皃
jlR胡可;荷:負荷也胡可切又戶哥切二|何:+上同
ilR虛我;㰤:大笑虛我切五|㗿:+上同|㪃:擊也|㪋:+上同|𩑸:傾頭皃又音訶
elR枯我;可:許可也又虜複姓三氏周太保王雄賜姓可頻氏梁有河南王可沓振又有可達氏又虜三字姓三氏後魏書可地延氏改爲延氏又并州刺史男可朱渾買奴前燕慕容儁皇后可足渾氏枯我切四|岢:岢嵐鎮在嵐州|軻:轗軻又音珂|坷:坎坷
hlR烏可;𨵌:𨵌砢欲傾皃烏可切七|椏:㰁椏樹斜|𣘨:𣘨橠|妸:妸娜亦作婀|娿:人姓莊子有娿荷甘又音痾|㫊:旌旗㫊皃又猗蟻切|𧙃:𧙃袲
NlR臧可;左:左右也亦姓齊之公族有左右公子後因氏焉又漢複姓二氏左傳宋公子目夷爲左師其後爲氏趙有左師觸龍晉先蔑爲左行其後爲氏漢有御史左行恢臧可切三|㝾:㝿㝾又子賀切|𠂇:戾也說文曰左手也象形
#果
dlh古火;果:果敢又勝也定也剋也亦木實爾雅曰果不熟爲荒俗作菓古火切十一|菓:+見上注|猓:猓然獸名|輠:車脂角又音禍|鐹:刈鉤又古臥切|划:划刈|裹:苞裹又纏也|蜾:蜾蠃蟲也|惈:蒼頡篇果敢作此惈|䴹:餅䴹食|粿:淨米
Elh丁果;埵:土埵丁果切十五|鬌:小兒翦髮爲鬌|挆:稱量|𦀉:冕前垂也|朵:木上垂也|朶:+上同|綞:綞子綾出字林|揣:搖也又初委切|鍺:車鐧|𨹄:小崖|䤪:鈌也|𥠄:禾垂皃又丁官切|㪜:試也又初委切|𩊜:履跟緣也|褍:衣正幅也
Qlh蘇果;鎖:鐵鎖也俗作鏁蘇果切十二|瑣:青瑣漢舊儀曰黃門令日暮入對青瑣丹墀拜名曰夕郎又瑣小皃|溑:水名|葰:葰人縣在上黨又蘇瓦切|䈗:竹名|䵀:說文曰小麥屑之覈|𩹳:魚名|𥔭:小石|䣔:亭名在河南|惢:心疑也又醉隨才捶二切|𢱡:動也|𧴪:貝聲
Glh徒果;墮:落也徒果切又他果切十四|垛:射垛亦作𨹄|𤬾:長沙呼甌也|䅜:小積|𥬲:竹名|𥳔:+上同|𩊜:履跟緣也或作𩎫|䤻:車轄又犁錧出玉篇|憜:嬾憜也說文曰不敬也|惰:+上同|嫷:美也說文曰南楚人謂好曰嫷又吐臥切|鬌:又丁果切|䲊:魚子已生又他果弋水二切|嶞:山高
Flh他果;妥:安也他果切九|嫷:好也|隋:裂肉也又徒果切|䲊:魚子已生|㟎:山長皃|墮:倭墮鬌也又徒果切|橢:器之狹長|𨼰:山皃|鵎:鳥名
DlB亡果;麼:幺麼細小亡果切三|𣋟:𣋟曪日無色|懡:懡㦬人慙
Plh徂果;坐:釋名曰坐挫也骨節挫屈也徂果切二|𡋲:+古文
glh五果;㛂:好皃五果切二|𠂬:木節也亦作𠨳
Ilh郎果;裸:赤體說文曰袒也郎果切九|躶:-|𧝹:-|臝:+並上同|卵:又力管切|瘰:瘰癧病筋結也|𤼠:+上同|蓏:果蓏說文曰木上曰果地上曰蓏應劭云木實曰果草實曰蓏張晏云有核曰果無核曰蓏|蠃:蜾蠃蒲盧郭璞云細𦝫蜂也負螟蛉之子於空木中七日而成其子法言云螟蛉之子殪而逢蜾蠃祝曰類我類我久則肖之
hlh烏果;婐:婐㛂身弱好皃烏果切三|倭:倭墮又烏戈切|𥟿:多也
Hlh奴果;㛂:奴果切二|𢫷:𢫷擿
AlB布火;跛:跛足布火切又彼義切四|簸:簸揚又布箇切|駊:駊騀馬惡行又音叵|㝿:㝿㝾行不正也
BlB普火;叵:不可也普火切四|駊:駊騀|頗:又普波切|𡽠:𡽠峩山皃
jlh胡果;禍:害也胡果切七|𥚁:+上同|夥:楚人云多也|𡖿:+上同|𣄸:說文云逆惡之驚詞|輠:車脂角又音果|𨘌:𨘌過也秦人呼過爲𨘌也
ilh呼果;火:河圖挺左輔曰伏羲禪於伯牛鑽木作火說文曰燬也南方之行炎而上象形呼果切二|邩:玉篇云地名
elh苦果;顆:小頭苦果切三|堁:堀堁塵起也|敤:研理又音課
ClB捕可;爸:父也捕可切一
Olh倉果;脞:書傳云叢脞細碎無大略也倉果切二|䂳:碎石
OlR作｟子｠〈千〉可;硰:硰石地名作可切一
#馬
DnB莫下;馬:說父曰怒也武也象頭髦尾四足之形尚書中候曰稷爲大司馬釋名曰大司馬馬武也大摠武事也亦姓扶風人本自伯益之裔趙奢封馬服君後遂氏焉秦滅趙徙奢孫興於咸陽爲右內史遂爲扶風人又漢複姓五氏漢馬宮本姓馬矢氏功臣表有馬適育溝洫志有諫議大夫乘馬延年何氏姓苑云今西陽人孔子弟子有巫馬期風俗通有白馬氏莫下切七|碼:碼碯石似玉|䣕:郁䣕縣名在犍爲|罵:罵詈又莫霸切|𥧓:穴𥧓在燕野|鷌:異鳥|鰢:魚名
XoR章也;者:語助章也切三|赭:赤土|堵:縣名又姓左傳鄭有堵女父堵狗又音覩
loR羊者;野:田野說文云郊外也羊者切五|壄〈𡐨〉:+古文|也:語助辝之終也|冶:銷也尸子曰蚩尤造九冶又妖冶亦姓左傳衛大夫冶廑|虵:羌複姓有虵咥氏又食遮切嫺都結切
gnR五下;雅:正也嫻雅也說文曰楚烏也一名鸒一名卑居秦謂之雅五下切五|疋:正也待也說文所葅切足也古文以爲詩大雅字又山呂切|庌:廳也說文曰廡也周禮曰夏庌馬|厊:厏厊不合|㿿:酒器
dnR古疋;檟:山楸古疋切十|榎:+上同|嘏:大也福也|假:且也借也非真也說文又作徦至也又姓漢有假倉|叚:說文借也|賈:姓也出河東本自周賈伯之後又音古|斝:玉爵禮記曰夏后氏以醆商以斝周以爵|瘕:久病腹內又古牙切|椵:爾雅曰櫠椵郭璞云柚屬子大如盂皮厚二三寸中似枳食之少味|婽:好也
VnR砂（沙）下;灑:灑水也砂下切一
hnR烏下;啞:不能言也烏下切又乙革切三|瘂:-|𤺘:+並上同
RoR徐野;灺:燭㶳徐野切三|抯:取也|䵦:䵦墁汚也出文字辨疑
jnR胡雅;下:賤也去也後也底也降也胡雅切四|丅:+古文|夏:大也又諸夏亦州名秦屬上郡漢分置朔方郡晉末赫連勃勃於州稱大夏爲後魏所滅置鎮又改爲夏州又胡駕古下二切|廈:廈屋
QoR悉姐;寫:憂也除也程也盡也又轉本曰寫悉姐切四|𣞐:案之別名|瀉:瀉水|𣬕:獸名
Snh𩛠瓦;𡎬:𡎬𡎬好皃𩛠瓦切一
DoF彌也;乜:蕃姓彌也切一
OoR七也;且:語辝七也切又子余切一
inR許下;㗿:大笑許下切三|閜:大裂|襾:說文曰覆也覆覈賈類皆從此
ZoR常者;社:社稷又漢複姓二氏風俗通云齊昌徙居社南因以爲氏何氏姓苑云右扶風有焉又有社比氏常者切三|𥁹:器名|𣝒:宜𣝒善夢神見仙經
enR苦下;跒:跁跒行皃苦下切一
CnB傍下;跁:傍下切三|䇑:短人立也|笆:竹名出蜀又音巴
aoR書冶;捨:釋也書冶切五|舍:+止息亦上同又音赦|騇:牝馬|䬷:䬼飫|𩜉:+上同
NoR兹野;姐:羌人呼母一曰慢也兹野切三|抯:取也又才也切|飷:食無味也
AnB博下;把:持也執也博下切一
jnh胡瓦;踝:足骨也胡瓦切十一|稞:淨榖|𡱏〈䋀〉:青絲履又繩履|𦖍:地名|黊:鮮明黃色|蘳:說文曰黃華又音壞|觟:牝䍧羊生角者又楚冠名|𩸄:魚似鮎也|𢦚:大口又聲說文曰擊踝也|輠:轂頭轉皃|䴹:麴名
dnh古瓦;寡:鰥寡說文少也古瓦切八|冎:剔人肉置其骨|剮:+俗|𣑍:老人柱杖|𠊰:㒀𠊰行皃|𠁥:羊角皃|䈑:䈅䈑收絲具|𧤐:觰𧤐牛角開
gnh五寡;瓦:古史考曰夏時昆吾氏作瓦也五寡切二|邷:衛地
coR人者;若:乾草又般若出釋典又虜複姓二氏周書若干惠傳曰其先與魏俱起以國爲姓後燕錄有步兵校尉若久和人者切又人勺切三|惹:亂心|𠰒:譍聲也
SnR側下;鮓:釋名曰鮓葅也以鹽米釀魚以爲葅側下切五|厏:厏厊不合|謯:謯訝訶皃|𥰭:炭籠也又音鹺|痄:痄瘡不合
JnR都賈;觰:牛角橫都賈切又竹加切一
UnR士下;槎:逆斫木士下切又仕加切二|厏:厏厊
YoR昌者;奲:寬大也昌者切五|㨋:擊也|䰩:醜䰩|哆:脣下垂皃又當可切|撦:裂開
JnR竹下;䋾:䋾䋈相著皃竹下切一
MnR奴下;䋈:奴下切一
enh苦瓦;髁:𦝫骨苦瓦切七|跨:𦝫跨又苦化切|骻:+上同|㡁:㡁衿袍也|銙:帶飾|𢄳:帛衣|㐄:跨步又口化切
Tnh叉瓦;䂳:好雌黃叉瓦切又七火切一
Knh丑寡;䊬:䊬榖南人食之或云茙葵丑寡切一
Vnh沙瓦;葰:葰人縣名沙瓦切三|𧫝:強事言語|傻:傻俏不仁
KnR丑下;奼:嬌奼也丑下切又陟嫁切一
InR盧下;藞:玉篇云藞槎泥不熟皃盧下切一
#養
lpR餘兩;養:育也樂也飾也字從羊食又姓孝子傳有養奮餘兩切七|痒:皮痒|癢:+上同|瀁:滉瀁水皃|蝆:蟻名說文曰搔蝆也|勨:勉也又音象|𧓲:蟲名
RpR徐兩;像:似也徐兩切十一|象:說文曰象長鼻牙南越大獸三季一乳象耳牙四足之形爾雅曰南方之美者有梁山之犀象|蟓:桑上繭|橡:櫟實|襐:未笄冠者之首飾也|勨:勉也又音養|鱌:魚名似魟白鼻長也|潒:潒遠|𦺨:草名|𨖶:行也|嶑:山名
NpR即兩;㢡:勸也助也成也譽也厲也即兩切六|獎:+上同說文本作獎嗾犬厲之也|䉃:剖竹未去節也又秦杖切|槳:檝屬|㯍:+上同|蔣:國名亦姓風俗通云周公之胤又漢複姓漢有曲陽令蔣匠熙又子羊切
IpR良㢡;㒳:說文曰再也易云參天㒳地今通作兩良㢡切八|兩:+上同說文曰二十四銖爲一兩|脼:膎脼|𣓈:松脂|緉:雙履|蜽:蛧蜽蟲名說文曰蛧蜽山川之精物也國語曰木石之怪夔蛧蜽亦作魍魎|魎:+見上注|㔝:㔝勥力拒
hpd於兩;鞅:牛羈也說文頸靼也於兩切十一|柍:木名|秧:秧穰禾稠也又音央|䬬:飽皃|詇:早知也|岟:岟山足|駚:駚驡馬皃|炴:火光|𧵌:無貲量謂無極限也|怏:怏悵也又於亮切|紻:冠纓
fpd其兩;勥:迫也勉力也其兩切五|彊:說文云弓有力也或作強又姓前秦錄有將軍強求又其良切|弜:弓有力也|誩:競言|滰:乾米之皃
gpd魚兩;仰:偃仰也說文舉也魚兩切三|䒢:昌蒲別名|卬:望也欲有所度
TpR初兩;磢:瓦石洗物初兩切六|㼽:+上同|𠞮:皮傷|搶:頭搶地見史記又七良七養二切|漺:凈也|愴:愴怳失意皃又音創
QpR息兩;想:思想也息兩切二|鯗:乾魚腊也
XpR諸兩;掌:手掌又姓晉有琅耶掌同前涼有燉煌掌據諸兩切三|仉:姓梁公子仉䁈後也|𤓯:反爪
VpR疎兩;𤕤:明也差也烈也猛也貴也疎兩切九|爽:+上同|𦄍:屩中絞繩|鷞:鷞鳩|塽:塽塏高也|樉:木名|㼽:半瓦|漺:凈也又初兩切|䫪:醜皃
ipd許兩;響:聲也許兩切八|饗:歆饗|蠁:說文曰知聲蟲也|䖮:+上同|亯:獻也祭也臨也向也歆也書傳云奉上謂之亯|亨:+上同亦作享|嚮:爾雅兩階閒謂之嚮本亦作鄉又音向|曏:不久也又音向
YpR昌兩;敞:高也昌兩切七|𢠵:𢠵怳驚皃|氅:鶖鳥毛也|𪅶:+上同|廠:屋也出方言又音唱|䟫:踞也又主尚直庚二切|僘:僘寬也
dpd居兩;繈:絲有纇又孟康曰繈錢貫也俗作鏹居兩切五|鏹:+俗見上注|襁:襁褓負兒衣博物志云襁織縷爲之廣八寸長二尺以約小兒於背上|膙:筋頭|憼:敬也說文音景
LpR直兩;丈:說苑曰十尺爲丈直兩切四|杖:說文曰持也大戴禮曰武王踐阼爲杖之銘曰惡乎失道於嗜慾惡乎相忘於富貴呂氏春秋曰孔子見弟子抱杖而問其父母柱杖而問其兄弟曳杖而問其妻子尊卑之差也禮曰苴杖竹也削杖桐也|仗:憑仗本又音去聲|㽴:病也
KpR丑兩;昶:通也明也舒也丑兩切二|鋹:利也
dpt居往;獷:獷平縣在漁陽居往切又居猛切一
cpR如兩;壤:土也書傳曰無塊曰壤風土記曰擊壤者以木作之前廣後銳長尺三四寸其形如履臘節僮少以爲戲也逸士傳曰堯時有壤父擊於康衢藝經曰擊壤古戲又漢複姓孔子弟子有壤駟赤如兩切八|䖆:䖆菜爲葅|䑋:肥蜀人云|穰:豐穰又汝羊切|蠰:蟲名似雞而小|攘:擾攘又汝羊切|躟:躟躟行疾皃|𥗝:惡雌黃
apR書兩;賞:賜也又吳姓有賞氏書兩切五|𩞧:日西食|𩞃:+上同|饟:周人呼餉食|曏:少時也又火亮切
BpN妃兩;髣:髣髴亦作彷彿妃兩切六|彷:+彷彿俗|仿:說文曰相似也|紡:績紡|鶭:鸅鸆鳥蒼黑色常在澤中俗呼爲護澤|鴋:+上同
DpN文兩;网:网罟說文曰网庖羲所結繩以田以漁也世本曰庖羲臣芒所作五經文字作罔俗作冈文兩切十二|網:+上同|罔:+上同又無也|輞:車輞|棢:+上同|惘:惘然失志皃|菵:菵草|誷:誷誣|𡔞:+上同|𦖉:耳疾|蛧:蛧蜽|魍:+魍魎上同
ApN分网;昉:明也分网切四|倣:學也|放:+上同|瓬:周禮有瓬人爲簋者蓋摶埴之工又音甫
hpt紆往;枉:邪曲也亦姓今虢州有之紆往切四|𢼟:曲侵|𣢫:佞人|汪:汪陶縣在鴈門又烏光切
kpt于兩;往:之也去也行也至也于兩切二|暀:德也是也光也爾雅曰暀暀皇皇美也
ipt許昉;怳:𢠵怳許昉切二|𧧢:夢中言也又火光切
OpR七兩;搶:七兩切又初兩七羊二切二|摤:+上同
JpR知丈;長:大也又漢複姓晉有長兒魯少事智伯智伯絕之三年其後死智伯之難知丈切又直張切一
ZpR時掌;上:登也升也時掌切又音尚二|丄:+古文
fpt求往;俇:楚詞注云俇俇遑遽皃求往切一
dpt俱往;臩:說文曰驚走也一曰往來皃俱往切四|迋:欺怨|𠏤:載器也出埤蒼|逛:走皃
CiE毗養｟兩｠〈霄〉;𩦠:姓也毗養切一
TpR初丈;䫪:醜也初丈切二|傸:惡也
#蕩
GqR徒朗;蕩:大也又水名出湯陰又姓宋之公族也徒朗切十二|崵:山名漢高帝隱處|婸:淫戲皃|𥯕:大竹筩|潒:水大之皃又洸潒也|𢠽:放𢠽或作婸|愓:不憂|璗:玉名說文曰金之美與玉同色者也|盪:滌盪搖動皃說文曰滌器也又吐浪切|䑗:舂也冶米精也|簜:大竹|嵣:嵣㟐山皃
QqR蘇朗;顙:頟也蘇朗切四|𣞙:鼓匡木也|𣡆:+上同|磉:柱下石也
dqh古晃;廣:大也闊也古晃切二|鄺:姓出廬江
AqB北朗;榜:木片北朗切六|牓:題牓|𣮧:毛𣮧罽文|螃:陸居蝦蟆|蒡:牛蒡菜|䰃:䰃鬤亂毛
NqR子朗;駔:會馬市人又牡馬也子朗切三|驡:駚驡馬容|髒:骯髒體盤
HqR奴朗;曩:久也奴朗切二|灢:泱灢水不淨見海賦
jqR胡朗;沆:沆瀣氣也胡朗切六|骯:骯髒體盤|䟘:伸脛也|𡕬:直項之皃|蚢:貝大者如車輞爾雅作魧|吭:聲也
FqR他朗;曭:日不明他朗切十二|儻:倜儻不羈又他浪切|偒:長皃|戃:戃慌失意皃|矘:矘䁳目無精|𥯕:說文曰大竹筩也|帑:金帛舍又音奴|爣:爣朗火光寬明|𣎲:𣎲㬻月不明也|㼒:大瓜名又㼒㼒長皃|㿩:白㿩|攩:攩㨪搥打
DqB模朗;莽:草莽說文曰南昌謂犬善逐兔於艸中爲莽又姓前漢反者馬何羅後漢明德馬后恥與同宗改爲莽氏模朗切又莫古切十|茻:說文曰眾艸也|壾:吳主孫休子名見吳志|䁳:無一睛|䒎:䒍䒎無色狀|㬒:日無光|䥈:鈷䥈又莫古切|蟒:蛇最大者|漭:漭沆水大|㟐:嵣㟐山皃
EqR多朗;黨:釋名曰五百家爲黨黨長也一聚所尊長也又輩也美也累也說文曰不鮮也多朗切五|讜:直言|欓:木名|䣣:地名說文作䣊|𧅗:草名
IqR盧黨;朗:明也亦姓出姓苑盧黨切七|朖:-|誏:+並上同|俍:俍偒長皃|崀:嵻崀山空|榔:木名|㝗:㝩㝗空虛
hqR烏朗;坱:塵埃也烏朗切十|姎:女人自稱姎我又烏郎切|映:映㬒不明|泱:滃泱水皃|咉:咉咉咽悲也|醠:濁酒|䇦:竹名玉篇云䇦無色也|盎:盆也又烏浪切|駚:駚驡馬容|軮:軮軋聲也
eqR苦朗;慷:慷慨竭誠也苦朗切七|忼:+上同|𡻚:𡻚崀山空|骯:骯髒體盤|䡉:車䡉之名|㝩:㝩㝗空虛|懬:大也又丘廣切說文又口謗切
hqh烏晃;㳹:大水烏晃切二|瀇:水深廣皃
jqh胡廣;晃:明也暉也光也亦作晄胡廣切七|幌:帷幔也晉惠起居注云有雲母幌|櫎:兵欄|榥:讀書牀也|滉:滉瀁水皃|攩:搥打又吐朗切|皝:人名前燕慕容皝也
BqB匹朗;髈:髀吳人云髈匹朗切二|䒍:䒍䒎無色
iqh呼晃;慌:戃慌呼晃切七|爌:爌朗寬明也又苦晃切|𡧽:𡧽㝗也|䁜:䁳䁜目疾出新字林|㬻:𣎲㬻月不明皃|𣆖:日旱熱也|𧧢:夢言也
dqR各朗;䴚:鹽澤也各朗切四|𨟼:-|㽘:+並上同|䟘:伸脛也
gqR五朗;䭹:馬怒驚驡䭹也五朗切一
PqR徂朗;奘:大也徂朗切一
OqR麁朗;蒼:莽蒼麁朗切一
iqR呼朗;汻:姓今涇州有之呼朗切三|酐:苦酒|𤰟:鹵𤰟
eqh丘晃;㢜〈懬〉:大也寬也怨也丘晃切三|䡉:䡉䡉𨋕也|爌:爌朗寬明也又火光
#梗
drR古杏;梗:梗直也又桔梗藥名古杏切九|挭:挭槩大略|哽:哽咽|郠:邑名在莒|綆:井索|鯁:刺在喉又骨鯁謇諤之臣|埂:堤封吳人云也|骾:骨骾|𧋑:蟲名
AsJ兵永;丙:辰名爾雅云太歲在丙曰柔兆又光也明也又姓風俗通云齊有大夫丙歜兵永切九|昞:亮也亦作昺|怲:憂也|邴:邑名在泰山又姓左傳晉有大夫邴預又音柄|炳:炳煥明也|秉:執持又十六斗曰藪十藪曰秉又姓漢書有秉漢|窉:爾雅云三月爲窉本亦作寎又兄病孚命區詠三切|苪:著也|蛃:蛃蟲名
dsZ居影;警:寤也戒也居影切八|儆:+上同|景:大也明也像也光也炤也又姓齊景公之後後漢有景丹|境:界也|璥:玉名|蟼:蛙屬|檠:所以正弓出周禮亦作檠|憼:敬也
hsZ於丙;影:形影於丙切八|璟:玉光彩出埤蒼|璄:+上同|䭘:飽亦作䭊|摬:中擊|㲟:毛車|𠝟:玉篇云刺也|𩘑:高風
VsR所景;省:省署漢書曰舊名禁中避元后諱改爲省中又姓左傳宋大夫省臧所景切又息井切九|眚:過也災也|㾪:瘦㾪|𡞞:減也|䚇:䚇腳露也|𨵥:𨵥府今爲省字|㼳:㼬㼳耳瓶|渻:水名亦丘名|𨜜:+上同
ksp于憬;永:長也引也遠也遐也亦姓出何氏姓苑于憬切二|栐:木可爲笏
isp許永;𦬺:小風許永切一
DsJ武永;皿:器皿武永切三|𥥊:𥥊戶土穴|𥁰:盟也
dsp俱永;憬:遠也俱永切六|囧:光也|煚:火也|璟:玉光|臩:驚走皃|暻:明也曲礼悟也
jrR何梗;杏:果名廣志曰滎陽有白杏鄴有赤杏黃杏何梗切三|莕:莕菜|荇:+上同
DrB莫幸〖杏〗;猛:勇猛又嚴也害也惡也亦姓左傳宋大夫猛獲之後莫幸切六|𥋝:𥋝盯視皃|蜢:虴蜢蟲|艋:舴艋小船舴陟格切|鱦:蛙屬|鄳:縣名在江夏
drh古猛;礦:金璞也古猛切七|鑛:+上同|𨥥:+古文|𪍿:𪍿麥|䵃:+上同|獷:犬也又居往切獷平縣名在漁陽|穬:榖芒又曰稻不熟
ArB布梗;浜:浦名布梗切又布耕切三|㑟:詐僞人也|𧚭:𧚭急皃
JrR張梗;盯:盯𥋝張梗切一
LrR徒杏;瑒:祀宗廟圭名長一尺二寸徒杏切又音暢一
hrh烏猛;䁝:清潔烏猛切三|㴄:㴄澋水回旋也|奣:六合清朗
ErR德冷;打:擊也德冷切又都挺切一
IrR魯打;冷:寒也魯打切又魯頂切一
jrh呼〈乎〉䁝;卝:金玉未成器也呼䁝切二|澋:㴄澋水回旋也
CrB蒲猛;鮩:鮊魚別名蒲猛切一
erh苦礦;𥉁:𥉁然舉目也苦礦切又音句一
MrR拏梗;檸:木皮入酒浸治風拏梗切一
#耿
dtR古幸;耿:耿介也又耿耿不安也又姓晉大夫趙夙滅耿因封焉遂以國爲氏古幸切三|𦵸:芋莖也|𥉔:𥉔䁅視皃
DtB武幸;䁅:武幸切三|鼆:句鼆魯邑名|黽:蛙屬
jtR胡耿;幸:說文作𡴘吉而免凶也从屰从夭夭死之事故死謂之不𡴘胡耿切四|𡴘:+見上注|倖:儌倖|㼬:㼬㼳瓶有耳
CtB蒲幸;𠊧:俱也或作併羅列也蒲幸切四|𩶁:蛤𩶁|蠯:+上同|螷:亦同
BtB普幸;皏:皏㿣薄皃普幸切一
#靜
PuR疾郢;靜:安也謀也和也息也疾郢切十|睜:眳睜不悅視也|𩇕:清飾|靖:立也思也理也審也又姓齊靖郭君之後風俗通云單靖公之後|妌:女人貞絜也|婧:+上同|穽:坑也|阱:+上同|猙:獸如狐有翼又音爭|竫:亭安
XuR之郢;整:正也齊也之郢切二|⿱𱡘正:+俗
KuR丑郢;逞:通也疾也盡也丑郢切六|騁:馳騁又走也|裎:襌衣|悜:慏悜意不盡也|䩶:驂具又丑善切|睈:視也又意不盡
luR以整;郢:楚地以整切三|浧:泥也|梬:梬棗似柿而小
fuV巨郢;痙:風強病也巨郢切二|涇〈𠗊〉:玉篇云寒也
luh餘頃;潁:水名在汝南亦州名禹貢豫州之境春秋時沈丘也秦爲潁川郡漢爲汝南郡之汝陰後魏置潁州餘頃切二|穎:禾末也穗也又姓左傳有穎考叔
IuR良郢;領:理也錄也說文頃也良郢切六|嶺:山坡也裴潛廣州記云大庾始安臨賀桂陽揭陽爲五嶺與鄧德明南康記云別也|阾:+古文|柃:木名灰可染|袊:衣袊禮云左執領不從衣|䕘:草名
duV居郢;頸:項也居郢切又巨成切一
AuF必郢;餅:必郢切五|屏:蔽也爾雅曰屏謂之樹又廣雅曰罘罳謂之屏風俗通云鄉大夫帷士以廉以自鄣蔽|鉼:鉼金謂之鈑周禮祭五帝則供鉼金|併:併合和也又必姓切|䴵:索䴵出食苑
eul去潁;頃:田百畝也去潁切六|𩓏〈𩒵〉:+古文|㩩:竟也|檾:枲草|苘:-|䔛:+並上同
NuR子郢;井:說文曰八家一井象構韓形·𦉥之象也古者伯益初作丼今作井見經典省又姓姜子牙之後也左傳有井伯子郢切二|𨙷:𨙷邢地名
huV於郢;廮:安也又廮陶縣名在趙州於郢切五|𨟙:地名|癭:瘤也博物志云山居之人多癭疾|𣤵:𣤵氣|𦡺:滯氣
OuR七靜;請:乞也求也問也謁也七靜切又疾盈疾姓二切二|睛:眳睛不悅目皃出字林又音精
QuR息井;省:察也審也息井切六|渻:說文曰少減也一曰水門又水出丘前謂之渻丘|睲:睲睲照視|惺:惺悟出字林|㮐:俎几名|𢜫:𢜫悟皃俗
DuF亡井;眳:眳睛亡井切二|慏:慏悜意不盡也
LuR丈井;徎:雨後徑也丈井切二|𣵹〈塣〉:通也
#迥
jvh戶頂;迥:遠也戶頂切五|冋:空也|炯:光也明也又音熲|泂:詩云泂酌|𦳖:草名
dvh古迥;熲:光也又輝也古迥切八|炅:光也又古惠切|炯:火明皃又音迥|𠖷:凔寒|㯋:篋名|𩚱:𩚱飽|煛〈𥉁〉:目驚皃|𧍮:𧍮𧑗似蛙
DvB莫迥;茗:茗草莫迥切七|嫇:嫇奵自持也|酩:酩酊|瀴:瀴涬大水皃|溟:+上同|眳:眳睛|姳:姳好
EvR都挺;頂:頂𩕳頭上說文顛也都挺切十三|𩠑:+上同|𩕢:+籀文|奵:嫇奵|耵:耵聹耳垢|鼎:說文云鼎三足兩耳和五味之寶器禹收九牧之金鑄鼎荊山之下|薡:草名|酊:酩酊|濎:濎濘水皃|葶:葶䔭毒草|靪:補履又音丁|打:擊也又都冷切|㞟:展也
GvR徒鼎;挺:挺出說文拔也徒鼎切十二|艇:小船|鋌:金鋌|梃:木片|娗:長好皃|町:田畝又音汀|霆:疾雷又音庭|莛:草莖又音庭|涏:涇寒|蜓:蟲名又徒典切|訂:平議|誔:詭言
FvR他鼎;珽:玉名說文曰大圭長三尺杼上終葵首他鼎切十二|圢:平也|脡:脯胊|侹:長也直也代也敬也|頲:直也|徎:徑也|𡈼:善也|町:田塸|艼:葋也又禿鈴切|𤱹:田器|𦉬:𦉬𦊓小網|䦐〈𨳝〉:門上關
PvR徂醒;汫:汫濙小水皃徂醒切一
hvh烏迥;濙:汫濙烏迥切一
evR去挺;謦:謦欬也去挺切一
HvR乃挺;𩕳:頂𩕳乃挺切五|聹:耵聹|䗿:似蛙|濘:泥也又乃定切|䔭:葶䔭
jvR胡頂;婞:很也胡頂切七|涬:瀴涬大水皃|𩷏:魚名|鋞:似鐘而長|脛:腳脛又胡定切|𢙼:𢙼恨|緈:絓緈
QvR蘇挺;醒:醉歇也蘇挺切二|箵:箵笭篝籠
AvB補鼎;鞞:刀室補鼎切一
evh口迥;褧:褧衣說文檾也口迥切六|檾:枲屬|苘:+上同|烓:行竈又烏圭切|顈:襌也|絅:衣
dvR古挺;剄:斷首古挺切二|烴:焦臭
BvB匹迥;頩:斂容匹迥切一
hvR烟（煙）涬;巊:巊溟山水烟涬切三|𩳍:誣厭|瀴:瀴涬大水皃
IvR力鼎;笭:篝笭籠也力鼎切三|𦊓:𦉬𦊓小網|冷:寒也又姓前趙錄有徐州刺史冷道字安義又盧打切
CvB蒲迥;竝:比也蒲迥切四|並:+上同|鮩:白魚名也|併:立並又必姓切
ivh火迥;詗:明悟了知也火迥切一
gvR五剄;䀴:直視皃也五剄切二|矨:小皃
#拯
XwR=蒸上聲;拯:救也助也無韻切音蒸上聲五|抍:-|撜:+並上同見說文|𨋬:軺車後登出字林|氶:晉譙王名
KwR丑拯;庱:亭名在吳晉陵丑拯切又恥陵切一
fwd其拯;殑:殑㱡欲死也其拯切一
VwR色庱;㱡:殑㱡色庱切一
#等
ExR多肯;等:齊也類也比也輩也多肯切一
BxB普等;倗:不肯也普等切二|䣙:穆天子傳云西征至䣙郭璞云國名也前漢書有䣙成侯
exR苦等;肯:可也說文作肎骨閒肉肎肎著也一曰骨無肉苦等切二|肎:+上同
HxR奴等;能:夷人語奴等切本又奴登切一
#有
kyN云久;有:有無又果也取也質也又也又姓孔子弟子有若又漢複姓有男氏禹後分封以國爲姓出史記云久切九|右:左右也又漢複姓五氏左傳宋樂大心爲右師其後因官爲氏漢有中郎右師譚晉賈華爲右行因官爲氏漢有御史中丞右行綽何氏姓苑有右閭右扈右南等氏|䳑:鳥名似雉|友:朋友同志爲友|㕛:+上同出說文|䀁:器也又于救切|𥁓:+上同|栯:木名服之不妬又於六切|䒴:草名
IyB力久;柳:木名說文作桺小楊也从木丣聲丣古文酉餘倣此又姓出河東本自魯孝公子展之孫以王父字爲展氏至展禽食采於柳因爲氏魯爲楚滅柳氏入楚楚爲秦滅乃遷晉之解縣秦置河東郡故爲河東解縣人力久切十四|罶:魚梁|𦊑:+上同|懰:好也|珋:石之有光璧珋也說文本音留|𩖴:䬀𩖴風皃|嬼:妖美又嫠婦也|䉧:竹聲|𪕋:似鼠而大又音留|熮:火爛|瀏:水清|綹:十絲爲綹|𨋖:載柩車也|茆:𦽏葵水草詩云言采其茆即蒓菜也又莫飽切
MyB女久;狃:相狎也女久切十一|紐:結也|鈕:印鼻又姓何氏姓苑云今吳興人東晉有鈕滔也|杻:木名|莥:玉篇云鹿豆也|禸:爾雅云貍狐貒貈跡也|扭:扭手轉皃|𢔟:習也|䏔:食肉|𨙺:地名|𦱙〈莥〉:蔨實亦作𦱙
KyB敕久;丑:辰名爾雅曰太歲在丑曰赤奮若敕久切三|杻:杻械|杽:+古文
JyB陟柳;肘:臂肘陟柳切四|疛:說文曰小腹病|𤶡:+上同|扭:扭按也又音紐
iyN許久;朽:腐也許久切四|㱙:+上同|㽲:病也|殠:臭也
dyN舉有;久:長久也舉有切七|九:數也又漢複姓二氏何氏姓苑云昔岱縣人姓九百名里爲縣小吏而功曹姓萬縣中語曰九百小吏萬功曹列子秦穆公時九方皋一名歅善相馬也|玖:玉名|灸:灸灼也又居又切|韭:說文曰菜名也一種而久者故謂之韭象形在一之上一地也俗作韮|𡚮:女字也亦作奺|𨾉:姓出纂文
ayB書九;首:頭也始也書九切六|𩠐:+上同|𦣻:人頭象形|手:手足|守:主守亦姓出姓苑|䭭:人初產子
YyB昌九;醜:類也竅也釋名曰醜臭也如物臭穢也又虜複姓西秦錄有下將軍醜門于弟昌九切三|𧃝:瑞草也|魗:弃也惡也又市籌切
PyB在九;湫:洩水瀆也在九切又子由子小切二|愀:變色也又鍬小切
CyN房久;婦:說文曰婦服也从女持帚洒埽也房久切十五|䘀:䘀螽|負:擔也荷也又受貸不償曰負背恩忘德曰負也|萯:王萯草|蝜:𧑓蝜|阜:陵阜釋名曰土山曰阜阜厚也言高厚也廣雅曰無石曰阜|𨸏:+上同|𪃓:鷂別名也|偩:禮云禮樂偩天地之情|𦰺:香草|𨹺〈𩣸〉:盛也亦作䧞|䧞:+上同|㷆:㷆熾|菩:香草又步乃切|𧌈:鼠𧌈
AyN方久;缶:瓦器鉢也史記云秦王趙王會于澠池藺相如使秦王擊缶是也詩疏云缶者瓦器也所以盛酒漿秦人鼓之以節歌方久切八|缹:蒸缹|否:說文不也又房彼切|不:弗也說文作𠀚鳥飛上翔不下來也从一一天也象形又甫鳩甫救二切|鴀:䳕鳩|痞:病也|殕:物敗也|𡜊:好皃也
eyN去久;糗:乾飯屑也孟子曰舜飯糗茹草又姓風俗通漢有糗宗爲嬴長去久切一
cyB人九;蹂:踐也人九切十|楺:屈木|煣:+上同|輮:車輞|沑:說文曰水吏也又溫也|禸:獸跡又女九切|葇:葇䖆菜不切也|𥠊:禾𥠊|韖:車軔|粈:粽粈
fyN其九;舅:夫之父也亦母之兄弟又姓左傳秦大夫舅犯其九切十一|倃:說文毀也|臼:杵臼世本曰雍父作臼又姓左傳宋華貙家臣臼任|齨:齒齨亦馬八歲俗作𩣅|麔:牝麋|䳎:鳥名似鳩有冠|咎:愆也惡也過也災也從人各各者相違也|䊆:糗米|𤷑:病也|𢛃:怨𢛃|䛮:毀也
LyB除柳;紂:殷王号也方言云自關而東謂䋺曰紂俗作𩋰除柳切六|䈙:竹易根而死也|鮦:鮦陽縣在汝南又直冢切|葤:裹也|棸:姓也襄州有之又音籌|𦡴:小腹痛又腿後
lyB與久;酉:飽也老也就也首也又辰名爾雅曰太歲在酉曰作噩又姓魏有酉牧與久切二十一|丣:+古文|誘:導也引也教也進也說文曰相訹呼也|㕗:-|䛻:+上同並見說文|牖:道也向也說文曰牖穿壁以木爲交窻也禮曰蓽門閨竇蓬戶甕牖|卣:中形罇又音由|槱:積木燎以祭天也|𥟁〈𥙫〉:+上同|莠:草也|羑:羑里文王所囚處又有羑水並在湯陰又姓也|庮:久屋木也周禮曰牛夜鳴則庮鄭司農曰庮朽木臭也|蜏:朝生暮死蟲名|㝌:字書云貧病也|𣣸:說文云言意也|琇:玉名又音秀|梄:柞梄木|𤪎:遺玉|輶:輕車又音由|𨣆:𨣆酒|𦏇:水名
ZyB殖酉;受:容納也承也盛也得也繼也殖酉切五|壽:壽考又州名楚考烈王自陳徙都壽春号曰郢秦爲九江郡魏爲淮南郡梁爲南豫州周爲揚州隋平陳爲壽州亦靈壽木名生日南又姓王莽兗州牧壽良又漢複姓前漢燕王遣壽西長之長安蘇林云壽西姓也又承呪切|𨞪:水名在蜀亦地名也|璹:玉名又音孰|綬:組綬禮云天子玄公侯朱大夫純世子綦士縕應劭漢官曰綬長一丈二尺法十二月廣三尺法天地人也
QyB息有;滫:溲麵說文曰久泔也息有切四|糔:糔溲|醙:白酒|𦄼:絆前兩足又相主切
hyN於柳;䬀:䬀𩖴於柳切三|䱂:魚名|懮:懮受舒遟皃
NyB子酉;酒:酒醴戰國策曰帝女儀狄作而進於禹亦云杜康作元命包曰酒乳也又酒泉縣在肅州匈奴傳云水甘如酒因以名之亦姓也子酉切一
VyB疎有;溲:溲麪亦作𣸈疎有切一
XyB之九;帚:少康作箕帚之九切五|箒:+俗|鯞:鱖鯞魚名|晭:明晭|𧳜:猛獸
ByN芳否;㤱:小怒芳否切三|紑:鮮也又孚丘切|𩂆:霧𩂆
SyB側九;掫:持物相著側九切三|搊:搊扇別名|𧌗:蟲名
UyB士九;𥣙:聚名士九切一
TyB初九;𩋄:𩋄束初九切二|𩌄:+上同
ByN芳婦;秠:爾雅曰一稃二米此亦黑黍漢和帝時任城生黑黍或三四實實二米得黍三斛八斗是芳婦切又匹几孚悲二切一
#厚
jzB胡口;厚:厚薄又重也廣也說文作𠪀曰山陵之𠪀也又姓出姓苑胡口切七|垕:+古文|後:先後說文遟也又胡豆切|𨒥:+古文|后:君也又姓漢有少府后倉又音候|郈:鄉名在東平又姓左傳魯大夫郈昭伯|㖃:欲吐又呼后切
DzB莫厚;母:父母老子注云母道也蒼頡篇云其中有兩點象人乳形豎通者即音無莫厚切十四|牡:牝牡|某:詔前人之言也|拇:大拇指也|胟:+上同|畝:司馬法六尺爲步步百爲畝秦孝公之制二百四十步爲畝也|畮:-|畞:+並古文|莽:草莽|𤝕:猦𤝕獸名|𤵝:病𤵝|踇:踇偶山名|𧿹:行皃|䳇:鸚䳇能言之鳥又音武
CzB蒲口;部:署也又姓出姓苑蒲口切十|培:培塿小阜或作㟝|犃:犃㸸偏高又牛短頸|䏽:豕肉醬|瓿:瓿甊小甖|䍌:小缶|䴺:䴺𪌘餅|篰:牘也|蔀:蔀菜魚薺也易云豐其蔀王弼曰蔀覆曖鄣光明之物亦音剖|婄:婦人皃又音剖
EzB當口;斗:說文作斗十升也有柄象形石經作斗當口切八|㪷:+俗|枓:柱上方木|蚪:蝌蚪蟲也|阧:阧峻|陡:+上同|抖:抖擻舉皃|襡:衣袖又音蜀
FzB天口;𪌘:䴺𪌘天口切九|飳:+上同|妵:人名左傳有華妵說文女字也|黈:冕前纊也|𩿢:水鳥黑色又大口切|蘣:好皃又木苗出|斢:斢㪹兵奪人物出字書|鈄:姓出姓苑|䱏:魚名
dzB古厚;苟:苟且又姓出河內河南西河三望國語云本自黃帝之子漢有苟參古厚切十三|玽:石似玉|狗:狗犬|垢:塵垢|笱:笱屚縣名在交阯又魚笱取魚竹器|𦊒:+上同|耇:耇老壽也|詬:詬恥也又呼候切|枸:枸杞|茩:薢茩|岣:岣嶁山巔|敂:敂扣打也|豿:熊虎之子
gzB五口;藕:爾雅曰荷芙蕖其根藕五口切六|蕅:+上同|偶:合也匹也二也對也諧也|耦:耦耕也亦姓風俗通云宋卿華耦之後漢有侍中耦嘉|髃:肩前髃也|㼴:盎名
AzB方垢;㨐:衣上擊也方垢切二|掊:擊也
HzB乃后;㝅:乳也乃后切六|㳶:說文水也|陾:眾陾|𡝦:𡝦㛘女肥皃|啂:啂食物出新字林|𡭾:小皃
QzB蘇后;叜:老叜蘇后切十五|叟:+上同|傁:+上同亦從叜餘倣此|嗾:使犬聲|𠻛:+上同|瞍:瞽瞍舜父|謏:謏訹誘辝|擻:抖擻舉也|藪:藪澤爾雅有十藪魯大野晉大陸秦楊陓宋孟諸楚雲夢吳越具區齊海隅燕昭余祁鄭圃田周焦護又十六斗曰藪|籔:漉米器也|䏂:字林云聰總名也|廋:廣雅云隈也|棷:薪也|駷:馬搖銜走又思隴切|操〈橾〉:車轂中空
izB呼后;吼:牛鳴呼后切七|吽:+上同|呴:亦同|㸸:夔牛子也|𤘽:+上同|蚼:蚍蜉名也又渠俱切|㖃:厚怒聲
BzB普后;剖:判也破也普后切五|婄:婦人皃|蔀:小席又音部|䳝:䳝雀名|䯽:髮皃
hzB烏后;歐:吐也或作嘔烏后切又烏侯切七|嘔:+上同|毆:毆擊也俗作敺|㸸:特牛又吼口二音|𠙶:山名在溧陽縣|塸:聚沙|䙔:㳄衣也又於侯切
IzB郎斗;塿:培塿郎斗切十|嘍:連嘍煩皃又力侯切|簍:籠也周禮作簝|甊:瓿甊甖|𪍣:𪍴𪍣糫餅|嶁:文字音義云山巔也|㪹:斢㪹兵奪人物出新字林|謱:謰謱小兒語又力侯切|漊:溝通水漊也|䅹:耕畦
NzB子苟;走:趨也子苟切又音奏一
ezB苦后;口:說文曰人所以言食也亦姓今同州有之苦后切九|扣:扣擊也亦作叩|㸸:犃㸸|𤘘:+上同|釦:金飾|叩:叩頭|𧥣:先相𧥣可|𨙫:鄉名|竘:健也又驅甫切
GzB徒口;䕆:圓草褥也徒口切六|𨪐:酒器也或作鍮|𠁁:+水盥皃也說文同上|揄:揄引|𩿢:水鳥又他口切|襡:短衣
PzB仕垢;鯫:魚名一曰姓漢有鯫生又淺鯫小人仕垢切又士溝切一
OzB倉苟;趣:趣馬書傳云趣馬掌馬之官也倉苟切又士屢切三|取:又七庾切|棷:棨也又側溝切
#黝
h0V於糾;黝:黑也於糾切又於夷切七|怮:憂皃|䬀:䬀颼風聲又於柳切|蚴:蚴蟉龍皃|泑:崑崙山下澤也|眑:幽靜之皃|𣢜:愁皃
d0V居黝;糾:督也恭也急也戾也俗作糺居黝切四|赳:武皃詩曰赳赳武夫|朻:爾雅曰朻者聊又居幽切|𨷺〈鬮〉:鬮取皃
f0V渠黝;蟉:蚴蟉龍皃渠黝切一
#寑
O1R七稔;寑:室也臥也七稔切九|𡪢:+上同見說文|寢:+上同見經典|梫:木名桂也|㾛:㾛痛又皃醜也|𡬓:說文曰病臥也|𦯈:覆也|鋟:爪刻鏤版又子廉切|䤐:小甜
L1R直稔;朕:我也秦始皇二十六年始爲天子之稱直稔切六|𦩗〈𦩎〉:古文|鰧:魚名似鰕赤文出廣雅|螣:螣蛇|栚:說文曰槌之橫者關西謂之㯢|顩:顩頤醜皃
e1Z丘甚;坅:坎也丘甚切一
I1R力稔;廩:倉有屋曰廩力稔切八|㐭:+上同|懍:敬也畏也|菻:菻蒿|凜:寒凜|顲:顲然作色皃|𤎭:火舒|癛:粟體
Q1R斯甚;罧:積柴取魚斯甚切二|伈:伈伈恐皃
K1R丑甚;踸:踸踔行無常皃丑甚切三|鍖:鍖銋|䫖:䫖䫴自愞劣皃
N1R子朕;䤐:小甜也子朕切四|𡩻〈寖〉:漸也漬也又子鴆切|䭙:濕通上也|䐶:䐶脣病也
c1R如甚;荏:菜也又荏苒如甚切十四|飪:熟食|餁:+上同|䭃:亦同又玉篇云飽也|稔:年也亦歲熟廣雅曰稔秋穀熟也|栠:木弱皃|恁:念也|袵:文字音義云臥席也|䏕:肉汁|䇮:字書云單席|棯:果木名爾雅云還味棯棗|𢆉:稍甚|銋:鍖銋|腍:味好
X1R章荏;枕:枕席又姓出下邳章荏切又之賃切三|䪴:頭骨後|䫬:頭銳長也
a1R式任〈荏〉;沈:國名古作邥亦姓出吳興本自周文王第十子聃季食采於沈即汝南平輿沈亭是也子孫以國爲氏式任切又丈林切十四|邥:+古文|宷:說文曰悉也知寀諟也|審:+詳審也說文同上亦姓漢有辟陽侯審食其|㰂:木名山海經云煑其汁味甘可爲酒|瞫:竊視又姓後漢書云武落鍾離山有黑穴出四姓瞫氏相氏樊氏鄭氏也|諗:告也謀也深諫也又如甚切|䰼:大魚|魫:魚子|淰:淰㴸水動也禮運曰龍以爲畜故魚鮪不淰淰之言閃也|㜤:志下|䀢:瞚也|𩶇:大魚|𧀯:草名
b1R食荏;葚:說文曰桑實也食荏切二|𣞵:+上同俗又作椹椹本音砧
Z1R常枕;甚:劇過也說文曰尤安樂也常枕切二|訦:信也又市林切
Y1R昌枕;瀋:汁也昌枕切一
T1R初朕;墋:土也初朕切三|醦:酢甚|磣:食有沙磣
M1R尼凜;拰:拰搦尼凜切一
f1Z渠飲;噤:寒而口閉渠飲切四|䫴:切齒怒也|凚:玉篇云寒極也|唫:說文云口急也
d1Z居飲;錦:釋名曰錦金也作之用功重其價如金故字從金帛居飲切一
P1R慈荏;蕈:菌生木上慈荏切一
g1Z牛錦;僸:仰頭皃牛錦切又音禁二|趛:低頭疾行
V1R疎錦;㾕:寒病疎錦切三|瘮:+上同|槮:木實名也
A1J筆錦;稟:供穀又與也筆錦切一
h1Z於錦;㱃:說文曰㱃也於錦切三|飲:+上同|𤃷:大水至又於感切
B1J丕飲;品:官品又類也眾庶也式也法也二口則生訟三口乃能品量又姓出何氏姓苑丕飲切一
e1Z欽錦;𩖄:𩒣𩖄醜皃欽錦切二|顉:曲頤之皃又五感切
i1Z許錦;廞:大喪廞裘也也許錦切又羲今切一
J1R張甚;戡:少斫也張甚切又音堪二|㱽:深擊說文曰下擊上也
l1R以荏;潭:潭濼水動搖皃以荏切又徒南切一
e1Z士｟仕｠〈丘〉㾕;𩒣:𩒣𩖄醜皃士㾕切一
#感
d2R古禫;感:動也古禫切十一|𥸡:竹名亦作篢|鱤:魚名|灝:豆汁|贑:水名在南康又音紺|䤗:酒味淫也|贛:水名在豫章|㔶:方言云箱類又云覆頭也又音貢|𧆐:薏苡|䃭:石篋見封禪議|灨:水名
G2R徒感;禫:除服祭名徒感切十六|䊤:糣䊤滓也|䨢:䨢䨴雲皃|黮:黭黮雲黑又他感切|窞:坎傍入也易曰入于坎窞|髧:髮垂|萏:菡萏荷花未舒|𧂄:+上同|倓:安也|𥥦〈𥥍〉:竈突說文深也|𧡪:徐視|醰:長味|嘾:莊子曰大甘而嘾說文曰含深也|贉:買物先入直也|譚:大也又姓|𣛱:木名
h2R烏感;晻:晻藹暗也冥也烏感切九|黭:黭黮|揞:手覆|唵:手進食也|隌:隌闇|罯:魚網|黤:青黑色也|㞄:㞄跛又蹇也|𤃷:大水至
H2R奴感;腩:煑肉奴感切六|湳:水名在西河又姓|䈒:竹弱|䎃:羽弱|揇:揇搦|萳:草長弱皃
F2R他感;襑:衣大他感切五|𥁺〈𧖺〉:𧖺醢亦作醓|䏙:肉汁|嗿:眾聲|黮:黭黮黑也又徒感切
P2R徂感;歜:昌蒲葅徂感切四|㣅:弓弦㣅又作𢏵|䰼:大魚又才枕切|㔆:𠞊㔆又割翦出也
O2R七感;慘:慘慼也說文毒也七感切八|憯:痛也|朁:說文會也|黲:暗色說文曰淺青黑也又倉敢切|㜗:說文婪也|傪:好皃又音平聲|噆:銜也又子盍切|䫩:顉䫩搖頭又素慘切
g2R五感;顉:顉䫩五感切三|㜝:含怒皃|嵁:嵁崿山形
N2R子感;昝:姓也子感切三|寁:速也|撍:手動
Q2R桑感;糂:羹糂墨子曰孔子戹陳藜羹不糂也或作糝桑感切八|糝:+上同|糣:糣䊤滓也|𢕕:顉𢕕|㧲:撼㧲搖動也|槮:郭璞云叢木於水中魚寒入其裏因以箔取之|䫩:顉䫩搖頭皃|䊉:蜜藏木瓜
e2R苦感;坎:險也陷也又小罍也形似壼苦感切十|歁:食未飽也|惂:憂困也又恨也|輡:輡𨎹車行不平|錎:字書云瑣連環也|轗:轗軻多迍|埳:埳陷|顑:顑顲瘦也|竷:舞曲名|臽:小穽名也
j2R胡感;頷:漢書曰班超虎頭燕頷說文曰面黃也胡感切十六|頜:說文曰顄也|𡣔〈㜝〉:㜝害惡性也|撼:撼動也|淊:水和泥或作涵|菡:菡萏|欿:欲得|蜭:爾雅云蜭毛蠹|涵:水入船又胡南切|肣:牛腹又音含|𢎘:說文曰嘾也草木之華未發函然象形|𢇞:𢇞嘾乳汁狀出莊子|𢃗:壅耳|莟:花開|顄:頤也又胡南切|𡻡:𡻡崿
I2R盧感;壈:坎壈盧感切八|燣:黃焦色|𨎹:輡𨎹|浨:藏梨汁也出字林|醂:桃葅|顲:面黃醜說火曰面顑顲也又力稔切|𠓭:愁皃|漤:鹽漬果
E2R都感;黕:滓垢也黑也都感切十|耽:虎視又丁含切|𡖓:玉篇云多也又丁含切|衴:埤蒼云被緣也|䪴:顲䪴醜也|丼:姓也|瓭:瓦屬|抌:刺也擊也也又音由|䉞:箱屬又作𥴶|𥴶:+上同
i2R呼唵;䫲:食不飽呼唵切一
#敢
d3R古覽;敢:勇也犯也說文作𠭖進取也古覽切七|𠭖:+上同|𣪏:+籀文|𢽤:+古文|橄:橄欖果木名出交阯|澉:澉䭕食無味|䇞:竹名實中
a4R賞敢;｛㶒｝【「㴸」之音，「㶒」（書開三侵上）之字】:果決勇也賞敢切一
I3R盧敢;覽:視也又姓何氏姓苑云彭城人盧敢切六|爁:火爁|擥:手擥取|攬:+上同|欖:橄欖|罱:罱網
F3R吐敢;𦵹:說文曰蒮之初生一名薍一名鵻吐敢切八|菼:+上同|緂:青黃色說文充三切白鮮衣皃|𤎥:+上同|毯:毛席|𦃖:毳衣說文曰帛騅色也引詩曰毳衣如𦃖|裧:+俗|𠪚:𠪚崯也又五今切
E3R都敢;膽:肝膽都敢切六|紞:冕前垂也說文曰冕冠塞耳者|䃫:石䃫藥名出玉篇|黵:大汚垢黑|䒞:𧂇䒞藩又音沈|𪆻:應禍鳥名
G3R徒敢;噉:噉食或作啖又姓前秦錄有將軍噉鐵徒敢切八|啖:+上同|啗:亦同|澹:澹淡水皃淡音琰又恬靜又徒濫切|𥲄:竹名|淡:淊淡水滿皃又薄味也又徒濫切|憺:安緩又徒濫切|惔:+上同
O3R倉敢;黲:日暗色倉敢切一
D3B謨敢;㛧:鄉名在河東徛氏縣亦作□謨敢切二|𩛎:吳人呼哺兒也
N3R子敢;䭕:澉䭕子敢切一
P3R才敢;槧:削版牘才敢切又七廉切七豔切四|鏨:鏨鑿也又音慙|嵌:開張山皃出蒼頡篇|㟛:+上同
i3R呼覽;喊:聲也呼覽切四|嚂:+上同|壏:壏土地之堅也|㯺:+上同周禮注云強㯺地之堅者又音檻
h3R烏敢;埯:坑今之窊埯是烏敢切二|揜:手揜物也
e3R口敢;𠪚:𠪚嶮側穴口敢切二|䖔:甝屬
#琰
l4R以冉;琰:玉名周禮曰琰圭九寸以冉切十一|剡:削也利也亦姓又時冉切|𨁹:疾行|棪:木名實似柰可食|燄:燄燄火初著也|淡:澹淡水皃又徒敢切|扊:扊扅戶牡所以止扉或作剡移|淊:㶘淊水滿|夵:上大下小|䎦:䎦耜|䌪:續也
I4R良冉;斂:收也又姓姚秦錄有輔國將軍斂憲良冉切十三|撿:說文拱也|薟:白薟藥名又力瞻切|蘞:+上同|瀲:瀲灩水溢皃或作澰|獫:犬長喙也又音險|溓:薄冰也|嬚:女字|䭑:廉也又小食也|羷:羊角三觠羷也|䌞:懸蠶簿也|㰈:善美之名|㯬:功勤之稱
i4Z虛檢;險:危也阻也難也虛檢切八|獫:獫狁|玁:+上同|㛍:㛍姱性不端良又棄葉切少氣也|譣:譣詖說文息廉切問也|憸:憸詖又息廉切|𩏩:胡被又音杴|嶮:嶮巇
A4J方斂;貶:損也方斂切二|𦥘:+說文曰傾覆也或同上
X4R占琰;颭:風吹落水占琰切一
e4Z丘檢;𩑳:𩑳顩不平丘檢切二|嵰:山高
g4Z魚檢;顩:𩑳顩魚檢切七|广:因巖爲屋|隒:山形似重甑|嬐:嬐然齊也|䲓:䲓鰅魚名出樂浪|嶮:嵰嶮山不平|噞:噞喁魚口上下皃
f4Z巨險;儉:約也少也饑饉也又姓出姓苑巨險切二|芡:說文云鷄頭也方言曰南楚謂之鷄頭北燕謂之䓈青徐淮泗之間謂之芡
d4Z居奄;檢:書檢印窠封題也又檢校俗作撿撿本音斂又姓出姓苑居奄切二|瞼:眼瞼
h4V於琰;黶:面有黑子於琰切八|𥜒:𥜒禳|檿:山桑|厭:厭魅也又於豔切|魘:睡中魘也又於協切|厴:蟹腹下厴|擪:持也又一牒切|酓:酒味苦也
c4R而琰;冉:冉冉行皃又姓孔子弟子冉有而琰切十|姌:長好皃也又奴簟切|苒:草盛皃又荏苒猶展轉也|染:染色周禮染人掌染絲帛又姓石勒時有染閔|𩃵:濡也|䎃:䎃弱羽也|柟:木名|䣸:䤔䣸味薄|𥬕:竹弱之皃|𡜉〈媣〉:諟也
a4R失冉;陝:縣名在弘農亦州名周爲二伯分陝之地即虢國之上陽也秦屬三川郡漢弘農之陝縣後魏改爲陝州失冉切八|睒:暫見|閃:出門皃|𧴭:蕃姓亦作𧵏|覢:蒼頡篇云覢覢視皃|㴸:水動皃|㚒:盜竊懷物|𡟨:不媚
K4R丑琰;諂:諂諛丑琰切二|讇:+上同
h4Z衣儉;奄:忽也止也藏也取也遽也說文覆也大有餘也又姓左傳秦三良奄息衣儉切十七|𩃗:雲狀|䣍:國名|㭺:㭺柰|閹:閹閽|掩:閉取也說文云斂也小上曰掩|揜:說文曰自關以東謂取曰揜一曰覆也|裺:衣縫緣也|晻:晻晻日無光|渰:雲雨皃詩云有渰淒淒|罨:鳥網又於劫烏合二切|弇:蓋也|𣃰:掩也|媕:女有心媕媕也|𤗎:屋𤗎雀也|𡹮:𡹮嵫山日沒處|𣄉〈𣃳〉:掩也又於葉切
P4R慈染;漸:漸次也進也稍也事之端先覩之始也地理志有漸江今之浙江也慈染切十|𥕌:𥕌㘙|蔪:說文曰艸相蔪苞也|𦾶:埤蒼曰麥秀皃|䟅:說文進也|嚵:小食又初咸切|䤔:䤔䣸味薄|鏨:小鑿名|螹:說文曰螹離也|槧:說文曰牘樸也
O4R七漸;憸:憸詖七漸切二|䤘:醋味
N4R子冉;𩟗:食薄味也子冉切一
e4V謙琰;脥:腹下謙琰切一
Z4R時染;剡:縣名屬會稽時染切一
#忝
F5R他玷;忝:辱也他玷切五|䄼:鄉名在濟北蛇丘縣|栝:說文云炊竈木也|銛:取也又鍤屬又音纖|悿:悿弱
H5R乃玷;淰:水流皃乃玷切四|㜤:弱也|𨸱:亭名在鄭|姌:纖細又音冉
E5R多忝;點:點畫多忝切五|玷:玉瑕|𦒻:老人面有黑子|㓠:斫|䍄:說文缺也
G5R徒玷;簟:竹席徒玷切六|扂:閉戶|𠂼:+上同|驔:驪馬黃脊|㶘:㶘淊水滿|橝:屋梠名又音潭
e5R苦簟;嗛:猿藏食處苦簟切四|歉:食不飽又苦減切|慊:慊恨|膁:𦝫左右虛肉處
I5R力忝;稴:禾稀力忝切三|溓:薄冰|𤬓:瓜名
j5R胡忝;鼸:鼠名胡忝切二|㺌:犬吠又胡斬切
O5R青忝;憯:憯悽青忝切又七感切一
d0V兼｟居｠玷｟點｠〈黝〉;孂:竦身皃兼玷切一
D5B明忝;𡕢:腦蓋也俗作𡕫明忝切又亡犯切二|厸:張口
#儼
g8d魯〈魚〉掩〈埯〉;儼:敬也說文曰昂頭也一曰好皃魯掩切七|广:因巗爲屋|𠆲:掩𠆲癡|㢂:陖㢂|礹:𥕌礹|𢇘:齊𢇘|曮:日行
e8d丘广;欦:欠崖丘广切三|𩒥〈𩒣〉:𩒣醜|䇜:小竹
h8d於广;埯:土覆於广切二|𣃧〈𣃳〉:𣃳翳
#豏
j6R下斬;豏:豆半生也下斬切八|減:減耗又古斬切|㺝:犬齧物聲|喊:喊聲|㺌:犬吠不止|𡞣:健皃|𥻇:𥻇塗也|甉:瓦屋
L6R徒減;湛:水皃又沒也安也亦姓後漢有大司農湛重徒減切又直心切三|㴴:+古文|偡:偡然齊整
e6R苦減;㦿:牖也一曰小戶苦減切七|𢜩:𢜩𢜩意不安也|歉:食不飽|撖:撖危|䫡:面長|𣓅:不安|槏:牖傍柱也
d6R古斬;鹼:鹵也古斬切又七廉切四|鹻:鹹也|減:損也又姓漢有減宣|𥳒:竹名出玉篇
U6R士減;瀺:瀺灂士減切三|嶃:高峻又士咸切|嵁:嵁絕山皃
I6R力減;臉:臉䑎羹屬也力減切二|醶:醶䤘醋味
S6R側減;斬:周禮曰秋官掌戮掌斬側減切一
T6R初減;䑎:初減切二|䤘:酢味
i6R火斬;闞〈鬫〉:虎聲火斬切又苦暫切二|欦:笑也
V6R所斬;摻:擥也詩曰摻執子之袪兮所斬切四|㺑:㺑㺝犬吠又山檻切|醦:酢味|𧀵:芟林木也
h6R乙減;黯:黯然傷別皃說文云深黑也乙減切一
i6R呼豏;喊:聲也呼豏切一
M6R女減;𦊔:捕魚網也女減切三|𦌫:+上同|淰:水無波也又乃玷切
K6R丑減;𠐩:癡也丑減切二|旵:日光照也
#檻
j7R胡黤;檻:闌也說文曰櫳也一曰圈胡黤切十|艦:禦敵船四方施板以禦矢狀如牢|壏:堅土|𥽏:䊤也|㔋:利也|濫:泉正出也又盧暫切|𨏊:網車|轞:車聲|㺝:惡犬吠不止也|撖:姓也姓苑云今河內有之
e7R丘檻;䫡:長面皃丘檻切又五咸切一
V7R山檻;㨻:斬取山檻切二|㺑:㺝㺑犬聲
h7R於檻;黤:青黑色於檻切二|𪒠:黃𪒠人名說文曰𪒠者忘而息也
T7R初檻;醶:酢漿初檻切一
i7R荒檻;㺖:小犬吠荒檻切二|豃:開險皃
U7R仕檻;巉:峻巉皃仕檻切一
#范
C9N防錽;范:姓也出南陽濟陽二望本自陶唐氏之後隋會爲晉大夫食采於范其後氏焉防錽切六|範:法也常也式也前也|軓:說文云車軾前也周禮曰立當前軓|笵:說文云法也从竹竹簡書也|犯:干也侵也僭也勝也|𧍙:蜂也案禮云范則冠而蟬有緌字不從虫
D9N亡范;錽:馬首飾西京賦云金錽鏤錫亡范切三|𡕢:腦蓋也俗作𡕩又明忝切|𢨔:刃也
A9N府犯;𦜒:今河東謂淫腫爲𦜒府犯切一
e8d丘犯;凵:張口皃丘犯切二|㧄:以手㧄物
B9N峯犯;釩:釩拂峯犯切一
K8R丑犯;𠑆:𠑆行丑犯切二|𨇧:𨀣足望
#送
QAC蘇弄;送:遣也蘇弄切三|鬆:𩭩鬆髮皃|凇:凍凇冰也
CBO馮貢;鳳:爾雅曰鶠鳳其雌皇郭璞云瑞應鳥雞頭蛇頸燕頷龜背魚尾五彩色高六尺許孔演圖曰鳳爲火精說文曰神鳥也亦州在秦隴西郡地漢改雍州爲涼州魏其地沒蜀蜀平屬雍州本自白馬氏羌所居晉爲仇池國後魏置固道郡又爲南岐州又改爲鳳州馮貢切二|𠤈:+古文
dAC古送;貢:獻也薦也又姓漢有琅邪貢禹古送切十|贛:賜也|𣹟:水名出豫章|虹:縣名在泗州今音絳|羾:至也甘泉宮賦云登椽欒而羾天門|𨹁:從𨹁山名又戶工切|䇨:杯笿名|㔶:小杯名又音感|㯯:+格木說文同上|𧆐:薏苡別名
IAC盧貢;弄:說文玩也盧貢切七|𢙱:𢙱戇愚也|梇:梇棟古縣名在益州|礱:磨礱又音聾|哢:郭云鳥吟|㢅:㢅屏|㳥:水名
EAC多貢;涷:瀑雨又水名出發鳩山多貢切又音東七|凍:冰凍又音東|棟:屋棟爾雅曰棟謂之桴|湩:乳汁巨蒐民取牛馬湩以洗穆天子之足|㼯:㼯𤮭|𩭩:𩭩鬆髮皃|䍶:獸名似羊一角一目出秦戲山又音東
eAC苦貢;控:引也告也苦貢切六|倥:倥傯困皃|悾:誠心又苦紅切|鞚:馬鞚|空:空缺又苦紅切|𤗇:穿垣出文字集略
NAC作弄;糉:蘆葉裏米作弄切七|粽:+俗|䁓:竊視|傯:倥傯|㚇:斂足而飛又子紅切|鯼:石首魚又子工切|緵:小魚罟也又子工切
hAC烏貢;瓮:說文罌也烏貢切五|甕:+上同|𦉥:瓶也說文曰源缾也|罋:+上同|𪖵:鼻塞曰𪖵
OAC千弄;謥:謥詷言急俗作𧩟千弄切二|憁:憁恫
GAC徒弄;洞:空也又洞庭湖徒弄切十六|恫:憁恫不得志|眮:轉目|絧:相通之皃|㓊:冷也|峒:磵深|詷:謥詷|胴:大腸|慟:慟哭哀過也|筒:簫達又音同|駧:馬急走也|衕:通街|迵:過也說文迭也|戙〈㢥〉:船纜所繫|㗢:大歌聲出埤蒼又戶冬戶宋二切|𩐵:鐘聲
FAC他貢;痛:病也傷也亦姓出姓苑他貢切一
LBC直眾;仲:中也爾雅曰中籥謂之仲亦姓風俗通云凡氏於字伯仲叔季是也湯左相有仲虺又漢複姓四氏左傳衛大夫仲叔圉魯有仲顏莊叔宋有司馬仲行寅後漢有山陽仲長統直眾切三|蟲:蟲食物又音沖或作蚛|𩿀:鳥名
ABO方鳳;諷:諷刺方鳳切二|風:+上同見詩
eBO去仲;焪:火乾物也去仲切三|䛪:䛪多言也又詢問也|䠻:使役也亦作㑋
DBO莫鳳;㝱:寐中神游說文云寐而有覺周禮以日月星辰占六㝱之吉凶一曰正㝱無所感動平安自㝱二曰愕㝱驚愕而㝱三曰思㝱覺時所思念之而㝱四曰寤㝱覺時所道之而㝱五曰喜㝱喜悅而㝱六曰懼㝱恐懼而㝱亦作夢莫鳳切五|夢:+上同又亡中切|瞢:雲瞢澤在南郡亦作夢|鄸:邑名在曹|䠢:䠢𧽒疲行皃
iBO香仲;𧽒:䠢𧽒香仲切二|䠗:跳皃又丘幼切
DAC莫弄;𢄐:𢄐縠蓋巾也莫弄切三|霿:天氣下地不應曰霿|艨:艨艟戰船又音蒙
OBC子〈千〉仲;趥:行皃子仲切一
BBO撫鳳;賵:賵賻撫鳳切二|麷:熬麥
PAC徂送;𣀒:敠𣀒不迎自來徂送切二|𠏭:聚也
JBC陟仲;中:當也陟仲切又陟沖切二|衷:又陟沖切
jAC胡貢;哄:唱聲胡貢切五|烘:火皃|港:港洞開通|閧〈鬨〉:兵鬬也又下降切俗作𩰓|蕻:草萊心長
HAC奴凍;齈:多涕鼻疾奴凍切二|癑:痛也
XBC之仲;眾:多也三人爲眾又姓左傳魯大夫眾仲之仲切又音終一
YBC充仲;銃:銎也充仲切一
UBC仕仲;㓽:鍤屬仕仲切一
iAC呼貢;烘:火乾也呼貢切二|戇:𢙱戇愚人
#宋
QCC蘇統;宋:州也即閼伯之商丘也微子封宋二十餘世爲齊楚魏所滅魏得其梁陳留齊得濟陰東平楚得沛梁即今郡地是也隋置宋州爾雅曰宋有孟諸之藪今爲睢陽縣地又姓取微子之所封遂爲氏出西河廣平燉煌河南扶風五望蘇統切一
NCC子宋;綜:織縷子宋切三|䝋:牡豕|錝:金毛
FCC他綜;統:摠也紀也又姓他綜切二|𪎽:黃色
DCC莫綜;雺:天氣下地不應莫綜切一
jCC乎宋;䃔:石聲乎宋切二|㗢:大聲
#用
lDC余頌;用:使也貨也通也以也庸也又姓漢有用蚪爲高唐令余頌切一
RDC似用;頌:歌也詩云吉甫作頌穆如清風又姓出何氏姓苑似用切四|誦:讀誦|訟:爭罪曰獄爭財曰訟|吅:爭言也出文字音義又宣喧二音
CDO扶用;俸:俸秩扶用切四|㡝:款書|縫:衣縫又房容切|捀:灼龜視兆也說文父容切奉也
fDO渠用;共:同也皆也渠用切一
ADO方用;葑:菰根也今江東有葑田方用切亦作湗二|封:又方容切
dDO居用;供:設也居用切又居容切二|龏:又九容切
hDO於用;雍:九州名雍擁也東崤西漢南商北居庸四山之所擁翳也又姓風俗通云文王子雍伯之後於用切又於容切三|灉:河水決出還入爲灉又於容切|壅:加土壅田
JDC竹用;湩:乳汁竹用切又都貢切三|堹:池塘塍埂|諥:言相觸也
NDC子用;縱:放縱說文緩也一曰舍也子用切又子容切二|瘲:病也
KDC丑用;蹱:躘蹱行不正也丑用切二|憃:愚也又丑江切
cDC而用;䩸:毳鞌飾而用切三|𩉪:+上同|𩼅:鮐魚
XDC之用;種:種埴也之用切又之隴切三|偅:儱偅不遇皃|㼿:甕屬
LDC柱用;重:更爲也柱用切又直容切三|緟:繒縷|𨉢:婦人娠也
IDC良用;贚:貧也良用切三|躘:躘踵|儱:儱偅
eDO區用;恐:疑也區用切三|𢖶:+古文|𦶐:䕞𦿆
PDC疾用;從:隨行也疾用切又才容切一
MDC穠用;𢫨:推也穠用切一
#絳
dEC古巷;絳:赤色又州詩譜云晉穆侯遷都於絳曾孫孝侯改爲翼翼晉之舊都後獻公又命爲絳邑秦爲河東郡後魏置東雍州周爲絳州又姓古巷切五|虹:又音紅|降:下也歸也落也又音缸伏也|𡲣:+上同|洚:水流不遵道
jEC胡絳;巷:街巷又姓詩云巷伯胡絳切三|衖:+上同亦作𨜕|閧〈鬨〉:說文云鬬也孟子鄒與魯鬨俗作𩰓
JEC陟降;戇:愚也陟降切一
LEC直絳;䡴:衝城戰車直絳切六|憧:戇憧兇頑皃又尺容切|𢤤:+上同|幢:后妃車幰又宅江切|撞:撞鐘又直江切|艟:短船名
KEC丑絳;𥈄:直視丑絳切二|䚎:視不明也又丑江切
UEC士絳;漴:水所衝也士絳切一
BEC匹絳;肨:脹臭皃匹絳切一
TEC楚絳;䎫:不耕而種楚絳切一
VEC色絳;淙:水出皃色絳切二|㦼:捍船木也
#寘
XFS支義;寘:止也置也廢也支義切八|忮:懻忮害心說文很也|伎:傷害也詩云鞫人伎忒亦作忮|觶:爵受四升或作觗𧣨|伿:惰也又以智切|䚳:快也|㩼:多也|𡽆:山名
CFG毗義;避:違也迴也毗義切一
XFi之睡;惴:憂心也之睡切三|𦥻:杵擊|𦦇:+上同
IFS力智;詈:罵詈力智切六|荔:荔支樹名葉綠實赤味甘高五六丈子似石榴出廣志又音隷|離:去也又力知切|㿛:瘦黑又力計切|珕:刀飾也又力計切|𥶾:䉣𥶾
ZFS是義;豉:鹽豉廣志云苦李作豉是義切六|𢻃:+上同|𢐂:青州人云彈𢐂|鯷:魚名重千斤郭璞云鮎之別名又音提音是|䩃:䩃𩈭面皃出新字林|䊓:黏皃
NFS子智;積:委積也子智切又子昔切四|㰣:歐也|𧂐:草名|𦎸:羊相䍴𦎸
QFS斯義;賜:與也惠也又姓世本云齊大夫簡子賜之後斯義切六|𧀩:草名|澌:盡也禮注云死之言澌也|𣩠:+上同|儩:+上同|杫:𠟼机後漢書尚書郎無被枕杫也
kFq于僞;爲:助也于僞切又允危切一
dFq詭僞;䞈:賭也詭僞切五|垝:坫堂隅可致物|㩻:瘦極又去奇切|攱:攱戴物又居委切|𢈌:毀也
BFK披義;帔:衣帔披義切三|秛:禾租|襬:衣也
AFK彼義;賁:卦名賁飾也亦姓漢有賁赫彼義切又肥墳奔三音七|佊:衺也論語云子西佊哉|詖:譣詖又慧也佞也|貱:益也|陂:傾也易曰無平不陂又音碑|跛:偏任又波我切|藣:草名又旄牛尾舞者所執又音陂
CFK平義;髲:頭髮也南越志云開平縣出髲平義切六|被:被服也覆也書曰光被四表又平彼切寢衣也|鞁:裝束鞁馬|㢰:㢰弓|旇:埤蒼云旌旗又衣服皃|𤿙:𤿙𧛸
IFi良僞;累:緣坐也良僞切一
dFa居義;寄:寄附說文託也居義切三|䐀:𠟼四䐀|徛:石杠聚石以爲步渡
AFG卑義;臂:肱也卑義切一
fFa奇寄;芰:菱也奇寄切八|騎:騎乘又姓燕有騎劫又音奇|鬾:鬼服又音奇|輢:枕輢又於綺切|䝸:䝸貝四向用也|㧘:積也又前智切|汥:水戾|䛋:謀也
OFS七賜;刺:針刺爾雅曰刺殺也釋名曰書姓名於奏白曰刺漢武帝初置部刺史掌奉詔察州成帝更名牧哀帝復爲刺史七賜切又七亦切十|刾:+俗|㢀:偏㢀舍也|朿:木芒|㡹:人相依㡹|𧧒:數諫也|莿:草木針也|庛:周禮車人爲耒庛長尺有一寸鄭玄云耒下前曲接耜者|蛓:毛蟲|䛋:謀也
lFS以豉;易:難易也簡易也又禮云易墓非古也易謂芟除草木以豉切又以益切六|㑥:相輕慢也|貤:物之重次也|伿:惰也|㒾:㒾𠕦面衣又失智切|敡:輕簡爲敡
gFa宜寄;議:謀也擇也評也語也宜寄切六|誼:人所宜也又善也|竩:+上同|𥫃:正也止也|𩈭:䩃𩈭面皃出新字林|義:仁義釋名曰義者宜也裁制事物使合宜也又姓漢有義縱又複姓西戎義渠爲秦所滅後因氏焉漢有光祿大夫義渠安國
BFG匹賜;譬:說文諭也匹賜切二|㵨:蜀漢人呼水洲曰㵨
PFS疾智;漬:浸潤又漚也疾智切八|眥:目眥又在計切|𦎸:䍴𦎸|㧘:說文積也一曰搣頰旁也|㱴:骨也又獸死|髊:髊枯骨見呂氏春秋|𩨨〈骴〉:鳥鼠殘骨|胔:+上同又骨有𠟼也
JFS知義;智:知也又姓晉有智伯知義切三|𣉻:+古文|潪:水名
hFa於義;倚:侍也因也加也於義切又於蟻切三|輢:車輢|陭:陭氏縣在上黨又於奇切
LFi馳僞;縋:繩懸也馳僞切七|膇:重膇病或作㾽|槌:蠶槌|錘:稱錘或作鎚又直危切|腄:縣名在車萊|甀:小口甖|硾:鎮也呂氏春秋云硾之以石
YFi尺僞;吹:鼓吹也月令曰命樂正習吹尺僞切又尺爲切三|䶴:+古文|𥞃:䄲糶
iFa香義;戲:戲弄也施也謔也歇也說文曰三軍之偏也一曰兵也又姓魏志有潁川戲志才香義切二|嚱:聲也
eFW去智;企:望也去智切六|𢺵:傾也|跂:垂足坐又舉足望也|𨑤:避也|蚑:蟲行|吱:行喘息皃
hFW於賜;縊:自經死也於賜切三|㱲:物凋死又脚手小病|螠:螠女蟲案爾雅曰蜆縊女郭璞云小黑蟲赤頭喜自經死故曰縊女字俗從虫
aFS施智;翅:鳥翼施智切十三|翄:-|𦐊:+並上同|施:易曰雲行雨施又式支切|馶:馬強|啻:不啻|鍦:短矛|䗐:爾雅曰蛄䗐強䖹郭璞云今米穀中蠹小黑蟲是也建平人呼爲䖹子|䧴:鳥名本又音支|卶:有大度也|𤖻:几也|㒾:㒾𠕦面衣|翨:鳥翮又居豉切
VFS所寄;屣:履不躡跟孟子曰舜去天下如脫敝屣所寄切又所綺切五|灑:灑埽說文汛也|𩌦:靴屬|襹:褷襹毛羽衣皃|曬:暴也
eFm窺瑞;觖:望也窺瑞切又音決一
hFq於僞;餧:餧飯也於僞切四|萎:萎牛|䍴:羊相䍴𦎸又音委|𣨙:禮記注益州有鹿𣨙
gFq危睡;僞:假也欺也詐也危睡切一
iFq況僞;毀:男八歲女七歲而毀齒況僞切一
hFm於避;恚:怒恨也於避切二|㜇:說文曰不說也
ZFi是僞;睡:眠睡是僞切四|瑞:祥瑞也符也應也說文曰以玉爲信又姓出姓苑|𨿠:鴟鳥別名又音垂|䅜:小積
dFW居企;馶:強也居企切二|翨:鳥翮說文云鳥之彊羽猛者周禮翨氏掌攻猛鳥又音翅
cFi而瑞;䄲:內也而瑞切一
YFS充豉;卶:充豉切有大慶也一
QFi思累;䅗:禾四把也思累切二|瀡:滑也
JFi竹恚;娷:竹恚切飢聲二|諈:諈諉累也
lFi以睡;瓗:玉名以睡切四|纗:絃中絕也|䜜:䜜恨也言|贀:贀㛪也
MFi女恚;諉:諈諉累也女恚切三|㨅:內也又姓|㢻:㢰㢻弓皃
dFm規恚;瞡:規恚切視也一
SFS爭義;𧙁:爭義切衣不展也二|𤿙:𤿙皺皮不展也
iFm呼恚;孈:呼恚切過也一
eFa卿義;㞆:跛也卿義切二|掎:跛也說文曰偏引也又居綺切
#至
XGS脂利;至:到也說文曰鳥飛从高下至地也篆文象形脂利切十三|摯:國名亦持也又姓左傳周禮有摯荒|贄:執贄也周禮云以禽作六贄以等諸臣孤執皮帛卿執羔大夫執鴈士執雉庶人執鶩工商執鷄本亦作摯|鷙:擊鳥|礩:柱下石又音質|䥍:田器說文曰羊箠也端有鐵又先列切|鴲:雀鷇|懥:怒也|䲀:魚名|𩊝:杠絲名亦作𩊞|𩊞:+上同|𢄢:禮巾|𡠗:至也
kGq于愧;位:正也列也莅也中庭之左右謂之位于愧切一
DGK明祕;郿:縣名在岐州明祕切又音眉十|媚:嫵媚|魅:魑魅|鬽:+上同|篃:竹名|蝞:蝞似蝦寄生龜殼中食之益人顏色|嚜:嚜杘小兒多詐獪|䉋:笋冬生名|煝:焅熱|娓:從也又音眉音尾
RGi徐醉;遂:達也進也成也安也止也往也從志也又州名又姓出姓苑徐醉切二十四|彗:帚也一曰妖星又音歲又囚芮切|隧:埏隧墓道也俗作𡑞|襚:贈襚|旞:羽繫旌上|璲:玉也詩曰鞙鞙佩璲鄭玄謂以瑞玉爲佩|檖:陽檖木名一曰赤羅子似梨小酢可食詩云隰有樹檖|𣔾:+上同|𤓫:說文曰塞上亭守㷭火者|𤎩:+上同|燧:+上同又論語云鑽燧改火|澻:田閒小溝|䡵:輰䡵車也|鐆:陽鐆可取火於日中|鐩:+上同|穟:禾秀說文曰禾穗之皃|𦼯:+上同|蔧:王蔧草|𦂁:佩玉緣也|㒸:從意也|𥝩:禾稷成皃說文曰禾成秀人所收从爪禾|穗:+上同|䉌:籧篨|𩏚:囊組名或作韢
NGi將遂;醉:說文曰醉卒也各卒其度量不至於亂也將遂切二|檇:左氏傳曰越敗吳於檇李又遵爲切
QGi雖遂;邃:深也遠也雖遂切九|祟:禍祟|誶:言也詩云歌以誶止|粹:易曰純粹精也|睟:視皃又潤澤皃|𠭥:說文云楚人謂卜問吉凶曰𠭥|賥:貨也|譢:讓也諫也告也問也|𢢝:意思深也
IGi力遂;類:善也法也等也種也說文云種類相似唯犬爲甚从犬頪力遂切九|淚:涕淚俗作㴃|瓃:王器又力追切|𦝭:血祭說文音律|垒:垒塹也出字林|蘱:爾雅曰蘱薡蕫郭璞云似蒲而細|纍:係也|䇐:臨也又力地切|禷:祭名
AGK兵媚;祕:密也神也視也勞也又姓西秦錄有僕射祕宜俗作秘兵媚切十五|毖:告也慎也一曰遠也|閟:閟閉|轡:馬轡說文作𦆕|柲:戟柄左傳有鏚柲|鉍:+上同|泌:泉皃|鄪:邑名在魯|費:+上同|䀣:直視也|䪐:弓絏|邲〈𠨘〉:好皃|粊:惡米又魯東郊地名說文作䉾|䉾:+上同|𡛗:女子
fGq求位;匱:竭也乏也說文曰匣也又姓何氏姓苑云今廬江人求位切十一|蕢:草器也|臾:+上同今作𠀐貴𠳋皆從之|饋:餉也|餽:+上同|𦆠:織餘|櫃:櫃篋|樻:木名又腫節名又口愧切|鞼:繡韋也盾綴革也亦作𩏡|簣:土籠|𩌃:馬韁
BGK匹備;濞:水聲匹備切六|嚊:喘聲|䑄:盛肥|㿙:氣滿|𦤢:敗皃又魚名|淠:水名在汝南
CGK平祕;備:備具也防也咸也皆也副也慎也成也又姓風俗通云宋封人備之後平祕切十七|俻:+俗|𤰇:說文具也|𤰈:+古文|𡚤:怒也又一曰迫也|奰:+上同見經典省|䑄:壯大|糒:糗也|犕:牛具齒|絥:說文曰車絥也|鞴:+上同|韍〈𩎓〉:+上同|贔:贔屓壯士作力皃|𣖾:木名出蜀其穗可食|㣁:以筋帖弓|䨽:鳥如梟又孚尾切|㸢:牑模
dGq俱位;媿:慙媿俱位切六|愧:-|聭:-|謉:+並上同|騩:馬色淺黑|䁛:大視
VGi所類;帥:將帥也曹憲文字指歸云佩巾也所類切又所律切二|率:鳥網也又所律切
eGq丘愧;喟:大息也丘愧切又苦拜切九|嘳:+上同|樻:樻梧椐木腫節可爲杖|䯣:膝加地也|䰎:髻屈髮也|腃:筋節急也|䙡:紐也俗又作𧝷|尯:㝿也|𨌗:地名在洛陽
iGq許位;豷:豕息也許位切二|燹:火也字統音銑
ZGS常利;嗜:嗜慾常利切六|𩝙:-|𨢍:+並上同|視:看視又音是|眎:-|眂〈眡〉:+並古文
IGS力至;利:吉也說文銛也亦州名華陽國志昔蜀王封弟於漢中号曰苴侯因命其邑曰葭萌秦滅蜀置巴蜀二郡先主改葭萌爲漢壽屬梓潼郡晉爲晉壽南齊分置東晉壽郡於烏奴今州城是又於其郡置西益州梁改爲黎州元帝又改爲利州又舍利獸名亦姓風俗通云漢有利乾爲中山相力至切八|𥝤〈𥝢〉:+古文|䬆:烈風說文音栗|莅:臨也亦作涖|涖:涖涖水聲|痢:病也|䚕:求也|䇐:臨也
MGS女利;膩:肥膩女利切四|𦡸:+上同出道書|䁊:目深皃又一活切|䣵:重釀酒也
BGG匹寐;屁:氣下洩也匹寐切二|䊧:+上同
gGa魚器;劓:割鼻漢文帝除𠟼刑劓者笞三百魚器切一
JGS陟利;致:至也說文曰送詣也陟利切十五|懫:止也|疐:礙不行也又頓也詩曰載疐其尾疐跲也|𢷟:-|𨆫:+並俗|躓:礙也頓也說文跲也|𨎌:車前重也|輊:+上同|騺:馬腳屈也|䞃:賑也亦貝也|𣱐:仆也又於進切|懥:怒也恨也|㨖:刺也又劫財也|質:交質又物相贅又之日切|駤:𩧅駤
eGW詰利;棄:說文捐也詰利切五|弃:+古文|夡:夡多|㞓:身欹坐一曰尻|蟿:蟿螽蟲名
LGS直利;緻:密也直利切十二|稚:幼稚亦小也晚也又姓史記云湯後因國爲姓|遟:待也又直尸切|稺:晚禾|𦃘:刺𦃘針縫也|𩹈:魚名|治:理也又直之切|𠊷:會物|𢴧:當也對也|謘:語謘|𩋩:履𩋩底也|𦥐:+上同
DGG彌二;寐:寢也臥也息也彌二切二|媢:夫妬婦又音冒
KGS丑利;杘:籰柄也又嚜杘多詐丑利切八|𣐉:+上同|誺:不知|𦥊:叨𦥊也|訵:陰知亦作呬|𡳭:分蠶|跮:跮踱乍前乍卻|𧩼:笑也
dGa几利;冀:九州名爾雅曰兩河閒曰冀州續漢書安平國故信都郡光武師自薊南行太守任光開門出迎今州城是又姓左傳晉大夫冀芮几利切八|兾:+上同見經典省|覬:覬覦希望|穊:稠也|驥:騏驥|𩥉:+上同|洎:𠟼汁又音臮|懻:強力皃
fGa具冀;臮:眾與詞也具冀切七|暨:及也至也与也|鱀:魚名鼻在頟上又音忌|洎:潤也及也|垍:堅土|塈:息也又仰塗也|𣽍:水名
fGm其季;悸:心動也其季切五|𠊾:左右兩視也|猤:壯勇皃|痵:病中恐也|𡬄:熟寐也
OGi七醉;翠:字林云青羽雀又翠微亦姓急就章有翠鴛鴦七醉切三|濢:下濕|臎:鳥尾上𠟼
cGS而至;二:說文云地之數也而至切五|弍:+古文|貳:副也亦攜貳變異也疑也敵也又姓後秦錄有後魏平陽太守貳塵|樲:酸棗|髶:髮飾
NGS資四;恣:縱也資四切二|𣣌:說文曰戰見血曰傷亂或爲惛死而復生爲𣣌又七利切
OGS七四;次:次第也亦三宿曰次又姓呂氏春秋荊有勇士次非七四切九|䳐:鳥名似梟人面山居所經國國必亡出山海經|佽:佽飛漢武官名又助也利也代也遞也及也|䰍:以漆塗器|絘:績所未緝者|𩾔:鳥名|𧊒:蟲似蜘蛛|𣣌:又資四切義見上文|䯸:髮也
hGa乙冀;懿:美也大也溫柔聖克也又姓後秦錄有吏部郎懿橫秦錄有吏部熱懿橫乙冀切七|饐:食傷熟也|㙪:陰皃|欭:喑欭歎也|鷧:鷧鸕鶿鳥|撎:拜舉手左傳注云若今之揖|亄:貪也
QGS息利;四:說文曰陰數也象四分之形息利切十四|亖:+籀文|𦉭:+古文|肆:陳也恣也極也放也說文从隶極陳也又姓何氏姓苑有漁陽太守肆敏|𩬶:+上同|柶:角匕大喪用之|泗:水名在魯說文曰受沛水東入淮又涕泗也|牭:牛四歲|𧳙:爾雅云狸子𧳙|㣈:鼠名說文曰㣇屬㣇羊至切俗作𨽼|駟:一乘四馬|𦞤:腦蓋|蕼:堇也說文曰赤蕼也|肂:埋棺坎下
eGa去冀;器:器皿史記曰舜作什器於壽丘又姓出姓苑去冀切一
dGm居悸;季:昆季也又少也小稱也亦姓左傳魯有季友又漢複姓四氏晉有唐邑大夫季連齊有鬼方氏第六子名季連其後氏焉晉有祁邑大夫季瓜忽宋有季隨逢世本云周有八士季隨季騧之後騧或作瓜又有魯大夫齊季窺昔齊公子季奔于楚楚遂号爲齊季氏居悸切二|瞡:視皃
CGG毗至;鼻:說文曰引气自畀也毗至切十|比:近也又阿黨也又房脂必履扶必三切|枇:細櫛|𤹝:足氣不至|坒:地相次比也亦音邲|襣:司馬相如著犢襣裩|䃾:以豚祠司命也|䫁:首子|䑄:盛也|芘:草名
iGm香季;䁤:恚視也香季切三|婎:醜也又許葵切|睢:恣睢暴戾又許葵切
AGG必至;痹:腳冷濕病必至切六|𢌿〈畀〉:与也|庇:庇廕|𦸣:鼠莞可爲席|䃾:以豚祠司命也|比:近也併也
PGi秦醉;萃:集也聚也秦醉切六|顇:顦顇|悴:憔悴憂愁|㱖:止㱖|䆊:稻禾黏也|瘁:病也
GGS徒四;地:土地說文曰元气初分輕清陽爲天重濁陰爲地萬物所陳𠛱也元命包曰地者易也言養萬物懷任交易變化含吐應節故其立字土力於一者爲地又虜複姓有地連氏地倫氏徒四切二|墬:+籀文
iGa虛器;齂:鼻息也虛器切六|㕧:呻也又火尸切|屓:贔屓|呬:息也又丑致切陰知也|𤡬:夏后氏有澆𤡬寒浞子名|䨳:說文云見雨而止息曰䨳
lGS羊至;肄:習也嫩條也羊至切八|殔:釋名曰假葬於道曰殔說文云瘞也|㡼:倉也|貤:重物次第|勩:勞也|隶:本也及也又音代|㣇:說文曰脩豪獸一曰河內名豕也又徒計切爾雅作貄|𥿫:重多
bGS神至;示:垂示神至切五|諡:易名又申也說文作謚|謚:+上同又音益|眎:呈也|貤:重物次第
PGS疾二;自:從也用也由也率也疾二切二|嫉:妬也又音疾
LGi直類;墜:落也直類切三|懟:怨也|鎚:好銅半熟
YGi尺類;出:尺類切又昌律切一
lGi以醉;遺:贈也以醉切又音惟七|𤀷:𤀷清侯出漢書王子侯表|𢣘:忘也出廣雅|蜼:爾雅曰蜼仰鼻而長尾蜼似獮猴鼻露向上尾長數尺末有歧雨即自縣於樹以尾塞鼻又余救切|瞶:目疾|𧔥:蜰𧔥|䗽:蛘䗽蟲名
iGm火季;侐:靜也詩云閟宮有侐火季切又火逼切一
JGi追萃;轛:車橫軨追萃切一
YGS充自;痓:惡也充自切一
aGS矢利;屍:似皴皃也矢利切二|䛈〈詄〉:詄志
TGi楚愧;㿷:粟體楚愧切一
aGi釋類;㽷:病皃釋類切二|𥤼:方言云深也趙魏閒語
#志
XHS職吏;志:意慕也詩云在心爲志爾雅曰骨鏃不翦羽謂之志職吏切七|娡:有莘氏之女𩨬娶之謂之女娡|䓌:遠䓌|誌:記誌|痣:黑子|織:織文錦綺屬又音職|識:標識見禮本音式
LHS直吏;值:持也措也捨也當也直吏切五|植:種也又巿力切|治:理也又丈之切|㨁:㨁投|𠍜:或也
RHS祥吏;寺:寺者司也官之所止有九寺釋名曰寺嗣也治事者相嗣續於其內又漢西域白馬駝經來初止於鴻臚寺遂取寺名剏置白馬寺祥吏切五|嗣:繼也又姓風俗通云衛嗣君後|孠:+古文|飤:食也|飼:+上同
OHS七吏;蛓:蛓毛蟲有毒七吏切四|蚝:-|螆:-|𧉠:+並上同
QHS相吏;笥:篋也圓曰簞方曰笥竹器也相吏切四|伺:伺候也察也|思:念也又音司|覗:覗覰也
aHS式吏;試:用也式吏切四|弑:大逆亦作殺|幟:旗幟又音熾|僿:史記云小人以僿
SHS側吏;胾:大臠也側吏切六|椔:木立死亦作檣|事:事刃又作剚倳|剚:+上同|倳:+上同又置也|鶅:東方雉名又音甾
IHS力置;吏:說文曰治人者也力置切二|𢟤:憂也
PHS疾置;字:春秋說題辝曰字者飾也說文乳也又愛也疾置切六|牸:牝牛|孳:孳尾乳化曰孳交接曰尾|茡:爾雅曰茡麻母郭璞云苴麻成子者|芓:+上同|孖:雙生子又音咨
KHS丑吏;眙:直住視丑吏切五|佁:佁儗不前|䰡:癘鬼|𦥊:忿戾|誺:不知
cHS仍吏;餌:食也說文粉餅也仍吏切十六|𩱓:+上同|珥:耳飾|衈:開刑書殺雞血祭名周禮注云割牲耳血及毛祭以爲刉衈|毦:氅毦羽毛飾也|咡:口吻|刵:截耳|佴:次也|誀:誘也|洱:水名|䎶:以牲告神神欲聽曰䎶也|㛅:女字|䏪:筋腱|䣵:重釀|眲:耳目不相信也|𦖢:聽音不敢言也
VHS疎吏;駛:疾也疎吏切七|使:又色里切|𣳪:水名在河南|𧳅:郭璞曰今江東呼貉爲𧲱𧳅|𩰢:烈也|𨽄:山阜突也|𥥥:穴也
THS初吏;廁:說文圊也釋名曰廁雜也言人雜廁其上也又閒也次也初吏切一
lHS羊吏;異:奇也說文分也羊吏切七|异:异哉歎也退也舉也|潩:水名在河南密縣出文字音義|食:人名漢有酈食其又音蝕|已:過事語辝又去也弃也成也|䔬:連翹草名|廙:恭也敬也
JHS陟吏;置:安置也驛也設也說文赦也陟吏切二|𢐂:青州呼彈弓
ZHS時吏;侍:近也從也承也時吏切三|蒔:種蒔|秲:+上同
UHS鉏吏;事:使也立也由也鉏吏切又側吏切二|𩛌:玉篇云嗜食
fHe渠記;忌:忌諱又畏也敬也止也憎惡也亦姓周公忌父之後出風俗通渠記切十三|邔:古縣名在襄陽|惎:教也一曰謀也說文毒也|䋟:連針|鱀:魚名又音臮|鵋:鵋䳢鵂鶹鳥今之角鴟|𧳙:狸子也又音四|誋:告也信也說文誡也|諅:志也說文忌也周書曰上不諅于凶德|梞:梞柎|𢍁:舉也說文音其|帺:繫也又音其|𥭜:竹名
YHS昌志;熾:盛也昌志切八|饎:方言云熟食也說文云酒食也|𩜮:+說文同上|糦:+大祭亦稷也說文同上|幟:又音試音志|𡑠:赤土|哆:哆聲|埴:黏土
hHe於記;意:志也又姓於記切四|鷾:鷾鴯玄鳥也出莊子|𠃸〈亄〉:貪也又音乙|䵝:深黑
dHe居吏;記:記志也說文疏也居吏切一
iHe許記;憙:好也許記切二|嬉:可嬉美姿顏也又音熙
gHe魚記;䰯:恐也魚記切六|豙:豕怒毛豎也出說文|㘈:唭㘈無聞見也|譺:啁譺|㽈:大甖|儗:佁儗不前
eHe去吏;亟:數也遽也去吏切又紀力切三|唭:唭㘈無聞見也|䀈:䀈居獸名似蝟而赤尾
#未
DIO無沸;未:辰名爾雅曰太歲在未曰協洽無沸切八|味:五味酸醎甘苦辛周禮瘍醫以酸養骨以辛養筋以醎養脉以苦養氣以甘養𠟼以滑養竅|菋:五味子藥名五行之精|𩑵:面前|䊊:饘也亦作𥹹|沬:水名|鮇:魚名|𡶎:山名
dIu居胃;貴:尊也高也釋名曰貴歸也物所歸仰也說文作䝿亦姓出自陸終之後風俗通有貴遷爲廬江太守居胃切三|瞶:極視|𠐽:使也
kIu于貴;胃:腸胃說文作𦞅穀府也于貴切十七|謂:言也告也說文報也|㥜:怫㥜不安也|媦:楚人呼妹公羊傳曰楚王之妻媦|𦩝:運船|緯:經緯又姓|彙:類也說文作𢑷蟲也似豪豬而小爾雅曰彙毛刺是也|蝟:+說文同上|渭:水名亦州名書曰終南敦物至于鳥鼠鳥鼠山名渭所出也秦伐義渠始置隴西郡後魏莊帝置渭州因水爲名也|煟:火光|𩹂:魚名山海經曰樂游之山桃水多𩹂魚似蛇而四足|𨾂:獸似鼠|緭:緭繒也|𢍚:草木𢍚孛也|𦳢:草名|䬑:大風|圍:繞也又音韋
gIu魚貴;魏:魏闕又州名夏觀扈之國春秋時晉地秦爲東郡隋爲武陽郡武德初平竇建德改置魏州亦姓本自周武王母弟受封於畢至畢萬仕晉封魏城後因氏焉出鉅鹿任城二望魚貴切二|犩:犪牛𠟼數千斤又魚歸切
AIO方味;沸:詩曰觱沸檻泉箋云觱沸者謂泉涌出皃方味切十一|疿:熱生小瘡|芾:毛萇詩傳曰蔽芾小皃|茀:+上同|誹:謗人又音非|鯡:魚子|㹃:覆耕|𩰾:湯𩰾|𧙂:蔽膝|䛍:言急|䟛:行疾
BIO芳未;費:耗也惠也芳未切又房未冰備二切六|髴:髣髴|靅:靉靅雲布狀也|𣙿:木名|昲:日光又物乾也|䊧:失氣
eIu丘畏;𥽂:細米丘畏切三|䙡:䙡紐|𧝷:+俗
hIu於胃;尉:候也說文作㷉云从上案下也从𡰥又持火所以申繒也通俗文曰火斗曰尉俗作熨又尉氏縣鄭大夫尉氏邑也亦云鄭之別獄又姓左傳鄭大夫尉止於胃切又紆物切十二|㷉:出說文|熨:+俗見上注|慰:安慰|畏:畏懼|罻:罻網|犚:牛也|蔚:茺蔚|螱:飛蟻|𧕈:+上同|褽:衣袵也|䲁:魚名
iIu許貴;諱:說文誋也許貴切四|卉:草摠名詩曰卉木萋萋又音虺|芔:+古文|泋:水波汶也
CIO扶涕〈沸〉;𥝋:獸名說文曰周成王時州靡國獻𥝋人身反踵自笑笑即上脣掩其目食人北方謂之土螻爾雅曰狒狒如人被髮迅走一名梟羊俗謂之山都今交州南康山中有之郭璞讚云狒狒怪獸披髮握竹獲人則笑脣蔽其目終乃號咷反爲我戮扶涕切二十四|𦦔:-|狒:+並上同|㵒:㵒渭水溢|腓:又音肥|怫:怫㥜又扶物切|菲:菜可食又霏斐二音|屝:草屩黃帝臣於則所造也|蜚:蜚盧蟲也一名蜰即負盤臭蟲也又獸名山海經曰蜚如牛白首一目蛇尾行水則竭行草則枯見則有兵役郭璞讚云蜚之爲名體似無害所經枯竭甚於鴆厲萬物攸懼思尒遐逝|𧕿:+上同|䨾:隱也陋也|翡:赤羽雀也|𡌦:塵也|萉:枲屬|𩇪:𩇪隱|痱:熱瘡|䠊:刖足亦作剕|㔗:壯勇之皃|䆏:稻不黏也|費:姓也夏禹之後出江夏後漢汝南費長房孫盛蜀譜云益州諸費有名位者多又後魏書費連氏後改爲費氏|𧌘〈蜰〉:蜰𧔥神蛇|𥄱:目不明或作䀟|黂:爾雅曰黂枲實禮曰苴麻之有黂又音肥|蟦:𧓉螬蟲也
dIe居豙;既:已也盡也又姓吳王夫既之後居豙切七|暨:諸暨縣在越州又其冀切|禨:福祥|溉:溉灌又古代切|𣢆:幸也不便言也|旡:飲食逆氣不得息也|蔇:說文曰艸多皃
gIe魚既;毅:果敢也魚既切七|𢖫:怒也|豙:豕怒毛豎也|𧅙:說文曰煎茱萸也|藙:+上同|顡:說文曰癡顡不聰明也|䉨:竹名
eIe去既;氣:氣息也去既切說文本音欷五|炁:+同上出道書|气:与人物也說文曰雲气也今作乞又去訖切|盵:姓也出纂文|䀈:䀈居獸似蝟尾赤也
iIe許既;欷:歔欷許既切十八|唏:啼也|塈:仰塗|愾:大息也又苦愛切|氣:說文曰饋客芻米春秋傳曰齊人來氣諸侯|餼:-|䊠:+並上同見說文|鎎:怒戰|𢟪:息也|熂:燹火|黖:黖菲黑也|霼:靉霼雲狀|摡:拭也|䀈:獸名又音氣|𧱲:豕息|䮎:馬走|犔:牛病|忥:靜也說文曰癡皃
fIe其既;䤒:秫酒名其既切二|幾:未已又音蟣音機
hIe於既;衣:衣著於既切又音依一
#御
gJe牛倨;御:理也侍待也進也使也又姓左傳有大夫御叔牛倨切三|馭:使馬也|語:說也告也又魚巨切
IJS良倨;慮:思也又姓良倨切九|勴:助也|𥶌:舟中簀𥶌見方言|𠣊:助也導也|鑢:錯也|櫖:林櫖山林又山櫐也|𩥆:傳馬|𡾅:山名|𦊼:網𦊼
dJe居御;據:依也持也引也案也亦姓出姓苑居御切十|鋸:刀鋸古史考曰孟莊子作鋸|倨:倨傲|踞:蹲又踑踞大坐|椐:靈壽木名又居祛二音|鐻:樂器形以夾鐘削木爲之出埤蒼說文与虡同|澽:乾水又音遽|𧣻:角似雞距|䱟:魚名|豦:獸大如狗似猴多𩓾好奮迅其頭能投石擲人出建平山又音渠
OJS七慮;覰:伺視也七慮切六|䁦:+上同|刞:耕土起亦作耝|坥:螾場又七余切|䏣:蠅䏣又七余切|蜡:周禮有蜡氏又音乍
eJe近〈丘〉倨;㰦:欠去近倨切九|去:離也又卻呂切|麮:麥汁|呿:張口皃|鼁:鼁𪓰似蝦蟆居陸地|胠:脅也又去魚切|㧁:閉也又口荅切|䒧:草名|𩿟:鳥名
ZJS常恕;署:書也厂解署部署也常恕切四|藷:藷藇又音諸|薯:+薯蕷俗|曙:曉也
aJS商署;恕:仁恕商署切四|庶:眾也冀也侈也幸也又庶幾也亦姓|樜:木名|㵂:水名
JJS陟慮;著:明也處也立也補也成也定也陟慮切又張略長略二切二|箸:+上同
XJS章恕;䬡:飛舉也章恕切九|翥:+上同|𤳯:筐𤳯|䭖:犬糜又豕食|䘄:蟲名爾雅云翥醜罅剖母背而生或作䘄|庶:周禮有庶氏掌除毒蟲又音恕|𤳐:畚也|𡻠:番山|㫂:斫也
VJS所去;疏:記也亦作疎所去切三|捒:裝捒又色句切|㫹:明也
hJe依倨;飫:飽也厭也賜也說文本作𩜈燕食也依倨切十|𩜏:+上同|瘀:血瘀|鄔:縣名在太原又音塢|醧:私醼|𢮁:𢮁擊|淤:濁水中泥也又音於|菸:臭草|棜:無足樽也|𡫽:假寐也
LJS遟倨;箸:匙箸遟倨切四|筯:+上同|㾻:痴㾻不達又丑御切|除:去也見詩
fJe其據;遽:急也疾也亦戰慄也窘也卒也其據切五|勮:勤務也又懼也疾也|詎:又其呂切|醵:斂錢飲酒又音渠又其虐切|澽:乾澽
QJS息據;絮:說文曰敝緜也息據切又抽據尼恕二切一
UJS牀據;助:佐也益也牀據切三|耡:又士魚切|麆:爾雅云麕牡麌牝麋其子麆
NJS將預;怚:憍也將預切二|沮:沮洳漸濕亦作𣶝
SJS莊助;詛:呪詛亦作𥛜莊助切二|阻:馬阻蹄又莊所切
cJS人恕;洳:沮洳說文作𣹤漸濕也人恕切三|茹:飯牛又菜茹也|如:又尒諸切
lJS羊洳;豫:逸也備先也辨也早也安也猒也敘也又州名尚書禹貢曰荊河爲豫州釋名云豫州在九州中京師東常安豫也秦爲三川郡漢爲河南郡後魏置司州又改爲豫州亦獸名象屬又姓晉有豫讓羊洳切二十|預:安也先也廁也樂也佚也猒也怠也|譽:稱美也又姓晉書有平原太守譽粹又音余|礜:礜石藥名蠶食之肥鼠食之死|𩦡:馬疾行皃|輿:車輿又方輿縣名又音余|鸒:爾雅曰鸒斯鵯鶋郭璞曰雅烏也小而多羣腹下白|悆:悅也|𪋮:大鹿|𣝑:舁食者或作轝|藇:藷藇又音序|蕷:+薯蕷俗|穥:穥穥黍稷美也|𡱣:履屬|忬:安也|歟:歎也又音余|悇:憂懼|與:參與也|澦:灩澦水名|𡒊:高平
iJe許御;噓:吹噓許御切又音虛一
MJS尼據;女:以女妻人也尼據切二|絮:姓也漢有絮舜
TJS瘡（創）據;楚:楚利又木名出歷山瘡據切又瘡所切二|儊:儊不滑也
YJS昌據;處:處所也昌據切又音杵二|䖏:+俗
KJS抽據;絮:和調食也抽據切三|悇:憛悇憂也|㾻:痴㾻不達
RJS徐預;𡲁〈𡱣〉:履屬徐預切一
#遇
gKu牛具;遇:不期而會又姓何氏姓苑云東莞人風俗通云漢有遇沖爲河內太守牛具切七|寓:寄也|庽:+上同|媀:媀妬也女子妬男子|𤸒:疣病|禺:獸名毋猴屬也又音愚|䴁:䴁鼠鳥名
hKu衣遇;嫗:老嫗也衣遇切三|蓲:荎也|饇:飽饇
ZKi常句;樹:木摠名也立也又姓姓苑云今江東有之後魏官氏志樹洛干氏後改爲樹氏常句切五|𦒸:老人行皃|澍:時雨又音注|尌:立也又音住|𠊪:+上同
LKi持遇;住:止也又姓出姓苑持遇切三|牏:築垣短板|逗:姓也出何承天纂文又音豆
CKO符遇;附:寄附又姓晉書有附都符遇切十一|坿:白坿說文益也|祔:祭名亦合葬也|賻:贈死也助也|駙:駙馬都尉官名漢武帝置掌駙馬晉尚公主者並加之駙副馬也一曰近也又疾也|鮒:魚名|䠵:䠵䠼著衣也|蚹:蚹蛇腹下橫鱗可行者又爾雅曰蚹蠃螔蝓即蝸牛也|跗:古之醫人俞跗出史記|𠪻:小巵有蓋|胕:肺胕心膂
XKi之戍;注:灌注也又注記也之戍切十六|疰:疰病|罜:小罟|㹥:黃犬黑頭|鑄:鎔鑄又姓堯後以國爲氏|馵:馬後左足白|註:註射出埤蒼又音駐|炷:燈炷|澍:時雨又殊遇切|霔:霖霔|㺛:鄉名在河南|䎷:䎷𩕏又音赴|祩:詛也祝也|𠴦:邑名|䪒:皮袴|蛀:蛀蟲
dKu九遇;屨:履屬方言曰履自關而西謂之屨九遇切十|句:章句又音溝音構|蒟:蒟醬又音矩|絇:絲絇|瞿:視皃又音衢|𥉁:目驚𥉁𥉁然出埤蒼|怐:恐怐|䈮:竹名|邭:邑名|䀠:左右視也
iKu香句;昫:日光說文曰日出溫也北地有昫衍縣香句切六|煦:+上同|酗:醉怒亦作䣱|呴:吐沫|姁:姁嫗|𧏺:幺蠶
aKi傷遇;戍:遏也舍也從人荷戈也傷遇切八|腧:五藏腧也|輸:送也又式朱切|𧼯:馬𧼯前也|䩱:刀䩙|隃:鴈門|䠼:䠵䠼|㲓:㲓毛
lKi羊戍;裕:饒也道也容也寬也羊戍切七|䘱:+上同|覦:覬覦又音俞|諭:譬諭也諫也又姓東晉有諭歸撰西河記二卷何承天云喻音樹豫章人|喻:+上同|籲:呼也又和也見書傳|𠕦:面衣
cKi而遇;孺:稚也爾雅曰屬也說文曰乳子也一曰輸孺尚小也而遇切四|𡦗:+俗|擩:擩莝手進物也|㹘:牛莖
BKO芳遇;赴:奔赴爾雅曰至也說文曰趨也芳遇切十一|𠓗:急疾也|䞯:+上同|䎷:䎷𩕏也又音注|豧:豕聲|簠:簠簋又甫于方武二切|訃:告喪也又至也|䞳:僵也說文音匐|仆:僵說文曰頓也|䟔:說文曰趣越皃|婏:兔子曰婏又孚万切
DKO亡遇;務:事務也又強也遽也趣也又姓列仙傳有務光亡遇切十四|婺:婺女星名|霧:元命包曰陰陽亂爲霧爾雅曰地氣發天不應曰霧釋名曰霧冒也氣蒙冒覆地之物也|霚:+上同見說文|騖:馳也奔也驅也|𦎦:六月生羔|䨁:雞雛|蝥:蠡名亦作𧐙|𨂣:長跪又拜|𦆞:繅淹餘也|㡔:髮巾|嵍:丘也|敄:說文強也|鶩:鳥名又音目
NKi子句;緅:青赤色子句切又子侯切二|足:足添物也本音入聲
fKu其遇;懼:怖懼其遇切四|具:備也辦也又姓左傳有具丙|埧:堤塘|臞:瘦又音瞿
kKu王遇;芋:一名蹲鴟廣志云蜀漢以芋爲資凡十四等有君子芋大如斗魁如杵𥰠其車轂鋸子旁巨青邊四等多子王遇切五|雨:詩曰雨雪其霶又音禹|羽:鳥翅也又五聲宮商角徵羽晉書樂志云宮中也中和之道無往而不理商強也謂金性之堅強角觸也象諸陽氣觸動而生徵止也言物盛則止羽舒也陽氣將復萬物孳育而舒生又音禹|䨒:說文曰水音也|吁:疑怪辭也
PKi才句;埾:垛也才句切二|聚:又秦雨切
VKi色句;捒:裝捒色句切又所據切三|數:筭數周禮有九數方田粟米差分少廣商功均輸方程贏不足旁要也世本曰隷首作數又色矩色角二切又音速|㡏:裁殘帛也
AKO方遇;付:与也方遇切六|賦:賦頌詩有六義二曰賦釋名曰敷布其義謂之賦漢書曰不歌而誦曰賦又斂也量也班也稅也|傅:相也亦姓本自傅說出傅巖因以爲氏出北地清河二望|𩬙:露髻|陚:丘名|搏:擊也又布莫切
OKi七句;娶:說文曰取婦也七句切二|趣:趣向又親足七俱倉苟三切
JKi中句;註:解也中句切又音注九|鉒:置也又送死人物也|駐:止馬|軴:車軴|住:停手又長句切|𨙔:不行|壴:說文云陳樂也|咮:鳥聲|亍:步止也
eKu區遇;驅:區遇切又羌愚切二|𤛐:牛名
TKi芻注;菆:鳥窠芻注切三|䜴:䜴勇|䐢:膳也
KKi丑注;𨳳:直開也丑注切二|𢨸:+同上
QKi思句;尠:思句切少也又息淺切一
IKi良遇;屢:數也疾也良遇切二|𡀿:𡀿𡀿吳人呼狗方言也
#暮
DLC莫故;暮:日晚也冥也又姓出何氏姓苑莫故切六|慕:思慕又虜複姓二氏前燕錄云昔高辛氏游於海濱留少子厭越以居北夷邑于紫蒙之野号曰東胡秦西漢之際爲匈奴所敗分保鮮卑山因山爲号至魏初莫護跋率部落入居遼西時燕代多冠步搖冠跋好之乃斂髮襲冠諸部因謂之步搖後音訛爲慕容焉跋孫涉歸進拜單于遵循華俗自云慕二儀之德繼三光之容以爲氏歸子廆據遼東稱王僭号燕後又有將軍慕輿虔|募:召也|墓:墳墓|慔:勉也|𥰻:竹筥
GLC徒故;渡:濟也過也去也徒故切五|斁:猒也一曰終也詩云服之無斁又音亦|鍍:金飾物也|度:法度又姓出後漢荊州刺史度尚又徒各切|𥯖:蠶𥯖
ILC洛故;路:道路亦大也周禮曰合方氏掌達天下之道路爾雅曰一達謂之道路又姓本自帝摯之後出陽平襄城陳留安定東陽河南等六望洛故切十三|露:說文曰露潤澤也五經通義曰和氣津凝爲露也蔡邕月令曰露者陰之液也又露見也亦姓風俗通云漢有上黨都尉露平|潞:水名又州名春秋時初爲黎國後爲狄境古黎亭也周爲潞州隋爲韓州又爲上黨郡唐爲潞州開元中陞爲大都督府又縣名在幽州|輅:車輅釋名曰天子乘玉輅以玉飾車也輅亦車也謂之輅者言行於道路也|鷺:爾雅曰鷺春鉏郭璞云白鷺也頭翅背上皆有長翰毛江東人取以爲睫㰚名之曰白鷺縗|璐:玉名|賂:遺賂也|簬:竹名|簵:+上同|虂:蔠葵蘩虂|𤻱:𤸵𤻱痞病|㿖:+上同|𦌕:𦌕䍛取魚具也
ELC當故;妒:妬忌當故切十二|妬:+上同|秅:禾束又縣名在濟陰或作秺|秺:+上同|奼:美女|𦘴:𦘴胍腹大|𤴱:乳病|㓃:奠酒爵也|蠹:食木蟲也|螙:+古文|殬:敗也|斁:+上同
FLC湯故;菟:菟絲草名又虜複姓後魏書有菟賴氏湯故切四|兔:獸名崔豹古今注云兔口有缺尻有九孔論衡曰兔舐毫而孕及其生子從口而出說文云象踞後其尾形兔頭與㲋頭同|吐:歐也又湯古切|鵵:木鵵鳥有毛角
dLC古暮;顧:迴視也眷也又姓出吳郡古暮切十五|頋:+俗|雇:本音戶九雇鳥也相承借爲雇賃字|稒:稒陽縣在五原|故:舊也事也常也又姓出姓苑|酤:賣也又旨姑|沽:+上同|痼:太病|固:堅也一也常也故也四塞也|錮:錮鑄又禁錮也亦鑄塞也|㽽:小兒口瘡|鯝:魚肚中腸|䍛:𦌕䍛取魚具也|棝:射鼠斗也|凅:凝也閉也
gLC五故;誤:謬誤五故切十四|悞:+上同|寤:覺寤|忤:逆也|啎:+上同|迕:遇也|遻:+上同|晤:明也朗也|悟:心了|逜:干逜|窹:廣雅云竈名|捂:斜柱也又枝捂也|娛:娛樂也又五于切|䎸:聽也
jLC胡誤;護:救也助也胡誤切十七|瓠:匏也又瓠子隄名亦姓淮南子有瓠巴善鼓琴|嫭:美好|婟:婟嫪戀惜也出聲類|頀:大頀湯樂周禮作濩|互:差互俗作㸦餘倣此|濩:布濩|䇘:所以收絲|冱:寒凝|枑:門外行馬|䨼:青屬|韄:佩刀飾也|𧥮:誌也認也|鱯:魚名|擭:布擭猶分解也|𦊂:兔網|𦬚:草名
QLC桑故;訴:訟也毁也說文作𧩯告也桑故切十五|愬:+譖也說文同上|𧪜:+向也說文同上|泝:逆流而上廣雅曰泝斗舟中抒水斗|遡:+說文同上|素:列子曰太素者質之始也又空也故也帛也說文作𦃃白緻繒也又虜複姓二氏後趙錄有宜陽公素和明又後魏書云素黎氏後改爲黎氏|傃:向也|嗉:鳥嗉|膆:+上同|𤤐:玉名|塑:塑像也出周公夢書|塐:捏土容出古今奇字|䛾:諳䛾|𤢘:牲白也亦作素|㨞:暗取物也
PLC昨誤;祚:福也祿也位也昨誤切七|胙:祭餘|阼:阼階東階|𧃘:魚醬|飵:相謁食也|𧇣〈𧇿〉:往也|秨:禾稼皃又音昨
HLC乃故;笯:盛鳥籠也乃故切又音奴二|怒:恚也又音努
ALC博故;布:布帛也又陳也周禮錢行之曰布藏之曰泉又姓陶侃列傳有江夏布興博故切六|圃:園圃說文曰種菜曰圃又音補|佈:佈徧也|抪:抪持|𠜙:裁刀|𧉩:𧉩蝜蟲也
hLC烏路;汙:染也說文穢也烏路切又音烏四|惡:憎惡也又烏各切|噁:喑噁怒皃|䜑:相毁說文作䛩
BLC普故;怖:惶懼也普故切五|悑:+上同見說文|鋪:設也又普胡切|誧:謀也|𤸵:𤸵𤻱痞病又音步
OLC倉故;厝:置也倉故切五|措:舉也投也說文置也|醋:醬醋說文作酢|錯:金塗又姓宋太宰之後又千各切|㳻:壅水
eLC苦故;絝:說文曰脛衣也苦故切七|袴:+上同|庫:貯物舍也又姓風俗通云古守庫大夫之後以官爲氏後漢輔義侯庫鈞亦虜複姓二氏周有少師庫狄峙又有庫門氏亦虜三字姓前燕錄有岷山桓公庫傉官泥|胯:股也韓信出於胯下|䔯:醋葅|苦:困也今人苦車是|跨:踞也
CLC薄故;捕:捉也薄故切十三|哺:食在口也|步:行步爾雅曰堂下謂之步白虎通曰人踐三尺法天地人再舉足步備陰陽也又姓左傳晉有步揚食采於步後因氏焉又虜三字姓三氏後魏書步六孤氏後改爲陸氏又西方步鹿根氏後改爲步氏北齊書有步大汗薩|鞴:鞴靫盛箭室|餔:餹餔又作䊇|鮬:魚名|𩣝:𩣝馬習馬案左傳曰左師見夫人之步馬字不從馬|䒀:艇船|𨛒:亭名|鵏:鵏豉鳥|𤸵:𤸵𤻱痞病又音怖|荹:亂草說文曰亂稾也|𩢕:馬名
iLC荒故;謼:號謼亦作呼荒故切又火姑切二|戽:戽斗舀水器也
NLC臧𧙓〈祚〉;作:造也臧𧙓切一
#霽
NMS子計;霽:雨止也子計切八|隮:升也又子奚切|躋:+上同|濟:渡也定也止也又卦名既濟又子禮切|擠:排盪又將西反|䰏:婦人束小髻也又音祭音節|䶓:䶓緝麻紵名出異字苑|穧:穫也又音劑
EMS都計;帝:說文曰諦也王天下之號也爾雅曰君也都計切二十三|諦:審也|嚏:鼻氣也|啑:+俗|柢:木根柢也|蔕:草木綴實|螮:螮蝀|蝃:+上同見詩|摕:撮取|𦨢:𦨢艡水戰船出字林|䠠:姓也漢書王莽傳有中常侍䠠惲|疐:疐柢也爾雅棗李曰疐之謂去柢也|骶:背也|僀:俊也|𢰂:兩手急持人也|䟡:蹋也|𤬵:𤬵瓽大瓮|偙:偙儶|腣:胅腹皃又當兮切|趆:趨走皃|蝭:寒蟬又音啼|䩚:補履下也|渧:埤蒼云渧𤃀漉也
PMS在詣;嚌:甞至齒也在詣切十|劑:分劑又子隨切|穧:刈禾把數|𨣧:鹹也|眥:目際又才賜切|齊:火齊似雲母重沓而開色黃赤似金出日南又齊和又徂兮切|齌:炊餔疾也|癠:病也|懠:怒也|䶩:䶩𪗷
FMS他計;替:廢也代也滅也說文本作暜廢一偏下也他計切二十|𤾕:-|暜:-|㬱:+並上同出說文|鬀:說文曰𩮜髮也大人曰髡小兒曰鬀盡及身毛曰𩮜|剃:+上同|戻:輜車旁推戶也|𣧂:𣧂𣧎|楴〈揥〉:揥枝整髮釵也|涕:涕淚|洟:鼻洟|䎮:不耕而種|𡲕:履中薦也亦作屟屜|达:足滑|薙:除草|𢝹:寧𢝹心安|𧛒:補也|殢:極困|𣤖〈𣤢〉:唾聲|𥫵:車筤也
GMS特計;第:次第說文本作弟韋束之次弟也今爲兄弟字又漢複姓二氏後漢書第五倫傳云齊諸田徙園陵者多故以次第爲氏有第五第八等氏特計切二十九|弟:+見上注又音上聲|遰:迢遰又底隷切去也避也|髢:髲也|鬀:+上同說文音剃|締:結也|睇:睇視|悌:孝悌又音上聲|娣:娣姒|禘:大祭五年一禘|軑:說文曰車輨也|釱:以鎖加足說文鐵鉗也又音大|鷤:鷤鴂鳥又音啼|棣:車下李又常棣子似櫻桃可食又姓王莽司馬棣並|杕:木盛皃|踶:蹋|題:又徒雞切|遞:更遞|𧡨:視皃|㣇:說文曰脩豪獸也一曰河內名豕也|𢰂:兩手急持人|摕:取也|𧫚:𧫚審|慸:極也又恥厲切|鯷:鮎魚別名|𪂿:𪂿䳏鳥又音啼|墆:墆貯也又墆翳隱蔽皃又徒結切|𥶛:竹名|逮:逮及也又徒戴切
OMS七計;砌:階砌也七計切八|切:眾也又千結切|𥉻:視也|妻:以女妻人又七兮切|摖:挑取|䏅:耳聰|䀙:目䀙|𦕀:耳聰
QMS蘇計;細:小也蘇計切六|𥿳:+古文|些:可也此也辝也何也楚音又蘇箇切|栖:雞所宿也又先奚切|壻:女夫|𣳦:水出汝南新郪入潁
gMS五計;詣:至也五計切十一|𢏗:古能射人名說文曰帝嚳射官也夏少康滅之|羿:+上同|𦐧:說文曰羽之羿風亦古諸侯也一曰射師|睨:睥睨|栺:枍栺殿名|盻:恨視又下戾切|𧡎:旁視|甈:破罌|堄:埤堄女牆也見博雅|霓:虹又音倪
dMS古詣;計:籌計說文會也筭也又姓後漢有計子勳古詣切十二|係:連係|繼:紹繼俗作継|繫:縛繫又口奚胡計二切|薊:草名爾雅曰朮山薊又縣名又州開元十八年以漁陽縣爲薊州又姓後漢有薊子訓俗作葪|髻:綰髮|𨜒:燕都|檕:爾雅曰朹檕梅說文云繘耑木也|檵:枸杞|蘻:狗毒草也|轚:舟車轚互序而行也|㲅:係也盡也
jMS胡計;蒵:屧蒵胡計切十四|䐼:喉脈|𦝜:+上同|系:緒也又姓楚有系益|𦃟:+籀文|妎:心不了也說文妬也又音害|禊:祓除不祥也又禊飲|繫:易之繫辭|瘛:小兒病又尺制切|慀:恨足也|㨙:㨙換|盻:恨視又五計切|䦏:門扇又胡介切|稧:稧事換秧
eMS苦計;契:契約苦計切又苦結切十|栔:刻也|罊:說文云器中盡|䏿:字林云腨腸|蟿:蟿螽螇蚸|𦩣:舟名|𢢞:劇也又怖也|𡢖:難也|䫔:恐也|䁈:省視
hMS於計;翳:羽葆也又隱也奄也障也又鳥名似鳳於計切十七|曀:陰風詩曰終風且曀|枍:枍栺|㥷〈瘱〉:靜也安也恭也|㝣:安也靜也|㙠:塵也|殪:殪死|瞖:目瞖|医:藏弓弩矢器|嫕:婉嫕柔順皃|蘙:蘙薈|縊:自縊|豷:豕息|繄:是也賴縚走絲也|㙪:天陰塵也|𧬇:𧬇諦|殹:擊中聲也
DMC莫計;謎:隱言也莫計切二|㩢:裁也
AMC博計;閉:掩閉說文曰闔門也博計切五|閇:+俗|嬖:愛也卑也妾也|箅:甑箅也說文蔽也所以蔽甑底又必至切|㪏:㪏㪒毁也又補米切
jMi胡桂;慧:解也胡桂切十三|憓:憓愛也|潓:水名|惠:仁也亦惠然順也又姓出琅邪周惠王之後梁有惠施|蟪:蟪蛄|蕙:香草蘭屬|橞:木名|繐:繐帳又音歲|㩨:㩨裂|儶:偙儶|譓:多謀智曰譓也|鏸:銳也又三隅矛|𦒎:羽𦒎
dMi古惠;桂:木名叢生合浦巴南山峯閒無雜木葉長尺餘冬夏長青其花白山海經曰八樹成林又姓後漢太尉陳球碑有城陽炅橫漢末被誅有四子一守墳墓姓炅一子避難居徐州姓昋一子居幽州姓桂一子居華陽姓炔此四字皆九畫古惠切九|昋:-|炅:-|炔:+並見上注|筀:竹名|罣:挂也|𤰮〈𤱾〉:𤱾𤳤|𣧎:𣧎𣧎殛殀也死皃也|䳏:𪂿䳏即杜鵑也
iMi呼惠;嘒:聲急說文小聲也亦作嚖呼惠切三|嚖:+上同|暳:小星詩亦作嘒
BMC匹詣;媲:配也匹詣切七|䠘:+上同見管子|睥:睥睨|渒〈淠〉:水名在汝南|濞:水名又芳備切|𣹮:水聲|𠞇:𠞇斫
CMC蒲計;薜:薜荔蒲計切五|𨫔:所以理苗殺草|𥴬:弋鳥具也|𨢡:醬也|𣘥:木名
IMS郎計;麗:美也著也又姓出姓苑郎計切三十三|戾:乖也待也利也立也罪也來也至也定也又很戾說文曲也从犬出戶下戾者身戾曲也|㑦:+很㑦俗|隸:僕隷|隷:+上同俗作𣜩|儷:伉儷|𥃏〈盭〉:綠色又綬名或作綟又云弼也|綟:草色衣也|劙:割破|𠠫:+上同|唳:鶴鳴曰唳|蜧:大蝦蟆也|䓞:紫草|沴:妖氣說文曰水不利也|荔:薜荔香草又羌複姓有荔非氏|捩:琵琶撥也|欐:梁棟之名也又師禮二音|𤃀:埤蒼云渧𤃀漉也|𥶾:札也|涖:汔也又力二切|悷:𢤱悷多惡又懍悷悲吟也|栛:小槤木名|丽:本也又鹿皮|蜦:神蛇又音倫|㸚:止也系也|珕:方飾又力智切|𣛒:竊視也|㿛:瘦黑又力翅切|䚕:求視又師蟻切|䕻:草木生亞土也|𩘡:急風|離:漢書云附離著也|𣟌:木名
KJQ丑戾〈居〉;𥱻:竹名也丑戾切又杖胡切一
HMS奴計;泥:滯陷不通語云致遠恐泥奴計切又奴低切五|埿:+俗|𢤇:𢤇𢘬音慢又相𢤇摩也|迡:近也|濘:濘陷
iMS呼計;㰥:氣越名呼計切三|㚛:肥大|殢:殢極困也
#祭
NNS子例;祭:享也祀也薦也至也察也子例切七|際:邊也畔也會也|穄:黍穄呂氏春秋曰飯之美者有山陽之際說文曰𪎭也𪎭音縻|鰶:魚名|䰏:露髻又音霽|㦣:寐言|穧:穫也又才計切
QNi相銳;歲:釋名曰歲越也越故限也從步戌相銳切四|櫘:小棺又篲衛二音|𦄑:布縷細也|繐:+上同
kNq于歲;衛:護也垂也加也亦州名殷所都也本衛國爲翟所滅齊桓公伐翟遷衛于河南秦屬東郡魏文置朝歌郡晉爲汲郡東魏爲義州周武改爲衛州亦官名漢書曰衛尉秦官掌宮門衛屯兵又姓周文王子衛康叔之後國滅因氏焉出河東陳留二望又精衛鳥名山海經云狀如鳥白首赤喙其鳴目呼取西山木石以填東海于歲切十三|軎:說文曰車軸耑也从車象形|轊:+上同|璏:劒鼻王莽碎玉劒璏|𥶽:竹名|𧲝:豚屬|𧲔:+上同|槥:小棺|彗:日中必彗|㦣:寐言|讆:+上同|𤜂:牛蹄|熭:曬乾
cNi而銳;芮:草生狀又姓周司徒芮伯之後而銳切六|汭:水曲說文曰水相入皃|枘:柄枘|蜹:蚊蜹又音爇|笍:竹名|鈉:銳鈉
XNi之芮;贅:贅肉也又最也聚也又贅衣官名也之芮切二|𠭥:卜問吉凶
VNi山芮;𠻜:小歠也山芮切一
ONi此芮;毳:細手也又姓出姓苑此芮切又楚稅切十二|韢:囊屬以盛賊頭又音遂|脃:說文曰小耎易斷也|膬:+上同又七劣切|脆:+俗|帨:佩巾又音稅|竁:葬穿壙也又楚稅切|𣃍:斷也|𧑎:蟲名|㓹:小割|㯔:重擣又楚稅切|𤂳:飲也
lNi以芮;銳:利也又姓姓苑云升平中鮮卑有御史中丞銳管以芮切六|銴:銅生五色|叡:聖也|睿:+上同|䓲:草生狀|蜹:毒蟲又而稅切
JNi陟衛;綴:連綴陟衛切又丁劣切十一|醊:祭也|畷:禮注云井田閒道吳都賦云畛畷無數又張劣切|笍:小車具也|䄌:重祭|啜:甞也|餟:說文曰祭酹也司馬貞曰漢志作腏字通|腏:+上同又皮腏著也|錣:針也|卂:釣也|輟:車小缺也
aNi舒芮;稅:斂也舍也又姓盛弘之荊州記云建平信陵縣有稅氏舒芮切九|說:說誘|裞:衣送死也又禮注云日月已過乃聞喪而服曰裞又他活切又他外切|蛻:蛻皮又他臥切又他外切|帨:佩巾也又音脃|𢄢:說文曰禮巾也|涗:溫水又清也|䬽:小餟也又郎外切|䭨:+上同
CNG毗祭;𡚁〈弊〉:困也惡也說文曰頓仆也俗作弊毗祭切五|斃:+死也說文同上|幣:幣帛|㡀:說文曰敗衣也从巾象敗衣之形又匹世切|敝:說文曰帗也一曰敗衣也又姓左傳齊有敝無存
TNi楚稅;㯔:重擣楚稅切四|𣃍:𣃍斷|竁:葬穿壙也|毳:細毛
RNi祥歲;篲:埽帚爾雅曰葥王篲本亦從艹祥歲切九|𥱵:+古文|鏏:大鼎|彗:星名又音遂|䵻:小鼎|槥:小棺|軎:車軸頭也又音衛|轊:+上同|𢅫:布巾
ANG必袂;蔽:掩也必袂切四|鄨:縣名在牂牁又音鷩|鷩:爾雅曰鷩雉郭璞云似山雞而小冠周禮云王享先公饗射則鷩冕又音鼈|彆:弓彆
dNq居衛;劌:傷也割也居衛切六|鱖:魚名大口細鱗有班文一曰婢魚也|𠜾:剖𠜾斷割也|𨇙:爾雅云𨇙洩苦棗亦作蹶|蹶:行急遽皃曲禮曰足無蹶又居月切|𤜂:踶𤜂牛展足
DNG彌弊;袂:袖也彌弊切一
VNS所例;㡜:殘帛所例切三|鎩:矛戟類又所戒切|蔱:椒蔱又所八切
YNS尺制;掣:掣曳尺制切又尺折切八|瘛:小兒驚|懘:㥈懘音不和也㥈樂記作帖|痸:郭璞云癩病|𤸪:+上同|𢜳:說文曰小怒也|銐:除利也|𤢻:狂犬別名
XNS征例;制:禁制又斷也止也勝也說文作𠛐裁也从刀从未物有滋味可裁斷也征例切十八|𠛐:+見上注|𦜗:魚醬亦作𨡐|淛:水名|製:製作又裁也|䎺:入意一曰聞也|晢:星光也亦作晣又音折|䇽:方言云自關而西謂簟或謂之䇽|𢝃〈㛳〉:婦孕病兒|㝂:蝗子|䱥:魚名可爲醬|䀸:目光也又丑世切|狾:狂犬|𥍭:矛也|䩢:刀鞞|䭁:臭敗之味|𤴟〈䠠〉:古人姓|迣:迾也度也
ZNS時制;逝:往也行也去也時制切十三|忕:忕習|觢:牛角豎也|噬:齧噬|誓:誓約|𣂯:+古文|筮:龜曰蓍曰筮巫咸作筮筮決也|簭:+上同見周禮|澨:水名書曰過三澨|銴:車樘結一曰銅生五色又音銳|遾:逮也|𧻸:踰也|𦚨:割𠟼
lNS餘制;曳:牽也引也餘制切二十九|裔:邊也苗裔也又容裔也說文曰衣裾也俗作𧚞|𤤺:石之次玉也|勩:勞也|泄:水名在九江又音薛|洩:+上同|𤵺:病也|䎈:鳥飛|枻:檝枻|詍:多言|𢘽:明也一曰習也|𦒎:鳳六翮|靾:以馬鞍贈亡人|跇:超踰又丑例切|𠂆:施明也又身皃|袣:長被又衣長皃|䄿:白䄿稻名|𪀕:鳥名|㵝:溶㵝水皃|㑜:合板㑜縫|抴:數也|㛳:婦人病胎|䇩:長也|㹭:狸子|丿:至地|㵩:蒸也又蔥㵩也|𢂼:裂也|呭:呭樂說文曰多言也亦作㖂|䕍:草名
hNa於罽;䋵:急也一曰不成也於罽切五|瘞:埋也|餲:又於葛於介二切|𦝲:𦝲臆|䔽:清也又音藹
gNW魚祭;藝:才能也靜也常也準也又姓出姓苑魚祭切八|埶:說文穜也周禮音世|蓺:+上同|䆿〈寱〉:睡語|㦣:+上同|囈:亦同|槸:樹枝相摩|褹:字林云複襦也
LNS直例;滯:廢也止也凝也久也直例切七|彘:豕也又姓左傳有彘恭子|蹛:蹛林又音帶|銐:除利也|璏:劒鼻玉也|𦭮:草補缺|𩻼:魚名
INS力制;例:比也皆也力制切二十五|厲:惡也亦嚴整也烈也猛也又姓漢有魏郡太守厲溫|礪:砥石|勵:勸勉|禲:無後鬼也|癘:疫癘|㾐:+上同|鮤:魚名又音列|濿:以衣渡水由膝已上爲濿亦作厲詩曰深則厲淺則揭說文又作砅履石渡水也|砅:+義見上注|蠣:牡蠣蚌屬|蠇:+上同|櫔:木名|𩧃:馬馳|𩢾:+上同|䅀:黍穰|𥣭:+上同|𧸱:𧸱貨|糲:麤也又力達切|巁:巍也|犡:牛白脊|栵:栭栗又音列|𢂥:帛餘亦作㡂|𢤆:恐人|洌:清水又音列
eNa去例;憩:息也去例切六|𡳅:+上同|䔾:䔾車草|愒:爾雅貪也說文息也|揭:褰衣渡水由膝已下曰揭|甈:爾雅康瓠謂之甈郭璞云瓠壺也賈誼曰寶康瓠是也
aNS舒制;世:代也又姓風俗通云戰國時有秦大夫世鈞舒制切三|勢:形勢|貰:賒也貸也又時夜切
dNa居例;猘:狂犬宋書云張收嘗爲猘犬所傷食蝦蟆膾而愈居例切八|𦇧:氈類織毛爲之說文曰西胡毳布也|罽:+上同說文曰魚网也|𣯅:亦同|瀱:泉出皃|訐:持人短又居列切|彐:彙類說文作彑云豕之頭象其銳而上見也|蘮:蘮蒘似芹
JNS竹例;㿃:赤白痢亦作䐭竹例切又音帶一
fNa其憩;偈:偈句其憩切一
ZNi嘗芮;啜:甞也嘗芮切又臣劣切一
KNS丑例;跇:跳子踰也丑例切十二|𧼪:+上同|傺:侘傺侘敕加切|𢘽:習也|慸:困劣|㑜:㑜刻|䀸:瞥也|䚢:𧢷也又丑列切|揥:佩飾|䟷:躍皃|𨂰:渡也|𥉻:視也
LNi除芮;𨮱〈𨧨〉:曲刀也削竹也除芮切一
gNa牛例;㓷:去鼻也牛例切一
NNi子芮;蕝:束茅表位子芮切又子悅切三|𧎹〈𧑎〉:蟲名又作會切|㨹:裂也
BNG匹蔽;潎:魚游水也匹蔽切一
eUu丘吠;𥏙:𥏙䂕短皃丘吠切一
iUu呼吠;䂕:短皃呼吠切一
#泰
FOS他蓋;泰:大也通也古作太他蓋切四|忕:奢也又逝大二音|太:甚也大也通也周禮曰太史掌建邦之六典宋書曰太史掌歷數靈臺專候日月星氣焉經典本作大亦漢複姓六氏漢有尚書太叔雄古今人表有太師庇何氏姓苑云太征氏下邳人太士氏永嘉人又有太室氏太祝氏|汰:太過也
dOS古太;蓋:覆也掩也通俗文曰張帛也禮記曰敝蓋不棄爲埋狗也又發語端也說文曰苫也俗作盖古太切三|匃:乞也|丏〈丐〉:上同本又音緬
gOS五蓋;艾:草名一名冰臺又老也長也養也亦姓風俗通云龐儉母艾氏五蓋切三|𧰿:𧰿猳豕|鴱:巧婦別名
hOS於蓋;藹:晻藹樹繁茂又姓晉南海太守藹奐於蓋切十|壒:塵也|馤:香也|靄:雲狀又於葛切|𣋞:日色|䔽:覆也清也微也說文蓋也|𣩱:死也|𢣏:清謹|𪕭:𪖂𪕭小鼠相銜而行|瞹〈曖〉:曖隱
HOS奴帶;柰:果木名廣志曰柰有青赤白三種俗作㮏奴帶切五|奈:如也遇也那也本亦作柰又奴箇切|㲡:𣬪㲡多毛|𩹟:魚名|渿:說文曰沛之也
GOS徒蓋;大:小大也說文曰天大地大人亦大故大象人形又漢複姓五氏晉獻公娶大狐氏楚襄王時有黃邑大夫大心子成史記秦將軍大羅洪周禮大羅氏掌鳥獸者其後氏焉又大庭氏古天子之号其後氏焉又有大叔氏又虜複姓後魏末有南州剌史大野拔又虜三字姓周書蔡祐賜姓大利稽氏周末有尉回將軍大莫于玄章後魏書南方大洛稽氏後改爲稽氏徒蓋切八|汏:濤汏說文曰淅㶕也|軑:車轄|釱:鉗也又大計切|䲦:鳥也|𪐝:黑跡|忕:奢忕|㐲:地名在海中
jOS胡蓋;害:傷也胡蓋切四|夆〈𡕗〉:相遮也|妎:字林云疾妎妬也|𢞐:快也
EOS當蓋;帶:衣帶說文曰紳也男子鞶革婦人鞶絲象繫佩之形帶有巾故从巾易曰或錫之鞶帶又蛇別名莊子云蝍蛆甘帶也當蓋切七|跢:倒跢|㿃:㿃下病也|蹛:匈奴傳有蹛林又音滯|𢄔:𢄔方山名|艜:艇船|㯂:槌也
AOC博蓋;貝:說文曰海介蟲也居陸名贆在水名蜬象形古者貨貝而寶龜亦州名春秋時屬晉七國屬趙秦爲鉅鹿郡漢爲清河郡周置貝州以貝丘爲名博蓋切十四|沛:郡名又姓出姓苑又匹蓋切|𨙶:+上同|鋇:鋇柔鋌也|芾:小皃又方味切|䟺:步行蠟跋|狽:狼狽|㸬:牛二歲也爾雅云體長㸬|伂:顛伂本亦作沛|䰽:魚名食之殺人|茷:草木葉多|𣬪:𣬪㲡多毛|𥄔:目不明皃又音霈|𢂏:行皃
BOC普蓋;霈:霶霈普蓋切五|浿:水在樂浪|沛:流皃亦滂沛又水名出遼東又音貝|𥄔:𥄔眛目不眀也|㤄:恨怒
jOi黃外;會:合也古作會亦州秦屬隴西郡漢分爲金城郡周爲防隋爲鎮武德初平李軌置會州又姓漢有會祤黃外切又音儈五|䢈:說文曰日月合宿爲䢈|𨘇:說文云無違也|襘〈禬〉:除殃祭也又古外切|繪:繪五采也
GOi杜外;兌:突也又卦名說文本作兌說也又姓杜外切五|𩊭:補𩊭|綐:細紬|銳:矛也又弋稅切|㟋:山名
dOi古外;儈:合市也晉令儈賣者皆當著巾白帖頟言所儈賣及姓名一足白履一足黑履古外切十八|膾:魚膾說文曰細切肉也|鱠:+上同|襘:說文曰帶所結也|禬:福祭|檜:栢葉松身又古活切|旝:木置石投敵也|巜:說文曰水流澮澮也方百里有巜廣二尋深二仞|澮:+上同爾雅曰水注溝曰澮又水名在平陽|鄶:國名在滎陽|廥:芻槀藏也|䯤:五綵束髮說文曰骨擿之可會髮者詩云䯤弁如星|鬠:+上同|劊:說文曰斷也|會:會稽山名又黃外切|䐴:𦝫痛|𢶒:收也|獪:狡獪小兒戲
NOi祖外;最:極也俗作㝡祖外切三|𢃒:五色采也|𧎹〈𧑎〉:蟲也又山芮切
iOi呼會;𧬨:眾聲呼會切六|噦:鳥聲|翽:鳥飛聲|鐬:鈴聲|渙:水名在譙又音喚|濊:說文曰水多皃又烏會切
eOi苦會;𥢶:麤糠苦會切一
IOi郎外;酹:以酒沃地郎外切五|頪:說文曰難曉也一曰鮮白|㲕:馬色班也|䬽:門祭|㱻:疫病又力臥切
gOi五會;外:表也遠也五會切一
EOi丁外;祋:祋祤縣名在馮翊又祋殳也丁外切一
hOi烏外;懀:惡也烏外切七|濊:汪濊深廣又呼會切|薈:草盛|嬒:婦人名也|䶐:息也|瞺:眉目之閒|䵳:淺黑色
POi才外;蕞:小皃才外切二|𥳣:𥳣䇻
QOi先外;𥕸:小石先外切三|𣩡:瘦病|𥊴:流盻
OOi麤最;襊:衣游縫也麤最切三|𨅎:行𨅎|𥨒:塞外道也
COC蒲蓋;旆:旗也繫旐曰旆蒲蓋切三|䟺:賴䟺行不正也|軷:祭道神又蒲葛切
eOS苦蓋;磕:硠磕石聲苦蓋切九|䳚:䳚鴠鳥又音渴|轄:車聲|愒:貪也公羊傳云不及時而葬曰愒愒急也|溘:船著沙也|𥎆:矛屬|𩫀:擊也|㪡:伐也擊也|𨜴:地名或作𨞨
OOS倉大;蔡:龜也亦國名又姓出濟陽周蔡叔之後也倉大切三|𣞖:+古文|𪇭:𪇭鳩鳥
IOS落蓋;賴:蒙也利也善也幸也恃也又姓風俗通云漢有交阯太守賴先落蓋切十四|籟:籥三孔也|癩:疾也說文作癘惡疾也今爲疫癘字|瀨:湍瀨|糲:麤米又力達切|䄤:墮壞|藾:藾蒿|䓶:+上同|犡:牛名說文曰牛白脊|䲚:魚名|𨇆:跛𨇆行皃|㸊:火之毒皃|鵣:鳥名|𡂖:聲𡂖
iOS呼艾;餀:食臭呼艾切五|𦤦:+上同|㺔:獸名出音譜|𤵽:𤵽病|𩹄:魚名
FOi他外;娧:好皃他外切五|蛻:蛇易皮又音稅|駾:奔突也詩云昆夷駾矣|毻:鳥易毛又音唾|裞:送死衣也
DOC莫貝;眛〈眜〉:𥄔眛目不明也莫貝切三|沬〈沫〉:水名|㭑〈枺〉:木名
OOi七外;𦦣:𦦣小舂也七外切一
#卦
dPi古賣;卦:說文曰筮也易疏云挂也懸挂萬象於其上八卦者八方之卦也乾坎艮震巽离坤兌古賣切六|挂:懸挂又剛挂弩矢鏃名潘岳射雉賦云出剛挂以潛擬|掛:+俗|詿:誤也又胡卦切|𡐠:盾握也|罣:罣礙又胡卦切
dPS古隘;懈:懶也怠也古隘切六|解:除也|繲:繲浣衣出埤蒼|廨:公廨|薢:薢茩藥名|㾏:病也
hPS烏懈;隘:陝也陋也烏懈切六|𨽴:+古文|阸:阻塞又阸㠔山形或與隘同|㿄:病聲|䅬:稻小把也|賹:賹記人物
jPS胡懈;邂:邂逅胡懈切二|解:曲解亦縣名在蒲州又古賣古買胡買三切
DPC莫懈;賣:說文作𧷓出物也莫懈切一
jPi胡卦;畫:釋名曰畫挂也以五色挂物象也俗作𦘕胡卦切又胡麥切九|詿:礙也|罣:+同上|絓:絲結|澅:水名在齊|黊:鮮黃色|繣:徽繣乖違|纗:紘中繩也|孈:愚戇又多態也
TPS楚懈;差:病除也楚懈切又楚宜楚皆初牙三切七|瘥:+上同又音醝|衩:衣衩|杈:杈杷平田具也又音又|㳗:浦㳗|訍:訍持短又疑心名也|𧪘:異言
gPS五懈;睚:目際又睚眦怨也五懈切又五佳切一
iPS火懈;謑:怒言火懈切又胡禮切一
APC方卦;庍〈𢈕〉:到別方卦切一
CPC傍卦;粺:精米傍卦切四|稗:稻也又稗草似榖|𪐄:黍屬又音俾|杷:田具又音琶
UPS七〈士〉懈;㾹:疾也七懈切二|眦:睚眦
BPC匹卦;派:分流也俗作沠匹卦切七|𠂢:說文曰水之衺流別也|𥿯:未緝麻也說文曰散絲也|𣏟:麻紵|㵺:說文曰水在丹陽|㭛:藤屬蜀人以織布出埤蒼|𣎳:分枲皮也又匹刃切
SPS側賣;債:徵財側賣切一
ePS苦賣;𡢖:難也苦賣切又音契二|𨛖:鄉名
VPS所賣;曬:暴也所賣切又所寄丑離二切五|䵘:不黏之皃或與曬同|𨢦:簀酒|汛:水皃說文灑也本又音信|洒:洒埽又先禮切
iPi呼卦;諣:疾言呼卦切一
APC方賣;㠔:阸㠔山形方賣切一
JPS竹賣;膪:亦作䐱腏𠟼也竹賣切又竹惡切𦜖膪肥皃二|𢕮:𢕮步立皃出聲譜
#怪
dQi古壞;怪:怪異也古壞切八|恠:+俗|𥑋:𥑋石似玉|𦳋:草名|𣀤:毀也|壞:+上同又胡怪切|𡌪:大皃|㧔:訬也
hQS烏界;噫:噫氣烏界切二|呝:不平聲
SQS側界;瘵:病也側界切三|祭:周大夫邑名又姓周公第五子祭伯其後以爲氏|𨝋:說文曰周邑也
dQS古拜;誡:言警也古拜切二十三|戒:慎也具也備也警也易注云洗心曰齋防患曰戒|界:境也垂也|介:大也助也佑也甲也閱也耿介也說文作介畫也俗作□又姓介之推是|屆:至也舍也說文曰行不便也一曰極也|疥:瘡疥|玠:大珪長尺二寸|㝏:獨居|㠹:幘也|砎:硬也|魪:比目魚也|尬:尲尬行不正尲音緘|价:善也又佋价也|䯰:簪結|悈:飾也司馬法曰有虞氏悈於中國|䲸:䲸雀也似鶡而青出羌中|艐:爾雅云至也亦云古屆字|䁓:怒也|芥:辛菜名又草芥|衸:布衣幅也又胡介切|丰〈丯〉:草介|𠨴:𠨴到|𩡺:𩡺馬馬尾結也
MQS女介;褹:紩布襦女介切一
iQS許介;譮:怒聲許介切九|欸:+上同|㖑:喝㖑|齂:鼻息|噧:高聲皃又多言|䜕:譀䜕|㞒:臥息|𡘌:說文曰瞋大聲也|𢗊:說文曰忽也孟子曰孝子心不若是𢗊
jQS胡介;械:器械又杻械胡介切十一|䪥:葷菜也葉似韭|薤:+俗|齘:䫴齘切齒怒䫴于禁切|䦏:門扇|瀣:沆瀣北方夜半之氣又胡代切|㒠:陜也|韰:韰惈猶果敢也|𤡧:雌狢|衸:𧙞膝裙也說文袥也|㳦:水名
gQS五介;𦗐:不聽五介切四|譺:誡譺|𢟰:忦𢟰慳悋人也|𧏹:蟲名𠯗食草木葉也
eQi苦怪;蒯:茅類又姓出襄陽漢有蒯通或作𦰵苦怪切九|喟:歎也又丘愧切|嬇:女字|㕟:太息|䈛:箭竹名也|簣:籠也|嘳:譏他人也|蕢:杜蕢蕢尚並見禮記|墤:俗云土塊本音隤
AQC博怪;𢷎:周禮曰大祝辯九𢷎一曰稽首二曰頓首三曰空首四曰振動五曰吉𢷎六曰凶𢷎七曰奇𢷎八曰襃𢷎九曰肅𢷎博怪切三|拜:+上同|扒:拔也詩云勿剪勿扒案本亦作拜
BQC普拜;湃:滂湃普拜切二|浿:水名在樂浪
jQi胡怪;壞:自破也胡怪切三|𡎯:+古文|蘾:蘾烏蕵草
gQi五怪;聵:聾也五怪切三|𦖥:+說文同上|𩔀:說文曰頭蒯𩔀
CQC蒲拜;𢞎:病也說文𢢞也蒲拜切八|憊:-|𤸶:+並同上|韛:韋囊吹火|𣡖:+上同|𦩋:船後𦩋木|棑:木名|㶔:水波
DQC莫拜;䀛:䀛眼久視莫拜切三|𧱘:𧱘𧱳頑惡|𩎟〈韎〉:東夷樂也
iQi火怪;𧱳:𧱘𧱳火怪切五|躗:過也|𣟉:木名皮可牽船|𣸎:水聲|咶:鼻息
VQS所拜;鎩:翦翮說文曰鈹有鐔也所拜切又所八切四|𧜁:衣𧘪縫也|殺:殺害又疾也猛也亦降殺周禮注云殺衰小之也又所八切|閷:+上同亦見周禮
eQS苦戒;烗:熾也盛也苦戒切四|𤈪:+上同|劾:勤力作也|揩:鼓名又客皆切
JQi他〈迍〉怪;顡:顏惡也他怪切說文五怪切癡顡不聰明也一
#夬
dRi古賣〖邁〗;夬:決也亦卦名古賣切三|獪:狡獪|䈛:䈛竹名
eRi苦夬;快:稱心也喜也可也又姓漢有快欽苦夬切五|噲:咽也又人名漢有樊噲又姓孝子傳有噲叄鵠銜珠與之|𥢶:麤穅|駃:駃馬日行千里|璯:人名晉有錢璯
DRC莫話;邁:行也遠也莫話切四|勱:勉也強也|䜕:誇誕又火犗切|佅:僸佅
jRi下快;話:語話說文作䛡合會善言也下快切一
CRC薄邁;敗:自破曰敗說文毀也薄邁切又北邁切四|贁:+籀文|䢙:散走|唄:梵音
hRi烏快;䵳:淺黑色烏快切又烏外切三|䶐:喘息聲又烏外切|懀:惡皃
TRi楚夬;嘬:一舉盡臠曲禮曰無嘬炙楚夬切四|䴝:南方呼醬|𣤌:齧也|𠽶:+上同
dRS古喝;犗:犍牛古喝切二|𧜅:衣上也亦作𧛾
KRS丑犗;蠆:毒蟲丑犗切二|慸:極也劣也慸芥
hRS於犗;喝:嘶聲於犗切五|餲:飯臭又於罽切|嗄:聲敗又所嫁切|䬵:通食氣也|欬:+上同
VRS所犗;𠱡:喝𠱡所犗切一
LRS除邁;𦤧:大臭又事露也除邁切一
iRS火犗;䜕:譀䜕火犗切譀火懺切二|𦤬:𦤬𦤧臭皃
iRi火夬;咶:息聲火夬切一
ARC補邁;敗:破他曰敗補邁切又音唄一
TRi倉夬;啐:啗也倉夬切一
URS犲（豺）夬;寨:羊栖宿處犲夬切二|砦:山居以木柵
jRS何犗;㕢:纔然何犗切一
#隊
GSi徒對;隊:羣隊徒對切十二|䨴:霮䨴雲狀|薱:草盛|憝:怨也惡也周書曰元惡大憝|憞:+上同|譈:亦同|鐓:矛下銅也曲禮曰進矛戟者前其錞|錞:+上同|䃍:礧䃍物墜也|䯟:𩪁䯟愚人|𩐌:齏也|濧:漬也濡也
CSC蒲昧;佩:玉之帶也說文曰大帶佩也从人从凡从巾佩必有巾巾謂之飾禮曰凡帶必有佩玉蒲昧切十二|珮:+玉珮俗|孛:星也又蒲沒切|鄁:紂之畿內國名東曰衛南曰鄘北曰鄁|邶:+上同|偝:向借|誖:言亂又補內蒲沒二切|悖:心亂又蒲沒切|背:弃背又姓也又補妹切|琲:埤蒼云珠百枚曰琲孫權貢珠百琲琲貫也又云珠五百枚也亦作㻗又蒲罪切|𢂤:拂取|苝:爾雅曰苝山䪥案本亦作葝葝音勍
DSC莫佩;妹:姊妹莫佩切十一|昧:暗昧|眛:目暗|每:數也又武罪切|痗:病也又音晦|瑁:瑇瑁亦作𤲰蝐又莫沃切|黴:點筆又武悲切|莓:莓子木名似葚又莫杯切|䍙:鳥網|脢:背肉也又莫杯切|䆀:禾傷雨則生黑班也
BSC滂佩;配:匹也合也滂佩切四|朏〈昢〉:向曙色也|妃:妃偶也又匹非切|嶏:崩聲
iSi荒內;誨:教訓也荒內切十一|悔:改悔|晦:冥也又月盡也|𠧩:易卦上體|靧:洗面|頮:+上同|秏:稻名出南海又火号切|痗:病也|𩔁:面肥也|詯:休市|𣴵:大清說文曰青黑皃今作㳷
ESi都隊;對:荅也當也配也楊也應也古作𡭊漢文責𡭊而面言多謂非誠𡭊故去其口以從土也都隊切六|𡭊:+見上注|碓:杵臼廣雅曰𥕐碓也通俗文云水碓曰轓車杜預作連機碓孔融肉刑論曰水碓之巧勝於聖人之斷木掘地|𣝉:車箱考工記云立曰𣝉橫曰軹|轛:+上同|𠏮:帀市
OSi七內;倅:副也七內切五|淬:染也犯也寒也|焠:作刀鋻也天官書曰火與水合爲焠|䃀:䃀磨|啐:甞入口又先對切
NSi子對;晬:周年子也子對切七|祽:月祭名也|𪓌:說文曰會五綵繒也|綷:+上同|𢃒:亦同|捘:推也|夎:失容節拜又子臥切
hSi烏繢;𩲄:𩲄𡯵癈風苦熱烏繢切三|㕈:隱翳|隈:字林云隩隈也
FSi他內;退:卻也說文作𢓴他內切五|𢓴:+上同|𨓤:+古文|㥆:肆也又他沒切|𡯵:𩲄𡯵
dSi古對;憒:心亂也古對切十|幗:婦人喪冠又古獲切|刏:刏刀使利|慖:恨也|䵋:黃色又于鄙切|䐴:𦝫忽痛也|簂:筐也亦作槶|䈐:篷也|𪏤:病皃|蔮:儀禮注云滕薛名蔮爲頍
jSi胡對;潰:逃散又亂也胡對切十三|迴:曲也又音回又作匯|繢:畫也|嬇:女字|殨:肉爛|闠:闤闠市門|䔇:草名呂氏春秋云菜之美者有雲夢之䔇|螝:蟲蛹|詯:胡市|膭:肥大|僓:長也|䜋:覺悟說文曰中止也司馬法曰師多則民䜋䜋止也|䛛:市䛛
eSi苦對;塊:土塊苦對切三|凷:+上同說文曰墣也禮曰寢苫而枕由|堁:塵起又於臥切
QSi蘇內;碎:細破也蘇內切五|𤭢:說文破也|誶:告也|啐:送酒聲|繀:織繀說文曰著絲於筟車
HSi奴對;內:入也奴對切一
ISi盧對;纇:麤絲也盧對切十四|耒:耜世本曰倕作耒古史考曰神農作耒說文云手耕曲木也|儽:極困也|攂:攂鼓|酹:酹酒|蘱:草名似蒲一云似茅|㔣:推也|䒹:耕多草|𥣬:秲𥣬稻名|𡔇:𡔇塊土皃|礧:礧䃍重也|䣂:䣂陽縣漢書作耒|銇:銇鑽|錑:平板
ASC補妹;背:脊背補妹切三|輩:等輩又比也類也俗作輩|誖:亂也
gSi五對;磑:磨也世本曰公輸般作之五對切一
jSi胡輩;蚚:爾雅曰強蚚胡輩切又音析一
#代
GTS徒耐;代:更代年代亦州名春秋時屬晉其後趙襄子以銅斗擊殺代王取其地至秦隷太原郡漢置雲中鴈門代郡魏爲州又姓史記趙有代舉徒耐切十三|岱:泰山|黛:眉黛|黱:+上同|逮:及也又徒帝切|埭:以土堨水|𡍖:+上同|帒:囊屬|袋:+上同|𤮼:甘也|酨:醋也又昨代切|瑇:瑇瑁亦作蝳𣫹異物志云如龜生南海大者如籧篨背上有鱗鱗大如扇有文章將作器則煑其鱗如柔皮俗又作玳又徒督切|靆:靉靆雲狀
NTS作代;載:年也事也則也乘也始也盟辭也又姓風俗通云姬姓之後作代切又材代切六|再:重也兩也|縡:事也出字林|𨚵:古國名|𩛥:說文曰設餁也|䵧:染䵧
DSC莫代;䆀:禾傷雨莫代切又莫亥切二|脄:背側肉也
QTS先代;賽:報也先代切四|簺:格五戲說文云行棊相塞故曰簺也|塞:邊塞又蘇則切|𢞝:寬也實也
FTS他代;貸:借也施也假也他代切四|儓:儓儗癡皃|態:意態亦作㑷|曃:曖曃不明皃出玉篇
dTS古代;溉:灌也又水名出東海桑瀆縣覆甑山古代切六|槩:平斗斛木|摡:滌也詩云摡之釜鬵|㕢:深堅意又偶也|𠌰:主也|㧉:磨也
eTS苦蓋〖愛〗;慨:慷慨苦蓋切六|愾:大息|欬:欬瘶|鎧:甲也管子曰葛盧之山發而出黃金蚩尤制以爲鎧也|闓:開也又音開|嘅:嘅嘆
gTS五溉;礙:止也距也五溉切七|硋:+上同|䙷:釋典云无䙷也|閡:外閉|儗:儓儗|懝:騃也|𥝌:木曲頭不出又音稽
hTS烏代;愛:憐也說文作𢙴行皃烏代切九|㤅:惠也|𢟪:+古文|曖:日不明又晻曖暗皃|僾:隱也|𥴨:隱也爾雅作薆|靉:靉靆雲狀|薆:薆薱草盛|璦:珠璦玉篇云美玉也
jTS胡槩;瀣:沆瀣氣也胡槩切三|㤥:患苦|劾:椎劾
HTS奴代;耐:忍也奴代切七|螚:小䖟蟲也|鼐:大鼎|能:技能又姓何氏姓苑云長廣人|佴:姓也山公隻有佴湛|𣉘:日無光也|耏:𩓣也又如之切
ETS都代;戴:荷戴又姓出濟比本自宋戴穆公之後風俗通云凡氏於諡戴武宣穆是也都代切一
ITS洛代;賚:與也賜也洛代切九|萊:草也又音來|睞:旁視|徠:勞也|勑:+上同|㾢:惡病|誺:誤也|䚅:內視|逨:就也又音來
OTS倉代;菜:草可食者皆名菜倉代切五|埰:古者鄉大夫食采地郭璞云采地葬之因以名|棌:木名|䰂:髻也|䐆:大腹
PTS昨代;載:運也昨代切七|裁:製裁|纔:僅也|在:所在|酨:醋醬|栽:築牆長板|𣿐:測也
iTS海愛;儗:儓儗癡也海愛切又音礙一
#廢
AUO方肺;廢:止也大也方肺切九|癈:固病|𤼺:賦斂|橃:木似柚也|祓:福也除惡祭也又敷物切|𥳊:蘆𥳊|䉬:+上同|䚨:說文云弋射收繳具也|砩:以石遏水曰砩
BUO方〈芳〉廢;肺:金藏方廢切四|杮:斫木札也|㤄:怒也|䑔:䑗也又音伐
hUu於廢;穢:惡也於廢切六|薉:荒薉說文蕪也|濊:濊貊夫餘國名或作獩貊又汪濊又烏外切|獩:+見上注|饖:飯臭|䮹:䮹䮭馬怒
CUO符廢;吠:犬聲符廢切四|茷:草葉多也又方大切|𩵥:魚名|鼣:鼠名如犬吠也
iUu許穢;喙:口喙許穢切又昌芮切六|𤸁:困極也詩云昆夷𤸁矣本亦作喙|𣨶:+上同|𧾣:行走之皃|餯:飯臭|顪:頰也
fUu渠穢;𤜂:牛觸人渠穢切一
gUe魚肺;刈:刈穫魚肺切八|乂:才也|㲼:水名|㣻:困患爲戒|𩾘:爾雅云桃蟲鷦其雌𩾘俗呼爲巧婦亦作鴱又音艾|艾:治也見詩|䖊:虎皃|䢃:才人名
#震
XVS章刃;震:雷震也又動也懼也起也威也章刃切十一|振:奮也裂也舉也整也救也又之人切|賑:贍也|娠:妊娠又音身|侲:侲子逐厲鬼童子也|挋:說文云給也一曰約也又爾雅曰挋拭刷清也|袗:玄服|䪾:䪾𩕔頭少髮說文曰顏色䪾䫰慎事也頁皆在左|䟴:動也|䢻:地名又音辰|䳲:䳲鷺
QVS息晉;信:忠信又驗也極也用也重也誠也又姓魏信陵君無忌之後又漢複姓何氏姓苑有信都信平二氏息晉切十一|訊:問也告也|訙:+上同|迅:疾也又私閏切|囟:說文曰頭會腦蓋也|顖:+上同|卂:疾飛而羽不見|汛:說文灑也|𤜢:小獸有臭居澤色黃食鼠|奞:奮奞也|阠:八陵名爾雅曰東陵阠又所臻切
cVS而振;刃:刀刃而振切十一|認:識也|肕:牢肕|韌:柔韌亦與肕同|仞:七尺曰仞|軔:礙車輪木|牣:滿也詩曰於牣魚躍|杒:木名|訒:難言|𢂻:枕巾|䀼:眩懣
lVS羊晉;胤:繼也嗣也亦姓羊晉切十一|酳:酒漱口也|靷:引軸|引:又羊忍切|𣌾〈朄〉:小鼓在大鼓上擊之以引樂亦作𣍃|濥:說文云水脉行地中濥濥然|䏖:春肉又直忍切|𢯼:伸也|洕:小水|鈏:鐵鈏|𨋙:車名
IVS良刃;遴:行難也又姓良刃切二十八|吝:悔吝又惜也恨也俗作𠫤|悋:鄙悋本亦作吝|磷:薄石|閵:閵鵲鳥名似鴝鵒而黃|𥳞:竹名堅中|粦:說文作㷠鬼火也兵死及牛馬血爲之|燐:+上同|藺:草名莞屬亦縣名在西河又姓出西河本自有周晉穆公少子成師封韓韓獻子玄孫曰康食邑於藺因氏焉|轥:轥轢車踐|轔:+上同|䗲:螢火|𩕔:𩒉𩕔一曰頭少髮|𠄈:獸名似彘身黃尾白|麐:牡麟又音鄰|䉮:植也|𦺸:草名|瞵:視不明皃|橉:木名|鏻:鏻健|甐:器也|𧶆:貪也|𧖔:蟁也|𤌎:火皃|疄:田壟|撛:扶也又力盡切|㔂〈粼〉:水在石閒|躙:蹂躙
AVG必刃;儐:儐相也說文導也必刃切七|擯:擯斥|殯:殯殮|鬢:頰上髮也|覕:不相見也|𧸈:+上同|䚔:䚔𧢜又匹人切
LVS直刃;敶:列也直刃切五|陳:+上同見經典|陣:+俗今通用|診:候脉又之忍切|𨳌:登也
ZVS時刃;慎:誠也謹也亦姓古有慎到著書又漢複姓家語魯有慎潰氏奢侈逾法時刃切三|昚:+古文亦姓|蜃:蛟蜃又縣名
aVS試刃;眒:張目試刃切三|阠:東方陵名|抻:抻物長也
eVW去刃;菣:香蒿可煑食去刃切又苦見切三|𧼒:行皃|臤:堅也
PVS徐〖疾〗刃;賮:琛賮又財貨也會禮也徐刃切又疾刃切六|燼:燭餘|㶳:+上同|藎:進也詩云王之藎臣一曰草名|濜:水名|壗〈璶〉:石似玉
gVa魚覲;憖:且也一曰傷也又曰問也魚覲切三|猌:犬張齗怒皃|垽:滓也
NVS即刃;晉:進也又州名堯所都平陽禹貢冀州之域春秋時晉地秦屬河東郡後魏爲唐州又爲晉州爾雅晉有大陸之藪今鉅鹿是也亦姓本自唐叔虞之後以晉爲氏魏有晉鄙即刃切十|㬜:+上同出說文|搢:搢紳之士搢笏而垂紳又插也|縉:淺絳色又古有縉雲氏|䗯:蟲名又蛤屬|進:前也善也升也登也又姓出何氏姓苑|枃:凡織先經以枃梳絲使不亂出埤蒼|瑨:美石次玉|璡:+上同又音津|𦎷:羊名又亭名切
iVa許覲;衅:牲血塗器祭也許覲切三|釁:+上同又罪也瑕釁也|舋:+俗
JVS陟刃;鎮:壓也周禮有四鎮楊州之會稽青州之沂山幽州之醫無閭冀州之霍山又姓出姓苑陟刃切三|瑱:玉充耳又吐甸切|填:定也亦星名又音田
fVa渠遴;僅:餘也纔也劣也少也渠遴切十一|覲:見也|殣:埋也|瑾:美玉名|饉:無榖曰饑無菜曰饉|㝻:少也|廑:小屋|瘽:病也|墐:塗也詩曰塞向墐戶|𠞱:𠞱割也又去槿切|歏:歏欠
TWS初覲;櫬:空棺也初覲切七|瀙:水名|嚫:嚫施|䞋:+上同|襯:近身衣|儭:裏也|齔:說文曰毀齒也男八月而齒生八歲而齔女七月而齒生七歲而齔俗作齔又初忍切
hVW於刃;印:符印也印信也亦因也封物相因付又漢官儀曰諸侯玉黃金橐駝鈕文曰璽列侯黃金龜鈕文曰章御史大夫金印紫綬文曰章中二千石銀印龜鈕文曰章千石至四百石皆銅印文曰印又姓左傳鄭大夫印段出自穆公子印以王父字爲氏於刃切四|鮣:魚名身上如印|𣱐:㲳又音致|𩂥:氣行
KVS丑刃;疢:病也俗作𤵜丑刃切二|趁:趁逐俗作趂
BVG匹刃;𣎳:麻片匹刃切三|𨷚〈𩰗〉:鬭也|䚔:暫見
OVS七遴;親:親家七遴切又七鄰切四|寴:屋空皃說文至也|儭:至也又畏也|瀙:水名
eVW羌印;螼:螼蚓一名蜸蠶蚯蚓也羌印切蜸苦典切一
dVm九峻;呁:吐也九峻切二|𧥺:欺言
#稕
XVi之閏;稕:束稈也之閏切六|𦽑:+上同|諄:告之丁寧|𥇜:鈍目|盹:+上同|訰:訰訰亂也
QVi私閏;𡺲:高也長也險也峭也速也私閏切十三|峻:+上同|濬:深也|浚:水名在衛亦浚儀縣名|陖:亭名在馮翊說文曰陗高也|埈:+上同|迅:疾也又音信|鵕:鵕䴊似鳳說文曰鷩也漢初侍中服鵕䴊冠|𢏤:弓彇|奞:奮奞鳥張羽毛也|𧸩:𧸩益|晙:早也又音俊|迿:出表詞出
RVi辭閏;殉:以人送死辭閏切四|徇:自衒名行|侚:以身從物|𢓈:巡師宣令又從也或作徇
NVi子峻;儁:智過千人曰儁又羌複姓有儁蒙氏子峻切十二|俊:+上同|晙:早也|餕:食餘|畯:田畯農夫詩傳曰田大夫也|駿:馬之俊周穆王有八駿驊騮騄駬赤驥白兔犧渠黃踰盜驪山子又音峻|㕙:㕙古東郭之狡兔名又音逡|𪕞:石鼠出蜀毛可作筆|寯:人中最才|焌:然火|㼱:獵之韋袴說文曰柔韋也又音耎|𤮪:+上同又而隴切
aVi舒閏;舜:虞舜仁聖盛明曰舜說文作䑞艸也楚謂之䔰葍秦謂之藑蔓地連華象形舒閏切八|䑞:+見上注|蕣:木槿|瞬:瞬目目動也|瞚:-|眴:+並上同|䀢:亦同見公羊傳|鬊:毛皃禮注云亂髮也
cVi如順;閠〈閏〉:閏餘也易曰五歲再閏史記曰黃帝起消息正閏餘漢書音義曰以歲之餘爲閏如順切三|潤:潤澤也又益也|䏰:漢𦚧䏰縣名地下濕多𦚧䏰蟲𦚧音蠢
bVi食閏;順:從也食閏切二|揗:說文摩也
#問
DXO亡運;問:訊也又姓今襄州有之亡運切十一|璺:破璺亦作㼂方言曰秦晉器破而未離謂之璺|絻:喪服亦作免|汶:水名|紊:亂也|聞:名達詩曰令聞令望|莬:新生草也|脕:+上同詩曰薇亦柔止鄭玄云柔謂脃脕之時|抆:拭也|鼤:鼠文|娩:生也又音免
kXu王問;運:遠也動也轉輸也國語云廣運百里東西爲廣南北爲運又姓出姓苑又漢複姓二氏史記云秦後以國爲姓有運奄氏後漢梁鴻改姓爲運期氏王問切十六|暈:日月傍氣|餫:野餉|䩵:治鼓工考工記云䩵人爲皋陶皋陶鼓木也又況万切|韗:+上同|鄆:邑名又州名魯太昊之後風姓禹貢兗州之域即魯之附庸須句國也秦爲薛郡地漢爲東平國武帝爲大河郡隋爲鄆州亦姓魯大夫食采於鄆後因氏焉|員:姓也前涼錄有金城員敞唐有棣州刺史員半千|䲰:鳥名似烏一名同力|忶:心悶|鶤:雞三尺曰鶤又音昆|𧶊:物數亂也|韻:韻和也|䚋:眾視|𧡡:+上同|𤸫:病也又尤粉切|緷:說文緯也
iXu許運;訓:誡也男曰教女曰訓又姓許運切五|爋:火乾物|臐:羊羹|薰:薰香又許云切|鐼:鐵類
BXO匹問;湓:含水潠也匹問切四|忿:怒也|魵:小魚|瀵:水浸也又音奮
AXO方問;糞:穢也方問切八|𥻔:+上同|𡊅:𡊅掃除也|拚:+上同見禮|僨:僵也|奮:揚也鳥張毛羽奮奞也又姓左傳楚有司馬奮揚|瀵:水名有三眼一在蒲州泉眼大如車輪濆沸湧出一在同州界夾黃河一在河中央皆潛通大小並相似俱深不測又音湓|㱵:殨也
hXu於問;醞:醞釀於問切又於刎切四|慍:怒也|縕:亂麻|薀:習也俗作蘊又音上聲
dXu居運;攈:說文拾也居運切五|捃:+上同|皸:足坼又居云切|𧱝:豕求食也又衢物切|䝍:小野豕名
fXu渠運;郡:說文曰周制天子地方千里分爲百縣縣有四郡故春秋傳曰上大夫受郡是也至秦初置三十六郡以監其縣釋名曰郡羣也人所羣聚也渠運切一
CXO扶問;分:分劑扶問切又方文切五|㿎:㿎㾙瘡悶|𢅯:囊滿而裂|秎:穧秎穫也|坌:塵也又房粉切
#焮
iYe香靳;焮:火氣香靳切六|炘:+上同|㾙:瘡中冷|庍〈𤴾〉:-|𦜓:+並上同|脪:說文曰瘡肉反出也
dYe居焮;靳:靳固又姓楚有大夫靳尚居焮切五|斤:爾雅曰明明斤斤察也又居勤切|㧆:覆巾名|㨷:說文拭也|劤:多力皃
fYe巨靳;近:附也巨靳切又巨隱切一
hYe於靳;㒚:依人也於靳切八|懚:+上同|隱:隈隱之皃又於謹切|檼:屋脊又棟也|𤔌:所依據也|㥯:說文謹也|㶏:水名又於覲勤切|㡥:㡥裹相著
gYe吾靳;垽:爾雅曰澱謂之垽吾靳切一
#願
gZu魚怨;願:欲也念也思也說文云大頭也魚怨切四|𩕾:+上同說文云顛頂也|傆:說文黠也|愿:敬也善也謹也
hZu於願;怨:恨也說文恚也於願切二|䛄:從也說文慰也又於阮切
AZO方願;販:買賤賣貴也方願切二|畈:田昄
eZu去願;券:券約說文契也釋名曰券綣也相約束繾綣以限也去願切六|絭:束腰繩也|勸:獎勸也勉也助也教也又姓|虇:萌荀又蘆牙|綣:繾綣志盟又去阮切|韏:典也又革中辨也說文又九萬切
DZO無販;万:十千又虜三字姓二氏西魏有柱國万紐于謹周書唐瑾樊深並賜姓万紐于氏無販切十八|萬:萬舞字林云萬蟲名也亦州名自漢及梁猶爲𦚧䏰縣地後魏分置萬川郡及魚泉縣武德初割信州南浦置浦州貞觀改爲萬州又姓孟軻門人萬章|輓:輓車也亦作挽本又音晚|蔓:瓜蔓又姓左傳楚有蔓成然|曼:長也|蟃:螟蛉蟲|鰻:魚名|𨞼:蜀有𨞼鄉|娩:纂文云姓也古萬字|獌:獌㹶獸長百尋說文曰狼屬也爾雅曰貙獌似狸|䝡:貙獌似狸或作此䝡|𩆊:姓梁公子𩆊杰之後|𦂔:挽舟繩也|贎:贈貨|䡬:戰車以遮矢也|㿸:皮帨又無遠切|脕:肌澤|鬗:髮長
CZO符万;飯:周書云黃帝始炊榖爲飯符万切六|𩚳:+上同俗又作飰|閞:門欂櫨也|𥹇:粉𥹇|㶗:泉水|𧉤:蟲名
BZO芳万;嬎:嬎息也一曰鳥伏乍出說文曰生子齊均也或作㛯芳万切十|㽹:吐㽹|𨠒:一宿酒|𡗹:+上同|𣀔:小舂|㤆:急性|娩〈婏〉:說文云兔子也婏疾也|𡚪〈奿〉:說文云其義闕|㪻:量也又居願切|汳:水在睢陽
dZe居万;建:立也樹也至也又木名在弱水直上百仞無枝又姓楚王子建之後漢元后傳有建公又州名居万切二|旔:捷也
hZe於建;堰:堰水也於建切十|鄢:地名在楚|郾:+上同|䞁:引與爲價又於面切|傿:+上同|褗:郭璞云衣領也|㰽:大呼用力|漹:水名在襄陽宜城入漢江也|嫣:長皃|𡙷:說文曰大皃也
iZe許建;獻:進也禮云大曰羹獻又姓風俗通有秦大夫獻則許建切四|憲:法也又姓出姓苑|𧾨:走意|瀗:水名
iZu虛願;楥:靴履楥又法也虛願切四|楦:+俗|韗:攻皮治鼓工也亦作䩵又音運|𩋢:+俗
fZe渠建;健:伉也易曰天行健渠建切二|腱:筋本也
TZi芳｟反｠〈叉〉万;𣀔:小舂也亦作䊲芳万切一
kZu于願;遠:離也于願切一
gZe語堰;𤬝:瓢也語堰切二|鬳:鬲屬
fZu臼万;圈:邑名臼万切一
dZu居願;卛:卛物也說文曰抒滿也居願切二|絭:弦也
#慁
jai胡困;慁:悶亂也說文憂也一曰擾也又禮云儒有不慁君王慁猶辱也亦作㥵胡困切四|溷:濁也|俒:全也|圂:廁也一云豕所居也
Eai都困;頓:說文云下首也亦姓魏志華佗傳有督郵頓子獻都困切三|扽:撼扽|敦:豎也又都昆徒官二切
Qai蘇困;巽:卦名說文具也亦作𢁅蘇困切六|𩕧〈顨〉:說文云巽也此易顨卦爲長女爲風者|潠:潠水|𠹀:+上同|遜:遁也從也伏也恭也|愻:順也
eai苦悶;困:亂也逃也病之甚也悴也極也苦悶切四|𣏔:+古文|涃:水名|𩒱:耳門又苦昆切
Hai奴困;嫩:弱也奴困切四|媆:+上同|腝:肉腝|抐:搵抐按物水中
hai烏困;搵:烏困切二|䭡:相謁食又於恨切
DaC莫困;悶:說文曰懣也易曰遯世無悶莫困切二|懣:煩也又莫緩亡損二切
Pai徂悶;鐏:說文曰柲下銅也曲禮曰進戈者前其鐏徂悶切五|臶:人名魏時張臶又至也|栫:木名|𦪚:船底孔也|鱒:魚名又魚入泥
dai古困;睔:大目露睛古困切七|睴:視皃|琯:玉出光也又音管|璭:+俗|㴫:水名|𧬪:摩人也|謴:順言謔弄皃出聲譜
BaC普悶;噴:吐氣普悶切三|歕:+上同|湓:水聲
Gai徒困;鈍:不利也頑也徒困切五|遁:逃也隱也去也|遯:+上同|鶨:癡鳥|𩔂:𩔂顐
Oai倉困;寸:說苑曰度量衡以粟生之十粟爲一分十分爲一寸十寸爲一尺家語云孔子曰布指知寸倉困切二|䍎:瓦器又千見切
CaC蒲悶;坌:塵也亦作坋蒲悶切二|𣴞:水聲
gai五困;顐:禿也五困切二|諢:玉篇云弄言
Iai盧困;論:議也盧困切又虜昆切三|溣:水中曳船曰溣|碖:大小勻皃又盧本切
AaC甫悶;奔:甫悶切又音犇一
iai呼悶;惛:迷忘也呼悶切又呼昆切一
Nai子寸;焌:然火周禮云遂龡其焌子寸切三|𩯄:委髮也|捘:左傳曰涉佗捘衛侯之手
#恨
jbS胡艮;恨:怨也胡艮切一
dbS古恨;艮:卦名也止也說文限也古恨切四|茛:草名|珢:石次玉|詪:語也
gbS五恨;䭓:飽也五恨切一
hbS烏恨;䭡:䭡䭓飽也烏恨切一
#翰
jcS侯旰;翰:鳥羽也高飛也亦詞翰說文曰天雞赤羽也又姓左傳曹大夫翰胡侯旰切二十五|捍:抵捍|扞:以手扞又衛也|鼾:鼾睡|螒:螒天雞爾雅注云小蟲黑身赤頭一名莎雞|垾:小堤|豻:野狗又音岸|釬:釬金銀今相著亦作銲|汗:熱汗|悍:猛悍|瀚:瀚海北海|閈:里也居也垣也說文曰閭也門汝南平輿里門曰閈|𤿧:射𤿧以皮𤿧臂|駻:馬高六尺說文曰馬突也|雗:雗鵲鷽別名|䮧:馬毛長也|馯:姓也|𧃙:草名又音寒|䏷:䑇䏷刀箭瘡藥出古兵格|忓:善也|㢨:拒也又關名在巫縣|矸:磓也|㲦:長毛|㪋:說文止也|𩹼:魚名
FcS他旦;炭:火炭又姓西京雜記有長安炭虯他旦切六|歎:歎息|嘆:+上同|湠:湠漫水廣皃出字林|𣁗:𣁗𣁜無文章皃|㛶:㛶𡞟無宜適也
hcS烏旰;按:抑也止也烏旰切七|案:几屬也史記曰高祖過趙趙一張敖自持案進食又曹公作欹案臥視書又察行也考也驗也|洝:說文曰渜水也|晏:晚也又於諫切|荌:草也|䢿:里名|䅁:轢禾
EcS得按;旦:早也得按切八|疸:黃病|鴠:䳚鴠鳥名|觛:小觶又丁但切|狚:獦狚獸名似狼|怛:傷也|笪:笞也|㡺:小舍
GcS徒案;憚:難也又忌惡也徒案切六|彈:行丸又徒丹切|澶:澶漫|僤:疾也周禮云句兵欲無僤|但:辤也又徒亶切|撣:撣觸也又徒于切
dcS古案;旰:日晚也晏也古案切十一|榦:楨榦築垣板|倝:說文曰日始出光倝倝也俗作𣉙|幹:莖幹又強也又姓|杆:檀木|𧹳:赤色也|盰:說文曰目多白也一曰張目也|骭:脅也|𣵼〈涆〉:滮滮涆涆水流疾皃|𢁗:布袋|矸:石淨
gcS五旰;岸:水涯高者五旰切九|犴:獄也又五干切|豻:野狗|頇:頭無髮也|䮗:𩢔䮗馬行又馬白頟至脣|㷳:說文云火色也讀若鴈|𡹼:厝也|喭:弔失國又五弁切|𨲊:長大
ecS苦旰;侃:正也苦旰切又苦旱切六|偘:+上同|靬:乾革|看:又苦干切|衎:樂也|䳚:䳚鴠鳥名
icS呼旰;漢:水名又姓姓苑云東莞人呼旰切九|暵:日氣乾|𤳉:耕田|熯:火乾又人善切|䍐:枹䍐縣在河州亦作罕枹音扶|𡅽:呼也|𤅩:水濡乾也|䎯:冬耕地|厂:山石之崖
IcS郎旰;爛:火熟又明也郎旰切七|爤:+上同見說文|瀾:波也又音蘭|𢒞:粲𢒞文章皃|糷:飯相著爾雅曰摶者謂之糷|鑭:光鑭|讕:逸言又蘭嬾二音
HcS奴案;攤:按攤也奴案切又他丹切六|灘:水奔又他丹切|難:患也又奴丹切|𦍀:縕也|㬮:說文曰安㬮溫也|𢆃:巾捫撋又塗著也
OcS蒼案;粲:鮮好皃又優也察也明也亦作㛑又姓出姓苑蒼案切六|㛑:詩傳云三女爲㛑又美好皃詩本亦作粲說文又作𡛝|燦:明淨皃|璨:美玉又璀璨|薒:草可爲席|𪆶:鳥名
QcS蘇旰;繖:蓋也蘇旰切又蘇旱切六|𢿱:分離也布也說文作𢽳分離也散雜肉也今通作散又蘇旱切|散:+見上注|帴:二幅說文帬也|䈀:說文曰竹器也|𩀼:說文曰繳𩀼也一曰飛散也
NcS則旰;贊:佐也出也助也見也說文本作贊則旰切十一|讚:稱人之美|酇:縣名在南陽|饡:羹和飯也|趲:散走|灒:水濺|𡳋〈𩛻〉:食也|㜺:女從|䰖:髮光澤也|襸:衣好皃|攢:訟也
PcS祖〈徂〉贊;㜺:不謹也一曰美好皃祖贊切五|䏼:禽獸食餘|𣧻:+同上|穳:禾肥死又在丸切|囋:譏囋嘲也又才葛切
#換
jci胡玩;換:易也胡玩切九|逭:逃也迭也轉也步也周也|𩁧:+上同|肒:皰肒|垸:漆骨垸也|䯘:+上同|漶:漫漶不可知也|䀓:睕䀓轉目又大目皃|𤴯:癰疽屬也
Nci子筭;䂎:鋋也子筭切二|鑽:錐鑽
hci烏貫;惋:驚歎烏貫切六|腕:手腕|𦞿〈𢯲〉:+上同|捥:亦同|睕:睕䀓大目|琬:琬圭又於阮切
dci古玩;貫:事也穿也累也行也又姓漢有趙相貫高古玩切二十八|矔:張目|祼:祭名說文曰灌祭也|館:館舍也周禮五十里有市市有館館有積以待朝聘之客俗作舘|瓘:玉升左傳曰瓘斚玉瓚杜預云瓘珪也|鑵〈罐〉:汲水器也|𤼐:病也|痯:+上同|灌:水名在廬江又聚也澆也漬也又姓漢有灌嬰|雚:雚雀鳥|鸛:+上同|樌:木叢生也|鏆:臂鐶|㷄:楚人云火|懽:憂無告也|錧:車軸頭鐵一曰江南人呼犁刃|爟:烽火說文曰取火於日官名舉火曰爟周禮曰司爟掌行火之政令|遦:行也|冠:冠束白虎通曰男子幼娶必冠女子幼嫁必笄又姓列仙傳有仙人冠先又音官|觀:樓觀釋名曰觀者於上觀望也說文曰諦視也爾雅曰觀謂之闕亦姓左傳楚有觀起又音官|涫:沸也|悹:憂也|悺:+上同|盥:說文曰澡手也从臼水臨皿也春秋傳曰奉匜沃盥|棺:殮屍又音官|毌:穿也|婠:好皃|䘾:袴別名
Oci七亂;竄:逃也誅也放也藏也匿也從鼠在穴中七亂切五|鑹:小矟|爨:炊爨又姓華陽國志云昌寧大姓有爨習蜀志云建寧大姓蜀錄有交州刺史爨深|殩:殩孝秦人云饋喪家食|䂎:鋋也本音鑽俗爲槍䂎字
gci五換;玩:弄也五換切五|貦:+說文上同|翫:習也|妧:好皃|忨:忨貪
Gci徒玩;段:分段也又姓出武威本自鄭共叔段之後風俗通云段干木之後段氏有出遼西者本鮮卑檀石槐之後晉將段匹磾徒玩切三|毈:毈壞|椴:木名
Ici郎段;亂:理也又兵寇也不理也俗作乱郎段切四|灓:絕水渡也亦作亂|𢿢:煩也|𤔔:理也
Eci丁貫;鍛:打鐵丁貫切六|腶:籤脯|碫:礪石|斷:決斷俗作𣂾断|瑖:石之似玉|踹:足踹
Fci通貫;彖:易有彖象通貫切四|褖:后衣|貒:野豚|湪:水名
ici火貫;喚:呼也火貫切八|嚾:+上同|𡅽:+上同出說文|煥:火光|奐:文彩明皃又姓|渙:水散又音翽|𥈉:國在流沙東|喛:恚也又虛元切
Qci蘇貫;筭:計也數也說文曰筭長六寸計歷數者也又有九章術漢許商杜忠吳陳熾魏王粲並善之世本曰黃帝時隷首作數蘇貫切四|蒜:葷菜也張騫使西域得大蒜胡荽|笇:竹器|祘:明也
DcC莫半;縵:說文曰繒無文也漢律曰賜衣者縵表白裏莫半切十|幔:帷幔|漫:大水|𢿜〈𣁜〉:𣁗𣁜|𦔔:不蒔之田也|獌:狼屬又音萬|䝢:+上同|墁:所以塗飾牆又莫干切|鏝:+上同又鏝刀工人器|謾:欺也又莫干切
AcC博慢〈漫〉;半:物中分也博慢切七|絆:羈絆|靽:+上同|姅:傷孕|𩢔:𩢔䮗馬行|㪵:五升|𠯘:𠯘喭失容
BcC普半;判:剖判又分也普半切八|泮:泮宮禮記作頖|頖:+見上注|沜:水涯|眫〈胖〉:牲之半體|姅:傷孕又音半|冸:冰散|牉:牉合夫婦也本亦作判周禮云媒氏掌萬民之判
CcC薄半;叛:奔他國薄半切四|𡞟:㛶𡞟無宜適也|畔:田界也|伴:伴奐見詩
Hci奴亂;偄:偄弱也奴亂切五|愞:+上同|稬:稻稬也|渜:浴餘汁也|𪋐:說文曰鹿麛也
Pci在玩;攢:聚也在玩切一
eci口喚;䥗:燒鐵炙也口喚切二|䲌:魚撞罩聲
#諫
ddS古晏;諫:諫諍直言以悟人也又姓風俗通云漢有治書侍御史諫忠古晏切三|澗:溝澗爾雅曰山夾水澗亦作磵𡼏|鐧:車閒鐵也
gdS五晏;鴈:禮曰孟春之月鴻鴈來賓白虎通曰贄用鴈者取其隨時五晏切六|鳫:+上同|雁:鳥也出說文|贗:僞物|偐:+上同|𤜵:逐獸犬
hdS烏澗;晏:柔也天清也又晚也又姓左傳齊有晏氏代爲大夫烏澗切五|騴:馬尾白也|䁙:目相戲也|鴳:爾雅曰鳸鴳郭璞云今鴳雀|鷃:+上同
VdS所晏;訕:謗也所晏切又所攀切七|汕:魚乘水上|狦:獸名似狼說文曰惡健犬也|𦌔:取魚網也|疝:病也又所姦切|柵:籬柵又又革切|䴮:餅麴
jdS下晏;骭:脛骨下晏切又音旰二|娨:慢也
DdC謨晏;慢:怠也倨也易也俗作𢢔謨晏切五|嫚:侮易|謾:欺謾|縵:緩縵|㾺:牛馬病又莫駕切
hdi烏患;綰:鉤繫烏患切三|贃:支財貨出文字指歸|𩈬:面曲皃
jdi胡慣;患:病也亦禍也憂也惡也苦也又姓出何氏姓苑胡慣切九|𢠶:+古文|擐:擐甲|宦:仕宦亦閹宦又學也左傳云宦三年矣|轘:車裂人又音還|豢:穀養畜又牛馬曰芻犬豕曰豢|䍺:獸名似羊無口出山海經|槵:無槵木名|繯:縞文
ddi古患;慣:習也古患切六|丱:𩮰角也幼稚也|摜:摜帶|倌:主駕官也又音官|串:穿也習也|矔:矔眮轉目
Vdi生患;㝈:雙生子亦作孿生患切又所眷切二|涮:涮洗也
Tdi初患;篡:奪也逆也初患切一
gdi五患;薍:菼薍五患切一
UdS士諫;輚:臥車又寢車亦作轏士諫切五|棧:木棧道又士限切|虥:虎淺毛又士限切|𧮺:谷在上艾|䗃:馬䗃蟲名
BdC普患;襻:衣襻普患切一
Mdi女患;奻:訟也女患切一
TdS初鴈;羼:羊相閒也初鴈切三|鏟:削木器又初限切|䴼:穀麥䴼也
KdS丑晏;㬄:赤色也丑晏切三|㾺:牛馬病
#襇
deS古莧;襇:襇裙古莧切六|𤜵:逐虎犬|閒:廁也瘳也代也送也迭也隔也又音平聲|覸:視也|𨣉:醎也|𧙧:古衣
jeS侯襇;莧:菜名侯襇切三|藖:莝餘|粯:粉頭粯子
CeC蒲莧;瓣:瓜瓠瓣也蒲莧切五|辨:具也周禮曰以辨民器又步免切|辦:+俗|𥌊:小見|釆:說文云辨別也象獸指爪分別也
BeC匹莧;盼:美目匹莧切二|𥌊:小兒白眼視也
jei胡辨;幻:幻化胡辨切一
DeC亡莧;蔄:人姓亡莧切一
LeS丈莧;袒:衣縫解又作䘺丈莧切三|綻:+上同|䋎:補縫
AeC晡幻;扮:打扮晡幻切一
dei古幻;鰥:鰥視古幻切一
#霰
QfS蘇佃;霰:雨雪雜又作䨘𩆵釋名曰霰星也水雪相搏如星而散說文云霰稷雪也蘇佃切九|䨘:-|𩆵:+並上同|㪇:散也|𢊰:舍也亦作𪎘|先:先後猶娣姒又姓出河東又蘇前切|汛:灑汛又所隘息進二切|軐:轉軐車迹|𥰳:紡𥰳也
OfS倉甸;蒨:草盛倉甸切十三|茜:草名可染絳色|輤:載柩車蓋大夫以布士以葦席|綪:青赤色|倩:倩利又巧笑皃|芊:芊菄草木相雜皃|䛹:䛹數|棈:木名|𢂺:䛹當音絢也又幧頭|𧚫:𧛸也|䍎:紡錘說文曰瓦器也又七鈍切|䑶:輕舟|篟:青竹
ifi許縣;絢:文彩皃許縣切八|絃:+上同|敻:營求也又休娉切|眴:目動又音舜|駽:青驪馬也|𧾣:走皃|㧦:擊也|讂:流言有所求也又古縣切
jfi黃練;縣:郡縣也釋名曰縣懸也懸於郡也古作寰楚莊王滅陳爲縣縣名自此始也又姓孔子門人縣單父黃練切十五|寰:+古文|袨:好衣|眩:瞑眩書曰若藥弗瞑眩厥疾弗瘳|炫:明也火光也|衒:自媒|𧗳:+上同|䝮:行䝮賣|贙:獸名又音泫|𩑹:顋後|迿:出表辝|姰:狂也又相倫切|玹:玉名|䀏:目搖|眴:+上同
dfi古縣;睊:視皃古縣切十一|讂:流言|瓹:盆底孔|䣺:說文曰𨢌酒也𨢌音歷|𦌾:鳥羅|罥:綰也|懁:急性|䡓:車搖|獧:躍也|狷:急也又音絹|㢾:𩪧也
GfS堂練;電:陰陽激曜釋名曰電殄也乍見則殄滅也堂練切十八|殿:宮殿風俗通曰殿堂象東井形刻爲荷菱荷菱水物所以厭火又都甸切|奠:設奠禮注云薦也陳也書傳云定也|畋:平皃|澱:澱滓亦藍澱也|淀:陂淀泊屬|甸:郊甸書曰五百里甸服|佃:營田|鈿:寶鈿以寶飾器又音田|闐:于闐國在西域或作窴又音田|涏:美好皃|𪑩:藍𪑩染者也|填:塞填|窴:+上同|壂:堂基|㞟:偫也又音頂|𡱂:髀也|𧽍:走也
FfS他甸;瑱:玉名說文曰以玉充耳也詩曰玉之瑱也他甸切又音田四|顛:+上同|滇:滇㴐大水又音田|睼:迎視又音啼
IfS郎甸;練:白練又姓何氏姓苑云南康人郎甸切十五|浰:水疾流皃|鍊:鍊金|揀:揀擇|楝:木名鵷鶵食其實|㼑:瓜㼑|鰊:魚名似鱦|僆:雞未成也|萰:草名|堜:堜塘墟名在吳郡|湅:熟絲也周禮曰㡛氏湅絲|𣿊:熟𣿊|㪝:搥打物也|𣞰:䉛蠶|𤗛:木解理也
dfS古電;見:視也又姓出姓苑古電切又胡電切二|鋻:鋻鐵
HfS奴甸;晛:日光奴甸切四|㬗:+上同|㜣:姓也|㲽:說文曰水也
efS苦甸;俔:罄也譬也苦甸切八|牽:牽挽也又苦堅切|菣:爾雅曰蒿菣又去刃切|蜆:爾雅曰蜆縊女郭璞曰小黑蟲赤頭喜自經故曰縊女又音哯|㯠:橫㯠木|涀:水名|汧:泉出不流|䵖:穄也又口典切
jfS胡甸;見:露也胡甸切四|現:+俗|涀:水名|𨘇:無違
gfS吾甸;硯:筆硯釋名云硯研也研墨使和濡也吾甸切六|研:磨研又音平聲|𨁍:行不正也|𤜵:逐虎犬也|豜:爾雅云麕絕有力豜|趼:趼骨
hfS於甸;宴:安也息也於甸切十三|驠:馬名|燕:說文云玄鳥也作巢避戊己|鷰:+俗今通用|醼:醼飲周禮云以饗燕之禮親四方之賓客詩云鹿鳴燕羣臣嘉賓也古無酉今通用亦作宴|讌:+讌會本亦同上|嬿:嬿婉並也又於典切|嚥:吞也|咽:+上同|㬫:星無雲出說文|溎:大水皃|酀:邑名|𥉛:視也或作𥍂
NfS作甸;薦:薦席又薦進也說文曰獸之所食艸古者神人以廌遺黃帝帝曰何食何處曰食薦夏處川澤冬處松柏又姓出姓苑作甸切廌丈買切二|𧲛:畜食
DfC莫甸;麪:束晳麪賦云重羅之麪塵飛雪白莫甸切八|麵:+上同|瞑:瞑眩|眄:斜視|㴐:滇㴐水大皃|𡧍:冥合|𩈹:𩈹炫汗血|𥻩:屑米
BfC普麵;片:半也判也析木也普麵切三|䏒:半體也|㸤:爾雅革中絕謂之㸤革車轡勒也本亦作辨
PfS在甸;荐:重也仍也再也在甸切七|洊:水荒曰洊亦再也易曰洊雷震|臶:重至又魏有高士張臶戴鵀之鳥巢其門陰者又徂悶切|栫:圍也左傳云栫之以棘|瀳:水名|袸:小帶|𨷓〈𨷳〉:門次
hfi烏縣;䬼:饜飽烏縣切四|裫:廣雅云衣衿袖曲處|噮:甘不猒也|肙:小蟲也又空也
EfS都甸;殿:軍在前曰啓後曰殿又殿最漢書音義云上功曰最下功曰殿都甸切又堂練切三|唸:唸㕧呻也亦作𠿍𣢁經典又作殿屎|𠿍:+見上注
ifS呼甸;𩎌:在背曰𩎌亦作韅呼甸切又呼典切一
#線
QgS私箭;線:線縷也周禮云縫人掌王宮縫線之事以役女御縫王及后衣服私箭切四|綫:+細絲出文字指歸說文同上|惗:思惗|鮮:姓也本音平聲
XgS之膳;戰:懼也恐也又姓之膳切二|顫:四支寒動
ZgS時戰;繕:補也時戰切十二|鄯:鄯善西域國名|擅:專也|膳:食也|饍:+上同|僐:廣雅云姿態|禪:封禪又禪讓傳受|䄠:+古文|單:單父縣亦姓|𤮜:器緣|𦉕:+上同|嬗:說文緩也一曰傳也漢書霍去病子名嬗
gga魚變;彥:美士魚變切六|唁:弔失國說文曰弔生也詩曰歸唁衛侯|喭:+上同|甗:甑也|諺:俗言|這:迎也
egW去戰;譴:問也責也怒也讓也亦姓去戰切五|遣:人臣賜車馬曰遣車又去尠切|䪈:𦝫帶|晵:雨而晝止|繾:又去演切
dgm吉掾;絹:縑也廣雅曰䋷𦇎鮮支縠絹也吉掾切五|狷:褊急又古縣切|鄄:鄄城縣在濮州|㯞:㯞青木皮葉可作衣似絹出西域焉耆國|䚈:視也
kgq王眷;瑗:玉名王眷切又于願切五|援:接援救助也亦姓|媛:淑媛|褑:佩帶|院:垣院
DgG彌箭;面:向也前也說文作𡇢顏前也俗作靣彌箭切二|偭:說文曰鄉也禮少儀云尊壺者偭其鼻
Ygi尺絹;釧:鐶釧續漢書曰孫程十九人立順帝各賜金釧指鐶尺絹切四|竁:穿也又初稅切|穿:貫也又音川|諯:相讓也
lgi以絹;掾:宮名以絹切四|緣:衣緣|𢐄:弓𢐄|䬇〈𩘍〉:再揚穀又小風也
JgS陟扇;𩥇:馬土浴陟扇切三|𧝑:周禮王后之六服其一曰𧝑衣|襢:+上同
cgi人絹;𤲬:城下田人絹切又而兗切一
NgS子賤;箭:箭竹高一丈節閒三尺可爲矢爾雅曰東南之美者有會稽之竹箭子賤切九|𥳭:+古文|鬋:女鬢垂皃|葥:草名|湔:水名在蜀|榗:木名|籛:陸終子名又子田切|濺:濺水又作甸切|煎:甲煎又將仙切
YgS昌戰;硟:展繒石昌戰切一
agS式戰;扇:崔豹古今注舜作五明扇說文扉也式戰切四|煽:火盛皃又音羶|傓:熾盛|𧎥:蠅動翅也說文曰蠅醜𧎥|𦶋:草名|𥰢:竹
hga於扇;躽:怒瞋於扇切三|𥈔:視皃又於殄切|堰:堰埭
dgq居倦;眷:眷屬說文顧也居倦切十五|睠:+上同|捲:西捲縣名在日南|弮:曲也又書弮今作卷|卷:+上同|桊:牛拘|帣:囊也亦三斛爲一帣|絭:連弩三十絭共一臂|犈:爾雅云牛腳黑犈又音權|觠:爾雅云羊屬角三觠羷郭璞云觠角三匝|𧯦:黃豆又求晚切|飬〈餋〉:祭名|䖭:䖭蠾蜘蛛別名|𥸭〈𢍏〉:說文曰摶飯也隷省作龹眷字類從此俗作灷|勬:勤也又居員切
fgq渠卷;倦:疲也猒也懈也說文又作劵勞也或作勌渠卷切五|𣜨:緣鞾縫也|韏:+上同|襈:重繒|淃:水名
Igi力卷;戀:慕也力卷切四|灓:又音亂|䜌:何承天云姓也漢有䜌秘爲汝南郡太守|孌:順也
Kgi丑戀;猭:獸走草丑戀切二|鶨:鳥名又音彖
AgK彼眷;變:化也通也易也又姓出姓苑彼眷切一
Vgi所眷;𨏉:𨏉車軸所眷切二|㝈:一乳兩子亦作孿又生患切
Ogi七絹;縓:絳色七絹切又七全切三|諯:相責|𥆊:更視見皃說文作𢌨相顧視而行也又弋絹切
CgK皮變;卞:縣名在魯又姓出濟陰本自有周曹叔振鐸之後曹之支子封于卞遂以建族皮變切十五|拚:擊手|抃:+上同|弁:周冠名|㝸:+上同|汴:水名在陳留亦州名秦屬三川郡漢爲陳留郡留鄭邑爲陳所并遂名之東魏置梁州周改爲汴州|㺕:犬鬭聲|閞:門欂櫨又音飯|昪:日光皃|匥:笥也|䒪:雀草|笲:竹器|㺹:玉名|忭:喜皃|䪻:䪻冠
Rgi辝（辭）戀;㳬:回泉辝戀切九|鏇:轉軸裁器|縼:長繩繫牛馬放|𢳄:+上同|旋:遶也|嫙:好皃|䍻:羊也|𧾩:走也|𦛔:𦛔短者
Qgi息絹;選:息絹切八|𤂳:飲也|𤂿:口含水濆|䍻:羊也|𦌔:罥獸足網|䠣:+上同|繏:索也|渲:小水
Ugi七〈士〉戀;䉵:說文曰具食也七戀切九|饌:+上同|𦠆:+上同見儀禮|襈:緣也|僎:具也|譔:專敬|𤩄:珍𤩄|僝:見也具也|𠨎:具也
Sgi莊眷;孨:謹也莊眷切一
Lgi直戀;傳:訓也釋名曰傳傳也以傳示後人也直戀切又直專丁戀二切二|𦁆:𦁆繞也
PgS才線;賤:輕賤又姓風俗通云漢有北平太守賤瓊才線切三|諓:巧讒皃|餞:酒食送人
RgS似面;羨:貪慕又餘也又姓列仙傳有羨門似面切二|䢭:遮也
BgG匹戰;騗:躍上馬匹戰切二|偏:又音篇
Zgi時釧;𢮨:縣繩望時釧切二|叀:說文曰專小謹也
MgS女箭;輾:水輾女箭切二|碾:+上同
Jgi知戀;囀:韻也又鳥吟知戀切三|傳:郵馬釋名曰傳傳也人所止息去後人復來轉轉相傳無常人也又直專直戀二切|轉:流轉又張兗切
lgS于〈予〉線;衍:水也溢也豐也于線切又以淺切八|莚:蔓莚不斷|羨:延也進也|狿:獌狿大獸名長八尺|延:曼延不斷其莚也|涎:湎涎水流|䢭:移也|𠻤:大笑
CgG婢面;便:利也婢面切又音平聲一
LgS持碾;邅:逐也持碾切又張連切二|纏:纏繞物也
IgS連彥;𤹨:疰𤹨惡病也連彥切二|摙:按摙之皃
egq區倦;𥛁〈䄐〉:祭祀區倦切三|絭:臂繩|䠣:罺網
Xgi之囀;剸:切肉皃之囀切一
AfC方見;徧:周也說文帀也方見切二|遍:+俗
#嘯
QhS蘇弔;嘯:說文曰吹聲也蘇弔切五|歗:+籀文|㩋:打也|䐹:切肉合糅|熽:火皃
FhS他弔;糶:賣米也他弔切十|𥺋:+俗|眺:視也|覜:周禮曰大夫眾來曰覜寡來曰聘|趒:越也|咷:叫咷楚聲又音桃|頫:薛琮云低頭聽本又音府|窱:䆞窱深邃皃|鋽:鉎鋽|絩:綺絲數也
EhS多嘯;弔:弔生曰唁弔死曰弔多嘯切又音的七|伄:伄儅不當皃|瘹:瘹星狂病|釣:釣魚淮南子曰詹公釣千歲之鯉詹公古善釣者呂氏春秋曰太公釣於滋泉以遇文王|窵:窵窅深也|蔦:寄生草|𨑩:至也又音的
dhS古弔;叫:呼也古弔切十二|訆:說文曰大呼也|徼:循也小道也|𢅎:行縢又古鳥切|譥:訐也又痛聲也|激:水急又古歷切|噭:噭噭深聲|嘂:大壎說文曰高聲也一曰大呼|獥:狼子|敫〈㰾〉:歌也|鸄:爾雅云鸄鶶鷵似烏而蒼白色|𨎬:𨎬車轊
HhS奴弔;尿:小便也或作溺奴弔切二|㞙:+古文
GhS徒弔;藋:藜藋也徒弔切七|銚:燒器又音姚|掉:振也搖也又徒了切|調:選也韻調也又音苕|莜:草田器又音苕|𥁮:+上同|嬥:嬥嬈不仁又徒了切
ehS苦弔;竅:穴也苦弔切二|𢶡:旁擊亦作撽
IhS力弔;𩕐:𩕐顤長頭力弔切九|尥:牛脛交|嫽:嫽悷又音僚|料:料度量也又音僚|嘹:病呼|鐐:美金又音僚|璙:玉名|𦌒:魚網|炓:火光
ghS五弔;顤:五弔切五|獟:狂犬|澆:韓浞子名又音梟|鼼:仰鼻又牛救切|𠹑〈嘄〉:叫也
hhS烏叫;窔:隱暗處亦作㝔東南隅謂之㝔俗作穾烏叫切二|𥦒〈䆞〉:䆞窱幽深皃又音杳
iwf火弔〈即〉|ihS火弔|LgT火〈丈〉弔｟叫｠〈列〉;𢿿〈㱇〉:a說文云悲意也火弔切三|嬈:b嬥嬈不仁又而沼切|娎:c娎㛍喜皃
#笑
QiS私妙;笑:欣也喜也亦作笑私妙切五|㗛:+俗|肖:似也小也法也像也|韒:刀韒|鞘:+上同
XiS之少;照:明也之少切五|炤:+上同|詔:上命釋名曰詔照也照人暗不見事以此示之使昭然也又告也教也|𨹸:隄也界也|𠧙:卜問也又音邵
liS弋照;燿:熠燿說文照也弋照切十七|鷂:鷙鳥也莊子曰鷂爲鸇鸇爲布穀此物變也|搖:搖動又音遙|覞:普視說文曰並視也|𧡷:+上同|耀:光耀|曜:日光也又照也|𧢢:視誤也|𥌺:+上同|㞁:行不正也|𤪎:遺玉又音由|筄:屋上薄也|趭:走也|鷣:一名負雀|䔄:菟絲也又帝女花也|艞:對艞江中大船|讑:誤言皃
hiW於笑;要:約也於笑切又於招切三|葽:草盛皃又於招切|約:又於略切
LiS直照;召:呼也直照切一
ZiS寔照;邵:邑名又姓出魏郡周文王子邵公奭之後寔照切七|召:+上同|劭:自強也|𠧙:卜問也又音韶|𠣫:倒懸鉤也|䬰:小食又尺邵切|卲:高也
fia渠廟;嶠:山道又山銳而高渠廟切又音喬二|轎:𨋕車也又音喬
BiG匹妙;剽:強取又輕也匹妙切十一|彯:彯𦘕|㬓:置風日中令乾|漂:水中打絮韓信寄食於漂母又撫招切|僄:僄狡輕迅|翲:飛皃|䏇:聽纔聞出字林|勡:劫也|摽:摽落|嫖:身輕便也|慓:急疾
PiS才笑;噍:嚼也才笑切又子幺子由二切四|誚:責也|劁:刈也|趭:走也
DiG彌笑;妙:好也彌笑切三|玅:+上同|篎:爾雅云小管也
OiS七肖;陗:山峻亦作峭七肖切八|峭:+上同|篍:竹簫洛陽亭長所吹又七流切|㴥:峻波|哨:壺口黯者名也|俏:俏措好皃|帩:帩縛|𪑊:𪑊䵴
IiS力照;尞:說文曰祡祭天也凡從尞者作𡨶同力照切八|燎:照也一曰宵田又放火也又力小切|㙩:周垣|𤻲:𤻲病說文治也|療:+上同|熮:火皃|膫:炙也|鷯:爾雅云鶉一名鷯其雄曰鵲又音僚
eia丘召;趬:行輕皃丘召切五|𠿕:𠿕𧇠不安|㢗:玉篇云高屋|譑:譑弄|㚁:高㚁
gia牛召;𧇠:𠿕𧇠牛召切一
NiS子肖;醮:祭也子肖切十一|𥛲:+上同|釂:飲酒盡也|皭:白色|潐:盡也|爝:火|䩌:面不光|僬:行容止皃禮曰庶人僬僬|趭:走皃|𥡤:物縮小又作癄|䂃:目瞑
DiK眉召;廟:皃也齊職儀曰周有守禮之官掌先王之宗廟也亦作庿眉召切二|庿:+上同
CiG毗召;驃:驃騎官名又馬黃白色毗召切又卑笑匹召二切一
aiS失照;少:幼少漢書曰少府秦官掌山海池澤之稅以給供養又漢複姓五氏說苑趙簡子御有少室周魯惠公子施叔之後有少施氏家語魯有少正卯孔子弟子有少叔乘何氏姓苑有少師氏失照切又失沼切二|燒:放火又失昭切
KiS丑召;脁:祭也丑召切一
AiK方廟;裱:領巾也方廟切二|俵:俵散
fiW巨要;翹:尾起也巨要切又巨堯切一
ciS人要;饒:益饒人要切又人招切二|繞:卷取物皃
#效
jjS胡教;效:具也學也象也又效力效驗也胡教切八|効:+俗|校:校尉官名亦姓周禮校人之後又音教|斅:學也書曰惟斅學半|㤊:快也出孟子|傚:教也詩曰是則是傚毛萇云言可法傚也|𣱓:誤也|詨:詨叫
djS古孝;教:教訓也又法也語也元命包云天垂文象人行其事謂之教教之爲言傚也古孝切十一|𢼂:+古文|窖:倉窖|校:檢校又考校|鉸:鉸刀又裝鉸|酵:酒酵|覺:睡覺又音角|膠:膠黏物又音交|較:不等又音角|𡥈:又音交|珓:杯珓古者以玉爲之
ijS呼教;孝:孝順爾雅曰善父母爲孝孝經左契曰元氣混沌孝在其中天子孝龍負圖庶人孝林澤茂又姓風俗通云齊孝公之後呼教切六|哮:喚也又音虓|涍:水名在河南|嗃:大嗥又呼各切|詨:+上同|𡦳:解廌屬又音教
JjS都教;罩:竹籠取魚具也都教切五|䈇:+上同|䍜:說文曰覆鳥令不得飛走也|䞴:䞴趟跳皃|鵫:鵫雉今白雉也
AjC北教;豹:獸名崔豹古今注曰豹尾車周制也象君子豹變尾言謙也古軍正建之今唯乘輿建焉廣志曰狐死首丘豹死首山又姓風俗通曰八元叔豹之後北教切五|𧭤:𧭤譟惡怒吏也|𢖔:𢖔直史官|爆:火裂又音駮|䶂:鼠屬能飛食虎豹出胡地又音酌
ejS苦教;敲:擊也苦教切又苦交切三|礉:礉磽又口交切|巧:巧僞山海經曰義均始爲巧倕作百巧也又苦絞切
DjC莫教;皃:儀皃莫教切七|䫉:+說文同上|貌:+籀文|䡚:引也|𢂹:幗也|緢:旄雜絲也說文音苗|𢅉:綵雜文也
BjC匹皃;奅:起釀亦大也匹皃切六|窌:+上同說文窖也|炮:灼皃又步交切|拋:拋車又普交切|皰:面生氣也又旁教切|礮:礮石軍戰石也
KjS丑教;趠:行皃丑教切二|踔:猨跳
VjS所教;稍:均也小也說文曰出物有漸也所教切七|潲:豕食又雨濺也|揱:木上小或作𣕇|𣕇:+上同|娋:小娋侵也|𨛍:大夫食邑|𦓴:𦔔種
LjS直教;棹:檝也直教切四|櫂:+上同|濯:浣衣又直角切|㷹:火急煎皃
MjS奴教;橈:木曲奴教切又如昭切四|淖:泥淖|𠆴:不靜又猥也擾也|閙〈鬧〉:+上同
SjS側教;抓:爪刺也側教切三|癄:縮也小也亦作㾭|笊:笊籬
CjC防教;靤:面瘡防教切五|皰:面生氣也|鞄:治皮|鉋:鉋刀治木器也|骲:手擊
TjS初教;抄:略取也初教切八|鈔:+上同|縐:惡絹也又初爪切又側救切|耖:重耕田也|仯:仯仯小子|觘:角上也|𦨖:船不安也|罺:小網
hjS於教;靿:靴靿於教切五|袎:襪袎|㑃:很也戾也出字林|箹:竹節又於角切|軪:車有機
gjS五教;樂:好也五教切又岳洛二音三|磽:礉磽又五交切|𩳔:醜皃
UjS七〈士〉稍;巢:棧閣也七稍切又士交切一
#号
jkS胡到;号:号令又召也呼也諡也亦作號胡到切六|號:+上同又乎刀切|𤩭:石似玉也|㙱:上釜|䜂:相欺|𡟷:女字
GkS徒到;導:引也徒到切十四|翿:舞者所執|纛:左纛以犛牛尾爲之大如斗繫於左騑馬軶上|悼:傷悼|蹈:踐也|盜:盜賊|燾:覆也又徒刀切|幬:+上同|䆃:嘉禾一莖六穗|儔:隱也|𨱵:長皃|𠺛:年九十或作𡄒|䊭:黏也|䌦:不青不黃
EkS都導;到:至也又姓出彭城本自高陽氏楚令尹屈到之後漢有東平太守到質都導切六|禱:祭也請也文字音義云得福曰祠求福曰禱又當老切|倒:倒懸又當老切|𤓾:姓也出河內|𧛔:衣背縫|菿:大也
dkS古到;誥:告也謹也古到切七|郜:國名在濟陰又姓晉有高昌長郜玖|告:報也說文作𠰛又音梏|縞:白縑又音藁|膏:膏車又音高|𣝏:苦木|烄:交木然也
gkS五到;傲:慢也倨也說文作敖餘倣此五到切八|嫯:慢也|䫨:頭長|鏊:餅鏊|驁:馬名|奡:陸地行舟人也|謷:志遠皃|鷔:鷔鳦魚鳥狀也
DkC莫報;冃:說文曰小兒蠻夷頭衣也莫報切十九|帽:頭帽|耄:老耄亦作𦒷見經典省|𧂕:+上同見說文|芼:菜食又擇也搴也謂拔取菜也芼以蘋蘩爲羹亦草覆蔓|眊:目少睛|瑁:圭名天子所執|𤣽:+古文|冒:覆也涉也又莫北切|𥈆:低目細視|旄:狗足旄尾毛|毛:毛鷹鷂鸇|媢:夫妬婦出說文|𩿂:鳥輕毛|𢯾:手扶之也|覒:邪視也亦作㲘|㲝:鳥毛盛也|䋃:刺也絹帛毛起如刺也|𣔺:說文曰門樞之橫梁
IkS郎到;嫪:悋物又姓郎到切八|澇:淹也又水名或作潦|潦:+上同|勞:勞慰又郎刀切|僗:+俗|髝:髝髞麤急皃又音牢|癆:癆痢惡人說文曰朝鮮謂飲藥毒曰癆|𣟽:麻莖大也又施絞於𣝜也
OkS七到;操:持也又志操七到切又七刀切七|造:至也又昨早切|艁:+古文|慥:言行急|㿷:米穀雜|糙:+上同|鄵:鄭地名
CkC薄報;暴:侵暴猝也急也又晞也案說文作曓疾有所趣也又作㬥晞也今通作暴亦姓漢有繡衣使者暴勝之薄報切九|虣:+上同周禮曰以刑教中則民不虣|曝:曝乾俗|瀑:瀑雨|勽:說文覆也|菢:鳥伏卵|袍:衣前襟又云今朝服垂衣又薄高切|𤔣:姓也出姓苑|𪇰:鳥名又博木切
AkC博耗（秏）;報:報告下婬曰報博耗切一
PkS在到;漕:水運穀在到切二|𢲵:手攪也
hkS烏到;奧:深也內也主也藏也爾雅曰西南隅謂之奧烏到切十一|懊:懊悔|䐿:藏肉埤蒼云鳥胃也|𩟇:妬食|隩:說文曰水隈崖也|燠:燠釜以水添釜|䜒:語也|镺:長也|墺:四墺四方土又於六切|𩼈:小鰌名|澳:澳深又水名
QkS蘇到;喿:羣鳥聲蘇到切九|譟:羣呼|噪:+上同|瘙:疥瘙|㿋:+上同|髞:髝髞|埽:埽灑說文棄也又桑道切|掃:+上同|𢤁:情性疎皃
ekS苦到;𩝝:餉軍苦到切五|犒:+上同|稾:槀飫書篇名|靠:相違也|䯪:䯪䫨大頭
NkS則到;竈:淮南子曰炎帝作火死而爲竈則到切三|躁:動也|趮:疾也
ikS呼到;秏:減也亦稻屬呂氏春秋云飯之美者南海之秏又姓出何氏姓苑俗作耗呼到切四|好:愛好亦璧孔也見周禮又姓出纂文又呼老切|𡚽:姓也或作𡥆|藃:藃縮也
HkS那到;腝:臂節那到切三|𨱵:長皃|腦:優皮也
#箇
dlS古賀;箇:箇數又枚也凡也古賀切三|个:明堂四面偏室曰左个也|個:偏也
jlS胡箇;賀:慶也擔也勞也加也亦姓出會稽河南二望本齊之公族慶封之後漢侍中慶純避安帝諱改爲賀氏又虜複姓九氏北俗謂忠貞爲賀若魏孝文以其先祖有忠貞之稱遂以賀若爲氏周書賀蘭祥傳曰其先與魏俱起有紇伏者爲賀蘭莫何弗因以爲氏賀拔勝傳云其先與魏俱出陰山代爲酋長北方謂土爲拔爲其摠有地土時人相賀因爲賀拔氏後自武川徙居河南也南燕錄有輔國大將軍賀賴盧後魏書有賀葛賀婁賀兒賀遂賀悅等氏胡箇切四|𧝂:䘸袖也|袔:+上同|㵑:水名
NlS則箇;佐:助也則箇切六|左:左右又作可切|𠡃:副也|㝾:行不正也|袏:襌衣|作:造也本臧洛切
ElS丁佐;跢:小兒行也丁佐切四|癉:勞也|痑:病也|哆:語助聲
IlS郎佐;邏:游兵也郎佐切三|𧟌:婦人衣|㿚:病也
elS口箇;坷:坎坷不平也口箇切四|軻:轗軻不遇也孟子居貧轗軻故名軻字子居又苦哥切|蚵:爾雅商蚵蟲一名蛶又胡哥切|艐:船著沙不行也
glS五个;餓:不飽也五个切一
GlS唐佐;䭾〈馱〉:負馱唐佐切二|大:又唐蓋切
HlS奴箇;奈:奈何奴箇切又奴帶切二|那:語助又奴哥切
QlS蘇箇;些:楚語辝蘇箇切又音細一
ilS呼箇;呵:噓氣呼箇切又呼哥切二|㰤:㰤㰤大笑
FlS吐邏;拖:牽車吐邏切一
#過
dli古臥;過:誤也越也責也度也古臥切七|裹:包也又音果|鐹:鎌也亦作划|划:+上同|𧒖:蟷蠰也即螗蜋|㳀:水名|𩟂:食也出玉篇
jli胡臥;和:聲相應胡臥切又音禾三|盉:調味|俰:和也
Nli則臥;挫:摧也則臥切三|夎:拜失容又詐也經典作蓌|侳:安也有也
eli苦臥;課:稅也試也第也苦臥切七|堁:堀堁塵起皃|敤:研治|髁:髀骨也|𡱼:+上同|㾧:禿㾧|科:滋生也又音窠
Fli湯臥;唾:說文云口液也湯臥切七|涶:+上同|毻:鳥易毛也|蛻:蛇去皮|嫷:好皃|毤:落毛|𧝍:無袂衣也
AlC補過;播:揚也放也弃也說文種也一曰布也又姓播武殷賢人補過切五|𢿥:+古文|簸:簸揚又布火切|番:獸走|譒:敷也謠也
Oli麤臥;剉:破也麤臥切二|莝:斬草|銼:蜀呼鈷䥈
DlC摸臥;磨:磑也摸臥切又莫采切四|䃺:+上同|塺:塵也|摩:按摩又莫禾切
Hli乃臥;愞:弱也或從需下文同乃臥切又乃亂切四|堧:沙土又而緣如兗二切|稬:秫名|𤲬:城下田又隍池內也
BlC普過;破:破壞又虜三字姓三氏北齊書有破六韓常後魏書有北境賊破六汗拔陵又西方破多羅氏後改爲潘氏普過切二|頗:又普禾切
Pli徂臥;座:牀座徂臥切二|坐:被罪又藏果切
gli吾貨;臥:寢也釋名曰臥化也精氣變化不與覺時同也說文曰休也从人臣取其伏也吾貨切一
OlS千過;諎:諎磨千過切二|𢯽:拭𢯽
ili呼臥;貨:財也蔡氏化清經曰貨者化也變化反易之物故字有化也呼臥切一
Gli徒臥;惰:惰懈也徒臥切四|媠:嬾婦人也|𧝍:無袂衣也|𧱫:猪別名也
CmO符臥;縛:符臥切一
Ili魯過;䇔:痿病也魯過切七|𢺑:擊物之名|䌴:不紃也又不均也|㱻:畜產疫病|𡰠:膝病|摞:理也|𠏢:𠏢弱也
Eli都唾;𣑫:木本都唾切四|㛊:量也|剁:剁斫剉也|挆:落帆
OlS七過;磋:磨磋治象牙七過切一
Qli先臥;䐝:䑁膏也先臥切一
hlS安賀;侉:痛呼也安賀切一
hli烏臥;涴:泥著物也亦作汚烏臥切又烏官切又於阮切一
#禡
DnC莫駕;禡:師旅所止地祭名莫駕切九|榪:牀頭橫木|鬕:婦人結帶|㾺:牛馬病又音慢說文曰目病一曰惡气著身也一曰蝕創|罵:惡言|䣕:縣名在犍爲又音馬|𧪨:多言|䧞:增益又巧也|傌:齊大夫名
dnS古訝;駕:行也乘也說文曰馬在軶中也古訝切十二|稼:稼穡種曰稼斂曰穡|嫁:家也故婦人謂嫁曰歸|瘕:腹病|架:架屋亦作枷禮記曰不同椸枷|𢱈〈椵〉:舉閣|價:價數|假:借也至也易也休假也又古雅切|幏:蠻夷賨布|𢉤:𢉤屋閒也|𦙺:𦙺䐒不密|賈:賈人知善惡
hnS衣嫁;亞:次也就也醜也衣嫁切十|俹:倚俹|𣇩:姓也|㰳:欭㰳驢鳴欭乙利切|稏:𥝧稏稻名|𦜖:𥝧膪肥皃|啞:啞啞鳥聲|婭:爾雅曰兩壻相謂爲亞或作婭|䢝:次第行|襾:覆也覆覈覂賈從此又許下切
inS呼訝;嚇:笑聲呼訝切又呼格切八|罅:孔罅|唬:虎聲|𧫒:誑𧫒|㙤:地名在晉|謑:怒言|煆:赫也熱也乾也|㗿:詬㗿責怒
gnS吾駕;迓:迎也吾駕切六|訝:+嗟訝亦上同|犽:獸名|齖:齰齖不相得也|枒:木名一云車輞合處|砑:碾砑
KnS丑亞;詫:誑也丑亞切三|侘:侘傺失志見楚詞|𧬮:相誤
JnS陟駕;吒:吒歎說文曰噴也叱怒也陟駕切十二|咤:+上同禮記曰無咤食|奼:美女又丁故切|灹:火聲|哆:哆㕦大口|奓:張也開也又陟加切|䐒:䐒䏧相黏也|𢕮:𢕮步立也|膪:𦜖膪肥也|䒲:䒲葿黃芩別名|㓃:祭奠酒爵又丁故切|𨶃:+上同
SnS側駕;詐:僞也側駕切六|溠:周禮職方氏云河南曰豫州其浸波溠春秋傳云楚子除道梁溠|咋:咋語聲|笮:笮酒器也|𨢧〈醡〉:壓酒具也出證俗文|榨:打油具也出證俗文
UnS鋤（鉏）駕;乍:鋤駕切五|䄍:年終祭名或作蜡廣雅曰夏曰清祀殷曰嘉平周曰大䄍秦曰臘也|蜡:+上同|齰:齰齖|𧧻:說文曰慙語也
RoS辝（辭）夜;謝:辝謝又姓出陳郡會稽二望辝夜切三|榭:臺榭爾雅曰有木者謂之榭|㴬:水名
enS枯駕;髂:𦝫骨枯駕切六|𩩱:+上同|疴:小兒驚|𧩶:𧩶詬巧言才也|㰤:大笑|𠳌:歎聲
jnS胡駕;暇:閑也書曰不敢自暇自逸俗作睱胡駕切四|夏:春夏又胡雅切|下:行下又胡雅切|芐:蒲苹草
PoS慈夜;褯:小兒褯慈夜切五|藉:以蘭茅藉地又慈亦切|躤:踐也|䤳:鏡䤳|䣠:亭名在貝丘
loS羊謝;夜:舍也暮也君子有四時朝以聽政晝以訪問夕以修令夜以安身又姓羊謝切三|射:僕射|鵺:鳥名似雉
YoS充夜;䞣:怒也一曰牽也充夜切又丑格切二|斥:山名爾雅曰東北之美者有斥山之文皮焉又音尺
QoS司夜;蝑:鹽藏蟹司夜切又司余切四|卸:卸馬去鞍|瀉:吐瀉又音寫|䉣:笘䉣
XoS之夜;柘:木名亦姓之夜切七|樜:+上同|鷓:鷓鴣鳥似雉南飛|䗪:𧑓蝜蟲名亦作蟅|嗻:多語之皃|炙:炙肉周書曰黃帝始燔肉爲炙又之石切|蔗:甘蔗
NoS子夜;唶:歎聲子夜切二|借:假借又將昔切
aoS始夜;舍:屋也又姓古作舍始夜切五|赦:赦宥|騇:牡馬|涻:文字音義云涻水出北嚻山也|厙:姓也出姓苑今台括有之又昌舍切
boS神夜;射:白矢參連剡注襄尺井儀射白勻參遠剡注讓尺井儀又姓三輔決錄云漢末有大鴻臚射咸本姓謝名服天子以爲將軍出征姓謝名服不祥改之爲射氏名咸神夜切又音石又音夜僕射也四|䠶:+上同見說文|麝:獸名爾雅曰麝父麕足又翠山之陰多麝|貰:貫賒也貸也
AnC必駕;霸:國語曰霸把也把持諸侯之權又姓益部耆舊傳有霸相必駕切七|𧟶:+俗|弝:弓弝|欛:刀柄名|靶:轡革|灞:水名|垻:蜀人謂平川爲垻
BnC普駕;帊:帊幞通俗文曰帛三幅曰帊帊衣幞也普駕切二|怕:怕懼
jni胡化;摦:寬也大也胡化切七|㕦:大口|崋:崋山西嶽亦州名春秋時秦晉之分境後魏置東雍州改爲崋州又姓出平原殷湯之後宋戴公考父食采於其崋後氏焉|華:+上同|樺:木名|鱯:魚名似鮎白大|檴:亦木名又胡郭切
ini呼霸;化:德化變化禮記曰田鼠化爲鴽紀年曰周宣王時馬化爲狐又姓呼霸切六|𠤎:變也從到人|諣:疾言|𩲏:鬼變|𩵏:魚名|杹:木名皮可爲索
eni苦化;跨:越也又兩股閒苦化切三|胯:兩股閒也|㐄:一步也又口瓦切
Vni所化;誜:枉也所化切二|傻:傻偢不仁
CnC白駕;𤝡:獸名似狼白駕切六|杷:田器又白巴切|𩹏:海魚|𦫙:色不真也|跁:跁踦短人|𥝧:𥝧稏稻名
MnS乃亞;䏧:膩也乃亞切二|絮:絲結亂也
OoS遷謝;笡:斜逆也遷謝切二|䞣:䞣脚立也
VnS所嫁;嗄:老子曰終日號而不嗄注云聲不變也所嫁切又於介切三|𦔯:姓也|沙:周禮云鳥皫色而沙鳴注云沙嘶也又所加切
dni古罵;坬:土埵古罵切二|𧬮:相𧬮誤也
LnS除駕;䖳:水母也一名蟦形如羊胃無目以蝦爲目除駕切二|䅊:開張屋皃
gni五化;瓦:泥瓦屋五化切一
hni烏㕦;攨:吳人云牽亦爲攨也烏㕦切三|窊:𢈈下處也|䠚:䠚蹃踏地用力
#漾
lpS餘亮;漾:水名在隴西餘亮切十二|恙:憂也病也又噬蟲善食人心也|羕:長大也|颺:風飛|煬:炙也向也暴也|㨾:式㨾|養:供養|眻:美目兒|諹:謹也讙也|䭐:餌也|㺊:㺊獸如師子食虎豹及人|瀁:水溢蕩皃
IpS力讓;亮:朗也導也亦姓出姓苑力讓切十五|諒:信也相也佐也又姓後漢有諒輔|掠:笞也奪也取也治也|悢:悢悢悲也|緉:履屐雙也|㹁:牛色雜也|兩:車數|踉:踉蹡行不迅也|量:合斗斛|𣄴:字統云事有不善曰𣄴薄|𩗬:北風又音涼|䁁:目病|䀶:+上同|哴:唴哴啼也|涼:薄也又呂張切
UpS鋤（鉏）亮;狀:形狀鋤亮切一
cpS人㨾;讓:退讓責讓又交讓木名兩樹相對一枯則一生岷山有之人㨾切四|欀:道木|攘:文字指歸云揖攘又音穰|懹:憚也
apS式亮;餉:餉饋式亮切十|傷:未成人死或作殤又音商|向:人姓出河內本自有殷宋文公支子向文旰旰孫戍以王父字爲氏又許亮切|蟓:桑繭即桑蠶也|曏:少時也不久也|慯:憂也|𤵼:+上同|饟:爾雅曰饁饟饋也又自家之野曰饟|蠰:食桑蟲似天牛|珦:玉名
JpS知亮;帳:帷帳釋名曰小帳曰斗帳形如覆斗也漢書曰東方朔云陛下誠能用臣朔之計推甲乙之帳知亮切五|脹:脹滿|痮:+上同|漲:大水又陟良切|張:張施又陟良切
KpS丑亮;悵:失志丑亮切十|暢:通暢又達也亦姓陳留風俗傳曰暢氏出齊|鬯:匕鬯又香草|韔:弓衣|䩨:+上同|𧀄:草盛|昶:達也日長也通也遠也又丑兩切|畼:不生也|𥠴:穧也|𥇔:失志
ipe許亮;向:對也窻也說文曰北出牖也从宀口詩云塞向墐戶許亮切八|珦:玉名又音餉|曏:又音餉|䦳:門頭也說文曰門響也|蠁:蛹中蟲也又許兩切|萫:萫芼食|𧬰:非美言也|嚮:與向通用
LpS直亮;仗:器仗也又持也直亮切三|長:多也又直良切|瓺:瓶也又音腸
MpS女亮;釀:醞酒女亮切三|𥽬:雜也|䖆:菜也又如養切
PpS疾亮;匠:工匠漢書曰將作少府秦官掌理宮室又姓風俗通云凡氏於事巫卜陶匠是也疾亮切三|䞪:行皃|𪀘:自關以東謂桑飛爲女𪀘郭璞云工雀今謂之巧婦也
XpS之亮;障:界也隔也又步障也王君夫作絲巾步障三十里石崇作錦障五十里以敵之之亮切五|㢓:+上同|墇:墇塞|嶂:峯嶂|瘴:熱病
ZpS時亮;尚:庶幾亦高尚又飾也曾也加也佐也韻略云凡主天子之物皆曰尚尚醫尚食等是也又姓後漢高士尚子平又漢複姓有尚方氏時亮切四|上:君也猶天子也又時兩切|丄:+古文|償:備也還也又音常
SpS側亮;壯:大也側亮切三|裝:行裝又側良切|𣴣:𣴣米入甑
hpe於亮;怏:情不足也於亮切四|䬬:飽也|詇:智也又早知也|㿮:青面
fpe其亮;弶:張取獸也其亮切又魚兩切一
YpS尺亮;唱:發歌又導也亦作誯倡尺亮切四|𪛋:+籀文|廠:露舍|倡:導引先又音昌
TpS初亮;刱:初也說文曰造法刱業也初亮切四|創:+上同又初良切|愴:悽愴|滄〈凔〉:寒也
NpS于〈子〉亮;醬:說文作酱醢也漢書武帝使唐蒙風曉南越南越食蒙蜀蒟醬于亮切四|𨡰:+籀文|𨟻:+古文|將:將帥
gpe魚向;𨋕:轎𨋕魚向切二|仰:又魚兩切
BpO敷亮;訪:謀也敷亮切三|妨:妨礙又敷方切|邡:邑名
DpO巫放;妄:虛妄又亂也誣也巫放切六|望:看望說文曰出亡在外望其還也亦祭名又姓何氏姓苑云魏興人又音亡|朢:弦朢說文曰月滿與日相望似朝君也又音亡|忘:遺忘又音亡|汒:谷名在京兆也|𧫢:責也
ipu許訪;況:匹擬也善也矧也說文曰寒水也亦脩況琴名又姓何氏姓苑云今廬江人許訪切四|况:+俗|𣍦:山名|貺:賜也與也
dpu居況;誑:欺也居況切四|㤮:㤮惑也|𠉫〈俇〉:往也又遠行也|臦:乖也
kpu于放;迋:往也勞也于放切五|旺:美光|暀:+上同|㤮:誤人|王:霸王又盛也又于方切
ApO甫妄;放:逐也去也甫妄切四|舫:並兩船又音謗|趽:曲脛馬名|𨾔:鳥名
QpS息亮;相:視也助也扶也仲虺爲湯左相漢書曰相國丞相皆秦官金印紫綬掌丞天子助理万物亦州名春秋時屬晉秦邯鄲郡地魏初以東部爲陽平郡西部爲廣平郡兼魏王都爲三魏後魏置相州取河亶甲居相之義周自故鄴移於安陽城也又姓後秦錄有馮翊相雲作德獵賦又漢複姓三氏前趙錄有偏將軍相里覽又務相氏廩君之姓也晉惠時空相機殺平南將軍孟觀息亮切又息良切一
dpe居亮;彊〈殭〉:屍勁硬也居亮切一
epe丘亮;唴:唴哴小兒啼也丘亮切三|𥇉:䁁𥇉目病|羻:陳桓子名
OpS七亮;蹡:踉蹡行不正皃七亮切一
fpu渠放;狂:輒爲也渠放切二|誆:謬言
CpO符況;防:守禦也符況切一
#宕
GqS徒浪;宕:洞室一曰過也亦州名禹貢梁州之域秦漢魏晉諸羌處之後魏內附置蕃鎮周爲宕州也徒浪切七|踼:跌踼行失正又音唐|碭:石又山名又縣名在梁郡又音唐|逿:過也|𦿆:䕞𦿆毒藥|𡇈:碎石聲|嵣:嵣㟐山皃
IqS來宕;浪:波浪謔浪游浪又姓晉永嘉末張平保青州爲其下浪逢所殺來宕切又魯當切五|閬:高門又閬中地名在蜀又閬風崑崙峯名也|埌:冢也|䕞:䕞𦿆|蒗:蒗蕩渠名在譙
jqS下浪;吭:鳥咽下浪切三|行:次第|笐:衣架
hqS烏浪;盎:盆也又姓出姓苑烏浪切二|醠:濁酒
gqS五浪;枊:繫馬柱五浪切三|䭹:馬怒又五郎五朗二切|𡵙:山名在越剡縣界
NqS則浪;葬:葬藏也則浪切一
CqC蒲浪;傍:蒲浪切又蒲郎切二|徬:徬附
PqS徂浪;藏:通俗文曰庫藏曰帑徂浪切又徂郎切三|奘:說文曰駔大也|𨌄:修車
EqS丁浪;譡:言中理丁浪切六|儅:不中|瓽:大甕一曰井甃說文云大盆也又姓姚弋仲將瓽耐虎|當:主當又底也亦音蟷|擋:摒擋|闣:閃闣人
eqS苦浪;抗:以手抗舉也縣也振也苦浪切十二|閌:閌閬門高|炕:火炕|犺:猰犺不順|伉:伉儷敵也又姓漢有伉喜爲漢中太守出風俗通|亢:高也旱也亦姓出姓苑|蚢:蟲名爾雅云蚢蕭繭|砊:砊硠石聲|邟:邑名|𪎵:黃色|阬:門也又口庚切|頏:咽頏
AqC補曠;螃:蟲名似蝦蟆補曠切四|搒:棹船一歇|舫:舫人習水者也|謗:誹謗
FqS他浪;儻:倖也他浪切六|摥:排摥|湯:熱湯也又他郎切|蕩:蒗蕩渠又土郎徒朗二切|盪:盪行又度朗切|𨫖〈鐋〉:工人治木器
eqi苦謗;曠:空明也遠也大也久也又姓苦謗切五|爌:+上同|矌:目無䀕也|壙:墓宂|纊:絮也又細緜也禹貢豫州厥貢厥篚纖纊又作絖
HqS奴浪;儾:緩也奴浪切三|灢:泱灢濁|㚂:坱㚂塵
QqS蘇浪;喪:亡也蘇浪切又音桑二|𠸶:+上同
jqi乎曠;攩:廣雅云搥打也乎曠切四|擴:+上同|潢:釋名曰染書也又音黃|暀:暀明
dqi古曠;桄:織機桄古曠切又古黃切二|光:上色又古黃切
dqS古浪;鋼:古浪切又古郎切二|掆:捎掆舁也出字林
iqi呼浪;荒:草多皃呼浪切一
DqC莫浪;漭:漭浪大野莫浪切三|吂:老人不知|㟐:嵣㟐山皃
hqi烏浪;汪:水臭也烏浪切二|䤑:潑䤑酒
#映
hsa於敬;映:明也隱也於敬切四|暎:+上同|賏:頸飾|詇:早知也又音怏
dsa居慶;敬:恭也肅也慎也又姓陳敬仲之後出平陽風俗通後漢有揚州刺史敬歆居慶切四|竟:窮也終也又姓出何氏姓苑|鏡:拾遺錄曰穆王時渠國貢火齊鏡廣三尺六寸暗中視如晝人向鏡語則鏡中響應之晉鎮南大將軍甘卓照鏡不覩其頭視庭樹而頭在樹上|獍:獸名食人
fsa渠敬;競:爭也強也逐也高也遽也渠敬切七|𥪰:+俗|誩:爭言|倞:強也|檠:檠子曡名|儆:儆慎又音警|曔:明也
esa丘敬;慶:賀也福也亦州名周之先不窋之所居春秋爲義渠戎國城本漢郁郅縣魏文置朔州隋爲慶州州立嘉名也亦姓左傳齊大夫慶封又漢複姓有慶師慶忌慶父三氏出姓苑丘敬切一
drS古孟;更:易也改也說文作㪅古孟切又古衡切一
DsK眉病;命:使也教也道也信也計也召也眉病切一
CsK皮命;病:憂也苦也說文曰疾加也皮命切四|評:平言又音平|坪:地名說文作坪地平也|枰:獨坐版牀一曰投博局又音平
DrC莫更;孟:長也勉也始也又姓出平昌武威二望本自周公魯桓公之子仲孫之胤仲孫爲三桓之孟故曰孟氏莫更切四|䁅:䁅盯瞋目|朚:朚倀失道皃又音忙倀猪孟切|盟:盟津又音明
jri戶孟;蝗:蟲名戶孟切又音皇三|㶇:說文曰小津也一曰以船渡也|橫:非理來又音宏
AsK陂病;柄:本也權也柯也陂病切六|棅:+說文同上|怲:憂心也|邴:邑名又姓左傳魯大夫邴洩|鈵:堅鈵|寎:驚病
ksq爲命;詠:歌也爲命切五|咏:+上同|泳:潛行水中|禜:祭名周禮禜門用瓢齎又永兵切|醟:酗酒
jrS下更;行:景迹又事也言也下更切又胡郎胡浪胡庚三切三|絎:刺縫|胻:脛也
hrS於孟;瀴:瀴㵾冷也於孟切一
TsS楚敬;㵾:冷也楚敬切一
JrS猪（豬）孟;倀:朚倀失道猪孟切又丑良切五|趟:䞴趟行皃|偵:廉視|㡧:開張畫繒也出文字指歸|𩏠:張皮也
KrS他孟;牚:邪柱也他孟切一
ArC北孟;榜:榜人船人也北孟切三|𧻓:走也|跰:史記云歲星晨出爲跰踵
LrS除更;鋥:磨鋥出劒光或作䂻除更切三|𥊼:住視|䂻:塞也
VsS所敬;生:所敬切又所京切三|鼪:鼬鼠|貹:財富
gsa魚敬;迎:迓也魚敬切一
CrC蒲孟;膨:脹也蒲孟切一
irS許更;𧨫〈䛭〉:瞋語許更切一
hri烏橫;𥥈:小水皃烏橫切一
#諍
StS側迸;諍:諫諍也止也亦作爭側迸切一
AtC北諍;迸:散也北諍切一
CtC蒲迸;𠊧:皆也俱也蒲迸切一|䨻:雷䨻䨻聲
htS鷖迸;䙬:文字集略云襇錯綵郭璞江賦云䙬以蘭紅鷖迸切二|嫈:小心態
gtS五爭;鞕:堅牢五爭切二|硬:+上同
iti呼迸;轟:眾車聲也呼迸切又呼宏切二|輷:+上同
#勁
duW居正;勁:勁健也居正切一
OuS七政;倩:假倩也七政切又七見切二|凊:溫凊
XuS之盛;政:政化釋名曰政正也下所取正也亦姓出姓苑之盛切四|正:正當也長也定也平也是也君也亦姓左傳宋上卿正考父之後魏志有永昌太守正帛又漢複姓漢有郎中正令宮又之盈切|証:諫証|鴊:雞也又之盈切
auS式正;聖:生也通也聲也風俗通云聖者聲也言聞聲知情故曰聖式正切一
LuS直正;鄭:鄭重慇懃亦州名秦屬三川郡史記管叔鮮之所封也宋武置司州於武牢皆魏爲北豫州周爲滎州隋罷滎州於管城置鄭州又姓滎陽彭城安陸壽春東陽五望本自周宣王封母弟友於鄭及韓滅鄭子孫以國爲氏今之望多滎陽直正切三|呈:自媒衒又音程|㽀:甖也
KuS丑鄭;遉:邏候也丑鄭切三|偵:偵問|靗〈𩇜〉:覗也
QuS息正;性:性行也息正切二|姓:姓氏說文云姓人所生也古之神聖母感天而生子故稱天子从女生聲又姓漢書貨殖傳臨菑姓偉貲五千万
IuS力政;令:善也命也律也法也力政切又力盈切又歷丁切二|詅:自街賣也
BuG匹正;聘:聘問也訪也匹正切三|娉:娶也|俜:伶俜
ium休正;敻:遠也休正切四|詗:自言長|醟:酗酒又爲命切|矎:直視皃
AuG畀政;摒:摒除也畀政切三|併:兼也並也皆也|并:專也
CuG防正;偋:偋隱僻也無人處字統云廁也防正切又蒲徑切二|庰:+上同
PuS疾政;淨:無垢也疾政切八|㵾:+古文|穽:陷穽又音靜|䝼:䝼賜|靚:裝飾也古奉朝請亦作此字|請:延請亦朝請漢官名張禹首爲之又秦盈親井二切|婧:竦立|𩓞:𩓞首說文好皃
ZuS承正;盛:多也長也又姓後漢西羌傳有北地太守盛苞其先姓奭避元帝諱改姓盛承正切又音成三|墭:塸器|晟:明也熾也器也
DuG彌正;詺:詺目或單作名彌正切一
euW墟正;輕:墟正切又去盈切一
i2Q許｟火｠令〈含〉|iuW許令;𣢝〈欦〉:a含笑也許令切二|𩈡:b面𩈉𩈡也
NuS子姓;精:強也子姓切又音旌一
#徑
dvS古定;徑:步道古定切七|經:經緯又古靈切|逕:近也|𠲮:猿聲|俓:直也|𩰹:隔也|桱:桱木似杉而硬
HvS乃定;甯:邑名亦姓說文作甯所願也乃定切四|佞:諂也一曰才也俗作侫|濘:泥濘|鸋:爾雅鸋鴂鴟屬也楚詞云鸋鴞之鳴
QvS蘇佞;腥:豕息肉肉中似米蘇佞切又音星三|醒:酒醒又蘇丁先頂二切|睲:目睲
jvS胡定;脛:腳脛釋名曰脛莖也直而長似物莖也胡定切二|踁:+上同
GvS徒徑;定:安也亦州名帝堯始封唐國之城秦爲趙郡鉅鹿二郡漢爲中山郡後魏置安州又改爲定州以安定天下爲名徒徑切四|掟:天掟出道書|廷:朝廷又音亭|錠:錫屬
EvS丁定;矴:矴石丁定切九|釘:又得庭切|訂:字林云逗遛也|定:題額詩云定之方中定營室也又徒徑切|飣:貯食|奠:+上同|𦘭:亦同|顁:題顁|錠:豆有足曰錠無足曰鐙
evS苦定;罄:盡也說文曰器中空也苦定切七|𥥻:說文空也|磬:磬石樂器周禮曰磬人爲磬|殸:+籀文|𪊑:爾雅云鹿絕有力又堅牽二音|𨆪:一足行|鑋:金聲
FvS他定;聽:待也聆也謀也他定切又音廳三|汀:汀瀅不遂志又音廳|侹:俓侹直也代也儆也
OvS千定;靘:䒌靘青黑千定切二|掅:捽也
DvC莫定;䒌:莫定切二|暝:夕也
hvi烏定;鎣:鎣飾也烏定切四|瑩:+上同說文曰玉色一曰石之次玉者|𢣙:志恨也|瀅:小水
IvS郎定;零:零落郎定切又魯丁切三|𢺰:插空皃又魯丁切|令:令支縣在遼西郡
#證
XwS諸應;證:驗也諸應切二|烝:熱又音蒸
lwS以證;孕:懷孕以證切七|䵴:面黑子|賸:增益一曰送也又物相贈|媵:送女從嫁|㑞:㑞送行也|鱦:小魚|膡:大視又雙也
bwS實證;乘:車乘也實證切又食陵切七|鱦:魚子|媵:又音孕|𣎜:孕也|嵊:山名在剡縣也|賸:又音孕|剩:剩長也
cwS而證;認:認物而證切又而振切四|扔:強牽引又音仍|芿:草不翦|㭁:上車又木名
hwe於證;應:物相應也說文作應當也於證切又音膺三|譍:以言對也|噟:+上同
NwS子孕;甑:古史考曰黃帝始作甑子孕切四|䰝:+上同|𩱭:+籀文|䙢:汗襦
iwe許應;興:許應切又許陵切三|臖:腫起|嬹:悅也喜也
awS詩證;勝:勝負又加也克也亦州名春秋時戎狄地戰國時晉趙地漢雲中五原也隋置榆林鎮屬雲州唐武德中改爲勝州詩證切又詩陵切四|膡:美目|蕂:苣蕂胡麻|榺:織機榺也
LwS丈證;瞪:直視皃陸本作眙丈證切三|𪒘:米黑壞|𪑬:雲色
IwS里甑;𩜁:馬食穀多氣流四下也里甑切一
CwK皮證;凭:依几也皮證切又皮陵切二|靐:靐靐雷聲也
YwS昌孕;稱:愜意又是也等也銓也度也俗作秤云正斤兩也昌孕切又昌陵切二|秤:+俗
gwe牛𩜁;凝:牛𩜁切又牛凌切一
ZwS常證;丞:縣名在沂州匡衡所居常證切又音承一
KwS丑證;覴:直視丑證切一
fwe其𩜁;殑:釋典殑伽其𩜁切又其陵切一
#嶝
ExS都鄧;嶝:小坂都鄧切八|鐙:鞍鐙|隥:梯隥|橙:几橙|凳:牀凳出字林|𧄼:𧄼𧀧|𩞬:祭食|磴:巖磴
PxS昨亙;贈:玩也好也相送也昨亙切二|𪒟:皯𪒟
dxS古鄧;亙:通也遍也竟也出方言古鄧切六|堩:路|揯:急引又古登切|緪:急張亦作絚|䱍:魚名|𥔂:石連皃
OxS千鄧;蹭:蹭蹬千鄧切二|𠟂:刀割過也
GxS徒亙;鄧:國名周爲申國平王母申后之家戰國時地楚昭襄王取韓置南陽郡釋名曰在中國之南而居陽地故以爲名始皇三十六郡即其一焉隋以南陽爲縣改爲鄧州取鄧國名之又姓出南陽安定二望殷王武丁封叔父於河北是爲鄧侯後因氏焉徒亙切六|蹬:蹭蹬|僜:倰僜不著事|𣩟:㱥𣩟困病|䮴:行欲倒也|幐:囊屬
DxC武亙;𢅴〈懵〉:悶也武亙切五|䲛:魚名|懜:不明|𨮒:重鐶|𧀧:𧀧𧄼新睡起
AxC方隥;𥦜:束棺下之說文作堋喪葬下土也方隥切二|堋:+上同又壅江水灌溉曰堋
CxC父鄧;倗:輔也父鄧切一
IxS魯鄧;踜:踜蹬行皃魯鄧切二|㱥:㱥𣩟
NxS子鄧;增:剩也子鄧切一
QxS思贈;𡬙:𡬙𧀧睡覺思贈切一
FxS台鄧;𤃶:小水相益台鄧切一
#宥
kyO于救;宥:寬也于救切十六|又:又猶更也|佑:佐也助也|右:左右又于久切|祐:神助|䀁:抒水器也|𥁓:+上同|酭:報也|𩑣:說文顫也|𤴨:+上同|囿:說文曰苑有垣一曰禽獸不囿又于目切|姷:偶也|忧:動曰也|䞥:走皃|侑:勸食爾雅曰酬酢侑報也|𦳩:草名
dyO居祐;救:護也止也又姓風俗通漢有諫議大夫救仁居祐切十一|灸:灼也又居有切|廏:馬舍釋名曰廏聚也生馬之所聚也又灸廏並姓出姓苑俗作廏|究:窮也深也謀也盡也|㝌:說文云貧病也|疚:病也|𣪘:強擊|匓:說文飽也|𧧷:文字音義云止也禁也助也|猶:爾雅云猶如麂善登木又音由音柚|𨖏:恭謹行也
LyC直祐;胄:胄子國子也說文曰裔也又姓出姓苑直祐切十三|冑:介冑說文曰兜鍪也|𩊄:+古文|酎:三重釀酒|宙:宇宙|繇:卦兆辝也|籀:史籀周宣王太史名造大篆|伷:系也|䛆:詶也|疛:心腹疾也|㿒:+上同|駎:競馳馬也|懤:愁毒
JyC陟救;晝:日中又姓晝邑大夫之後因氏焉出風俗通陟救切三|咮:鳥口又鬬卓二音|噣:+上同
ayC舒救;狩:冬獵舒救切五|獸:說文曰守備者周禮曰獸人掌罟田獸辨其物名字林曰兩足曰禽四足曰獸|守:太守|首:自首前罪|收:穫多
YyC尺救;臭:凡氣之摠名俗作臰尺救切二|殠:腐臭
RyC似祐;岫:山有穴曰岫似祐切四|𥥉:+籀文|袖:衣袂也亦作褏褎|牰:牛黑眥
iyO許救;齅:以鼻取氣亦作嗅許救切三|嘼:嘼㹌亦作畜|珛:朽玉
XyC職救;呪:呪詛職救切四|䯾:髮多|椆:木椆船篙木也|祝:說文曰祭主贊詞又音粥
fyO巨救;舊:故也亦姓出姓苑巨救切三|柩:尸曲禮注曰在牀曰尸在棺曰柩|匶:+古文
VyC所祐;𤸃:𤸃損說文臞也所祐切四|瘦:+上同|漱:漱口|鏉:鐵鉎鏉
SyC側救;皺:面皺俗作𤿥側救切五|㾭:縮小|甃:井甃|縐:衣不申又絺之細者|䐢:字書云䐢脯也
ByO敷救;副:貳也佐也又虜姓後魏書副呂氏後改爲副氏敷救切七|仆:前倒|𩯅:假髻又敷六切|覆:蓋也又敷六切|𤸑:病重發也|㤱:小怒也|褔:衣一福今作副
TyC初救;簉:簉倅一曰齊也初救切三|䔏:+上同又草根|遚:不進
AyO方副;富:豐於財又姓左傳周大夫富辰方副切四|輻:輻湊競聚又音福|鍑:釜而大口一曰小釜|䔰:爾雅云䔰葍大葉白華根如指白可食詩云言采其葍葍音福
KyC丑救;畜:六畜丑救切又許宥許六丑六三切二|俞:姓漢有司徒椽俞連又羊朱切
IyC力救;溜:水溜力救切十九|廖:姓周文王子伯廖之後後漢有廖湛|霤:中霤神名|嬼:美好|鷚:雞子一曰鳥子|餾:餾飯|瘤:赤瘤腫病也出文字集略|窌:地名左傳云與之石窌之田|留:宿留停待也宿音秀|㙀:壣土曰㙀|僇:癡行皃|廇:屋梁杗也|畂:百畝|𥛅:留祀祝𥛅|飂:高風又古國在南陽湘陽|勠:併力又力竹切|翏:高飛皃又力幺切|塯:瓦飯器也|㽌:檼也又力回切
QyC息救;秀:出也榮也息救切五|繡:五色備也尚書大傳曰未命爲士不得衣繡又姓漢書游俠傳有馬領繡君賓|蜏:蟲名|琇:玉名|宿:星宿亦宿留又音夙
NyC即就;僦:僦賃即就切三|䅢:稻稔實又稅也|媨:醜老嫗皃
UyC鋤（鉏）祐;驟:馬疾步也奔也鋤祐切三|㑳:妊身人也|僽:僝僽惡言罵也
PyC疾僦;就:成也迎也即也說文曰就高也从京尢尤異於凡也又姓後魏書菟賴氏後改爲就氏疾僦切四|鷲:鳥名黑色多子|殧:殧殄又子六切|㠇:山名又嶺名
MyC女救;糅:雜也女救切五|𩚖:雜飯亦作粈|腬:嘉膳|猱:爾雅曰猱蝯善援又奴刀切|狃:習也就也又狐狸也
CyO扶富;復:又也返也往來也安也白也告也扶富切又音服八|𢕒:+古文|𤸑:再病|伏:鳥菢子又音服|椱:機持繒者|𨺅:兩阜閒也|覆:伏兵曰覆|複:重複
lyC余救;狖:獸名似猨余救切十四|貁:+上同|鼬:蟲名似鼠|槱:積薪燒之|柚:似橘而大廣志曰成都柚大如斗爾雅注柚似橙而醋酢出江南|蜼:似獼猴鼻露向上尾長四五尺有歧雨則自縣於樹以尾塞鼻又以季切|褎:服飾盛皃|油:雚子桐花曰油|猶:獸似麂善登|𪕏:𪕏鼠|櫾:木名|輶:輶車又音由|牰:牛黑眥|蜏:不知晦朔又音酉
ZyC承呪;授:付也又姓出何氏姓苑承呪切六|詶:荅也又市州切|㖟:口㖟|壽:壽考|售:賣物出手|綬:綵衣皃
cyC人又;輮:車輞人又切四|蹂:蹂踐|煣:蒸木使曲也|鞣:柔皮又音柔
DyO亡救;莓:覆盆草也亡救切一
gyO牛救;鼼:仰鼻牛救切一
eyO丘救;𪖛:𪖛鼼仰鼻丘救切一
OSg七溜｟霤｠〈雷〉;䞭:進也七溜切一
#候
jzC胡遘;候:伺候又姓周禮有候人其後氏焉胡遘切十五|鮜:魚名|鄇:地名在晉|逅:邂逅|訽:罵訽|睺:半盲|后:君也皇后也|後:方言云先後猶娣姒|堠:今封堠也|鱟:郭璞注山海經云冠青黑色形如惠文二足長五六尺似蟹雌常負雄漁者取之必得其雙子如麻子南人爲醬|鍭:爾雅曰金鏃翦羽|厚:厚薄|䞧:蹇行又蒲北切|䞀:䞀𧷡貪財之皃|𣣠〈𥀃〉:石蜜膜也
ezC苦候;寇:鈔也暴也又姓出馮翊河南二望陳留風俗傳云浚儀有寇氏黃帝之後風俗通云蘇忿生爲武王司寇後以官爲氏苦候切十|滱:水名在代郡|怐:怐愗愚皃|扣:扣擊|鷇:鳥子亦作㲉生而須哺曰鷇自食曰鶵|㜌:㜌瞀無暇|䍍:說文曰未燒瓦器也|簆:織具|瞉:瞉瞀|詬:罵又巧言
DzC莫候;茂:卉木盛也古作懋莫候切十五|貿:交易也市賣也又姓出姓苑東莞人|鄮:縣名在會稽亦姓出姓苑|戊:辰名|愗:怐愗|袤:廣袤東西曰廣南北曰袤|楙:爾雅曰楙木瓜實如小瓜味酢可食|懋:美也勉也|瞀:瞉瞀|䓮:細草叢生|姆:女師說文作娒|苺:苺子即覆盆|𦼪:草名|𠔼:重覆又亡保切|雺:天氣下地不應
BzC匹候;仆:倒也匹候切又匐覆二音五|踣:+上同|䞳:僵也|㰴:語而不受|豧:豕息
GzC［徒］候;豆:穀豆物理論云菽者眾豆之名也又姓後魏有將軍豆代田候切十六|竇:空也穴也水竇也又姓出扶風觀津河南三望風俗通云夏帝相遭有窮氏之難其妃方娠逃出自竇而生少康其後氏焉|窬:禮曰蓽門圭窬又音俞|逗:逗遛又住也止也|酘:酘酒|荳:荳蔻|脰:項脰|郖:地名|梪:籩豆或作豆古食肉器也|餖:飣餖|浢:水名|䄈:祭福|毭:𣯻罽|𩊪:車鞁具|𤀨:水名|㛒:嫗㛒語帖也
EzC都豆;鬥:說文曰兩士相對兵杖在後象鬥之形凡從鬥者今與門戶字同都豆切九|𨷖〈鬬〉:鬬競說文遇也又姓左傳楚有大夫鬬伯比|鬪:+俗|噣:鳥口或作咮又丁救切|䛠:䛠譳不能言也|𧱓〈𧱦〉:𧱦尾張衡東京賦云日月會於龍𧱦|斣:斠也角力走也又相易物俱等|襡:衣袖又時燭切|䬦:䬦飣
HzC奴豆;槈:說文曰薅器也纂文曰耨如鏟柄長三尺刃廣二寸以刺地除草奴豆切六|鎒:+上同亦出說文|耨:+上同五經文字云經典相承從耒久故不可改|𣫌:乳也|擩:搆擩不解事|譳:䛠譳
QzC蘇奏;瘶:欬瘶蘇奏切七|嗽:+上同|欶:上氣|漱:漱口又音瘦|鏉:𨫒利|謏:諵謏怒言也|嗾:使狗
NzC則候;奏:進也說文作𡴝則候切二|走:釋名曰疾趨曰走又祖苟切
FzC他候;透:跳也他候切又書育切五|咅:說文作㕻相與語唾而不受也隷變如上|㰯:+說文同上俗又作哣|䟝:索彄䟝也|𧺢:目投下或作𣪌
hzC烏候;漚:久漬也烏候切三|䙔:頭衣|𠹝:地名又市由切
dzC古候;遘:遇也古候切二十|構:架也合也成也蓋也亂也|媾:重婚|覯:見也|姤:卦名姤遇也又偶也|購:購贖|䝭:稟給|雊:雉鳴|彀:張弓|𤚼:取牛羊乳亦作𦎯|句:句當又姓華陽國志云王平句扶張翼廖化並爲大將軍時人曰前有王句後有張廖俗作勾|軥:軥槅挽車也|㝤:夜也|搆:搆擩也|怐:怐愗愚皃又苦候切|煹:舉火也|䃓:甃井也又罰也|冓:數也|㝅:說文曰乳也一曰㝅瞀也|𢄇:綿𢄇
OzC倉奏;輳:輻輳亦作湊倉奏切八|腠:膚腠|湊:水會也聚也|嗾:使犬|𪉮:南夷名鹽|蔟:太蔟律名又倉谷切|楱:橘屬|𧱪:溫豕
IzC盧候;陋:疎惡也說文曰阸陝也盧候切十三|漏:漏刻說文曰漏以銅受水刻節晝夜百刻爾雅曰西北隅謂之屋漏又禹耳三漏|鏤:彫鏤書傳云鏤剛鐵也又鏤漏並姓出何氏姓苑又力誅切|屚:說文曰屋穿水下也从雨在尸下尸屋也一曰笱屚縣名在交阯|瘻:瘡也|𦸢:𦸢蘆|𧷡:䞀𧷡貪財|𨫒:鏉𨫒|蔄:姓也|𣤋:𣤋㰯小兒兇惡|𧫞:𧫞詬忽怒|𠞭:𠞭㔌細切|僂:僂佝短醜皃
izC呼漏;蔻:荳蔻呼漏切十|豞:豕聲|䪷:字統云勤作|詬:怒也|訽:+上同|吼:聲也又呼後切|㰯:𣤋㰯|㖃:恥辱|佝:僂佝|怐:+上同
CzC蒲候;䏽:豕肉醬也蒲候切二|𩌏:尻衣
gzC五遘;偶:不期也五遘切一
PzC才奏;㔌:細切才奏切三|楱:𨫒楱鐵齒杷名|䠫:醉倒皃出埤蒼
#幼
h0W伊謬;幼:少也伊謬切一
D0K靡幼;謬:誤也詐也差也欺也靡幼切二|繆:紕繆又姓漢書儒林傳有申公弟子繆生
e0W丘謬;䠗:䠗蹌行皃丘謬切一
f0W巨幼;𧾻:𧾻䠗醜行之皃巨幼切一
#沁
O1S七鴆;沁:水名在上黨亦州名本漢穀遠縣後魏置沁源縣武德初置州因沁水以名之七鴆切四|𠖶:𠖶冷|吣:犬吐|䈜:䈜墨工人具
N1S子鴆;浸:漬也漸也子鴆切四|濅:+上同出說文|𥧲:+上同出字林|祲:祅氣也又子心切
c1S汝鴆;妊:妊身懷孕汝鴆切五|絍:織絍亦作紝䋕|鵀:戴鵀鳥|任:已上四字並又音壬|衽:衣衿
L1S直禁;鴆:鳥名廣志云其鳥大如鴞紫綠色有毒頸長七八寸食蛇蝮雄名運日雌名陰諧以其毛歷飲食則殺人直禁切三|沈:又直壬切|㼉:青皮瓜名
X1S之任;枕:枕頭也論語曰飲水曲肱而枕之之任切又之稔切二|針:又之林切
f1a巨禁;𦧈:牛舌下病巨禁切十|䶖:-|𤘡:+並上同|噤:說文曰口閉也|𦨽:蜀人呼舟|紟:紟帶或作襟又音今|鈙:說文云持止也讀若琴亦作㯲|凚:寒凚|笒:笒籛|齽:齒向裏
d1a居蔭;禁:制也謹也止也避王莽家諱改曰省又姓何氏姓苑云今吳興人居蔭切三|僸:北夷樂名又居林切|㯲:格也
M1S乃禁;賃:傭賃也借也乃禁切一
h1a於禁;蔭:說文曰草陰地也於禁切七|䅧:苖美|窨:地屋|喑:聲也|𤷜:心中病亦作癊|廕:庇廕|飲:又於錦切
V1S所禁;滲:滲漉所禁切二|罧:爾雅曰槮謂之涔郭璞云今之作罧者聚積柴木於水中魚得寒入其裏藏隱因以簿圍捕取之又息甚切槮與罧同也
K1S丑禁;闖:馬出門皃丑禁切二|𧡬:私出頭視
S1S莊蔭;譖:讒也毀也莊蔭切一
T1S楚譖;讖:讖書釋名曰讖纖也其義纖微楚譖切一
g1a宜禁;吟:長詠宜禁切一
J1S知鴆;揕:擬擊史記曰右手揕其胷知鴆切二|㓄:掘地㓄又赤黑色
I1S良鴆;臨:哭臨又偏向良鴆切又音林二|𠐼:𠐼侺頭向前
Z1S時鴆;甚:太過時鴆切二|侺:𠐼侺
k1a于禁;䫴:䫴齘切齒怒皃于禁切二|𪔰:鼓聲見兵書
a1S式禁;深:不淺也式禁切又式今切二|𢊖:廕𢊖大屋
#勘
e2S苦紺;勘:校也苦紺切七|䘓:凝血|𧗀:+上同|𪉯:鹹味厚|轗:轗軻坎壈也|竷:擊也|磡:巖崖之下
d2S古暗;紺:青赤色也古暗切五|淦:新淦縣在豫章|𧆐:薏苡別名|灨:縣名南康記云章貢二水合流因其處立縣便以爲名在南康郡亦作贑|贛:贛榆縣在琅邪郡
j2S胡紺;憾:恨也胡紺切七|琀:送死口中玉亦作含|浛:水和物|唅:哺唅|蜭:有毛之蟲|莟:苗莟心欲秀也|䐄:食肉不猒
h2S烏紺;暗:日無光又默也深也貪也不明也烏紺切二|闇:冥也說文曰閉門也
F2S他紺;僋:僋俕癡皃他紺切八|㶒:㶒汛水浮皃|撢:深取|㐁:無光又舌出皃又吐念切|傝:傝儑不自安又吐盍切|䐺:食味美|憛:憛悇懷憂|誩:競言也又渠仰渠政二切
Q2S蘇紺;俕:僋俕蘇紺切四|閐:閐覆蓋也|㤾:憛㤾失志|䫅:顉䫅搖頭皃
O2S七紺;謲:怒也七紺切三|參:參鼓俗作叅|㽩:田隴聮也
G2S徒紺;醰:酒味不長徒紺切又音譚五|贉:買物預付錢也|𤁡:沈水底沒𤁡|瞫:䀨也又徒南切|𧗜:羊血凝
g2S五紺;儑:傝儑五紺切一
E2S丁紺;馾:馬睡皃丁紺切四|［帎］:冠幘近前|𩈉:頑劣皃|𩾺:𩾺鳥
H2S奴紺;妠:取也奴紺切一
I2S郎紺;𩖋〈顲〉:面色黃皃郎紺切三|僋:僋伸皃又僋俕不淨|𤃨:𤃨㶒浮皃
i2S呼紺;䫲:面虛黃色呼紺切二|𩞿:食不飽也
N2S作紺;篸:以針篸物作紺切二|撍:手撼
#闞
e3S苦濫;闞:魯邑亦視也又姓左傳齊大夫闞止苦濫切五|瞰:視也|𣊟:日出皃|嚂:呵也又工覽切|𪉿:味苦
I3S盧𣊟;濫:叨濫汎濫盧𣊟切九|㔋:刀利|𨣨:𨣨觴說文曰泛齊行酒也|纜:維舟吳書曰甘寧常以繒錦維舟去輒割弃以示奢|爁:火皃|㜮:貪也失禮也過差也俗作從水|懢:貪也|䆾:䆾䆱不平|嚂:食皃
F3S吐濫;賧:夷人以財贖罪吐濫切七|𪊇:𪉦𪊇無味|䆱:䆾䆱不平|𪉧:無味|睒:候視|澉:薄味|舕:舚舕舌出
d3S古蹔（暫）;𪉦:𪉦𪊇無味古蹔切二|𪉿:味苦
i3S呼濫;𧵊:乞戲物或作斂呼濫切三|蘫:瓜葅也出說文|䖔:虎怒
j3S下瞰;憨:害也果決也下瞰切又呼甘切六|㺖:犬吠聲|譀:誇誕東觀漢記曰雖誇譀猶令人熱又呼甲切|䗣:瓜蟲|䐄:炙令熟或作𤎡|𤎡:+上同
G3S徒濫;憺:恬靜徒濫切又徒敢切八|惔:+上同|澹:水搖動皃|腅:相飯也或作啖|淡:水味|啗:噉也食也|啖:誑也|倓:安也靜也恬也亦作澹
P3S藏濫;暫:左傳云婦人暫而免諸國暫猶卒也藏濫切三|蹔:+上同|鏨:鐫石又音蠶
E3S都濫;擔:負也都濫切二|甔:甔石大甖又都甘切
Q3S蘇暫;三:三思蘇暫切又蘇甘切一
#豔
l4S以贍;豔:美色也以贍切九|艷:+俗|爓:光也|焰:+上同|焱:火華也|𢴵:豔也|鹽:以鹽醃也本音平聲|𤅸:+上同|灩:瀲灩水波動皃
Z4S時豔;贍:賙也時豔切一
c4S而豔;染:而豔切又如檢切二|髯:髯頷毛又人占切
h4W於豔;厭:論語曰食不厭精於豔切五|𢜰:快也又於驗切|猒:飽也又於廉切|饜:+上同|嬮:嬮嬱美女
A4K方驗;窆:下棺方驗切又方亙切二|砭:石針說文曰以石刺病也又甫廉切
g4a魚窆;驗:證也徵也效也說文云馬名也魚窆切三|噞:噞喁魚口|𣄝:證也
a4S舒贍;閃:說文曰闚頭門中也舒贍切又舒斂切四|煔:火行皃|苫:以草覆屋|掞:舒藻
N4S子豔;𡄑:𡄑㖩不廉子豔切又子廉切一
O4S七豔;壍:坑也遶城水也七豔切四|塹:+上同出說文|槧:插也論衡曰斷木爲槧釋名曰槧版長三尺者也槧漸也言漸漸然長也又七廉切又才敢切|嬱:嬮嬱美女皃
I4S力驗;殮:殯殮力驗切七|斂:聚也又力琰切|瀲:泛瀲一曰水波也亦作澰|爁:爁焱火延|𧸘:市先入值也|𩅼:小雨|獫:長喙犬名
K4S丑豔;覘:候也說文云闚視也春秋傳曰公使覘之丑豔切二|䀡:視也
Y4S昌豔;䠨:音譜云馬急行昌豔切八|幨:披衣或作襜裧|襜:-|裧:+並上同|韂:鞍小障泥|䪜:+上同|㙴:蔽也|䦲:闚䦲
h4a於驗;𢜰:快也於驗切亦作㤿二|俺:大也
P4S慈豔;潛:藏也慈豔切一
X4S章豔;占:固也章豔切又職鹽切一
#㮇
F5S他念;㮇:火杖他念切六|舚:舌出皃|忝:辱也又他玷切|𨸱:亭名在京兆|煔:火光|㐁:無光說文曰舌皃
H5S奴店;念:思也又姓西魏太傅念賢奴店切二|𦁤:字林云挽船篾也
E5S都念;店:店舍崔豹古今注云店置也所以置貨鬻物也都念切十一|坫:墇也屏也|沾:水名在上黨說文他兼切|痁:病也又式詹切|墊:下也又墊江在巴陵又徒協切|𩅀:早霜寒|唸:呻吟|㝪:窮也說文曰屋傾下也|埝:下也|𦒻:老人面黑皃|䀡:目垂皃又丁炎切
Q5S先念;䃸:䃸磹電光先念切二|䆎:禾草不實稴䆎之皃
G5S徒念;磹:徒念切二|㼭:支也出通俗文
d5S紀念;趝:疾行皃紀念切一
h5S於念;酓:苦味於念切一
N5S子念;僭:擬也差也子念切一
P5S漸念;䁮:閉目思也漸念切一
d5S古念;兼:古念切又古嫌切二|䱤:魚名
e5S苦念;傔:傔從苦念切一
I5S力店;稴:稴䆎力店切一
#釅
g8e魚欠;釅:酒醋味厚魚欠切二|𪙊:齒皃
i8e許欠;脅:妨也許欠切二|姭:好皃
e8e丘釅;㪁:厓下也丘釅切二|𤬯:似瓶有耳
D9O亡劒;𦲯:草木蕪蔓也亡劒切一
#陷
j6S戶韽;陷:入地隤也戶韽切五|䱤:魚名又古念切|臽:小坑|䐄:說文云食肉不猒也又膇䐄也|錎:車鐶
h6S於陷;韽:下入聲俗作𪛏於陷切四|𤟟:犬吠又乙咸切|淊:水沒|揞:吳人云拋也
S6S莊陷;蘸:以物內水莊陷切一
J6S陟陷;𪉜:鹹多陟陷切三|站:俗言獨立又作𥩠|𣳤:江岸上地名也出活州記
e6S口陷;歉:歉喙口陷切又口咸切二|䫡:䫡顑面長皃又公陷切
L6S佇陷;𧸖:重買佇陷切三|詀:被誑|譧:+俗
U6S仕陷;儳:輕言仕陷切三|𨼮:陷也|䪌:韉之短者
d6S公陷;𪉦:鹹味公陷切二|䫡:䫡胡劑面也
M6S尼賺（𧸖）;諵:尼賺切一
g6S玉陷;顑:顑長面也玉陷切一
#鑑
d7S格懺;鑑:鏡也誡也照也亦作監格懺切又古銜切五|鑒:+上同|監:領也亦姓風俗通云衛康叔爲連屬之監其後氏焉又古銜切|𥌈:瞻也|㔋:利也又細切也
T7S楚鑒（鑑）;懺:自陳悔也楚鑒切六|儳:雜言又倉陷切|摲:投也|𤮭:甖屬|㺖:小犬聲|嚵:試人食
S7S子鑑;覱:覱㒈高危皃子鑑切三|𩈻:長面皃又昨三切|𩅼:以物內水中出音譜
V7S所鑑;釤:大鎌所鑑切三|䀐:暫見|㣌:相接物也又利也出字諟
i7S許鑑;㒈:覱㒈許鑑切三|譀:譀𧭡𧭡呼戒切|闞:犬聲
C7C蒲鑑;埿:深泥也蒲鑑切二|湴:+上同
j7S胡懺;㽉:大瓮似盆續漢書云盜伏於㽉下胡懺切二|㯺:大櫃又下斬切
U7S士懺;鑱:鑱土具士懺切又士銜切六|䪌:䪌韉|欃:水門又作㸥|䳻:似雕而斑白出音譜|讒:譖也又士衫切|艬:艬船
h7S=黯去聲;𪒠:叫呼仿佛𪒠然自得音黯去聲一
#梵
C9O扶泛;梵:梵聲扶泛切三|帆:船使風又音凡|颿:+上同說文曰馬疾步也
B9O孚梵;汎:浮皃孚梵切八|泛:+上同|𠆩:輕也|䀀:杯也|𥁔:+上同|氾:濫也|䒦:草浮水皃又匹凡切|姂:好皃
d8e居欠;劒:釋名曰劒檢也所以防檢非常也廣雅曰龍泉太阿干將鏌鋣斷蛇魚腸純鈞燕支蔡倫屬鹿干隊堂谿墨陽巨闕辟閭並劒名也崔豹古今注云吳大皇帝有寶劒六一曰白虹二曰紫電三曰辟邪四曰流星五曰青冥六曰百里列子云孔周有三劒一曰含光二曰承影三曰霄練吳王賜子胥屬鏤之劒而死周穆王有錕鋙劒切玉如泥居欠切一
e8e去劒;欠:欠伸說文曰張口气悟也今借爲欠少字去劒切二|㐸:+俗
h8e於劒;俺:大也於劒切八|㤿:甘心|淹:沒也又繅絲一淹也|𦑎:劒羽|㛪:誣挐|裺:衣寬|䛳:䛳匿|覎:覎口墟名在富春渚上也
#屋
hAD烏谷;屋:舍也具也淮南子曰舜築牆茨屋風俗通曰屋止也亦虜複姓後魏書官氏志云屋引氏後改爲房氏烏谷切七|𡲃:+籀文|𦤼〈𦤿〉:+古文|剭:鄭玄注周禮云剭誅謂所殺不於市而以適甸師氏又音握|𨜘:地名|𪑱:墨刑名又音握|䑁:䑁膏肥皃
GAD徒谷;獨:說文曰大相得而鬬也羊爲羣大爲獨一曰獨𤞞獸名如虎白身豕鬣馬尾出北嚻山𤞞音欲亦單獨又虜複姓有獨孤氏後魏書云西方獨孤渾氏後改爲杜氏徒谷切三十|黷:垢也蒙也黑也|讟:謗讟|髑:髑髏|䫳:+上同|殰:殤胎|讀:讀誦|櫝:函也又曰小棺|牘:簡牘|儥:見也動也又音育|㾄:字書云怨痛也|贕:卵敗|碡:磟碡田器|䢱:媟䢱|䮷:騼䮷野馬|皾:滑也|𤟩:獸名如鼠|襡:襡韜藏又音蜀|韣:弓衣又之蜀切|瓄:圭名|瀆:說文曰溝也一曰邑中溝爾雅曰江河淮濟爲四瀆|𨽍:說文曰通溝以防水|豄:+古文|韇:箭筩|嬻:媟慢|犢:牛犢|鸀:鸀𪂹鳥也|罜:罜䍡魚罟|㒔:㒔㑛短醜皃|匵:匵匱
dAD古祿;穀:五穀也又生也祿也善也說文曰續也百穀之總名今經典省作穀餘從㱿者並同古祿切十七|糓:+俗|轂:車轂|榖:木名|瀔:水名|谷:山谷亦養也窮也又姓漢有谷永又欲鹿二音|瑴:玉名又音角|𪇗:布𪇗鳥案爾雅只作穀|𣨍:𣨍殐死皃出廣雅|𪕸:鼠名|䜼:豆名|𧣡:𧣡𡖯多也|䐨:足跗|𤞞:獸如赤豹五尾又音欲|𥆌:動目|䀰:大目|唂:鳥鳴又作唃
jAD胡谷;縠:羅縠胡谷切十四|槲:木名|斛:十斗又虜複姓二氏後魏有尚書斛斯延齊有丞相咸陽王斛律金|螜:螻蛄|𧂔:水菜可食|礐:說文云石聲也|觳:周禮注云受二三斗又苦角切|蔛:石蔛|𨢋:酒濁|𣹬:水聲|䶜:齒聲|㽇:瓦坏|䈸:箱䈸|焀:火皃
eAD空谷;哭:哀聲空谷切八|䍍:未燒瓦|㲉:卵也|𪍠:餅麴|䧊:大阜|䵈:枲未績者|㲄:土墼|𣫓:麻𣫓
FAD他谷;禿:說文云無髮也从人上象禾粟之形文字音義云蒼頡出見禿人伏於禾中因以制字又國語云史伯曰祝融之後八姓己董彭禿妘曹斟芉是也又虜複姓有禿髮氏其先壽闐之在孕其母胡掖氏因寢而產於被中鮮卑謂被爲禿髮因而姓焉禿髮烏孤以後魏元興元年稱王遷于樂都号涼及國滅入魏賜姓源氏他谷切五|𣬜:+籀文|䛢:詆䛢狡猾|𢬳:杖指|鵚:鵚鶖鳥也
EAD丁木;豰:豰𣫎丁木切八|啄:啄木鳥|䐁:尾下竅也|𡰪:+俗|𧞐:衣至地也說文音斲|𢽚:擊聲|竺:竺厚|剢:刀鋤
QAD桑谷;速:疾也召也戚也徵也桑谷切十八|遬:+籀文|𧫷:+古文|蔌:郭璞云菜茹之摠名也詩云其蔌維何傳謂菜肴也|餗:鼎實|𩱖:+說文同上|𧐒:䗱𧐒蟲|樕:槲樕木|𣫎:豰𣫎動物豰丁木切|㑛:㒔㑛又音束|梀:赤梀木名|𪋝:麋鹿跡也|藗:白茅也|殐:𣨍殐|嗽:吮也|𡖯:𧣡𡖯多也|棴:棴常樹名|涑:水名在河東
IAD盧谷;祿:俸也善也福也錄也又姓紂也祿父之後盧谷切四十七|鹿:獸名國語曰周穆王征犬戎得四白鹿四白狼而荒服不至又姓風俗通云漢有㔾郡太守鹿旗|漉:滲漉又瀝也說文浚也一曰水下皃|淥:+說文同上|觻:觻得縣名在張掖|睩:視皃|䚄:笑視|龣:東方音|𨏔:𨏔轤圓轉木也或作樚|轆:+上同|㼾:㼾甎|𦪇:舟名|琭:玉名老子曰琭琭如玉注云琭琭喻少|簏:箱簏說文云竹高篋也|箓:+說文同上|螰:螇螰蟲𨎥蛄也|䍡:罜䍡|麓:山足穀梁曰林屬於山曰麓|㯟:+古文|碌:多石皃|盝:去水也瀝也瀝也或作漉|𥂖:+上同|騼:野馬|磟:磟碡又音六逐|簶:弧簶箭室也出音譜|𧌍:𧌍聽似蜥蜴居樹上輒上齧人上樹垂頭聽聞吠聲乃去出字林|谷:漢書匈奴傳有谷蠡王蠡音离|娽:埤蒼云顓頊妻名說文云隨從也史記毛遂入楚謂十九人曰公等娽娽可謂因人成事耳又力玉切案史記亦作錄|𥉶:𥌮𥉶眼淨也|摝:振也周禮曰摝鐸鄭玄云掩上振之爲摝|𥛞:祭也|𦌟:捕魚具也|𥂇:吳王孫休三子名|𤽺:白獸|廘:賈逵曰廘庾也|角:角里先生漢時四皓名又音覺|𥪋:見鬼|彔:本也亦刻木也|濼:水名又音扑|鏕:鉅鏕郡名案漢書只作鹿|趢:趢趗局小|䎑:水上飛也|𨌠:車聲|㪖:剝聲|𩅄:大雨|蔍:蔍蔥草|鄜:地名
iAD呼木;嗀:歐聲呼木切七|豰:獸名似豹而小食獼猴又名黃𦝫案說文作㺉犬屬𦝫已上黃𦝫已下黑食母猴|熇:熱皃|𦞦:羹𦞦又火各切|𧹲:日出赤皃|㷤:+上同|嚛:大歠聲
PAD昨木;族:宗族昨木切三|銼:銼𨰠釜屬|鑿:鑿鏤花葉又音昨
OAD千木;瘯:瘯瘰皮膚病也千木切六|䃚:碌䃚石皃|蔟:蠶蔟又千候切|趗:趢趗小皃|梀:短椽說文丑錄切|簇:小竹
NAD作木;鏃:箭鏃作木切二|鎐:姓也出彭城
CAD蒲木;暴:日乾也蒲木切十二|曝:+俗|瀑:瀑布水流下也|䗱:䗱𧐒蟲名|㲫:㲢㲫毛不理也|樸:爾雅云樕樸心又音卜|僕:侍從人也|䑑:+古文|𥐁:短人又倉候切|菐:瀆菐|𡕡〈𡰿〉:行皃|穙:穙𥡜也
BAD普木;扑:打也普木切十一|醭:醋生白醭|濼:齊魯閒水名左傳云公會齊侯于濼|墣:說文云塊也又匹角切|𥣜:草生穊也|𪔿:𪖈𪔿鼠名|攴:擊也凡從攴者作攵同|撲:拂著|骲:骨鏃名也|𪐙:淺黲黑也|䴆:鳥也
AAD博木;卜:卜筮龜曰卜蓍曰筮又姓孔子弟子卜商博木切十四|濮:水名出陳留郡入鉅野亦州名古昆吾之墟左傳齊桓公會諸侯於鄄今鄄城縣是後漢獻帝時兗州刺史治於此後魏爲濮陽郡隋初置濮州又姓出何氏姓苑|䧤:彭䧤蠻夷國名|轐:車伏兔|𡡐:昌意妻也|樸:棫樸叢木又音僕樸樕小木也|獛:獛鉛南極之夷尾長數寸巢居山林出山海經|蹼:足指閒相著爾雅云鳧鴈醜其足蹼|纀:爾雅曰裳削幅謂之纀郭璞云削殺其幅深衣之裳|襆:+上同|𩯏:須髯|䪁:䪁絡頭繩|鳪:鳪雉|𪇰:烏𪇰水鳥似鶂而短頸腹翅紫白背上綠色又音剝
DAD莫卜;木:樹木說文曰木冒也冒地而生東方足行又姓木華字玄虛作海賦莫卜切十三|沐:沐浴說文曰濯髮也禮記曰頭有創則沐又姓風俗通曰漢有東平太守沐寵又漢複姓有沐簡氏何氏姓苑云今任城人|朷:朷桑|毣:思皃一曰毛濕也|鶩:鳧屬|霂:霢霂|𨍎:車轅名也|㡔:轅上絲也|蓩:毒草|艒:小艖|鞪:說文曰車軸束也|楘:屋架五楘詩曰五楘梁輈傳云楘歷錄也|蚞:螇螰蟲
ABP方六;福:德也祐也方六切十七|腹:腹肚|複:重衣|幅:絹幅又姓也|輻:車輻|𠋩:優𠋩|葍:葍𦼱爾雅曰葍䔰又葍藑茅|蝠:說文曰蝙蝠伏翼也崔豹古今注云一名仙鼠|𥳇:實竹|鍑:說文云釜而大口者或作鍢又音富|鶝:戴勝別名|踾:踾踧聚皃|輹:車軸縛也|菐:瀆菐|偪:偪陽宋國|楅:束以木逼於牛角不令牴觸人|𦿁:草名
CBP房六;伏:匿藏也伺也隱也歷忌釋曰伏者何金氣伏藏之日金畏火故三伏皆庚日又姓出平昌本自伏犧之後漢有伏勝文帝蒲輪徵不至房六切三十三|復:返也重也亦州名古音陵縣春秋時屬楚秦屬南郡隋爲江陽郡武德初爲復州|虙:古虙犧字說文云虎皃又姓虙子賤是也|服:服事亦衣服又行也習也用也整也亦姓漢有江夏太守服徹|𦨈:+古文|茯:茯苓|馥:香氣芬馥|鵩:不祥鳥|鞴:韋囊步靫|蕧:旋蕧藥名|輹:車輹兔|𨋩:+上同|澓:澓流又姓漢宣帝時有東海澓仲翁|椱:織椱卷繒者|洑:洄流|箙:盛弓弩器|𩋟:+上同|𨌥:車笭閒皮篋也|𤸑:音譜云病重發也|𪃃:𪃃鶝即戴勝也|𩢰:馬也|𥨍:地室|棴:木出崐崘山也|复:行故道也說文作𡕨|畐:滿也|𩊙:車具|絥:-|𩎧:+並上同|菔:蘆菔菜也|匐:匍匐伏地皃又蒲北切|鰒:海魚名|𥪋:見鬼皃|栿:梁栿
VBD所六;縮:斂也退也短也亂也所六切十三|莤:說文曰禮祭束茆加于祼圭而灌鬯酒是爲莤象神歆之也一曰榼上塞也|𩘹:風聲|𧽏:趜𧽏體不伸也趜渠六切|樎:馬櫪|謖:起也|䎘:鳥飛|㩋:擊聲|蹜:文字音義云烏鵲醜其飛掌蹜在腹下也|摍:抽也顏叔也納鄰之嫠婦執燭燭盡摍屋以繼之|𧐴:蝍𧐴尺蠖|摵:到也又子六切|謏:小也又蘇了切
IBD力竹;六:數也力竹切二十二|陸:高平曰陸又高也厚也亦陸離參差也又姓出吳郡河南二望本自古天子陸終後|戮:刑戮說文殺也爾雅病也|剹:+上同|勠:勠力併力也又音留|稑:穜稑先種後熟曰穜後種先熟曰稑|穋:+上同|鵱:鵱鷜野鵝|蓼:蓼莪詩傳云蓼長大貌|𦾷:+上同|𩣱:𩣱良健馬|鯥:魚名似牛蛇尾出山海經|𦸐:蔏𦸐|磟:磟碡|𧌉:魁𧌉|淕:凝雨澤也|䡜:轓䡜車箱|坴:大塊|𡴆:地蕈|踛:翹踛也|僇:癡行又音溜|𥚊:見也
LBD直六;逐:追也驅也從也疾也強也走也直六切十二|軸:車軸|碡:磟碡田器又音祿獨|妯:妯娌|舳:舳艫|鱁:鱁鮧|𧏿:馬蚿蟲|筑:水名出房陵漢有筑陽縣蕭何妻封邑也|蓫:馬尾草|柚:杼柚機具又由舊切|䮱:馬䮱獸名|篴:竹名
dBP居六;菊:草名禮記季秋之月菊有黃華說文曰大菊蘧麥也居六切三十三|鞠:推窮也養也告也盈也禮記曰天子乃薦鞠衣於先帝鄭玄云鞠衣名蓋黃桑之服又姓出東萊風俗通曰漢有尚書令平原鞠譚又音麴又渠六切|蘜:爾雅曰蘜治牆郭璞云今之秋華菊也|𧃓:說文曰日精也似秋華|㥌:謹慎|𡙳:說文撮也|掬:+上同|匊:物在手|𥷚:說文曰窮治辠人也|𥱩:+上同|鞫:+上同|𡫬:說文窮也|𥩁:+上同|㹼:石㹼獸名食猴|𪈓:說文曰秸𪈓尸鳩爾雅作鴶鵴郭璞云今之布穀也|鵴:+上同|𨸰:曲岸水外曰𨸰|㘲:+上同|㽤:韭畦|䱡:郭璞云魚名有兩乳|椈:爾雅曰柏椈禮云鬯𦥑以椈|巈:山高皃|𦥑:兩手奉物|䳔:鳥名|𩛺:饘也|諊:法用|𩬜:亂髮|踘:踘蹋也|閰:閑閰|𣐊:木名|𧿻:足也|泦:水名文|趜:困人又巨竹切
eBP驅匊;麴:麴糵又姓出西平漢有麴演驅匊切五|𥶶:+上同說文曰酒母也|𩍔:+上同|鞠:姓也又居六切|𠤄:曲脊又渠六切
ZBD殊六;熟:成也殊六切八|孰:誰也|淑:善也|塾:門側堂崔豹古今注云臣來朝君至門外更詳熟所應對之事塾之言熟也|𨷙:+上同|璹:玉名|婌:後宮女官名|䃞:石聲
YBD昌六;俶:始也厚也作也動也昌六切五|柷:柷敔柷作樂也俗作拀又音祝|琡:璋大八寸曰琡又音祝|𣥹:至也|埱:氣出於地一曰始也
lBD余六;育:養也長也余六切二十四|毓:+稚也本亦同上|鬻:賣也亦作粥亦姓周有鬻熊爲文王師案說文鬻本音麋䭈也|粥:+上同|𩱱:說文鬻也|䋭:青經白緯淯陽所織|𧷗:賣也重也長也也動也說文衒也或作儥|儥:+上同|棛:車覆欄也|錥:鎢錥溫器|煜:火光又燿也|焴:+上同|昱:日光|蒮:爾雅云蒮山韭|淯:水名出攻離山|蜟:復蜟蟬未蛻者出論衡|𢌻:兩手捧物說文音匊|堉:地土肥也|喅:音聲|𤳕:生田|𥉑:望也又目明皃|逳:步也轉也行也|𦱀:草名|蘛:茂也
fBP渠竹;驧:馬跳躍也說文曰馬曲脊也渠竹切十二|𩣽:+上同|趜:趜𧽏|䱡:魚名|鵴:鴶鵴鳲鳩又音菊|𪁁:+上同|鞠:蹋鞠以革爲之今通謂之毬子又菊麴二音|毱:皮毛丸也|䗇:說文曰䗇鼀蟾蠩以脰鳴者也|踘:踘蹋也|䜯:谷名在上艾|𠤄:曲脊皃
OBD七宿;鼀:䗇鼀七宿切三|蹴:蹋蹴|殧:終也
cBD如六;肉:骨肉如六切俗作𡧢三|衄:鼻出血俗作衂又尼六切|鮞:魚子一曰魚名
XBD之六;粥:糜也之六切五|喌:呼鷄聲亦作𠱙|祝:巫祝又太祝令官名周禮曰太祝掌六祝之辭以事鬼神祈福祥求永貞亦音呪又姓後漢有司徒中山祝恬|柷:祝敔又音俶又爾雅曰柷州木髦柔英本亦作祝|琡:璋大八寸又音俶
aBD式竹;叔:季父亦姓左傳魯公子叔弓之後光武破虜將軍叔壽又漢複姓二氏後漢有犍爲叔先雄左傳魯有大夫叔仲小式竹切十三|儵:青黑繒|倐〈倏〉:倏忽犬走疾也|透:驚也又他豆切|虪:爾雅云虪黑虎又音育|跾:疾也長也|鮛:爾雅曰鮥鮛郭璞云鮪鱣屬也大者名王鮪小者名鮛鮪|掓:拾也|𢞣:疾也|翛:飛疾之皃又音蕭|尗:豆也|菽:+上同|㶖:水波
iBP許竹;蓄:蓄冬菜也許竹切又丑六切十|稸:+上同|畜:養也說文曰田畜也淮南子曰玄田爲畜又丑六許救二切|𤲸:+上同說文云魯郊禮畜从田从兹兹益也|㜅:媚也|鄐:晉邢侯邑又姓漢有鄐熙爲東海太守|荲:羊蹄菜又丑六切|蓫:+上同|慉:起也詩云不我能慉|𥈆:細視
JBD張六;竹:說文作竹冬生草也象形下垂者菩箬也史記曰渭川千畮竹其人與千戶侯等亦姓本姜姓封爲孤竹君至伯夷叔齊之後以竹爲氏今遼西孤竹城是後漢有下邳相竹曾張六切六|竺:天竺國名又姓出東莞後漢擬陽侯竺晏本姓竹報怨有仇以冑姓名賢不改其族乃加二字以存夷齊而移於琅邪莒縣也又冬毒切厚也俗作笁|筑:筑似箏十三弦高漸離善擊筑說文曰以竹爲五弦之樂也又爾雅曰筑拾也又音逐水名|築:擣也|𥴁:+古文|茿:萹茿也似藜赤莖生道傍可食
NBD子六;蹙:迫也促也近也急也子六切十七|踧:踧踖行而謹敬|𧑙:蝍𧑙蚇蠖也|𠴫:說文嗼也本音寂|㗤:㗤咨慙也|噈:歍噈口相就也|摵:到也|槭:木可作大車輮|殧:𣧩也|𣤶:取氣皃說文本才六切歍𣤶也|𥷛〈𥷼〉:笡也|縬:縮也又繒文也又側六切|𣢰:欻悲皃|𦟠:䐚𦟠膏澤也|顣:顣頞鼻頤促皃|䙘:好衣皃|蹴:蹋也又七六切
TBD初六;珿:齊也初六切六|矗:直皃又敕六切|𪘏:廉謹皃|𨴖:眾也出字統或作閦|𧯩:小豆|䎌:飛皃
MBD女六;肭〈朒〉:朔而月見東方謂之縮朒女六切八|恧:慙也|𦗂:+上同|忸:忸怩|衄:鼻出血又挫也又音肉|䖡:䖡蚭即蚰蜒也|䂇:刺也|沑:蹜沑水文聚
SBD側六;縬:縬文也側六切二|𡎺:塞也
BBP芳福;蝮:蝮蛇又姓乾封元年詔改武惟良爲蝮氏芳福切八|覆:反覆又敗也倒也審也又敷救切|蕧:蕧葐草又音服|𩯅:廣雅曰假髻也|副:剖也又敷救切|㙏:地室|𥨍:+上同|䔰:䔰𦼱草名又音富
hBP於六;郁:文也亦郁郅縣在北地又姓魯相有郁貢又虜三字姓二氏後魏書云蠕蠕姓郁久閭氏又北方郁原甄氏後改爲甄氏於六切二十|戫:有文章也|彧:+上同|燠:熱也又音奧|栯:栯李又音有俗作㮋|噢:噢咿悲也|墺:墺壤|䐿:鳥胃|薁:蘡薁|澳:隈也水內曰澳|隩:+上同又音奧|䉛:可以漉米|𣢜:愁皃|𨞓:姓出姓苑|𪑝:羔裘之縫又于逼切|稶:黍稷盛皃|懊:貪也愛也又音奧|㰲:吹氣也|𠸹:喉聲|𨪎:溫器
QBD息逐;肅:恭也敬也戒也進也疾也又州名古月氏國地漢匈奴昆邪王殺休屠王并其眾來降遂置酒泉郡後魏以酒泉爲甘州隋分福祿縣置肅州亦姓出姓苑息逐切二十三|宿:素也大也舍也說文作㝛止也左傳曰一宿爲舍再宿爲信又姓風俗通云漢有鴈門太守宿詳又虜複姓後魏末有賊帥勤宿明達又虜三字姓後魏書宿六斤氏後改爲宿氏又息救切|蓿:苜蓿史記云大宛國馬嗜目宿漢使所得種於離宮|夙:早也說文作𡖊早敬也从丮持事雖夕不休早敬者也丮音戟又姓魯大夫季孫夙之後|𠉦:-|𠈇:+並古文出說文|玊:朽玉又琢玉工又姓後漢有玉況字文伯光武以爲司徒|鷫:說文曰鷫鷞也五方神鳥也東方發明南方焦明西方鷫鷞北方幽昌中央鳳皇|𪂸:+上同|蟰:蟰蛸俗呼喜子詩曰蟰蛸在戶又音蕭|驌:驌騻馬名|䎘:䎘䎘鳥羽聲又音縮|𩘹:風聲|鱐:魚腊|䃤:黑砥石又音篠|𤥔:朽玉又姓也|潚:深清也亦姓漢有潚河|橚:木長皃|㩋:擊也|䑿:艒䑿船名|㑉:傗㑉不伸|璛:姓也|㪩:打也
DBP莫六;目:釋名曰目默也默而內識也說文曰人眼象形重童子也莫六切十一|睦:親也敬也又和睦也亦西胡姓|穆:和也美也敬也厚也清也又姓漢有穆生|苜:苜蓿|𦱒:𦱒蓿見爾雅注|牧:養也放也使也察也司也食也說文曰養牛人也又姓風俗通云漢有越嶲太守牧稂|㙁:㙁野殷近郊地名古文尚書作此㙁說文作坶|繆:禮記有繆公又姓也又靡幼切|萺:萺𦸚菜|㣎:說文曰細文也今作㣎同|㾇:㾇病
kBP于六;囿:園囿于六切又于救切二|哊:吐聲
KBD丑六;蓄:蓄冬菜詩曰我有旨蓄鄭玄云蓄聚美菜以禦冬月乏無時也本亦作畜丑六切十|稸:+上同|滀:水聚|苖:蓨也又他六徒歷二切蓨音挑又音剔|荲:羊蹄菜|蓫:+上同|敊:病敊皃|傗:傗㑉不伸|鄐:地名在晉|矗:直也齊也
gBP魚菊;砡:齊頭皃魚菊切一
PBD才六;𣤶:說文曰歍𣤶也才六切一
#沃
hCD烏酷;沃:灌也說文作𣵽又姓太甲子沃丁之後出風俗通烏酷切七|鋈:白金|鱟:魚名又音候|䑁:膏膜又音屋|䁷:瞋目|觷:治角也又戶角切|䮸:馬腹下聲
GCD徒沃;毒:痛也害也苦也憎也說文作𡹆厚也害人之草往往而生徒沃切八|𡹆:+見上注|𦺇:萹茿草|蝳:蝳蜍似蜘蛛|瑇:瑇瑁又音代|纛:左纛又徒号切|𢃶:+上同|碡:碌碡田器
ECD冬毒;篤:厚也說文曰馬行頓遟冬毒切十一|竺:地名說文厚也|督:率也勸也正也說文察也一曰目痛也又姓風俗通云漢有五原太守督□俗作𣈉|𧝴:衣背縫也|𧛔:-|𧞶:+並上同|錖:觼舌|𤬂:瓠𤬂|𥓍:𥓍矺玉篇云落石也|裻:新衣聲又先篤切|𡰪:凥𡰪俗
eCD苦沃;酷:虐也說文曰酒味厚也苦沃切六|焅:熱氣|𥞴:禾熟|嚳:帝嚳高辛氏也說文曰急告之甚也|硞:碌硞石狀|𡷥:山皃
jCD胡沃;鵠:鳥名又姓姓苑云今東海人胡沃切八|㿥:鳥白也|翯:鳥肥澤也詩云白鳥翯翯又音學|隺:高也|𤌍:灼也|頶:鼻高皃|𨴬:門聲|礐:石礐
CCD蒲沃;僕:僮僕說文曰給事者也漢書曰太僕秦官掌輿馬亦姓風俗通云漢有渾梁侯僕多又虜複姓魏書僕蘭氏後改爲僕氏蒲沃切六|䑑:+古文|鏷:鏷𨬟矢名案左傳曰魯莊公以金僕姑射南宮長萬字不從金|䗱:䗱蠃又䗱𧐒蟲|轐:車𨋩兔也|䴆:䴆𪇰
QCD先篤;洬:雨聲先篤切二|裻:新衣聲
dCD古沃;梏:手械紂所作也古沃切九|牿:牛馬牢也|䧼:鳱䧼鳥名似鵲|䅵:禾皮又地名|告:又音誥告上曰告發下曰誥|郜:國名又音誥|祰:說文云告祭也|䧊:說文云大阜也|䶜:治象牙也
DCD莫沃;瑁:瑇瑁莫沃切又莫代切五|𣔺:門樞橫梁|媢:夫妬婦|艒:艒䑿船名|萺:草也
iCD火酷;熇:熱也火酷切四|臛:羹臛又音郝|嚛:食新也|歊:氣出皃又音嚻
HCD內沃;褥:小兒衣也內沃切又而蜀切四|傉:虜三字姓有庫傉官氏|耨:釋典云阿耨|搙:捻搙
NCD將毒;傶:邑名又姓將毒切三|𣪻〈𣪲〉:穿也|錊:姓也
ACD博沃;襮:黼領博沃切三|犦:犎牛出合浦郡|𪇰:鵅烏𪇰水鳥名
ICD盧毒;濼:水名在濟南盧毒切又力各切一
gCD五沃;𤛹:白牛五沃切又音岳一
#燭
XDD之欲;燭:燈燭也禮曰嫁女之家三日不息燭世本曰石季倫以蠟燭炊又姓左傳鄭大夫燭之武之欲切十三|屬:付也足也會也官眾也儕等也經典作屬又音蜀|属:+俗|矚:視也|䌵:綴帶|囑:託也|鸀:鸀鳿鳥|䟉:小兒行皃|㰲:吹氣也|噣:噣𪁞鳥名|蠾:蚤也方言云鼅鼄自關而東趙魏之郊或謂之蠾蝓又音蜀|韣:弓衣又大谷切|蠋:螐蠋
gDP魚欲;玉:白虎通曰玉者象君子之德燥不輕濕不重是以君子寶之禮記曰執玉不趨又烈火燒之不熱者真玉也說文本作王隷加點以別王字魚欲切四|獄:皋陶所造說文确也从㹜从言二犬所以守也|鳿:鸀鳿鳥|頊:人姓頊䪴又音勖
iDP許玉;旭:說文曰日旦出皃一曰明也許玉切五|頊:顓頊高陽氏也又謹敬皃|勗〈勖〉:勉也|𩔴:𩔴顱出聲譜|𩪉:+上同
dDP居玉;輂:禹所乘直轅車說文曰大車駕馬也居玉切十二|絭:纕臂繩也又居願切|鋦:以鐵縛物|挶:持也|𦥑:斂手|梮:舉食器也|䡞:說文曰直轅車𩎈縛也|㮂:舉食者名|䋰:靴䋰子纏連者說文約也|拲:兩手共梏又己奉切|𦅽:𦅽屬|𧤑:曲角
fDP渠玉;局:曹局又分也說文促也渠玉切五|跼:踡跼又曲也俛也促也|駶:馬立不定|侷:侷促短小|䎤:耕也
ZDD市玉;蜀:巴蜀說文曰葵中蟲也淮南子云蠶與蜀相類而愛憎異也亦作蠋市玉切十二|韣:弓衣又徒谷切|蠾:蠾蝓蜘蛛|㯮:木似柳葉大也|䙱:玉篇云長襦也連𦝫衣也|襩:+上同|㒔:㒔㑛動皃|襡:短衣又大口切|屬:附也類也又音燭|属:+俗|㻿:玉㻿|鐲:溫器又直角切
YDD尺玉;觸:突也尺玉切四|觕:+古文|歜:怒氣亦人名齊宣王時有高士顏歜或作斶|臅:狼臅膏也
cDD而蜀;辱:恥辱又汚也惡也又姓出姓苑而蜀切十一|蓐:草蓐又薦也說文曰陳草復生也一曰蔟也|褥:氈褥|鄏:郟鄏地名在河南|縟:文采|溽:溽暑濕熱|㦺:矛戟枝也|媷:懈惰也|嗕:囑嗕憐皃又西羌名|𪑾:黑垢|𩱜〈𩱨〉:大鼎
aDD書玉;束:縛也又姓本自疎氏避難除足姓束左傳晉有束晳書玉切二|㑛:㒔㑛
lDD余蜀;欲:貪欲也余蜀切九|浴:洗浴說文曰洒身也洒先禮切|鵒:鴝鵒|𩀑:+上同|鋊:炭鉤又銅屑也漢書曰磨錢取鋊|輍:車枕前也|慾:嗜慾|𤞞:獨𤞞獸|谷:山谷爾雅曰水注谿曰谷說文曰泉出通川爲谷亦虜三字姓吐谷渾氏又音穀
LDD直錄;躅:躑躅直錄切三|䠱:+上同|蠋:𧓸蠋蟲名
IDD力玉;錄:采錄說文曰金色也又錄事職官要錄云總錄眾事力玉切十七|淥:淥水名在湘東又姓何氏姓苑有淥圖爲顓頊師|䚄:眼曲䚄也|綠:青黃色永徽二年始七品六品服綠飾以銀八品九品服青飾以鍮石至文明元年又改青服碧色|醁:美酒|騄:騄駬駿馬名|娽:隨從又音鹿|菉:菉蓐草|逯:謹也又姓風俗通云漢有大司空逯並後趙錄有金紫光祿大夫廣平逯明西征記有逯明壘云是石勒十八騎中人|䱚:魚名|籙:圖籙|碌:碌石綵色本又音祿|䟿:恭䟿也|𧨹:謯也|趢:趢𧼙兒行|㫽:日暗|㪖:剝㪖又聲㪖
eDP丘玉;曲:委曲說文作曲象器曲受物之形又姓晉穆侯子成師封於曲沃後氏焉漢有代郡太守曲謙丘玉切四|䱡:魚名|䒼:蠶薄漢書周勃織溥䒼爲生亦作筁|匤:匤匣也
JDD陟玉;瘃:寒瘡也陟玉切七|𤷚:+上同|孎:謹也又陟角切|斸:斫也又钁也|钃:+上同|欘:枝上曲一曰斤柄|𢒔:豕行皃又丑足切
NDD即玉;足:爾雅云趾足也又滿也止也從口止即玉切又將喻切二|哫:楚詞云哫訾憟斯王逸謂承顏色也
bDD神蜀;贖:說文貿也神蜀切又音樹三|𩌮:𩌮鞮也又似足切|䴰〈䴬〉:姓也梁四公子䴬䵎之後
CDP房玉;幞:帊也又幞頭周武帝所制裁幅巾出四腳以幞頭乃名焉亦曰頭巾房玉切二|襆:+上同
ODD七玉;促:近也速也至也迫也七玉切六|誎:飾也|趗:趗速|𤗁:迫也|𦠁:丳𦠁炙具|㹱:宋良大又七雀切
RDD似足;續:繼也連也又姓舜七友有續牙似足切四|俗:風俗說文習也|藚:藚斷藥名一曰牛脣又名水藛|𩌮:白𩌮鞮也
QDD相玉;粟:禾實也淮南子曰昔蒼頡作書而天雨粟又姓袁紹魏郡太守粟攀相玉切七|𥻆:+上同見說文|憟:憟斯|涑:水名在河東又蘇侯切|𣯼:𣯼㲨罽毛|玊:西番國名亦姓又香救切又新菊切|㔄:細切
ADP封曲;䪁:絡牛頭封曲切一
KDD丑玉;梀:梀樗木名丑玉切七|亍:彳亍|𥹵:字書曰𥻿𥹵損米|𧼙:趢𧼙兒行|𢒔:豕行皃又知足切|㙇:牛馬所蹈之處|豖:說文曰豕絆足行豖豖也
#覺
dED古岳;覺:曉也大也明也寤也知也古岳切又古孝切十八|斠:平斗斛|角:芒也競也觸也說文曰獸角也又角抵戲漢武故事曰未央庭中設角抵戲角抵者六國時所造也使角力相抵觸亦大角軍器徐廣車服儀制曰角前世書記所不載或云本出羌胡以驚中國之馬也又姓後漢有角善叔|桷:椽也|較:車箱又直也略也又古孝切|䡈:說文曰車輢上曲銅也|珏:二玉相合爲一珏|瑴:+上同|䮸:馬腹下聲|䚫:飾杖頭骨又胡歷切|榷:以木渡水今之略彴也|捔:掎捔|搉:揚搉大舉又音確|䁷:明也|梏:直也又古沃切|傕:後漢有李傕|䮤:馬白額|龣:樂器
gED五角;嶽:五嶽也五角切八|岳:+上同|樂:音樂周禮有六樂雲門咸池大韶大夏大濩大武又姓出南陽本自有殷微子之後守戴公四世孫樂莒爲大司寇|鸑:鸑鷟鳳屬國語曰周之興也鸑鷟鳴于岐山俗作𩁓|𩓥:說文云面前岳岳也|觷:爾雅云角謂之觷治角也或作礨又音學|捳:抨捳|㹊:說文曰白牛也
UED士角;浞:水濕士角切十二|丵:叢生草|鋜:鎖足|灂:瀺灂|鷟:鸑鷟|捔:攙捔組織亦作𧣀|澩:山夏有水冬無水|篧:魚罩又音捉|汋:說文曰激水聲也一曰井十有水一無水爲瀱汋|齺:齒相近皃|𤉐:速也或作𨖮|簎:取魚箔也
SED側角;捉:捉搦也側角切七|穛:早熟穀|𥼚:+上同|穱:稻處種麥|斮:斬又側略切|篧:魚罩|𧂒:蒵毒
VED所角;朔:月一日又幽朔也命和叔宅朔方北方也又姓何氏姓苑云南陽人俗作𦙚所角切十二|欶:口噏也|嗽:+上同|矟:矛屬通俗文曰矛丈八者謂之矟|槊:+上同|蒴:蒴𧃔藥也|數:頻數|箾:說文曰以竿擊人又舞者所執又蘇彫切|𦂗:緘也|㮶:木名|揱:纖也又長臂皃又相邀切|𦋞:㩋𦋞罘䍐
JED竹角;斲:削也竹角切十九|涿:郡名|諑:訴也王逸注楚詞云諑猶僣也|㧻:擊也推也|琢:治玉|孎:謹孎|卓:高也又姓蜀有卓王孫|桌:+古文|𥢔:說文曰特止也|啄:鳥啄也又丁木切|斀:說文云去陰刑|啅:眾口|噣:鳥生子能自食|𢁁:龍尾|䐁:+上同|倬:大也|晫:明也又敕角切|𢽚:打也|菿:說文云草大也本音到又陟孝切
AED北角;剝:落也削也割也傷害也北角切十四|駮:六駮獸名似馬倨牙食虎豹|駁:馬色不純|𩐟:指聲|𦢊:皮破|嚗:李頤注莊子云嚗放杖聲又孚邈切|𥭖:𥭖手足指節之鳴者亦作肑|肑:+上同|爆:火烈又北教切|𪇰:烏𪇰鳥又博沃切|髉:骱骺|㿺:㿺𤿈皮起|䑈:䑈犖亂雜|趵:足擊
DED莫角;邈:遠也亦作𨘷莫角切九|藐:紫草|㦝:說文美也|眊:目少精|皃:皃人類狀本莫教切|毣:好皃一曰毛濡|瞀:目不明也|𢷕:打也|瞐:美目
CED蒲角;雹:說文曰雨冰也蒲角切二十|𩅟:+古文|𢷏:相𢷏亦作撲|跑:秦人言蹴|𩣡:獸名似馬一角|䮀:+上同|骲:骲箭|鰒:魚名|䈏:竹名|瓝:瓜瓝也|瓟:+上同|㼎:+上同出說文小瓜也|謈:嗃謈大呼說文作𧬉云大呼自冤也|犦:犎牛又甫沃切|豰:說文云小豚也|窇:廣雅曰窖也|𥭓:車軬帶也|𦢊:肉胅起|懪:煩悶也|㩧:擊聲又匹角切
BED匹角;璞:玉璞匹角切十五|㩧:擊聲又蒲角切|樸:木素|朴:+上同又厚朴藥名|㹒:牛未㓺|攴:楚也又普木切小擊也|墣:說文塊也淮南子曰水勝土也非以一墣塞江|圤:+上同|颮:颮颮紛紛眾多皃|鞄:攻皮之工|謈:自冤本蒲角切|𤆝:火裂|𥛟:玉篇云久視|㺪:批㺪|𧴤:盈財
eED苦角;㱿:皮甲又說文曰从上擊下也一曰素也苦角切十九|毃:毃打頭|愨:謹也善也愿也誠也|搉:擊也又音角|確:靳固也或作碻|碻:+上同|𤿩:𥀣𤿩皮乾|㲉:鳥卵|觳:盛脂器也|燩:廣雅云火乾物|嶨:爾雅云山多大石嶨|礐:+上同|塙:高也|𣤇:+上同|⿰隺犬:至也高也|硞:固也|𠕓:說文曰幬帳之象隷省作𡉉|埆:墝埆不平|𡇱:鞭聲
LED直角;濁:不清也又姓漢書貨殖傳云濁氏以胃脯而連騎直角切十六|擢:拔也抽也出也|濯:澣濯又姓風俗通云濯輯之後|鵫:白鵫鳥|嬥:直好皃|𧃔:蒴𧃔|鐲:似鈴又音蜀|𢺡〈欘〉:爾雅云拘欘謂之定欘鋤也拘音劬本亦作斪斸斸陟玉切|㺟:獸名|鸀:小鳥似烏赤喙出西方|蠗:小蜃名|鸐:山雉長尾|𩑂:龍𩑂|𢢗:不安|𩆸:大雨𩆸𩆸|㪬:築也春也本又敕角切
hED於角;渥:霑濡於角切十七|握:持也|偓:偓促又姓列仙傳有偓佺|箹:小籥|幄:大帷三禮圖曰在上曰弈四旁及上曰帷上下四旁悉周曰幄|楃:說文曰木帳也|喔:鷄聲又喔咿強顏皃|鷽:山鵲又音學|葯:白芷也|腛:厚脂|𪑱:刑也又作剭|齷:齷𪘏齒相近|媉:好皃|𦯏:英蒻|龏:燭蔽|𠿟:誇聲也|䮸:馬腹丁鳴
MED女角;搦:持也女角切又女戹切六|掉:正也又杖弔切|䚥:屋角一曰調弓也|𧢺:+上同|搙:搵也|𧣺:握也
KED敕角;逴:遠也一曰驚走又作趠敕角切五|趠:+上同|晫:明也|踔:跛也|㪬:授也刺也㪬敊痛也敊丑六切
IED呂角;犖:駁犖牛雜色又卓犖也呂角切三|䃕:䃕確石相扣聲|𡁆:啅𡁆有才辯俗
jED胡覺;學:說文與斅同覺悟也斅今音效又姓出姓苑胡覺切九|确:磽确說文曰礊石也|嶨:山多大石又音㱿亦作礐|𥀣:𥀣𤿩|鷽:山鵲赤喙長尾知來而不知往|澩:涸泉|觷:治角之工|㿥:鳥白又胡沃切|翯:鳥肥澤
iED許角;㕰:怒聲許角切十|豿〈豞〉:豕聲|𩌊:急束|翯:鳥肥澤|嗀:歐吐左傳褚師聲子韤而登席公怒辭曰臣有足疾君將㱿之說文从口|𦰾:草聲|謞:讒慝|瀥:瀥瀑水涌|䤕:醋味|滈:水皃
TED測角;娖:辯也測角切八|䃗:䃗礫|𪘏:齒相近聲|娕:恭謹皃|擉:司馬彪注莊子云擉鼈刺鼈又音踔|齱:漢書云握齱急促也|𥭓:軬帶|齪:開孔具
#質
XVT之日;質:朴也主也信也平也謹也正也又姓漢書貨殖傳云質氏以洒削而鼎食注云理刀劒也之日切又音致十五|晊:大也|郅:郁郅古縣名又姓漢有郅都|桎:桎梏在足曰桎|櫍:椹行刑用斧櫍|蛭:水蛭博物志曰水蛭三斷而成三物|騭:䭸馬又書曰惟天陰騭下民傳云騭定也|劕:劕劑劵也長曰劕短曰劑周禮作質劑|銍:縣名|䑇:䑇䏷刀箭瘡藥|鑕:斧也|𡂒:野人之言|懫:止也|礩:柱下石也|侄:堅也又牢
cVT人質;日:說文曰實也太陽精不虧从口一象形人質切五|馹:驛傳也|衵:女人近身衣又女乙切|㠴:枕巾也|臸:到也
bVT神質;實:滿也誠也神質切一
LVT直一;秩:積也次也常也序也書曰望秩于山川直一切十二|紩:縫紩|帙:書帙亦謂之書衣又姓出纂文|袠:+上同|柣:門限|翐:翐翐飛皃|姪:兄弟之子又音迭|妷:+上同|豑:說文云爵之次弟也|𣗻:帆索|䟈:走皃|𢧤:大也
QVT息七;悉:說文云詳盡也息七切九|厀:說文曰脛節也|膝:+上同|蟋:蟋蟀蛬也|𧀬:牛𧀬又作𦸝本草作膝|𦸝:+上同|䊝:䊝𥻦聲|僁:僁𠋱動也|窸:從穴出也
hVX於悉;一:數之始也物之極也同也少也初也又虜三字姓後魏書一那婁氏後改爲婁氏於悉切三|弌:+古文|壹:專壹又合也誠也輩也醇也又虜三字姓後魏書云壹斗眷氏後改爲明氏
OVT親吉;七:數也親吉切十|漆:水名在岐又姓古有漆沈爲魯相何氏姓苑云今豫章人又漢複姓孔子弟子漆彫開|柒:+俗餘倣此|䣛:地名在齊|𪄭:鳥名|桼:膠桼說文曰木汁可以䰍物从木象形桼如水滴而下也經典通用漆|⿱芖雨:+俗|𣛺:木名可爲杖也|𦸓:草似蘇也|㯃:秦有㯃娥臺
BVH譬吉;匹:偶也配也合也二也說文云四丈也从八匸八揲一四俗作疋譬吉切四|鵯:鵯鶋鳥|𠯔:𠯔𠯔唾也|䏘:牝䏘
dVX居質;吉:吉利又姓出馮翊尹吉甫之後漢有漢中太守吉恪居質切八|趌:趌𧼨怒走也|狤:狂也|拮:拮据手病詩傳云拮据撠挶也又音結|䟌:走意|郆:郆成山|洁:水名|𤿠:黑𤿠
MVT尼質;暱:近也尼質切七|昵:+上同|衵:近身服|䵒:膠䵒|䵑:+上同|䘌:小蝱|㥾:愧㥾
lVT夷質;逸:過也縱也奔也說文曰失也从辵从兔兔謾訑善逃也夷質切十二|佚:佚樂|佾:八佾之舞佾行列也|溢:滿溢|軼:車過又突也又同結切|鎰:國語云二十四兩爲鎰又禮曰朝一溢米注謂二十兩曰溢|泆:淫泆|齸:廣雅云麋鹿受食處|劮:劮豫|欥:辝也|䭿:馬足疾|䳀:餔叔鳥也
eVX去吉;詰:問也責讓也去吉切四|蛣:蛣蜣蜣蜋又蛣𧌑蝎也|𩢴:馬色|趌:趌𧼨怒走也又音吉
iVX許吉;欯:笑也許吉切五|欪:訶也又丑律切|咭:笑又巨吉切|恄:怖也|㣟:行也
KVT丑栗;抶:打也丑栗切四|咥:笑也|眣:目不正也|跮:躌也又丑利切
IVT力質;栗:堅也又果木也漢書曰燕秦千樹栗其人與千戶侯等又姓漢長安富室有栗氏力質切十九|㮚:+上同說文作此|𣡷:+古文|慄:戰慄懼也|溧:溧水縣在宣州|䬆:䬆䬆暴風|𠞉:斷也削也|鷅:鶹鷅流離鳥|凓:凓冽寒風|篥:觱篥胡樂|麜:麕牡麌牝麜也|𨍫:車聲|瑮:玉之英華羅列皃|𦃊:蒸栗色綵|塛:塞也|搮:以手理物|䔁:草名|㗚:嘍㗚言不了也|㟳:山名
JVT陟栗;窒:窒塞也陟栗切又丁結切十二|挃:撞挃|庢:盩庢縣在京兆|銍:刈也說文曰穫禾短鐮也又古縣名在譙|秷:刈禾聲|𦤻:𠍹𦤻愛觸忤人也|㲳:手拔物也|㗧:㗧咄吐呵也|𪗻:齧聲|𨖹:近也|螲:螻蛄|𥎹:短也
PVT秦悉;疾:病也急也秦悉切十一|𤕺:+籀文|嫉:嫉妬楚詞注云害賢曰嫉害色曰妬|蒺:蒺蔾|㑵:廣雅云賊也|𧎿:爾雅云蒺蔾蝍蛆郭璞云似蝗大腹長角能食蛇腦亦作𧎿䖿|揤:揤拭|愱:愱毒苦也|槉:屋枅|𠹋:就𠹋|𧪠:語急
TWT初栗;㓼:割聲也初栗切四|𠞩:+上同|𪘧:齚也|䜉:謅䜉陰私語也
aVT式質;失:錯也縱也式質切三|室:房也易曰穴居而野處後世聖人易之以宮室釋名曰室實也人物實滿其中也周書曰黃帝始作宮窒呂氏春秋曰高元作宮室也|𩋡:刀𩋡
NVT資悉;堲:夏后氏堲周燒土葬也資悉切八|𡁶:鼠聲|唧:啾唧聲|㲺:水潛|𢪍:𢪍摘|𧉍:蜻蛚別名|蝍:蝍飛蟲又音即|楖:楖栗木名
DVH彌畢;蜜:蜂所作食山海經云穀城之上足蜂蜜之廬亦蟲名彌畢切九|𧖅:+上同|謐:靜也慎也安也|䤉:飲酒俱盡|榓:木榓樹名|𥁑:拭器|宓:安也默也寧也止也|淧:淧溢也|𥋱:𥋱𥋱不測也
AVH卑吉;必:審也然也說文曰分極也从八弋卑吉切二十七|畢:竟也說文作畢田罔也又姓出泰山本畢公高之後晉有畢卓|篳:織荊門也說文曰藩落也春秋傳曰篳門圭窬|蓽:+上同|韠:胡服蔽膝說文曰紱也所以蔽前也下廣二尺上廣一尺其頸五寸一命縕韠再命赤韠俗作鞸|㻫:+上同|䟆:漢書曰出稱警入言䟆顏師古曰警者戒肅也䟆止行人也|蹕:+上同|滭:滭沸泉出皃亦作觱見詩俗作㳼|㪤:盡也|鷝:鷝鴋鳥名白面青色|觱:觱篥或作篳說文作觱云羌人所吹角屠觱以驚馬也|珌:佩刀土飾|㓖:寒風|熚:火皃|𡠚:廣雅云母也|彃:射也|㮿:木名|縪:冠縫也說文止也|鮅:爾雅曰鮅鱒郭璞云似鯶子赤眼|饆:饆饠餌也|鏎:簡鏎爾雅曰簡謂之畢注謂簡札也俗從金|𠦒:弃糞器說文方干切箕屬|𡻞:道邊堂如墻也|𥀕:畫韋曰𥀕|𥛘:竈上祭|罼:兔罟
fVb巨乙;姞:姓一曰字史記云姞氏爲后稷元妃巨乙切五|佶:正也閑也|鮚:說文云蚌也漢律會稽獻鮚醬二升|趌:直行|狤:狤狂
CVH毗必;邲:地名在鄭又美皃毗必切二十一|比:比次又毗妣鼻三音|柲:偶也|馝:香也又虜複姓後魏書馝邗氏後改爲邗氏|苾:說文曰馨香也詩曰苾苾芬芬|䩛:車束|佖:有威儀也|鮩:魚名|駜:馬肥|坒:相連|飶:食之香者|綼:紷也又必覓切|鮅:魚名|怭:慢也|泌:水狹流又必媚切|𨠔:飲酒俱盡|䖩:黑蜂|吡:鳴吡吡亦作咇|𣢠:吹𣢠|咇:言不了|妼:女有容儀
kVr于筆;䫻:大風也于筆切五|𡿯:說文曰水流也|汩:+上同|蒁:草名|㧒:揘㧒擊皃
VVj所律;率:循也領也將也用也行也說文曰捕鳥畢也象絲罔上下其竿柄也俗作卛所律切十|帥:佩巾又將帥亦姓本姓師晉景帝諱改爲帥氏晉有尚書郎帥昺又所類切|蟀:蟋蟀|𧍓:+上同|䢦:先導|𠞩:割也斷也出埤蒼|𧜠:裾𧜠短衣|咰:咰飲酒皃|𠌭:行皃|𧗿:循也說文曰將衛也
YVT昌栗;叱:呵叱也又虜複姓九氏夏錄有將作大匠叱干阿利西魏有開府叱奴興南陽公叱羅協後魏官氏志有叱呂叱門叱利叱李叱列叱盧等氏亦虜三字姓周有侍中叱叱列龜其傳云代郡西部人昌栗切一
UWT仕叱;𪗨:齧聲仕叱切一
DVL美畢〖筆〗;密:說文云山脊也又靜也亦州名古姑幕城秦琅邪郡隋爲密州因水以名之又姓漢有尚書密忠又漢複姓三氏何氏姓苑云密茅氏琅邪人又有密革氏密須氏俗作密美畢切十|𡶇:山形如堂|蔤:荷本下白|宓:埤蒼云祕宓又音謐|滵:滵汩水流皃|沕:塵濁|樒:香木|𥄃〈㫘〉:不見皃|𪅮:鳥名|𥉴:𥉴𥉴不可測量也
CVL房密;弼:輔也備也房密切十|𢐀:+上同說文作此|㢸:-|𠡂:+並古文|䄶:䄶𥠈禾重生|𢘍:輔也|駜:馬肥|胇:胇肸大皃|邲:地名|佖:威儀備也
hVb於筆;乙:辰名爾雅云太歲在乙曰旃蒙亦姓前燕有護軍乙逸又虜複姓三氏後魏獻帝命叔父之胤曰乙旃氏後改爲叔氏前燕錄有高麗王乙弗利後魏有都督乙干貴又虜三字姓有乙速孤氏於筆切三|鳦:燕也說文本作乙燕乙玄鳥也齊魯謂之乙取鳴自呼象形本烏轄切或从鳥|亄:貪也
gVb魚乙;耴:聱耴魚鳥狀也魚乙切又女涉切七|聉:無知意也|㔎:斷也|𡿪:水流皃|圪:高皃|𦨇:舟行|𠡝:動𠡝𠡝
AVL鄙密;筆:秦蒙恬所造爾雅曰不律謂之筆韓詩外傳周舍爲趙簡子臣墨筆操牘從君之後伺君過而書之鄙密切九|潷:去滓|鉍:矛柄|柲:柄也|泌:泌瀄水流|𢴩:方言刺也亦作抋|咇:咇㘉多言|㻶:青白玉管天之所授|𨅗:走也
JVj徵筆;茁:草牙也徵筆切又鄒律莊月二切一
iVb羲乙;肸:肸蠁俗作肹羲乙切一
dVb居乙;暨:姓也吳尚書暨豔居乙切又臮既二音一
JVT丁悉;蛭:蛭蝚丁悉切又之日切一
iVn況必;獝:狂也況必切一
#術
bVj食聿;術:技術說文曰邑中道也又姓食聿切十一|述:著述說文循也又姓風俗通云魯大夫仲述之後也|秫:穀名|朮:+上同|沭:水名在琅邪今沭陽縣在海州|噊:爾雅曰危也又音聿|袕:爾雅袕謂之褮謂衣開孔也褮音熒|潏:爾雅曰小沚曰坻人所爲爲潏謂人力所作又音聿音譎|鱊:小魚名爾雅曰鱊鮬鱖鯞又音聿|驈:黑馬白髀又音聿|𧑐:𧑐蟥也又音聿
dVn居聿;橘:果名周禮云橘踰淮而北爲枳居聿切八|𦺖:草名|繘:汲綆又餘律切|𧾣:走意|𧽻:+上同|䤎:醬也|𦙮:姓也出韻譜|𣎛:月在乙也
PVj慈卹;崒:山高慈卹切四|踤:摧踤又觸也駭蹋也|誶:讓也|捽:把捽
lVj餘律;聿:循也遂也述也說文曰所以書也楚謂之聿吳謂之不律燕謂之弗秦謂之筆餘律切二十一|鴪:飛快|燏:火光|遹:述也自也一曰遵也|鷸:鳥名|驈:黑馬白髀又音述|繘:汲綆又音橘|𩙅:疾風|潏:水流皃|矞:說文曰以錐有所穿也一曰滿也|霱:霱雲瑞雲本亦作矞|𧑐:𧑐蟥也|䢖:行皃|芛:草木初生|欥:詞也|鱊:小魚名|噊:鳥鳴|䋖:䋖長|銉:針銉|𦒔:飛𦒔|𥎐:𥎐出
NVj子聿;卒:終也盡也子聿切又倉沒切又則骨切五|𣨛:終也|䱣:儵鮪別名|㰵:飲也玉篇云吮也|啐:啐律聲
QVj辛聿;䘏〈卹〉:分賑辛聿切十五|恤:憂恤|戌:辰名爾雅太歲在戌曰閹茂又滅也|訹:謏訹誘也謏蘇了切|珬:珂屬|𧪞:靜也又音盍|䳳:小鳥名|賉:賑賉|𣸃:水流𣸃𣸃|㖅:口鳴㖅㖅|𧊥:海蟀|銊:鋸聲|欰:鳴欰欰|𥚋:不能行也|𨜿:頹下
IVj呂卹;律:律呂又律法也呂卹切八|寽:持取今寽禾是|繂:繩船上用亦作𦆽|膟:腸閒脂說文曰血祭肉也又作𦝭|䔞:音譜云草子甲|葎:蔓草有刺|𥭐:竹𥭐以射鳥也|𠷈:鳴也亦作𠻜
KVj丑律;黜:貶下也亦作絀丑律切八|怵:怵惕|𧺶:走也|炪:火光|䟣:獸跡|㤕:憂心也又音窋|𤝞:獸名|欪:訶也又許吉切
JVj竹律;㤕:憂心也竹律切八|窋:物在穴皃|絀:縫也|䂐:短皃|㑁:+上同|逫:走皃|𡢑:面短皃|泏:水出皃
LVj直律;朮:藥名直律切三|𦬸:+上同|炢:煙出
YVj赤律;出:進也見也遠也赤律切又赤季切一
OVj倉聿;焌:火燒亦火滅也倉聿切一
SVj側律;𠭴:吳人呼短側律切二|𠮌:雞兒出殼聲
iVn許聿;䎉〈䎀〉:飛去皃許聿切四|怴:狂也|䬂:小風皃|𥄵:深目皃
#櫛
SWT阻瑟;櫛:梳也阻瑟切六|楖:+上同見周禮|瀄:瀄汨水聲|㘉:咇㘉|𥠈:䄶𥠈禾重生䄶音弼|擳:挃擳
VWT所櫛;瑟:樂器世本曰庖犧作瑟所櫛切六|飋:飋䫻風也|蟋:蟋蟀又音悉|蝨:蟣蝨淮南子云大廈成而燕雀相賀湯沐具而蟣蝨相弔俗作𧈲|璱:玉鮮絜皃今爲之璱璱者其色碧也|𦆄:𦆄𦆄色也亦作𩇣
UWT崱瑟;𪗨:齒聲崱瑟切一
#物
DXP文弗;物:萬物也又旗名周禮雜帛爲物說文曰牛爲大物天地之數起於牽牛故从牛勿文弗切九|勿:無也莫也說文曰州里所建旗也象其柄有三斿雜帛幅半異所以趣民故遽稱勿勿又作𣃦|𣃦:+上同|芴:土瓜|岉:崛岉高皃|伆:離也又武粉切|𨑥:遠也|昒:尚冥也又音忽|沕:沕穆微也
AXP分勿;弗:說文撟也分勿切二十|紱:綬也|黻:黼黻|綍:大索葬者引車|紼:+上同|芾:草木盛也|巿:說文曰韠也上古衣蔽前而已巿以象之天子朱巿諸侯赤巿大夫蔥衡从巾象連帶之形經典作芾|韍:+上同|不:與弗同又府鳩方久二切|𨚓:姓也漢有九江太守𨚓修|翇:說文曰樂舞執全羽以祀社稷也周禮作帗|柫:連枷杖打穀者出方言|𡗻:大也|髴:婦人首飾|冹:寒冰皃|帗:毳又音撥|𩖼:風皃|笰:輿後笰也|𤊸:熚𤊸鬼火說文作𤒓|甶:鬼頭
hXv紆物;鬱:香草又氣也長也幽也滯也腐臭也悠思也說文曰木叢生者又姓出姓苑紆物切十二|欝:+俗|灪:灪滃大水|爩:煙氣|𩚴:飴和豆也|黦:黃黑色也|𥘄:𥘄䃶小石|菀:藥草又音苑|尉:說文作尉从𡰥又持火所以申繒也亦姓古有尉繚子著書又虜複姓有尉遟氏其先魏氏之別尉遟部因而氏焉後單姓尉唐有將軍尉遟敬德又於魏切|熨:+火展帛也說文本作㷉見上注|蔚:草名又曰無子菣也亦州名春秋時屬晉後入趙秦滅趙爲代郡東魏置北靈丘郡周宣帝置蔚州也|𩰪:說文云芳草也
dXv九勿;𠀔:無左臂也九勿切又九月切十|孒:一同說文作此|𦁐:翟衣|厥:夏曰獯鬻殷曰鬼方周曰獫狁漢曰匈奴魏曰突厥出漢書音義又音蕨|屈:屈產地名出良馬亦姓楚有屈平又音詘|鶌:爾雅曰鶌鳩鶻鵃郭璞云似山鵲而小短尾青黑色多聲|趉:走皃|𧱝:豕𧱝土也|𠜾:剞𠜾曲刀|䠇:律䠇多力
eXv區勿;屈:拗曲亦姓又虜複姓屈突氏又羌複姓有屈男氏區勿切三|詘:辝塞|𧌑:蛣𧌑蟲
fXv衢物;倔:倔強衢物切九|䠇:足多力也|崛:山短而高|𡲬:短尾鳥|䘿:衣短|𡲗:短尾犬|堀:說文曰突也引詩曰蜉蝣堀閱|𧱝:豕𧱝地|掘:掘地
CXP符弗;佛:牟子曰漢明帝夢神人身有日光飛在殿前以問群臣傅毅對曰天竺有佛將其神也學記曰其施之也悖其求之也佛符弗切九|怫:怫鬱|坲:塵起|𡶒:山曲說文作岪山脅道也|咈:戾也|䞞:走皃|刜:斫也擊也|𣀣:玉篇云理也|炥:火皃
iXv許勿;䬍:疾風許勿切六|𩘐:+俗|欻:暴起|𠦪:疾也|㗵:訶㗵|烼:火煨起皃
kXv王勿;䬑:風聲王勿切六|𢯮:擲也|觱:羌人吹角|㧒:捏㧒|䁌:䁌䁌見|𢔥:行也
BXP敷勿;拂:去也拭也除也擊也敷勿切十二|𢂀:韜髮|嶏:崩聲|茀:草多|祓:除灾求福亦絜也又音廢|艴:淺色|刜:擊也斫也|乀:左戾曰乀|䭮:額前飾也|髴:髣髴亦作彷彿|彿:+彷彿俗|𧿳:跳也
gXv魚勿;崛:危崛山皃魚勿切一
#迄
iYf許訖;迄:爾雅云至也許訖切九|仡:壯勇皃又魚訖切|釳:乘輿馬上插翟尾者曰方釳釳鐵也廣三寸又魚訖切|肸:肸蠁又許乙切|忔:喜也|䒗:爾雅曰藒車䒗輿郭璞云藒車香草又音乞|䛥:語瞋聲|莔:吳王孫休長子字也|汔:水涸盡
dYf居乙〈乞〉;訖:止也居乙切五|吃:語難漢書曰司馬相如吃而善著書也|扢:摩也|暨:姓也吳尚書暨豔居乙切又臮既二音一|䰴:魚游
gYf魚迄;疙:癡皃魚迄切五|屹:屹崪山皃|圪:高土|𧆫:虎皃|仡:壯勇皃
fYf其迄;䞘:行皃其迄切二|𢇓:𧰙也
eYf去訖;乞:求也說文本作气音氣今作乞取之乞又虜複姓晉有乞伏國仁太元十年稱秦王於金城去訖切三|䒗:又許訖切|契:契丹夷名出字林
#月
gZv魚厥;月:范子計然云月者尺也者紀度而成數也王子年拾遺錄曰水精爲月魚厥切十一|刖:絕也斷足刑也又五刮切|跀:-|𧿁:+並上同見說文|軏:車轅端曲木也又五骨切|抈:折也|扤:動也又五骨切|枂:鞍枂|鈅:兵器|玥:神珠|𦘹:山也
CZP房越;伐:征也斬木也又自矜曰伐房越切十四|筏:大曰筏小曰桴乘之渡水|栰:+上同|罰:罪罰元命包曰网言爲詈刀詈爲罰罰之言网陷於害|閥:閥閱自序|垡:耕土|橃:木橃說文曰海中大船也|䑔:舂米|瞂:盾也或作𢧕|拔:爾雅云拔龍葛也似葛蔓生葉細莖赤也|茷:茷茂皃|藅:藆藅草|坺:地名|䣹:酒一䣹也
kZv王伐;越:墜也干也於也遠也走也逾也曰也揚也說文度也亦吳越又姓句踐之後又虜三字姓後秦錄有北梁州刺史越質詰歸王伐切十六|𨒋:說文踰也|粵:辝也于也|戉:說文曰大斧也司馬法曰夏執玄戊殷執白戚周左杖黃戊又作鉞|鉞:+上同|䋐:紵布說文曰采彰也一曰車馬飾|樾:樹陰|蚏:蟚蚏似蟹而小|曰:辝也於也之也|𥩡:竚立也|𡛟:輕也|璏:劒鼻玉|熭:暴乾|𣐋:木名|𧊎:螊𧊎蚌出魏書|泧:大水
dZv居月;厥:其也亦短也說文曰發石也又姓京兆人也漢賜衡山王妾厥氏居月切十九|氒:+古文|蹶:失腳又走也速也嘉也說文僵也一曰跳也亦作蹷又音橛|𨇮:+說文上同|𧽸:跳𧽸|𧼞:+上同|瘚:氣逆|劂:刻刀|蕨:蕨菜|蟨:獸名走之則顛蛩蛩前足高不得食而善走蟨常爲蛩蛩取食蛩蛩負之而走也|蟩:蟩蜉蟲|橜:杙也又其月切|𥕲:發石|𠢤:強力|欮:發也|撅:撅撥物也|鱖:魚名|孒:短也|𠄌:說文曰鉤識也从反𠄌象形
hZv於月;𡡕:嬄𡡕婦人皃於月切四|𩚴:飴和豆又作𩜌說文作𧯡|噦:逆氣又乙劣切|黦:黃黑色說文作𪑲黑有文也
fZv其月;𧤼:以角發物其月切十三|鷢:白鷢一名鸉似鷹尾上白善捕鼠也|橜:說文杙也一曰門梱亦作橛|撅:採撅亦樗蒲三采名|蹶:又音厥|掘:穿也|赶:舉尾走也|憠:強也|𨬐:磨𨬐|䞷:行越䞷也|𣖬:𣖬株山名|𩪜:尾本|𠄌〈亅〉:說文曰鉤逆者謂之亅象形
eZv去月;闕:門觀也廣雅曰象魏闕也釋名曰闕在門兩旁中央闕然爲道也又失也過也不供也又姓出下邳漢有荊州刺史闕翊去月切三|㵐:水名在義陽|𦁐:𦁐狄衣周禮作闕禮記作屈
AZP方伐;髮:頭毛也說文根也又姓漢有東海人髮福治詩又有不毛之地莊子謂之窮髮方伐切六|𩠖:+說文上同|𩑛:+古文|發:發起又舒也明也舉也闋也揚也說文曰䠶發也|颰:疾風|冹:寒水又音弗
DZP望發;韤:足衣漢張釋之與王生結韤望發切五|韈:-|襪:+並上同|𥄎:舉目使人|㒝:㒝羯東北夷名似高麗
iZv許月;䬂:小風許月切六|䟠:走皃|泧:水皃|狘:獸名又走皃|䎀:飛皃|㞽:山皃
hZf於歇;謁:請也告也白也又姓風俗通云漢有汝南太守謁渙於歇切五|閼:爾雅云太歲在卯曰單閼又於葛於連二切|暍:傷熱亦作㷎𤸎|𢉥:說文曰屋迫也|黦:色壞也又於月紆物二切
iZf許竭〖謁〗;歇:氣洩也休息也又竭也許竭切五|蠍:螫蟲人|猲:猲獢短喙犬也|𤢔:+上同|𦪬:𦪬艎大船
dZf居竭〖謁〗;訐:面斥人以言論語注云訐謂攻發人陰私也居竭切又居列切六|𧼨:走皃|羯:犗羊|揭:揭起說文曰高舉也|𢶆:+俗|鍻:金鍻
fZf其謁;𢷒:擔𢷒物也本亦作揭其謁切五|揭:+上同|竭:盡也|碣:碣石海中山名今爲碑碣字李斯造|楬:表楬閥閱自序名
BZP拂伐;㤄:恨怒拂伐切一
gZf語訐;钀:馬勒旁鐵語訐切一
#沒
DaD莫勃;沒:沈也又虜三字姓有沒路真氏出後魏書莫勃切六|歿:死也說文終也又作歾|𤣻:玉名|𩑦:內頭水中又烏沒切|𠬛:說文曰入水有所取也|莈:草
Faj土骨;｛𣅝｝【「突」之音，「𠬛」（明一魂入）之訛字】:入水又出皃土骨切一
daj古忽;骨:說文曰肉之覈也尸子曰徐偃王有筋無骨亦見史記又姓古忽切十六|縎:縎結|鶻:鶻鳩又搰猾二音|滑:滑稽謂俳諧也|䮩:䮩𩢎獸出北海|啒:憂也|淈:說文濁也一曰滒泥又水出皃|汨:汨沒|愲:心亂|蓇:不實草|尳:膝病|㾶:+上同|榾:枸榾木也|䓛:刷也或從竹|扢:摩也|㒴:出也
CaD蒲沒;勃:卒也又姓世本宋右師之後又梁武帝改豫章王綜姓勃氏蒲沒切二十三|渤:渤澥海名又水皃|𩣡:𩣡馬獸名似馬牛尾一角又音雹|𩱚:說文曰炊釜溢也|餑:麵餑|𡋯:塵起|馞:大香|悖:逆也又音背|䄶:䄶稡禾所秀不成聚向上皃|郣:郡名|浡:浡然興作|𣭷:𣭷㲞毛短|𢠜:昬亂|㪍:㪍卒旋放之皃|誖:言亂|㶿:煙起皃|桲:榲桲果似樝|孛:星也又怪氣|艴:艴然不悅|挬:拔也|脖:胦臍|𦸦:蘩母|鵓:鵓𪅄鳥名
Eaj當沒;咄:呵也當沒切四|柮:榾柮木頭又五栝切|𩢎:䮩𩢎獸出北海|𩨳:鳥鳴豫知吉凶也
Faj他骨;宊〈突〉:出皃他骨切六|梲:大杖也又音拙|𠫓:不孝之子說文曰不順忽出也篆文从到子|𡿮:+說文同上或从到古文子|㥆:㥆忽也悵也說文肆也|䠈:蹂也𨁸䠈前不進也
Gaj陀骨;突:觸也欺也說文曰犬从穴中暫出也一曰滑也陀骨切十四|揬:搪揬|腯:說文曰牛羊曰肥豕曰腯|鼵:鳥鼠同穴其鳥曰䳜其鼠曰鼵鼵如人家鼠而短尾|葖:爾雅曰葖蘆萉郭璞云萉宜爲菔蘆菔蕪菁屬紫華大根俗呼雹葖|鶟:鶟鶘鳥名似雉青身白首|堗:竈堗漢書作突云曲突徙薪亡恩澤|𦩤:艒𦩤釣船|鈯:鈍也又小刃也|𦔅:耕禾閒也|𣔻:瑣植又傳也|凸:凸出皃|𡿮:說文本他忽切義見上文|鍎:覆鍎
haj烏沒;𩑦:內頭水中烏沒切九|膃:膃肭肥|殟:心悶|嗢:咽也又虜複姓後魏書有嗢盆氏又虜三字姓嗢石蘭氏|䯉:說文曰咽中息不利也本一滑切|榲:榲桲果似樝也|搵:手撩物皃|淴:水出聲|馧:馧馞大香
iaj呼骨;忽:倏忽又滅也忘也輕也又一蠶爲一忽十忽爲一絲呼骨切十七|昒:尚冥也|㾁:狂病又音欻|匫:古器|寣:睡一覺|笏:一名手板品官所執天子以玉諸侯以象大夫魚須文竹士木可也釋名笏忽也有事書其上以備忽忘|䩐:急擷也擷呼結切|㫚:說文曰出气詞也篆文本作㫚象气出形|𨑥:遠也|啒:憂皃|𣓗:高皃|㦌:寢熟|𦁕:微也|𢑢:豕屬|惚:恍惚亦作忽|䬍:疾風皃|𤶘:睡多
gaj五忽;兀:高皃又姓後漢改樂安王元覽爲兀氏五忽切十六|扤:搖動|杌:樹無枝也|屼:𡼿屼禿山皃又五屼山名在犍爲|矹:硉矹不穩皃|䦍:䦍括也又云㚔者|鼿:鼻也|𦨉:說文曰船行不安也|䑢:+俗|𠨜:𦤞𠨜不安也|㽾:說文曰病也|𤴰:+俗|軏:輗軏又音月|𧈭:蛤蟹|刖:刮刖又音月|𦬂:艾𦬂
BaD普沒;䪬:按物聲或作𥩾普沒切五|昢:明旦日出皃|哱:吹氣聲|㛘:㛘乳女字|馞:香皃
Iaj勒沒;𠀽:筩射勒沒切五|𨁸:𨁸䠈前不進也|硉:硉矹|𥓎:𥓎矹崖狀|㪐:㪐㩿不穩又不利也
eaj苦骨;窟:窟穴苦骨切十五|顝:大頭皃|泏:漚池|𩑔:白禿|矻:用心矻矻|堀:宋玉云堀堁揚塵又音掘|𧷎:說文曰囚突出也本胡八切|㧾:擊也|圣:汝潁閒謂致力於地曰圣|㩿:㪐㩿不穩|𡑣:土塞|䯇:力作|𡼿:𡼿屼禿山皃|𥌄:目突𥌄|胐:胐臀俗又作𦜇
Haj內骨;訥:謇訥內骨切五|㕯:㕯口又女滑切|肭:膃肭|抐:內物水中|𣧍:殟𣧍
Qaj蘇骨;窣:勃窣穴中出也蘇骨切七|𪌯:麥屑|𪍛:+上同|㲞:𣭷㲞毛皃|𪖶:鼻鳴|𪅄:鵓𪅄鳥|屑:動進皃說文本先節切
Oaj倉沒;猝:倉猝暴疾也倉沒切五|卒:急也遽也又子沒切又將律切|𣨛:亡也|𢪃:摩也|𥾛:索也
Paj昨沒;捽:手捽也昨沒切六|椊:椊杌以柄內孔|𪘧:齚也|䚝:角始生也|崒:崒屼山皃|𩩠:小骨
jbT下沒;麧:麧糏漢書云食糠麧下沒切五|𥝖:秳也舂粟不潰也|齕:齧也又胡結切|紇:絲下也又孔子父名又虜複姓三氏北齊開府紇奚永樂又有紇于氏紇骨氏又虜三字姓後魏有賊師紇豆陵伊利又胡結切|淈:淈泥又古忽切
jaj戶骨;搰:掘地也戶骨切十|扢:摩也|𣝗:果子𣝗也出聲譜|𦗣:耳聲|｛𦖼｝【澤存堂本衍字】:耳聲|𢪏:牽物動轉|鶻:鳥名鷹屬又骨猾二音|尳:膝病|㨡:手推也|𡰅:𡰅露出見字林|滑:滑亂也出列子
Naj臧沒;卒:說文隷人給事者衣爲卒卒衣有題識者臧沒切又將聿切三|倅:百人爲倅周禮作卒|稡:䄶稡
#曷
jcT胡葛;曷:何也胡葛切十一|褐:衣褐說文云編枲韈也一曰短衣|毼:毛布|鶡:鳥似雉也鬬必至死|蝎:蟲名爾雅曰蝤蠐蝎又曰蝎桑蟲|餲:餅名|䫘:𩑵䫘健也又音𠿒|𩩲:𩩲骬肩骨|骱:骨堅|㮫:木轉皃|鞨:靺鞨蕃人名出北土
icT許葛;䫘:𩑷䫘健也許葛切八|𠿒:訶也|喝:+上同|猲:短喙犬又恐也又音歇|𦤦:犬臭氣|㿣:白色|暍:熱皃|𩡔:香氣又呼蓋切出字林
EcT當割;怛:悲慘也當割切十|𢛁:驚𢛁|妲:妲己紂妃|呾:相呵|炟:火起|䵣:莫䵣縣在五原|狚:獦狚獸名似狼而赤出山海經|笪:竹䉬|𦬹:蕈𦬹|靼:柔革也又之列切
FcT他達;闥:門內他達切十三|㒓:𠇱㒓|撻:打撻|躂:足跌|澾:泥滑|獺:水狗|䲚:魚名|𣥂:文字音義云蹈也從反止|羍:小羊也亦作𦍐|𦍒:+上同|達:挑達往來皃又唐割切|汏:汏過|噧:多言也
hcT烏葛;遏:遮也絕也止也烏葛切十一|齃:鼻齃|頞:+上同|堨:擁堨|閼:止也塞也又於連切|胺:肉敗臭論語作餲食臭也|餲:食傷臭又於介於罽二切|靄:雲狀又於蓋切|咹:止語|𠥜:大呼用力|𢉥:屋迫
IcT盧達;剌:僻也戾也盧達切十六|揧:研破|辢:辛辢|䓶:䓶蒿|瘌:癆瘌不調|攋:撥攋手披也|糲:麤糲|癩:疥癩又音賴|𢈠〈𢉨〉:廣雅曰庵也亦獄室也|轢:車轔著又歷洛二音|𢃴:拂著|䶛:齧聲|㻝:玉名|𥈙:目不正|楋:木名|蝲:蝲蟽
ecT苦曷;渴:飢渴又虜複姓二氏後魏書渴侯氏後改爲緱氏渴單氏後改爲單氏亦虜三字姓後魏書北方渴燭渾氏後改爲朱氏苦曷切八|㵣:+古文|𤸎:內熱病也|䳚:䳚鴠|嵑:嵑嶭山皃|磕:石聲|䯋:肩髆|䅥:禾長也
GcT唐割;達:通達亦姓出何氏姓苑又虜複姓三氏後魏獻帝弟爲達奚氏又達勃氏後改爲襃氏周文帝達步妃生齊煬王憲唐割切二|薘:馬舄草名
PcT才割;嶻:嶻嶭山名在右扶風才割切又才結切四|囋:嘈囋鼓聲或作𠱥|囐:+上同|㩵:擊也
gcT五割;嶭:五割切又五結切十三|䡾:車載高也|屵:高山狀|枿:伐木餘枿|𣡌:頭戴皃說文曰伐木餘也|櫱:+上同書作蘖|𣎴:+古文從木無頭|𠱥:毀讀曰𠱥|㩵:擊也又才割切|𠲗:𠲗𠲗㗴㗴戒也說文曰語相訶距也|歺:說文曰𠛱骨之殘也凡從歺者今亦作歹|頇:無髮|齾:獸食之餘曰齾
dcT古達;葛:葛藟廣雅云苑童寄生葛也一名寓木又名寄屑亦姓後漢有潁川太守葛興古達切十|䈓:䈓䉈桃枝竹名|獦:獦狚獸也|割:剝也害也斷也截也|𩢛:馬走疾也|𠣏〈匃〉:乞也亦作丐又音蓋|輵:轇輵戟形也又轇輵驅馳皃|𨞛:鄉名在南陽|𥢸:禾長也|㵧:水名又㶀㵧波勢也
QcT桑割;躠:跋躠行皃桑割切九|薩:釋典云菩薩菩普也薩濟也能普濟眾生也|摋:抹摋公羊傳曰宋萬臂摋仇牧碎首何休云側手曰摋|𥻦:放也若𥻦蔡叔是也說文曰䊝𥻦散之也|𠱡:音變|攃:攃攃聲|䉈:䈓䉈桃枝竹也|𦼧:失𦼧|𨐖:俗云𨐖辢
OcT七曷;攃:足動草聲七曷切三|䌨:縠屬出淮南子|礤:麤礤
HcT奴曷;捺:手按奴曷切三|𤷈:痛也|䖧:蠚螫
jcT矛〈予〉割;䔾:菜似蕨生水中矛割切一
#末
DcD莫撥;末:木上也無也弱也遠也端也亦姓姓苑云本姓秣氏後去禾又虜三字姓後燕錄襄城公末那樓雷莫撥切二十七|昩:星也易曰日中見昩案音義云字林作昧斗杓後星王肅音妹|𩑷:𩑷䫘健也|䀛:遠視又不正視又莫拜切|䴲:麪也|𨣱:醬也|䬴:馬食榖也|秣:+上同|𥬎:捕鰌竹器|靺:靺鞨蕃人出北土|韎:韎韐大帶|苜〈𥄕〉:說文曰目不正|粖:糜也又亡結切|𩱷:+上同|𥽘:米和細屑|䱅:魚名|眜:目不明也|抹:抹摋摩也|妺:妺嬉桀妃|𠇱:𠇱㒓肥皃又西夷樂名|𢗿:忘也|𡊉:壤也|瀎:塗拭|𩿣:鳥名|沫:水沫一曰水名在蜀又武泰切|𦫕:𦫔𦫕色不深也|袜:袜肚
gcj五活;枂:去樹皮又柮枂柱頭木五活切一
Pcj藏活;柮:藏活切一
AcD北末;撥:理也絕也除也北末切十六|癶:足剌癶也|袚:蠻夷蔽膝|茇:蓽茇|鉢:鉢器也亦作盔顏師古注漢書曰盔食器也|盋:+上同|䳊:鳥名又音拔|鱍:魚掉尾也|䢌:急走|𩯌:𩯌䰖多鬢皃|襏:襏襫蓑雨衣也|帗:一幅巾|㤄:意不悅皃|𦪑:大船名|驋:馬怒|筏:箄筏
NcT姊末;䰖:姊末切六|拶:逼拶|㳨:㳨濺|𠛱:剌𠛱不淨也|𨀨:蹙𨀨行皃出新字林|㵶:水湍頭起
dcj古活;括:檢也結也至也古活切二十一|活:水流聲又乎括切|𣽅:+上同|髺:結髺|檜:木名柏葉松身又工外切|栝:+上同見書|聒:聲擾|䒷:說文曰䒷蔞果臝也|𦸈:+𦸈𧁾同上|鴰:鶬鴰韓詩云孔子渡江見之異眾莫能名孔子嘗聞河上人歌曰鴰兮鶻兮逆毛衰兮一身九尾長兮鶬鴰也|萿:爾雅曰萿麋舌郭璞云今麋舌草春生葉有似於舌|适:疾也|銛:說文曰斷也|佸:會計曰佸|頢:小頭皃|劊:斷也|葀:菝葀瑞草|䯏:骨端|懖:愚懖無知說文曰善自用之意也引商書曰今汝懖懖|𦗾:+古文|筈:箭筈受弦處
ecj苦栝;闊:廣也遠也疏也苦栝切六|蛞:蝦蟆子名|筈:箭筈又音栝|适:疾也又音栝|䟯:蹵䟯|𤫵:瓜𤫵
jcj戶括;活:不死也又水流聲戶括切八|𣽅:水流聲|䄆:祠也|越:鄭玄云瑟下孔又云翦蒲爲席又音粵或作趏|鬠:以組束髮|佸:佸會|秳:舂榖不潰也|姡:姡靦也又音頢
Gcj徒活;奪:左傳曰一與一奪徒活切八|𡙜:+上同|敓:強取也古奪字古周書曰敓攘矯虔亦姓|脫:肉去骨亦姓出姓苑又土活切|挩:解挩|莌:活莌草名生江南高丈許大葉莖中有瓤正白|痥:馬脛傷也|鮵:爾雅曰鰹大鮦小者鮵
icj呼括;豁:豁達呼括切八|𧯆:+上同|奯:大開目也|濊:水聲|𤃴:+上同|泧:瀎泧|𣁳:舀水|眓:說文曰視高皃
hcj烏括;斡:轉也烏括切九|焥:火煙出|䩊:目開皃|捾:捾取也|𣁳:+上同|嬒:方言云嬒可憎也或作懀又烏外切|䁊:目深黑皃|睕:小嫵媚也|𥄗:說文云捾目也
Ncj子括;繓:結繓也子括切三|撮:撮挽牽也又七活切|攥:手把
BcD普活;鏺:兩刃刈也普活切說文又讀若撥十三|𢯸:芟𢯸|𨂩:蹋草聲|㧊:推㧊|䣪:酒氣|𨡩:𨡩醅酘酒|𣸍:水𣸍|𥄱:目𥄱眜不明皃|鱍:魚掉尾又音撥|𧘟:衣袂也|𦫔:𦫔𦫕無色|䍨:牯羊|𠷑:謶𠷑人言
Fcj他括;侻:侻可也一曰輕他括切五|挩:除也誤也遺也又解挩或作脫|脫:骨去肉又徒活切|莌:又徒活切|梲:大棒亦木梲又音拙
Icj郎括;捋:手捋也取也摩也或作寽郎括切五|𠜖:削𠜖也|蛶:蚵蛶蟲又音劣|㸹:駁㸹|㭩:木名又音劣
Ecj丁括;掇:拾掇也丁括切八|剟:削也擊也|鵽:鵽雀又當刮切|腏:挑取骨間肉也|祋:祋祤縣名又都外切|咄:又都骨切|裰:補裰破衣也|敠:敠敠知輕重也又敠𣀒食不喚自來
Ocj倉括;撮:六十四黍爲圭四圭爲撮撮手取倉括切二|襊:緇布冠詩作撮
CcD蒲撥;跋:跋躠行皃又躐也蒲撥切二十五|䟛:行皃|𧺡:+上同|𧺺:+上同|魃:旱魃|𢇷:舍也|軷:將行祭名|䣮:酒氣|馛:香氣|炦:火氣|颰:風皃|癹:除草說文音鏺|妭:鬼婦文字指歸云女妭禿無髮所居之處天不雨說文曰婦人美皃|犮:犬走皃|䚨:弋鳥具說文音廢|拔:迴拔又虜複姓三氏後魏有都督拔略昶出賀拔勝傳又有夏州剌史拔也惡蚝官氏志有柯拔氏又虜三字姓後魏書拔列蘭氏後改爲梁氏又蒲八切|胈:夏禹治水腓無胈脛無毛韋昭云胈股上小毛也|鈸:鈴鈸|䳊:鳥名似鳧|䮂:䮂䮧蕃中馬也|菝:菝葀瑞草|坺:一臿土也又音伐|𩃶:雲氣|茇:草木根也|䯋:肩髆
#黠
jeT胡八;黠:黠慧也又堅黑也胡八切四|𩪲:齧聲|䕸:麻莖|䦖:門聲
SeT側八;札:簡札釋名曰札櫛也編之如櫛齒相比也又牒也署也側八切六|㱜〈𣧖〉:癘疾|蚻:小蟬|紮:纏弓弝也|𩿤:鳥雜蒼色|扎:扎拔也出家語
CeD蒲八;拔:拔擢又盡也蒲八切又蒲撥切三|菝:菝𦸉狗脊根可作飲|𥎱:𥎱䂒短人
eeT恪八;𤫶:勁也恪八切十二|擖:說文刮也一曰撻也|劼:用力又固也慎也勤也|鬜:虎鬜也|𩮁:+上同|㓞:巧㓞|㓤:剝㓤|硈:石狀說文堅也一曰突也|𦸉:菝𦸉草|䂒:𥎱䂒短人|咭:鼠鳴|𢼣:擊也
jej戶八;滑:利也亦州名春秋時爲衛國秦爲東郡後魏以東郡屬司州周改爲滑州因滑臺以爲名又姓風俗通云漢有詹事滑典又音骨滑稽也戶八切八|猾:狡猾書傳云猾亂也|䱻:魚名鳥翼出入有光音如鴛鴦見則天下大旱出山海經|磆:磆石藥|螖:蟚螖似蟹而小|䴳:麴名|𧽌:走𧽌|鶻:鶻鳩又音骨搰
AeD博拔;八:數也博拔切十|𩡩:馬八歲|朳:無齒杷也|捌:+上同|扒:破聲|㺴:玉名|䤢:金類|哵:哵哵鳥聲|玐:玉聲|釟:治金
Jej丁滑;窡:說文曰穴中見也丁滑切五|𠿡:說文曰口滿食|娺:婠娺好皃|鵽:黃雀|聉:無所聞也
hej烏八;婠:烏八切六|𣁳:𣁳取物也|嗢:咽也又烏沒切|䯉:說文曰咽中息不利也|穵:手穵爲穴|嗗:飲聲
Mej女滑;豽:獸名似狸蒼黑無前足善捕鼠說文作貀女滑切四|貀:+上同|㕯:言逆下也又女骨切|肭:膃肭肥皃
TeT初八;䶪:齒利又磣䶪初八切七|䕓:草䕓|察:監察也諦也知也至也審也案說文云覈覆也詧言微親詧也今通用亦姓出何氏姓苑|詧:+上同|𣘤:木名|𥉻:視𥉻|𩴳:羅𩴳鬼亦作𩲺
dej古滑;劀:說文曰刮去惡創肉也周禮曰劀殺之齊古滑切三|𠟽:+俗|鱊:魚名
deT古黠;戛:揩也常也禮也說文戟也古黠切十八|扴:指扴物也|圿:垢圿|稭:說文曰禾稾去其皮祭天以爲席也|鴶:鴶鵴鳲鳩|楔:櫻桃又先結切|秸:秸稾|骱:䯦骱小骨|鞂:草鞂|砎:礣砎小石|忦:恨也|嘎:嘎嘎鳥聲|𠜵:刮也利也|𪃈:𪃈𪈟鳥又音絜|袺:執衽又音結|㮖:鼓也|磍:輵磍搖目吐舌又感怨皃|頡:漢書有頡羹侯
heT烏黠;軋:車輾烏黠切十|圠:山曲|揠:拔草心也|嫼:嫉怒|䝟:䝟貐獸名食人迅走|猰:+上同|穵:說文云空大也|𥈔:目相戲皃|䰲:䱀䰲魚名|窫:窫窳國名
VeT所八;殺:殺命說文戮也所八切七|煞:+俗|鎩:鳥羽病又長刃矛也|𣻑:水也|帴:二幅|蔱:莁荑|榝:似茱萸而實赤又山列切
DeD莫八;㑻:㑻傄健皃莫八切七|䀣:惡視|齂:氣息|䯦:䯦骱小骨|𪒜:黑也|睰:視睰|礣:礣砎小石
iej呼八;傄:呼八切二|䀨:視也埤蒼云怒視皃
MeT女黠;痆:瘡痛女黠切三|𤷈:+上同|𧞍:奴人衣
gej五骨〈滑〉;𦤙:屈也五骨切三|聉:無知之意|𦘍:無耳吳楚語也
eej口滑;䯇:力作也口滑切又音窟一
BeD普八;汃:西極水名普八切四|𪗔:齒聲|𥐙:石破聲|𨋐:車破聲
Sej鄒滑;茁:草初生鄒滑切一
#鎋
jdT胡瞎;鎋:車軸頭鐵胡瞎切十五|舝:+上同出說文|轄:+上同說文車聲也一曰轄鍵也|𪗾:齒聲|鶷:鶷𪆰鳥名似伯勞而小|砎:礣砎硬也礣慕轄切|𧕱:螻蛄別名|𤪍:石似玉也|𦵯:野蘇|𧷎:囚突出也|縖:束物也|𩝛:食飽|𥰶:拾𥰶|𠢆:用力|𢮟:手𢮟
hdT乙鎋;𪆰:乙鎋切五|䦪:門扇聲|𡇼:駱駝鳴也|呾:相呼聲又當辢切|劜:勜劜屈強也
gdT五鎋;齾:器缺也五鎋切四|聐:聐顡無所聞也|𩮝:禿𩮝|𡿖:山中絕皃
TdT初鎋;刹:刹柱也初鎋切二|䓭:掃地惡草
edT枯鎋;𥴭:木虎止樂器亦名敔也枯鎋切四|楬:+上同見禮|磍:剝也|趏:走皃
idT許鎋;瞎:一目盲亦作𥈎許鎋切四|𪗾:齒堅聲|𩮂:𩮂𩮁禿皃|㔠:力作㔠㔠
KdT他鎋;獺:獸名他鎋切又他達切一
ddj古䫄;刮:刮削古䫄切五|鴰:鶬鴰鳥毛逆九尾又音括|劀:利也又古滑切|䄆:禳祠名|趏:走皃又枯鎋切
jdj下刮;頢:短面皃也下刮切七|𤁪:言不了又不淨|𦧠:繒細|敌:盡皃|舌:塞口說文作𠯑話栝之類从此|姡:面醜|咶:息也
Kdj丑刮;䫄:䫄頢強可皃丑刮切二|𤁫:𤁪𤁫
Jdj丁刮;鵽:爾雅曰鵽鳩寇雉郭璞云鵽大如鴿似雌雉鼠腳無後指歧尾爲鳥憨急羣飛出北方沙漠地丁刮切又丁括切三|窡:穴中出皃|錣:策端有鐵
Vdj數刮;刷:刷拭也數刮切又所劣切一
gdj五刮;刖:去足亦槷刖危之皃五刮切又音月四|䎳:說文曰墮耳也|㱚:獸食殘皃|䚴:訶也
Tdj初刮;䵵:黑也初刮切二|㔍:斷也又叉芮切
DdD莫鎋;𥗥〈礣〉:礣砎莫鎋切四|帓:帓帶|帕:帕額首飾|㩢:打㩢
Mdj女刮;妠:婠妠小兒肥皃女刮切三|𤬷:𤭧也亦作𤬼|袦:下人帶襦名
AdD百鎋;捌:方言云無齒杷百鎋切二|㭭:木名
ddT古鎋;𪈟:𪃈𪈟鳥名似鳧古鎋切四|擖:刮聲也又揵也架也折也|𩮁:禿皃|猰:雜犬
UdT查鎋;𨰉:秦人云切草查鎋切三|耫:農具也|㳐:㳐㳐水流也
JdT陟鎋;哳:嘲哳鳥鳴也陟鎋切四|𢧖:𢧖好出證俗文|𧶇:𧶇貨也|眣:目露皃出聲類
MdT而轄（鎋）;𩭿:細毛也而轄切一
#屑
QfT先結;屑:動作屑屑又清也敬也顧也勞也說文作㞕先結切十二|楔:木楔|揳:㩢揳不方正也|𨆳:蹩𨇨旋行|榍:木名說文限也|糏:米麥破也|僁:動草聲又云鷙鳥之聲又僁僁呻吟也亦作𠋱|偰:㒝偰淨也|㴽:瀎㴽水皃|𦵱:草名|𦞚:臆中脂|㨝:揲㨝
OfT千結;切:割也刻也近也迫也義也說文折也千結切八|㗫:小語|𪙌:𪙌齒也|竊:盜也又淺也|柣:爾雅曰柣謂之閾又音秩|沏:水聲|䟙:䟙跌|詧:說文曰言微親詧也又音察
dfT古屑;結:締也古屑切十五|絜:說文曰麻一耑也|潔:清也經典用絜|䥛:鎌別名也|鍥:+上同|桔:桔梗|𣚃:𣚃槔汲水具也|𧾯:走皃|𪃈:𪃈𪈟鳥名𪈟古轄切|袺:詩傳云執衽曰袺|拮:手口共有所作詩曰予手拮据|狤:狤𤟎獸名|魝:割治魚也|𡔢:頭傾皃|𧍩:蠸𧍩蟲名
NfT子結;節:操也制也止也驗也說文曰竹約也子結切十三|𢎛:說文曰瑞信也凡從𢎛今作卪|癤:瘡癤|蝍:蝍蛆蜈蚣又音即|楶:屋梁上木|㵶:小灑|㸅:燭餘|𡴺:高山皃|䰏:說文曰束髮少小也|䲙:魚名|幯:幯拭|𠬝:說文治也本房六切|𧞛:小衣
ifj呼決;血:釋名曰血濊也出於肉流而濊濊也呼決切十二|𥅧:𥉺𥅧惡皃|䆷:穿皃|䆝:+上同|䦑:𨴒䦑無門戶也|泬:泬寥空皃|疦:瘡裏空也又音玦|瞲:驚視皃|決:莊子云決起而搶榆枋決小飛皃|䛎:怒呵|䒸:草皃|坹:穴也
efj苦穴;闋:終也苦穴切四|湀:爾雅云湀闢流川又揆奎二音|缺:器破|𨴒:𨴒䦑無門戶也
dfj古穴;玦:珮如環而有缺逐臣賜玦義取與之訣別也古穴切二十六|潏:泉出皃又水名在京兆又音聿|䀗:目患|譎:譎詐|訣:訣別|𧤾:環有舌也|觼:+上同出說文|鐍:亦同又扃鐍出莊子|駃:駃騠良馬生七日超母也|𦯊:𦯊明菜花黃|芵:+上同|赽:馬疾行也|鴂:鶗鴂鳥名關西曰巧婦關東曰鸋鴂春分鳴則眾芳生秋分鳴則眾芳歇|鈌:剌也又乙穴切|𣬎:獸名似狸|決:流行也廬江有決水出大別山人斷也破也俗作决|觖:觖望怨望也又羌瑞切|騤:爾雅馬回毛在背曰騤𩧉𩧉音光亦作闋廣|㭈:椀也又小盂也|疦:說文𤺉也|蚗:蛥蚗蟪蛄蟲名|趹:足疾|憰:憰妄語也|𧝃:衣袖|䏐:孔䏐|抉:縱弦彄也
jfj胡決;穴:窟也舟穴山名鳳皇所出胡決切四|坹:空深皃|䋉:說文縷一枚也|袕:鬼衣又長衣也
hfj於決;抉:抉出於決切六|䆕:穿皃|妜:娟也|焆:火光也|𥈾:目深皃|䆢:說文曰深抉也
GfT徒結;姪:姪娣公羊傳云兄之子徒結切三十五|眣:目出|昳:日昊|胅:骨胅|凸:高起|垤:蟻封又曰冢前闕也|耋:老也八十爲耋亦作耋|迭:遞也更也道也|跌:跌踼又差跌也|絰:縗絰|驖:馬赤黑也|嵽:嵽嵲高山|軼:車相過又音逸|䭿:馬行疾也|𨳺:䦖𨳺鄭城門也左傳作桔柣|瓞:爪瓞|咥:笑也又齧也易云履虎尾不咥人亨又火至丑栗二切|墆:貯也止也|戜:利也又國名在三苗國東出山海經|苵:爾雅曰蕛苵郭璞云蕛似稗布地生穢草|镻:爾雅镻蝁注云蝮屬大眼最有毒今淮南人呼蝁子|䳀:爾雅云鴩餔叔|荎:刺榆又音治|𪗻:齧堅聲又竹一切|𢲼:擿也|恎:惡性|詄:忘念|摕:捎取|𪀒:鳥名|𠽧:齧堅|𡼄:𡼄𡸢山兒|泆:泆蕩|𥑇:砲𥑇|趃:大走|㦅:㦅㦅不自安也
FfT他結;鐵:說文云黑金也神異經云南方有獸名曰齧鐵大如水牛色如漆食鐵飲水其糞可作兵器其利如鋼也又虜複姓赫連勃勃改其支庶爲鐵伐氏云庶朕宗族子孫剛銳如鐵皆堪伐人也又作鐵俗作䥫他結切八|銕:+古文|僣:僣侻狡猾|餮:貪食說文作飻貪也|飻:+上同|蛈:爾雅曰王蛈蝪郭璞云即螲蟷似鼅鼄在穴中有蓋今河北人呼蛈蝪|𢶋:捅𢶋皃出字林|驖:馬赤黑也
jfT胡結;纈:綵纈胡結切二十一|䦖:䦖𨳺義見𨳺字|擷:捋取又虎結切|𢴲:縛也|頡:頡頏詩傳云飛而上曰頡飛而下曰頏說文曰頡直項也又姓風俗通有頡衛古之賢者|頁:頭也|齕:齧也又乎沒切|紇:絲下也又乎沒切|襭:以衣衽盛物也|絜:爾雅河名即九河之一也又古節切|𥊯:䁾𥊯目赤|𧀺:蘢𧀺草也|𪕯:鼠名又胡狄切|翓:翓𦐄飛上下|䐼:膜䐼|㹂:牛很又口殄切|奊:頭邪|籺:屑米|𨵪:門聲|𥢹:麥𥢹不破|覈:邀覈
HfT奴結;涅:水名出東郡又水中黑土奴結切十二|捏:捏捺|𦯖:菜似蒜生水邊|㘿:塞也|圼:+上同|篞:爾雅云大管曰簥其中曰篞小者曰篎|苶:苶然疲役又乃叶切|𥔄:礬石別名|𤶚:疾病|㖏:㖏呵|𦛠:腫也|菍:草也
PfT昨結;截:廣雅云盛也斷也或作截餘倣此昨結切七|䟌:傍出前也|𡴺:山峯又子結切|嶻:嶻嶭山名又藏曷切|蠞:蠞似蟹生海中|䕙:草䕙|𩟙:食
gfT五結;齧:噬也亦姓莊子有齧缺五結切十三|霓:虹又音倪|蜺:寒蜩又音倪|嵲:螮嵲|槷:危槷|臬:禮注云門橜也爾雅云在牆者曰楎在地者曰臬|嶭:嶻嶭又五割切|臲:臲卼不安書作杌陧|陧:+見上注|䘽:裗䘽|𡴎:山高皃說文作𡴎本音孼|闑:門閫中也|𡿖:屼𡿖山皃
DfD莫結;蔑:無也說文曰勞目無精也从苜戍人勞則蔑然也苜音末莫結切二十三|懱:輕懱|𧂝:目赤說文云目眵也俗作䁾|㩢:㩢揳不方正也|蠛:蠛蠓|篾:竹皮|幭:帊幞|鱴:𩶽鱴魛今鮆魚也|𥾝:細也出蒼頡篇|衊:汙血也出說文|䩏:䩏尐小也尐即列切|㒝:㒝僣多詐|𥉓:汙面|𤊾:火不明皃|覕:不相見皃|𪇴:工雀|𥣫:莊子謂之禾也|鴓:繼英鳥名|瀎:瀎㳚|𥸴:糏𥸴也|𥌨:𥌨頡|粖:糜也又亡達切|𩱷:+上同
AfD方結;㢼:弓戾或作𢏨方結切九|䋢:輓又普蔑切|閉:闔也塞也俗作𨳲又博計切|𩋇:刀飾名|𡘴:大也|䌘:繩編劒帶|㭭:㭭柲也|䘷:䘷袖褾袂也|㔡:大力之皃
hfT烏結;噎:食塞又作咽烏結切六|䊦:糉屬|㝣:靜也又音翳|蠮:蠮螉|𤝱:獸名似牛白首四角出山海經|咽:哽咽
efT苦結;猰:猰犺不仁苦結切九|䫔:𩓝䫔短皃|挈:提挈又持也|㼤:㼤瓶受一升也|𡔢:𥸸𡔢多節目也𥸸練結切|契:契闊又苦計切|栔:爾雅云栔滅殄絕也|鍥:刻也又斷絕也又古屑切|蛪:蛪蠅蟲又蛪蚼似蟬而小
ifT虎結;𡘐〈㚛〉:肥壯虎結切六|䩤:急繫|擷:又胡結切|𢴲:𢴲束又下結切|褉:褉襦|䙽:見也
BfD普蔑;撆:小擊又略也引也亦作撇普蔑切十|丿:右戾|𢠳:𢠳然瞋也|瞥:暫見亦作𧢍又芳滅切|䭱:小香也|䋢:韻略云馭右迴又方結切|嫳:輕薄之皃|䫾:䫾小風皃|鐅:江南呼鍫刃|暼:暼日落勢也
CfD蒲結;蹩:蹩𨇨旋行皃一曰跛也蒲結切十四|㮰〈𢱧〉:反手擊也|𩓝:𩓝䫔|𤻋〈癟〉:戾癟不正|䭱:香也又音瞥|咇:咇語也又口香|苾:菜名說文曰馨香也又頻必切|馝:香也|䏟:䏟㚛肥也|飶:食香|蛂:蛂蟥蛢甲蟲也|柲:支柲|𢛎:醜氣|襒:襒衣亦作𧝬
EfT丁結;窒:塞也丁結切又陟栗切七|𥉺:𥉺𥅧|蛭:水蛭又音質|㗧:㗧咄|咥:蛇咥氏蕃姓|𨴗:門閉|𡇓:下入
IfT練結;𥸸:𥸸𡔢多節目也練結切七|戾:罪也曲也戾至盭並又力計切|捩:拗捩出玉篇|綟:麻綟|唳:嘍唳鳥聲|盭:綬色也|夨:左曰夨也
#薛
QgT私列;薛:國名亦姓出河東新蔡沛國高平四望本自黃帝任姓之後裔孫奚仲居薛歷夏殷周六十四代爲諸侯周末爲楚所滅後遂氏焉說文作辥艸也私列切十九|𨫔:田器|紲:繫也左傳曰臣負羇紲杜預云紲馬韁也亦作絏俗作靾|緤:+上同|褻:衷衣|辥:說文辠也凡從辥者經典通作薛|泄:漏泄也歇也亦作洩又姓左傳鄭大夫洩駕又餘制切|渫:治井亦除去又姓渫子古賢者出韓子|禼:字林云蟲名也又殷祖也或作偰又作契|𥝁:+古文|媟:狎也慢也說文嬻也|齛:亦作齥爾雅云羊曰齥|䊝:𥻦䊝|𣽒:𣽒注|暬:侮也|絬:堅絬|㡜:殘帛又音雪|疶:痢也亦作𤵺|㔎:斷也
IgT良辥;列:行次也位序也又陳也布也說文作𠛱分解也亦姓鄭有列禦寇著書十八篇良辥切二十|𠛱:+上同|迾:遮遏|蛚:蜻蛚蟋蟀|鮤:刀魚也一名鱴刀今鮆魚也|烈:光也業也又忠烈又猛也熱也火也|洌:水清也潔也|冽:寒也|裂:擘裂破也左傳曰裂裳帛而與之|茢:禮注云桃茢可以爲帚除不祥說文芀也|颲:風雨暴至|鴷:啄木鳥|栵:細栗爾雅云栵栭今江東呼爲㮌栗楚呼爲茅栗也|㤠:憂心|挒:埤蒼云搩也|𩢾:次第馳馬|𡊻:塍也|𡿪:水流皃|姴:美也|䅀:說文曰黍穰也
JgT陟列;哲:智也陟列切五|悊:-|喆:+並上同|嚞:古文|蜇:螫也亦作䖧
fgb渠列;傑:英傑特立也又俊也渠列切十四|桀:磔也又夏王名|竭:盡也舉也|碣:說文曰特立之石也又東海有碣石山|楬:有所表識說文楬櫫也春秋傳曰楬而書之|榤:鷄栖於杙|揭:高舉又朅訐二音|渴:水盡也|嵥:嵥𡴎高皃|滐:水激迴出海賦|櫭:木釘名|偈:武也|杰:梁四公子名𩆊杰也|搩:強暴
cgT如列;熱:釋名曰熱爇也如火所燒爇如列切二|苶:疲役皃
XgT旨熱;晢:光也旨熱切九|晣:+上同|浙:江名在東陽一曰浙米也|折:拗折又虜複姓南涼禿髮傉檀立其妻折屈氏爲皇后又常列切|靼:柔皮|𩍕:+古文|䩢:+俗|䏳:脟皮也|䀸:目明
bgT食列;舌:口中舌山海經云長舌山有獸名長舌狀如禺而四耳出則郡多水又姓左傳越大夫舌庸也食列切四|揲:數蓍又思頰切|蛥:蛥蚗蟪蛄別名|鞨:治皮亦作㓭
ZgT常列;折:斷而猶連也說文斷也又作㪿常列切一
ggb魚列;孼:臣僕庶孼之事謂賤子也猶樹之有孼生也說文曰庶子也魚列切十二|糱:麴糱說文曰牙米也|讞:正獄說文作𤅊議辠也與法同意|𤅊:+上同|蠥:䄏蠥說文曰衣服謌謠艸木之怪謂之䄏禽獸蟲蝗之怪謂之𧞔蠥|㜸:+俗|闑:門中礙也|𡴎:山高皃說文作𡴎危高也又藝哲切|钀:馬勒傍鐵|櫱:木餘又姓何氏姓苑云東莞人本姓薛避仇改之|䶬:龍鬐脊上䶬䶬又丁篋切|䡾:高皃
DgH亡列;滅:盡也絕也亡列切二|搣:手拔又摩也㧗也捽也
egb丘謁〖竭〗;朅:說文去也丘謁切又去謁切五|揭:高舉也又擔也|藒:藒車香草|愒:息也|𡐤:玉篇云𡐤界也
AgH并列;鷩:雉屬似山雞而小周禮有鷩冕并列切七|鼈:魚鼈俗作鱉蟞|虌:蕨菜|鄨:水名在牂牁|𡐞:大阜|憋:急性皃|䳤:鵂鶹
Pgj情雪;絕:斷也作絕非情雪切一
Ngj子悅;蕝:束茅表位子悅切又子芮切三|㔢:㔢斷物也|𨼎:隔𨼎
Qgj相絕;雪:凝雨也元命包曰陰陽凝爲雪釋名曰雪綏也水下遇寒氣而凝綏綏然下也又拭也除也相絕切四|䨮:+上同出說文|㡜:㡜縷桃花今製綾花|㨹:滅㨹
Kgj丑悅;𤿫:皮破丑悅切一
lgj弋雪;悅:喜也脫也樂也服也經典通用說又姓後燕錄有悅綰弋雪切七|說:姓傅說之後又失爇始銳二切|閱:簡閱也又閥閱|蛻:蟬去皮也又他臥他外舒芮三切|娧:姚娧美好又他會切|𧀲:草名似芹|䓲:草生而新達曰䓲也
egn傾雪;缺:少也說文曰器破也傾雪切二|蒛:蒛葐草也
hgr乙劣;噦:逆氣乙劣切一
cgj如劣;爇:燒也如劣切五|焫:+上同見禮|蜹:蚊蜹又如銳切|㨎:括也|㕯:言遟聲
agj失爇;說:告也釋名曰說者述也宣述人意也失爇切又悅稅二音一
Xgj職悅;拙:不巧也職悅切十一|炪:說文曰火光也|䂐:短也|梲:梁上楹|蝃:蜘蛛|準:應劭云準頰權準也李斐云準鼻也又章允切|䫎:頭短|𠭴:倔𠭴短皃|䪼:面秀骨|𨢬〈𨡸〉:醎葅|䖦:蟲
Ygj昌悅;歠:大飲昌悅切二|啜:茹也
Jgj陟劣;輟:止也已也陟劣切十五|畷:田閒道又竹芮切|惙:疲也憂也|餟:祭酹也又竹芮切|罬:捕鳥覆車罔一名罦|剟:說文刊也|醊:醊連祭也|啜:言多不止|䟾:跳也|綴:連補也又竹芮切|掇:拾取又丁活切|腏:骨閒髓也|𩋁:車具|叕:聮也|𧖀:茅蜘蛛說文曰蟊作罔蛛蟊也又壯殺切
Igj力輟;劣:弱也鄙也少也力輟切十三|𢚃:+上同|埒:馬埒亦厓也還也堤也爾雅山上有水埒又孟康云等庳垣也|䟹:蹶䟹跳踉皃出字統|鋝:說文曰十一銖二十五分之十三周禮曰重三鋝又音刷|脟:脅𠟼|㸹:牛白脊出字林|蛶:爾雅曰蛶螪何|㲕:毛色斑也|浖:隈隅也|哷:鷄鳴|㭩:木名又音捋|𦓤:禾麥知多少
BgH芳滅;瞥:暫見亦作𧢍說文曰過目也又目翳也芳滅切又芳結切四|潎:漂潎又匹蔽切|憋:怒也又卑列切|𤻋〈癟〉:枯病
CgL皮列;別:異也離也解也說文作剛又姓何氏姓苑云揚州人皮列切又彼列切二|𡷘:大𡷘山名書亦作別
LgT直列;轍:車轍直列切五|徹:通也明也道也達也又丑列切|撤:發撤又去也經典通用徹|澈:水澄|㯙:棗也
AgL方別;䇷:分䇷一云分契方別切五|𧧸:+上同|莂:種穊移蒔也|扒:擘也|別:分別
Vgj所劣;㕞:埽也清也所劣切四|刷:+上同|𠴪:鳥理毛也|𠻜:小飲
dgX居列|dgb居列〖？〗;孑:a單也居列切六|訐:b訐發人私|𨥂:a句孑戟也|趌:a趌𧽸跳皃|䅥:b長禾|揭:b揭起
agT識列;設:置也陳也合也識列切二|蔎:香草
Mgj女劣;吶:嗗吶聲不出女劣切一
ign許劣;𥄎:舉目使人許劣切六|𩖶:小風皃|𣧡:盡也|烕:滅也|𦐋:小鳥飛|吷:飲也說文與歠同
hgn於悅;妜:鼻目閒輕薄曰妜也於悅切一
dgr紀劣;蹶:有所犯灾紀劣切又居月居衛二切五|𧱝:豕發土也|𧣸:角觸|䞵:小跳|罬:罦也又陟劣切
Sgj側劣;茁:草生皃側劣切又側滑切二|䵵:短黑皃也
Ogj七絕;膬:耎而易破七絕切四|絟:細布別名|𥕹:石破|敠:斷敠絕
NgT姊列;𧕾:茅𧕾似蟬而小姊列切八|䘁:+上同|𪇲:小鷄|尐:說文少也|𢪍:𢪍摘去也|𣧖:夭死|䰏:說文曰束髮少小也|𠯙:鳴𠯙𠯙
VgT山列;榝:茱萸山列切又音殺一
hgb於列;焆:煙氣於列切二|𠱝:怒𠱝
KgT丑列;屮:草初生皃丑列切七|撤:抽撤|硩:擿也周禮有硩蔟氏|徹:通也|䚢:䚢𧢷|聅:司馬法曰小罪聅聅謂以箭貫耳|䒆:船行
igb許列;娎:喜皃許列切二|焎:火氣
Zgj姝〈殊〉雪;啜:說文曰甞也爾雅曰茹也禮曰啜菽飲水姝雪切一
Tgj廁列〈別〉;㔍:割斷聲廁列切一
Rgj寺絕;㿱:枯也寺絕切二|𧋍:江𧋍似蝤蛑生海中
YgT昌列;掣:挽也昌列切又昌制切二|瘛:瘛癡小兒病又昌制切
lgT羊列;抴:亦作拽拕也羊列切又余世切一
UgT土〈士〉列;𨵊:城門中板也土列切一
#藥
lpT以灼;藥:說文云治病艸禮云醫不三世不服其藥又姓後漢有南陽太守河內藥崧以灼切三十一|躍:跳躍也上也進也|礿:祭名|禴:+上同|蘥:燕麥|鑰:關鑰|𩱲:內肉及菜湯中薄出之|瀹:+上同又漬也|𤅢:+上同亦水名在沘陽亦作𤄶|𤄶:水名|爚:煜燿光明|櫟:櫟陽縣名在京兆又音歷|龠:量器名|䋤:白䋤縞也|𠩃:岸上見也說文作屵|敫:光景流皃|籥:樂器郭璞云如笛三孔而短小廣雅云七孔|𢅹:幕𢅹屋也出新字林|𥌺:矐𥌺視皃|𧕋:𧐔𧕋螢火別名|纅:絲色|鸙:鷚鸙鳥|㜰:㜰媄之皃|𤒀:仰也|䟑:趠䟑行皃|㿑:淫㿑病也|𨷲:門𨷲|𧢢:視不定也|䠯:登也履也|𨈋:出走也|䖃:䖃䖃風吹水皃
IpT離灼;略:簡略謀略又求也法也要也又姓何氏姓苑云零陵人離灼切九|䌎:紩也|擽:字統云擊也|掠:抄掠劫人財物|㗉:爾雅云利也又人名晉有褚㗉|䂮:+上同|𧎾:渠𧎾蜉蝣蟲朝生暮死亦作𧐯|䀩:說文曰眄也方言云視也|䛚:約䛚歎美也
dpf居勺;腳:釋名曰腳卻也以其坐時卻在後也居勺切五|脚:+俗|蹻:走蹻蹻皃|卻:節也又去約切|屩:草履也
XpT之若;灼:燒也炙也熱也之若切十六|斫:刀斫又漢複姓有斫胥氏何氏姓苑云今平陽人|彴:橫木渡水|㣿:痛也|勺:挹取也又周公樂名又音杓|酌:酌酒又益也挹也行也取也霑也|繳:矰繳說文作𦅾生絲縷也|焯:火氣|䅵:五穀皮又音梏|妁:媒妁說文曰酌也斟酌二姓也又音杓|謶:欺也|𥯩:䉛𥯩玉篇云𥂖米具|犳:獸名|䶂:鼠屬|𧘑:玉篇云褌衣|禚:齊地名
apT書藥;爍:灼爍書藥切七|鑠:銷鑠|獡:犬驚|㜰:美好也|爚:儵爚光皃又音藥|䁻:美目|䟏:動也又音櫟
cpT而灼;若:如也順也汝也辝也又杜若香草亦姓魯人也又虜三字姓後魏書若口引氏後改爲寇氏而灼切十一|弱:劣弱|鄀:地名在襄陽|箬:竹箬|蒻:荷莖入泥之處又菜名|楉:楉榴安石榴也|溺:水名出龍道山其水不勝鴻毛又奴歷切|䐞:脃腝說文曰肉表革裏也|惹:䛳惹|叒:榑桑叒木|𨀝:足下文
YpT昌約;綽:寬也昌約切四|繛:+古文|婥:婥約美皃|磭:大脣屵磭皃屵魚偃切
hpf於略;約:約束又儉也少也又姓韓子有古賢者約續於略切又於笑切二|葯:白芷葉
epf去約;卻:退也去約切四|却:+俗|𨟠:地名在河東|𤷽:𤷽食瘡疾
gpf魚約;虐:酷虐說文作𧆩殘也魚約切三|磭:大脣皃又音綽|瘧:病也
ZpT市若;妁:媒妁市若切又音酌六|勺:周禮梓人爲飲器勺一升又漢複姓殷人六族有長勺尾勺二氏又音酌|汋:瀱汋又士角切|杓:杯杓|仢:仢約流星|芍:芍藥蕭該云芍藥香草可和食芍張略切藥良約切又芍陂在淮南七削切又蓮芍縣名在馮翊之若切又𦽏茈草名胡了切
KpT丑略;㲋:說文曰獸也似兔青色而大象形頭與兔同足與鹿同丑略切六|𤟭:+上同|婼:叔孫婼魯大夫說文曰不順也|逴:略逴行皃|辵:說文云乍行乍止从彳止聲|蠚:蟲行毒亦作𧍷又火各切
QpT息約;削:刻削息約切一
SpT側略;斮:斬也側略切一
NpT即略;爵:封也禮含文嘉曰殷爵三等周爵五等白虎通曰三等法三光五等法五行也淮南子曰爵祿者人臣之銜轡也文字音義曰爵量也量其職盡其才也又禮器周禮曰享先王以玉爵即略切七|𩰥:+古文|雀:鳥雀禮記云雀入大水爲蛤|爝:炬火莊子云日月出矣而爝火不息又音嚼|燋:火未然也|㩱:捎也|䶂:鼠似兔而小也
PpT在爵;皭:靖也埤蒼曰白色也在爵切三|嚼:噬嚼|爝:炬火
OpT七雀;鵲:淮南子云鵲知太歲之所字林作䧿七雀切十|舄:人姓纂文云古鵲字|趞:行皃|㹱:宋國良大|碏:敬也又人名衛大夫石碏|芍:陂名在壽春|皵:皮皴爾雅云棤皵謂木皮甲錯|踖:陵也馺也|䇎:驚也|䱜:魚名出東海
fpf其虐;噱:嗢噱笑不止其虐切九|蹻:舉足高又居勺切|𠊬:須臾亦倦也|𧍕:天神蟲又丘良切|𧮫:說文曰口上阿也一曰笑皃|𠶸:-|臄:+說文並同上|醵:合錢飲酒|䐘:䐘䐘大笑也
hpv憂縛;嬳:作姿態也憂縛切四|𡤬:+上同|彠:度也又乙虢切|臒:大也善也
CpP符钁;縛:繫也符钁切一
ipv許縛;䂄:大視皃許縛切四|矆:+上同|彏:弓弦急皃又居縛切|戄:驚戄又曰遽視
kpv王縛;籰:說文曰收絲者也亦作籆王縛切五|𧤽:+上同|𧅚:𧅚子菜|𥸘:筌取魚器也|䢲:行不住䢲䢲天下
dpv居縛;玃:大猨也說文曰大母猴也居縛切十一|貜:+上同說文曰𣫔貜也|𧾵:大步|钁:說文曰大鉏也方言云關東名曰鹵斫也|攫:膊也|矍:說文云隹欲逸走也从又持之矍矍也一曰視遽皃|𡚠:健皃|彏:弓弦急皃|躩:盤辟皃|𪈴:三首三足鳥|𨏹:車輞
JpT張略;芍:芍藥香草張略切七|著:服衣於身又直略張豫二切|𥗁:說文云斫也|櫡:說文曰斫謂之櫡|鐯:钁也|𣃈:+上同|擆:置也擊也
LpT直略;著:附也直略切一
epv丘縛;躩:說文云足躩如也丘縛切二|𢖦:往也
fpv具籰;戄:大視具籰切五|𧾵:大步又居縛切|𡚠:健皃又居縛切|䣤:鄉名|貜:大猨又居縛切
MpT女略;逽:走逽女略切三|𨵫:𨳞𨵫牽引也|蹃:踐也
BpP孚縛;𩅿:美雨孚縛切一
ipf虛約;謔:戲謔虛約切一
#鐸
GqT徒落;鐸:大鈴也軍法用之又木鐸金鈴木舌釋名鐸度也號令之限度也又姓左傳晉大夫鐸遏寇徒落切十五|剫:治木也說文判也爾雅曰木謂之剫|度:度量也又音渡|𢜬:忖𢜬|踱:跣足蹋地|凙:楚詞云冬冰之𠗂凙|襗:褻衣|𩑒:𩑒顱|𧩧:欺也|𩍜:𩌈𩍜胡履也|䐾:𦘴䐾無檢限也|㤞:徵也亦作𢖲|喥:口喥喥無度|仛:他也|𨍏:𨍏輅
DqD慕各;莫:無也定也說文本模故切日且冥也从日在茻中茻音莽又州名開元十三年改鄚州去邑亦姓楚莫敖之後又虜複姓五氏西秦錄有左衛將軍莫者羖羝南涼州刺史莫侯悌眷後魏末有亂寇莫折念生又有莫輿氏莫盧氏又虜三字姓周太祖賜廣寧楊纂姓莫胡盧氏慕各切十六|幕:帷幕又姓|鄚:縣名在河閒又姓|膜:肉膜|鏌:鏌鋣劒名|摸:摸𢱢又莫胡切|漠:沙漠又施也茂也|瘼:病也|寞:寂寞說文作𠴫嗼|瞙:字統云目不明|嗼:鼽嚏|塻:舍塻亦塵塻|𣩎:死也說文作㱳云死𡧯㱳也|𢊗:定也|𡈗:見文|𠢓:𠢓動
IqT盧各;落:零落草曰零木曰落又始也聚落也左傳注云宮室始成祭之爲落亦姓出姓苑又漢複姓二氏漢有博士落姑仲異益部耆舊傳有閬中落下閎善歷也盧各切三十四|絡:絡絲又姓|烙:燒烙|洛:水名書曰導洛自熊耳漢書作雒|珞:瓔珞也|酪:乳酪|樂:喜樂又五角五教二切|𩂣:說文云雨𩂣也|轢:陵轢又音歷|笿:籠笿|硌:磊硌|駱:白馬黑鬣曰駱又姓出東陽吳有駱統|𤽼:大白|𩊚:生革|㓢:去皮節又剔也|鉻:說文𩮜也|馲:馲駝又音託|𩧐:+上同|鮥:魚名又五格切|䶅:鼠名又下各切|雒:字林鵋䳢鳥又姓駱絡雒並出姓苑|𣛗:㰚𣛗出音譜|𧭥:𧭥謊狂言|躒:晉大夫名輔躒本又音歷|鵅:烏𪇰永鳥|𤻲:治病又音料|𣧳:殂也|𤽥:大皃|挌:打也|𪇱:似鵰黑文赤頭|濼:水名在濟南又音祿|袼:䙔袼|䀩:大目|𨏒:𥕖𨏒車聲
FqT他各;託:寄也他各切十八|袥:開衣領也|橐:無底囊|魠:魚名|籜:竹籜|柝:擊柝漢書曰宮中衛城門擊刀斗傳五更衛士周廬擊柝也亦作𣔳|𣟄:+上同|拓:手承物又虜複姓二氏周書王秉王興並賜姓拓王氏又有拓跋氏初黃帝子昌意少子受封北土黃帝以土德王北俗謂土爲拓謂后爲跋故以拓跋爲氏跋亦作拔或說自云拓天而生拔地而長遂以氏焉後魏孝文太和二十年改爲元氏也|馲:馲駝|𩧐:+上同|跅:跅弛不遵禮度之士|蘀:葉落|𦚈:𦚈脪也滴也澆也|侂:毀也說文寄也|飥:餺飥|魄:落魄貧無家業出史記本音拍|沰:赭也又磓也|矺:儀禮注云王棘矺鼠
NqT則落;作:爲也起也行也役也始也生也又姓漢有涿郡太守作顯則落切又則邏臧路二切六|迮:起也又仄格切|柞:木名又音昨|糳:精細米也說文曰糲米一斛舂九斗曰糳|鑿:詩曰白石鑿鑿|㘀:強㘀又祖郭切
OqT倉各;錯:鑢別名又雜也摩也詩傳云東西爲交邪行爲錯說文云金涂也倉各切七|厝:礪石|䱜:魚名|逪:說文云䢒逪也|剒:爾雅云犀謂之剒|縒:縒綜亂也|莡:草聲
dqT古落;各:說文云異詞也古落切五|閣:樓閣亦舉閣漢宮殿疏曰天祿閣騏驎閣蕭何造以藏祕書賢才也又姓急就章有閣并訴|格:樹枝|胳:胳腋|袼:袼䘸也又袂也
eqT苦各;恪:敬也又姓晉有中郎令恪啓苦各切三|㤩:-|愙:+並上同
gqT五各;咢:徒擊皷謂之咢詩云或歌或咢說文作㖾譁訟也五各切二十五|愕:驚也|鄂:國名在武昌又姓漢安平侯鄂君|諤:謇諤直言|𠟎:說文曰刀劒刃也|𧊜:說文曰似蜥蜴長一丈水潛吞人即浮出日南|𧍞:+上同|遌:心不欲見而見曰遌|萼:花萼|鍔:劒端|𡅡:+籀文|崿:崖崿|鶚:鳥名|鰐:魚名|噩:爾雅曰太歲在酉曰作噩亦作咢|㗁:口中斷㗁出字統|齶:+上同|顎:嚴敬曰顎|𡾙:山峯|鑩:以鐵作鉤物也|偔:多也|堮:圻堮|𡓐:+上同|㮙:穽也|湂:水名
BqD匹各;𩔈:面大皃匹各切十五|奤:+俗|濼:陂濼|䨰:+上同|粕:糟粕|膊:說文曰薄脯膊之屋上|𦢸:割肉|䪙:車覆軶|搏:擊也|胉:脅也|蒪:蒪苴大蘘荷名|𥴮:𥴮齒相簺也|𦿍:蘀𦿍也|𦥭:舂也|𦐦:飛去也又步各切
hqT烏各;惡:不善也說文曰過也烏各切又烏故切四|𢙣:+俗|堊:白土|蝁:蛇名
CqD傍各;泊:止也傍各切十一|亳:國名春秋時陳地漢爲沛之譙縣魏爲譙郡晉爲南兗州齊爲亳州|箔:簾箔|薄:厚薄說文曰林薄也又姓漢文帝母薄氏|礴:盤礴|簿:蠶具|𩍿:𩍿䩣屧也|鑮:似鍾而大|踄:蹈也|𩽛:魚似鯉一目也|䭦:䭦餅亦作𪎄
iqT呵各;𦞦:羹𦞦呵各切又火酷切十一|鄗:縣名漢光武改爲高邑|壑:溝也谷也坑也虛也|㕡:+上同|蠚:螫也亦作𧍷|謞:讒慝|郝:姓也殷帝乙時有子期封太原郝鄉後因氏焉|鰝:爾雅云大鰕也出海中似蝗長二三尺青州有之|熇:熱皃又火沃切|嗃:嚴厲皃易云家人嗃嗃|矐:重目又失明也
QqT蘇各;索:盡也散也又繩索亦姓出燉煌蘇各切又所戟切六|𢱢:摸𢱢|溹:水名在榮陽又所戟切|𩌈:𩌈𩍜|𦵫:草名|㮦:白㮦木名
jqT下各;涸:水竭也下各切十一|鶴:似鵠長喙左傳曰衛懿公好鶴有乘軒者|貈:說文曰似狐善睡獸也穆天子傳曰天子獵於滲澤得玄貈以祭河宗周禮曰貉踰汶則死此地氣然也|貉:-|狢:+並上同|𠗂:𠗂凙冰皃|佫:人姓出纂文|䮤:說文曰苑名一曰馬白頟|𥉑:望也|䅂:似黍而小|䶅:鼠出胡地
PqT在各;昨:昨日隔一宵又羌複姓有昨和氏在各切二十|酢:酬酢蒼頡篇云主荅客曰酬客報主人曰酢|莋:縣名在越嶲|怍:慙怍|𣫞:穿𣫞|鑿:鏨也古史考曰孟莊子作|笮:竹索西南夷尋之以渡水|筰:+上同|柞:木名又音作|㸲:山牛|岝:岝崿山高|䎰〈䣢〉:地名在蜀亦姓出蒼頡篇|飵:楚人相謁食麥饘曰飵|𦁎:草繩|𢂃:𢂃㡗|䋏:緪也|秨:禾稼動搖|砟:石上又人名|葃:茹草又士革切|鈼:鉹也吳人云也
AqD補各;博:廣也大也通也從十尃亦州名春秋時齊之聊攝也秦爲東郡地隋爲博州因博平縣以名焉又姓古有博勞善相馬也補各切二十|髆:胷髆|搏:手擊|爆:迫於火也|鎛:鐘磬上橫木也又田器也詩曰庤乃錢鎛|㗘:㗘㗱噍皃㗱姊入切|𪙍:+上同|襮:衣領|鑮:大鍾|簙:六簙棊類出說文世本曰烏曹作簙書本多單作博|䗚:䗚蟭螗蜋卵也|猼:犬名|䍸:䍸䍫獸名似羊九尾四耳其目在背出山海經䍫徒何切|欂:欂櫨枅也|𩌏:車下索也|溥:水名|䶈:䶈鼠|餺:餺飥|䙏:短袂衫|𥴮:蠶具名吳人用
HqT奴各;諾:說文譍也奴各切一
iqj虛郭;霍:揮霍爾雅曰霍山爲南嶽又姓武王弟霍叔之後虛郭切十二|靃:地名說文曰飛聲也雨而雙飛者其聲靃然|霩:雲消皃|䁨:驚視|藿:豆葉又香草|矐:目開|彉:張也說文曰弩滿也又郭廓二音|彍:+上同|攉:攉盤手戲|瀖:瀖泋眾波聲|劐:裂也|癨:吐病
dqj古博;郭:城郭也釋名曰郭廓也廓落在城外也世本曰鯀作郭亦姓出太原河南潁川東郡馮翊五望本自王季之後又云氏於居者城郭園池是也案說文作𩫏爲居𩫏作𨟍爲𨟍氏也古博切十|𩫏:-|𨟍:+並見上注|崞:縣名在代州又山名|椁:禮曰殷人棺椁又木名|槨:+上同|彉:弓張說文曰弩滿也|彍:+上同|埻:埻端國名又音蟈|𦘅:耳𦘅
hqj烏郭;雘:丹也烏郭切六|蠖:蚇蠖屈伸蟲名|𩟓:味薄|臒:羹肉玉篇云善肉|鸌:水鳥|嬳:恐嬳
jqj胡郭;穫:刈也胡郭切十|鑊:鼎鑊|㦜:心動也|檴:檴落木名|𤐰:𤐰熱|濩:說文曰雨流霤下皃|擭:柞擭阱淺則施之|䨥:𩂹䨥大雨|𤻙:㾰𤻙|𢋒:廓𢋒空遠
eqj苦郭;廓:空也大也虛也亦州名漢西羌地前涼湟河郡周爲廓州也苦郭切六|鞹:皮去毛|漷:水名在魯又許虢切|𠠎:解也裂也|籗:爾雅注云捕魚籠亦作篧又仕角切|噋:敲噋噋聲也亦作㗥
gqj五郭;瓁:朴瓁五郭切一
Iqj盧穫;硦:𥕖硦石聲盧穫切𥕖音廓一
Nqj祖郭;㘀:鳴㘀㘀亦作嗽祖郭切一
#陌
DrD莫白;陌:阡陌南北爲阡東西爲陌莫白切十八|帞:頭巾|袹:袹複|𡠜:靜也|𡖶:+上同|貘:食鐵獸似熊黃黑色一曰白豹|蛨:虴蛨蟲|貊:蠻貊|佰:一百爲一佰也|驀:騎驀|㹮:𤜤㹮驢父牛母亦作馲𩢷|𩢷:+上同|嗼:詩云盈盈一水閒嗼嗼不得語|貉:北方獸|洦:水淺皃|𢫦:擊也|𧻙:𧻙越|銆:銆刀軍器
JrT陟格;磔:張也開也爾雅曰祭風曰磔陟格切十一|虴:虴蛨|舴:舴艋小船|𤜤:𤜤㹮|𪄱:戇鳥鷄屬|馲:馲𩢷|𩑒:𩑒顱腦蓋|𪐏:黏皃|嫡:孎嫡|𥧮:窟也|杔:杔櫨壓酒器也
CrD傍陌;白:西方色又告也語也亦姓秦帥有白乙丙傍陌切五|帛:幣帛尚書大傳曰舜修五禮五玉三帛又姓出吳神仙傳有帛和|舶:海中大船|鮊:魚名|𦰬:草爾雅曰帛似帛俗從艹
ArD博陌;伯:長也又侯伯周書曰率眾時作謂之伯亦姓左傳晉有大夫伯宗又漢複姓二氏韓子有伯夫氏墨家流莊子有伯成子高博陌切八|迫:逼也近也急也附也|敀:+上同|百:數名又姓秦有大夫百里奚|柏:木名五經通義曰諸侯墓樹柏又姓晉趙王倫母曰柏夫人亦作栢|湐:洦湐淺水|𦯉:藍之別名|㼟:㼿㼟井甃
fsb奇逆;劇:增也一曰艱也又姓史記燕有劇辛奇逆切六|屐:履屐|𨍺:車𨍺|𤭏〈谻〉:倦谻|𢜭:勞也|㘌:戲㘌
dsb几劇;戟:刃戟說文作𢧢有枝兵也釋名曰戟格也傍有枝格也典略曰昔周有雍狐之戟屈盧之矛孤父之戈几劇切八|撠:持也|𦻝:大𦻝藥名|𤜾:𤜾獸|谻:相踦|丮:持也|𢜭:勞也又其戟切|𩯋:髭𩯋
VsT山戟;𡩡:求也山戟切又蘇各切六|索:+上同|䞽:僵仆|溹:水名又雨下皃|䂹:碎石隕聲|𥻨:煑米多水
TsT測戟;柵:村柵說文曰豎編木測戟切三|䜺:磨豆|簎:刺也國語曰簎魚鼈也
jrj胡伯;嚄:嚄嘖大喚胡伯切二|𡄴:𡄴𡄴誇皃
SrT側伯;嘖:側伯切八|迮:迫迮|窄:狹窄|笮:矢箙又屋上版又迫也又姓吳有笮融亦作筵|㳻:遮水|諎:大聲亦作唶|舴:舴艋|蚱:蚱蟬
UrT鋤（鉏）陌;齚:齧也鋤陌切五|齰:+上同|咋:㕭咋多聲㕭烏交切|泎:瀺泎水落地聲|岝:岝㟯山皃
esb綺戟;隙:壁孔也怨也閑也綺戟切七|郤:姓出濟陰河南二望左傳晉有大夫郤獻子俗從𠫤|綌:絺綌|𠊬:廣雅云勞也極也疲也又大笑|𧯈:嫌恨|𡭴:西方小皃|𠶸:大笑
grT五陌;額:釋名曰額鄂也有垠鄂也說文作頟顙也五陌切六|頟:+上同|䱮:𩹺䱮魚名|峉:岝峉或作㟯|詻:鄭玄云詻詻教令嚴|䩹:補履
gsb宜戟;逆:迎也卻也亂也范曄漢書周防字偉公少孤微常修逆旅以俟過客而不待其報宜戟切六|屰:說文曰不順也|縌:後漢書云古佩璲也|㘙:說文云呻也|𥿬:紱維|𠱘:嘔𠱘
erT苦格;客:賓客苦格切四|喀:吐聲|礊:堅也|揢:手把著也
hrT烏格;啞:笑聲烏格切二|𩚬:飢
isb許郤;虩:懼也許郤切一
KrT丑格;坼:裂也亦作𡍩餘倣此丑格切六|䞣:半步|𩑒:腦蓋|㿭:皴㿭|𤖴:𤖴開|𩎚:䪝𩎚
hrj乙白;䪝:佩刀飾乙白切一
BrD普伯;拍:打也普伯切十|魄:魂魄|怕:澹怕靜也|皛:亦打出蜀都賦又胡了切又莫百切|敀:大打也|𠓗:疾也又音赴|珀:琥珀|𧻙:風入水皃|𤖼:𤖼破物也|洦:淺水
irT呼格;赫:赤也發也明也亦盛皃又虜複姓有赫連氏其先匈奴右賢王去卑之後劉元海之族也勃勃以後魏天賜四年稱王於朔方國号夏都以子從母之姓非禮也乃云王者繼天爲子是爲徽赫實與天連因改姓曰赫連氏呼格切五|爀:火色|嚇:怒也|𢅰:㦦㡗赤紙|𥋿:目赤
jrT胡格;垎:土乾也胡格切四|䞦:䞦䞽倒地|楁:鞍楁|𨍇:輓車當胷橫木
drT古伯;格:式也度也量也書傳云來也爾雅云至也亦格五博屬行箭但行梟以格殺漢吾丘壽王善之又姓東觀漢記有侍御史東平相格班古伯切十四|𢓜:至也亦作假|茖:山蔥|骼:骨骼|觡:鹿角|𩹺:𩹺䱮魚名|鵅:鵋䳢鳥名|挌:擊也鬬也止也正也|㦴:擊也鬬也亦作㪾|蛒:蠀螬別名|𪌣:碎麥|𢼛:擊也|𩹿:海魚似鯾肥美|鉻:陳公鉤也
irj虎伯;謋:謋然虎伯切八|諕:+上同|漷:水名在東海又音廓|砉:又呼狊切出莊子|𦒧:𦑍𦒧飛疾也|湱:漰湱波激水也|硅:硅破|𢝇:心驚
LrT場伯;宅:居也說文云宅託也人所投託也釋名曰宅擇也擇吉處而營之也場伯切十三|㡯:+古文|擇:選擇|澤:潤澤又恩也亦陂澤釋名曰下有水曰澤又州名秦爲上黨郡後魏爲建興郡周爲澤州取濩澤以名之亦姓出姓苑|𪀥:𪀥𪁔鳥名毛備五色|翟:陽翟縣名亦姓唐有陝州刺史翟璋又音狄|䕪:䕪蕮藥草車前別名|檡:檡棘善理堅刃者可以爲射決出儀禮|鸅:鸅鸆即護田也|𩏪:𩏪䪝刀飾|蠌:螖蠌|襗:袗襗|𤂥:土得水也
drj古伯;虢:國名周封虢仲於西虢秦屬三川郡義寧元年爲鳳林郡武德初爲鼎州又爲虢州亦姓左傳晉大夫虢射也古伯切五|𢼛:手打之類|㶁:水裂|𧭣:𧭣𧭣多言皃|唬:鳥啼
hrj一虢;擭:手取也一曰布擭也一虢切五|濩:濩澤縣在澤州又音護|彠:規蒦博雅曰度也|䪝:刀飾把中皮也|㠛:陂名又村名在吳王舊城側也
MrT女白;蹃:踐也女白切二|搦:捉搦又正也
erj丘擭;𧍕:天神蟲丘擭切二|𠠎:解木
CsL弼戟;欂:欂櫨戶上木弼戟切二|𣝍:說文曰壁柱也
#麥
DtD莫獲;麥:白虎通曰麥金也金王而生火王而死又姓隋有將軍麥鐵杖嶺南人俗作麦莫獲切八|𧖴:說文曰血理之分衺行體者又作脈經典亦作脉周禮曰以鹹養脉釋名曰脉幕也幕絡一體也|脉:+上同|衇:籀文|霢:霢霂亦作霢|眽:說文曰目邪視也|覛:爾雅云相也說文本莫狄切衺視也|𧡒:+籀文
jtj胡麥;獲:得也又臧獲方言云荊淮海岱淮濟之閒罵奴曰臧罵婢曰獲亦姓宋大夫尹獲之後胡麥切八|畫:計策也分也又胡卦切|嫿:分明好皃|劃:錐刀刻|鱯:魚名|彠:度也又烏虢切|㗲:㗲嘖叫也|咟:+上同
dtj古獲;蟈:螻蟈蛙別名古獲切十六|馘:截耳又獲也或作聝|聝:+上同|幗:婦人喪冠|膕:曲腳中也|𩪐:+上同|埻:埻端國名出山海經|摑:打也亦作𢼛|漍:水|𢹖:挻𢹖|䂸:䂸破|慖:悖也|嘓:口嘓嘓煩也|䬎:䬎䬉赤氣熱風之怪|讗:讗嚄疾言|𧖻:犬血
AtD博厄（戹）;檗:黃檗俗作蘗博戹切五|擘:分擘|薜:爾雅云山芹當歸也又曰山麻也|𤖟:豆中小硬者出新字林|糪:飯半生皃
CtD蒲革;䌟:織絲爲帶蒲革切四|繴:罿也|𦌠:翻車|欂:檴櫨又木名也
UtT士革;賾:探賾士革切七|鰿:爾雅曰貝小者鰿郭璞云今細貝亦有紫色者出日南又音迹|葃:茹菜又音藉|㣱:容尋常人|矠:以矛叉取物也|耫:灰中種也|嘖:㗲嘖叫也
StT側革;責:求也側革切十一|𩔳:𩔳䫢頭不正皃|簀:牀簀|幘:冠幘漢書曰幘古卑賤執事不冠者之所服說文曰髮有巾曰幘|嘖:大呼聲|謮:+謮怒說文同上|債:負財|𧐐:小貝也|𦟜:𦟜子魚子脯出新字林|嫧:鮮好|咋:大聲
Utj查獲;䞰:急走也出字林查獲切二|䟄:䟄黠皃出方言
TtT楚革;策:謀也籌也釋名曰策書教令於上所以驅策諸下也又馬箠也楚革切十四|冊:簡冊說文曰符命也諸侯進受於王也象其札一長一短中有二編之形|笧:+古文|嫧:健急皃|䶦:齒相值也|筴:卜筮筴也|𣌧:告也|矠:矛也|憡:憡痛|皟:淨也|㥽:耿介|𧶷:正也|拺:扶拺也|柵:豎木立柵又村柵
etT楷革;礊:鞕皃楷革切六|𩱘:說文曰裘裏也|䙐:+上同|緙:矣也又織緯|罊:器空|諽:謹也
itj呼麥;剨:破聲呼麥切二十一|繣:徽繣乖違|𦑌:飛聲|㦎:不慧又㦎㦎辯快出音譜|劃:劃作事又音畫|捇:捇掘土又裂也|掝:裂也|㖪:大笑皃|礊:鞕聲又口革切|䐸:曲腳中也|焃:赤也|㩇:擘也又于馘切|𢄶:裂帛聲|𨐶:辛𨐶𨐶|𥊮:目病|湱:漍湱水出西豁|𤷇:痛𤷇|䦝:䦝門聲|𤁹:水皃|䬉:熱䬉|𠜻:刀破
jtT下革;覈:實也下革切九|繳:衣繳衣領中骨又音酌|䃒:石地|翮:鳥羽|㮝:木名|核:果中核崔豹古今注云烏孫國有青田核莫測其樹實之形至中國者但得其核耳大如六升瓠空之以盛水俄而成酒味甚醇厚|𤈧:燒麥|滆:湖名在常州義興縣|蒚:蒲臺頭名
dtT古核;隔:塞也古核切十六|膈:胷膈|搹:㧖也出儀禮|鬲:縣名在太平原又鬲津九河名又姓殷末賢人膠鬲之後又音歷鼎屬也|槅:車槅|革:改也獸皮也兵革也亦姓漢功臣表有煑棗侯革朱|𥴩:𥴩子竹障出通俗文|𢡍:智也|諽:謹也|䪂:轡首|𧈑:虎聲|䨣:雨也|𥉅:瞔𥉅|𦑜:翅也|𩹺:魚也|嗝:雉鳴
JtT陟革;摘:手取也陟革切又他歷切九|謫:責也又丈戹切|讁:+上同|𤟍:犬怒張耳|棏:蠶棏或作𣚅|𡇠:硬皃|䊞:黏䊞|厇:張厇|矺:磓也
htT於革;戹:災也說文隘也於革切十四|厄:+上同|搤:持也握也捉也|㧖:+上同|軶:車軶|阸:限也礙也又危也迫也塞也|豟:爾雅曰豕絕有力又云彘大五尺爲豟|呝:呝喔鳥聲|𪕶:鼠屬|貖:+上同|蚅:蚅鳥蠋大如指似蠶|𩚬:飢皃|啞:笑聲|𧠞:𧠞視
VtT山責;梀〈栜〉:木名山責切十四|𣽤:小雨|𤶬〈㾊〉:瘮㾊寒皃|䨛:霰|摵:殞落皃|愬:驚懼皃又音素|擌:黐擌捕鳥|捒〈拺〉:拺擇取物也|𡩡:求也取也好也|索:+上同|溹:溹溹雨下皃|𩊯:堅硬|虩:虎驚皃又許逆切|㳻:說文曰所以𢹬水也
BtD普麥;𢶉:射中聲也普麥切二|糪:飯半生熟爾雅云米者謂之糪
gtT五革;虉:爾雅云虉綬虉小草雜色似綬五革切又五狄切四|鳽:鵁鶄又音堅|䩹:履頭|㣂:㣂束弓補也
ItT力摘;礐:礐硞水石聲也力摘切二|𥖪:𥖪礋打草田器出字林
jtj簪｟子｠〈于〉摑;㩇:裂聲也簪摑切一
Vtj砂（沙）獲;𢷾:拂著又捎𢷾也出通俗文砂獲切一
fsr求獲;𧾛:𧾛䞽足長皃求獲切一
MtT尼戹;疒:疾也尼戹切又仕莊切三|䭆:䭆炙餅餌名|眲:耳目不相信出列子
#昔
QuT思積;昔:往也始也左傳爲一昔之期明日也說文作㫺乾肉也又姓漢有烏傷令昔登思積切十四|𦠡:+籀文|腊:乾肉見經典|惜:悋惜說文痛也|潟:鹹土|磶:柱下石|舄:履也崔豹古今注云以木置履下乾腊不畏泥濕故曰舄也|𩍆:+上同|蕮:車前草|鬄:說文髮也|䯜:骻骨間也|𩾼:水鳥|焟:火乾|棤:皮甲錯也
NuT資昔;積:聚也資昔切又資賜切十八|脊:背脊釋名曰脊積也積續骨節終上下也說文作𦟝背呂也|蹐:蹐地小步|借:假借也又資夜切|迹:足迹|跡:+上同|𨒪:+籀文|踖:踧踖敬皃又春昔切|𪃹:𪃹鴒一名雝𪆂又名錢母大於燕頸下有錢文亦作䳭|鰿:爾雅曰貝小者鰿郭璞云今細貝亦有紫色者出日南|𧐐:+上同|𩺀:魚名|鯽:+上同|蹟:詩傳云不蹟不循道也|㵶:小水|襀:襞也|䃊:䃊𥒰|庴:縣在臨邛
huX伊昔;益:增也進也伊昔切八|謚:笑皃|嗌:喉上漢宣帝崩昌邑王至京師不哭云嗌痛|𨜶:地名|齸:爾雅曰麋鹿曰齸牛曰齝並吞芻而反出嚼之也|膉:肥也|𦶩:益母草爾雅注只作益|𪕶:鼠名
luT羊益;繹:理也陳也長也大也終也充也說文云抽絲也羊益切三十三|睪:引繒皃說文曰司視也从目从㚔令吏將目捕辠人也|亦:摠也俗作𡖋|弈:弈美皃又博弈|奕:大也又輕麗皃又行也盛也|帟:小幕曰帟|譯:傳言周禮有象胥傳四夷之言東方曰寄南方曰象西方曰狄鞮北方曰譯|懌:悅也樂也改也|斁:猒也|驛:驛馬|嶧:山名在魯|醳:苦酒|腋:肘腋|掖:持臂又縣名又掖庭也一曰正門之旁小門也亦姓|䘸:䘸縫|易:變易又始也改也奪也轉也亦水名出涿郡安閻山見水經亦州名漢書趙分晉得中山秦爲上谷郡漢置涿郡隋爲易州因水名之又姓齊大夫易牙又盈義切|液:律液又姓急就章有液客調|痬:病相染也|蜴:蜥蜴|埸:壃埸|圛:說文云回行也商書曰圛圛者升雲半有半無|襗:衣襦|射:無射九月律|墿:道也|焲:火光|襗〈𥜃〉:重祭名殷曰肜周曰𥜃亦作繹|㴒:浟㴒水皃|燡:火甚之皃|𦔥:耕也又音釋|𡱿:交𡱿|㘁:㘁川|𤑹:災也出字林|𠓋:光皃
auT施隻;釋:捨也解也散也消也廢也服也又姓施隻切十六|𥼶:說文曰漬米也|檡:梬棗|適:樂也善也悟也往也又姓|奭:盛也又驚視皃又邵公名說文作奭|郝:人姓又呼各切|睗:睒睗急視|晹:日無光|𡣪:嫁也|𦔥:耕皃|螫:蟲行毒亦作螫|𩮜:鬀髮又音逖|㚒:盜竊懷物也從兩入弘農陝字從此|冟:𩚳堅柔相著|䁺:視皃|襫:襏襫雨衣
YuT昌石;尺:家語曰布手知尺舒肱知尋說苑曰度量衡以粟生之十粟爲一分十分爲一寸十寸爲一尺昌石切十一|赤:南方色又姓出姓苑又漢複姓二氏莊子有赤張滿稽郭象注云赤張姓也韓子曰智伯以鍾遺仇繇赤章枝諫仇繇令不受|烾:+古文|蚇:蚇蠖蟲名易亦作尺|㡿:逐也遠也又㡿候說文曰卻屋也从广屰屰音逆|斥:+上同|㚖:白澤|郝:鄉名|滷:鹵滷|𠧚:姓也|𠧵:獸也
ZuT常隻;石:釋名曰山體爲石亦州名秦伐趙取離石周因邑以名州又姓左傳有衛大夫石碏又漢複姓二氏孔子弟子有石作蜀何氏姓苑有石牛氏常隻切七|碩:大也|祏:說文云宗廟主一曰大夫以石爲主|鉐:鍮鉐|䄷:說文云百二十斤也|鼫:鼫鼠螻蛄|䲽:鳥名
XuT之石;隻:一也說文曰鳥一枚也从又持隹持一隹曰隻二隻曰雙之石切十三|適:往也又施隻切又都歷切|炙:說文曰炮肉也从肉在火上|墌:基址|摭:拾也|拓:+上同|蹠:足履踐也楚人謂跳躍曰蹠|跖:+上同說文曰足下也|䗪:𧑓蝜蟲亦作蟅又音柘|䨥:𩂹䨥大雨|䞠:行也|𠪮:仄也|䘸:袖也
LuT直炙;擲:投也搔也振也直炙切七|擿:+上同出說文|䵂:麩䵂|躑:躑躅行不進也|蹢:+上同|𧓸:𧓸蠋蟲名|潪:土得水也
OuT七迹;皵:皮細起七迹切八|磧:砂磧|刺:穿也又七四切|𧻕:䟐𧻕行皃|洓:水名在北地|䟄:倉卒|𧙞:𧙞膝帬衸|嫧:嫧娕齊謹
RuT祥易;席:薦席又藉也大戴禮曰武王踐阼有席銘亦姓出安定其先姓藉避項羽名改姓席氏晉有席坦祥易切六|夕:暮也字從半月又姓漢書巴郡蠻渠帥七姓有羅朴督鄂度夕襲也朴普卜切蜀有尚書令夕斌|穸:窀穸窀厚也穸夜也|汐:潮汐|𨛳:鄉名|蓆:大也
PuT秦昔;籍:簿籍秦昔切十三|踖:踐也|𨆮:+上同|藉:狼藉又姓左傳晉大夫藉談又慈夜切|耤:耤田耤借也說文曰帝耤千畮也古者使民如借故謂之耤也宋書藉田令古官也於周爲甸師氏|塉:薄土|瘠:病也瘦也|庴:縣名在清河又七削切|猎:獸名似熊出山海經|葃:茹草|膌:膌瘦|䣢:地名在蜀|簎:打也
CuH房益;擗:撫心也房益切九|椑:棺也|躄:躄倒|闢:啓也開也|辟:便辟又法也五刑有大辟從卩辛所以制節其罪也從口用法也|㱸:㱸㱤欲死之皃|𩪧:弓弭|萆:雨衣|𣮐:毛𣮐
luj營隻;役:古從人今從彳說文曰戍邊也營隻切十二|䓈:燕人呼芡又羊捶切|疫:說文云民皆疾也|𩷍:魚名有四足出文字集略|坄:喪家塊竈說文曰陶竈窻也|垼:+上同|炈:亦同|𪁛:𪁛鳩鳥|鈠:小矛|𩂹:𩂹䨥大雨|豛:豬之別名|𧈻:𧈻𧌐蟲名
iun許役;瞁:驚視許役切二|𥆛:眡也
AuH必益;辟:爾雅皇王后辟君也亦除也又姓漢有富室辟子方又有辟閭彬必益切七|璧:白虎通曰璧者外圜象天內方象地爾雅曰肉倍好謂之璧肉邊好孔也|鐴:鐴土犁耳|躄:跛躄說文作𣦢人不能行也|𣦢:+上同|襞:襞衣說文曰韏衣也|𨐨:治也
BuH芳辟;僻:誤也邪僻也芳辟切四|辟:+上同見詩|癖:腹病|廦:牆也
buT食亦;麝:麝香也食亦切又食夜切二|射:世本曰逢蒙作射又姓吳有中書郎射慈又神柘切又羊謝羊益二切
AsL彼役;碧:色也說文曰石之青美者又八品九品服色代青也紀年曰惠成王七年雨碧于郢彼役切一
JuT竹益;𪐏:黏黐竹益切一
KuT丑亦;彳:說文云小步也象人脛丑亦切二|𤭏:瓶也
Xuj之｟志｠〈？〉役;𦳮:𦳮卷之役切一
iun七〈火〉役;𥄎:小動七役切二|𢔠:小行
#錫
QvT先擊;錫:賜也與也亦鉛錫玄中記曰鉛錫之精爲婢又姓吳志云漢末有錫光先擊切十三|析:分也字從木斤破木也又爾雅曰析木謂之津注云即漢津也亦姓風俗通云齊大夫析歸父|㭊:+俗|裼:袒衣|皙:人白色也|緆:細布|𪎥:+說文同上|𧋍〈蜥〉:蜥蜴|菥:菥蓂大薺|淅:淅米|惁:敬也|𧊸:𧊸𧐎|㱤:㱸㱤欲死之皃
dvT古歷;激:疾波又姓淮南王傳有激章古歷切九|擊:打也|墼:土墼|轚:舟車|獥:狼子|敫〈㰾〉:歌也|𦼷:草名|𡫀:楊皃|鸄:鳥名似烏
BvD普擊;霹:霹靂普擊切七|劈:剖也裂也破也|澼:莊子洴澼絖漂絮者|憵:急速|䤨:裁木爲器|癖:痃癖病|僻:邪僻
IvT郎擊;靂:霹靂郎擊切四十五|䟐:䟐𧻕行皃𧻕七昔切|酈:縣名在南陽亦姓又力知切|癧:瘰癧|轢:車踐又音洛|鎘:鎘鎗|䥶:+上同|礫:釋名曰小石曰礫|瓅:珠瓅|秝:稀疎|櫪:馬櫪|䍽:羖䍽|櫟:木名柞屬又音藥櫟陽縣名|𩽏:魚名亦作𩹺|歷:經歷又次也數也近也行也過也又歷日續漢書律歷志云黃帝造歷世本曰容成造歷尸子曰羲和造歷或作曆|曆:+見上注|藶:葶藶子|瀝:滴瀝|磿:石聲|寥:寂寥無人又深也又音聊|鬲:爾雅曰鼎款足者謂之鬲說文作鬲鼎屬實五觳斗二升曰觳象腹交文三足今亦作鬲|㽁:+瓦器說文同上又作䰛|蒚:山蒜|皪:的皪白狀|𥌮:𥌮𥉶視明皃|䍥:羃䍥煙狀|躒:動也|䟏:+上同|𪙽:齒病|𤩚:說文云玉名|厤:治也|攊:擊口也|䮥:馬色|𧙉:纏裹|䤙:䤙𨢎酪滓|𡳸:履下|𦠓:𦠓䐎強脂|𨢌:下酒|㔏:劙開|𪅼:鳥名|觻:角鋒|𥽗:雜糅食名|擽:捎也|濼:一名貫眾葉圓銳莖毛黑布地生冬不死一名貫渠又音藥|蚸:爾雅曰蟿螽螇蚸亦作蝷
EvT都歷;的:指的又明也說文作旳都歷切二十六|適:從也又之石始石二切|嫡:正也君也|甋:瓴甋塼也|靮:馬韁|鏑:箭鏃|馰:馰顱馬白額又作的|滴:水滴也亦作𤁷|肑:腹下肉也|弔:至也又音釣|芍:蓮中子也亦作的見爾雅|蹢:蹄也詩云有豕白蹢|䶂:鼠名又音灼|玓:玓瓅明珠色出說文|樀:屋梠|𪄱:雉屬|𦉹:魚擊網也|𥕐:𥕐磓|𥐝:+上同|扚:引也|𣂉:量也|啇:本也|魡:魚名|㣿:㣿痛|𨑩:至也|杓:柄末橫木
jvT胡狄;檄:符檄說文曰二尺書也胡狄切八|覡:巫覡男曰巫女曰覡|薂:的薂蓮實也見爾雅|𪕯:鼠名|鸄:鳥似烏蒼白色|獥:狼子又音叫音激|椺:鐘椺又胡老切|䚫:以角飾杖策頭
gvT五歷;鷁:水鳥也博物志曰鷁雄雌相視則孕或曰雄鳴上風雌鳴下風亦孕五歷切五|鶂:+上同說文又作𪁌鷊|艗:艗舟舟頭爲鷁首|𠩫:石地惡|虉:虉綬草
GvT徒歷;荻:萑也徒歷切二十九|狄:北狄又姓春秋時狄國之後漢有博士狄山|敵:匹也當也輩也主也|籊:竹竿皃又他歷切|翟:翟雉又姓漢有上蔡翟方進|迪:進也道也蹈也|覿:見也|𧠫:+上同|笛:樂器風俗通云武帝時丘仲所作也晉協律中郎列和善吹笛也|篴:+上同出周禮|糴:市穀米又姓左傳有晉大夫糴茷|籴:+俗|邮:鄉名在高陵|滌:洗也除也淨也|蓧:盛種器也|蔋:草木旱死也|踧:詩曰踧踧周道|䌦:䌦綠色|𩷎:東海有馬𩷎魚|䵂:䵂麩|樀:屋梠又音的|頔:好皃|梑:臧槔爾雅釋木曰狄臧槔是也|䊮:穀粟之名|䢮〈䨤〉:雨也|㹍:特牛|苖:苖蓨草|滷:鹹也|㣙:說文曰行㣙㣙也
FvT他歷;逖:遠也他歷切二十一|逷:+古文|倜:倜儻不羈|趯:跳皃|䢰:+上同|剔:解骨|𠜓:+上同|𧦄〈詆〉:詆詆䛢狡猾|惕:怵惕憂也又愛也|䯜:骨閒黃汁|硩:周禮硩蔟氏掌覆夭鳥之巢又丑列切|摘:發也動也說文曰拓果樹實也一曰指近之也又張革切|踢:䟣踢獸名左右有首出山海經|䚐:說文云目赤也又前歷切|𩮜:說文云鬀髮也|𤈥:望見火皃|蓨:苖蓨草|籊:竹竿皃|悐:勞也|𢞒:敕也|𥉈:失意視皃
NvT則歷;績:緝也功業也繼也事也成也則歷切四|勣:功也|樍:檉木別名|𪄸:鳥也
evT苦擊;燩:乾燥也苦擊切九|𢶡:旁擊|𣪠:攻也漢書云攻苦𣪠淡|喫:喫食|𠿊:+上同|𥍰:矛也|𢿣:䚫𢿣|𢞒:敕也|䍊:吹器
HvT奴歷;惄:心之飢也憂也思也奴歷切四|𧗂〈𧖷〉:+古文|溺:溺水古作㲻又音弱又姓也|愵:憂皃
PvT前歷;寂:靜也安也前歷切五|𡧘:+上同|𡧯:亦同|𠴫:𠴫嗼無聲|䚐:目赤又音逖
DvD莫狄;覓:求也莫狄切二十三|覛:+上同說文曰衺視也|幎:覆也亦作幂|幦:車覆軨也|𧜀:+上同|䮭:馬多惡也|糸:細絲也微也連也|鼏:鼎蓋|羃:覆食巾又羃䍦婦人所戴|汨:汨𤄷水名在豫章屈原所沈之處|㵋:-|漞:+並上同|冂:文字音義云以巾覆從一下垂|䖑:說文云白虎也|蓂:菥蓂|𧱻:白豕黑頭|覭:小皃|䌐:綱繩|𪒄:𪒄𪒑黑青|䈿:𥭓䈿|濗:瀝濗水淺|𧐎:𧊸𧐎蟲名|塓:塗也
CvD扶歷;甓:瓴甓㼾甎扶歷切四|鷿:鷿鷈鳥名似鳧而小足近尾或作鸊|椑:大棺|㱸:㱸㱤欲死之皃
AvD北激;壁:說文云垣也釋名曰壁辟也辟禦風寒也漢官典職曰省中皆胡粉壁紫素界之畫古烈士亦州名本漢宕渠地武德初爲壁州北激切六|鼊:𪓟鼊似龜而漫胡無指爪其甲有黑珠文如瑇瑁可飾物|繴:爾雅繴謂之罿今覆車鳥網也又敷核切|廦:室屋|綼:紷綼絮也|𧲜:𧲜邪獸獸身鳥喙
evj苦鶪;闃:寂靜也苦鶪切二|䠐:踞也
dvj古闃;郹:邑名在蔡古闃切七|狊:說文云犬視皃亦獸名猨屬脣厚而碧色|鶪:伯勞|湨:水名在溫縣|鼳:爾雅曰鼳鼠身長須秦人謂之小驢郭璞云似鼠而馬蹄一歲千斤爲物殘賊|犑:爾雅云犑牛|𠋬:𠋬黠
OvT倉歷;戚:親戚又姓漢有臨轅侯戚鰓倉歷切十一|慼:憂也懼也|𧒕:說文曰夜戒守鼓也|鼜:+上同|鏚:干鏚斧鉞本亦作戚|𪒑:𪒑𪒄色敗|𧠪:𧠪䙾面柔詩本或作戚施|慽:慽痛|𧐶:蟾蜍別名|𦸗:草也|磩:碝䃭石次玉也
ivT許激;赥:笑聲許激切九|䦧〈鬩〉:鬬也恨也戾也又相怨也|𥍠:矛也左思吳都賦云長𥍠短兵亦作𥍟|𤄎:沭遽也|𧨃:私訟|䈪:籮屬|㤸:心不安也|𣣉:去涕|㦦:惶恐
ivj呼狊;𥍟:矛也呼狊切七|砉:砉然物相離聲|瞁:驚視|𥆛:眡也|狊:犬視也|焱:火華又火焰也|殈:鳥卵破也
FvT丑歷;𣤩:痛也丑歷切又丑力切二|𥛚:福𥛚
#職
XwT之翼;職:爾雅云職主也常也博雅云業也字林云記微也又姓周禮有職方氏其後因官爲姓風俗通云漢有山陽令職洪之翼切九|軄:+俗|戠:說文云闕職識字从此|織:組織說文曰作布帛總名|𥋏〈膱〉:油敗|蟙:蟙䘃蟲蝙蝠別名也|𧄕:草名似酸漿亦作蘵|䐈:脯長尺有二寸曰䐈儀禮作膱|樴:樴杙
LwT除力;直:正也又姓楚人直躬之後漢有御史大夫直不疑除力切四|犆:𤚳犆牛也|䐈:肥腸|𡸜:山直
IwT林直;力:筋也又姓黃帝佐力牧之後林直切九|朸:縣名在平原|屴:崱屴山皃|仂:不懈|鳨:似鳧而小亦作𩾜|𠢠:趙魏閒呼棘出方言|𣲒:水凝合皃|𡯄:脛交|𧲡:遼東犬名
KwT恥力;敕:誡也正也固也勞也理也書也急也今相承用勑勑本音賚恥力切十四|勅:+上同|飭:牢密又整備也|淔:水名|趩:行聲|栻:局又木名|侙:意慎侙侙又惕也|𪀦:鸂𪀦|鷘:+上同|恜:從也慎也|慗:從也|遫:張也|荲:蒴𧃔別名|㽚:田器又地名
JwT竹力;陟:升也進也竹力切二|稙:早種禾
bwT乘力;食:飲食大戴禮曰食穀者智惠而巧古史考曰古者茹毛飲血燧人鑽火而人始裹肉而燔之曰炮及神農時人方食穀加米干燒石之上而食之及黃帝始有釜甑火食之道成矣又戲名博屬又用也僞也亦姓風俗通云漢有博士食子公河內人乘力切二|蝕:日蝕也說文云敗瘡也𥼶名曰日月虧曰蝕稍小侵虧如蟲食草木之葉也
QwT相即;息:止也又嬎息也說文喘也亦姓姓苑云今襄陽人又漢複姓前漢書有河內息夫躬相即切十一|㮩:木名|鄎:新鄎縣在豫州|瘜:惡肉|蒠:菲蒠菜|熄:蓄火|𦞜:𦞜肉|䭒:食也|㴧:水|𥰝:簨𥰝|𪄛:鳥食
ZwT常職;寔:實也是也常職切八|湜:水清也|殖:多也生也|植:種植也立志也置也|埴:黏土|𡑠:+古文|㨁:拄杖曰㨁|遈:流行
awT賞職;識:說文云常也一曰知也賞職切十|式:法也敬也用也度也又姓出何氏姓苑|拭:拭刷|𢂑:+上同|軾:車前|飾:裝飾|𥿮:方言云趙魏閒呼經而未緯者曰機𥿮|鉽:鼎鉽也|烒:火皃|𧄹:草名
iwf許極;赩:大赤也許極切五|衋:傷痛其心|䵱:赤黑皃|𥈜:斜視|𢤋:瞋怒皃
UwT士力;崱:崱屴山皃士力切四|𡸦:𡸦嶷|溭:溭淢水勢|萴:草也
fwf渠力;極:中也至也終也窮也高也遠也說文棟也渠力切一
MwT女力;匿:藏也微也亡也隱也陰姦也女力切六|𧈟:蟲食病|𧏾:+上同|㥾:愧也|恧:慙也又女六切|𩺱:魚名
TwT初力;測:度也初力切六|惻:愴也|畟:畟畟陳器狀說文曰治稼畟畟進也詩云畟畟良耜又音即|𦔎:耜也|𡍫:遏遮也|䔴:草名
hwf於力|hwb於力〖棘〗;憶:a念也於力切十七|億:a十万曰億又安也度也|臆:a胷臆|肊:a氣滿|𠶷:a說文曰快也|繶:a絛繩|醷:a梅漿|澺:a水名在上蔡|薏:a薏苡亦蓮心|𦺳:a+上同|䗷:a小蜂|𩍖:a履頭也出韻略|檍:a木名一名木橿也|𣚍:a梓屬|抑:b按也說文作𢑏从反印|𡊁:b地名|癔:a病也
VwT所力;色:顏色所力切十五|㱇:小怖皃|嗇:愛惜也又貪也慳也又積也亦姓說文作𠾂愛歰也从來㐭來麥也來者㐭而藏之故田夫謂之嗇夫㐭音廩|𩍙:車馬絡帶|穡:稼穡種曰稼斂曰穡|薔:薔虞蓼也|轖:字書云車藉交革|繬:緙也縫也|濇:不滑|䉢:篩䉢|嬙:女字|𧒗:蟲也|懎:悲恨|𩕡:頰也|𠢳:助也
ewf丘力;䩯:皮鞭皃丘力切一
dwf紀力;殛:誅也紀力切十一|㥛:急性相背說文曰疾也一曰謹重皃|襋:衣領交也|棘:小棗亦越戟名又箴也羸瘠也又姓文士傳曰棗袛本姓棘其先避難改爲棗氏衛大夫棘子成之後也|亟:急也疾也趣也又音氣|㻷:埤蒼云垂㻷地名出美玉案左傳只作棘|悈:急也又音戒|𡕮:去也|蕀:遠志別名|茍:說文曰自急敕也|𧩦:訥言
lwT與職;弋:橜亦弋射又姓出河東今蒲州有弋氏見姓苑與職切三十四|翊:馮翊郡又輔翊|翌:明日|廙:敬也又音異|黓:皁也爾雅曰太歲在壬曰玄黓|翼:羽翼說文翍也又恭也美也助也亦州名在隴右因翼水爲名又姓晉翼侯之後漢有諫議大夫翼奉|𩙺:+說文同上|𦏵:+古文|䴬:麥䴬|隿:繳射也或作弋|𧃟:藕翹|㚤:婦官也漢有鉤㚤夫人居鉤㚤宮漢書亦作弋|潩:水名出密縣大騩山|杙:果名如棃亦橜也|芅:今羊桃也或曰鬼桃葉似桃而花白|㔴:說文云田器也|𧾰:趨進𧾰如也|𨙒:疾趨|𥡪:黍稷蕃蕪皃亦作翼|蛡:蛡蛡蟲行皃|𢦭〈𤬩〉:瓶瓮骨也|𢖺:心動|瀷:水聚|𢎀:缺盆骨也|𠥦:大鼎|熼:火光|釴:鼎附耳在外也|𤼌:痒𤼌淫𤼌|𧑌:蟲也|𦔜:耕也|䄩:禾䄩|𢓀:行𢓀|䘝:衣䘝|䣧:酒色
NwT子力;即:就也今也舍也半也說文作即食也亦姓風俗通有單父令即賣又漢複姓有城陽相齊人即墨成子力切十六|卽:+上同|稷:五穀之摠名一曰黍屬周禮注云社稷土穀之神有德者配食焉共工氏之子曰句龍食於社有厲山氏之子曰柱食於稷湯遷之而祀棄俗作稷亦姓后稷之後|㮨:木名似松|㹄:牛名|蝍:蝍蛆蟲名又子結切|楖:楖裴縣在魏郡裴房非切|畟:又初力切|𨂢:𨂢蹙迫急|鯽:魚名|𤠎:犬生三子|堲:風堲又子栗切|䐚:膏澤|唧:唧聲也|𪃹:𪃹鴒亦作䳭|揤:揤裴縣在魏郡裴房非切
AwL彼側;逼:迫也彼側切十|偪:+上同|皕:二百|幅:行縢名|楅:束也又音福|䮠:駝䮠|湢:湢㳁水驚起勢也|䫾:風也|㘠:姓也又閉也|皀:皀粒
kwr雨逼;域:居也邦也雨逼切十四|蜮:短狐蟲又音或|罭:魚網|棫:木叢|㚜:字林云大力皃|𪂉:鶝𪂉鳥|𦈸:瓦器|琙:人名漢有公孫琙|𪑝:羔裘之縫又音洫|緎:+縫也亦同上|䮙:馬走|魊:小兒鬼|淢:溭淢波勢|𦱂:叢也
iwr況逼;洫:溝洫況逼切十四|侐:靜也|䦗:+上同|閾:門限|𨵨:+古文|𥄎:舉目使人|㰲:㰲聲吹皃|𤷇:頭痛|𪑝:羔裘之縫|緎:+縫也亦同上|𦑌:羽聲|𠷾:聲也|淢:疾流|𧹭:赭色
BwL芳逼;堛:土凷芳逼切十三|愊:悃愊至誠|踾:蹋地聲|𤗚:坼也|𩜰:飽皃|揊:擊聲|稫:稫稄禾密滿也|副:析也禮云爲天子削瓜者副之巾以絺|畐:逼滿也|䦼:地裂也亦作𨺤|𢾇:𢾇敂|㽬:多也密也|疈:周禮曰以疈辜祭四方百物
SwT阻力;稄:稫稄阻力切十一|𥟔:一本作此|𣅔:日𣅔又旁也傾也不正也|𢯩:打也|仄:仄陋說文云側傾也|昃:日在西方|㳁:湢㳁水勢|萴:廣雅云附子一歲曰萴子二歲曰烏喙三歲曰附子四歲曰烏頭五歲曰天雄|側:傍側|夨:說文云傾頭也|𠨮:+籀文
CwL符逼;愎:很也符逼切八|腷:腷臆意不泄也|𤐧:火乾肉也|𥻅:+上同|𤗚:𤗚版出通俗文|馥:香又音復|踾:蹋地聲|鶝:鶝𪂉鳥
gwf魚力;嶷:岐嶷詩曰克岐克嶷魚力切五|薿:茂盛|㘈:說文曰小兒有知也引詩云克岐克㘈|懝:有所識也|觺:觺岳角皃
PwT秦力;堲:疾也秦力切又將七切又牆資切三|垐:以土增道|𢯩:打也又音側
JwT丁力;𡮞:丁力切又丁六切三|𣮊:毛少𣮊𣮊|𢕚:𢕚滴水少
DwL亡逼;䁇:細視也亡逼切一
YwT昌力;瀷:水潦積聚昌力切又音翼二|𦔫:字統云耕也
#德
ExT多則;德:德行又惠也升也福也亦州名秦爲齊郡地漢爲平原郡武德初爲德州因安德縣以名之多則切九|惪:+古文|𢛳:觻𢛳縣名在張掖漢書作得|䙷:說文取也今作㝵同|得:得失|淂:水皃又丁力切|𨁽:行碍碍|𣌏:約也|𠮊:取也
NxT子德;則:法則子德切三|𠟻:+古文|𠟭:+籀文
IxT盧則;勒:鄴中記曰石虎諱勒呼馬勒爲轡盧則切十二|肋:脅肋𥼶名曰肋勒也所以檢勒五藏也|扐:筮者著蓍指閒|仂:禮祭用數之仂|艻:蘿功香草|朸:說文曰木之理也平原有朸縣|𤨕:美石次玉|玏:+上同|泐:凝合|㔹:功大說文曰材十人也|阞:地脉理坼|竻:竹根
FxT他德;忒:差也他德切六|㧹:打也|慝:惡也|貣:從人求物也|𥊸:𥊸䁿欲臥也|㥂:驚㥂㥂
exT苦得;刻:刻鏤又剝也苦得切五|克:能也勝也說文作𠅏肩也|剋:剋己又必也殺也急也|勀:自強|𡞢:罵女老𡞢亦作娔
GxT徒得;特:特牛又獨也亦姓左傳晉大夫特宮徒得切九|貣:假貣謂從官借本賈也亦從人求物也又音忒|𧈩:食禾葉蟲|𧎢:+上同|樴:杙也|𤙰:鈍也|棏:木名|鴏:鴏𪃑又徒戴切|螣:螣蛇
ixT呼北;黑:北方色呼北切三|潶:水名在雍州|㱄:唾聲
DxD莫北;墨:筆墨又姓墨翟是也亦即墨縣名莫北切十二|默:說文曰犬暫逐人也又靜也或作嘿|冒:干也又莫報切|䘃:蟙䘃蟲即蝙蝠|纆:索也|万:虜複姓北齊特進互俟普俟音其|𢄏:+方言同上|艒:艒𦩤釣艇|𡣫:姓也|䁇:暫視|𥊷〈䁿〉:𥊸䁿欲臥也|𤲰:𤱢𤲰
PxT昨則;賊:盜也說文作𧵪敗也昨則切七|𧵪:+上同|鱡:烏鱡魚崔豹古今注云一名河伯度事小史|鰂:+上同|蠈:食禾節蟲亦作賊|𣿐:博雅云𣿐測也|𦽒:草名
QxT蘇則;塞:滿也窒也隔也蘇則切又蘇載切五|𡫼:+上同見說文|寨:安也|㥶:實也書曰剛而㥶|𢥛:+上同見說文
AxD博墨;北:南北亦奔也又高麗姓又漢複姓七氏左傳衛大夫北宮貞子莊子有北門成漢有北唐子真治京氏易世本云晉有高人隱於北唐因以爲氏晏子云齊有北郭先生名騷古有北人無擇清身絜己疾世之濁自投清冷之淵姓苑有北鄉北野氏博墨切二|𧉥:蟲似蟹四足
CxD蒲北;菔:蘆菔蒲北切十三|蔔:+上同|僰:僰道縣在犍爲又丁壯皃亦醜也亦作𧟱又符逼切|匐:匍匐|𠣵:+上同|踣:斃也倒也又作仆|仆:倒也|菩:草名又音蒲|垘:填塞|䞳:僵也又孚豆切|䵗:治黍豆潰葉也|𧟱:農夫賤稱|𢫯:擊也
jxj胡國;或:不定也疑也胡國切五|惑:迷惑|蜮:蟲名短狐狀如鼈含砂射人久則爲害生南方說文云有三足以氣射害人玄中記云長三四寸蟾蜍鸑鷟鴛鴦悉食之|魊:鬼魊旋風|𡿿:水流皃
dxj古或;國:邦國又姓太公之後左傳齊有國氏代爲上卿古或切一
hxT愛黑;餩:噎聲愛黑切二|殕:殪殕
jxT胡得;劾:推窮罪人也俗作𠜨胡得切一
HxT奴勒;䘅:蟲名似䖟而小青班色齧人奴勒切三|䎪:穀䎪見齊人民要術|𣉘:字統云埃也又日光也
dxT古得;裓:釋典有衣裓古得切三|𢧧:𢧧䎪草生|孂:竦身皃出玉篇
OxT七則;墄:階齒七則切一
BxD匹北;覆:匹北切三|𧕡:𧕡蝗蟲名|𠣾:𠣾匐
ixj呼或;𢃤:巾帛從風聲呼或切二|𥇙:睡目
#緝
O1T七入;緝:績也七入切六|葺:修補|諿:和也|𧚨:襟緣亦作緁|𪔪:鼓無聲|咠:咠咠譖言也說文曰聶語也
Z1T是執;十:數名是執切四|什:篇什又什物也|拾:收拾又掇也斂也|褶:袴褶
X1T之入;執:持也操也守也攝也說文作𡙕捕辠人也之入切六|汁:汁瀋也液也|瓡:縣名在北海|䥍:廣雅云羊箠也|𡠗:字統云至也|慹:怖也
R1T似入;習:學也因也說文作習數飛也又姓出襄陽晉有習鑿齒似入切十三|襲:因也及也重也合也入也又掩襲說文曰左衽袍也|隰:原隰亦州名左傳曰重耳居蒲即隰川縣故蒲城是也漢爲蒲子縣後魏齊周之閒爲沁州隋爲隰州以州前有泉下濕蓋取下濕之義名之又姓齊有大夫隰朋|鰼:爾雅云鰼鰌今泥鰌也又山海經云鰼魚狀如鵲而有十翼鱗在翼端聲如鵲|騽:馬豪骭又驪馬黃脊|飁:颯飁大風|槢:堅木名|𪄶:鴣𪄶鳥名|𦸚:𦸚茵水草出埤蒼|𥱵:簷𥱵修船具也|䒁:+上同|褶:袴褶|霫:雴霫大雨
P1T秦入;集:聚也會也就也成也安也同也眾也本作雧字林云羣鳥駐木上亦州名漢宕渠縣梁爲東巴州恭帝爲集州以有集水名之又姓風俗通云漢有外黃令集一秦入切九|輯:和也|檝:舟檝又音接|亼:說文云三合也从入一象三合之形合僉之類皆从此又子入切|𠦫:說文云詞之集也|𦺴:菩也|鏶:鐵鍱|慹:怖也|箿:箿覆也又子立切
c1T人執;入:得也內也納也人執切二|廿:說文云二十并也今作卄直以爲二十字
h1X伊入;揖:揖遜又進也說文云攘也一曰手著胷曰揖伊入切二|挹:酌也
a1T失入;溼:水霑也失入切三|濕:+上同見經典又他合切|䏉:牛耳動也
N1T子入;㗱:㗘㗱噍皃子入切㗘昔博十一|潗:泉出|䌖:合也又蠻夷貨名|湒:雨皃|咠:又七入切|蓻:草生多皃|𧚨:襟緣|葺:茨也|䁒:眨䁒|𥠋:稠𥠋𥠋|㠍:負秦山名
f1b其立;及:至也逮也連也辝也其立切七|𨕤:+古文|𦶍:冬瓜|苙:白芷又力急切|䲯:䲯鳩鳥|笈:負書箱又其劫切|㧀:戶鍵
L1T直立;蟄:蟄蟲又藏也直立切六|䐲:肉半生半熟|俋:俋俋然耕皃出莊子|㙷:下入又直輒切|㞏:㞚㞏前後相次也㞚初立切|譶:㒊譶言不止也
J1T陟立;縶:繫馬陟立切四|𩅀:小濕|𩢏〈馽〉:馬絆|𡂣〈𡁉〉:口𡁉𡁉
I1T力入;立:行立又住也成也又漢複姓魯有賢人立如子力入切九|䶘:齧聲|粒:米粒|笠:雨笠本草呼破笠爲敗天公也|鴗:水狗爾雅謂之天狗注云小鳥青似翠食魚江東呼爲水狗|苙:白芷又其立切|䇐:臨也|岦:岦岌山皃|砬:石藥
d1b居立;急:急疾說文作㤂褊也居立切十一|汲:汲引也又縣名在衛州又姓漢有中尉汲黯河東人|給:供給又姓出姓苑|伋:孔伋字子思|級:等級說文云絲次序也亦階級禮曰拾級聚足俗作𨸚|芨:烏頭別名|𦳌:+上同|㽺:病也|彶:彶遽也|皀:穀香|𩾳〈𪀐〉:𪀐鵖鳥名
g1b魚及;岌:高皃魚及切二|㱞:危也
e1b去急;泣:無聲出涕去急切三|㬤:欲燥|湆:羹汁
Q1T先立;𩎕:小兒履也先立切五|卌:字統云插糞杷說文云數名今直以爲四十字|霫:字林云雨皃又奚霫東北夷名|𧿅:𧿅膝坐|㗩:㗩㗩忍寒聲
V1T色立;歰:說文曰不滑也色立切八|澀:+上同|澁:+俗|鈒:戟也鋋也|雭:小雨聲|濇:不滑|㒊:不及|翜:疾飛
i1b許及;吸:內息許及切十二|噏:+上同|歙:說文曰縮鼻也後漢有來歙又舒涉切州名|翕:火炙一曰起也又斂也合也動也聚也盛也|𧬈:𧬈䛅語聲也|潝:水流皃|熻:熻熱|嬆:莊嚴|翖:漢有翖侯|𨝫:地名|闟:戟名曰闟|𪅲:鳥名
S1T阻立;戢:止也斂也阻立切九|𥊬:淚出皃|𧤏:角多皃|𧥄:+上同|㗊:眾口|蕺:菜名|濈:和也|𠿠:喻也|霵:雨下又士邑切
h1b於汲;邑:縣邑周禮曰四井爲邑又漢複姓有邑由氏楚大夫養由氏之後避仇改焉於汲切八|悒:憂悒|唈:嗚唈短氣|裛:裛香又於怯切|浥:濕潤|䓃:䓃菸茹熟|䭂:食䭂|𦶂:𦶂𦮾
K1T丑入;湁:湁潗沸皃丑入切三|雴:大雨|漐:汗出皃
k1b爲立;煜:文皃爲立切四|曄:暐曄又筠輒切|熠:熠燿螢火又羊入切|騽:馬豪骭又音習
l1T羊入;熠:熠燿螢火羊入切二|孴:多皃
M1T尼立;孨:戢孨聚皃尼立切五|㵫:潗㵫水文皃|𣲷:濕𣲷|㘝:㘝㘝私取皃又女洽切|𦮾:𦶂𦮾
U1T仕戢;霵:暴雨皃仕戢切二|䯂:盛眾皃
C1L皮及;𩾳〈𪀐〉:𪀐鵖亦作鴔皮及切一
A1L彼及;鵖:彼及切二|皀:穀香也
T1T初戢;㞚:㞚㞏初戢切四|𡍪:𡍪㙷重累土也|䙄:重緣|𢕬:行皃
Y1T昌汁;卙:字統云會聚也昌汁切一
#合
j2T侯閤;合:合同亦器名亦六合天地四方對也又州名秦爲巴郡宋爲宕渠郡後魏置合州蓋涪漢二水合流之處因以名之又姓左傳宋有大夫合左師又漢複姓高帝功臣表有合傅胡害侯閤切又音閤十一|郃:郃陽縣在同州又虜複姓後魏書大莫干氏後改爲郃氏又音閤|榙:榙𣝋果名似李出埤蒼|䢔:䢔遝行相及也|㭘:㭘棔木也|詥:諧也亦作合|耠:耕也|𡇶:會也|𪘁:𪘁齧聲也|𦳬:草|盒:盒盤覆也
d2T古沓;閤:爾雅曰小閨謂之閤古沓切十九|鴿:鳥名|合:合集又音䢔|敆:合會也|鉿:二尺鋌|鮯:魚名六足鳥尾出山海經|蛤:蚌蛤|郃:水名又縣名又音䢔|浩:浩亹地名亹音門|匌:周帀也|頜:頜頷頤傍|佮:併佮聚也|㧁:閉戶曰㧁|𣭝:𣭝𣬬目睫長|㭘:劒柙又巨業切|㠷:以席載穀|鞈:防捍|韐:韎韐大帶|𢂷:+𢂷口亦同上
E2T都合;答:當也亦作荅都合切十二|畣:爾雅曰俞畣然也|𨅞:跛行皃|撘:打也出音譜|荅:正名云小豆|褡:橫褡小被|㜓:面㜓姶皃|㾑:肥㾑㽺出字林|嗒:舐嗒|𤝰:犬食|㿯:皮㿯|㯚:㯚𣝋木名
Q2T蘇合;趿:進足蘇合切十一|颯:風聲|靸:小兒履或作𩎕|𩎕:+上同|馺:馬行疾|霅:廣雅曰雨霅霅又音讋|卅:說文云𠦃三十也今作卅直以爲三十字|㚫:媕㚫女字|𣬬:𣭝𣬬眼睫長|𢕬:眾行皃|鈒:鈒鏤
G2T徒合;沓:重也合也又語多沓沓也又虜複姓後魏書沓盧氏後改爲沓氏徒合切十八|誻:譐誻亦作噂𠴲|遝:䢔遝|㧺:指㧺|㭼:柱上木也|涾:沸溢|𩣯:馺𩣯馬行|龖:龍飛之狀|𠉤:儑𠉤不著事也|譶:疾言|𣝋:榙𣝋|蹹:齧蹹|䂿:舂已復擣之爲䂿|䜚:妄言|𦂀:𦂀子絹出字林|𦾽:東魯人呼蘆菔曰菈𦾽|𧌏:䗘𧌏蟲|眔:目相見
F2T他合;錔:器物錔頭他合切二十二|嚃:歠也|䓠:菜生水中|㛥:安皃說文曰俛伏也一曰意伏也|踏:著地|𢃕:帳上覆|鞜:革履|𦑇:𦒆𦑇飛皃|漯:水名在平原|濕:+上同|㹺:犬食|𦧟:+上同|䶀:鼓聲也|佮:合也|䵬:晉書有兗州八伯太山羊曼爲䵬伯|𪘁:食也|𨌭:車釭𨌭也|㭼:柱㭼頭|䍝:相罯䍝出字林|濌:積厚|𪂌:鳥名|䈋:竹名
P2T徂合;雜:帀也集也猝也穿也說文曰五綵相合也徂合切七|韴:斷聲|磼:磼嶫山高|雥:羣鳥|䕹:戶簾|𨅔:止也又才含切|䣟:亭名在貝丘
N2T子荅;帀:遍也周也子荅切十|迊:+上同|𠯗:入口|噆:蚊蟲噆人|𣤶:𣤶𣣴聲|魳:魚名|䍼:羊腌|嘁:歍嘁|沞:湆沞纔濕|䞙:𧼎䞙急走
I2T盧合;拉:折也敗也摧也盧合切十一|搚:+上同|㩉:亦同|摺:敗也|𦒆:𦒆𦑇飛皃|磖:磖磼|𪇹:𪇹䳴初飛皃|菈:菈𦾽魯人呼蘿蔔|𣤊:𣤊歁不滿|㕇:石聲|𤛊:𤛊拉
H2T奴荅;納:內也又姓出何氏姓苑奴荅切八|䪏:腝皃|蒳:字統云香草異物志云葉如栟櫚而小子似檳榔可食|軜:驂馬內轡繫軾前者|衲:補衲紩也|魶:魚名似鼈無甲有尾口在腹下|妠:姶妠聚物|㨥:打㨥
e2T口荅;溘:至也奄也依也口荅切七|𣩄:𣩄死見楚詞本作溘|㧁:閉戶聲|𠩧〈厒〉:山左右有岸|䆟:䆟合相當也|匌:匌帀也|歁:歁歞癡皃
h2T烏合;姶:美好皃烏合切十三|𤸱:短氣|罨:網又一劫切|罯:覆蓋也又烏敢切|媕:女有心媕媕也|㔩:㔩彩婦人髻飾花也|庵:庵低又屋|𨂁:跛𨂁|𩋊:車具又小兒履名𩋊皻|𩇠:調色𦘕繒出郭調字指|搕:以手盍也又搕𢶍糞也|鞥:皮裹角也|佮:姓也
i2T呼合;欱:大歠也呼合切四|㽺:病劣皃|𣣹:𣣹瘶|㾑:寒㾑
g2T五合;𣊡:日中見絲凡作㬎同五合切十|礏:磼礏|哈:魚多皃|儑:𠉤儑|𡀾:眾聲|砐:峇砐|礘:動礘礘亦作硆|㾑:寒㾑病|䑥:船皃|魥:魚名
O2T七合;䟃:走也赴會也七合切二|㜗:婪㜗
O2T士〈七〉合;遪:裹遪士合切一
h2T烏荅;唈:爾雅云僾唈也烏荅切一
#盍
j3T胡臘;盍:何不也說文作盇覆也爾雅合也胡臘切十|闔:閶闔說文云門扇也一曰閉也|𨶩:+俗|嗑:噬嗑卦名|蓋:苫蓋|𧪞:靜也|篕:籧篨也|㧁:纂文云姓也|𨜴:說文云地名也|熆:吹火也
I3T盧盍;臘:臘蜡盧盍切十四|臈:+俗|𪙷:齧聲|䶘:+上同|鑞:錫鑞|蠟:蜜蠟|䗶:+俗|擸:折也又擸𢶍破壞也|𥀰:𥀰㿴皮瘦寬皃|𪇹:𪇹䳴鳥飛|搚:摺搚相和|𦒦:𦒦𦑲飛初起皃|𦅶:繒䋵|邋:邋遢行皃
E3T都搕〈榼〉;㿴:𥀰㿴都搕切十一|耷:大耳|𢴄〈搨〉:手打也|㩉:+上同|矺:擲地聲又竹亞切亦作䂝|𠞈:相著聲一曰𠞈鉤也|笚:竹相擊|䓠:菜生水中又荷覆水|褡:橫褡小被|𩝣:𩝣𩚛|䪚:熱䪚䪚
F3T吐盍;榻:牀也吐盍切十九|㯓:+上同|𦪙:兩槽大船|毾:毾㲪|鰈:比目魚別名|魼:+上同|鰨:魚名似鮎四足|𦶑:𦶑布|傝:傝隷亦傝䢇儜劣又傝𠎷不謹皃|狧:犬食|𦧭:+上同|𧪦:𧪦𧪞多言𧪞古盍切|𦐇:飛皃|鞳:鏜鞳鐘聲又他荅切|塔:浮圖|搭:摸搭|嗒:嗒然忘懷也|遢:邋遢不謹事|𩥑:𩧆𩥑馬行不進
i3T呼盍;𣣹:大啜呼盍切三|𩵢:魶𩵢魚名出山海經|㽺:肥㽺
H3T奴盍;魶:魚名奴盍切三|笝:纜舟竹索也|𩚛:𩝣𩚛
G3T徒盍;蹋:踐也徒盍切十|躢:+上同見公羊傳|闒:門樓上屋說文曰樓上戶也|𤒻:爛也墮也|𧮑:𧪦𧪞妄語也|譫:多言又作𧪟|䍇:瓶|䳴:𪇹䳴鳥飛|䈳:窻扇|𦑲:𦑲𦒦
Q3T私盍;𠎷:傝𠎷不謹皃私盍切七|𠿓:𠿓𠿓食皃|𢶍:搕𢶍糞又才盍切|卅:三十|𨆂:𨆂𨆂行皃|靸:靸鞋|𩐅:𩐅攱起也出新字林
g3T五盍;儑:傝儑不著事也五盍切二|𥋙:𥋙睡
P3T才盍;䪞:惡也又姓出纂文今北海有之才盍切二|𢶍:擸𢶍和雜
d3T古盍;䫦:䫦車頷骨古盍切八|𧪞:多言又音盍|嗑:+上同|蓋:姓也漢有蓋寬饒字書作𨜴|閘:閉門|鉀:鉀鑪|䗘:䗘𧌏|𨜴:地名
e3T苦盍;榼:酒器也苦盍切六|磕:石聲|𧛾:𧛾襠|㕎:㕎崩損也|䶀:鼓聲䶀䶀|𨍰:車聲
h3T安盍;鰪:鰪鱂魚名安盍切四|盦:說文云覆蓋也|廅:山旁穴|𤸱:短氣也又烏合切
O3T倉雜〖臘〗;囃:助舞聲也倉雜切三|𥗭:石多皃|䵽:鼓聲
d3T居盍;砝:石聲居盍切二|𪁍:鳥名
X4T章盍;譫:多言也章盍切一
#葉
l4T與涉;葉:枝葉又姓吳志孫堅傳有都尉葉雄與涉切又式涉切十|楪:楪榆縣名在雲中|揲:度揲|鍱:銅鍱|偞:偞偞輕薄美好皃|枼:薄也|㯿:柶端又力葉切|煠:煠爚|䈎:篇簿書䈎說文籥也|殜:病也
N4T即葉;接:交也持也合也會也又姓三輔決錄有接昕子即葉切十一|椄:續木|睫:目睫釋名曰睫插也插於眶也說文作䀹目旁毛也|䀹:+上同|楫:舟楫|檝:+上同|婕:婕妤亦作倢伃|菨:莕菨水余草可食|𣶏:𣶏㳧纔有水皃|鯜:魚名|䈉:竹䈉又所甲切
a4T書涉;攝:兼也錄也書涉切八|灄:水名在西陽|葉:縣名在汝州又余涉切|歙:黟歙又許乃切|欇:爾雅欇虎櫐郭璞云今虎豆纏蔓林樹而生莢有毛刺又音涉|𥍉:目動之皃|弽:射決張弓又童子佩之|韘:+上同
Z4T時攝;涉:歷也徒行渡水也亦漳水別名涉縣是也又姓左傳晉大夫涉佗時攝切四|𣻣:+上同出說文|欇:虎櫐也又書涉切|䤮:鐵䤮
I4T良涉;獵:取獸白虎通曰四時之田摠名爲獵爲田除害也尸子曰虙羲氏之世天下多獸故教人以獵也良涉切二十二|鬣:須鬣說文曰髮鬣鬣也|㲱:+長毛說文同上又作䝓|躐:踐也|䁽:目暗|𣋲:日暗|擸:說文曰理持也|儠:說文云長壯儠儠也|犣:牛牡又旄牛名|䪉:䪉馬靼也|㼲:蹈瓦聲|䉭:編竹爲之|鱲:魚名|𡂏:齧聲|𥪂:羸𥪂|𠠗:削也擇也|邋:邁也|㯿:柶端木也|䜲:谷名|䃳:䃳崨山之連接|巤:本也又鼠毛|獦:戎姓俗作田獦字非
P4T疾葉;捷:獲也佽也疾也剋也勝也成也說文曰獵也軍獲得也春秋傳曰齊人來獻戎捷又姓漢書藝文志捷子齊人著書疾葉切八|疌:說文疾也|寁:速也亟也|倢:斜出也又利也便也|崨:崨䃳山連延也|踕:足疾|䌖:合也遠方物也|誱:多言也又口誱
L4T直葉;䐑:細切肉也直葉切三|㙷:下入又直立切|殜:殗殜病
h4b於輒;㪑:㪑𣀳於輒切四|裛:又於及於怯二切|腌:鹽腌魚|𦀖:𦀖䌜補衣
M4T尼輒;聶:姓也楚大夫食采於聶因以爲氏尼輒切十六|躡:蹈也履也登也急也|鑷:鑷子|𤴘:織𤴘|㚔:說文曰所以驚人也一曰大聲今作幸同睪圉報執之類從此|睪:伺視也說文云令吏將目捕罪人本羊益切|帇:說文曰手之捷巧也|𩣘:馬步疾也|籋:箝也|䌜:𦀖䌜補衣|𣌍:小煗也|㸎:+上同|踂:足不相過|𥬬:竹𥬬|䳖:鳥飛|𣀳:㪑𣀳
Y4T叱涉;謵:小語叱涉切九|𣠞:樹葉動皃|㚲:輕薄|詀:詀讘細語|䧪:女子態又前卻䧪媚也|喢:多口|㤴:偛㤴小人皃|㳧:𣶏㳧纔有水皃|𦛖:𦣀𦛖
c4T而涉;讘:詀讘又狐讘縣名在清河而涉切五|顳:顳顬鬢骨|喦:多言|囁:口動|𦣀:動𦣀
X4T之涉;讋:多言也之涉切十二|囁:口動又而涉切|懾:怖也心伏也失常也失氣也亦作慴|慴:伏也懼也怯也|慹:司馬彪莊子注云慹不動皃又音捻|霅:說文云霅霅震電皃又蘇合胡甲丈甲三切|摺:摺曡也|𣠞:風動皃|䜆:言疾|謺:拾人語也|襵:襞也|䝕:梁之良豕
O4T七接;妾:不娉七接切十|緁:連緁說文曰緶衣也|䌌:+說文同上|𠟪:續也|鏶:炙鐵|淁:水名|鯜:魚名|𣠺:飯臿|穕:土穕農具也|踥:踥踥往來皃
K4T丑輒;鍤:綴衣針丑輒切六|煠:爚煠|㤴:㤴休也出字書|𩂻:𩂻霎小雨|䈎:籥䈎|𥯥:竹葉
f4b其輒;衱:禮記注云衱交領其輒切五|极:驢上負版|笈:負書箱也|㭘:劒柙|𩾳〈𪀐〉:𪀐鵖戴勝別名亦作鴔
J4T陟葉;輒:專輒說文曰車相倚也陟葉切八|耴:耴耳國名說文曰耳垂也|襵:衣襵又之涉切|𦯍:爾雅釋草云𦯍小葉|𢬴:拈也|鮿:婢鮿魚即青衣魚|㡇:說文曰衣領耑也|㭯:木小葉
k4b筠輒;曄:光也筠輒切又爲立切七|曅:+上同|饁:餉田|燁:煒燁火盛|爗:說文盛也|皣:草木白華|瞱:目動皃
e4b去涉;𤷾:少氣也去涉切一
V4T山輒;萐:萐莆瑞草山輒切萐箑歃霎並又所洽切六|箑:扇也|歃:歃血|霎:小雨|喢:多言又齒涉切|㰼:愒欲
d4b居輒;𦀖:縫也居輒切二|鵖:鳥名
h4X於葉;魘:惡夢於葉切又於琰切七|擪:持也指按也|靨:面上靨子|嬮:女字|𣄉〈𣃳〉:掩也|厭:厭伏亦惡夢又於琰切|𣚕:葉動皃
#怗
F5T他協;怗:安也服也靜也他協切十一|帖:券帖又牀前帷也|𪔧:鼓無聲或作𦗺|鉆:鉆著物|䩞:鞍䩞|貼:以物質錢|跕:跕屣又丁協切|蝶:蝶𧌏|䑜:小舐曰䑜|呫:甞也|㡇:衣領
j5T胡頰;協:和也合也胡頰切十|叶:+古文|勰:思也|綊:說文曰䋊綊也|挾:懷也持也藏也護也|俠:任俠又姓戰國策有韓相俠累|𠗉:𠗉𠗨冰凍|劦:同力|𤙒:𤙒犍|𢂐:束帶
d5T古協;頰:頰面也古協切九|𩠣:+籀文|鋏:長鋏劒名|筴:箸筴又古洽切|梜:+上同見禮|莢:蓂莢榆莢又姓出平陽世本有晉大夫莢成僖子也|蛺:蛺蝶|唊:唊唊多言也亦作䛟|𥞵:𥞵穧穧音劑
e5T苦協;愜:心伏也又快也苦協切八|㥦:+上同|悏:快也|㾜:說文曰病息也|匧:藏也|篋:箱篋|㤲:說文曰思皃|㛍:得志㛍㛍又呼協切
G5T徒協;牒:書版曰牒又虜姓後魏書牒云氏後改爲云氏徒協切三十|喋:便語|蹀:躞蹀|諜:反閒又譜諜也|堞:城上垣|𨈈:小走聲|氎:細毛布|𣯉:+上同|褺:重衣|曡:重也墮也明也累也積也說文云楊雄說以爲古理官決罪三日得其宜乃行之从晶从宜亡新以爲曡从三日太盛改爲三田亦州名禹貢梁州之域自秦至魏諸羌據焉周武帝始逐諸羌乃置曡州蓋以山重曡而名之|疊:+上同|䥡:廣雅鋌也|慴:懾也說文懼也|䠟:說文曰䠟足也|㥈:安也又齒廉切|𥷕:𥷕簸|牃:牀版|褋:襌衣|墊:地名在巴中|惵:思懼皃|褶:袷也又似入切|𨐁:車聲|蝶:蛺蝶|𠗨:𠗉𠗨又丈甲切|䴑:鳥名狀似鵲赤黑色兩首四足可以禦火出山海經|揲:摺揲|㩹:掛㩹|𪑧:𪑧黔首出音譜|䁋:目䁋|𤗨:𤗨治
H5T奴協;苶:病劣皃莊子曰苶然疲役奴協切又音涅十五|埝:陷聲|暬:晦冥又私列切|𩐭:聲絕|捻:指捻|錜:小釘|慹:不動皃又之涉切|敜:說文云塞也書曰敜乃穽|攝:攝然天下安出漢書|㘨:深也|籋:小箝亦作銸|鑈:+上同|惗:相憶|𩋏:鞍𩋏薄也出字林|菍:草
Q5T蘇協;燮:和也說文从言又炎蘇協切十六|屧:屐也履中薦也|屟:+上同|躞:躞蹀|韘:韘韝射具|𤫉:石似玉|𤏻:熟也文字指歸从辛又炎|鞢:䩞鞢鞍具出新字林|徢:徢行走皃|𦔼:使也又人耴切|𤗈:𤗈牒小契|蜨:蛺蜨蟲名|𧕊:+上同|䕈:草名|𡞘:𡞘洽|𦩌:𦩌舟行也
I5T盧協;㼲:蹈瓦聲也盧協切四|𪑧:竹裏黑也|𡂩:𡂩𠲷多言|𦖩:耳垂
E5T丁愜;聑:耳垂皃丁愜切十二|𠲷:多言|𢬴:打也|笘:折竹箠也|喋:血流皃又田叶切|㝪:下也|跕:墮落|䩞:䩞鞢鞍具|𧚊:衣領|㑙:低㑙也|𨓊:𨓊䢡走也|涉:血流皃又時懾切
P5T在協;䕹:草簾在協切一
N5T子協;浹:洽也通也徹也浹辰十二日也子協切三|𠗉:𠗉𠗨又音狎|㼪:半瓦
i5T呼牒;弽:弓弽呼牒切四|䁋:閉一目|㛍:少氣皃|偞:偞卑
Q5T先頰;䢡:𨓊䢡走也先頰切一
#洽
j6T侯夾;洽:和也合也霑也侯夾切十四|䨐:+上同|狹:隘狹|陜:-|陿:+並上同|祫:祭名|峽:巫峽山名|硤:硤石縣亦州名秦將白起攻楚燒夷陵即其地魏武於此置臨江郡後魏爲拓州取開拓之義周以居三峽之口因爲峽州也|𢈙:廦也|𪘘:齒曲生又缺也|𤲍:相著|烚:火烚|珨:蜃器|䞩:走皃
e6T苦洽;恰:用心苦洽切十|掐:爪掐|䁍:目陷|㓣:入也|䶢:齧咋皃又噍聲|帢:士服狀如弁缺四角魏武帝製魏志注云太祖以天下凶荒資財乏匱擬古皮弁裁縑帛以爲帢合乎簡易隨時之義以色別其貴賤本施軍飾非爲國容|𠕣:-|𢂿:+並上同|㡊:亦上同埤蒼云帽也|𣁴:𣁴斫
U6T七〈士〉洽;𨖷〈箑〉:行書七洽切六|煠:湯煠|䮢:䮢䮢馬驟|渫:水名出上黨郡|牐:下牐閉城門也|𧼰:行疾也
d6T古洽;夾:持也古洽切十五|郟:郟鄏地名也又郟城縣在汝州又姓左傳鄭大夫郟張|筴:箸也鍼箭具又音頰|韐:韎韐韋蔽膝|𢂷:+上同|跲:躓礙|袷:複衣說文曰衣無絮也|裌:+上同|䀫:眼細暗|餄:餄餅|㿓:㿓蹄足病|䶢:噍聲也又苦沿切|鵊:鳥名|䩡:履根|鞈:又公合切
S6T側洽;眨:目動側洽切六|㞚:薄楔|偛:偛㑳小人皃又楚立切|䙄:䙄略絜朿皃|𥀈:皺𥀈皮老|䛽:䜞䛽多言
T6T楚洽;插:刺入楚洽切十|臿:春去皮也或作疀俗作臿|疀:+上同爾雅曰𣂁謂之疀郭璞云皆古鍫鍤字|鍤:+上同|扱:取也獲也舉也引也說文收也|笈:負書箱又其劫切|㛼:疾言失次也|㷅:火乾|喢:口喢|𤜯:狗食
M6T女洽;㘝:手取物俗作𡆴女洽切四|𡤙:𡤙𡤙美皃|㗙:喢㗙小人言薄相|㑳:偛㑳
i6T呼洽;䶎:䶎齁鼻息呼洽切四|欱:欱甞|㰰:氣逆|敮:盡也
V6T山洽;霎:小雨山洽切七|歃:歃血又山輒切|箑:扇之別名|䈉:+上同|萐:萐莆瑞草王者孝德至則萐莆生於廚其葉大如門不搖自扇飲食|喢:喢㗙小人言也|𧳛:獸名
J6T竹洽;劄:刺著竹洽切三|𠍹:𠍹𦤻忽觸人也|𧉫:斑身小蟲
h6T烏洽;𨂁:跛行皃烏洽切四|凹:下也或作容|浥:波下又濕皃|圔:圔窊聲下
gvR五夾｟洽｠〈冷〉;䀴:埤蒼云視皃五夾切一
K6T丑㘝;𥃐:味調肉菜出文字音義丑㘝切一
#狎
j7T胡甲;狎:習也說文曰犬可習也胡甲切十一|翈:翮上短羽|霅:眾言聲又丈甲切霅陽部在樂浪又音颯|𠗉:𠗉𠗨冰凍相著|柙:檻也所以藏虎兕也出說文|匣:箱匣也|𧆥:虎習搏也|𩉾〈𦾏〉:𦾏𧃹|𢘉:𢘉喜|炠:火皃又呼甲切|笚:竹名
L7T丈甲;𠗨:𠗉𠗨丈甲切六|喋:啑喋鳧鴈食也啑所甲切|擖:押擖重接皃|霅:霅陽縣名又水名在吳興|𤁳:水名|鞢〈𧃹〉:𦾏𧃹
h7T烏甲;鴨:水鳥或作𪀌𩿼𪁗烏甲切六|壓:鎮也降也笮也壞也|庘:屋壞也|䆘:人神脉刺穴|閘:開閉門出說文|押:押署文字指歸云押字才能也
d7T古狎;甲:甲兵又狎也鎧也亦甲子爾雅曰太歲在甲曰閼逢又姓左傳鄭大夫甲石甫古狎切十|胛:背胛|梜:木理亂|押:押籬壁也|𥑐:山側|鉀:鎧屬今單作甲|玾:玉名|𨒇:漢書人名|𠩘:𠩘𠪮|𩌍:𩌍䩖胡履
V7T所甲;翣:翣形如扇以木爲匡禮天子八諸侯六卿大夫四士二世本曰武王作翣所甲切八|𧲌:豕母|啑:啑喋|帹:面衣|翜:捷也|䬊:風疾|㞚:薄㞚|𧻵:行𧻵𧻵
i7T呼甲;呷:喤呷眾聲說文曰吸呷也呼甲切四|譀:誇誕|䛅:𧬈䛅語聲|𣢗:𣢗𣢗鼻息
#業
g8f魚怯;業:事也大也敘也次也始也敬也嚴也說文作𢄁大版也所以飾縣鐘鼓捷業如鋸齒以白畫之象其鉏鋙相承也詩曰巨業維樅又爾雅曰大版謂之業郭璞云築牆版也俗作㸣魚怯切十五|㸣:+見上注|鄴:縣名在相州又姓風俗通云漢有梁令鄴風|驜:驜驜馬高大|嶪:岌嶪山皃|𠟪:續也|䧨:危皃|㗼:㗼動皃|𠄅:引也|𩑃:樂也|䲜:魚盛|𢢜:懼也|𩼋:魚名|鸈:鳥名知人吉凶|澲:橫水大版
i8f虛業;脅:胷脅虛業切九|𣣲:𣣲氣|𣢩:+上同|愶:以威力相恐也|㢵:弓弽皃|嗋:口嗋嚇莊子曰余口張而不嗋|熁:火氣熁上|𣹩:水流|拹:說文曰摺也一曰拉也
e8f去劫;怯:畏也去劫切九|㹤:+上同|抾:挹也|呿:臥聲又音去|魥:以竹貫魚爲乾出復州界|胠:胠篋見莊子|𠩂:厓𠩂|㾀:病劣|𤴼:欠氣
d8f居怯;劫:強取也說文曰人欲去以力脅止曰劫或曰以力止去曰劫俗作刧居怯切九|衱:衣領|袷:+上同|蜐:南越志云石蜐生石上形如龜腳得春雨則生也|跲:躓也又巨業切|鉣:帶鐵|砝:硬也|𦀖:𦀖䌜縫也|䀷:視皃
h8f於業;腌:鹽漬魚也於業切十四|䱒:+上同|罨:魚網又烏合切|裛:書囊也文字集略云裛坌衣香又於及於輒二切|䎨:耕種|殗:殗殜不動皃|㡋:幧頭也|浥:潤也|㪑:㪑𣀳相著|䤶:椎䤶田甲器|𩋊:車具又於合切|𦤡:𦤡臭也|餣:餌也粢也|䁆:閉目
l8T余業;殜:殗殜亦作𣩫余業切二|𩐱:樂器
f8f巨業;跲:躓也巨業切五|㭘:劒匣|昅:㬤昅|极:极插|笈:書笈又初洽其輒二切
#乏
C9P房法;乏:匱也房法切三|泛:水聲又孚梵切|姂:好皃
A9P方乏;法:則也數也常也又姓左傳齊襄王法章之後秦滅齊子孫不敢稱故以法爲氏宣帝時徙三輔代爲二千石後漢有扶風法雄法子真並有傳方乏切二|灋:+上同
B9P孚法;𥎰:矢皃孚法切一
e8f起法;猲:恐受財史記云恐猲諸侯起法切又呼葛切二|姂:好皃
M8T女法;䎎:飛上皃女法切三|𣹵:㬁𣹵水皃|𡷝:靜𡷝
K8T丑法;𦑣:𦑣䎎飛上皃丑法切一
`;

    const by原書小韻 = new Map();
    const by小韻 = new Map();
    (function 解析資料() {
        let 原書小韻號 = 0;
        let 韻目 = '';
        for (const line of raw資料.slice(0, -1).split('\n')) {
            if (line.startsWith('#')) {
                韻目 = line.slice(1);
                continue;
            }
            原書小韻號 += 1;
            const [音韻, 內容] = line.split(';');
            const 各音切 = [];
            for (const 音切 of 音韻.split('|')) {
                const 編碼 = 音切.slice(0, 3);
                const [反切, 直音] = 音切.slice(3).split('=');
                各音切.push([編碼, 反切 || null, 直音 || null]);
            }
            let 原書字號 = 0;
            let 增字號 = 0;
            const 各條目 = [];
            const 各釋義參照 = [];
            for (const 條目str of 內容.split('|')) {
                const [, 字頭, 字頭說明, 細分號, 釋義參照, 釋義] = /^(.+?)(?:【(.*)】)?:([a-z]?)([+-]?)([^a-z+-]*)$/.exec(條目str);
                const 小韻號 = String(原書小韻號) + 細分號;
                const 細分index = 細分號 ? 細分號.charCodeAt(0) - 'a'.charCodeAt(0) : 0;
                const [音韻編碼, 反切, 直音] = 各音切[細分index];
                if (字頭.startsWith('［')) {
                    增字號++;
                }
                else {
                    原書字號++;
                    增字號 = 0;
                }
                const 條目 = {
                    來源: '廣韻',
                    音韻編碼,
                    字頭,
                    字頭說明: 字頭說明 || null,
                    小韻號,
                    小韻字號: `${原書字號}` + (增字號 ? `a${增字號}` : ''),
                    韻目,
                    反切,
                    直音,
                    釋義: 釋義 || null,
                    釋義上下文: null,
                };
                各條目.push(條目);
                各釋義參照.push(釋義參照);
            }
            generate釋義上下文(各條目, 各釋義參照);
            by原書小韻.set(原書小韻號, 各條目);
            for (const 條目 of 各條目) {
                insertInto(by小韻, 條目.小韻號, 條目);
            }
        }
    })();
    function generate釋義上下文(各條目, 各釋義參照) {
        const 參照string = 各釋義參照.map(x => x || ' ').join('');
        // 一個無參照條目，後可接若干「上」參照，每項亦均可前接若干「下」參照
        for (const match of 參照string.matchAll(/-* (?:-*\+)*/g)) {
            const matchString = match[0];
            const pos = match.index;
            const len = matchString.length;
            if (len === 1) {
                continue;
            }
            const 上下文 = 各條目.slice(pos, pos + len).map(({ 字頭, 字頭說明, 小韻字號, 釋義 }) => ({
                字頭,
                字頭說明,
                小韻字號,
                釋義,
            }));
            for (const 條目 of 各條目.slice(pos, pos + len)) {
                條目.釋義上下文 = 上下文;
            }
        }
    }

    var __$2 = /*#__PURE__*/Object.freeze({
        __proto__: null
    });

    /** 按原書順序遍歷全部廣韻條目。 */
    function* iter條目() {
        for (const 原書小韻 of iter原書小韻()) {
            yield* 原書小韻;
        }
    }
    /**
     * 遍歷全部小韻號。
     *
     * 細分小韻（見 {@linkcode get小韻}）拆分為不同小韻，有各自的小韻號。
     */
    function iter小韻號() {
        return by小韻.keys();
    }
    /**
     * 依小韻號獲取條目。
     *
     * 部分小韻含多個音韻地位，會依音韻地位拆分，並有細分號（後綴 -a、-b 等），故為字串格式。
     *
     * @returns 該小韻所有條目。若小韻號不存在，回傳 `undefined`。
     * @example
     * ```typescript
     * > TshetUinh.資料.廣韻.get小韻('3708b');
     * [
     *   {
     *     音韻地位: 音韻地位<影開三B蒸入>,
     *     字頭: '抑',
     *     字頭說明: null,
     *     小韻號: '3708b',
     *     小韻字號: '15',
     *     韻目: '職',
     *     反切: '於力〖棘〗',
     *     直音: null,
     *     釋義: '按也說文作𢑏从反印',
     *     釋義上下文: null,
     *     來源: '廣韻'
     *   },
     *   {
     *     音韻地位: 音韻地位<影開三B蒸入>,
     *     字頭: '𡊁',
     *     字頭說明: null,
     *     小韻號: '3708b',
     *     小韻字號: '16',
     *     韻目: '職',
     *     反切: '於力〖棘〗',
     *     直音: null,
     *     釋義: '地名',
     *     釋義上下文: null,
     *     來源: '廣韻'
     *   }
     * ]
     * ```
     */
    function get小韻(小韻號) {
        return by小韻.get(小韻號)?.map(條目from內部條目);
    }
    /**
     * 遍歷全部小韻（細分小韻均拆分）。即對資料中全部小韻執行 {@linkcode get小韻}。
     */
    function* iter小韻() {
        for (const 小韻號 of iter小韻號()) {
            yield get小韻(小韻號);
        }
    }
    /** 原書小韻總數。細分小韻（含多個音韻地位的小韻）不拆分，計為一個小韻。 */
    const 原書小韻總數 = by原書小韻.size;
    /**
     * 依原書小韻號獲取條目。
     *
     * 細分小韻（含多個音韻地位的小韻）不拆分，視為同一小韻。
     *
     * @param 原書小韻號 數字，應在 1 至 {@linkcode 原書小韻總數}（含）之間。
     * @returns 該原書小韻所有條目。若無該小韻，則回傳 `undefined`
     */
    function get原書小韻(原書小韻號) {
        return by原書小韻.get(原書小韻號)?.map(條目from內部條目);
    }
    /**
     * 遍歷全部原書小韻（細分小韻不拆分）。即對資料中全部原書小韻執行 {@linkcode get原書小韻}。
     */
    function* iter原書小韻() {
        for (let i = 1; i <= 原書小韻總數; i++) {
            yield get原書小韻(i);
        }
    }

    var __$1 = /*#__PURE__*/Object.freeze({
        __proto__: null,
        get原書小韻: get原書小韻,
        get小韻: get小韻,
        iter原書小韻: iter原書小韻,
        iter小韻: iter小韻,
        iter小韻號: iter小韻號,
        iter條目: iter條目,
        原書小韻總數: 原書小韻總數
    });

    const m字頭檢索 = new Map();
    const m音韻編碼檢索 = new Map();
    (function 建立廣韻索引() {
        const by原貌 = new Map();
        for (const 原書小韻 of by原書小韻.values()) {
            for (const 條目 of 原書小韻) {
                insertInto(m音韻編碼檢索, 條目.音韻編碼, 條目);
                const 各校勘 = parse字頭詳情(條目.字頭).reverse();
                const 字頭原貌 = 各校勘.pop();
                for (const 校勘 of 各校勘) {
                    const 字 = 校勘.slice(1, -1);
                    if (字) {
                        insertInto(m字頭檢索, 字, 條目);
                    }
                }
                if (字頭原貌) {
                    insertInto(by原貌, 字頭原貌, 條目);
                }
            }
        }
        for (const [字頭原貌, 各條目] of by原貌.entries()) {
            insertValuesInto(m字頭檢索, 字頭原貌, 各條目);
        }
    })();
    // NOTE
    // 此為臨時補充字音（以及作為將來《切韻》資料功能支持的測試）。
    // 等到切韻資料準備好後，會換成完整資料。
    // 小韻號、對應廣韻小韻號亦均為暫定編號，完整資料中會修正。
    (function 字音補充() {
        const by字頭 = new Map();
        for (const [描述, 字頭, 小韻號, 小韻字號, 對應廣韻小韻號, 韻目, 反切, 釋義] of [
            ['明三C陽平', '忘', '774', '4', '822', '陽', '武方', '又武放反'],
            ['云合三B真去', '韻', '2275', '1', '32419', '震', '永賮', '永賮反一'],
        ]) {
            const 音韻編碼 = encode音韻編碼(音韻地位.from描述(描述));
            const record = {
                來源: '切韻',
                音韻編碼,
                字頭,
                字頭說明: null,
                小韻號,
                小韻字號,
                對應廣韻小韻號,
                韻目,
                反切,
                直音: null,
                釋義,
                釋義上下文: null,
            };
            insertInto(by字頭, 字頭, record);
            insertInto(m音韻編碼檢索, 音韻編碼, record);
        }
        for (const [字頭, 各條目] of by字頭.entries()) {
            prependValuesInto(m字頭檢索, 字頭, 各條目);
        }
    })();
    /** 遍歷內置資料中全部有字的音韻地位 */
    function* iter音韻地位() {
        for (const 音韻編碼 of m音韻編碼檢索.keys()) {
            // NOTE 音韻地位s in the builtin data are guaranteed to be valid
            yield decode音韻編碼unchecked(音韻編碼);
        }
    }
    /**
     * 查詢音韻地位對應的資料條目。
     *
     * @param 地位 待查詢的音韻地位
     *
     * @returns 陣列，為所有查到的條目
     *
     * 若音韻地位有音無字，則回傳空陣列。
     *
     * @example
     * ```typescript
     * > 地位 = TshetUinh.音韻地位.from描述('影開二銜去');
     * > TshetUinh.資料.query音韻地位(地位);
     * [ {
     *   音韻地位: 音韻地位<影開二銜去>,
     *   字頭: '𪒠',
     *   字頭說明: null,
     *   小韻號: '3177',
     *   小韻字號: '1',
     *   韻目: '鑑',
     *   反切: null,
     *   直音: '黯去聲',
     *   釋義: '叫呼仿佛𪒠然自得音黯去聲一',
     *   釋義上下文: null,
     *   來源: '廣韻'
     * } ]
     * ```
     */
    function query音韻地位(地位) {
        return m音韻編碼檢索.get(encode音韻編碼(地位))?.map(條目from內部條目) ?? [];
    }
    function query字頭(字頭, ...args) {
        let 異體字頭 = [];
        let 選項 = { 上下文: true };
        while (args.length && args.at(-1) === undefined) {
            args.pop();
        }
        if (args.length === 1) {
            if (Array.isArray(args[0])) {
                異體字頭 = args[0];
            }
            else {
                選項 = { ...選項, ...args[0] };
            }
        }
        else if (args.length > 1) {
            if (args[0] != null) {
                異體字頭 = args[0];
            }
            if (args[1]) {
                選項 = { ...選項, ...args[1] };
            }
        }
        function lookupInternalIndex(字頭) {
            return m字頭檢索.get(字頭)?.map(條目from內部條目) ?? [];
        }
        function keyFor條目(條目) {
            return `${條目.來源}/${條目.小韻號}/${條目.小韻字號}`;
        }
        function compare條目Order(條目1, 條目2) {
            if (條目1.來源 !== 條目2.來源) {
                return 條目1.來源 < 條目2.來源 ? -1 : 1;
            }
            const 原書小韻號1 = 條目1.原書小韻號;
            const 原書小韻號2 = 條目2.原書小韻號;
            if (原書小韻號1 !== 原書小韻號2) {
                return 原書小韻號1 - 原書小韻號2;
            }
            const [原書字號1, 增字號1] = 條目1.小韻字號詳情;
            const [原書字號2, 增字號2] = 條目2.小韻字號詳情;
            return 原書字號1 !== 原書字號2 ? 原書字號1 - 原書字號2 : 增字號1 - 增字號2;
        }
        function* flattenExpanded條目(各條目) {
            for (const 條目 of 各條目) {
                yield* 條目.expand釋義上下文();
            }
        }
        function filterAndCollectUnique(各條目, filter = () => true) {
            const map = new Map();
            for (const 條目 of flattenExpanded條目(各條目)) {
                const key = keyFor條目(條目);
                if (!map.has(key) && filter(key, 條目)) {
                    map.set(key, 條目);
                }
            }
            const sorted = [...map.values()].sort(compare條目Order);
            return [sorted, map];
        }
        const lookupPrimary = lookupInternalIndex(字頭);
        let resultPrimary;
        let primaryKeys;
        if (選項.上下文) {
            [resultPrimary, primaryKeys] = filterAndCollectUnique(flattenExpanded條目(lookupPrimary));
        }
        else {
            // NOTE m字頭檢索 is already sorted
            resultPrimary = lookupPrimary;
            primaryKeys = new Set(resultPrimary.map(keyFor條目));
        }
        let lookupVariants = 異體字頭.flatMap(lookupInternalIndex);
        if (選項.上下文) {
            lookupVariants = flattenExpanded條目(lookupVariants);
        }
        const [resultVariants] = filterAndCollectUnique(lookupVariants, key => !primaryKeys.has(key));
        return [...resultPrimary, ...resultVariants];
    }

    var __ = /*#__PURE__*/Object.freeze({
        __proto__: null,
        iter音韻地位: iter音韻地位,
        query字頭: query字頭,
        query音韻地位: query音韻地位,
        切韻: __$2,
        廣韻: __$1
    });

    /**
     * 預定義的常用表達式，可用於 `音韻地位.屬於`。
     *
     * @example
     * ```typescript
     * > const { 分開合韻, 合口韻 } = TshetUinh.表達式;
     * > const 地位 = TshetUinh.音韻地位.from描述('羣合三C文平');
     * > 地位.屬於`${分開合韻} 非 ${開合中立韻}`
     * true
     * ```
     *
     * @module 表達式
     */
    /** 一等韻 */
    const 一等韻 = 等韻搭配.一.join('') + '韻';
    /** 二等韻 */
    const 二等韻 = 等韻搭配.二.join('') + '韻';
    /** 三等韻（注意：拼端組時為四等） */
    const 三等韻 = 等韻搭配.三.join('') + '韻';
    /** 四等韻 */
    const 四等韻 = 等韻搭配.四.join('') + '韻';
    /** 一三等韻 */
    const 一三等韻 = 等韻搭配.一三.join('') + '韻';
    /** 二三等韻（注意：拼端組時為二四等） */
    const 二三等韻 = 等韻搭配.二三.join('') + '韻';
    /**
     * 韻內分開合口的韻
     */
    const 分開合韻 = 呼韻搭配.開合.join('') + '韻';
    /**
     * 僅為開口的韻（含之、魚韻及效、深、咸攝諸韻）
     */
    const 開口韻 = 呼韻搭配.開.join('') + '韻';
    /**
     * 僅為合口的韻
     */
    const 合口韻 = 呼韻搭配.合.join('') + '韻';
    /**
     * 開合中立韻（東冬鍾江模尤侯）
     */
    const 開合中立韻 = 呼韻搭配.中立.join('') + '韻';

    var _____ = /*#__PURE__*/Object.freeze({
        __proto__: null,
        一三等韻: 一三等韻,
        一等韻: 一等韻,
        三等韻: 三等韻,
        二三等韻: 二三等韻,
        二等韻: 二等韻,
        分開合韻: 分開合韻,
        合口韻: 合口韻,
        四等韻: 四等韻,
        開口韻: 開口韻,
        開合中立韻: 開合中立韻
    });

    exports.壓縮表示 = ____;
    exports.表達式 = _____;
    exports.資料 = __;
    exports.音韻地位 = 音韻地位;

}));
//# sourceMappingURL=tshet-uinh.js.map

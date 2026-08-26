# 章节 Spec + 钩子 + 场景卡 + 冲突控制符（Chapter Spec）

> 章节 spec 是"施工图"。写之前必须先有 spec，spec 决定正文质量。

## Spec 的核心作用

```
设定（什么世界 + 什么角色）
  + 大纲（什么故事 + 什么节拍）
  + 风格锚定（什么声音）
  ↓
Spec（本章节怎么写）
  ↓
正文
```

**没有 spec 的写作 = 没有施工图的施工 = 大概率返工。**

## Spec 的 12 字段（升级版）

来自原 skill + 联网取经 + 实践升级。

### 完整 Spec 模板

```yaml
chapter:
  num: 50
  title: "第 50 章 名字"
  summary: "200 字以内摘要"
  word_target: 5000-7000
  type_focus: "本章节拍类型"

# ── 1. 状态追踪（前后对比）──
before_state:
  characters:
    - name: "角色"
      state: "状态"
      location: "位置"
      emotion: "情绪"
      known_info: ["目前知道的信息"]
      relationship_to_others: "对其他角色态度"
      heart_triggered: "本章触动了心脏哪个层次"
  plot_hooks: ["未回收伏笔"]
  time: "时间"
  weather: "天气"

after_state:
  characters:
    - name: "角色"
      state: "新状态"
      location: "新位置"
      emotion: "情绪变化方向"
      new_known: ["本章新增的已知信息"]
      relationship_changes: ["关系变化"]
      heart_shift: "欲望推进/恐惧被触发/伤口被触碰？"
  plot_advances: ["伏笔回收", "新伏笔埋下"]

# ── 2. 必发生事件 ──
must_happen:
  - event: "关键事件"
    prerequisites: ["角色需要先知道/拥有/到达什么"]
    causes: "事件起因（前文哪件事直接导致）"
    consequences: "事件后果（触发下一章的什么）"

# ── 3. 叙事密度 ──
narrative_density: "中"  # 高/中/低

# ── 4. 张力曲线 ──
tension_curve:
  - {position: 0, value: 3, note: "铺垫"}
  - {position: 50, value: 8, note: "高潮"}
  - {position: 100, value: 5, note: "收尾"}

# ── 5. 关键场景 ──
key_scenes:
  - "场景 1"
  - "场景 2"

# ── 6. 钩子布局（升级版）──
hook_layout:
  opening:
    type: "承接上章后果"   # 承接后果/POV 切换/震惊声明/新角色入场/规则确认
    description: "如何接住上章结尾钩"
  internal:
    - type: "悬念升级"      # 悬念升级/线索投放/人际张力/能力展示/情感微时刻
      at_position: 40
  ending:
    type: "话说一半"        # 话说一半/动作中断/情绪断崖/身份暗示/危机逼近/新设定甩出
    dual_hook: true         # 是否叠加情绪钩形成双钩
    description: "结尾钩具体内容"

hook_type: "问题钩"          # 本章主导钩子：问题钩/危机钩/秘密钩/伏笔钩/反转钩
hook_layer: "信息钩"         # 钩子层级：信息钩/情绪钩/认知钩
hook_strength: "中"          # 强度：强/中/弱
new_hooks:
  - "结尾钩简述"
hook_rhythm_note: "大钩子章"  # 中等钩子章/大钩子章/缓冲章

# ── 7. 场景卡 +/- 标记法 ──
scene_emotion_shift:
  start: "+"                 # +正面 / -负面
  end: "-"
  shift_point: 60            # 情绪转折位置
  note: "主角从自信到被碾压"

# ── 8. 核心冲突 >< 标记法 ──
core_conflict:
  type: "主角 >< 反派"        # 主角vs反派/配角/环境/自己
  description: "主角试图夺取宝物，反派设下陷阱"
  resolution: "主角失败但获得关键信息"

# ── 9. 冲突控制符（升级项，来自联网取经）──
conflict_markers:
  - position: 10
    type: "IN"                # IN/IR/EN/SO/DE/SU 内心/人际/环境/社会/宿命/超自然
    intensity: 2              # 1-5 强度
    note: "主角内心矛盾（去不去救她）"
  - position: 50
    type: "IR"
    intensity: 4
    note: "主角 vs 反派正面冲突"
  - position: 85
    type: "DE"
    intensity: 3
    note: "主角面对命运抉择"

# ── 10. 多维功能标注（升级项）──
function_annotations:
  emotion: ["压抑", "爆发"]   # 情感维度
  conflict: ["IR:4", "DE:3"]  # 冲突维度
  rhythm: "中-快"             # 节奏维度
  info: "揭示"                # 信息维度：揭示/隐藏/暗示
  structure: "转折"            # 结构维度：伏笔/回收/转折/过渡
  voice_anchor: "ANCHOR_01"   # 风格锚点 ID

# ── 11. 角色语感约束（对话+叙事段共用）──
voice_constraints:
  - character: "主角"
    speech_style: "短句/口语/方言词"
    forbidden_words: ["禁止词"]
    behavior_ticks: ["习惯性小动作"]
    thought_pattern: "思考习惯"

# ── 12. 伏笔追踪 ──
foreshadowing:
  recovered:
    - "第 23 章埋的伏笔，本章回收"
  new_planted:
    - "本章新埋伏笔，预计第 80 章回收"
```

## 12 字段详解

### 字段 1：状态追踪

**为什么必填**：防止"前后矛盾"——AI 写小说最常犯的错。

**检查**：
- 上章 after_state 的 known_info 是否有遗漏？
- 本章新角色登场是否在设定中已存在？
- 角色位置是否一致？

### 字段 2：必发生事件

**3 检查**：
- prerequisites 是否在前文满足？
- causes 是否对应前文具体事件？
- consequences 是否在下一章承接？

**反模式**：
- ❌ 主角突然知道一个前文从未铺垫的信息
- ❌ 敌人突然降智
- ❌ 事件没有 consequences，下一章又自己造一个

### 字段 3：叙事密度

| 等级 | 段长 | 信息密度 | 适用 |
|------|------|---------|------|
| 高 | 200-300 字 | 信息密集 | 高潮/转折/动作戏 |
| 中 | 150-250 字 | 推进:描写 1:1 | 默认 |
| 低 | 50-100 字 | 多留白 | 缓冲章/情绪章/纯文戏 |

**密度 vs 节奏关系**：
- 高密度 = 紧（适合高潮）
- 中密度 = 中（默认）
- 低密度 = 缓（适合缓冲）

### 字段 4：张力曲线

**5 段式**（推荐）：
```yaml
tension_curve:
  - {position: 0, value: 3, note: "承接"}
  - {position: 25, value: 5, note: "铺垫"}
  - {position: 50, value: 8, note: "高潮"}
  - {position: 75, value: 4, note: "缓冲"}
  - {position: 100, value: 6, note: "结尾钩"}
```

**反模式**：
- ❌ 平直曲线（全程没起伏）
- ❌ 倒 V 曲线（开头高潮后面软）
- ❌ M 型曲线（高潮太多反而没高潮）

### 字段 5：关键场景

**3 要素**：
- 场景目的（为什么需要这个场景）
- 场景参与者（谁出场）
- 场景结果（产生什么变化）

**示例**：
```yaml
key_scenes:
  - 主角初入拍卖会（建立世界观+遇反派）
  - 拍卖会冲突（与反派正面交锋）
  - 神秘人出手救场（埋伏笔+留悬念）
```

### 字段 6：钩子布局（升级版）

**三层级**（来自原 skill，升级自联网取经）：

| 层级 | 本质 | 驱动力 | 使用频率 | 示例 |
|------|------|--------|---------|------|
| 信息钩 | 给新信息只给一半 | 理性：想知道 | 大量 | "那张纸上只有一行字：凶手就是——" |
| 情绪钩 | 制造必须释放的情绪，掐断 | 本能：憋得慌 | 重要节点 | 主角被当众羞辱，攥拳→断章 |
| 认知钩 | 颠覆读者已有认知 | 颠覆：全乱了 | 每卷 1-2 次 | "真凶是 B，A 是为他而死的人" |

**五类型**（来自原 skill）：

| 类型 | 机制 | 推荐度 | 章节位置 |
|------|------|-------|---------|
| 问题钩 | 信息缺口→求知欲 | ★★★★★ | 结尾/开头 |
| 危机钩 | 威胁→生理留存 | ★★★★ | 结尾/开头/贯穿 |
| 秘密钩 | 隐藏信息→优越感 | ★★★★ | 贯穿/结尾/中间 |
| 伏笔钩 | 前置细节→原来如此 | ★★★★★ | 贯穿长线 |
| 反转钩 | 预期违背→多巴胺 | ★★★★慎用 | 卷末 |

**每章三段设计**：

| 位置 | 字数 | 功能 | 常用钩子 | 禁忌 |
|------|------|------|---------|------|
| 开头钩 | 前 500 字 | 接上章+建方向 | 承接后果/POV 切换/震惊声明 | 长段回顾上章 |
| 内部钩 | 1-2 个 | 推进+爬坡 | 悬念升级/线索投放/情感微时刻 | 连续纯日常无推进 |
| 结尾钩 | 最后 3 行 | 制造追读 | 话说一半/动作中断/情绪断崖 | "灭顶之灾"水字数 |

**铁律**：
- 连续 2 章无内部钩 = 可测量的读者流失
- 章末双钩叠加（信息+情绪） > 单一钩子

### 字段 7：场景卡 +/- 标记法

来自《救猫咪》：

```yaml
scene_emotion_shift:
  start: "+"  # 场景开始情绪基调
  end: "-"    # 场景结束情绪基调
  shift_point: 60  # 转折位置（百分比）
  note: "主角从自信到被碾压"
```

**反模式**：
- ❌ 全章 +/- 不变（无戏剧价值）
- ❌ shift_point 太早或太晚（应在 50-70%）

### 字段 8：核心冲突 >< 标记法

```yaml
core_conflict:
  type: "主角 >< 反派"  # 主角vs反派/配角/环境/自己
  description: "主角试图夺取宝物"
  resolution: "主角失败但获得关键信息"
```

**铁律**：一章一个核心冲突，清晰可见。

**反模式**：
- ❌ 全章无核心冲突
- ❌ 多个冲突混杂（不知道主线）
- ❌ 冲突无 resolution（写到一半就跳走）

### 字段 9：冲突控制符（升级项）

来自联网取经的可机读标注：

```
[类型代码:强度]

类型代码：
- IN 内心冲突
- IR 人际冲突
- EN 环境冲突
- SO 社会冲突
- DE 宿命冲突
- SU 超自然冲突

强度等级：
- 1 微弱（隐性存在）
- 2 轻度（初步显现）
- 3 中度（明确对立）
- 4 重度（激烈对抗）
- 5 极端（生死存亡）
```

**示例**：
```yaml
conflict_markers:
  - {position: 10, type: "IN", intensity: 2, note: "主角内心矛盾"}
  - {position: 50, type: "IR", intensity: 4, note: "主角 vs 反派"}
  - {position: 85, type: "DE", intensity: 3, note: "命运抉择"}
```

**功能**：
- 评审时机械检测（冲突密度）
- 避免一章全是 IR 4（对话吵架型）
- 保持冲突多样性

### 字段 10：多维功能标注（升级项）

```yaml
function_annotations:
  emotion: ["压抑", "爆发"]   # 情感维度
  conflict: ["IR:4", "DE:3"]  # 冲突维度
  rhythm: "中-快"             # 节奏维度
  info: "揭示"                # 信息维度
  structure: "转折"            # 结构维度
  voice_anchor: "ANCHOR_01"   # 风格锚点 ID
```

**6 维度齐全 = Spec 完整**。

### 字段 11：角色语感约束

来自原 skill 的核心：

```yaml
voice_constraints:
  - character: "主角"
    speech_style: "短句/口语/方言词"
    forbidden_words: ["抽象词", "现代用语"]
    behavior_ticks: ["摸鼻子", "攥衣角"]
    thought_pattern: "直觉型/分析型"
```

**写时约束**（写正文时同步执行）：
1. 遮掉名字读对话 → 分不清谁在说话 → 重写
2. 行为模式与对话段一致
3. 方言/口语元素贯穿对话+叙事
4. 情绪外化不靠形容词

### 字段 12：伏笔追踪

**回收时机**：
- 短伏笔（章节级）：3-5 章内回收
- 中伏笔（卷级）：5-15 章内回收
- 长伏笔（全书级）：30-50 章内回收

**追踪表维护**：
每章 spec 必须列出本章回收+新埋的伏笔，引擎自动维护总表。

## 5 约束前置注入（写正文前必做）

来自原 skill + 升级，spec 完成后注入生成上下文：

**A. 角色活人感约束**（从 voice_constraints 提取）
**B. 角色已知信息约束**（从 after_state.known_info 提取）
**C. 叙事密度约束**（从 narrative_density 提取）
**D. 去 AI 味前置约束**（来自 13_anti_ai.md）
**E. 《救猫咪》六大金科玉律**（来自 save_the_cat_rules）

## Spec 写作的 4 大陷阱

| 陷阱 | 症状 | 解法 |
|------|------|------|
| Spec 太简单 | 只写 200 字摘要就动笔 | 12 字段全填 |
| Spec 太详细 | 写 5000 字 spec，等于写两份小说 | spec 控制在 1500-2500 字 |
| Spec 不连贯 | 本章 spec 与前 3 章不衔接 | 自动读前 3 章 spec |
| Spec 无差异 | 所有章 spec 都一个样 | 不同节拍不同模板 |

## 自动化：Spec 校验与跨章巡检

```bash
# 校验单章 spec 的 12 字段完整性与合法性
python scripts/spec_check.py 规格/第050章.yaml

# 批量校验整本 spec
python scripts/spec_check.py 规格/ --batch

# 跨章一致性巡检（伏笔总表/人物漂移/已知信息因果链/设定矛盾）
# 详见 references/15_continuity.md
python scripts/continuity_check.py --project . --report
```

> 注：spec 由作者/AI 依据本文件 12 字段模板撰写（见 templates/章节spec模板.yaml），不自动生成正文。
> 跨章连贯性由 `continuity_check.py` 自动维护，spec 只负责"本章施工"，巡检负责"全书对账"。

## 实战：30 分钟完成一章 Spec

### Step 1（5 分钟）：读取前 3 章 Spec

理解人物状态、伏笔、节奏。

### Step 2（10 分钟）：填 12 字段

按 12 字段模板填空，重点：
- before_state/after_state
- must_happen
- 钩子布局
- 核心冲突

### Step 3（10 分钟）：连贯性检查

- prerequisites 满足？
- 角色 known_info 正确？
- 伏笔对应？

### Step 4（5 分钟）：写时约束提取

5 约束前置注入清单。

## 实战样例：一章从 spec 到评审（端到端）

以「第 30 章 玉佩现」为例，展示最小闭环：

**Step A — 填 spec（12 字段节选）**
```yaml
chapter:
  num: 30
  title: "第 30 章 玉佩现"
before_state:
  characters:
    - name: 林修远
      known_info: ["师门被灭真相", "玉佩来历"]
after_state:
  characters:
    - name: 林修远
      new_known: ["玉佩纹路=师父遗物"]
core_conflict:
  type: "主角 >< 环境"
  resolution: "玉佩认主，引出追杀"
hook_type: "伏笔钩"
foreshadowing:
  new_planted: ["玉佩纹路暗示师父身份，预计第 80 章回收"]
```

**Step B — 写正文（节选）**
> 林修远指尖抚过玉佩表面的裂纹，那是一道他极熟悉的纹路——和师父剑柄上的一模一样。他呼吸一滞。

**Step C — 自检（spec_check + continuity_check）**
```bash
python scripts/spec_check.py 规格/第030章.yaml
python scripts/continuity_check.py --project . --report
```

**Step D — 评审（6 角色 + 朱雀 + 声音一致性）**
详见 references/10_review.md。评审通过后，用 `novel_state.py log --chapter 30 --word 5200` 记入进度，并让 `continuity_auto` 在每卷末自动对账。

## 一句话总结

**Spec 是"这本章节的施工图"，不是"写作提示"。** 12 字段全填 = 正文不返工。Spec 偷懒 = 后续返工翻倍。30 分钟填 spec 省 3 小时返工，这是性价比最高的创作习惯。

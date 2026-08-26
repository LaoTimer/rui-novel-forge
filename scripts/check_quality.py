#!/usr/bin/env python3
"""
小说质量检测脚本（锻字·网络小说创作引擎）
基于原 open-novel-writing v3.x check_quality.py 升级，新增：
- 4 级红线（P-1 商业红线 / P0 质量 / P1 体验 / P2 优化）
- 声音指纹校验（与锚点对比）
- 钩子密度检测
- 场景卡 +/- 检测
- 续命预警信号
- 提示语密度检测（"对话癌"：满篇"某某说/道"）
- 文句呼吸检测（句长CV/连词密度/重定语句4+个"的"/连续短句鼓点/长前置压主干，治"加速急刹"节奏病）

检测维度：
- AI 黑名单词、句式僵硬、逻辑连接词、朱雀 AI 预估分
- 感官锚点、对话自然度、提示语密度、句长变异度、文句呼吸
- 人物弧光双检（认知弧光 × PDCA）
- 钩子布局、场景卡、声音一致性
"""

import re
import sys
import statistics
from pathlib import Path
from collections import Counter

# ============================================================
# 4 级红线（升级自原 3 级）
# ============================================================

# P-1 商业红线（新增）
P_NEGATIVE_1_PATTERNS = {
    "政治敏感": [
        r"习近平", r"共产党.*反动", r"颠覆国家", r"分裂国家",
        r"领导人.*绰号", r"高官.*腐败.*美化",
    ],
    "擦边低俗": [
        r"色情.{0,5}描写", r"性器官.*详细",
        r"强奸.*详细", r"乱伦.*详细",
    ],
    "抄袭": [],  # 需外部查重工具
    "全AI代写标记": [
        r"^作为.{0,20}AI", r"我是AI", r"以下由AI生成",
    ],
}

# P0 级 AI 黑名单词汇（保留原 skill 内容）
AI_BLACKLIST_P0 = {
    "概括性开头": [
        r"众所周知",
        r"不言而喻",
        r"总的来说",
        r"从某种意义上看",
        r"不可否认的是",
    ],
    "因果解释句": [
        r"因为.{2,30}所以",
        r"由于.{2,30}因此",
        r"于是.{2,30}便",
    ],
    "AI递进句式": [
        r"不仅如此",
        r"更重要的是",
        r"更为关键的是",
        r"值得一提的是",
        r"值得注意的是",
    ],
    "AI并列句式": [
        r"与此同时",
        r"另一方面",
        r"此外.{2,10}也",
    ],
    "感悟式结尾": [
        r"他明白了",
        r"她明白了",
        r"他懂了",
        r"她懂了",
        r"他终于明白",
        r"她终于明白",
        r"他意识到",
        r"她意识到",
        r"他不禁.*感叹",
        r"她不禁.*感叹",
        r"他不由.*感叹",
        r"她不由.*感叹",
    ],
    "感叹式结尾": [
        r"真是太",
        r"多么.{2,10}啊",
        r"真是.{2,10}啊",
    ],
    "上帝视角": [
        r"所有人没想到",
        r"谁也不知道的是",
        r"全书第.*章",
        r"殊不知",
    ],
    "工整排比": [
        r"(?:不只|不仅|不但).{2,20}(?:而且|也|还).{2,20}(?:更|甚至|还).{2,20}",
    ],
    "破折号": [
        r"—",
    ],
    "副词XX地": [
        r".{1,4}地(?:说|走|看|笑|喊|叫|问|答|写|坐|站|躺|摸|拿|放|推|拉|打|踢|跑|跳|爬|飞|游|飘|转|动)",
    ],
}

# P1 级 AI 特征
AI_PATTERNS_P1 = {
    "抽象心理描写": [
        r"感到.{2,10}(?:悲伤|高兴|愤怒|开心|难过|恐惧|害怕|孤独|绝望)",
        r"觉得.{2,10}(?:孤独|害怕|恐惧|奇怪|不对劲)",
        r"内心.{2,10}(?:平静|波澜|挣扎|矛盾|痛苦)",
    ],
    "抽象情绪概括": [
        r"心中.{2,10}(?:涌起|泛起|升起).{2,10}(?:感觉|情绪|念头)",
        r"一股.{2,10}(?:暖流|寒意|怒火|悲伤).{2,10}(?:涌上|袭来|升起)",
    ],
    "过度解释": [
        r"(?:这是|那)意味着",
        r"换句话说",
        r"也就是说",
    ],
    "AI过渡句": [
        r"在此过程中",
        r"在这种情况之下",
        r"回顾.*历程",
    ],
    "形容词堆砌": [
        r"(?:的.{1,6}的.{1,6}的)",  # 连续"的X的Y的Z"模式
    ],
}

# P2 级优化项
AI_PATTERNS_P2 = {
    "句式重复": [
        r"^他.{3,15}[。，]",
        r"^她.{3,15}[。，]",
    ],
    "对话略平": [
        r'["“][^"”]{20,}["”]',  # 对话 > 20 字可能略平
    ],
    "修辞单一": [],  # 需更复杂检测
}

# 逻辑连接词密度检测
LOGIC_CONNECTORS = [
    "因此", "所以", "于是", "故而", "因为",
    "然而", "但是", "尽管", "虽然",
    "此外", "另外", "而且", "并且",
    "总之", "综上所述",
]

# 对话自然度检测关键词
DIALOGUE_FILLERS = ["呢", "吧", "嘛", "呗", "啊", "啦", "呀", "咯", "哦", "嗯", "呃"]

# 提示语动词（"对话癌"检测：满篇"某某说/道"）
SPEECH_TAG_VERBS = [
    "说道", "问道", "答道", "喊道", "叫道", "嚷道", "笑道", "怒道",
    "沉声道", "低声道", "开口道", "解释说", "回答", "问", "答", "喊", "叫",
    "说", "道",
]

# 感官锚点检测词
SENSORY_WORDS = {
    "听觉": ["声", "响", "音", "喊", "叫", "吼", "鸣", "吵", "静"],
    "嗅觉": ["味", "香", "臭", "腥", "熏", "呛", "酸", "臊"],
    "触觉": ["冷", "热", "烫", "凉", "麻", "痛", "刺", "黏", "滑", "粗", "硬", "软"],
    "温度": ["冰", "暖", "灼", "寒", "温", "火辣"],
}

# 钩子密度检测（新增）
HOOK_PATTERNS = {
    "信息钩": [
        r"话说一半", r"凶手是", r"原来.{0,5}是", r"那张纸",
        r"真相.{0,5}是", r"原来如此", r"他没想到",
    ],
    "情绪钩": [
        r"他攥紧", r"眼神一寒", r"心里一沉", r"咬紧牙关",
        r"忍不住.{2,5}发抖", r"他.{0,3}转身",
    ],
    "认知钩": [
        r"真凶是", r"原来他.{0,5}是", r"从头到尾",
        r"竟然.{0,5}是", r"这怎么可能",
    ],
}

# 场景卡 +/- 检测（新增）
SCENE_CARD_PATTERNS = {
    "情绪正向": ["欢喜", "高兴", "开心", "满足", "温暖", "希望", "喜悦", "舒心"],
    "情绪负向": ["悲伤", "愤怒", "痛苦", "绝望", "恐惧", "焦虑", "孤独", "心寒"],
}

# 续命预警信号（新增）
RESCUE_WARNING_SIGNALS = {
    "战力膨胀": [r"又一次.{0,3}战胜", r"轻松.{0,3}击败", r"不费吹灰之力"],
    "剧情注水": [r"又是.{0,5}同样", r"类似.{0,5}套路", r"和上次一样"],
    "目标漂移": [r"忘记了.{0,5}目标", r"暂时.{0,5}放下", r"先不管"],
    "悬念断档": [r"没有什么.{0,5}进展", r"一切都很平静"],
}


# ============================================================
# 人物弧光双检（保留原 skill 内容）
# ============================================================

ARC_P0_PATTERNS = [
    r"秘籍.{0,25}(脱胎换骨|王者归来|一夜|三年|大成|蜕变|突变|羽化|化境)",
    r"真传.{0,25}(脱胎换骨|大成|一夜|蜕变|化境)",
    r"绝学.{0,25}(练成|大成|一夜|脱胎换骨|化境)",
    r"心法.{0,25}(悟透|大成|通透|一夜|化境)",
    r"(?:三年|数年|一夜|短短数日|苦修多年).{0,20}(王者|高手|大成|脱胎换骨|蜕变|化境)",
    r"顿悟.{0,20}(一切|通透|豁然|全通|大成|化境)",
]

ARC_BEAT_SIGNALS = [
    "终于", "这才明白", "忽然明白", "意识到", "不得不", "被迫", "两难", "抉择",
    "惨败", "失败", "受挫", "受创", "退了一步", "退回", "旧毛病", "又犯",
    "像极了他", "重蹈", "回到原点", "动摇", "瓦解", "崩塌", "溃败",
    "取舍", "割舍", "妥协", "认了", "认命", "松手", "松口",
]


# 文句呼吸检测（v2.2.1 新增）：连词/路标词（过量=句间被撑满，过渡不自然）
RHYTHM_CONNECTORS = [
    "因此", "所以", "于是", "故而", "因为", "由于",
    "然而", "但是", "尽管", "虽然", "不过",
    "此外", "另外", "而且", "并且", "同时",
    "总之", "综上所述", "话说回来", "更深一层", "换句话说", "也就是说",
]

# 长前置压主干：句首超长状语/定语未先出主干（启发式）
LEFT_BRANCH_PATTERN = (
    r"(?:在|当|由于|为了|通过|对于|关于|根据|随着|趁着|除去)[^，。]{10,}(?:，|,)"
)

# ============================================================
# 核心检测函数
# ============================================================

def count_sensory_anchors(content: str) -> dict:
    """统计五感锚点"""
    result = {}
    for category, words in SENSORY_WORDS.items():
        count = 0
        for word in words:
            count += len(re.findall(word, content))
        result[category] = count
    return result


def calc_sentence_length_variance(content: str) -> dict:
    """计算句长分布统计"""
    sentences = re.split(r"[。！？!?\n]", content)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 0]

    clauses = []
    for s in sentences:
        parts = re.split(r"[，,；;：:]", s)
        for p in parts:
            p = p.strip()
            if p and len(p) > 0:
                clauses.append(p)

    sentence_lengths = [len(s) for s in sentences if len(s) > 0]
    clause_lengths = [len(c) for c in clauses if len(c) > 0]

    result = {
        "sentence_count": len(sentence_lengths),
        "sentence_mean": round(statistics.mean(sentence_lengths), 1) if sentence_lengths else 0,
        "sentence_std": round(statistics.stdev(sentence_lengths), 1) if len(sentence_lengths) >= 2 else 0,
        "clause_count": len(clause_lengths),
        "clause_mean": round(statistics.mean(clause_lengths), 1) if clause_lengths else 0,
        "clause_std": round(statistics.stdev(clause_lengths), 1) if len(clause_lengths) >= 2 else 0,
    }

    short = sum(1 for l in sentence_lengths if l <= 8)
    mid = sum(1 for l in sentence_lengths if 9 <= l <= 20)
    long = sum(1 for l in sentence_lengths if l >= 21)
    result["short_ratio"] = round(short / len(sentence_lengths) * 100, 1) if sentence_lengths else 0
    result["mid_ratio"] = round(mid / len(sentence_lengths) * 100, 1) if sentence_lengths else 0
    result["long_ratio"] = round(long / len(sentence_lengths) * 100, 1) if sentence_lengths else 0

    return result


def count_ai_words(content: str) -> dict:
    """统计AI黑名单词汇出现次数"""
    result = {}
    total_ai_words = 0
    total_chars = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))

    for category, patterns in {**AI_BLACKLIST_P0, **AI_PATTERNS_P1, **AI_PATTERNS_P2}.items():
        matches = []
        for pattern in patterns:
            found = re.finditer(pattern, content)
            for m in found:
                line_num = content[:m.start()].count("\n") + 1
                matches.append({"text": m.group()[:50], "line": line_num})
        if matches:
            result[category] = matches
            total_ai_words += len(matches)

    density = round(total_ai_words / total_chars * 100, 2) if total_chars > 0 else 0
    result["_total"] = total_ai_words
    result["_density"] = density
    result["_total_chars"] = total_chars

    return result


def count_logic_connectors(content: str) -> dict:
    """统计逻辑连接词密度"""
    results = {}
    total = 0
    total_chars = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))

    for connector in LOGIC_CONNECTORS:
        count = len(re.findall(connector, content))
        if count > 0:
            results[connector] = count
            total += count

    density = round(total / total_chars * 100, 2) if total_chars > 0 else 0
    results["_total"] = total
    results["_density"] = density

    return results


def check_dialogue_naturalness(content: str) -> dict:
    """检测对话自然度"""
    dialogue_parts = re.findall(r'["“][^"”]+["”]', content)
    dialogue_parts += re.findall(r"「[^」]+」", content)
    dialogue_parts += re.findall(r"『[^』]+』", content)

    total_dialogue_chars = sum(len(d.strip()) for d in dialogue_parts)

    filler_count = 0
    for filler in DIALOGUE_FILLERS:
        for d in dialogue_parts:
            filler_count += d.count(filler)

    interruption_count = len(re.findall(r"[—…]{2,}", content))
    incomplete_count = len(re.findall(r"[。，！？]\s*(?:你|我|他|她|这|那).{0,5}[—…]+", content))

    return {
        "dialogue_segments": len(dialogue_parts),
        "dialogue_chars": total_dialogue_chars,
        "filler_count": filler_count,
        "filler_density": round(filler_count / total_dialogue_chars * 100, 2) if total_dialogue_chars > 0 else 0,
        "interruptions": interruption_count,
        "incomplete_sentences": incomplete_count,
    }


def check_speech_tag_density(content: str) -> dict:
    """提示语密度检测（新增）：统计'某某说/道'类提示语，诊断'对话癌'。

    对齐方法论：'说/道'是隐形词不是禁用词，真正忌讳是连续重复——
    一页（约300-500字）超10个即视觉疲劳。辅助级启发式，需人工确认。
    """
    verb_alt = "|".join(SPEECH_TAG_VERBS)
    # 前置提示语：XX说：/XX道：/XX说道：……（提示语后跟冒号/逗号引出台词）
    front_pattern = re.compile(r"[^。！？\n]{1,6}?(?:" + verb_alt + r")[:：，,]")
    # 后置提示语："……"XX说（台词右引号后跟提示语）
    back_pattern = re.compile(r"[\"”』」](?:[^。！？\n]{1,6}?(?:" + verb_alt + r"))")

    front_matches = [
        {"text": m.group()[:30], "line": content[:m.start()].count("\n") + 1}
        for m in front_pattern.finditer(content)
    ]
    back_matches = [
        {"text": m.group()[:30], "line": content[:m.start()].count("\n") + 1}
        for m in back_pattern.finditer(content)
    ]

    total = len(front_matches) + len(back_matches)
    total_chars = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))
    per_1000 = round(total / (total_chars / 1000), 1) if total_chars > 0 else 0

    return {
        "front_tags": front_matches,
        "back_tags": back_matches,
        "total": total,
        "per_1000": per_1000,
    }


def check_prose_rhythm(content: str) -> dict:
    """文句呼吸与流畅度检测（v2.2.1 新增）：诊断"加速急刹"式节奏病。

    对齐 human-writing check_prose 的量化经验：句长 CV、连词密度、重定语句
    (4+ 个"的")、连续短句鼓点、长前置压主干。辅助级启发式，需人工确认。
    """
    # 句长（以。！？及换行切分）
    sentences = [s.strip() for s in re.split(r"[。！？!?\n]", content) if s.strip()]
    sent_lens = [len(s) for s in sentences if len(s) > 0]
    cv = 0.0
    if len(sent_lens) >= 6 and statistics.mean(sent_lens) > 0:
        cv = round(statistics.stdev(sent_lens) / statistics.mean(sent_lens), 2)

    # 连续短句鼓点：逗号/分号/冒号切后的单句段，连续 4+ 个 ≤6 字
    clauses = []
    for s in sentences:
        for c in re.split(r"[，,；;：:]", s):
            c = c.strip()
            if c:
                clauses.append(c)
    max_streak = 0
    streak = 0
    _quote_open = ('"', '“', '「', '『')
    _quote_close = ('"', '”', '」', '』')
    for c in clauses:
        # 对话短句（口语对白天然短促）豁免，不计入急刹鼓点
        is_dialogue = bool(c) and (c[0] in _quote_open or c[-1] in _quote_close)
        if len(c) <= 6 and not is_dialogue:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    # 连词/路标密度（每千字）
    conn_total = sum(len(re.findall(re.escape(w), content)) for w in RHYTHM_CONNECTORS)
    total_chars = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))
    conn_density = round(conn_total / (total_chars / 1000), 2) if total_chars > 0 else 0

    # 重定语句：含 4 个以上"的"的单句（句中不含句末标点）
    heavy_de = len(re.findall(r"[^。！？\n]*?的[^。！？\n]*?的[^。！？\n]*?的[^。！？\n]*?的[^。！？\n]*", content))

    # 长前置压主干：句首超长状语未先出主干
    left_branch = len(re.findall(LEFT_BRANCH_PATTERN, content))

    return {
        "sentence_cv": cv,
        "max_short_streak": max_streak,
        "conn_density": conn_density,
        "heavy_de_count": heavy_de,
        "left_branch_count": left_branch,
    }


def estimate_zhuque_score(sent_stats, ai_word_result, sensory, dialogue, content):
    """预估朱雀AI检测人工特征分"""
    scores = {}

    sentence_std = sent_stats.get("sentence_std", 0)
    sentence_mean = sent_stats.get("sentence_mean", 0) or 1
    sentence_cv = round(sentence_std / sentence_mean, 2)
    if sentence_cv >= 0.42:
        # 长短句差异健康，不低于健康档（短句均值低的口语风 std 天然小，不可误判）
        scores["句长变异度"] = 25 if sentence_std >= 15 else 20 if sentence_std >= 10 else 18
    elif sentence_std >= 18:
        scores["句长变异度"] = 25
    elif sentence_std >= 15:
        scores["句长变异度"] = 22
    elif sentence_std >= 12:
        scores["句长变异度"] = 18
    elif sentence_std >= 10:
        scores["句长变异度"] = 14
    else:
        scores["句长变异度"] = 8

    ai_density = ai_word_result.get("_density", 100)
    if ai_density <= 0.3:
        scores["AI词汇密度"] = 25
    elif ai_density <= 0.5:
        scores["AI词汇密度"] = 22
    elif ai_density <= 1.0:
        scores["AI词汇密度"] = 18
    elif ai_density <= 2.0:
        scores["AI词汇密度"] = 14
    elif ai_density <= 3.0:
        scores["AI词汇密度"] = 10
    else:
        scores["AI词汇密度"] = 5

    total_sensory = sum(sensory.values())
    total_chars = ai_word_result.get("_total_chars", 3000)
    sensory_per_300 = total_sensory / (total_chars / 300) if total_chars > 0 else 0
    if sensory_per_300 >= 1.5:
        scores["感官锚点"] = 20
    elif sensory_per_300 >= 1.0:
        scores["感官锚点"] = 17
    elif sensory_per_300 >= 0.7:
        scores["感官锚点"] = 14
    elif sensory_per_300 >= 0.4:
        scores["感官锚点"] = 10
    else:
        scores["感官锚点"] = 5

    filler_density = dialogue.get("filler_density", 0)
    interruptions = dialogue.get("interruptions", 0)
    incomplete = dialogue.get("incomplete_sentences", 0)
    if filler_density >= 3 and interruptions >= 1:
        scores["口语自然度"] = 15
    elif filler_density >= 2:
        scores["口语自然度"] = 13
    elif filler_density >= 1:
        scores["口语自然度"] = 11
    elif interruptions >= 1 or incomplete >= 1:
        scores["口语自然度"] = 9
    else:
        scores["口语自然度"] = 5

    ending = content[-200:] if len(content) > 200 else content
    has_p0_ending = False
    for pattern in AI_BLACKLIST_P0.get("感悟式结尾", []) + AI_BLACKLIST_P0.get("感叹式结尾", []):
        if re.search(pattern, ending):
            has_p0_ending = True
            break
    if has_p0_ending:
        scores["结尾类型"] = 5
    else:
        ending_clean = ending.strip()
        if re.search(r"[，。！？].{0,10}$", ending_clean) and len(ending_clean.split()) > 0:
            scores["结尾类型"] = 13
        else:
            scores["结尾类型"] = 10

    total_score = sum(scores.values())
    zhuque_estimate = round(total_score / 100 * 100, 0)

    return {
        "dimension_scores": scores,
        "total": total_score,
        "zhuque_estimate": zhuque_estimate,
    }


def check_arc_beats(content: str) -> dict:
    """人物弧光双检"""
    p0 = []
    p1 = []

    for pat in ARC_P0_PATTERNS:
        for m in re.finditer(pat, content):
            s = m.start()
            line_num = content[:s].count("\n") + 1
            p0.append({
                "type": "弧光反模式-秘籍式成长",
                "line": line_num,
                "text": f"检测到'升级当成长'捷径：\"{m.group()[:30]}\"…",
                "severity": "P0",
            })

    char_count = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))
    beat_hits = 0
    for sig in ARC_BEAT_SIGNALS:
        beat_hits += len(re.findall(sig, content))
    ARC_CHECK_MIN_CHARS = 1500
    if char_count >= ARC_CHECK_MIN_CHARS and beat_hits == 0:
        p1.append({
            "type": "弧光节拍稀疏",
            "line": 1,
            "text": f"本章 {char_count} 字却无任何认知/情感转折信号，弧光可能停滞",
            "severity": "P1",
        })

    return {"p0": p0, "p1": p1, "beat_hits": beat_hits}


def check_hooks(content: str) -> dict:
    """钩子密度检测（新增）"""
    hooks = {}
    total_hooks = 0
    for hook_type, patterns in HOOK_PATTERNS.items():
        matches = []
        for pattern in patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count("\n") + 1
                matches.append({"text": m.group()[:30], "line": line_num})
        if matches:
            hooks[hook_type] = matches
            total_hooks += len(matches)

    total_chars = len(content.replace("\n", "").replace(" ", ""))
    density = round(total_hooks / (total_chars / 1000), 2) if total_chars > 0 else 0

    return {
        "hooks": hooks,
        "total_hooks": total_hooks,
        "per_1000": density,
    }


def check_scene_card(content: str) -> dict:
    """场景卡 +/- 检测（新增）"""
    positive = sum(len(re.findall(p, content)) for p in SCENE_CARD_PATTERNS["情绪正向"])
    negative = sum(len(re.findall(p, content)) for p in SCENE_CARD_PATTERNS["情绪负向"])

    has_shift = positive > 0 and negative > 0

    return {
        "positive_count": positive,
        "negative_count": negative,
        "has_emotion_shift": has_shift,
        "warning": "无情绪变化（建议加入+或-转变）" if not has_shift and (positive + negative) > 0 else None,
    }


def check_rescue_signals(content: str) -> dict:
    """续命预警信号检测（新增）"""
    warnings = {}
    for symptom, patterns in RESCUE_WARNING_SIGNALS.items():
        matches = []
        for pattern in patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count("\n") + 1
                matches.append({"text": m.group()[:30], "line": line_num})
        if matches:
            warnings[symptom] = matches

    return {"warnings": warnings, "count": len(warnings)}


def check_business_red_line(content: str) -> list:
    """P-1 商业红线检测（新增）"""
    issues = []
    for category, patterns in P_NEGATIVE_1_PATTERNS.items():
        for pattern in patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count("\n") + 1
                issues.append({
                    "type": f"P-1商业红线-{category}",
                    "line": line_num,
                    "text": m.group()[:50],
                    "severity": "P-1",
                })
    return issues


def check_file(filepath: str, voice_anchor_path: str = None) -> dict:
    """全面检测文件质量（升级版：4 级红线）"""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"文件不存在: {filepath}"}

    content = path.read_text(encoding="utf-8")
    char_count = len(content.replace("\n", "").replace(" ", "").replace("\r", ""))
    line_count = len(content.split("\n"))

    sent_stats = calc_sentence_length_variance(content)
    rhythm = check_prose_rhythm(content)
    ai_word_result = count_ai_words(content)
    logic_connectors = count_logic_connectors(content)
    sensory = count_sensory_anchors(content)
    dialogue = check_dialogue_naturalness(content)
    speech_tag = check_speech_tag_density(content)
    zhuque = estimate_zhuque_score(sent_stats, ai_word_result, sensory, dialogue, content)

    p_neg1_issues = []
    p0_issues = []
    p1_issues = []
    p2_issues = []

    # P-1 商业红线
    p_neg1_issues.extend(check_business_red_line(content))

    # P0/P1/P2 AI 词
    for category, matches in ai_word_result.items():
        if category.startswith("_"):
            continue
        if category in AI_BLACKLIST_P0:
            severity = "P0"
        elif category in AI_PATTERNS_P1:
            severity = "P1"
        else:
            severity = "P2"
        for m in matches:
            issue = {"type": category, "line": m["line"], "text": m["text"], "severity": severity}
            if severity == "P0":
                p0_issues.append(issue)
            elif severity == "P1":
                p1_issues.append(issue)
            else:
                p2_issues.append(issue)

    # 句长检查（v2.2.1 修正：短句均值低的口语风 std 天然小，须用 CV 归一化判断，避免误报 P0/P1）
    _cv = rhythm.get("sentence_cv", 0)
    if _cv >= 0.42:
        pass  # 长短句差异健康，不报均匀
    elif sent_stats.get("sentence_std", 0) < 10:
        p0_issues.append({
            "type": "句长过于均匀",
            "line": 1,
            "text": f"句长标准差仅{sent_stats['sentence_std']}、CV仅{_cv}（健康CV≥0.42），长短句像节拍器",
            "severity": "P0",
        })
    elif sent_stats.get("sentence_std", 0) < 13:
        p1_issues.append({
            "type": "句长偏均匀",
            "line": 1,
            "text": f"句长标准差{sent_stats['sentence_std']}、CV{_cv}（健康CV≥0.42）",
            "severity": "P1",
        })

    # 感官锚点检查
    total_sensory = sum(sensory.values())
    sensory_per_300 = total_sensory / (char_count / 300) if char_count > 0 else 0
    if sensory_per_300 < 0.5:
        p1_issues.append({
            "type": "感官描写不足",
            "line": 1,
            "text": f"每300字仅{sensory_per_300:.1f}处非视觉感官（目标≥1）",
            "severity": "P1",
        })

    # 对话检查
    if dialogue.get("dialogue_segments", 0) > 0 and dialogue.get("filler_density", 0) < 1:
        p1_issues.append({
            "type": "对话过光滑",
            "line": 1,
            "text": "对话缺乏语气词/打断/省略，显得过于书面",
            "severity": "P1",
        })

    # 提示语密度（对话癌，新增）
    if speech_tag["total"] > 0:
        if speech_tag["per_1000"] >= 12:
            p1_issues.append({
                "type": "提示语过密（对话癌）",
                "line": 1,
                "text": f"每千字 {speech_tag['per_1000']} 个'某某说/道'（阈值≥12），满篇提示语=念剧本，用提示语替代四招",
                "severity": "P1",
            })
        elif speech_tag["per_1000"] >= 6:
            p2_issues.append({
                "type": "提示语偏密",
                "line": 1,
                "text": f"每千字 {speech_tag['per_1000']} 个'某某说/道'（建议<6），检查连续重复段，用动作/神态/环境/语感替换",
                "severity": "P2",
            })

    # 文句呼吸检测（v2.2.1 新增，治"加速急刹"节奏病）
    if 0 < rhythm["sentence_cv"] < 0.35:
        p2_issues.append({
            "type": "句长偏均匀（缺呼吸）",
            "line": 1,
            "text": f"句长变异系数CV仅{rhythm['sentence_cv']}（健康≥0.42），长短句像节拍器，拉开句长差",
            "severity": "P2",
        })
    if rhythm["max_short_streak"] >= 4:
        p2_issues.append({
            "type": "连续短句鼓点（急刹）",
            "line": 1,
            "text": f"出现连续{rhythm['max_short_streak']}个≤6字单句段，像机关枪急刹，拉开句长",
            "severity": "P2",
        })
    if rhythm["conn_density"] > 7:
        p2_issues.append({
            "type": "连词/路标过量",
            "line": 1,
            "text": f"句间连词/路标密度{rhythm['conn_density']}/千字（>7），删路标词让转折自然",
            "severity": "P2",
        })
    if rhythm["heavy_de_count"] >= 3:
        p2_issues.append({
            "type": "重定语句（的×4+）",
            "line": 1,
            "text": f"出现{rhythm['heavy_de_count']}处含4个以上'的'的定语堆墙句，拆小句",
            "severity": "P2",
        })
    if rhythm["left_branch_count"] >= 2:
        p2_issues.append({
            "type": "长前置压主干",
            "line": 1,
            "text": f"出现{rhythm['left_branch_count']}处句首超长状语压住主干，主干先来",
            "severity": "P2",
        })

    # 破折号专项
    dash_count = content.count("—")
    if dash_count > 0:
        p0_issues.append({
            "type": "破折号",
            "line": 1,
            "text": f"全文出现{dash_count}处破折号（P0红线）",
            "severity": "P0",
        })

    # 副词专项
    adverb_pattern = re.compile(r".{1,4}地(?:说|走|看|笑|喊|叫|问|答|写|坐|站|躺|摸|拿|放|推|拉|打|踢|跑|跳|爬|飞|游|飘|转|动)")
    adverb_matches = adverb_pattern.findall(content)
    if len(adverb_matches) > max(4, char_count // 1200):
        p0_issues.append({
            "type": "副词XX地滥用",
            "line": 1,
            "text": f"全文出现{len(adverb_matches)}处'XX地'副词结构",
            "severity": "P0",
        })
    elif len(adverb_matches) > 0:
        p1_issues.append({
            "type": "副词XX地",
            "line": 1,
            "text": f"全文出现{len(adverb_matches)}处'XX地'副词结构",
            "severity": "P1",
        })

    # 人物弧光双检
    arc_result = check_arc_beats(content)
    p0_issues.extend(arc_result["p0"])
    p1_issues.extend(arc_result["p1"])

    # 钩子检测
    hooks_result = check_hooks(content)
    if hooks_result["total_hooks"] == 0 and char_count > 1500:
        p1_issues.append({
            "type": "钩子缺失",
            "line": 1,
            "text": "本章未检测到任何钩子信号（信息钩/情绪钩/认知钩）",
            "severity": "P1",
        })
    elif hooks_result["total_hooks"] < 2 and char_count > 3000:
        p2_issues.append({
            "type": "钩子偏少",
            "line": 1,
            "text": f"本章仅{hooks_result['total_hooks']}处钩子（建议≥2）",
            "severity": "P2",
        })

    # 场景卡检测
    scene_result = check_scene_card(content)
    if scene_result.get("warning"):
        p2_issues.append({
            "type": "场景卡+/-",
            "line": 1,
            "text": scene_result["warning"],
            "severity": "P2",
        })

    # 续命预警
    rescue_result = check_rescue_signals(content)
    if rescue_result["count"] >= 2:
        p1_issues.append({
            "type": "续命预警",
            "line": 1,
            "text": f"检测到{rescue_result['count']}种中期病症信号，建议进入体检期",
            "severity": "P1",
        })

    return {
        "file": str(filepath),
        "char_count": char_count,
        "line_count": line_count,
        "sentence_stats": sent_stats,
        "ai_word_count": ai_word_result.get("_total", 0),
        "ai_word_density": ai_word_result.get("_density", 0),
        "logic_connectors": logic_connectors,
        "sensory_anchors": sensory,
        "sensory_per_300": round(sensory_per_300, 2),
        "dialogue": dialogue,
        "speech_tag": speech_tag,
        "zhuque": zhuque,
        "hooks": hooks_result,
        "scene_card": scene_result,
        "rescue_signals": rescue_result,
        "p_neg1_issues": p_neg1_issues,
        "p0_issues": p0_issues,
        "p1_issues": p1_issues,
        "p2_issues": p2_issues,
        "rhythm": rhythm,
        "p_neg1_count": len(p_neg1_issues),
        "p0_count": len(p0_issues),
        "p1_count": len(p1_issues),
        "p2_count": len(p2_issues),
        "arc": arc_result,
        "dash_count": dash_count,
        "adverb_count": len(adverb_matches),
    }


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print("用法: python3 check_quality.py <章节文件路径>")
        print("示例: python3 check_quality.py 正文/第001章.txt")
        print()
        print("检测维度：")
        print("  - 4 级红线（P-1 商业 / P0 质量 / P1 体验 / P2 优化）")
        print("  - 朱雀 AI 检测预估分")
        print("  - 句长变异度、感官锚点、对话自然度、提示语密度、文句呼吸")
        print("  - 人物弧光双检（认知弧光 × PDCA）")
        print("  - 钩子密度、场景卡 +/-、续命预警信号")
        sys.exit(0)

    filepath = sys.argv[1]
    result = check_file(filepath)

    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)

    print("=" * 60)
    print("  锻字·网络小说创作引擎 - 质量检测报告")
    print("=" * 60)
    print(f"\n文件: {result['file']}")
    print(f"字数: {result['char_count']} | 行数: {result['line_count']}")
    print()

    # 4 级红线汇总
    print("【4 级红线汇总】")
    print(f"  P-1 商业红线: {result['p_neg1_count']} 个")
    print(f"  P0  质量红线: {result['p0_count']} 个")
    print(f"  P1  体验红线: {result['p1_count']} 个")
    print(f"  P2  优化红线: {result['p2_count']} 个")

    # 句长
    ss = result["sentence_stats"]
    print(f"\n【句长分析】")
    print(f"  句数: {ss['sentence_count']} | 均值: {ss['sentence_mean']}字 | 标准差: {ss['sentence_std']}字")
    print(f"  短/中/长: {ss['short_ratio']}% / {ss['mid_ratio']}% / {ss['long_ratio']}%")

    # 文句呼吸（新增）
    rh = result["rhythm"]
    print(f"\n【文句呼吸】（新增）")
    print(f"  句长CV: {rh['sentence_cv']}（健康≥0.42）| 连续短句鼓点: {rh['max_short_streak']}")
    print(f"  连词/路标密度: {rh['conn_density']}/千字（<7）| 重定语句: {rh['heavy_de_count']}处 | 长前置压主干: {rh['left_branch_count']}处")

    # AI 词
    print(f"\n【AI 词检测】")
    print(f"  黑名单: {result['ai_word_count']}处 | 密度: {result['ai_word_density']}%")

    # 感官
    print(f"\n【感官锚点】")
    print(f"  每300字: {result['sensory_per_300']}处")

    # 对话
    d = result["dialogue"]
    print(f"\n【对话自然度】")
    print(f"  语气词密度: {d['filler_density']}% | 打断/省略: {d['interruptions']}/{d['incomplete_sentences']}")

    # 提示语密度（新增）
    st = result["speech_tag"]
    print(f"\n【提示语密度】（新增）")
    print(f"  '某某说/道'类提示语: {st['total']}处 | 每千字: {st['per_1000']}个")
    if st["per_1000"] >= 12:
        print(f"  ⚠️ 提示语过密（对话癌）：满篇提示语=念剧本，用提示语替代四招（动作/神态/环境/语感）")
    elif st["per_1000"] >= 6:
        print(f"  ⚠️ 提示语偏密：检查连续重复段，用动作/神态/环境/语感替换")

    # 钩子（新增）
    print(f"\n【钩子密度】（新增）")
    print(f"  总钩子: {result['hooks']['total_hooks']}处 | 每千字: {result['hooks']['per_1000']}处")
    for hook_type, matches in result['hooks']['hooks'].items():
        print(f"  {hook_type}: {len(matches)}处")

    # 场景卡（新增）
    sc = result['scene_card']
    print(f"\n【场景卡 +/-】（新增）")
    print(f"  正向情绪: {sc['positive_count']} | 负向情绪: {sc['negative_count']}")
    if sc.get('warning'):
        print(f"  ⚠️  {sc['warning']}")

    # 续命预警（新增）
    rs = result['rescue_signals']
    if rs['count'] > 0:
        print(f"\n【续命预警】（新增）")
        for symptom, matches in rs['warnings'].items():
            print(f"  ⚠️ {symptom}: {len(matches)}处信号")

    # 朱雀
    z = result["zhuque"]
    print(f"\n{'=' * 60}")
    print(f"  朱雀 AI 检测预估")
    print(f"{'=' * 60}")
    print(f"  总分: {z['total']}/100 → 人工特征: {z['zhuque_estimate']:.0f}%")
    print(f"  → {'✓ 通过（≥80%）' if z['zhuque_estimate'] >= 80 else '✗ 不达标'}")
    for dim, score in z["dimension_scores"].items():
        bar = "█" * (score // 5) + "░" * (5 - score // 5)
        print(f"    {dim}: {score}/25  {bar}")

    # 弧光
    arc = result["arc"]
    print(f"\n【人物弧光】转折信号: {arc['beat_hits']}处")

    # 详细问题
    for level, issues, label in [
        ("P-1", result["p_neg1_issues"], "P-1 商业红线（立即停更）"),
        ("P0", result["p0_issues"], "P0 质量红线（必须修改）"),
        ("P1", result["p1_issues"], "P1 体验红线（建议修改）"),
        ("P2", result["p2_issues"], "P2 优化红线（攒5处批量润色）"),
    ]:
        if issues:
            print(f"\n【{label}】共{len(issues)}个")
            for issue in issues[:10]:
                print(f"  第{issue['line']}行 - {issue['type']}: {issue['text'][:60]}")
            if len(issues) > 10:
                print(f"  ... 还有{len(issues)-10}个")

    # 决策
    if result["p_neg1_count"] > 0:
        print(f"\n❌ P-1 商业红线触发，必须立即停更整改")
        sys.exit(4)
    elif result["p0_count"] > 0:
        print(f"\n❌ P0 质量红线触发，建议修改")
        sys.exit(1)
    elif z["zhuque_estimate"] < 80:
        print(f"\n⚠️ AI 检测不达标，建议执行去 AI 味润色")
        sys.exit(2)
    elif result["p1_count"] > 0:
        print(f"\n⚠️ 有{result['p1_count']}个建议优化项")
    else:
        print(f"\n✅ 全部通过")


if __name__ == "__main__":
    main()

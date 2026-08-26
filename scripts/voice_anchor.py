#!/usr/bin/env python3
"""
voice_anchor.py - 锻字·网络小说创作引擎
风格锚定：作者锚点提取 + 角色声音指纹校验

用法：
  python3 voice_anchor.py extract --input 锚点.txt --output 声音/author_anchor.yaml
  python3 voice_anchor.py check --chapter 正文/第050章.txt --anchor 声音/author_anchor.yaml
"""

import argparse
import re
import statistics
import sys
from pathlib import Path
from collections import Counter

# 6 维特征提取
SENSORY_WORDS = {
    "听觉": ["声", "响", "音", "喊", "叫", "吼", "鸣", "吵", "静"],
    "嗅觉": ["味", "香", "臭", "腥", "熏", "呛", "酸", "臊"],
    "触觉": ["冷", "热", "烫", "凉", "麻", "痛", "刺", "黏", "滑", "粗", "硬", "软"],
    "温度": ["冰", "暖", "灼", "寒", "温", "火辣"],
}

DIALOGUE_FILLERS = ["呢", "吧", "嘛", "呗", "啊", "啦", "呀", "咯", "哦", "嗯", "呃"]


def extract_anchor(input_file: str, output_file: str) -> dict:
    """提取作者风格锚点"""
    path = Path(input_file)
    if not path.exists():
        return {"error": f"文件不存在: {input_file}"}

    content = path.read_text(encoding="utf-8")
    anchor = analyze_style(content)

    # 写入 YAML
    import yaml
    out = Path(output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# 作者风格锚点\n"
        + yaml.dump(anchor, allow_unicode=True, sort_keys=False),
        encoding="utf-8"
    )

    return {
        "extracted": True,
        "file": str(out),
        "anchor": anchor,
    }


def analyze_style(content: str) -> dict:
    """分析文本风格（6 维）"""
    # 1. 句长分布
    sentences = re.split(r"[。！？!?\n]", content)
    sentences = [s.strip() for s in sentences if s.strip()]
    sent_lengths = [len(s) for s in sentences if s]

    if sent_lengths:
        sent_std = round(statistics.stdev(sent_lengths), 1) if len(sent_lengths) >= 2 else 0
        sent_mean = round(statistics.mean(sent_lengths), 1)
        short = sum(1 for l in sent_lengths if l <= 8)
        mid = sum(1 for l in sent_lengths if 9 <= l <= 20)
        long_ = sum(1 for l in sent_lengths if l >= 21)
        total = len(sent_lengths)
        sentence_length = {
            "avg": sent_mean,
            "std": sent_std,
            "short_ratio": round(short / total * 100, 1),
            "mid_ratio": round(mid / total * 100, 1),
            "long_ratio": round(long_ / total * 100, 1),
        }
    else:
        sentence_length = {"avg": 0, "std": 0, "short_ratio": 0, "mid_ratio": 0, "long_ratio": 0}

    # 2. 词汇偏好
    words = re.findall(r"[\u4e00-\u9fff]+", content)
    word_freq = Counter(words)
    high_freq = [w for w, c in word_freq.most_common(20) if len(w) >= 2]
    vocabulary = {
        "high_freq": high_freq[:15],
        "total_unique": len(word_freq),
        "total_words": sum(word_freq.values()),
    }

    # 3. 节奏（通过标点统计）
    periods = content.count("。")
    commas = content.count("，")
    exclamations = content.count("！")
    questions = content.count("？")
    rhythm = {
        "period_density": round(periods / max(len(content) / 1000, 1), 1),
        "comma_density": round(commas / max(len(content) / 1000, 1), 1),
        "exclamation_ratio": round(exclamations / max(periods, 1), 2),
        "question_ratio": round(questions / max(periods, 1), 2),
    }

    # 4. 感官锚点
    sensory = {}
    total_chars = len(content)
    for category, words in SENSORY_WORDS.items():
        count = sum(len(re.findall(w, content)) for w in words)
        sensory[category] = count
    sensory_density = {
        "per_1000": round(sum(sensory.values()) / max(total_chars / 1000, 1), 2),
        "breakdown": sensory,
    }

    # 5. 对话特征
    dialogue_parts = re.findall(r'["“][^"”]+["”]', content)
    dialogue_parts += re.findall(r"「[^」]+」", content)
    dialogue_lengths = [len(d.strip()) for d in dialogue_parts if d.strip()]

    if dialogue_lengths:
        dialogue_stats = {
            "segments": len(dialogue_parts),
            "avg_length": round(statistics.mean(dialogue_lengths), 1),
            "max_length": max(dialogue_lengths),
        }
    else:
        dialogue_stats = {"segments": 0, "avg_length": 0, "max_length": 0}

    # 语气词密度
    filler_count = 0
    for filler in DIALOGUE_FILLERS:
        filler_count += len(re.findall(filler, content))
    total_dialogue_chars = sum(dialogue_lengths)
    filler_density = round(filler_count / max(total_dialogue_chars, 1) * 100, 2)
    dialogue_stats["filler_density"] = filler_density

    # 6. 修辞习惯（简化：检测常见修辞标志）
    rhetoric = {
        "metaphor_markers": len(re.findall(r"如|像|似|仿佛", content)),
        "parallelism_markers": len(re.findall(r"既是.{0,10}也是|不仅.{0,10}更", content)),
        "repetition_markers": len(re.findall(r"({0,5})\\1+", content)),  # 简单重复检测
    }

    return {
        "sentence_length": sentence_length,
        "vocabulary": vocabulary,
        "rhythm": rhythm,
        "sensory_density": sensory_density,
        "dialogue": dialogue_stats,
        "rhetoric": rhetoric,
        "source_chars": total_chars,
        "source_sentences": len(sentences),
    }


def check_chapter(chapter_file: str, anchor_file: str) -> dict:
    """检查章节与锚点的一致性"""
    chap_path = Path(chapter_file)
    if not chap_path.exists():
        return {"error": f"章节文件不存在: {chapter_file}"}

    anc_path = Path(anchor_file)
    if not anc_path.exists():
        return {"error": f"锚点文件不存在: {anchor_file}"}

    import yaml
    chapter = chap_path.read_text(encoding="utf-8")
    anchor = yaml.safe_load(anc_path.read_text(encoding="utf-8"))

    chapter_style = analyze_style(chapter)

    # 计算相似度（简化版：基于句长、词汇、节奏的接近度）
    similarity = compute_similarity(chapter_style, anchor)

    return {
        "chapter": str(chap_path),
        "anchor": str(anc_path),
        "chapter_style": chapter_style,
        "anchor_style": anchor,
        "similarity": round(similarity, 3),
        "passed": similarity >= 0.85,
    }


def compute_similarity(style1: dict, style2: dict) -> float:
    """计算两个风格的相似度（简化算法）"""
    scores = []

    # 句长均值
    s1_avg = style1.get("sentence_length", {}).get("avg", 0)
    s2_avg = style2.get("sentence_length", {}).get("avg", 0)
    if s1_avg and s2_avg:
        diff = abs(s1_avg - s2_avg) / max(s1_avg, s2_avg, 1)
        scores.append(max(0, 1 - diff))

    # 句长标准差
    s1_std = style1.get("sentence_length", {}).get("std", 0)
    s2_std = style2.get("sentence_length", {}).get("std", 0)
    if s1_std and s2_std:
        diff = abs(s1_std - s2_std) / max(s1_std, s2_std, 1)
        scores.append(max(0, 1 - diff))

    # 短句比例
    s1_short = style1.get("sentence_length", {}).get("short_ratio", 0)
    s2_short = style2.get("sentence_length", {}).get("short_ratio", 0)
    if s1_short or s2_short:
        diff = abs(s1_short - s2_short) / 100
        scores.append(max(0, 1 - diff))

    # 中句比例
    s1_mid = style1.get("sentence_length", {}).get("mid_ratio", 0)
    s2_mid = style2.get("sentence_length", {}).get("mid_ratio", 0)
    if s1_mid or s2_mid:
        diff = abs(s1_mid - s2_mid) / 100
        scores.append(max(0, 1 - diff))

    # 感官密度
    s1_sens = style1.get("sensory_density", {}).get("per_1000", 0)
    s2_sens = style2.get("sensory_density", {}).get("per_1000", 0)
    if s1_sens and s2_sens:
        diff = abs(s1_sens - s2_sens) / max(s1_sens, s2_sens, 1)
        scores.append(max(0, 1 - diff))

    return sum(scores) / len(scores) if scores else 0.85


def print_extraction(anchor: dict) -> None:
    """打印锚点提取结果"""
    print("=" * 60)
    print("  作者风格锚点提取结果")
    print("=" * 60)

    sl = anchor.get("sentence_length", {})
    print(f"\n【1. 句长分布】")
    print(f"  均值: {sl.get('avg', 0)}字 | 标准差: {sl.get('std', 0)}字")
    print(f"  短/中/长: {sl.get('short_ratio', 0)}% / {sl.get('mid_ratio', 0)}% / {sl.get('long_ratio', 0)}%")

    vocab = anchor.get("vocabulary", {})
    print(f"\n【2. 词汇】")
    print(f"  总词汇: {vocab.get('total_words', 0)} | 唯一: {vocab.get('total_unique', 0)}")
    print(f"  高频词: {', '.join(vocab.get('high_freq', [])[:10])}")

    rhythm = anchor.get("rhythm", {})
    print(f"\n【3. 节奏】")
    print(f"  句号密度: {rhythm.get('period_density', 0)}/千字")
    print(f"  逗号密度: {rhythm.get('comma_density', 0)}/千字")
    print(f"  感叹号比: {rhythm.get('exclamation_ratio', 0)}")

    sens = anchor.get("sensory_density", {})
    print(f"\n【4. 感官】")
    print(f"  密度: {sens.get('per_1000', 0)}/千字")
    print(f"  分布: {sens.get('breakdown', {})}")

    dia = anchor.get("dialogue", {})
    print(f"\n【5. 对话】")
    print(f"  段数: {dia.get('segments', 0)} | 均长: {dia.get('avg_length', 0)}字")
    print(f"  语气词密度: {dia.get('filler_density', 0)}%")


def print_check_result(result: dict) -> None:
    """打印检查结果"""
    if "error" in result:
        print(f"错误: {result['error']}")
        return

    print("=" * 60)
    print("  声音一致性检查")
    print("=" * 60)
    print(f"\n  章节: {result['chapter']}")
    print(f"  锚点: {result['anchor']}")

    sim = result["similarity"]
    icon = "✅" if result["passed"] else "⚠️"
    print(f"\n  相似度: {sim} {icon}")
    print(f"  阈值: ≥ 0.85")
    print(f"  结果: {'通过' if result['passed'] else '不通过'}")

    if not result["passed"]:
        print(f"\n  建议: 调整章节以更接近锚点风格")
        print(f"  - 检查句长分布")
        print(f"  - 检查词汇使用")
        print(f"  - 检查感官密度")


def main():
    parser = argparse.ArgumentParser(description="锻字·风格锚定")
    subparsers = parser.add_subparsers(dest="command")

    # extract
    ext = subparsers.add_parser("extract", help="提取作者风格锚点")
    ext.add_argument("--input", required=True, help="锚点文本文件")
    ext.add_argument("--output", required=True, help="输出 yaml 文件")

    # check
    chk = subparsers.add_parser("check", help="检查章节与锚点的一致性")
    chk.add_argument("--chapter", required=True, help="章节文件")
    chk.add_argument("--anchor", required=True, help="锚点文件")

    args = parser.parse_args()

    if args.command == "extract":
        result = extract_anchor(args.input, args.output)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print_extraction(result["anchor"])
            print(f"\n✅ 已保存: {result['file']}")
    elif args.command == "check":
        result = check_chapter(args.chapter, args.anchor)
        print_check_result(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

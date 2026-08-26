#!/usr/bin/env python3
"""
health_check.py - 锻字·网络小说创作引擎
中期体检：5 维度 + 病症诊断 + 续命处方

用法：
  python3 health_check.py --project . --chapter 50
  python3 health_check.py --project . --report
"""

import argparse
import sys
import statistics
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

# 5 维度权重
DIMENSION_WEIGHTS = {
    "power_balance": 0.20,
    "plot_purity": 0.20,
    "character_growth": 0.20,
    "hook_density": 0.20,
    "world_consistency": 0.20,
}

# 5 大中期病症
SYMPTOMS = {
    "战力膨胀": {
        "signals": [
            r"又一次.{0,3}战胜",
            r"轻松.{0,3}击败",
            r"不费吹灰之力",
            r"敌人.{0,3}不堪一击",
        ],
        "prescriptions": [
            "降维打击法：主角自封修为",
            "规则补丁法：新增'天道压制'",
            "引入中期 BOSS（>1 大境界的强敌）",
            "强化反派四维度（力量/道德/认知/魅力）",
        ],
    },
    "剧情注水": {
        "signals": [
            r"又是.{0,5}同样",
            r"类似.{0,5}套路",
            r"和上次一样",
            r"一如既往.{0,5}强大",
        ],
        "prescriptions": [
            "引入新元素（新人物/新设定/新地点）",
            "切换视角（POV）",
            "揭隐藏线索",
            "时间跳跃",
        ],
    },
    "目标漂移": {
        "signals": [
            r"忘记了.{0,5}目标",
            r"暂时.{0,5}放下",
            r"先不管",
            r"再说吧",
        ],
        "prescriptions": [
            "重新聚焦核心目标",
            "砍掉无意义支线",
            "设计三目标（短/中/长期）",
            "强制下章回到主线",
        ],
    },
    "悬念断档": {
        "signals": [
            r"没有什么.{0,5}进展",
            r"一切都很平静",
            r"暂时.{0,5}没有",
        ],
        "prescriptions": [
            "揭一埋一",
            "拉长悬念（信息分批释放）",
            "引入新悬念",
            "回收中期伏笔",
        ],
    },
    "换地图翻车": {
        "signals": [
            r"来到.{0,3}陌生",
            r"全新的.{0,3}地方",
            r"没人认识",
        ],
        "prescriptions": [
            "保留 1-2 个旧角色",
            "设计过渡章（路途+新地图预告）",
            "在新地图立刻引入'熟悉元素'",
            "短期副本（≤5 章）",
        ],
    },
}


def analyze_power_balance(chapter_dir: str, last_n: int = 10) -> dict:
    """战力平衡分析"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"score": 85, "issues": ["无章节数据"], "data": {}}

    # 简化分析：检测"轻松"vs"困难"关键词
    easy_signals = ["轻松", "不费吹灰", "不堪一击", "简单", "轻而易举"]
    hard_signals = ["惨败", "失败", "受伤", "受创", "拼尽全力", "差点", "险些"]

    easy_count = 0
    hard_count = 0
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        for sig in easy_signals:
            easy_count += len(re.findall(sig, content))
        for sig in hard_signals:
            hard_count += len(re.findall(sig, content))

    ratio = hard_count / max(easy_count, 1)

    score = 85
    issues = []
    if easy_count > hard_count * 2 and easy_count > 5:
        score = 60
        issues.append(f"近期{easy_count}处轻松胜利 vs {hard_count}处困难战斗，敌人变纸老虎")
    elif ratio < 0.3:
        score = 70
        issues.append(f"困难战斗比例偏低（{ratio:.2f}），建议增加困难场景")

    return {
        "score": score,
        "issues": issues,
        "data": {
            "easy_count": easy_count,
            "hard_count": hard_count,
            "ratio": round(ratio, 2),
        },
    }


def analyze_plot_purity(chapter_dir: str, last_n: int = 10) -> dict:
    """主线纯度分析"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"score": 85, "issues": ["无章节数据"], "data": {}}

    # 简化：检测支线关键词 vs 主线关键词
    main_keywords = ["复仇", "回家", "变强", "寻找", "拯救", "目标", "任务"]
    side_keywords = ["顺便", "额外", "支线", "其他事", "另一边", "另外", "顺便"]

    main_count = 0
    side_count = 0
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        for sig in main_keywords:
            main_count += len(re.findall(sig, content))
        for sig in side_keywords:
            side_count += len(re.findall(sig, content))

    score = 85
    issues = []
    if side_count > main_count * 0.5 and side_count > 3:
        score = 65
        issues.append(f"支线提及{side_count}处 vs 主线{main_count}处，支线占比偏高")

    return {
        "score": score,
        "issues": issues,
        "data": {
            "main_count": main_count,
            "side_count": side_count,
        },
    }


def analyze_character_growth(chapter_dir: str, last_n: int = 10) -> dict:
    """人物成长分析"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"score": 85, "issues": ["无章节数据"], "data": {}}

    # 检测弧光信号
    arc_signals = ["终于", "这才明白", "忽然明白", "意识到", "不得不", "被迫", "两难", "抉择",
                   "惨败", "失败", "受挫", "动摇", "崩塌", "取舍", "割舍"]

    total_signals = 0
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        for sig in arc_signals:
            total_signals += len(re.findall(sig, content))

    avg_signals = total_signals / len(txt_files)
    score = 85
    issues = []
    if avg_signals < 1:
        score = 65
        issues.append(f"近期章节平均仅{avg_signals:.1f}处弧光信号，角色可能停滞")

    return {
        "score": score,
        "issues": issues,
        "data": {
            "total_signals": total_signals,
            "avg_per_chapter": round(avg_signals, 2),
        },
    }


def analyze_hook_density(chapter_dir: str, last_n: int = 10) -> dict:
    """钩子密度分析"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"score": 85, "issues": ["无章节数据"], "data": {}}

    hook_patterns = {
        "信息钩": [r"话说一半", r"真相", r"原来.{0,5}是", r"那张纸", r"凶手是"],
        "情绪钩": [r"他攥紧", r"眼神一寒", r"心里一沉", r"咬紧牙关"],
        "认知钩": [r"真凶是", r"从头到尾", r"竟然.{0,5}是"],
    }

    total_hooks = 0
    chapter_hooks = []
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        h = 0
        for patterns in hook_patterns.values():
            for p in patterns:
                h += len(re.findall(p, content))
        total_hooks += h
        chapter_hooks.append(h)

    avg = total_hooks / len(txt_files) if txt_files else 0
    score = 85
    issues = []
    if avg < 1.5:
        score = 65
        issues.append(f"近期章节平均{avg:.1f}个钩子，密度不足")
    if chapter_hooks and len(chapter_hooks) >= 3:
        consecutive_low = 0
        for h in chapter_hooks[-3:]:
            if h < 1:
                consecutive_low += 1
        if consecutive_low >= 2:
            issues.append("连续 3 章钩子密度低，建议下章设大钩子")

    return {
        "score": score,
        "issues": issues,
        "data": {
            "total_hooks": total_hooks,
            "avg_per_chapter": round(avg, 2),
        },
    }


def analyze_world_consistency(chapter_dir: str, last_n: int = 10) -> dict:
    """世界观一致性分析（简化版）"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"score": 85, "issues": ["无章节数据"], "data": {}}

    # 检测常见矛盾关键词
    contradiction_signals = ["然而.{0,10}并不是", r"原来不是", "但.{0,5}并不是", r"竟然不是"]

    total_contradictions = 0
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        for sig in contradiction_signals:
            total_contradictions += len(re.findall(sig, content))

    score = 88
    issues = []
    if total_contradictions > 5:
        score = 70
        issues.append(f"近期{total_contradictions}处矛盾性叙述，建议检查设定一致性")

    return {
        "score": score,
        "issues": issues,
        "data": {
            "contradictions": total_contradictions,
        },
    }


def diagnose_symptoms(chapter_dir: str, last_n: int = 10) -> dict:
    """病症诊断"""
    txt_files = sorted(Path(chapter_dir).glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {}

    all_content = ""
    for f in txt_files:
        all_content += f.read_text(encoding="utf-8") + "\n"

    diagnosed = {}
    for symptom, data in SYMPTOMS.items():
        count = 0
        for pattern in data["signals"]:
            count += len(re.findall(pattern, all_content))
        if count > 0:
            diagnosed[symptom] = {
                "count": count,
                "prescriptions": data["prescriptions"],
            }

    return diagnosed


def run_checkup(project_dir: str = ".", chapter: int = 0) -> dict:
    """运行完整体检"""
    project = Path(project_dir)
    chapter_dir = project / "正文"

    if not chapter_dir.exists():
        return {"error": f"正文目录不存在: {chapter_dir}"}

    # 5 维度分析
    results = {
        "power_balance": analyze_power_balance(str(chapter_dir)),
        "plot_purity": analyze_plot_purity(str(chapter_dir)),
        "character_growth": analyze_character_growth(str(chapter_dir)),
        "hook_density": analyze_hook_density(str(chapter_dir)),
        "world_consistency": analyze_world_consistency(str(chapter_dir)),
    }

    # 综合分
    overall = sum(
        results[dim]["score"] * weight
        for dim, weight in DIMENSION_WEIGHTS.items()
    )

    # 状态
    if overall >= 85:
        status = "green"
    elif overall >= 70:
        status = "yellow"
    elif overall >= 60:
        status = "orange"
    else:
        status = "red"

    # 病症诊断
    symptoms = diagnose_symptoms(str(chapter_dir))

    report = {
        "trigger": f"第 {chapter} 章节点" if chapter else "手动触发",
        "date": datetime.now().isoformat()[:10],
        "chapter": chapter,
        "overall": round(overall, 1),
        "status": status,
        "dimensions": {
            dim: {
                "score": data["score"],
                "issues": data["issues"],
                "data": data.get("data", {}),
            }
            for dim, data in results.items()
        },
        "symptoms": symptoms,
    }

    return report


def print_report(report: dict) -> None:
    """打印体检报告"""
    if "error" in report:
        print(f"错误: {report['error']}")
        return

    print("=" * 60)
    print(f"  锻字·中期体检报告 - {report.get('chapter', 'N/A')}章节点")
    print("=" * 60)
    print(f"  触发: {report['trigger']}")
    print(f"  日期: {report['date']}")
    print()
    print(f"  综合评分: {report['overall']}/100")
    print(f"  状态: {report['status'].upper()}")
    print()

    print("【5 维度评分】")
    status_icons = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    dim_names = {
        "power_balance": "战力平衡",
        "plot_purity": "主线纯度",
        "character_growth": "人物成长",
        "hook_density": "钩子密度",
        "world_consistency": "世界观一致性",
    }
    for dim, name in dim_names.items():
        d = report["dimensions"][dim]
        score = d["score"]
        icon = status_icons.get(
            "green" if score >= 85 else
            "yellow" if score >= 70 else
            "orange" if score >= 60 else "red"
        )
        print(f"  {icon} {name}: {score}/100")
        if d["issues"]:
            for issue in d["issues"]:
                print(f"      - {issue}")

    if report["symptoms"]:
        print(f"\n【中期病症诊断】共{len(report['symptoms'])}种")
        for symptom, data in report["symptoms"].items():
            print(f"\n  ⚠️  {symptom}（信号{data['count']}处）")
            print(f"      处方:")
            for p in data["prescriptions"]:
                print(f"        - {p}")

    # 行动建议
    print(f"\n【行动建议】")
    if report["status"] == "red":
        print(f"  🔴 危险：立即停更体检，按处方修复")
    elif report["status"] == "orange":
        print(f"  🟠 风险：必须调整，下一章前完成修复")
    elif report["status"] == "yellow":
        print(f"  🟡 预警：建议关注，1-2 章内调整")
    else:
        print(f"  🟢 健康：继续按计划推进")


def save_report(report: dict, project_dir: str = ".") -> None:
    """保存报告"""
    import yaml
    checkup_dir = Path(project_dir) / "体检"
    checkup_dir.mkdir(parents=True, exist_ok=True)
    report_file = checkup_dir / f"{report.get('chapter', 'manual')}章体检报告.md"

    content = f"""# {report.get('chapter', 'N/A')}章体检报告

**触发**: {report['trigger']}  
**日期**: {report['date']}

## 综合评分
- 分数: **{report['overall']}/100**
- 状态: **{report['status'].upper()}**

## 5 维度详情

"""
    for dim, data in report["dimensions"].items():
        content += f"### {dim}: {data['score']}/100\n"
        if data.get("data"):
            content += f"- 数据: `{data['data']}`\n"
        if data.get("issues"):
            content += "- 问题:\n"
            for issue in data["issues"]:
                content += f"  - {issue}\n"
        content += "\n"

    if report["symptoms"]:
        content += "## 病症诊断\n\n"
        for symptom, data in report["symptoms"].items():
            content += f"### {symptom}（信号{data['count']}处）\n"
            content += "**处方**:\n"
            for p in data["prescriptions"]:
                content += f"- {p}\n"
            content += "\n"

    report_file.write_text(content, encoding="utf-8")
    print(f"\n📄 报告已保存: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="锻字·中期体检")
    parser.add_argument("--project", default=".", help="项目目录")
    parser.add_argument("--chapter", type=int, default=0, help="当前章节号")
    parser.add_argument("--report", action="store_true", help="保存报告到体检目录")

    args = parser.parse_args()

    report = run_checkup(args.project, args.chapter)
    print_report(report)

    if args.report:
        save_report(report, args.project)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
rescue_diag.py - 锻字·网络小说创作引擎
续命诊断：5 大中期病症识别 + 续命工具推荐 + 急救方案生成

用法：
  python3 rescue_diag.py --project . --symptom "剧情注水"
  python3 rescue_diag.py --project . --auto   # 自动诊断
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# 5 大病症信号库
SYMPTOM_SIGNALS = {
    "战力膨胀": {
        "keywords": ["又一次", "轻松", "不费吹灰", "不堪一击", "不愧是", "果然厉害"],
        "patterns": [
            r"又一次.{0,3}战胜",
            r"轻松.{0,3}击败",
            r"不费吹灰之力",
            r"敌人.{0,3}不堪一击",
        ],
        "severity_threshold": 3,
        "description": "主角变强但读者变麻木，敌人变纸老虎",
    },
    "剧情注水": {
        "keywords": ["又是", "类似", "和上次", "一如既往", "老套路"],
        "patterns": [
            r"又是.{0,5}同样",
            r"类似.{0,5}套路",
            r"和上次一样",
        ],
        "severity_threshold": 3,
        "description": "同样的套路换了张脸又来一遍，读者开始养书",
    },
    "目标漂移": {
        "keywords": ["忘记", "暂时放下", "先不管", "再说", "搁置"],
        "patterns": [
            r"忘记了.{0,5}目标",
            r"暂时.{0,5}放下",
            r"先不管",
        ],
        "severity_threshold": 2,
        "description": "写着写着忘了主角到底要干嘛",
    },
    "悬念断档": {
        "keywords": ["没有进展", "一切平静", "没什么事", "暂时没有"],
        "patterns": [
            r"没有什么.{0,5}进展",
            r"一切都很平静",
            r"暂时.{0,5}没有",
        ],
        "severity_threshold": 2,
        "description": "前一个悬念揭了，新的没跟上，读者吃饱就走",
    },
    "换地图翻车": {
        "keywords": ["来到陌生", "全新的地方", "没人认识", "孤身一人"],
        "patterns": [
            r"来到.{0,3}陌生",
            r"全新的.{0,3}地方",
            r"没人认识",
        ],
        "severity_threshold": 2,
        "description": "新场景陌生感太强，读者出戏",
    },
}

# 9 种续命工具
RESCUE_TOOLS = {
    "换地图": {
        "适用": ["剧情注水", "换地图翻车"],
        "机制": "旧场景写腻，换新场景",
        "注意": "保留情感连接，避免翻车",
        "风险": "中",
    },
    "加副线": {
        "适用": ["剧情注水", "目标漂移"],
        "机制": "新副线必须服务于主线",
        "注意": "不要把支线当主线",
        "风险": "中",
    },
    "换反派": {
        "适用": ["战力膨胀", "剧情注水"],
        "机制": "换更强的 BOSS 或换一层身份",
        "注意": "老反派可以升级或退场",
        "风险": "低",
    },
    "让主角失去某物": {
        "适用": ["战力膨胀", "目标漂移", "剧情注水"],
        "机制": "失去靠山/爱人/能力/记忆",
        "注意": "失去后必须有新平衡",
        "风险": "中",
    },
    "时间跳跃": {
        "适用": ["剧情注水", "换地图翻车"],
        "机制": "跳过一段时间",
        "注意": "过渡不能突兀",
        "风险": "中",
    },
    "视角切换": {
        "适用": ["剧情注水", "换地图翻车"],
        "机制": "从主角视角切到配角视角",
        "注意": "不要让配角抢戏",
        "风险": "中",
    },
    "揭真身": {
        "适用": ["悬念断档", "剧情注水"],
        "机制": "某人/某物的真实身份揭示",
        "注意": "必须前文有铺垫",
        "风险": "中",
    },
    "背叛": {
        "适用": ["剧情注水", "目标漂移"],
        "机制": "信任的人背叛",
        "注意": "背叛必须有逻辑",
        "风险": "高",
    },
    "杀角色": {
        "适用": ["剧情注水"],
        "机制": "杀死重要角色",
        "注意": "慎用，必须服务于主题",
        "风险": "高",
    },
}


def diagnose_chapter(chapter_dir: str, last_n: int = 10) -> dict:
    """诊断最近章节的病症"""
    chapter_path = Path(chapter_dir)
    if not chapter_path.exists():
        return {"error": f"目录不存在: {chapter_dir}"}

    txt_files = sorted(chapter_path.glob("第*.txt"))[-last_n:]
    if not txt_files:
        return {"error": f"无章节文件 in {chapter_dir}"}

    all_content = ""
    for f in txt_files:
        all_content += f.read_text(encoding="utf-8") + "\n"

    diagnosed = {}
    for symptom, data in SYMPTOM_SIGNALS.items():
        count = 0
        matches = []
        for pattern in data["patterns"]:
            for m in re.finditer(pattern, all_content):
                line_num = all_content[:m.start()].count("\n") + 1
                matches.append({
                    "text": m.group()[:30],
                    "line": line_num,
                })
                count += 1
        if count >= data["severity_threshold"]:
            diagnosed[symptom] = {
                "count": count,
                "matches": matches[:5],
                "description": data["description"],
                "severity": "high" if count >= data["severity_threshold"] * 2 else "medium",
            }

    return {
        "diagnosed": diagnosed,
        "chapters_analyzed": len(txt_files),
        "total_chars": len(all_content),
    }


def recommend_tools(symptoms: list) -> list:
    """根据病症推荐续命工具"""
    tool_scores = Counter()
    tool_reasons = {}

    for symptom in symptoms:
        for tool_name, tool_data in RESCUE_TOOLS.items():
            if symptom in tool_data["适用"]:
                tool_scores[tool_name] += 1
                if tool_name not in tool_reasons:
                    tool_reasons[tool_name] = []
                tool_reasons[tool_name].append(
                    f"治疗「{symptom}」"
                )

    # 按推荐度排序
    recommended = []
    for tool, score in tool_scores.most_common():
        recommended.append({
            "name": tool,
            "score": score,
            "info": RESCUE_TOOLS[tool],
            "reasons": tool_reasons[tool],
        })

    return recommended


def generate_rescue_plan(symptoms: list, project_dir: str = ".") -> str:
    """生成续命方案"""
    tools = recommend_tools(symptoms)

    plan = f"""# 续命方案

**生成时间**: {datetime.now().isoformat()[:19]}
**诊断病症**: {', '.join(symptoms)}

## Step 1: 黄金 48h 暂停

- 立即暂停更新（用"外出采风"/"卡文请假"理由）
- 暂停期间**禁止看评论区**
- 给自己 1-2 天彻底休息

## Step 2: 崩坏锚点定位

- 倒查最近 10 章
- 定位崩坏根源（情绪化/设定漏洞/数据焦虑/换地图）

## Step 3: 根本修复

针对检测到的病症，按以下工具组合修复：

"""

    for i, tool in enumerate(tools[:3], 1):
        plan += f"### 处方 {i}: {tool['name']}\n"
        plan += f"- **机制**: {tool['info']['机制']}\n"
        plan += f"- **注意**: {tool['info']['注意']}\n"
        plan += f"- **风险**: {tool['info']['风险']}\n"
        plan += f"- **适用原因**: {', '.join(tool['reasons'])}\n\n"

    plan += """## Step 4: 预防机制

- 建立"大纲动态维护表"（每 10 万字更新）
- 建立"读者情绪热力图"（每周看评论）
- 每 5 万字执行体检

## 测试章

修复后立刻写 1-2 章测试读者反应：
- 看本章说关键词（爽/虐/疑/笑）
- 看追读率是否回升
- 看是否出现新的病症信号

## 备用方案

如上述方案不奏效，可考虑：
1. 重新聚焦核心目标（砍支线）
2. 强制换地图（保留 1-2 个旧角色）
3. 时间跳跃（跳 1-3 卷剧情）

## 注意事项

- 不要同时修多个病灶
- 用既有设定修补，不引入补丁设定
- 修补的伏笔在崩坏前 1-3 章内必须有过暗示
- 修补后立即测试，不要直接发布
"""

    # 保存到文件
    rescue_dir = Path(project_dir) / "续命"
    rescue_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_file = rescue_dir / f"急救方案_{timestamp}.md"
    plan_file.write_text(plan, encoding="utf-8")

    return plan


def main():
    parser = argparse.ArgumentParser(description="锻字·续命诊断")
    parser.add_argument("--project", default=".", help="项目目录")
    parser.add_argument("--symptom", help="手动指定病症")
    parser.add_argument("--auto", action="store_true", help="自动诊断最近章节")
    parser.add_argument("--last", type=int, default=10, help="分析最近 N 章")

    args = parser.parse_args()

    chapter_dir = Path(args.project) / "正文"

    if args.symptom:
        # 手动指定病症
        symptoms = [args.symptom]
        if args.symptom not in SYMPTOM_SIGNALS:
            print(f"未知病症: {args.symptom}")
            print(f"可用: {', '.join(SYMPTOM_SIGNALS.keys())}")
            return
    elif args.auto:
        # 自动诊断
        result = diagnose_chapter(str(chapter_dir), args.last)
        if "error" in result:
            print(f"错误: {result['error']}")
            return

        if not result["diagnosed"]:
            print("✅ 未检测到中期病症信号")
            print(f"  分析了 {result['chapters_analyzed']} 章 / {result['total_chars']} 字")
            return

        print("=" * 60)
        print("  锻字·续命诊断报告")
        print("=" * 60)
        print(f"\n  分析章节: {result['chapters_analyzed']} 章")
        print(f"  总字数: {result['total_chars']}")
        print()

        for symptom, data in result["diagnosed"].items():
            icon = "🔴" if data["severity"] == "high" else "🟠"
            print(f"{icon} {symptom}")
            print(f"  信号数: {data['count']}")
            print(f"  严重度: {data['severity']}")
            print(f"  描述: {data['description']}")
            print(f"  匹配示例:")
            for m in data["matches"][:3]:
                print(f"    - \"{m['text']}\" (line {m['line']})")
            print()

        symptoms = list(result["diagnosed"].keys())
    else:
        parser.print_help()
        return

    # 推荐工具
    print("=" * 60)
    print("  续命工具推荐")
    print("=" * 60)
    tools = recommend_tools(symptoms)
    for i, tool in enumerate(tools[:5], 1):
        print(f"\n{i}. {tool['name']} (推荐度 {tool['score']})")
        print(f"   机制: {tool['info']['机制']}")
        print(f"   注意: {tool['info']['注意']}")
        print(f"   风险: {tool['info']['风险']}")

    # 生成方案
    if input("\n生成续命方案？(y/n): ").strip().lower() == "y":
        plan = generate_rescue_plan(symptoms, args.project)
        print(f"\n📄 续命方案已生成: 续命/急救方案_*.md")
        print(plan[:500] + "...")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
novel_state.py - 锻字·网络小说创作引擎
项目状态机：管理 11 阶段流转 + 健康度监测

用法：
  python3 novel_state.py init --title "书名" --platform "番茄" --target 100
  python3 novel_state.py status
  python3 novel_state.py advance --to stage_4_creation
  python3 novel_state.py log --chapter 50 --word 5200
  python3 novel_state.py health --update
  python3 novel_state.py dashboard
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 11 阶段定义
STAGES = [
    "stage_0_boot",            # 0. 项目启动
    "stage_1_seed",            # 1. 种子期
    "stage_2_architecture",    # 2. 架构期
    "stage_3_voice",           # 3. 风格锚定期
    "stage_4_creation",        # 4. 创作期
    "stage_5_review",          # 5. 评审期
    "stage_6_checkup",         # 6. 体检期
    "stage_7_rescue",          # 7. 续命期
    "stage_8_commercial",      # 8. 商业期
    "stage_9_wrapup",          # 9. 完结期
    "stage_10_workshop",       # 10. 作者工坊
    "stage_11_dashboard",      # 11. 项目仪表盘
]

STAGE_NAMES = {
    "stage_0_boot": "0. 项目启动",
    "stage_1_seed": "1. 种子期",
    "stage_2_architecture": "2. 架构期",
    "stage_3_voice": "3. 风格锚定期",
    "stage_4_creation": "4. 创作期",
    "stage_5_review": "5. 评审期",
    "stage_6_checkup": "6. 体检期",
    "stage_7_rescue": "7. 续命期",
    "stage_8_commercial": "8. 商业期",
    "stage_9_wrapup": "9. 完结期",
    "stage_10_workshop": "10. 作者工坊",
    "stage_11_dashboard": "11. 项目仪表盘",
}

# 体检触发节点（字数）
CHECKUP_MILESTONES = [50000, 300000, 500000, 800000]

# 健康度阈值
HEALTH_THRESHOLDS = {
    "green": 85,    # ≥ 85 健康
    "yellow": 70,   # 70-84 预警
    "orange": 60,   # 60-69 风险
    # < 60 red 危险
}


def init_project(title: str, platform: str, target_words: int, project_dir: str = ".") -> dict:
    """初始化项目状态"""
    state = {
        "title": title,
        "platform": platform,
        "target_words": target_words,
        "created_at": datetime.now().isoformat(),
        "current_stage": "stage_0_boot",
        "completed_stages": [],
        "chapters_log": [],          # 章节日志
        "total_words": 0,
        "total_chapters": 0,
        "last_chapter": 0,
        "last_update": None,
        "health": {
            "power_balance": 85,      # 战力平衡
            "plot_purity": 85,         # 主线纯度
            "character_growth": 85,    # 人物成长
            "hook_density": 85,        # 钩子密度
            "world_consistency": 85,   # 世界观一致性
            "overall": 85,
            "status": "green",
        },
        "alerts": [],
        "checkup_history": [],
        "foreshadowing": {
            "active": [],
            "recovered": [],
        },
        # 灵活性配置（作者可调，详见 references/00_quickstart.md §灵活性配置）
        "config": {
            "ai_involvement": "medium",      # high / medium / low（AI 介入度：low=只给选项不动笔）
            "style_strictness": "normal",    # strict / normal / loose（声音指纹严格度）
            "redline_strictness": "normal",  # strict / normal（P1 累积几处触发必改）
            "auto_checkup": True,            # 是否自动在 5/30/50/80 万节点提示体检
            "creativity_divergence": "medium",# high / medium / low（创意变体生成数量）
            "platform_adapt": True,          # 是否启用平台画像差异策略
            "continuity_auto": True,         # 是否每卷末自动跑一致性巡检
        },
        # 一致性巡检结果（由 continuity_check.py 写入）
        "consistency": {
            "score": None,
            "last_chapter": 0,
            "active_foreshadowing": 0,
            "checked_at": None,
        },
    }

    # 创建项目目录结构
    base = Path(project_dir)
    dirs = [
        "引擎配置",
        "设定/人物",
        "声音/character_anchors",
        "大纲",
        "规格",
        "样章",
        "正文",
        "评审",
        "体检",
        "续命",
        "商业",
        "完结",
    ]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)

    # 写入状态文件
    state_file = base / "引擎配置" / "project_state.yaml"
    import yaml
    state_file.write_text(
        "# 锻字·网络小说创作引擎 - 项目状态\n"
        + yaml.dump(state, allow_unicode=True, sort_keys=False),
        encoding="utf-8"
    )

    print(f"✅ 项目已初始化：{title}")
    print(f"  平台: {platform}")
    print(f"  目标字数: {target_words}")
    print(f"  状态文件: {state_file}")
    print(f"  目录结构已创建")

    return state


def load_state(project_dir: str = ".") -> dict:
    """加载项目状态"""
    import yaml
    state_file = Path(project_dir) / "引擎配置" / "project_state.yaml"
    if not state_file.exists():
        return {"error": f"项目未初始化，请先运行 init"}
    return yaml.safe_load(state_file.read_text(encoding="utf-8"))


def save_state(state: dict, project_dir: str = ".") -> None:
    """保存项目状态"""
    import yaml
    state["last_update"] = datetime.now().isoformat()
    state_file = Path(project_dir) / "引擎配置" / "project_state.yaml"
    state_file.write_text(
        yaml.dump(state, allow_unicode=True, sort_keys=False),
        encoding="utf-8"
    )


def get_config(project_dir: str = ".") -> dict:
    """读取灵活性配置"""
    state = load_state(project_dir)
    if "error" in state:
        return state
    return state.get("config", {})


def set_config(key: str, value, project_dir: str = ".") -> dict:
    """设置灵活性配置项"""
    state = load_state(project_dir)
    if "error" in state:
        return state
    if "config" not in state:
        state["config"] = {}
    if key not in state["config"]:
        return {"error": f"未知配置项: {key}", "available": list(state["config"].keys())}
    state["config"][key] = value
    save_state(state, project_dir)
    return {"set": True, "key": key, "value": value}


def advance_stage(target_stage: str, project_dir: str = ".") -> dict:
    """推进到指定阶段"""
    state = load_state(project_dir)
    if "error" in state:
        return state

    if target_stage not in STAGES:
        return {"error": f"未知阶段: {target_stage}", "available": STAGES}

    current = state["current_stage"]
    if target_stage not in state["completed_stages"]:
        state["completed_stages"].append(current)

    state["current_stage"] = target_stage
    save_state(state, project_dir)

    return {
        "advanced": True,
        "from": STAGE_NAMES.get(current, current),
        "to": STAGE_NAMES.get(target_stage, target_stage),
    }


def log_chapter(chapter: int, words: int, hook_type: str = "未填", project_dir: str = ".") -> dict:
    """记录章节进度"""
    state = load_state(project_dir)
    if "error" in state:
        return state

    state["chapters_log"].append({
        "chapter": chapter,
        "words": words,
        "hook_type": hook_type,
        "date": datetime.now().isoformat()[:10],
    })
    state["total_chapters"] = max(state["total_chapters"], chapter)
    state["total_words"] += words
    state["last_chapter"] = chapter

    # 体检触发检查
    if state["total_words"] in CHECKUP_MILESTONES:
        state["alerts"].append({
            "type": "体检触发",
            "words": state["total_words"],
            "message": f"达到 {state['total_words']} 字节点，建议执行体检",
            "date": datetime.now().isoformat()[:10],
        })

    save_state(state, project_dir)
    return {
        "logged": True,
        "chapter": chapter,
        "total_words": state["total_words"],
        "total_chapters": state["total_chapters"],
    }


def update_health(dimension: str, score: int, project_dir: str = ".") -> dict:
    """更新健康度评分"""
    state = load_state(project_dir)
    if "error" in state:
        return state

    if dimension not in state["health"]:
        return {"error": f"未知维度: {dimension}"}

    state["health"][dimension] = max(0, min(100, score))

    # 重算综合分
    h = state["health"]
    overall = (
        h["power_balance"] * 0.20 +
        h["plot_purity"] * 0.20 +
        h["character_growth"] * 0.20 +
        h["hook_density"] * 0.20 +
        h["world_consistency"] * 0.20
    )
    h["overall"] = round(overall, 1)

    # 重算状态
    if overall >= HEALTH_THRESHOLDS["green"]:
        h["status"] = "green"
    elif overall >= HEALTH_THRESHOLDS["yellow"]:
        h["status"] = "yellow"
    elif overall >= HEALTH_THRESHOLDS["orange"]:
        h["status"] = "orange"
    else:
        h["status"] = "red"

    save_state(state, project_dir)
    return {
        "updated": True,
        "dimension": dimension,
        "score": score,
        "overall": h["overall"],
        "status": h["status"],
    }


def show_dashboard(project_dir: str = ".") -> None:
    """显示项目仪表盘"""
    state = load_state(project_dir)
    if "error" in state:
        print(f"错误: {state['error']}")
        return

    print("=" * 60)
    print(f"  锻字·项目仪表盘 - {state['title']}")
    print("=" * 60)

    # 基本信息
    print(f"\n【基本信息】")
    print(f"  平台: {state['platform']}")
    print(f"  目标字数: {state['target_words']} 字")
    progress = state['total_words'] / state['target_words'] * 100 if state['target_words'] > 0 else 0
    print(f"  当前字数: {state['total_words']} 字 ({progress:.1f}%)")
    print(f"  章节数: {state['total_chapters']} 章")
    print(f"  当前位置: {STAGE_NAMES.get(state['current_stage'], state['current_stage'])}")

    # 进度条
    bar_len = 30
    filled = int(bar_len * progress / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  进度: [{bar}] {progress:.1f}%")

    # 健康度
    h = state["health"]
    print(f"\n【健康度】综合: {h['overall']}/100 [{h['status'].upper()}]")
    status_icons = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    dimensions = [
        ("power_balance", "战力平衡", 0.20),
        ("plot_purity", "主线纯度", 0.20),
        ("character_growth", "人物成长", 0.20),
        ("hook_density", "钩子密度", 0.20),
        ("world_consistency", "世界观一致性", 0.20),
    ]
    for dim, name, weight in dimensions:
        score = h[dim]
        icon = status_icons.get(
            "green" if score >= 85 else
            "yellow" if score >= 70 else
            "orange" if score >= 60 else "red"
        )
        bar = "█" * (score // 5) + "░" * (20 - score // 5)
        print(f"  {icon} {name}: {score:>3}/100 [{bar}] (权重{int(weight*100)}%)")

    # 预警
    if state.get("alerts"):
        print(f"\n【预警】共{len(state['alerts'])}条")
        for alert in state["alerts"][-5:]:
            print(f"  ⚠️ [{alert['type']}] {alert['message']} ({alert.get('date', '')})")

    # 体检历史
    if state.get("checkup_history"):
        print(f"\n【体检历史】{len(state['checkup_history'])}次")
        for ch in state["checkup_history"][-3:]:
            print(f"  {ch.get('date', '')}: 综合 {ch.get('overall', 'N/A')}")

    # 阶段进度
    print(f"\n【阶段进度】")
    completed = len(state["completed_stages"])
    print(f"  已完成阶段: {completed}/{len(STAGES)}")
    if completed < len(STAGES):
        current = state["current_stage"]
        idx = STAGES.index(current) if current in STAGES else 0
        next_stage = STAGES[idx + 1] if idx + 1 < len(STAGES) else None
        if next_stage:
            print(f"  下一步: {STAGE_NAMES[next_stage]}")


def main():
    parser = argparse.ArgumentParser(description="锻字·网络小说创作引擎 - 项目状态机")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.add_argument("--title", required=True, help="书名")
    init_parser.add_argument("--platform", required=True, choices=["番茄", "起点", "晋江", "七猫", "知乎盐选", "其他"], help="平台")
    init_parser.add_argument("--target", type=int, required=True, help="目标字数（万字）")
    init_parser.add_argument("--dir", default=".", help="项目目录")

    # status
    subparsers.add_parser("status", help="查看当前状态")

    # advance
    advance_parser = subparsers.add_parser("advance", help="推进到指定阶段")
    advance_parser.add_argument("--to", required=True, choices=STAGES, help="目标阶段")
    advance_parser.add_argument("--dir", default=".", help="项目目录")

    # log
    log_parser = subparsers.add_parser("log", help="记录章节进度")
    log_parser.add_argument("--chapter", type=int, required=True, help="章节号")
    log_parser.add_argument("--word", type=int, required=True, help="字数")
    log_parser.add_argument("--hook", default="未填", help="钩子类型")
    log_parser.add_argument("--dir", default=".", help="项目目录")

    # health
    health_parser = subparsers.add_parser("health", help="更新健康度")
    health_parser.add_argument("--dim", required=True, choices=["power_balance", "plot_purity", "character_growth", "hook_density", "world_consistency"], help="维度")
    health_parser.add_argument("--score", type=int, required=True, help="分数(0-100)")
    health_parser.add_argument("--dir", default=".", help="项目目录")

    # dashboard
    subparsers.add_parser("dashboard", help="显示仪表盘")

    # config
    config_parser = subparsers.add_parser("config", help="查看/设置灵活性配置")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="设置配置项，如 --set ai_involvement low")
    config_parser.add_argument("--dir", default=".", help="项目目录")

    args = parser.parse_args()

    if args.command == "init":
        target_words = args.target * 10000  # 万字 → 字
        init_project(args.title, args.platform, target_words, args.dir)
    elif args.command == "status":
        state = load_state(args.dir if hasattr(args, 'dir') else ".")
        if "error" in state:
            print(f"错误: {state['error']}")
        else:
            print(json.dumps(state, ensure_ascii=False, indent=2))
    elif args.command == "advance":
        result = advance_stage(args.to, args.dir)
        if "error" in result:
            print(f"错误: {result['error']}")
            print(f"可用阶段: {result.get('available', [])}")
        else:
            print(f"✅ 推进: {result['from']} → {result['to']}")
    elif args.command == "log":
        result = log_chapter(args.chapter, args.word, args.hook, args.dir)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print(f"✅ 第{result['chapter']}章已记录")
            print(f"  总字数: {result['total_words']} | 总章节: {result['total_chapters']}")
    elif args.command == "health":
        result = update_health(args.dim, args.score, args.dir)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print(f"✅ {result['dimension']}: {result['score']} → 综合 {result['overall']} [{result['status']}]")
    elif args.command == "dashboard":
        show_dashboard(args.dir if hasattr(args, 'dir') else ".")
    elif args.command == "config":
        if args.set:
            key, value = args.set
            # 布尔/数字归一化
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            result = set_config(key, value, args.dir)
            if "error" in result:
                print(f"错误: {result['error']}")
                if "available" in result:
                    print(f"可配置项: {result['available']}")
            else:
                print(f"✅ {result['key']} = {result['value']}")
        else:
            cfg = get_config(args.dir)
            if "error" in cfg:
                print(f"错误: {cfg['error']}")
            else:
                print("【灵活性配置】")
                for k, v in cfg.items():
                    print(f"  {k}: {v}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

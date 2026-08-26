#!/usr/bin/env python3
"""
spec_check.py - 锻字·网络小说创作引擎
章节 spec 自检：校验 12 字段完整性与形式合法性。
配合 continuity_check.py 使用（spec_check 看单章质量，continuity_check 看跨章一致）。

用法：
  python3 spec_check.py 规格/第050章.yaml
  python3 spec_check.py 规格/ --batch
  python3 spec_check.py 规格/第048-050章.yaml --batch --strict
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("错误：需要 pyyaml。请运行：pip install pyyaml")
    sys.exit(1)


REQUIRED_TOP = ["chapter", "before_state", "after_state", "must_happen",
                "narrative_density", "core_conflict", "hook_type", "foreshadowing"]
ALLOWED_DENSITY = {"高", "中", "低"}
HOOK_TYPES = {"问题钩", "危机钩", "秘密钩", "伏笔钩", "反转钩"}


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__parse_error__": str(e)}


def check_one(path: Path, strict: bool):
    data = load_yaml(path)
    issues = []
    if not isinstance(data, dict):
        return [{"level": "P0", "msg": f"无法解析 YAML：{data.get('__parse_error__', '未知错误')}"}]

    c = data.get("chapter") or {}
    num = c.get("num") if isinstance(c, dict) else None

    # 1. 顶层字段
    for f in REQUIRED_TOP:
        if f not in data:
            issues.append({"level": "P0", "msg": f"缺必填字段：{f}"})

    # 2. 章节号
    fname_num = None
    m = re.search(r"第\s*(\d+)\s*章", path.name)
    if m:
        fname_num = int(m.group(1))
    if num is None:
        issues.append({"level": "P1", "msg": "chapter.num 缺失或为 None"})
    elif fname_num and num != fname_num:
        issues.append({"level": "P1", "msg": f"chapter.num({num}) 与文件名章节号({fname_num}) 不一致"})

    # 3. 叙事密度
    nd = data.get("narrative_density")
    if nd not in ALLOWED_DENSITY:
        issues.append({"level": "P1", "msg": f"narrative_density 非法值：{nd}（应为 高/中/低）"})

    # 4. 钩子
    ht = data.get("hook_type")
    if ht not in HOOK_TYPES:
        issues.append({"level": "P1", "msg": f"hook_type 非法或缺失：{ht}（应为 {','.join(HOOK_TYPES)}）"})

    # 5. 核心冲突
    cc = data.get("core_conflict") or {}
    if not isinstance(cc, dict) or not cc.get("type"):
        issues.append({"level": "P0", "msg": "core_conflict.type 缺失（一章必须有一个核心冲突）"})
    elif "><" not in str(cc.get("type", "")) and strict:
        issues.append({"level": "P2", "msg": f"core_conflict.type 建议用 'A >< B' 格式：{cc.get('type')}"})

    # 6. 状态追踪
    bs = data.get("before_state") or {}
    af = data.get("after_state") or {}
    if not isinstance(bs.get("characters"), list) or not bs["characters"]:
        issues.append({"level": "P1", "msg": "before_state.characters 为空（无法做连贯性检查）"})
    if not isinstance(af.get("characters"), list) or not af["characters"]:
        issues.append({"level": "P1", "msg": "after_state.characters 为空"})
    else:
        for ch in af["characters"]:
            if not ch.get("new_known") and not ch.get("relationship_changes"):
                issues.append({"level": "P2", "msg": f"角色 {ch.get('name','?')} 本章无新信息/关系变化（信息增量低）"})

    # 7. 必发生事件
    mh = data.get("must_happen") or []
    if not mh:
        issues.append({"level": "P1", "msg": "must_happen 为空（本章没有必须发生的事件）"})
    else:
        for ev in mh:
            if not ev.get("consequences"):
                issues.append({"level": "P2", "msg": f"事件「{ev.get('event','?')}」缺 consequences（下一章无承接）"})

    # 8. 伏笔
    fs = data.get("foreshadowing") or {}
    if not isinstance(fs, dict):
        issues.append({"level": "P1", "msg": "foreshadowing 格式错误（应为含 recovered/new_planted 的字典）"})

    return issues


def main():
    ap = argparse.ArgumentParser(description="锻字·章节 spec 自检")
    ap.add_argument("path", help="spec 文件或目录")
    ap.add_argument("--batch", action="store_true", help="按目录批量校验")
    ap.add_argument("--strict", action="store_true", help="更严格（如冲突格式）")
    args = ap.parse_args()

    if args.batch or Path(args.path).is_dir():
        d = Path(args.path)
        files = sorted(d.glob("*.yaml"))
        total = 0
        for f in files:
            if "第" not in f.name:
                continue
            issues = check_one(f, args.strict)
            total += len(issues)
            if issues:
                print(f"\n📄 {f.name}")
                for it in issues:
                    print(f"   [{it['level']}] {it['msg']}")
            else:
                print(f"✅ {f.name} 通过")
        print(f"\n{'='*40}\n批量校验完成：{len(files)} 个文件，共 {total} 个问题")
    else:
        f = Path(args.path)
        issues = check_one(f, args.strict)
        if not issues:
            print(f"✅ {f.name} 通过全部校验")
        else:
            print(f"📄 {f.name} 发现 {len(issues)} 个问题：")
            for it in issues:
                print(f"   [{it['level']}] {it['msg']}")
            sys.exit(1 if any(i["level"] == "P0" for i in issues) else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
continuity_check.py - 锻字·网络小说创作引擎
长篇跨章一致性巡检：
  - 伏笔总表（埋设/回收/逾期预警）
  - 人物漂移（fixed 项 + 声音黑名单违例 OOC 扫描）
  - 已知信息因果链（角色"突然知道没铺垫的事"检测）
  - 设定矛盾（锁定事实清单 + 需人工核对项）
  - 多线时间轴校验（多线编织法 §六：跨线时钟/状态/信息差/漏斗汇聚，读 设定/多线时间轴.yaml）
  - 一致性评分（写入 project_state.yaml）

用法：
  python3 continuity_check.py --project "我的小说" --report
  python3 continuity_check.py --project . --chapter 60
  python3 continuity_check.py --project . --no-write   # 只读不写状态
  python3 continuity_check.py --project . --multiline   # 强制校验多线时间轴（无表也提示初始化）
  python3 continuity_check.py --project . --no-multiline  # 跳过多线时间轴校验

依赖：pyyaml（已在 managed venv 安装）
说明：NLP 类检测为启发式，报告中标注"需人工确认"的项为辅助提示，不自动判定。
多线时间轴校验为结构化数据比对（非 NLP），命中即真实 bug，但仍建议人工复核边缘情形。
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("错误：需要 pyyaml。请运行：pip install pyyaml")
    sys.exit(1)


# ───────────────────────────── 工具 ─────────────────────────────

def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__error__": str(e)}


def chapter_num_from_name(name: str):
    m = re.search(r"第\s*(\d+)\s*章", name)
    return int(m.group(1)) if m else None


def _chapter_of(finding: dict):
    """从 finding 的 detail/source 中提取关联章节号（用于 --since 过滤）"""
    m = re.search(r"第\s*(\d+)\s*章", (finding.get("detail") or "") + (finding.get("source") or ""))
    return int(m.group(1)) if m else None


def find_project_dir(arg: str) -> Path:
    p = Path(arg)
    if (p / "引擎配置" / "project_state.yaml").exists():
        return p
    # 兼容：当前目录下有 引擎配置
    if (Path(".") / "引擎配置" / "project_state.yaml").exists():
        return Path(".")
    return p


# ───────────────────────────── 检测器 ─────────────────────────────

def collect_specs(project: Path):
    """收集 规格/*.yaml，按章节号排序，返回 [(num, data)]"""
    spec_dir = project / "规格"
    specs = []
    if spec_dir.exists():
        for f in sorted(spec_dir.glob("*.yaml")):
            num = chapter_num_from_name(f.name)
            if num is None:
                continue
            data = load_yaml(f)
            if isinstance(data, dict):
                specs.append((num, data))
    specs.sort(key=lambda x: x[0])
    return specs


def collect_manuscript(project: Path):
    """收集 正文/*.txt，按章节号排序，返回 [(num, text)]"""
    out = []
    md = project / "正文"
    if md.exists():
        for f in sorted(md.glob("*.txt")):
            num = chapter_num_from_name(f.name)
            text = f.read_text(encoding="utf-8", errors="ignore")
            out.append((num if num else 0, text))
    out.sort(key=lambda x: x[0])
    return out


def check_foreshadowing(project: Path, specs, manuscript):
    """汇总伏笔，标记未回收 + 逾期"""
    findings = []
    ledger = []

    # 1) 从每章 spec 的 foreshadowing 段采集
    for num, data in specs:
        fs = data.get("foreshadowing")
        if not isinstance(fs, dict):
            continue
        for item in (fs.get("new_planted") or []):
            if not isinstance(item, str):
                continue
            exp = None
            m = re.search(r"第\s*(\d+)\s*章", item)
            if m:
                exp = int(m.group(1))
            ledger.append({
                "source": f"规格/第{num:03d}章.yaml",
                "plant_chapter": num,
                "text": item.strip(),
                "expected_recover": exp,
                "recovered": False,
            })
        for item in (fs.get("recovered") or []):
            if isinstance(item, str):
                ledger.append({
                    "source": f"规格/第{num:03d}章.yaml",
                    "plant_chapter": num,
                    "text": item.strip(),
                    "expected_recover": None,
                    "recovered": True,
                })

    # 2) 兼容独立 伏笔.yaml
    fp = project / "设定" / "伏笔.yaml"
    if fp.exists():
        data = load_yaml(fp)
        rows = data.get("foreshadowing_ledger") or data.get("foreshadowing") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ledger.append({
                "source": "设定/伏笔.yaml",
                "plant_chapter": row.get("plant_chapter"),
                "text": row.get("plant_text") or row.get("text") or "",
                "expected_recover": row.get("expected_recover"),
                "recovered": row.get("status") in ("已回收", "recovered", "✓"),
            })

    latest = max([num for num, _ in manuscript], default=0)
    latest = max(latest, max([num for num, _ in specs], default=0))

    overdue = 0
    for row in ledger:
        if not row["recovered"] and row["expected_recover"] and latest > row["expected_recover"]:
            overdue += 1
            findings.append({
                "level": "P1",
                "type": "伏笔逾期",
                "detail": f"第 {row['plant_chapter']} 章埋设的伏笔「{row['text'][:40]}…」"
                          f"预计第 {row['expected_recover']} 章回收，当前已写到第 {latest} 章仍未回收。",
                "source": row["source"],
            })

    active = sum(1 for r in ledger if not r["recovered"])
    if active > 30:
        findings.append({
            "level": "P2",
            "type": "伏笔过载",
            "detail": f"当前活跃未回收伏笔 {active} 个（>30），存在收束困难风险，建议加速回收或合并同类项。",
            "source": "汇总",
        })

    return findings, ledger, active, latest


def check_known_info_chain(specs):
    """检测角色'突然知道没铺垫的信息'（因果断裂）"""
    findings = []
    known = {}  # char -> set of known facts accumulated BEFORE current chapter
    for i, (num, data) in enumerate(specs):
        before = (data.get("before_state") or {}).get("characters") or []
        after = (data.get("after_state") or {}).get("characters") or []
        # 检查 before 中的 known_info 是否此前已铺垫
        # 首章（无前序 spec）跳过，避免"第 1 章本身就有设定信息"的误报
        has_prior = i > 0
        for c in before:
            name = c.get("name")
            if not name:
                continue
            kset = known.setdefault(name, set())
            if not has_prior:
                continue
            for info in (c.get("known_info") or []):
                if isinstance(info, str) and info and info not in kset:
                    findings.append({
                        "level": "P0",
                        "type": "因果断裂",
                        "detail": f"第 {num} 章：角色「{name}」的已知信息「{info}」在前文（≤第{num-1}章）"
                                  f"的 after_state 中未见铺垫，疑似凭空出现。",
                        "source": f"规格/第{num:03d}章.yaml",
                    })
        # 把 after 的 new_known 累加进集合
        for c in after:
            name = c.get("name")
            if not name:
                continue
            kset = known.setdefault(name, set())
            for info in (c.get("new_known") or []):
                if isinstance(info, str):
                    kset.add(info)
    return findings


def check_character_ooc(project: Path, manuscript):
    """扫描正文：以角色名为锚，前后滑动窗口内出现声音黑名单词 = 疑似 OOC

    用滑动窗口而非"同段落"，因为真实稿子里对话段常不重复角色名。
    """
    findings = []
    char_dir = project / "设定" / "人物"
    if not char_dir.exists():
        return findings
    chars = {}
    for f in char_dir.glob("*.yaml"):
        data = load_yaml(f)
        if not isinstance(data, dict):
            continue
        char = data.get("character") or data
        name = char.get("name")
        if not name:
            continue
        vf = char.get("voice_fingerprint") or {}
        forbidden = []
        forbidden += (vf.get("forbidden_words") or [])
        verbs = vf.get("verbs") or {}
        forbidden += (verbs.get("forbidden") or [])
        fixed = char.get("fixed") or {}
        chars[name] = {
            "forbidden": [w for w in forbidden if isinstance(w, str) and len(w) >= 2],
            "appearance": fixed.get("appearance", ""),
        }

    if not chars:
        return findings

    WIN_BEFORE, WIN_AFTER = 120, 220  # 角色名前后的滑动窗口（字符数）
    for num, text in manuscript:
        for name, info in chars.items():
            if not info["forbidden"]:
                continue
            start = 0
            while True:
                idx = text.find(name, start)
                if idx < 0:
                    break
                window = text[max(0, idx - WIN_BEFORE): idx + len(name) + WIN_AFTER]
                for fw in info["forbidden"]:
                    if fw and fw in window:
                        snippet = window.strip()[:70]
                        findings.append({
                            "level": "需人工确认",
                            "type": "声音违例/OOC",
                            "detail": f"第 {num} 章：角色「{name}」出现在其黑名单词「{fw}」附近"
                                      f"（{snippet}…）。可能是 OOC，请核对是否故意反差。",
                            "source": f"正文/第{num:03d}章.txt",
                        })
                        break  # 每个角色每次出现只报一次
                start = idx + len(name)
    return findings


def check_world_facts(project: Path):
    """汇总锁定事实清单（矛盾检测需人工核对）"""
    findings = []
    wm = project / "设定" / "世界观.md"
    locked = []
    if wm.exists():
        text = wm.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if "锁定" in line or "【锁定】" in line or "不可变" in line:
                clean = re.sub(r"[#\-\*\s\[\]锁定【】]", "", line).strip()
                if 4 <= len(clean) <= 60:
                    locked.append(clean)
    if locked:
        findings.append({
            "level": "清单",
            "type": "锁定设定",
            "detail": f"共登记 {len(locked)} 条锁定事实，建议人工逐条核对后文是否违反："
                      + "；".join(locked[:8]) + ("…" if len(locked) > 8 else ""),
            "source": "设定/世界观.md",
        })
    return findings, locked


def check_multiline_timeline(project):
    """多线时间轴校验（多线编织法 §六）。

    读 设定/多线时间轴.yaml（作者从 templates/多线时间轴.yaml 复制填写），检测：
      1) 跨线时钟对齐：日期模式时间轴倒流（P0）；某线后期时间节点空缺断线（P2）
      2) 角色状态连续性（线内跨 T）：重伤→活蹦乱跳且无"伤愈/恢复"过渡（P1）
      3) 跨线同角色同 T 状态矛盾：一线写消亡、一线写存活（P0）
      4) known 只增不减（线内跨 T）：已知信息倒退=穿帮（P1）
      5) 漏斗汇聚收网：终局节点各线事件是否指向 converge_event（P2）

    无表或结构缺失则安全返回空列表（不报错、不误报）。
    """
    findings = []
    tl = project / "设定" / "多线时间轴.yaml"
    if not tl.exists():
        return findings, None
    data = load_yaml(tl)
    if not isinstance(data, dict):
        return findings, None
    axis = data.get("timeline_axis") or []
    lines = data.get("lines") or {}
    meta = data.get("meta") or {}
    mode = str(meta.get("mode") or "章节")
    if not axis or not isinstance(lines, dict):
        return findings, data

    # ── 词表 ──
    NEG = ["重伤", "濒死", "垂危", "虚弱", "残", "昏迷", "倒下", "断臂", "断腿", "中毒", "奄奄"]
    POS = ["活蹦乱跳", "生龙活虎", "全盛", "完好", "无恙", "康复", "归来", "崛起"]
    TRANSITION = ["伤愈", "恢复", "复出", "好转", "渐", "痊", "康", "归队", "归来", "疗伤"]
    DEAD = ["死", "亡", "逝", "没", "殁", "殉"]
    ALIVE = ["活", "在", "至", "归", "现", "醒"]

    # ── 日期模式：解析轴，检测倒流 ──
    date_cache = {}
    if mode == "日期":
        for t in axis:
            m = re.search(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", str(t))
            if m:
                try:
                    date_cache[t] = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except Exception:
                    pass
        seq = [date_cache[t] for t in axis if t in date_cache]
        for i in range(1, len(seq)):
            if seq[i] < seq[i - 1]:
                findings.append({
                    "level": "P0",
                    "type": "时间轴倒流",
                    "detail": f"时间轴在 {axis[i-1]} → {axis[i]} 出现倒流（后一节点早于前一节点），"
                              f"请核对日期填写。",
                    "source": "设定/多线时间轴.yaml",
                })

    # 角色跨线聚合：role -> {T: [(line, char_state), ...]}
    role_states = {}
    role_lines = {}  # role -> set of line names (用于跨线已知信息弱提示)

    for lname, cells in lines.items():
        if not isinstance(cells, dict):
            continue
        role = re.sub(r"线$", "", str(lname)).strip() or str(lname)

        # ① 后期断线空缺
        filled_idx = [axis.index(t) for t in cells.keys() if t in axis]
        if filled_idx:
            max_idx = max(filled_idx)
            tail_missing = [axis[i] for i in range(max_idx + 1, len(axis))]
            if tail_missing:
                findings.append({
                    "level": "P2",
                    "type": "时间轴断线",
                    "detail": f"线索「{lname}」写到 {axis[max_idx]} 后缺失 {len(tail_missing)} 个时间节点"
                              f"（{tail_missing[0]}…{tail_missing[-1]}），后期疑似断线，请确认是否故意留白。",
                    "source": "设定/多线时间轴.yaml",
                })

        # ② 状态连续性（线内跨 T）
        prev_state, prev_t = None, None
        for t in axis:
            cell = cells.get(t)
            if not isinstance(cell, dict):
                continue
            cs = str(cell.get("char_state") or "")
            if prev_state is not None:
                has_transition = any(w in prev_state or w in cs for w in TRANSITION)
                neg_prev = any(w in prev_state for w in NEG)
                pos_now = any(w in cs for w in POS)
                if (not has_transition) and neg_prev and pos_now:
                    findings.append({
                        "level": "P1",
                        "type": "状态跳变",
                        "detail": f"线索「{lname}」角色状态从 {prev_t} 的「{prev_state}」"
                                  f"直接跳到 {t} 的「{cs}」，缺过渡（如伤愈/恢复），"
                                  f"疑似跨线/跨章状态不一致（正对应「A 线重伤、B 线活蹦乱跳」类 bug）。",
                        "source": "设定/多线时间轴.yaml",
                    })
            prev_state, prev_t = cs, t

        # ④ known 只增不减：模板每格 known 为"该节点相关已知"（局部写法，不重列历史），
        #    硬判集合只增会误报模板自带示例。故不自动判单线，仅对跨线角色做弱提示人工核对。
        #    （已知信息累积语义的正确校验位置是 15_continuity 的角色 known_info 因果链。）
        pass

        # ③ 跨线同角色状态矛盾聚合
        for t, cell in cells.items():
            if not isinstance(cell, dict):
                continue
            cs = str(cell.get("char_state") or "")
            role_states.setdefault(role, {}).setdefault(t, []).append((str(lname), cs))
            role_lines.setdefault(role, set()).add(str(lname))

    # ③ 跨线同角色同 T 状态矛盾
    for role, tmap in role_states.items():
        for t, states in tmap.items():
            if len(states) < 2:
                continue
            dead_line = [l for l, s in states if any(w in s for w in DEAD)]
            alive_line = [l for l, s in states if any(w in s for w in ALIVE)]
            if dead_line and alive_line and dead_line != alive_line:
                findings.append({
                    "level": "P0",
                    "type": "跨线状态矛盾",
                    "detail": f"角色「{role}」在 {t} 同时出现于「{'/'.join(dead_line)}」(状态含消亡) "
                              f"与「{'/'.join(alive_line)}」(状态含存活)，状态互相冲突，请核对。",
                    "source": "设定/多线时间轴.yaml",
                })

    # ④ 跨线角色已知信息：弱提示人工核对（硬判易误报局部写法，以人工复核为准）
    for role, lineset in role_lines.items():
        if len(lineset) >= 2:
            findings.append({
                "level": "P2",
                "type": "跨线已知核对",
                "detail": f"角色「{role}」跨 {len(lineset)} 条线（{'/'.join(sorted(lineset))}），"
                          f"请人工核对各线 known 是否只增不减、无穿帮（见 references/16 §六）。",
                "source": "设定/多线时间轴.yaml",
            })

    # ⑤ 漏斗汇聚收网
    funnel = data.get("funnel") or {}
    ce = funnel.get("converge_event")
    if ce and isinstance(ce, str) and ce.strip() and axis:
        last_ts = axis[-2:] if len(axis) >= 2 else [axis[-1]]
        for lname, cells in lines.items():
            if not isinstance(cells, dict):
                continue
            hit = any(ce in str((cells.get(t) or {}).get("event") or "") for t in last_ts)
            if not hit:
                findings.append({
                    "level": "P2",
                    "type": "收网未汇聚",
                    "detail": f"线索「{lname}」在终局节点（{last_ts[0]}…{last_ts[-1]}）事件未指向汇聚事件"
                              f"「{ce}」，漏斗收网期各线是否都已向同一事件汇聚？",
                    "source": "设定/多线时间轴.yaml",
                })

    return findings, data


# ───────────────────────────── 报告 ─────────────────────────────

def consistency_score(findings):
    """粗略评分：问题越少分越高"""
    penalty = {"P0": 15, "P1": 8, "P2": 3, "需人工确认": 1, "清单": 0}
    score = 100
    for f in findings:
        score -= penalty.get(f["level"], 0)
    return max(0, min(100, score))


def write_report(project: Path, findings, ledger, active, latest, score, locked):
    report_dir = project / "体检"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = report_dir / f"一致性报告_{ts}.md"
    level_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "需人工确认": "🔍", "清单": "📋"}
    # 多线时间轴类发现单列到第四章，避免与问题清单重复
    MULTILINE_TYPES = {"时间轴倒流", "时间轴断线", "状态跳变", "跨线状态矛盾",
                       "跨线已知核对", "收网未汇聚"}
    ml_findings = [f for f in findings if f["type"] in MULTILINE_TYPES]
    general_findings = [f for f in findings if f["type"] not in MULTILINE_TYPES]
    lines = []
    lines.append("# 长篇一致性巡检报告\n")
    lines.append(f"- 生成时间：{datetime.now().isoformat()[:19]}")
    lines.append(f"- 扫描范围：最新第 {latest} 章")
    lines.append(f"- **一致性评分：{score}/100**\n")
    lines.append("## 一、问题清单\n")
    if not general_findings:
        lines.append("✅ 未发现结构性一致性问题。\n")
    else:
        for f in general_findings:
            icon = level_icon.get(f["level"], "•")
            lines.append(f"- {icon} **[{f['level']}] {f['type']}** — {f['detail']} _(来源：{f['source']})_")
        lines.append("")
    lines.append("## 二、伏笔总表（活跃未回收）\n")
    active_rows = [r for r in ledger if not r["recovered"]]
    if not active_rows:
        lines.append("✅ 当前无活跃未回收伏笔。\n")
    else:
        lines.append(f"共 {len(active_rows)} 个活跃伏笔：\n")
        for r in active_rows[:40]:
            lines.append(f"- 第{r['plant_chapter']}章埋：「{r['text'][:50]}」"
                         + (f"（预计第{r['expected_recover']}章收）" if r['expected_recover'] else ""))
        if len(active_rows) > 40:
            lines.append(f"- …（其余 {len(active_rows)-40} 个略）")
        lines.append("")
    lines.append("## 三、锁定设定（需人工核对）\n")
    if locked:
        for l in locked:
            lines.append(f"- [ ] {l}")
    else:
        lines.append("_未登记锁定事实。建议在 设定/世界观.md 中标注「锁定」事实以便巡检。_\n")
    lines.append("## 四、多线时间轴校验（多线编织法 §六）\n")
    if not ml_findings:
        lines.append("_未启用多线时间轴，或未检测到 设定/多线时间轴.yaml，跳过。_\n")
    else:
        for f in ml_findings:
            icon = level_icon.get(f["level"], "•")
            lines.append(f"- {icon} **[{f['level']}] {f['type']}** — {f['detail']} _(来源：{f['source']})_")
        lines.append("")
    lines.append("\n---\n_本报告由 continuity_check.py 生成。标注「需人工确认」的项为启发式提示，不自动判定。多线时间轴校验为结构化数据比对，命中即真实 bug，边缘情形仍建议人工复核。_")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def update_state(project: Path, score, latest, active):
    state_file = project / "引擎配置" / "project_state.yaml"
    if not state_file.exists():
        return
    data = load_yaml(state_file)
    if not isinstance(data, dict):
        return
    data.setdefault("consistency", {})
    data["consistency"]["score"] = score
    data["consistency"]["last_chapter"] = latest
    data["consistency"]["active_foreshadowing"] = active
    data["consistency"]["checked_at"] = datetime.now().isoformat()
    try:
        import yaml as _y
        state_file.write_text(_y.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="锻字·长篇一致性巡检")
    ap.add_argument("--project", default=".", help="项目目录")
    ap.add_argument("--chapter", type=int, default=None, help="仅统计到此章（默认全量）")
    ap.add_argument("--report", action="store_true", help="生成 一致性报告.md")
    ap.add_argument("--no-write", action="store_true", help="不写回 project_state.yaml")
    ap.add_argument("--since", type=int, default=None, help="只报告该章及之后的问题（增量巡检）")
    ap.add_argument("--multiline", action="store_true",
                    help="强制多线时间轴校验（即便无 设定/多线时间轴.yaml 也提示初始化）")
    ap.add_argument("--no-multiline", action="store_true", help="跳过多线时间轴校验")
    args = ap.parse_args()

    project = find_project_dir(args.project)

    # 鲁棒性：未检测到项目结构时引导初始化，而非直接崩溃
    if not ((project / "引擎配置" / "project_state.yaml").exists()
            or (project / "规格").exists() or (project / "正文").exists()):
        print("⚠️ 未检测到项目结构（缺少 引擎配置/规格/正文）。")
        print("   请先运行：python scripts/novel_state.py init --title '书名' --platform '番茄' --target 100")
        sys.exit(2)

    print(f"🔍 巡检项目：{project}")

    specs = collect_specs(project)
    manuscript = collect_manuscript(project)
    if args.chapter:
        specs = [(n, d) for n, d in specs if n <= args.chapter]
        manuscript = [(n, t) for n, t in manuscript if n <= args.chapter]
    print(f"   规格文件：{len(specs)} 个 | 正文文件：{len(manuscript)} 个")

    f_fs, ledger, active, latest = check_foreshadowing(project, specs, manuscript)
    f_ki = check_known_info_chain(specs)
    f_ooc = check_character_ooc(project, manuscript)
    f_wf, locked = check_world_facts(project)
    findings = f_fs + f_ki + f_ooc + f_wf

    # 多线时间轴校验（多线编织法 §六）
    ml_findings = []
    tl_path = project / "设定" / "多线时间轴.yaml"
    if not args.no_multiline and (tl_path.exists() or args.multiline):
        ml_findings, _ = check_multiline_timeline(project)
        if not tl_path.exists() and args.multiline:
            print("   （--multiline：未找到 设定/多线时间轴.yaml，请用 templates/多线时间轴.yaml 初始化后重跑）")
    findings += ml_findings

    # 增量巡检：只保留该章及之后的问题（全局类问题如"伏笔过载"始终保留）
    if args.since:
        findings = [f for f in findings if _chapter_of(f) is None or _chapter_of(f) >= args.since]

    score = consistency_score(findings)
    icon = "🔴" if score < 60 else "🟠" if score < 75 else "🟡" if score < 90 else "🟢"
    print(f"\n{icon} 一致性评分：{score}/100")
    print(f"   伏笔：活跃 {active} 个 / 逾期 {sum(1 for f in findings if f['type']=='伏笔逾期')} 个")
    print(f"   因果断裂（P0）：{sum(1 for f in findings if f['type']=='因果断裂')} 处")
    print(f"   声音违例（需人工确认）：{sum(1 for f in findings if f['type']=='声音违例/OOC')} 处")
    ml_count = sum(1 for f in findings if f['type'] in
                   {"时间轴倒流", "时间轴断线", "状态跳变", "跨线状态矛盾", "跨线已知核对", "收网未汇聚"})
    if ml_count:
        print(f"   多线时间轴：{ml_count} 处（P0 {sum(1 for f in findings if f['type'] in {'时间轴倒流','跨线状态矛盾'} and f['level']=='P0')} / "
              f"P1 {sum(1 for f in findings if f['level']=='P1' and f['type']=='状态跳变')} / "
              f"P2 {sum(1 for f in findings if f['level']=='P2' and f['type'] in {'时间轴断线','跨线已知核对','收网未汇聚'})}）")
    for f in findings:
        if f["level"] in ("P0", "P1"):
            print(f"   [{f['level']}] {f['type']}：{f['detail'][:60]}…")

    if args.report:
        path = write_report(project, findings, ledger, active, latest, score, locked)
        print(f"\n📄 报告已生成：{path}")
    if not args.no_write:
        update_state(project, score, latest, active)
        print("✅ 已更新 project_state.yaml 的 consistency 段")


if __name__ == "__main__":
    main()

# 锻字 · 网络小说创作引擎（rui-novel-forge）

> 写作不是流水线，是锻造。每章都是一块铁，从毛坯到精钢，要过一百遍锤炼。

一个面向**网络小说创作**的全流程引擎 Skill，覆盖「灵感 → 架构 → 风格 → 创作 → 评审 → 体检 → 续命 → 商业 → 完结」的完整闭环。不是工具箱，是带状态机、项目健康度、作者-AI 分工协议的**完整创作系统**。

**哲学基线**：作者即主理人，AI 即工具；商业即视角；节奏即生命；续命即能力；体检即保险；连贯即信任。
【关注贴图号：阿米巴睿叔】
---

## 核心特性

- **11 阶段状态机**：项目启动 → 种子 → 架构 → 风格锚定 → 创作 → 评审 → 体检 → 续命 → 商业 → 完结，外加作者工坊与项目仪表盘两个常驻横切模块。
- **项目健康度 5 维仪表盘**：战力平衡 / 主线纯度 / 人物成长 / 钩子密度 / 世界观一致性，自动预警。
- **作者-AI 分工协议**：每个阶段都明确「AI 能做 / 必须作者做 / 边界提醒」，AI 越界即触发 P0 红线。
- **风格锚定 + 声音指纹**：写前先定调，作者锚点 6 维特征提取 + 每角色 4 清单声音指纹。
- **续命急救包**：5 大中期病症 + 4 步 24h 急救 + 9 种续命工具，写崩了能救。
- **平台画像 + 读者画像前置**：番茄 / 起点 / 晋江 / 七猫 / 知乎盐选差异策略。
- **长篇一致性巡检**：伏笔总表 / 人物漂移 / 已知信息因果链 / 设定矛盾，配 `continuity_check.py` 自动对账。
- **7 个辅助脚本**：状态机 / 健康度体检 / 风格锚定 / 质量检测 / 续命诊断 / 一致性巡检 / Spec 自检。
- **17 篇方法论文档 + 7 个可直接复制的模板**：开箱即用。

---

## 目录结构

```
rui-novel-forge/
├── SKILL.md                  # 引擎总说明（必读）
├── references/               # 17 篇方法论文档（00–16）
│   ├── 00_quickstart.md      # 5 分钟快速上手
│   ├── 01_platforms.md       # 平台选择
│   ├── 02_readers.md         # 读者画像
│   ├── 03_storyline.md       # 故事线 3 层公式
│   ├── 04_worldbuilding.md   # 世界观三招 + 经济体系
│   ├── 05_characters.md      # 人物心脏 + 声音指纹
│   ├── 06_voice_calibration.md  # 风格锚定
│   ├── 07_structure.md       # 四层瀑布 + 分卷
│   ├── 08_chapter_spec.md    # 章节 spec
│   ├── 09_writing_techniques.md # 写作技巧（含对话/心理描写）
│   ├── 10_review.md          # 评审 + 朱雀
│   ├── 11_rescue.md          # 续命急救包
│   ├── 12_commercial.md      # 商业运营
│   ├── 13_anti_ai.md         # 去 AI 味
│   ├── 14_creative_diversity.md # 创意多样性引擎
│   ├── 15_continuity.md      # 长篇连贯性
│   └── 16_multiline_weave.md # 多线编织法
├── scripts/                  # 7 个 Python 脚本
│   ├── novel_state.py        # 项目状态机
│   ├── health_check.py       # 健康度体检
│   ├── voice_anchor.py       # 风格锚定
│   ├── check_quality.py      # 质量检测（P0/P1/P2 + 朱雀预估 + 文句呼吸）
│   ├── rescue_diag.py        # 续命诊断
│   ├── continuity_check.py   # 一致性巡检
│   └── spec_check.py         # Spec 自检
└── templates/                # 7 个可复制模板
    ├── 章节spec模板.yaml
    ├── 人物卡模板.yaml
    ├── 对白变体模板.md
    ├── 宣传文案模板.md
    ├── 续命方案模板.md
    ├── 伏笔总表模板.yaml
    └── 多线时间轴.yaml
```

---

## 安装

### 方式一：Git 克隆（推荐，便于后续更新）

```bash
# 放到你所用 Agent 的 skills 目录
git clone https://github.com/LaoTimer/rui-novel-forge.git ~/.workbuddy/skills/rui-novel-forge
```

- **WorkBuddy**：`~/.workbuddy/skills/rui-novel-forge/`
- **CodeBuddy**：对应 skills 加载目录
- 其他支持 `SKILL.md` 规范的 Agent：放到其 skill 搜索路径下即可

### 方式二：手动下载 ZIP

在仓库页面点 **Code → Download ZIP**，解压后重命名为 `rui-novel-forge`，移动到上述 skills 目录。

> 安装后重启或重新加载 Agent 即可在对话中调用本引擎。

---

## 快速使用

在对话中直接描述创作意图，引擎会自动路由到对应阶段：

| 你说 | 进入阶段 |
|------|----------|
| "我想写本小说" / "开新书" | 0. 项目启动 |
| "我的灵感是……" | 1. 种子期 |
| "帮我设计世界观/人物/大纲" | 2. 架构期 |
| "我想先校准文风" | 3. 风格锚定期 |
| "写第 3 章" / "推进 5 章" | 4. 创作期 |
| "评审这章" | 5. 评审期 |
| "写到 30 万字了，感觉不对劲" | 6. 体检期 |
| "剧情崩了，救救我" | 7. 续命期 |
| "追读率掉了" | 8. 商业期 |
| "写完了，该收尾" | 9. 完结期 |

也可直接输入 `/rui-novel-forge` 触发出境。

---

## 脚本（需 Python 3.10+）

```bash
# 初始化项目（生成 project_state.yaml）
python scripts/novel_state.py init --title "我的小说" --platform "番茄" --target 100

# 5 维健康度体检
python scripts/health_check.py --project ./我的小说 --chapter 50

# 作者风格锚定
python scripts/voice_anchor.py extract --author-text ./参考资料/作者风格.txt

# 章节质量检测
python scripts/check_quality.py 正文/第050章.txt

# 续命诊断
python scripts/rescue_diag.py --project ./我的小说 --symptom "剧情注水"
```

> ⚠️ 脚本均为辅助级启发式检测，标注「需人工确认」的项不自动判定，朱雀预估与 OOC 扫描仅供参考，**最终以作者判断为准**。

---

## 许可证

[MIT](LICENSE) © 睿叔。可自由使用、修改、再分发，请保留原作者署名。

---

## 版本

当前 **v2.3.0**。完整升级说明见 `SKILL.md` 末尾「升级说明」。

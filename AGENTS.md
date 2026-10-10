# 即梦分镜师（Codex 适配版）

> 工作空间：任意 clone 到本地的仓库根（以 `AGENTS.md` 所在目录为准）。
> 本包是完整的制片人 + 六角色子代理调度流程；所有创造性生产都在子代理里完成，主会话只派活和回读摘要。
> Codex 启动时自动把本文件（AGENTS.md）加载为项目规则；角色子代理定义在 `.codex/agents/*.toml`，技能定义在 `.agents/skills/*/SKILL.md`。

[硬约束]
**以下规则为不可绕过的强制约束，任何对 `02-jimeng-prompts.md` 的修改都必须遵守：**
1. **改完必验**：每次对 `02-jimeng-prompts.md` 完成修改后，必须立即跑四道一键校验：`tools\py.cmd tools/run_all_checks.py <剧名> <epXX>`，全绿才能向用户报告完成；发现超时/禁写词/长度超标/编号异常/台词缺失改写或冗余，立即修正并重新验证。
2. **母镜头硬上限**：每个母镜头总时长 **4-15秒**，不得超出；超过 15 秒必须拆分。四道校验走 `tools\py.cmd tools/run_all_checks.py`。
   - **Seedance 2.5 / 30s 直出链：禁用**（链路技能口径错误、不可用，待修好再启用）。派遣时不得使用 30s 链技能；本项目分发包不携带 30s 链技能与脚本。
3. **修改前备份**：修改前先读取文件确认当前内容，避免覆盖已有修改。
4. **画面字段铁律 / 人物资产标准**：具体判定细则与执行顺序由「分镜师」「美术」子代理的 `developer_instructions` + 技能承载（见各自 toml）；主会话只负责派活与回读摘要。

[角色]
你是一名**制片人**，负责协调六个子代理完成即梦平台格式的分镜提示词生成工作：

| 子代理 | 中文名 | 技能归属 |
|--------|--------|----------|
| `script-handler` | 拆剧本专家 | `$jimeng-script-intake`（主）· `$jimeng-global-style-flow`（衔接）· `$jimeng-asset-report`（衔接，用户明确点名才动） |
| `dialogue-assistant` | 台词专家 | `$jimeng-dialogue-assistant` |
| `director` | 导演 | `$jimeng-director`（主） |
| `art-designer` | 美术 | `$jimeng-art-design`（主）· `$jimeng-character-assets`（人物资产建库）· `$jimeng-asset-report`（资产报告，用户明确点名才动） |
| `storyboard-artist` | 分镜师 | `$jimeng-panorama-blocking`（阶段四全景）· `$jimeng-storyboard`（阶段六核心） |
| `review` | 审核 | `$jimeng-review` |

[制片人调度规则]
**你（制片人）是调度者，不是执行者。** 所有创造性生产（导演分析、服化道设计、镜头设计、分镜填写）和审核比对必须**派遣子代理**在独立会话中完成，禁止在制片人主会话里直接执行这些环节——否则主会话上下文很快爆满。

**Codex 工具映射**

| 环节 | Codex 侧 | 用法 |
|------|---------|------|
| 派遣子代理 | 子代理工作流（subagents） | 直接说明「用 subagent 跑 X」「并行 3 个子代理做 A/B/C」；子代理跑在独立线程，只回摘要到主会话 |
| 角色选取 | `.codex/agents/*.toml` 自定义 agent | 按名派遣：`script-handler` / `dialogue-assistant` / `director` / `art-designer` / `storyboard-artist` / `review` |
| 加载技能 | 技能（skills） | 显式写 `$jimeng-storyboard`（或同族技能名）触发；也可由 `description` 隐式匹配。技能在 `.agents/skills/<name>/SKILL.md` |
| 跑脚本 | shell | 统一走 `tools\py.cmd`（见文末「运行环境注意」） |
| 文件读写 / 检索 | 文件工具 + shell | 单文件读写用文件工具，批量检索用 `rg` |
| 联网 / 看图 | web 搜索 / 图像查看 | 参考示例、角色参考图、视图截图复核 |
| 任务清单 | 计划工具 | 维护阶段进度 |

**调度分工**
| 环节 | 执行方 | 制片人主会话动作 |
|------|--------|-----------------|
| 阶段零前 剧本入库与拆集 | 派 `script-handler` 子代理 | 派活（拿到用户剧本路径 → 拆集 + 格式规范化 + 验证）→ 读一行摘要 |
| 阶段一 台词本生成 | 制片人直接跑脚本 | shell 运行 gen_dialogue_list.py |
| 阶段一 台词本核对 | 派 `dialogue-assistant` 子代理 | 读 PASS/FAIL 报告 → 判断 |
| 阶段二 导演分析 | 派 `director` 子代理 | 读剧本原文片段 → 派活 → 读一行摘要（无独立审核） |
| 阶段二末 预算自检 | 制片人直接跑脚本 | shell 运行 check_budget.py |
| 阶段三 服化道设计 | 派 `art-designer` 子代理 | 读讲戏本摘要 → 派活 → 读一行摘要（可用 check_assets_change.py 条件跳过） |
| 阶段四 全景站位 | 派 `storyboard-artist` 子代理 | 派活 → 读一行摘要（与阶段二可并行，仅纯复用集） |
| 阶段五 分镜要点卡 | 制片人直接跑脚本 | shell 运行 gen_episode_brief.py 生成 episode-brief.md（阶段六 输入） |
| 阶段六 分镜填写 | 派 `storyboard-artist` 子代理 | 派活 → 读一行摘要 |
| 阶段七 时长校验/修正/派生 | 制片人直接跑脚本 | calc_duration / apply_corrections / gen_clean / gen_html_view / gen_asset_list；**与阶段八 终审并行执行**（终审只依赖 02-jimeng-prompts.md + 四道脚本，不读派生文件） |
| 阶段八 终审 | 派审核子代理 | 读 PASS/FAIL + 问题清单 → 判断 |

**子代理派遣契约（每次派遣的说明里必须包含）**
0. **专属身份读取**：子代理在「<剧名>」项目下工作，开工前先读自己的身份记忆文件：
   - `.codex/memory/<剧名>-<role>.md`
   制片人负责把短别名映射到实际剧名（如 `<剧名>=重生1980，断亲后我把妻女宠上天`）。
   **失败保护**：读取身份文件失败 → 子代理立即 abort 并报告"身份读取失败，无法继续"。
1. **角色定位**：什么角色，执行什么阶段。
2. **输入文件**：绝对路径清单（剧本、台词本、讲戏本、资产、全景站位、config/global-style.md 等），要求先读取。
3. **技能加载**：指明加载哪个技能（如 `$jimeng-storyboard`），规范在 `.agents/skills/<name>/SKILL.md`（一律用完整版）。
4. **输出文件**：绝对路径，要求写入后确认。
5. **返回格式**：一行摘要（输出了哪些文件 + 校验是否通过 + 关键问题点），不返回文件全文。

要点：
- 子代理不依赖对话上下文，一切从文件读取；制片人派活时只给路径和任务说明，不给文件内容。
- 剧本原文只在三处读取：台词本生成时（脚本机械提取）、派导演前、分镜师填台词前（台词权威来源，由子代理自读）。
- 审核子代理返回 PASS/FAIL + 问题清单，制片人只读报告做最终判断，不读被审文件全文。
- 子代理 FAIL → 把审核报告回传给同一角色子代理重跑（context 附审核意见）；校验不通过 → 主会话改 corrections.json 重跑脚本。

- [项目路径]
Codex 项目根（`AGENTS.md` 所在目录；下面所有 `scripts/…`、`tools/…`、`.agents/…`、`.codex/…` 都相对项目根）。

- 本包只保留可运行流程、技能、模板和知识库；剧本与产出不上传。
- 目录改名或迁移后，可跑 `tools/_repoint_root.py` 重指历史路径。
- 子代理身份记忆目录 `.codex/memory/`：**新剧首次派活前**先跑 `tools\py.cmd tools\new_drama_memory.py "<剧名>"` 生成 `<剧名>-<role>.md` 六份，否则子代理会按契约 abort。
- 新剧首次派活前先跑 `tools\py.cmd tools\new_drama_memory.py "<剧名>"` 生成六份身份记忆，否则子代理会按契约 abort。

[技能清单]
技能放 `.agents/skills/<name>/SKILL.md`，Codex 自动发现（改完自动重扫，未生效则重启 Codex）；技能**按上面《[角色]》的技能归属表挂到各子代理**，不在主会话平铺调用。
- `jimeng-director`（导演分析，阶段二） · `jimeng-dialogue-assistant`（台词本核对，阶段一） · `jimeng-art-design`（服化道设计，阶段三）
- `jimeng-panorama-blocking`（全景站位，阶段四） · `jimeng-storyboard`（即梦分镜编写，阶段六，核心） · `jimeng-review`（终审，阶段八）
- `jimeng-html-view`（HTML 视图生成，阶段七，主会话直接跑脚本） · `jimeng-asset-report`（资产分析报告，美术衔接） · `jimeng-global-style-flow`（阶段零全局风格纪律，拆本/美术衔接）
- `jimeng-script-intake`（剧本入库，拆本主技能） · `jimeng-character-assets`（人物资产，美术衔接）
- **30s 链（`jimeng-director-30s` / `jimeng-storyboard-30s` / `jimeng-seedance-30s`）：禁用**（当前技能口径错误、待修复后重启；分发包不携带）
- 对应角色子代理（`.codex/agents/`）：`script-handler` / `dialogue-assistant` / `director` / `art-designer` / `storyboard-artist` / `review`
- **技能源 = 项目 `.agents/skills/`**；如需同步个人全局 `~/.agents/skills/`，跑 `python tools/install_global_skills.py`（--dry-run 可预演）。
- 校验脚本只有一份：`.agents/skills/jimeng-storyboard/scripts/`（随技能自包含）。**改校验器后必须在旧剧上跑一次回归对比**：`tools\py.cmd tools\run_all_checks.py "<剧名>" epXX`。

[文件结构]
```
<仓库根>/
├── AGENTS.md（本文件，Codex 自动加载为项目规则）
├── README.md / 工作台.html / 启动工作台.bat
├── .codex/
│   ├── config.toml                    # 项目级 Codex 配置（顶层键如 project_doc_max_bytes）
│   ├── agents/*.toml                  # 6 个角色子代理定义
│   └── memory/                        # 子代理身份记忆 <剧名>-<role>.md + _template/
├── .agents/skills/                    # 技能（SKILL.md 规范 + 校验/生成脚本 + 模板 + config）
├── tools/                             # 一键脚本与工具
│   ├── run_all_checks.py <剧名> <epXX> # 一键四道校验+预算自检（跨平台，首选）
│   ├── finish_ep.py     <剧名> <epXX> # 四道通过后一键生成派生文件（跨平台，首选）
│   ├── py.cmd / py.ps1                # Python 解释器转发（读 tools/python-path.txt）
│   └── *.sh                           # 同上的 bash 版（有 Git Bash / WSL 的环境可用）
├── scripts/[剧本名]/                  # 剧本仓库（script/assets/config/outputs）
└── knowledge/                         # 知识库（prompt-kb / video-prompt-kb / reusable-kb）
```

[工作流程]

### 阶段零前：剧本入库与拆集（新剧第一步）
1. 派 `script-handler` 子代理：入库（源稿原字节留档剧根）+ 拆集 + 标记类规范化（台词一字不改）+ 两级回环验证。
2. 主会话只做两件事：把用户给到的源稿位置交给它；读完一行摘要（输出文件 + 台词条数/未命名场景数）再进阶段零。
3. 具体的拆集命令、双语稿分工、规范化规则、验证口径都由拆本子代理 toml + `jimeng-script-intake` 技能承载。

### 阶段零：全局风格与制片批注（首次使用任一副本时）
主会话专属（不派子代理）：检测 `config/global-style.md` 是否存在 → 不存在就给用户 **A-D 四个选项**，**等用户敲定**才写入 config；已存在直接读取复用。文件骨架见 `.agents/skills/jimeng-global-style-flow/templates/global-style-template.md`。写入内容包括两部分：
1. **成片文案**：固定头 + 光线从句（+ 特殊剧的角色/文学强化子句）——分镜视觉基准；
2. **制片批注**（主 agent 通读剧本后生成并维护，不派子代理）：核心卖点 / 故事主线 / 故事梗概 / 故事人物 / 制作特别要求（节奏把控 + 主角人设锚点）——成稿先给用户预览，确认后与成片文案一并落盘。

纪律：一次最多 4 个选项、不代用户定稿；绘内向文字类规则（海外剧英文入画/面孔铁律）须写入 config 与分镜成片文案两处。

定稿落盘后（含后续批注修改落盘后），主会话跑
`tools\py.cmd .agents\skills\jimeng-html-view\scripts\gen_global_style_html.py "scripts/<剧名>/config/global-style.md"`
生成工作台同风格视图 `config/global-style-view.html`。

### 阶段零点五：资产预建（新剧首集前，全剧一次性建库）
派 `art-designer` 子代理建全库，主会话只做三件事：
1. 制片人先出「角色外观分配表」`assets/_face-allocation.md`（角色名 + 本剧外观要点，默认不分配识别锚点，只标出「需识别」的角色及其剧本依据），不先出分配表就并行派活必然撞脸。
2. 读完一行摘要（改了哪些文件 + 新增/复用条目数 + 校验结果），确认场景/道具库非空——严禁在场景/道具库为空时让 `check_assets_change.py` 判 SKIP 蒙混过关。
3. 用户明确要「生成/做资产报告」时，主会话直接跑 `tools\py.cmd tools\gen_asset_report.py "<剧名>"`，之后 `node tools/check_asset_report.js <四份 report.html>` + 无头 Chrome 截图复检。
4. 提示词以 `assets/{character,scene,prop}-prompts.md` 为唯一源：四联报告为每条角色/场景/道具**预留提示词槽位**，库建好后重跑 `gen_asset_report.py` 自动填充到人物/场景/道具分析报告；不再生成或使用旧资产 HTML 视图。
人物/场景清点、并行分批合并等执行细节全部走美术 toml + `jimeng-art-design` / `jimeng-character-assets` / `jimeng-asset-report` 技能；人物提示词按 2026-10-09 统一六段格式执行。

### 阶段一：台词本生成与核对
1. 制片人直接跑脚本生成台词本：`gen_dialogue_list.py scripts/<剧名>/script/epXX.txt`（本机统一走 `tools\py.cmd`）。
2. 派 `dialogue-assistant` 子代理逐字比对剧本原文和台词本，PASS 才进阶段二；台词本 PASS 后为阶段六唯一复用依据。
（细节：docx/双语稿入库、逐字一致性、画外音写法等核对面 → 台词子代理 toml + `$jimeng-dialogue-assistant`。）

### 阶段二：导演分析（v2 精简模式）
1. 派 `director` 子代理（说明含剧本路径 + 台词本 + global-style + 输出路径），读回一行摘要；产物 `01-director-analysis.md`。
2. 无独立审核（拆点合理性阶段八兜底），主会话末尾跑一次 `check_budget.py` 预算自检即可。

### 阶段三：服化道设计（可条件跳过）
1. 主会话跑 `check_assets_change.py` 决定是否派美术（0=SKIP，1=NEEDED）。
2. NEEDED 时派 `art-designer` 补人物/道具/场景提示词到 `assets/{character,prop,scene}-prompts.md`，再派 review 子代理审核，FAIL 回传重跑。

### 阶段四：全景站位分镜
1. 派 `storyboard-artist` 子代理产出 `epXX-asset-list.md` + `00-panorama-blocking.md`（单一母镜头 ≤15s、零台词零心理、时间轴，@引用名以资产清单为唯一权威）。
2. 阶段二可比并行（仅纯复用集，一次派遣多个 subagent）；新增资产集必须串行。

### 阶段五：分镜要点卡（制片人跑脚本）
1. 主会话跑 `gen_episode_brief.py --ep-dir …` 生成 `episode-brief.md`，阶段六分镜子代理读取它加速定位（剧本原文仍为台词字面唯一权威）。

### 阶段六：分镜编写（镜头设计内联 + 7 字段）
1. 派 `storyboard-artist` 子代理按剧情点 1:1 映射母镜头、填 7 字段，输出 `02-jimeng-prompts.md`；可附上一集分镜作风格参考。
2. 具体铁律（台词逐字 + 时长锁定 + 4-15s + 反应镜头禁 0.5s）在分镜师 toml + `jimeng-storyboard` 技能，主会话不再重复。

### 阶段七：时长校准 + 派生文件（配置驱动，制片人跑脚本）
1. 一键入口：`tools\py.cmd tools\finish_ep.py <剧名> <epXX>`（校验+派生一体；有 Git Bash 时等价 `bash tools/finish_ep.sh`）。
2. 硬错误时走 `corrections.json` + `apply_corrections.py`，重跑校验硬错误=0 才继续；严禁手动编辑分镜文件。

### 阶段八：终审（合并常规审核，一集完成唯一判定）
1. 派 `review` 子代理执行全量终审，输出 `03-final-review.md`。
2. 完成判定 = 四道全绿 AND 无「必须修复」级问题 → PASS，进入下一集（跳过阶段零）。
3. FAIL → 脚本问题回主会话走 `corrections.json`；其余问题回传分镜子代理重跑。

[脚本速查（统一走 `tools\py.cmd <脚本> [参数...]`）]
| 环节 | 脚本 | 产出 |
|------|------|------|
| 阶段一 台词本 | `.agents/skills/jimeng-storyboard/scripts/gen_dialogue_list.py` | `epXX-dialogue-list.md` |
| 阶段零 档案视图 | `.agents/skills/jimeng-html-view/scripts/gen_global_style_html.py` | `config/global-style-view.html` |
| 阶段二末 预算自检 | 同上 `check_budget.py` | 讲戏本 Parse + 台词秒数核对 |
| 阶段三 跳过决策 | 同上 `check_assets_change.py` | 0=SKIP / 1=NEEDED |
| 阶段五 要点卡 | 同上 `gen_episode_brief.py` | `episode-brief.md` |
| 阶段七 一键校验+派生 | `tools/finish_ep.py` | clean.txt / view.html / xlsx / sub-durations.json |
| 阶段七 修正 | 同上 `calc_duration.py` + `apply_corrections.py` | 硬错误=0 后才派生 |
| 终审四道 | `tools/run_all_checks.py` | 时长 / 画面字段 / 台词对照 / 编号 |
| 阶段零点五 资产 | `tools/gen_character_inventory.py` + `gen_scene_inventory.py`（清点） / `tools/gen_asset_report.py`（资产报告，自动预留/填充提示词槽位） / `tools/check_asset_report.js`（复检） |
| 30s 链 | **禁用**：技能与脚本不随分发包携带，不新增不派遣 |
| 接新剧 | `tools/new_drama_memory.py "<剧名>"`（6 份身份记忆）/ `tools/docx_script_import.py / split_script_episodes.py`（拆本轮到拆本子代理） / `tools/_repoint_root.py` | 剧本仓库骨架 + 身份文件 |
| 技能同步 | `tools/install_global_skills.py` | 项目/个人全局（可选） |
| 路径重指 | `tools/_repoint_root.py` | 可选；目录改名/迁移后使用 |

[输出文件]
| Agent | 输出路径 |
|-------|---------|
| 本集资产清单 | scripts/[剧本名]/outputs/epXX/epXX-asset-list.md |
| 全景站位分镜 | scripts/[剧本名]/outputs/epXX/00-panorama-blocking.md |
| 导演讲戏 | scripts/[剧本名]/outputs/epXX/01-director-analysis.md |
| 台词本 | scripts/[剧本名]/outputs/epXX/epXX-dialogue-list.md |
| 即梦分镜（含格式） | scripts/[剧本名]/outputs/epXX/02-jimeng-prompts.md |
| 即梦分镜（纯文本） | scripts/[剧本名]/outputs/epXX/02-jimeng-prompts-clean.txt |
| 即梦分镜（HTML 视图） | scripts/[剧本名]/outputs/epXX/02-jimeng-prompts-view.html |
| 素材清单表（Excel） | scripts/[剧本名]/outputs/epXX/[剧本名]_epXX_素材清单表.xlsx |
| 终审报告 | scripts/[剧本名]/outputs/epXX/03-final-review.md |
| 资产提示词库（分镜引用唯一权威） | scripts/[剧本名]/assets/{character,scene,prop}-prompts.md |
| 全局风格配置 + 制片批注 | scripts/[剧本名]/config/global-style.md |
| 全局风格视图（工作台同风格） | scripts/[剧本名]/config/global-style-view.html |

[运行环境注意]
- **所有 Python 调用统一走 `tools\py.cmd`**（解释器路径写在 `tools/python-path.txt`；本机 PATH 上没有可用 python）。四道脚本已自动 UTF-8 输出。
- **Codex 下用 Python 版入口**：`tools/run_all_checks.py` / `tools/finish_ep.py`；`tools/*.sh` 只在有 Git Bash / WSL 的机器可用。
- 校验器/拆集规则的坑（导演时长行格式、check_dialogue 兼容性、场景行格式等）是子代理/脚本的执行细节，执行层（导演、拆本、台词、分镜）各自的 toml/技能里承载；主会话只在出现问题时派对应子代理排查。
- **新建工作文件夹清单（复制本目录时的最小步骤）**：① 整目录复制；② 跑 `tools\py.cmd tools/_repoint_root.py` 重指路径；③ 重写 `tools/python-path.txt`；④ 每部在跑的剧跑 `tools\py.cmd tools/new_drama_memory.py "<剧名>"` 建 `.codex/memory/<剧名>-<role>.md` 六份；⑤ 跑一次 `tools\py.cmd tools/run_all_checks.py "<剧名>" epXX` 验证工具链。

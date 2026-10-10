# 子代理身份/记忆模板

规则依据：`AGENTS.md` →「子代理派遣契约」第 0 条——**每个子代理被派遣前必须先读自己的身份文件**
`.codex/memory/<剧名>-<role>.md`，读取失败即 abort 并报告「身份读取失败，无法继续」。

## 用法

新剧首次派活前，在项目根跑：

```bash
python tools/new_drama_memory.py "<剧名>"
```

会按本目录模板生成 6 份身份文件（已存在的不覆盖）：

| 模板 | 生成文件后缀 | 对应角色 | 对应技能 |
|------|--------------|----------|----------|
| director.md | `-director.md` | 导演分析（阶段二） | `jimeng-director` |
| art-designer.md | `-art-designer.md` | 服化道设计（阶段三） | `jimeng-art-design` |
| dialogue-assistant.md | `-dialogue-assistant.md` | 台词助理（阶段一核对） | `jimeng-dialogue-assistant` |
| storyboard-artist.md | `-storyboard-artist.md` | 即梦分镜师（阶段四全景 / 阶段六分镜） | `jimeng-panorama-blocking` / `jimeng-storyboard` |
| review.md | `-review.md` | 审核员（阶段八终审 / 阶段三审核） | `jimeng-review` |

## 维护纪律

- 模板里的 `{{剧名}}` / `{{日期}}` 由脚本替换，**不要在模板中写死具体剧目**。
- 子代理每次任务完成后，只在自己那份记忆文件的「经验总结 / 本次工作记录」两节追加（每条 ≤3 行、可复用），禁止改动其他角色文件。
- 全项目通用的铁律写进 `AGENTS.md`，不要写进身份文件；身份文件只放"本剧沉淀"。

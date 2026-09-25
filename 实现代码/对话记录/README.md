# LearnBuddy 对话记录（交付素材）

本目录是**真实**平台会话导出的记录（不是模拟）：在 LearnBuddy 内以一次性自动化任务绑定本作品专家
`research-retro-assistant` 执行，逐条处理 27 条评测用例；记录含专家调用确定性引擎（CLI）的原文、
自检与负对照过程。

> **开源仓库说明**：为控制仓库体积，`*.jsonl` 原件（5 份，合计约 4.6 MB）**不进本仓库**，
> 随赛事提交材料（源码压缩包）一并提供；下表即其清单。结论摘录可先看 `reports/eval-real-sessions.md`。

| 文件 | 覆盖用例 |
| --- | --- |
| real-session-3.jsonl | 15 / 21 / 18 |
| real-session-2642.jsonl | 16 / 19 / 22 / 25 + 盲测 7 / 24 |
| real-session-3624.jsonl | 2 / 11 + 盲测 13 / 17 / 20 / 23 |
| real-session-4633.jsonl | 1 / 3 / 4 + 盲测 5 / 10 / 14 |
| real-session-56.jsonl | 6 / 8 / 9 / 12 / 26 / 27 |

**复核方式**：jsonl 每行一个事件对象；结论汇总另见 `reports/eval-real-sessions.md`。
**说明**：平台把会话原文写在本机 `~/.learnbuddy/projects/<cwd-slug>/<conversationId>.jsonl`，
此处为原样副本；为控制体积，也可只看 `reports/eval-real-sessions.md` 里的结论摘录。

## 脱敏说明（2026-09-24）

记录里专家调用本机解释器/引擎时出现的绝对路径，已统一替换为 `%USERPROFILE%`（例如
`%USERPROFILE%\...\python.exe`）。**除路径前缀外，记录内容未作任何改动**；会话 id、命令原文、
输出内容、判定与结论均为原样。如需完全原始版本，见本机 `~/.learnbuddy/projects/<cwd-slug>/<conversationId>.jsonl`。

# data/ 数据目录（唯一真源）

| 文件 | 用途 | 是否入库 |
| --- | --- | --- |
| `data/library.seed.json` | 种子数据：12–15 条模拟档案，含「死实验复活」所需的伏笔。由 `rra.seed.generator` 产出 | 是 |
| `data/library.local.json` | 本地调试库，随时可丢 | 否（已在 .gitignore） |

## 与 web/data/ 的关系

- `data/` 是**唯一真源**：所有编辑、校验、评测都以这里的文件为准。
- `web/data/library.sample.json` 是**静态站点启动时读到的那一份**，由 `tools/validate_library.py` 从 `data/` 同步过去。
- 两份文件不是同一个东西，改了种子数据必须重新同步，否则网页看到的还是旧的。

## 禁止

- 不得把真实实验记录直接放进本目录再标成「模拟」。
- 不得在种子数据里混入未脱敏的个人信息。

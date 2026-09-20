# tools/ 一次性与运维脚本

与 `src/rra/` 的分工：`src/rra/` 是可被复用的库代码；`tools/` 是**命令行入口**，只做参数解析与调用，不放业务逻辑。

| 脚本 | 用途 | 产物 |
| --- | --- | --- |
| `make_seed.py` | 生成种子数据 | `data/library.seed.json` |
| `validate_library.py` | 校验库文件并把样例同步给网页 | 校验报告 + `web/data/library.sample.json` |
| `run_eval.py` | 跑用例并生成记录表 | `reports/eval-results/*.json`、`reports/eval-log.md` |

## 约定

- 脚本必须先校验输入再写盘：校验不通过就退出，不产生半成品文件。
- 任何脚本都不得调用第三方模型。AI 判断只在平台侧发生。

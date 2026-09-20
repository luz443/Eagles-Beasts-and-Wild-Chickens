# 尝试记录格式（Record Format v0.1）

对外可移植的字段规范，供其他课题组复用。稳定编号为 `R-###`，引用格式为 `R-013@v2（课题组，2026-08）`。

## 必填字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | `R-\d{3}`，库内唯一 |
| `attempt` | string | 试了什么方法 |
| `expectation` | string | 目标是什么 |
| `observation` | string | 实际结果 |
| `blocker` | string | 卡在哪一步，具体到组件或参数 |
| `attribution` | object | `{ "text": string, "type": "assumption" | "observed" }` |
| `missing_info` | string[] | 判断所需但记录中缺失的字段 |
| `boundary` | string | 该结论在什么条件下成立 |
| `confidence` | enum | `high` / `medium` / `low` |
| `status` | enum | `进行中` / `已放弃` / `已绕过` / `已解决` |
| `provenance` | object | 提出人、时间、来源（真实 / 模拟） |
| `version` | integer | 档案版本，默认 1，用于引用格式 `R-013@v2` |

## 关联字段

| 字段 | 说明 |
| --- | --- |
| `conditions`（可选） | 九个条件维度到非空字符串取值的对象；历史档案缺失时不推断 |
| `links[]` | `{ target, relation: 重复/相似/冲突, same[], diff[], transferable }` |
| `same[]` | `{ "dim": <维度枚举>, "value": string }` |
| `diff[]` | `{ "dim": <维度枚举>, "from": string, "to": string }` |
| `evidence_refs[]` | `{ "record": "R-008", "quote": string }`——引用必须带原文片段 |
| `artifacts[]` | `{ "kind": "code" | "data" | "log", "ref": string }` |
| `dedup_key` | 归一化「尝试 + 阻塞点 + 关键条件」的指纹，用于导入去重 |

## 维度枚举（`dim`）

`model` 模型 / `seq_len` 序列长度 / `batch` 批大小 / `micro_batch` 微批 / `precision` 精度 /
`hardware` 硬件 / `dataset_version` 数据版本 / `stage` 阶段 / `framework` 框架。

`dim` 必须取自枚举，**不得写入自由文本**——网页的条件对比矩阵靠它对位。

`conditions` 的键只能是上述九个维度，值必须是非空字符串。允许只提供已知维度；空对象与缺失字段等价，序列化时省略。多场景结果使用一个准确描述场景的字符串，例如 `512（稳定） / 2048（OOM）`，不要把它压成单一标量。

## 派生指标不入档案

「被关联次数」由 `links[].target` 在前端统计得出，是派生值，**不写进档案文件**——
避免出现两份真源、以及导入合并后计数失真。

## 三条禁止

1. 无编号的「以前有人做过」不允许出现。
2. 日志未给出原因时，`attribution.type` 只能是 `assumption`。
3. 不得用失败次数给探索方向下判决。

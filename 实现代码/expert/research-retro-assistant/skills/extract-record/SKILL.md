# 技能 1：抽取建档（extract-record）

## 用途

把一段**原始实验记录**（日志、周报片段、聊天里的实验描述）抽成一条**符合契约的结构化档案**。

## 什么时候用

用户贴来一段日志/失败描述，要求「记下来」「变成档案」「整理成条目」时。

## 输入

- 必填：日志原文（`raw_text`）。
- 可选：库文件（用于第 4 步查号与查重）。

## 步骤

1. **读原文，只提取事实**：期望（expectation）、观察（observation）、阻塞点（blocker）必须能在原文里找到出处；
   原文没写的，不要替用户补。
2. **归因**：`attribution.type` 只有 `observed`（原文明确写了原因）与 `assumption`（你的推测）两个值。
   原文只描述现象时必然是 `assumption`，且 `attribution.text` 要用「怀疑 / 可能」的口径。
3. **边界必填**：`boundary` 必须非空，写清「这个结论在什么条件下成立」
   （硬件、精度、阶段、数据集版本等）；写不出边界说明这条记录还不成立，写进 `missing_info`。
4. **给编号**（确定性，别自己算）：

```bash
python3 bin/rra_cli.py next-id <库文件>
```

5. **查重**（确定性）：

```bash
python3 bin/rra_cli.py dedup-check <库文件> <候选档案.json>
```

   若 `duplicate=true`，不要新建——把 `match_ids` 告知用户，问是否补充已有档案。

6. **自检**：写出候选档案后先校验，不合规就改到自己过为止：

```bash
python3 bin/rra_cli.py validate-record <候选档案.json>
```

## 输出

- 一条档案 JSON（字段以 `references/record.schema.json` 为准）。
- 一段中文说明：这条记录说了什么、哪句话是依据、还缺什么。
- **id 留到第 4 步由 CLI 给定**，不要自己编。

## 拒绝条件（必须照做）

- 原文里找不到「观察」或「阻塞点」→ 拒绝建档，说明缺什么，请用户补原文。
- 只能给出主观评价（如「效果不好」）而没有可引用的观察 → 拒绝，给出需要补充的具体项。
- 不许把 `assumption` 写成 `observed`；不许编造 `evidence_refs`。

## 参考

- `references/prompt.md`（抽取提示词）
- `references/record-format.md`（字段口径与写法）
- `references/record.schema.json`、`references/dim.json`（契约与九维枚举）

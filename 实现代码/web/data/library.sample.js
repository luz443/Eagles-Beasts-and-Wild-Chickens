export const SAMPLE_LIBRARY = {
  "version": "0.1.0",
  "generated_at": "2026-09-19",
  "records": [
    {
      "id": "R-001",
      "attempt": "直接用 batch=32 跑 seq_len=2048 的微调",
      "expectation": "一晚跑完 3 个 epoch",
      "observation": "第 40 step 触发 CUDA OOM",
      "blocker": "长序列训练显存不足",
      "attribution": {
        "text": "怀疑 batch=32 在 seq_len=2048 下激活值超出 24G",
        "type": "assumption"
      },
      "missing_info": [
        "micro-batch 实际值",
        "是否启用 flash-attention"
      ],
      "boundary": "单卡 RTX 4090（24G）、bf16、未开梯度检查点",
      "confidence": "low",
      "status": "进行中",
      "artifacts": [
        {
          "kind": "log",
          "ref": "runs/0714-oom.log"
        }
      ],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-07-14",
        "source": "模拟"
      },
      "conditions": {
        "seq_len": "2048",
        "batch": "32",
        "hardware": "RTX 4090（24G）",
        "precision": "bf16",
        "stage": "微调"
      }
    },
    {
      "id": "R-002",
      "attempt": "把 batch 降到 4、seq_len 降到 512 先验证流程",
      "expectation": "先跑通小规模再放大",
      "observation": "512 下稳定，放大回 2048 又 OOM",
      "blocker": "长序列训练显存不足",
      "attribution": {
        "text": "怀疑序列长度回到 2048 后注意力开销随长度平方增长（未做分解实验验证）",
        "type": "assumption"
      },
      "missing_info": [
        "4096 是否完全不可行"
      ],
      "boundary": "同 R-001 硬件；seq_len=512 稳定 / 2048 不足",
      "confidence": "medium",
      "status": "进行中",
      "artifacts": [
        {
          "kind": "log",
          "ref": "runs/0718-seqlen.log"
        }
      ],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-07-18",
        "source": "模拟"
      },
      "conditions": {
        "seq_len": "512（稳定） / 2048（OOM）",
        "batch": "4",
        "hardware": "RTX 4090（24G）"
      }
    },
    {
      "id": "R-003",
      "attempt": "开启 gradient checkpointing 换显存",
      "expectation": "用时间换空间，2048 能过",
      "observation": "显存降到 19G，单步耗时约 2.4 倍，能跑但极慢",
      "blocker": "长序列训练显存不足",
      "attribution": {
        "text": "checkpointing 重算激活，显存换时间",
        "type": "observed"
      },
      "missing_info": [],
      "boundary": "单卡 4090；速度损失换显存余量",
      "confidence": "high",
      "status": "已绕过",
      "artifacts": [
        {
          "kind": "code",
          "ref": "train.py@v5"
        },
        {
          "kind": "log",
          "ref": "runs/0721-ckpt.log"
        }
      ],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·王同学",
        "date": "2026-07-21",
        "source": "模拟"
      },
      "conditions": {
        "seq_len": "2048",
        "hardware": "RTX 4090"
      }
    },
    {
      "id": "R-004",
      "attempt": "micro-batch=4 + 梯度累积 8 步补回等效 batch=32",
      "expectation": "等效 batch 不变，显存可控",
      "observation": "显存稳定在 21G，训练完成，loss 曲线与 batch=32 基本重合",
      "blocker": "无（此条为已解决的成功经验）",
      "attribution": {
        "text": "梯度累积可补回优化意义上的等效 batch",
        "type": "observed"
      },
      "missing_info": [],
      "boundary": "seq_len=512、Llama-3-8B、bf16；优化语义等价，吞吐下降约 15%",
      "confidence": "high",
      "status": "已解决",
      "artifacts": [
        {
          "kind": "code",
          "ref": "train.py@v7"
        }
      ],
      "links": [],
      "evidence_refs": [
        {
          "record": "R-002",
          "quote": "512 下稳定，放大回 2048 又 OOM"
        }
      ],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-07-25",
        "source": "模拟"
      },
      "conditions": {
        "seq_len": "512",
        "model": "Llama-3-8B",
        "precision": "bf16",
        "micro_batch": "4",
        "batch": "32（等效）"
      }
    },
    {
      "id": "R-005",
      "attempt": "沿用 R-004 的累积配置直接跑 seq_len=4096",
      "expectation": "4096 也能用同样配置跑通",
      "observation": "仍然 OOM；累积并不能降低单步激活峰值",
      "blocker": "长序列训练显存不足",
      "attribution": {
        "text": "梯度累积不减少单步激活显存，对激活主导的 OOM 无效",
        "type": "observed"
      },
      "missing_info": [
        "4096 下 flash-attention 是否开启"
      ],
      "boundary": "seq_len=4096 时该结论成立；512 时 R-004 已证明有效",
      "confidence": "medium",
      "status": "进行中",
      "artifacts": [],
      "links": [
        {
          "target": "R-004",
          "relation": "相似",
          "same": [
            {
              "dim": "model",
              "value": "Llama-3-8B"
            }
          ],
          "diff": [
            {
              "dim": "seq_len",
              "from": "512",
              "to": "4096"
            }
          ],
          "transferable": "R-004 的做法只对激活主导的显存压力有效，对注意力矩阵开销无效"
        }
      ],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·王同学",
        "date": "2026-08-02",
        "source": "模拟"
      },
      "conditions": {
        "seq_len": "4096",
        "model": "Llama-3-8B",
        "micro_batch": "4",
        "batch": "32（等效）"
      },
      "challenge": {
        "challenges": [
          {
            "text": "同一阻塞点已有 4 条记录，其中 3 条结论仍是假设，且都没有说明是否启用 flash-attention。请先给出本次与前几次在条件上的差异，再谈预期。",
            "evidence_ids": [
              "R-001",
              "R-002",
              "R-005"
            ]
          }
        ]
      }
    },
    {
      "id": "R-006",
      "attempt": "用 LoRA 对 70B 模型做 seq_len=8192 的长文本微调",
      "expectation": "省显存的同时完成长文本任务",
      "observation": "LoRA 部分显存可控，但基座权重 + 优化器状态仍超 24G，放弃",
      "blocker": "单卡放不下 70B 的权重与优化器状态",
      "attribution": {
        "text": "LoRA 只省激活与增量参数，不省基座权重",
        "type": "assumption"
      },
      "missing_info": [
        "int8 量化加载后是否放得下"
      ],
      "boundary": "单卡 24G；多卡或量化加载未测",
      "confidence": "low",
      "status": "已放弃",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-07-30",
        "source": "模拟"
      },
      "conditions": {
        "model": "70B（型号未提供）",
        "seq_len": "8192",
        "hardware": "单卡 24G",
        "stage": "LoRA 微调"
      }
    },
    {
      "id": "R-007",
      "attempt": "自实现 ring-attention 替代标准注意力",
      "expectation": "显存与序列长度解耦，跑超长文本",
      "observation": "两周实现后数值对齐困难（数值稳定性问题），暂放弃",
      "blocker": "ring-attention 的数值稳定性难以对齐",
      "attribution": {
        "text": "分块重排在 bf16 下累计误差",
        "type": "assumption"
      },
      "missing_info": [
        "官方实现是否存在可用版本"
      ],
      "boundary": "自实现版本；官方实现未测",
      "confidence": "low",
      "status": "已放弃",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·王同学",
        "date": "2026-08-10",
        "source": "模拟"
      },
      "conditions": {
        "precision": "bf16"
      }
    },
    {
      "id": "R-008",
      "attempt": "数据清洗脚本去重后训练",
      "expectation": "去重提升数据质量并提升评测分",
      "observation": "去重后训练集从 1.2M 降到 0.9M，评测分反而降 0.6",
      "blocker": "数据量下降的损失大于质量收益",
      "attribution": {
        "text": "该任务对数据多样性敏感，激进去重有害",
        "type": "assumption"
      },
      "missing_info": [],
      "boundary": "该数据集与配比下成立",
      "confidence": "low",
      "status": "已绕过",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·赵同学",
        "date": "2026-08-05",
        "source": "模拟"
      }
    },
    {
      "id": "R-009",
      "attempt": "学习率 3e-4 warmup 100 步",
      "expectation": "更大学习率加速收敛",
      "observation": "loss 在 300 步内发散",
      "blocker": "学习率过大导致发散",
      "attribution": {
        "text": "该规模模型对 3e-4 敏感",
        "type": "observed"
      },
      "missing_info": [],
      "boundary": "Llama-3-8B 全参微调；LoRA 下未测",
      "confidence": "medium",
      "status": "已解决",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·赵同学",
        "date": "2026-08-08",
        "source": "模拟"
      },
      "conditions": {
        "model": "Llama-3-8B",
        "stage": "全参微调"
      }
    },
    {
      "id": "R-010",
      "attempt": "用 vLLM 做推理加速评测",
      "expectation": "评测吞吐提升 3 倍以上",
      "observation": "吞吐约 2.2 倍，但长输入下 kv-cache 占用高，并发受限",
      "blocker": "长输入下 kv-cache 显存挤占并发",
      "attribution": {
        "text": "kv-cache 随序列长度线性增长",
        "type": "observed"
      },
      "missing_info": [],
      "boundary": "该模型与 24G 单卡",
      "confidence": "medium",
      "status": "已绕过",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·王同学",
        "date": "2026-08-15",
        "source": "模拟"
      },
      "conditions": {
        "hardware": "单卡 24G",
        "framework": "vLLM",
        "stage": "推理评测"
      }
    },
    {
      "id": "R-011",
      "attempt": "混合精度 fp16 训练",
      "expectation": "fp16 比 bf16 数值精度更高",
      "observation": "loss 出现 NaN",
      "blocker": "fp16 溢出导致 NaN",
      "attribution": {
        "text": "fp16 动态范围不足，大梯度溢出",
        "type": "observed"
      },
      "missing_info": [],
      "boundary": "该模型与学习率设置",
      "confidence": "high",
      "status": "已解决",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·赵同学",
        "date": "2026-08-18",
        "source": "模拟"
      },
      "conditions": {
        "precision": "fp16",
        "stage": "训练"
      }
    },
    {
      "id": "R-012",
      "attempt": "web qa 数据配比从 1:1 调到 1:3",
      "expectation": "偏向通用数据提升泛化",
      "observation": "领域评测降 1.2，通用评测升 0.3",
      "blocker": "领域与通用此消彼长",
      "attribution": {
        "text": "配比敏感点在 1:2 附近",
        "type": "assumption"
      },
      "missing_info": [],
      "boundary": "当前任务组合",
      "confidence": "low",
      "status": "进行中",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·赵同学",
        "date": "2026-08-20",
        "source": "模拟"
      }
    },
    {
      "id": "R-013",
      "attempt": "D 数据集 v2（修复了标注错位）直接替换 v1 训练",
      "expectation": "数据修复带来全面提升",
      "observation": "多数指标上升，但长文本摘要 Rouge-L 意外下降 0.8",
      "blocker": "数据版本变更引入回归",
      "attribution": {
        "text": "v2 修复改变了长文本样本分布",
        "type": "assumption"
      },
      "missing_info": [
        "v1/v2 长文本样本 diff"
      ],
      "boundary": "该任务与 v1/v2 差异",
      "confidence": "low",
      "status": "进行中",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-08-25",
        "source": "模拟"
      },
      "conditions": {
        "dataset_version": "D 数据集 v1 → v2",
        "stage": "训练"
      }
    },
    {
      "id": "R-014",
      "attempt": "试图复现某论文的 0.92 分结果",
      "expectation": "按论文配置应能接近",
      "observation": "最好 0.87，差 5 个点",
      "blocker": "论文关键细节未披露（数据划分与后处理）",
      "attribution": {
        "text": "复现差距来自未披露的后处理",
        "type": "assumption"
      },
      "missing_info": [
        "作者的后处理代码"
      ],
      "boundary": "论文公开配置",
      "confidence": "low",
      "status": "已放弃",
      "artifacts": [],
      "links": [],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·王同学",
        "date": "2026-09-01",
        "source": "模拟"
      }
    },
    {
      "id": "R-015",
      "attempt": "int8 量化加载 70B 基座 + 8-bit 优化器状态，再跑 LoRA 长文本",
      "expectation": "权重与优化器状态都压到 24G 单卡放得下，从而解掉 R-006 的阻塞点",
      "observation": "int8 加载后基座权重降到约 18G，8-bit 优化器状态约 3G，24G 单卡可启动；8192 序列下激活仍超限",
      "blocker": "量化加载后长序列激活值仍超 24G",
      "attribution": {
        "text": "权重与优化器已不再是瓶颈，瓶颈转移到长序列激活",
        "type": "observed"
      },
      "missing_info": [
        "8192 下叠加梯度检查点能否把激活压到 24G 以内"
      ],
      "boundary": "单卡 24G、int8 基座 + 8-bit 优化器；seq_len=8192 时激活仍超限",
      "confidence": "medium",
      "status": "进行中",
      "artifacts": [],
      "links": [
        {
          "target": "R-006",
          "relation": "相似",
          "same": [
            {
              "dim": "model",
              "value": "70B（型号未提供）"
            },
            {
              "dim": "seq_len",
              "value": "8192"
            }
          ],
          "diff": [
            {
              "dim": "precision",
              "from": "未量化",
              "to": "int8 基座 + 8-bit 优化器"
            }
          ],
          "transferable": "量化加载解掉了「权重与优化器放不下」这一层；对长序列激活开销无效（与 R-005 的结论方向一致）"
        }
      ],
      "evidence_refs": [],
      "dedup_key": "",
      "version": 1,
      "provenance": {
        "author": "模拟·李师兄",
        "date": "2026-09-05",
        "source": "模拟"
      },
      "conditions": {
        "model": "70B（型号未提供）",
        "seq_len": "8192",
        "precision": "int8 基座 + 8-bit 优化器",
        "hardware": "单卡 24G",
        "stage": "LoRA 微调"
      },
      "resurrection": {
        "unblocks": [
          {
            "record": "R-006",
            "basis": "R-015",
            "quote": "int8 加载后基座权重降到约 18G，8-bit 优化器状态约 3G，24G 单卡可启动"
          }
        ]
      }
    }
  ]
};

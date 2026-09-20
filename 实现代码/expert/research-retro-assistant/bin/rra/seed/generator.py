"""种子数据：12–15 条模拟记录。

硬约束（附录 D.6）：必须预留 1–2 条「已放弃且阻塞点明确」的记录，
否则死实验复活（S2）到演示时无法呈现。
"""

from dataclasses import dataclass, field

from ..contracts.dims import Dim
from ..contracts.models import (
    Archive, Artifact, Attribution, DimDelta, DimValue, EvidenceRef, Link, Provenance,
)


@dataclass
class SeedPlan:
    """造数据计划：方向、条数、阻塞点分布、必须埋的伏笔。"""

    total: int = 14
    abandoned_with_blocker: int = 2
    same_blocker_cluster: int = 3


# 三条叙事线：同一课题组三个月里的真实感
# A 线：长序列显存问题（3 条同阻塞点 → 失败地图与孵化清单的主材料）
# B 线：梯度累积有效性边界（2 条相似但条件不同 → 条件比较的演示材料）
# C 线：两次已放弃的尝试（死实验复活的伏笔）
# D 线：分散的独立记录（撑起库的真实感）
_SEEDS = [
    # ---- A 线：长序列显存不足（R-001/002/003，同阻塞点）----
    dict(
        id="R-001", attempt="直接用 batch=32 跑 seq_len=2048 的微调",
        expectation="一晚跑完 3 个 epoch",
        observation="第 40 step 触发 CUDA OOM",
        blocker="长序列训练显存不足",
        attribution=("怀疑 batch=32 在 seq_len=2048 下激活值超出 24G", "assumption"),
        boundary="单卡 RTX 4090（24G）、bf16、未开梯度检查点",
        conditions=dict(seq_len="2048", batch="32", hardware="RTX 4090（24G）", precision="bf16", stage="微调"),
        confidence="low", status="进行中",
        missing_info=["micro-batch 实际值", "是否启用 flash-attention"],
        artifacts=[("log", "runs/0714-oom.log")],
        author="模拟·李师兄", date="2026-07-14",
    ),
    dict(
        id="R-002", attempt="把 batch 降到 4、seq_len 降到 512 先验证流程",
        expectation="先跑通小规模再放大",
        observation="512 下稳定，放大回 2048 又 OOM",
        blocker="长序列训练显存不足",
        attribution=("怀疑序列长度回到 2048 后注意力开销随长度平方增长（未做分解实验验证）", "assumption"),
        boundary="同 R-001 硬件；seq_len=512 稳定 / 2048 不足",
        conditions=dict(seq_len="512（稳定） / 2048（OOM）", batch="4", hardware="RTX 4090（24G）"),
        confidence="medium", status="进行中",
        missing_info=["4096 是否完全不可行"],
        artifacts=[("log", "runs/0718-seqlen.log")],
        author="模拟·李师兄", date="2026-07-18",
    ),
    dict(
        id="R-003", attempt="开启 gradient checkpointing 换显存",
        expectation="用时间换空间，2048 能过",
        observation="显存降到 19G，单步耗时约 2.4 倍，能跑但极慢",
        blocker="长序列训练显存不足",
        attribution=("checkpointing 重算激活，显存换时间", "observed"),
        boundary="单卡 4090；速度损失换显存余量",
        conditions=dict(seq_len="2048", hardware="RTX 4090"),
        confidence="high", status="已绕过",
        artifacts=[("code", "train.py@v5"), ("log", "runs/0721-ckpt.log")],
        author="模拟·王同学", date="2026-07-21",
    ),
    # ---- B 线：梯度累积的边界（R-004/005，相似但条件不同）----
    dict(
        id="R-004", attempt="micro-batch=4 + 梯度累积 8 步补回等效 batch=32",
        expectation="等效 batch 不变，显存可控",
        observation="显存稳定在 21G，训练完成，loss 曲线与 batch=32 基本重合",
        blocker="无（此条为已解决的成功经验）",
        attribution=("梯度累积可补回优化意义上的等效 batch", "observed"),
        boundary="seq_len=512、Llama-3-8B、bf16；优化语义等价，吞吐下降约 15%",
        conditions=dict(seq_len="512", model="Llama-3-8B", precision="bf16", micro_batch="4", batch="32（等效）"),
        confidence="high", status="已解决",
        evidence=[("R-002", "512 下稳定，放大回 2048 又 OOM")],
        artifacts=[("code", "train.py@v7")],
        author="模拟·李师兄", date="2026-07-25",
    ),
    dict(
        id="R-005", attempt="沿用 R-004 的累积配置直接跑 seq_len=4096",
        expectation="4096 也能用同样配置跑通",
        observation="仍然 OOM；累积并不能降低单步激活峰值",
        blocker="长序列训练显存不足",
        attribution=("梯度累积不减少单步激活显存，对激活主导的 OOM 无效", "observed"),
        boundary="seq_len=4096 时该结论成立；512 时 R-004 已证明有效",
        conditions=dict(seq_len="4096", model="Llama-3-8B", micro_batch="4", batch="32（等效）"),
        confidence="medium", status="进行中",
        links=[dict(target="R-004", relation="相似",
                    same=[("model", "Llama-3-8B")],
                    diff=[("seq_len", "512", "4096")],
                    transferable="R-004 的做法只对激活主导的显存压力有效，对注意力矩阵开销无效")],
        missing_info=["4096 下 flash-attention 是否开启"],
        author="模拟·王同学", date="2026-08-02",
    ),
    # ---- C 线：已放弃的尝试（死实验复活的伏笔，R-006/007）----
    dict(
        id="R-006", attempt="用 LoRA 对 70B 模型做 seq_len=8192 的长文本微调",
        expectation="省显存的同时完成长文本任务",
        observation="LoRA 部分显存可控，但基座权重 + 优化器状态仍超 24G，放弃",
        blocker="单卡放不下 70B 的权重与优化器状态",
        attribution=("LoRA 只省激活与增量参数，不省基座权重", "assumption"),
        boundary="单卡 24G；多卡或量化加载未测",
        conditions=dict(model="70B（型号未提供）", seq_len="8192", hardware="单卡 24G", stage="LoRA 微调"),
        confidence="low", status="已放弃",
        missing_info=["int8 量化加载后是否放得下"],
        author="模拟·李师兄", date="2026-07-30",
    ),
    dict(
        id="R-007", attempt="自实现 ring-attention 替代标准注意力",
        expectation="显存与序列长度解耦，跑超长文本",
        observation="两周实现后数值对齐困难（数值稳定性问题），暂放弃",
        blocker="ring-attention 的数值稳定性难以对齐",
        attribution=("分块重排在 bf16 下累计误差", "assumption"),
        boundary="自实现版本；官方实现未测",
        conditions=dict(precision="bf16"),
        confidence="low", status="已放弃",
        missing_info=["官方实现是否存在可用版本"],
        author="模拟·王同学", date="2026-08-10",
    ),
    # ---- D 线：独立记录（撑真实感，覆盖不同场景）----
    dict(
        id="R-008", attempt="数据清洗脚本去重后训练",
        expectation="去重提升数据质量并提升评测分",
        observation="去重后训练集从 1.2M 降到 0.9M，评测分反而降 0.6",
        blocker="数据量下降的损失大于质量收益",
        attribution=("该任务对数据多样性敏感，激进去重有害", "assumption"),
        boundary="该数据集与配比下成立",
        confidence="low", status="已绕过",
        author="模拟·赵同学", date="2026-08-05",
    ),
    dict(
        id="R-009", attempt="学习率 3e-4 warmup 100 步",
        expectation="更大学习率加速收敛",
        observation="loss 在 300 步内发散",
        blocker="学习率过大导致发散",
        attribution=("该规模模型对 3e-4 敏感", "observed"),
        boundary="Llama-3-8B 全参微调；LoRA 下未测",
        conditions=dict(model="Llama-3-8B", stage="全参微调"),
        confidence="medium", status="已解决",
        author="模拟·赵同学", date="2026-08-08",
    ),
    dict(
        id="R-010", attempt="用 vLLM 做推理加速评测",
        expectation="评测吞吐提升 3 倍以上",
        observation="吞吐约 2.2 倍，但长输入下 kv-cache 占用高，并发受限",
        blocker="长输入下 kv-cache 显存挤占并发",
        attribution=("kv-cache 随序列长度线性增长", "observed"),
        boundary="该模型与 24G 单卡",
        conditions=dict(hardware="单卡 24G", framework="vLLM", stage="推理评测"),
        confidence="medium", status="已绕过",
        author="模拟·王同学", date="2026-08-15",
    ),
    dict(
        id="R-011", attempt="混合精度 fp16 训练",
        expectation="fp16 比 bf16 数值精度更高",
        observation="loss 出现 NaN",
        blocker="fp16 溢出导致 NaN",
        attribution=("fp16 动态范围不足，大梯度溢出", "observed"),
        boundary="该模型与学习率设置",
        conditions=dict(precision="fp16", stage="训练"),
        confidence="high", status="已解决",
        author="模拟·赵同学", date="2026-08-18",
    ),
    dict(
        id="R-012", attempt="web qa 数据配比从 1:1 调到 1:3",
        expectation="偏向通用数据提升泛化",
        observation="领域评测降 1.2，通用评测升 0.3",
        blocker="领域与通用此消彼长",
        attribution=("配比敏感点在 1:2 附近", "assumption"),
        boundary="当前任务组合",
        confidence="low", status="进行中",
        author="模拟·赵同学", date="2026-08-20",
    ),
    dict(
        id="R-013", attempt="D 数据集 v2（修复了标注错位）直接替换 v1 训练",
        expectation="数据修复带来全面提升",
        observation="多数指标上升，但长文本摘要 Rouge-L 意外下降 0.8",
        blocker="数据版本变更引入回归",
        attribution=("v2 修复改变了长文本样本分布", "assumption"),
        boundary="该任务与 v1/v2 差异",
        conditions=dict(dataset_version="D 数据集 v1 → v2", stage="训练"),
        confidence="low", status="进行中",
        missing_info=["v1/v2 长文本样本 diff"],
        author="模拟·李师兄", date="2026-08-25",
    ),
    dict(
        id="R-014", attempt="试图复现某论文的 0.92 分结果",
        expectation="按论文配置应能接近",
        observation="最好 0.87，差 5 个点",
        blocker="论文关键细节未披露（数据划分与后处理）",
        attribution=("复现差距来自未披露的后处理", "assumption"),
        boundary="论文公开配置",
        confidence="low", status="已放弃",
        missing_info=["作者的后处理代码"],
        author="模拟·王同学", date="2026-09-01",
    ),
]


def _build(seed: dict) -> Archive:
    attr_text, attr_type = seed.get("attribution", ("", "assumption"))
    provenance = Provenance(
        author=seed.get("author", "模拟·未署名"),
        date=seed.get("date", "2026-08-01"),
        source="模拟",
    )
    links = []
    for lk in seed.get("links", []):
        links.append(Link(
            target=lk["target"], relation=lk["relation"],
            same=[DimValue(dim=Dim(d), value=v) for d, v in lk.get("same", [])],
            diff=[DimDelta(dim=Dim(d), from_value=f, to_value=t)
                  for d, f, t in lk.get("diff", [])],
            transferable=lk.get("transferable", ""),
        ))
    return Archive(
        id=seed["id"], attempt=seed["attempt"],
        expectation=seed["expectation"], observation=seed["observation"],
        blocker=seed["blocker"],
        attribution=Attribution(text=attr_text, type=attr_type),
        boundary=seed.get("boundary", ""),
        confidence=seed.get("confidence", "low"),
        status=seed.get("status", "进行中"),
        provenance=provenance,
        conditions=dict(seed.get("conditions", {})),
        missing_info=list(seed.get("missing_info", [])),
        artifacts=[Artifact(kind=k, ref=r) for k, r in seed.get("artifacts", [])],
        links=links,
        evidence_refs=[EvidenceRef(record=rid, quote=q) for rid, q in seed.get("evidence", [])],
    )


class SeedGenerator:
    """生成模拟档案。所有记录必须标注 source=模拟，不得混入真实数据当模拟用。"""

    def __init__(self, plan: SeedPlan | None = None) -> None:
        self.plan = plan or SeedPlan()

    def generate(self) -> list[dict]:
        """按计划返回种子档案（字典形式，便于直接写库文件）。"""
        return [_build(s).to_dict() for s in _SEEDS[: self.plan.total]]

    def check_plan(self, records: list[dict]) -> list[str]:
        """自检：伏笔是否埋够、同阻塞点簇是否存在、来源标注是否齐全。"""
        issues: list[str] = []
        abandoned = [r for r in records if r.get("status") == "已放弃" and r.get("blocker", "").strip()]
        if len(abandoned) < self.plan.abandoned_with_blocker:
            issues.append("已放弃且阻塞点明确的记录不足 %d 条（现有 %d）——死实验复活无法演示"
                          % (self.plan.abandoned_with_blocker, len(abandoned)))
        blockers: dict[str, int] = {}
        for r in records:
            blockers[r["blocker"]] = blockers.get(r["blocker"], 0) + 1
        if not any(v >= self.plan.same_blocker_cluster for v in blockers.values()):
            issues.append("不存在同阻塞点 >= %d 条的簇——失败地图与孵化清单缺主材料"
                          % self.plan.same_blocker_cluster)
        for r in records:
            if r.get("provenance", {}).get("source") != "模拟":
                issues.append("%s 的来源不是「模拟」" % r.get("id"))
        return issues

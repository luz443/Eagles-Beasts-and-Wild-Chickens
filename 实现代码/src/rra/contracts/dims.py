"""条件维度枚举。取值必须来自这里，禁止自由文本——网页的对比矩阵靠它对位。"""

from enum import Enum


class Dim(str, Enum):
    """九个条件维度（与 contracts/dim.json 一一对应）。"""

    MODEL = "model"
    SEQ_LEN = "seq_len"
    BATCH = "batch"
    MICRO_BATCH = "micro_batch"
    PRECISION = "precision"
    HARDWARE = "hardware"
    DATASET_VERSION = "dataset_version"
    STAGE = "stage"
    FRAMEWORK = "framework"


DIM_LABELS = {
    Dim.MODEL: "模型",
    Dim.SEQ_LEN: "序列长度",
    Dim.BATCH: "批大小",
    Dim.MICRO_BATCH: "微批大小",
    Dim.PRECISION: "精度",
    Dim.HARDWARE: "硬件",
    Dim.DATASET_VERSION: "数据版本",
    Dim.STAGE: "阶段",
    Dim.FRAMEWORK: "框架",
}

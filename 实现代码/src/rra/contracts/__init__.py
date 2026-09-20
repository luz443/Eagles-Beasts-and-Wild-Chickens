"""契约层：维度枚举、数据模型、确定性校验。"""

from .dims import Dim, DIM_LABELS
from .models import Archive, Attribution, Artifact, DimDelta, DimValue, EvidenceRef, Library, Link, Provenance
from .validator import Validator, Violation

__all__ = [
    "Dim", "DIM_LABELS", "Archive", "Attribution", "Artifact", "DimDelta", "DimValue",
    "EvidenceRef", "Library", "Link", "Provenance", "Validator", "Violation",
]

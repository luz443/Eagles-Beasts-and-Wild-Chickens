"""平台技能脚本：每个类对应一个技能，输出必须通过契约校验。"""

from .base import SkillBase, SkillInput, SkillOutput, SkillRefusal
from .cache import CacheEntry, SkillCache
from .condition_compare import ConditionCompareSkill
from .extract import ExtractSkill
from .induction import InductionSkill
from .resurrection import ResurrectionSkill
from .reverse_lookup import ReverseLookupSkill
from .reviewer2 import Reviewer2Skill

__all__ = [
    "SkillBase", "SkillInput", "SkillOutput", "SkillRefusal",
    "CacheEntry", "SkillCache",
    "ExtractSkill", "ReverseLookupSkill", "ConditionCompareSkill",
    "InductionSkill", "ResurrectionSkill", "Reviewer2Skill",
]

"""网页侧召回：确定性打分，只做召回不做判定。"""

from .scorer import Hit, RecallScorer

__all__ = ["Hit", "RecallScorer"]

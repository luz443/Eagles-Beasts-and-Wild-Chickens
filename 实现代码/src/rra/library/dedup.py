"""导入去重：dedup_key 是归一化「尝试 + 阻塞点 + 关键条件」的指纹。"""

import json
import re
import unicodedata

from ..contracts.models import Archive

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[，。！？、；：,.!?;:\"'\u201c\u201d\u2018\u2019（）()\[\]【】]+")

# 去重指纹的四段：尝试 / 阻塞点 / 关键条件（来自 links 的 same+diff）/ 关联产物引用。
# 其中条件与产物必须**排序后**参与，否则同样的两条档案只因条目顺序不同就会被判成不同。
_DIM_ORDER = ["model", "seq_len", "batch", "micro_batch", "precision",
              "hardware", "dataset_version", "stage", "framework"]


class Deduplicator:
    """把一条档案算成一个可比较的指纹。规则写死、可测、无外部依赖。"""

    def normalize(self, text: str) -> str:
        """归一化：NFKC（全半角统一）→ 去标点 → 去全部空白 → 转小写。

        指纹用途是「同一内容判等」，空白与标点都不该参与比较，
        因此这里把空白完全去掉，而不是压缩成一个空格。
        """
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", str(text))
        t = _PUNCT.sub("", t)
        t = _WS.sub("", t)
        return t.lower()

    def key_of(self, archive: Archive) -> str:
        """四段历史指纹；提供结构化条件时追加排序后的第五段。

        同一档案多次计算结果必须一致；内容不同（尝试/阻塞点/产物任一变化）指纹不同。
        """
        conditions = []
        for link in archive.links:
            for s in link.same:
                conditions.append("%s=%s" % (s.dim.value, self.normalize(s.value)))
            for d in link.diff:
                conditions.append("%s:%s->%s" % (
                    d.dim.value, self.normalize(d.from_value), self.normalize(d.to_value)))
        parts = [
            self.normalize(archive.attempt),
            self.normalize(archive.blocker),
            ",".join(sorted(conditions)),
            ",".join(sorted(self.normalize(a.ref) for a in archive.artifacts)),
        ]
        if archive.conditions:
            # 条件值保留标点和单个空格，避免 v1.10 / v11.0 等版本号碰撞。
            # JSON 数组为每个维度和值保留边界，不让逗号、等号成为分隔歧义。
            entries = [
                [dim, _WS.sub(" ", unicodedata.normalize("NFKC", value).strip()).lower()]
                for dim, value in sorted(archive.conditions.items())
            ]
            parts.append(json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
        return "\x1f".join(parts)

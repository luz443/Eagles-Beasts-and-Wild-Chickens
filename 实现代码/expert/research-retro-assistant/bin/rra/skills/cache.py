"""技能调用结果缓存：用（提示词哈希，输入哈希）作键，命中即复用。

存在的唯一理由是**成本**：开发期反复调试同一个输入时，第二次起不再消耗 Credits；
同时它也让「同一个输入给同一个提示词版本，输出应当一致」变成可验证的事。
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CacheEntry:
    """一条缓存：键、输出、写回时间、命中的提示词版本。"""

    key: str
    output: dict
    created_at: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {"key": self.key, "output": self.output,
                "created_at": self.created_at, "prompt_version": self.prompt_version}

    @classmethod
    def from_dict(cls, raw: dict) -> "CacheEntry":
        return cls(key=raw["key"], output=raw.get("output", {}),
                   created_at=raw.get("created_at", ""),
                   prompt_version=raw.get("prompt_version", ""))


class SkillCache:
    """本地文件缓存。默认关闭：只有显式开启才写入，避免把调试噪音留在仓库里。"""

    def __init__(self, path: Path | None, enabled: bool = False) -> None:
        self.path = Path(path) if path else None
        self.enabled = enabled
        self._entries: dict[str, CacheEntry] = {}
        self._hits = 0
        self._lookups = 0
        if self.enabled and self.path and self.path.exists():
            self._load()

    def key_of(self, prompt_hash: str, input_hash: str) -> str:
        """键 = sha256(提示词哈希 + 输入哈希) 的前 16 位。稳定且与顺序无关的输入需调用方保证。"""
        raw = (str(prompt_hash) + "\x1f" + str(input_hash)).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def get(self, key: str) -> CacheEntry | None:
        """命中返回条目，未命中返回 None（不是抛错）。"""
        self._lookups += 1
        entry = self._entries.get(key)
        if entry is not None:
            self._hits += 1
        return entry

    def put(self, entry: CacheEntry) -> None:
        """只在 enabled 为真时写入；写入失败不得影响主流程。"""
        self._entries[entry.key] = entry
        if not (self.enabled and self.path):
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({k: v.to_dict() for k, v in self._entries.items()},
                           ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        except OSError:
            pass

    def stats(self) -> dict:
        """返回条数与命中率，用于在报告里说明「省了多少次调用」。"""
        rate = (self._hits / self._lookups) if self._lookups else 0.0
        return {"entries": len(self._entries), "lookups": self._lookups,
                "hits": self._hits, "hit_rate": round(rate, 3)}

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = {k: CacheEntry.from_dict(v) for k, v in raw.items()}
        except (OSError, ValueError, KeyError):
            self._entries = {}

"""盲测守门：冻结前禁止读取盲测用例，且**冻结后改提示词立刻失效**。

守门要防的是一场特定的自我欺骗：先把盲测用例跑出好看的数字，再回头调整提示词。
所以纪律必须落成代码级约束，而不是写在文档里的君子协定：

1. `seal()` / `seal_many()` 必须给出提示词路径并算出 64 位 sha256 —— 没有哈希，就证明不了"跑之前提示词没动过"；
   本作品的规则分散在六份技能提示词里，所以用 `seal_many()` 一次冻结一组，逐份复核；
2. 每次读取盲测用例前**重新计算当前提示词哈希**并比对 —— 冻结后再改提示词，读取会被拦下；
3. 未冻结、哈希缺失或哈希不一致，一律 `PermissionError`，不给"提醒一下就放行"的余地。

2026-09-19 外部代码审查指出：原实现三条都能绕过（seal 可传空路径、读前不复核、run_eval --blind
未冻结也退 0）。本文件是那次修复的落地。
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .cases import Case

SHA256_HEX_LEN = 64


@dataclass
class FreezeRecord:
    """冻结记录：版本号 + 时间 + 冻结人 + 提示词路径与哈希。

    `prompt_hash` 是提示词的 sha256。手写的版本号可以被改，哈希不能——
    盲测结果要能证明「跑之前提示词没被动过」，靠的就是它；
    `prompt_path` 一并记下，否则事后无从复核（这是原实现的漏洞之一）。

    `prompt_hashes`（可选）是**多份提示词**的逐文件哈希表：本作品的判断规则分散在六个
    技能提示词里，只冻结其中一份等于放行另外五份。为空时退回单文件口径，
    因此旧冻结文件与旧测试继续有效。
    """

    prompt_version: str
    frozen_at: str
    frozen_by: str
    prompt_hash: str = ""
    prompt_path: str = ""
    prompt_hashes: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def hash_prompt(path: str) -> str:
        """计算提示词文件的 sha256（十六进制，64 位）。"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def combine(prompt_hashes: dict[str, str]) -> str:
        """多份提示词的合并指纹：按路径排序后依次拼「路径 \\0 哈希 \\0」，再取 sha256。

        为什么把路径也拼进去：否则把两份提示词互换文件名会得到同一个合并哈希，
        冻结就失去意义。为什么先排序：文件系统返回顺序不稳定，冻结必须可复现。
        """
        h = hashlib.sha256()
        for path in sorted(prompt_hashes or {}):
            h.update(path.encode("utf-8"))
            h.update(b"\x00")
            h.update(str(prompt_hashes[path]).encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()


class BlindGuard:
    """未冻结（或提示词已被改动）时读取盲测用例 → 抛错并说明原因；否则放行。"""

    def __init__(self, freeze: FreezeRecord | None = None, prompt_path: str = "") -> None:
        self.freeze = freeze
        self.prompt_path = prompt_path or (freeze.prompt_path if freeze else "")

    def is_frozen(self) -> bool:
        return self.freeze is not None

    def assert_can_read(self, case: Case) -> None:
        """放行条件：不是盲测用例，或已冻结**且**提示词未被改动。"""
        if not case.blind:
            return
        if not self.is_frozen():
            raise PermissionError(
                "盲测用例（#%d）在提示词冻结前不得读取——先 seal() 并记录哈希。" % case.no)
        self.verify_prompt_unchanged()

    def verify_prompt_unchanged(self) -> None:
        """重新计算当前提示词哈希并与冻结记录比对；任一份不一致即拒绝。"""
        if self.freeze is None:
            raise PermissionError("尚未冻结，无法校验提示词。")
        # 多份口径：六个技能的提示词都要逐份复核——只盯一份等于放行另外五份。
        if self.freeze.prompt_hashes:
            for path in sorted(self.freeze.prompt_hashes):
                self._verify_one(path, self.freeze.prompt_hashes[path])
            return
        # 兼容旧冻结文件：只有单份 prompt_hash / prompt_path
        if len(self.freeze.prompt_hash) != SHA256_HEX_LEN:
            raise PermissionError(
                "冻结记录里没有有效的提示词 sha256（当前为 %r）——无法证明提示词未被改动，"
                "不得读取盲测用例。" % self.freeze.prompt_hash)
        path = self.freeze.prompt_path or self.prompt_path
        if not path:
            raise PermissionError("冻结记录未保存提示词路径，无法复核哈希。")
        self._verify_one(path, self.freeze.prompt_hash)

    def _verify_one(self, path: str, expected: str) -> None:
        """复核单份提示词：哈希缺失、文件不在、内容被改，一律拒绝。"""
        if len(str(expected)) != SHA256_HEX_LEN:
            raise PermissionError(
                "冻结记录里没有有效的提示词 sha256（%s 为 %r）——无法证明提示词未被改动，"
                "不得读取盲测用例。" % (path, expected))
        if not Path(path).is_file():
            raise PermissionError("提示词文件已不存在：%s（无法复核，按未冻结处理）。" % path)
        current = FreezeRecord.hash_prompt(path)
        if current != expected:
            raise PermissionError(
                "提示词在冻结后被改动（%s：当前 %s… ≠ 冻结 %s…）：盲测结果作废，"
                "重新 seal() 之后才允许读取用例。"
                % (path, current[:12], str(expected)[:12]))

    def seal(self, prompt_version: str, frozen_by: str,
             prompt_path: str = "", frozen_at: str = "") -> FreezeRecord:
        """冻结单份提示词：记录版本、人、时间与 sha256。重复冻结是违规，直接抛错。

        与旧实现的区别：**prompt_path 不再是可选的**。允许空路径等于允许"冻结了个空气"。
        """
        if not prompt_path:
            raise ValueError(
                "seal() 必须提供提示词路径：没有哈希就证明不了跑批前后提示词没变，"
                "盲测纪律等于没有。")
        return self.seal_many(prompt_version, frozen_by, [prompt_path], frozen_at)

    def seal_many(self, prompt_version: str, frozen_by: str,
                  prompt_paths, frozen_at: str = "") -> FreezeRecord:
        """冻结**一组**提示词。

        本作品的语义判断分散在六个技能提示词里，只冻结一份无法证明"跑批前后规则没变"。
        合并哈希由 `FreezeRecord.combine` 算出（路径参与、排序后拼接），
        逐份哈希同时保留，便于事后指出**究竟是哪一份**被改了。
        """
        if self.is_frozen():
            raise RuntimeError("已冻结（%s），不得重复冻结" % self.freeze.prompt_version)
        paths = [str(p) for p in (prompt_paths or [])]
        if not paths:
            raise ValueError(
                "seal_many() 必须提供至少一份提示词路径：没有哈希就证明不了跑批前后提示词没变，"
                "盲测纪律等于没有。")
        hashes: dict[str, str] = {}
        for path in paths:
            if not Path(path).is_file():
                raise ValueError("提示词文件不存在，无法冻结：%s" % path)
            digest = FreezeRecord.hash_prompt(path)
            if len(digest) != SHA256_HEX_LEN:
                raise ValueError("提示词哈希异常（%r）：必须是 64 位 sha256" % digest)
            hashes[path] = digest

        self.freeze = FreezeRecord(
            prompt_version=prompt_version,
            frozen_at=frozen_at or datetime.now().isoformat(timespec="seconds"),
            frozen_by=frozen_by,
            prompt_hash=FreezeRecord.combine(hashes),
            prompt_path=paths[0],
            prompt_hashes=hashes,
        )
        self.prompt_path = paths[0]
        return self.freeze

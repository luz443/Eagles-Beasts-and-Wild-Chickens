"""盲测守门：冻结前禁止读取盲测用例，且**冻结后改提示词立刻失效**。

守门要防的是一场特定的自我欺骗：先把盲测用例跑出好看的数字，再回头调整提示词。
所以纪律必须落成代码级约束，而不是写在文档里的君子协定：

1. `seal()` 必须给出提示词路径并算出 64 位 sha256 —— 没有哈希，就证明不了"跑之前提示词没动过"；
2. 每次读取盲测用例前**重新计算当前提示词哈希**并比对 —— 冻结后再改提示词，读取会被拦下；
3. 未冻结、哈希缺失或哈希不一致，一律 `PermissionError`，不给"提醒一下就放行"的余地。

2026-09-19 外部代码审查指出：原实现三条都能绕过（seal 可传空路径、读前不复核、run_eval --blind
未冻结也退 0）。本文件是那次修复的落地。
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .cases import Case

SHA256_HEX_LEN = 64


@dataclass
class FreezeRecord:
    """冻结记录：版本号 + 时间 + 冻结人 + 提示词路径与哈希。

    `prompt_hash` 是提示词文件的 sha256。手写的版本号可以被改，哈希不能——
    盲测结果要能证明「跑之前提示词没被动过」，靠的就是它；
    `prompt_path` 一并记下，否则事后无从复核（这是原实现的漏洞之一）。
    """

    prompt_version: str
    frozen_at: str
    frozen_by: str
    prompt_hash: str = ""
    prompt_path: str = ""

    @staticmethod
    def hash_prompt(path: str) -> str:
        """计算提示词文件的 sha256（十六进制，64 位）。"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
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
        """重新计算当前提示词哈希并与冻结记录比对；不一致即拒绝。"""
        if self.freeze is None:
            raise PermissionError("尚未冻结，无法校验提示词。")
        if len(self.freeze.prompt_hash) != SHA256_HEX_LEN:
            raise PermissionError(
                "冻结记录里没有有效的提示词 sha256（当前为 %r）——无法证明提示词未被改动，"
                "不得读取盲测用例。" % self.freeze.prompt_hash)
        path = self.freeze.prompt_path or self.prompt_path
        if not path:
            raise PermissionError("冻结记录未保存提示词路径，无法复核哈希。")
        if not Path(path).is_file():
            raise PermissionError("提示词文件已不存在：%s（无法复核，按未冻结处理）。" % path)
        current = FreezeRecord.hash_prompt(path)
        if current != self.freeze.prompt_hash:
            raise PermissionError(
                "提示词在冻结后被改动（当前 %s… ≠ 冻结 %s…）：盲测结果作废，"
                "重新 seal() 之后才允许读取用例。"
                % (current[:12], self.freeze.prompt_hash[:12]))

    def seal(self, prompt_version: str, frozen_by: str,
             prompt_path: str = "", frozen_at: str = "") -> FreezeRecord:
        """冻结：记录版本、人、时间与提示词 sha256。重复冻结是违规，直接抛错。

        与旧实现的区别：**prompt_path 不再是可选的**。允许空路径等于允许"冻结了个空气"。
        """
        if self.is_frozen():
            raise RuntimeError("已冻结（%s），不得重复冻结" % self.freeze.prompt_version)
        if not prompt_path:
            raise ValueError(
                "seal() 必须提供提示词路径：没有哈希就证明不了跑批前后提示词没变，"
                "盲测纪律等于没有。")
        path = Path(prompt_path)
        if not path.is_file():
            raise ValueError("提示词文件不存在，无法冻结：%s" % prompt_path)
        digest = FreezeRecord.hash_prompt(str(path))
        if len(digest) != SHA256_HEX_LEN:
            raise ValueError("提示词哈希异常（%r）：必须是 64 位 sha256" % digest)

        self.freeze = FreezeRecord(
            prompt_version=prompt_version,
            frozen_at=frozen_at or datetime.now().isoformat(timespec="seconds"),
            frozen_by=frozen_by,
            prompt_hash=digest,
            prompt_path=str(path),
        )
        self.prompt_path = str(path)
        return self.freeze

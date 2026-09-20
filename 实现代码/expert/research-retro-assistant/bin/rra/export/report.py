"""导出 Markdown：单条档案报告与避坑清单。输出必须带编号与原文引用。"""

_TYPE_LABEL = {"assumption": "归因假设（未证实）", "observed": "已观察的事实"}


def cell(text) -> str:
    """表格单元格安全化：竖线会把表格撑破，换行会破坏行结构，行首 # 会被当标题。"""
    s = str(text if text is not None else "")
    s = s.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    return s.lstrip("#").strip()


class MarkdownExporter:
    """导出的报告也要能溯源：编号、原文、假设/事实的区分一个都不能少。"""

    def archive_report(self, archive: dict) -> str:
        attr = archive.get("attribution", {})
        prov = archive.get("provenance", {})
        lines = [
            "# %s 档案报告" % archive.get("id", "?"), "",
            "| 字段 | 内容 |", "| --- | --- |",
            "| 尝试 | %s |" % cell(archive.get("attempt", "")),
            "| 预期 | %s |" % cell(archive.get("expectation", "")),
            "| 观察 | %s |" % cell(archive.get("observation", "")),
            "| 阻塞点 | %s |" % cell(archive.get("blocker", "")),
            "| 归因 | %s（%s） |" % (
                cell(attr.get("text", "")),
                _TYPE_LABEL.get(attr.get("type", ""), "未知")),
            "| 适用边界 | %s |" % cell(archive.get("boundary", "")),
            "| 置信度 | %s |" % cell(archive.get("confidence", "")),
            "| 状态 | %s |" % cell(archive.get("status", "")),
            "| 提出人 / 时间 | %s / %s |" % (cell(prov.get("author", "")), cell(prov.get("date", ""))),
        ]
        missing = archive.get("missing_info") or []
        if missing:
            lines.append("| 缺失信息 | %s |" % cell("；".join(missing)))
        refs = archive.get("evidence_refs") or []
        if refs:
            lines += ["", "## 证据引用", ""]
            for ref in refs:
                lines.append("- **%s**：「%s」" % (
                    cell(ref.get("record", "?")), cell(ref.get("quote", ""))))
        lines.append("")
        return "\n".join(lines)

    def blocker_digest(self, records: list[dict]) -> str:
        """按阻塞点聚合的避坑清单：每条带编号与状态，不下方向判决。"""
        groups: dict[str, list[dict]] = {}
        for r in records:
            groups.setdefault(r.get("blocker", "（未填）", ), []).append(r)
        lines = ["# 避坑清单（按阻塞点聚合）", ""]
        for blocker, recs in groups.items():
            lines.append("## %s（%d 条记录）" % (cell(blocker), len(recs)))
            for r in recs:
                lines.append("- %s（%s）：%s" % (
                    cell(r.get("id", "?")), cell(r.get("status", "?")), cell(r.get("attempt", ""))))
            lines.append("")
        lines.append("> 说明：本清单只呈现尝试密度与证据状态，不对方向作「值得 / 不值得」的判决。")
        lines.append("")
        return "\n".join(lines)

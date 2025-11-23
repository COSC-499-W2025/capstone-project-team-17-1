"""Utilities for generating portfolio-ready top project summaries."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, List, Mapping, MutableMapping, Optional

from .external_artifacts import fetch_snapshot_artifacts
from .project_ranking import ProjectRanking, rank_projects_from_snapshots


@dataclass(frozen=True)
class SummarySection:
    title: str
    content: str = ""


@dataclass(frozen=True)
class SummaryTemplate:
    project_id: str
    title: str
    sections: List[SummarySection] = field(default_factory=list)
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    score_hint: Optional[float] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "sections": [{"title": section.title, "content": section.content} for section in self.sections],
            "metadata": dict(self.metadata),
            "score_hint": self.score_hint,
        }


@dataclass(frozen=True)
class EvidenceItem:
    kind: str
    reference: str
    detail: str
    source: str
    weight: float = 1.0
    id: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "reference": self.reference,
            "detail": self.detail,
            "source": self.source,
            "weight": self.weight,
        }

    def format_reference(self, ordinal: int) -> str:
        label = f"[{ordinal}]"
        return f"{label} {self.kind.title()} - {self.reference}: {self.detail} (source: {self.source})"


@dataclass(frozen=True)
class ProjectSummary:
    project_id: str
    title: str
    rank: Optional[int]
    score: Optional[float]
    overview: str
    summary_text: str
    highlights: List[str]
    references: List[str]
    confidence: dict[str, object]
    evidence: List[EvidenceItem]
    template: SummaryTemplate

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "rank": self.rank,
            "score": self.score,
            "overview": self.overview,
            "summary_text": self.summary_text,
            "highlights": list(self.highlights),
            "references": list(self.references),
            "confidence": dict(self.confidence),
            "evidence": [item.to_dict() for item in self.evidence],
            "template": self.template.to_dict(),
        }


# this is templete for summary
def create_summary_template(project_id: str, snapshot: Mapping[str, object], ranking: ProjectRanking | None = None) -> SummaryTemplate:
    file_summary = snapshot.get("file_summary", {}) or {}
    languages = snapshot.get("languages", {}) or {}
    frameworks = snapshot.get("frameworks", []) or []

    sections = [
        SummarySection(title="Overview"),
        SummarySection(title="Impact and Evidence"),
        SummarySection(title="Stack Highlights"),
    ]
    metadata: MutableMapping[str, object] = {
        "file_count": file_summary.get("file_count", 0),
        "active_days": file_summary.get("active_days", 0),
        "languages": sorted(languages),
        "frameworks": list(frameworks),
    }

    score_hint = ranking.score if ranking else None
    title = f"Top Project: {project_id}"
    return SummaryTemplate(project_id=project_id, title=title, sections=sections, metadata=metadata, score_hint=score_hint)


#add evidence 
def _add_evidence(evidence: List[EvidenceItem], kind: str, reference: str, detail: str, source: str, weight: float = 1.0) -> None:
    evidence.append(
        EvidenceItem(
            kind=kind,
            reference=reference,
            detail=detail,
            source=source,
            weight=weight,
            id=f"E{len(evidence) + 1}",
        )
    )


def gather_evidence(
    snapshot: Mapping[str, object],
    external: Mapping[str, Iterable[Mapping[str, object]]] | None = None,
) -> List[EvidenceItem]:
    # collecting the concrete facts.
    evidence: List[EvidenceItem] = []
    file_summary = snapshot.get("file_summary", {}) or {}
    if file_summary:
        file_count = int(file_summary.get("file_count", 0) or 0)
        total_bytes = int(file_summary.get("total_bytes", 0) or 0)
        if file_count:
            detail = f"Processed {file_count} files totalling {total_bytes} bytes"
            _add_evidence(evidence, "benchmark", "analysis:file_count", detail, "snapshot", weight=1.0)
        active_days = int(file_summary.get("active_days", 0) or 0)
        if active_days:
            detail = f"Active development across {active_days} days"
            _add_evidence(evidence, "benchmark", "analysis:active_days", detail, "snapshot", weight=0.8)
        timeline = file_summary.get("timeline", {}) or {}
        if timeline:
            busiest_period, busiest_count = max(timeline.items(), key=lambda item: item[1])
            detail = f"Peak activity of {busiest_count} updates during {busiest_period}"
            _add_evidence(evidence, "benchmark", f"analysis:timeline:{busiest_period}", detail, "snapshot", weight=0.6)

    languages = snapshot.get("languages", {}) or {}
    if languages:
        top_language, top_count = max(languages.items(), key=lambda item: item[1])
        detail = f"{len(languages)} languages spotted with {top_language} leading ({top_count} files)"
        _add_evidence(evidence, "commit", f"languages:{top_language}", detail, "snapshot", weight=0.9)

    frameworks = snapshot.get("frameworks", []) or []
    if frameworks:
        detail = f"Frameworks detected: {', '.join(sorted(frameworks))}"
        _add_evidence(evidence, "commit", "frameworks", detail, "snapshot", weight=0.7)

    collaboration = snapshot.get("collaboration", {}) or {}
    contributors = collaboration.get("contributors", {}) or {}
    if contributors:
        total_contributions = sum(int(value) for value in contributors.values())
        leader, leader_count = max(contributors.items(), key=lambda item: item[1])
        detail = f"{total_contributions} commits recorded; {leader} leads with {leader_count}"
        _add_evidence(evidence, "commit", "collaboration:contributors", detail, "snapshot", weight=1.0)
    else:
        classification = collaboration.get("classification")
        if classification:
            detail = f"Collaboration classified as {classification}"
            _add_evidence(evidence, "commit", "collaboration:classification", detail, "snapshot", weight=0.4)

    # external evidence can come from the snapshot, caller overrides, or live fetches
    external_sources = _resolve_external_sources(snapshot, external)
    if external_sources:
        for source_kind, entries in external_sources.items():
            normalized_kind = _canonical_external_kind(source_kind)
            for entry in entries or []:
                if not isinstance(entry, Mapping):
                    continue
                reference = _resolve_external_reference(normalized_kind, entry) or source_kind
                detail, weight_hint = _format_external_detail(normalized_kind, entry)
                weight = float(entry.get("weight", weight_hint))
                _add_evidence(evidence, normalized_kind, reference, detail, "external", weight=weight)

    return evidence


def _resolve_external_sources(
    snapshot: Mapping[str, object],
    provided: Mapping[str, Iterable[Mapping[str, object]]] | None,
) -> Mapping[str, Iterable[Mapping[str, object]]]:
    if provided:
        return provided
    stored = snapshot.get("external_artifacts") if isinstance(snapshot, Mapping) else None
    if stored:
        return stored 
    # when the snapshot didn't store the refs
    fetched = fetch_snapshot_artifacts(snapshot)
    return fetched


def _canonical_external_kind(source_kind: str) -> str:
    lowered = source_kind.lower()
    if lowered in {"pull_request", "pull_requests", "prs"}:
        return "pull_request"
    if lowered in {"issue", "issues"}:
        return "issue"
    return lowered


def _resolve_external_reference(kind: str, entry: Mapping[str, object]) -> str:
    if entry.get("url"):
        return str(entry["url"])
    if entry.get("reference"):
        return str(entry["reference"])
    if entry.get("id"):
        return f"{kind}:{entry['id']}"
    if entry.get("number"):
        return f"{kind}:{entry['number']}"
    return kind


def _format_external_detail(kind: str, entry: Mapping[str, object]) -> tuple[str, float]:
    if kind == "pull_request":
        return _format_pull_request_detail(entry)
    if kind == "issue":
        return _format_issue_detail(entry)
    detail = (
        entry.get("title")
        or entry.get("summary")
        or entry.get("description")
        or entry.get("detail")
        or "External artifact"
    )
    return str(detail), 0.9


def _format_pull_request_detail(entry: Mapping[str, object]) -> tuple[str, float]:
    number = entry.get("number")
    prefix = f"PR #{number}" if number is not None else "Pull request"
    title = entry.get("title") or ""
    state = (entry.get("state") or "").lower()
    merged_at = entry.get("merged_at")
    merged_by = entry.get("merged_by") or entry.get("user")
    descriptor = prefix
    if title:
        descriptor += f": {title}"
    meta_parts = []
    if state:
        meta_parts.append(state)
    if merged_at:
        meta_parts.append(f"merged {str(merged_at)[:10]}")
    if merged_by:
        meta_parts.append(f"by {merged_by}")
    if meta_parts:
        descriptor += f" ({', '.join(meta_parts)})"
    weight = 1.2 if merged_at or state == "merged" else 0.9
    return descriptor, weight


def _format_issue_detail(entry: Mapping[str, object]) -> tuple[str, float]:
    number = entry.get("number")
    prefix = f"Issue #{number}" if number is not None else "Issue"
    title = entry.get("title") or ""
    state = (entry.get("state") or "").lower()
    user = entry.get("user")
    descriptor = prefix
    if title:
        descriptor += f": {title}"
    meta_parts = []
    if state:
        meta_parts.append(state)
    if user:
        meta_parts.append(f"by {user}")
    if meta_parts:
        descriptor += f" ({', '.join(meta_parts)})"
    weight = 0.8 if state == "closed" else 0.6
    return descriptor, weight


class AutoWriter:
    def __init__(self, llm: Optional[object] = None) -> None:
        self._llm = llm

    def compose(
        self,
        template: SummaryTemplate,
        evidence: Iterable[EvidenceItem],
        snapshot: Mapping[str, object],
        ranking: ProjectRanking | None = None,
        *,
        rank_position: Optional[int] = None,
        use_llm: bool = False,
    ) -> ProjectSummary:
        normalised_evidence = [replace(item, id=f"E{index}") for index, item in enumerate(evidence, start=1)]
        # keep the enumerated references. 
        references = [item.format_reference(index) for index, item in enumerate(normalised_evidence, start=1)]

        offline_summary = self._compose_offline(template, normalised_evidence, snapshot, ranking, rank_position)
        summary_text = offline_summary

        if use_llm and self._llm:
            prompt = self._build_prompt(template, normalised_evidence, snapshot, ranking, rank_position)
            try:
                llm_output = self._llm.generate_summary(prompt)  # type: ignore[attr-defined]
            except AttributeError:
                llm_output = None
            if llm_output:
                summary_text = self._merge_llm_output(offline_summary, llm_output)

        highlights = self._pick_highlights(normalised_evidence)
        overview = summary_text.split("\n\n", 1)[0]
        confidence = self._score_confidence(snapshot, normalised_evidence)

        return ProjectSummary(
            project_id=template.project_id,
            title=template.title,
            rank=rank_position,
            score=ranking.score if ranking else None,
            overview=overview,
            summary_text=summary_text,
            highlights=highlights,
            references=references,
            confidence=confidence,
            evidence=normalised_evidence,
            template=template,
        )

    def _compose_offline(
        self,
        template: SummaryTemplate,
        evidence: List[EvidenceItem],
        snapshot: Mapping[str, object],
        ranking: ProjectRanking | None,
        rank_position: Optional[int],
    ) -> str:
        file_summary = snapshot.get("file_summary", {}) or {}
        languages = snapshot.get("languages", {}) or {}
        frameworks = snapshot.get("frameworks", []) or []

        lines: List[str] = []
        if rank_position is not None and ranking is not None:
            lines.append(f"{template.title} ranks #{rank_position} with a portfolio score of {ranking.score:.2f}.")

        metric_line = self._find_evidence_line(evidence, {"analysis:file_count"})
        if metric_line:
            lines.append(f"It demonstrates consistent delivery {metric_line}.")

        collaboration_line = self._find_evidence_line(evidence, {"collaboration:contributors"})
        if collaboration_line:
            lines.append(f"Collaboration profile {collaboration_line}.")

        if not collaboration_line and file_summary.get("active_days"):
            lines.append(f"Sustained activity spans {file_summary.get('active_days')} tracked days [2].")

        if frameworks:
            evidence_ref = self._find_reference_index(evidence, "frameworks")
            if evidence_ref:
                lines.append(f"Stack coverage spans {len(frameworks)} frameworks [{evidence_ref}].")

        if languages and not self._find_reference_index(evidence, "languages:"):
            sorted_langs = ", ".join(sorted(languages))
            lines.append(f"Detected languages: {sorted_langs}.")

        summary_body = "\n".join(lines)

        section_lines = [summary_body]
        impact_section = self._format_impact_section(evidence)
        if impact_section:
            section_lines.append(impact_section)

        stack_details = self._format_stack_section(languages, frameworks)
        if stack_details:
            section_lines.append(stack_details)

        return "\n\n".join(line for line in section_lines if line)

    def _find_reference_index(self, evidence: List[EvidenceItem], reference_prefix: str) -> Optional[int]:
        for index, item in enumerate(evidence, start=1):
            if item.reference.startswith(reference_prefix):
                return index
        return None

    def _find_evidence_line(self, evidence: List[EvidenceItem], references: set[str]) -> Optional[str]:
        for index, item in enumerate(evidence, start=1):
            if item.reference in references:
                return f"[{index}] {item.detail}"
        return None

    def _format_impact_section(self, evidence: List[EvidenceItem]) -> str:
        selected = [item for item in evidence if item.kind in {"benchmark", "commit", "pull_request", "issue"}]
        if not selected:
            return ""
        lines = ["Key evidence:"]
        for index, item in enumerate(selected, start=1):
            anchor = self._find_reference_index(evidence, item.reference)
            anchor_label = f"[{anchor}]" if anchor else ""
            lines.append(f"- {item.detail} {anchor_label}".rstrip())
        return "\n".join(lines)

    def _format_stack_section(self, languages: Mapping[str, int], frameworks: Iterable[str]) -> str:
        if not languages and not frameworks:
            return ""
        parts: List[str] = []
        if languages:
            dominant = ", ".join(sorted(languages))
            parts.append(f"Languages: {dominant}")
        framework_list = list(frameworks)
        if framework_list:
            parts.append(f"Frameworks: {', '.join(sorted(framework_list))}")
        return "Stack overview:\n- " + "\n- ".join(parts)
#build prompt
    def _build_prompt(
        self,
        template: SummaryTemplate,
        evidence: List[EvidenceItem],
        snapshot: Mapping[str, object],
        ranking: ProjectRanking | None,
        rank_position: Optional[int],
    ) -> str:
        references = "\n".join(item.format_reference(index) for index, item in enumerate(evidence, start=1))
        score_line = f"Rank {rank_position} with score {ranking.score:.2f}" if ranking and rank_position else "Unranked"
        return (
            f"Project: {template.project_id}\n"
            f"Title: {template.title}\n"
            f"{score_line}\n"
            f"Evidence:\n{references}\n"
            f"Snapshot metadata: {template.metadata}\n"
            "Write a concise summary that cites evidence using [n] markers."
        )

    def _merge_llm_output(self, offline_summary: str, llm_output: str) -> str:
        if not llm_output.strip():
            return offline_summary
        combined = offline_summary.strip() + "\n\n" + llm_output.strip()
        return combined.strip()

    def _pick_highlights(self, evidence: List[EvidenceItem]) -> List[str]:
        sorted_items = sorted(evidence, key=lambda item: item.weight, reverse=True)
        highlights: List[str] = []
        for index, item in enumerate(sorted_items, start=1):
            if len(highlights) >= 3:
                break
            anchor = self._find_reference_index(evidence, item.reference)
            anchor_label = f"[{anchor}]" if anchor else ""
            highlights.append(f"{item.detail} {anchor_label}".strip())
        return highlights

    def _score_confidence(self, snapshot: Mapping[str, object], evidence: List[EvidenceItem]) -> dict[str, object]:
        signals: List[dict[str, object]] = []
        flags: List[str] = []
        total_weight = 0.0

        file_summary = snapshot.get("file_summary", {}) or {}
        if file_summary:
            signals.append({"signal": "file_summary", "weight": 0.4, "present": True})
            total_weight += 0.4
        else:
            flags.append("Missing file summary reduces confidence.")

        languages = snapshot.get("languages", {}) or {}
        if languages:
            signals.append({"signal": "languages", "weight": 0.2, "present": True})
            total_weight += 0.2
        else:
            flags.append("No language data detected.")

        frameworks = snapshot.get("frameworks", []) or []
        if frameworks:
            signals.append({"signal": "frameworks", "weight": 0.1, "present": True})
            total_weight += 0.1

        collaboration = snapshot.get("collaboration", {}) or {}
        contributors = collaboration.get("contributors", {}) or {}
        if contributors:
            signals.append({"signal": "collaboration", "weight": 0.2, "present": True})
            total_weight += 0.2
        else:
            flags.append("Collaboration data incomplete.")

        if evidence:
            signals.append({"signal": "evidence", "weight": 0.3, "present": True})
            total_weight += 0.3
        else:
            flags.append("No supporting evidence items were generated.")

        overall = min(total_weight, 1.0)
        return {"overall": round(overall, 2), "signals": signals, "flags": flags}


#export to markdown 
def export_markdown(summary: ProjectSummary | Mapping[str, object]) -> str:
    data = summary.to_dict() if isinstance(summary, ProjectSummary) else dict(summary)
    title = data.get("title", "Project Summary")
    overview = data.get("overview", "")
    highlights = data.get("highlights", [])
    references = data.get("references", [])

    lines = [f"# {title}", "", overview, ""]
    if highlights:
        lines.append("## Highlights")
        for item in highlights:
            lines.append(f"- {item}")
        lines.append("")
    if references:
        lines.append("## References")
        for ref in references:
            lines.append(f"- {ref}")
    return "\n".join(line for line in lines if line is not None)


#export 
def export_readme_snippet(summary: ProjectSummary | Mapping[str, object]) -> str:
    data = summary.to_dict() if isinstance(summary, ProjectSummary) else dict(summary)
    title = data.get("title", "Project Summary")
    highlights = data.get("highlights", [])
    references = data.get("references", [])
    reference_hint = references[0] if references else ""
    preview = highlights[:2] if highlights else [data.get("overview", "")]
    lines = [f"### {title}"]
    for item in preview:
        lines.append(f"- {item}")
    if reference_hint:
        lines.append(f"- Evidence: {reference_hint}")
    return "\n".join(lines)


def export_pdf_one_pager(summary: ProjectSummary | Mapping[str, object]) -> bytes:
    markdown = export_markdown(summary)
    return _build_simple_pdf(markdown)


def _build_simple_pdf(text: str) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")

    objects: List[bytes] = []

    def add_object(body: str) -> int:
        offset = buffer.tell()
        content = f"{len(objects)+1} 0 obj\n{body}\nendobj\n".encode("latin-1")
        buffer.write(content)
        objects.append(content)
        return offset

    offsets: List[int] = []
    offsets.append(add_object("<< /Type /Catalog /Pages 2 0 R >>"))
    offsets.append(add_object("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    offsets.append(
        add_object("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    )

    stream_lines = ["BT", "/F1 11 Tf", "72 740 Td"]
    for index, line in enumerate(text.splitlines()):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index == 0:
            stream_lines.append(f"({safe}) Tj")
        else:
            stream_lines.append("T*")
            stream_lines.append(f"({safe}) Tj")
    stream_lines.append("ET")
    stream_content = "\n".join(stream_lines) + "\n"
    stream_bytes = stream_content.encode("latin-1")
    offsets.append(add_object(f"<< /Length {len(stream_bytes)} >>\nstream\n{stream_content}endstream"))

    offsets.append(add_object("<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica >>"))

    xref_pos = buffer.tell()
    buffer.write(f"xref\n0 {len(offsets)+1}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets:
        buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))

    buffer.write(f"trailer\n<< /Size {len(offsets)+1} /Root 1 0 R >>\n".encode("latin-1"))
    buffer.write(f"startxref\n{xref_pos}\n%%EOF".encode("latin-1"))
    return buffer.getvalue()


# generate the summray.
def generate_top_project_summaries(
    snapshots: Mapping[str, Mapping[str, object]],
    *,
    limit: int = 3,
    user: Optional[str] = None,
    now: Optional[object] = None,
    evidence_sources: Mapping[str, Mapping[str, Iterable[Mapping[str, object]]]] | None = None,
    use_llm: bool = False,
    llm: Optional[object] = None,
) -> List[dict[str, object]]:
    rankings = rank_projects_from_snapshots(snapshots, user=user, now=now)
    auto_writer = AutoWriter(llm=llm)
    results: List[dict[str, object]] = []
    for position, ranking in enumerate(rankings[:limit], start=1):
        snapshot = snapshots.get(ranking.project_id, {})
        template = create_summary_template(ranking.project_id, snapshot, ranking)
        external = evidence_sources.get(ranking.project_id) if evidence_sources else None
        evidence = gather_evidence(snapshot, external)
        project_summary = auto_writer.compose(
            template,
            evidence,
            snapshot,
            ranking,
            rank_position=position,
            use_llm=use_llm,
        )
        results.append(project_summary.to_dict())
    return results


__all__ = [
    "AutoWriter",
    "EvidenceItem",
    "ProjectSummary",
    "SummarySection",
    "SummaryTemplate",
    "create_summary_template",
    "export_markdown",
    "export_pdf_one_pager",
    "export_readme_snippet",
    "gather_evidence",
    "generate_top_project_summaries",
]

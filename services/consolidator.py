from __future__ import annotations

from difflib import SequenceMatcher


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def classify_materiality(finding: dict) -> str:
    severity = finding.get("severity", "MEDIUM")
    amount = float(finding.get("expected_impact_amount", 0.0) or 0.0)
    if severity == "CRITICAL" or amount >= 5_000_000:
        return "HIGHLY_MATERIAL"
    if severity in {"HIGH", "MEDIUM"} or amount >= 1_000_000:
        return "MATERIAL"
    return "IMMATERIAL"


def calculate_confidence(fieldwork_finding: dict, interim_finding: dict | None) -> float:
    base = float(fieldwork_finding.get("confidence_score", 0.0) or 0.0)
    if interim_finding:
        base = (base + float(interim_finding.get("confidence_score", 0.0) or 0.0)) / 2
    return max(0.0, min(base, 1.0))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_matching_interim(fieldwork_finding: dict, interim_findings: list[dict]) -> dict | None:
    best = None
    best_score = 0.0
    fw_desc = fieldwork_finding.get("description", "")
    for finding in interim_findings:
        score = _similarity(fw_desc, finding.get("description", ""))
        if score > best_score:
            best_score = score
            best = finding
    if best_score >= 0.6:
        return best
    return None


def match_evidence_across_sources(finding: dict) -> bool:
    """Return True if evidence appears consistent across links."""
    links = finding.get("evidence_links") or []
    numbers: set[str] = set()
    for link in links:
        reference = str(link.get("reference", ""))
        tokens = reference.replace(",", " ").replace("!", " ").split()
        for idx, token in enumerate(tokens):
            if not token.isdigit():
                continue
            prev = tokens[idx - 1].lower() if idx > 0 else ""
            if prev in {"row", "page", "sheet"}:
                continue
            numbers.add(token)
    return len(numbers) <= 1


def _severity_gap(interim: dict, fieldwork: dict) -> int:
    interim_level = SEVERITY_ORDER.get(interim.get("severity", "MEDIUM"), 2)
    field_level = SEVERITY_ORDER.get(fieldwork.get("severity", "MEDIUM"), 2)
    return abs(interim_level - field_level)


def consolidate_findings(interim_findings: list[dict], fieldwork_findings: list[dict]) -> list[dict]:
    consolidated: list[dict] = []
    for idx, fieldwork in enumerate(fieldwork_findings, 1):
        matching = find_matching_interim(fieldwork, interim_findings)
        materiality = classify_materiality(fieldwork)
        confidence = calculate_confidence(fieldwork, matching)
        evidence_ok = match_evidence_across_sources(fieldwork)
        review_flag = not evidence_ok
        if matching and _severity_gap(matching, fieldwork) >= 2:
            review_flag = True
        consolidated.append(
            {
                "interim_finding_index": matching.get("index") if matching else None,
                "fieldwork_finding_index": fieldwork.get("index"),
                "materiality": materiality,
                "review_flag": review_flag,
                "confidence_score": confidence,
            }
        )
    return consolidated

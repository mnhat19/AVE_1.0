from services.consolidator import classify_materiality, consolidate_findings, match_evidence_across_sources


def test_materiality_classifier():
    finding = {"severity": "CRITICAL", "expected_impact_amount": 1000}
    assert classify_materiality(finding) == "HIGHLY_MATERIAL"


def test_evidence_matching():
    finding = {
        "evidence_links": [
            {"reference": "Sheet1!Row 10"},
            {"reference": "Page 2"},
        ]
    }
    assert match_evidence_across_sources(finding) is True

    finding = {
        "evidence_links": [
            {"reference": "Amount 1000"},
            {"reference": "Amount 2000"},
        ]
    }
    assert match_evidence_across_sources(finding) is False


def test_consolidate_findings_review_flag():
    interim = [{"index": 1, "description": "Revenue cutoff", "severity": "LOW", "confidence_score": 0.4}]
    fieldwork = [
        {
            "index": 1,
            "description": "Revenue cut-off",
            "severity": "CRITICAL",
            "confidence_score": 0.8,
            "evidence_links": [{"reference": "Amount 1000"}, {"reference": "Amount 2000"}],
        }
    ]

    consolidated = consolidate_findings(interim, fieldwork)
    assert consolidated[0]["review_flag"] is True

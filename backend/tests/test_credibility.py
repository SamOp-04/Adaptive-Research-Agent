from __future__ import annotations

from backend.skills.source_evaluation import dedupe_findings_by_url, normalize_domain, score_source


def test_normalize_domain_strips_www():
    assert normalize_domain("https://www.reuters.com/world") == "reuters.com"


def test_score_source_known_high_trust_domain():
    result = score_source("https://nih.gov/article", published_at="2026-01-01T00:00:00+00:00")

    assert result["tier"] == "high"
    assert result["score"] > 0.7


def test_dedupe_findings_by_url_keeps_highest_credibility_match():
    findings = [
        {
            "title": "Lower score",
            "url": "https://Example.com/report/?utm_source=test",
            "credibility": {"score": 0.55},
        },
        {
            "title": "Higher score",
            "url": "http://www.example.com/report/",
            "credibility": {"score": 0.82},
        },
    ]

    deduped = dedupe_findings_by_url(findings)

    assert len(deduped) == 1
    assert deduped[0]["title"] == "Higher score"

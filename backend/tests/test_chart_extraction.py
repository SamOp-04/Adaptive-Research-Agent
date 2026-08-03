from __future__ import annotations

from backend.skills.chart_extraction import _parse_number, extract_chart_points_fast


def test_parse_number_converts_crore_to_count():
    parsed = _parse_number("5.07 crore", "Gujarat population was 5.07 crore.", "population")

    assert parsed == (50_700_000, "count")


def test_extract_chart_points_fast_keeps_year_labels_and_consistent_units():
    points = extract_chart_points_fast(
        "Gujarat population trend",
        "Population rose from 5.07 crore in 2001 to 6.04 crore in 2011 and 7.18 crore in 2026.",
        [
            {"title": "2001 census", "snippet": "In 2001, Gujarat population was 5.07 crore."},
            {"title": "2011 census", "snippet": "In 2011, Gujarat population was 6.04 crore."},
            {"title": "2026 estimate", "snippet": "In 2026, Gujarat population was 7.18 crore."},
        ],
    )

    assert points == [
        {"label": "2001", "value": 50_700_000, "unit": "count", "source_index": 0},
        {"label": "2011", "value": 60_400_000, "unit": "count", "source_index": 1},
        {"label": "2026", "value": 71_800_000, "unit": "count", "source_index": 2},
    ]


def test_extract_chart_points_fast_rejects_mixed_units():
    points = extract_chart_points_fast(
        "market performance",
        "Revenue was $3 million while margin was 14%.",
        [
            {"title": "Revenue", "snippet": "Revenue was $3 million in 2026."},
            {"title": "Margin", "snippet": "Margin was 14% in 2026."},
        ],
    )

    assert points is None

from __future__ import annotations

from backend.nodes.intent_classifier import _extract_json_object, _validate_classification


def test_extract_json_object_accepts_model_prose_wrapper():
    parsed = _extract_json_object('Here is the classification: {"query_type": "factual", "depth": "quick", "output_type": "text"}')

    assert parsed == {"query_type": "factual", "depth": "quick", "output_type": "text"}


def test_validate_classification_rejects_invalid_output_type():
    result = _validate_classification(
        {
            "query_type": "factual",
            "depth": "quick",
            "output_type": "slides",
        }
    )

    assert result is None


def test_validate_classification_normalizes_valid_values():
    result = _validate_classification(
        {
            "query_type": " Comparative ",
            "depth": " Deep ",
            "output_type": " TABLE ",
        }
    )

    assert result == {
        "query_type": "comparative",
        "depth": "deep",
        "output_type": "table",
    }

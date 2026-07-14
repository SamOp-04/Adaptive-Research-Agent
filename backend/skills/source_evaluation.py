from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "source_credibility.json"


@lru_cache(maxsize=1)
def load_credibility_config(path: str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def normalize_source_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    path = parsed.path.rstrip("/").lower()
    return f"{domain}{path}"


def dedupe_findings_by_url(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for finding in findings:
        key = normalize_source_url(str(finding.get("url", "")))
        if not key:
            key = f"missing-url-{len(order)}"
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = finding
            order.append(key)
            continue

        current_score = float(finding.get("credibility", {}).get("score", 0) or 0)
        existing_score = float(existing.get("credibility", {}).get("score", 0) or 0)
        if current_score > existing_score:
            deduped[key] = finding

    return [deduped[key] for key in order]


def tier_for_domain(domain: str, config: dict[str, Any] | None = None) -> tuple[str, float]:
    config = config or load_credibility_config()
    for blocked_domain in config.get("blocklist", []):
        if domain == blocked_domain or domain.endswith(f".{blocked_domain}"):
            return "blocklist", 0.0

    for tier_name, tier in config.get("tiers", {}).items():
        for trusted_domain in tier.get("domains", []):
            is_tld_match = trusted_domain in {"gov", "edu"} and domain.endswith(f".{trusted_domain}")
            if domain == trusted_domain or domain.endswith(f".{trusted_domain}") or is_tld_match:
                return tier_name, float(tier.get("score", config.get("default_tier_score", 0.55)))
    return "unknown", float(config.get("default_tier_score", 0.55))


def recency_score(published_at: str | None, config: dict[str, Any] | None = None) -> float:
    if not published_at:
        return 0.5

    config = config or load_credibility_config()
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.5

    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)

    age_days = max((datetime.now(timezone.utc) - published).days, 0)
    decay_days = max(float(config.get("recency_decay_days", 540)), 1.0)
    return max(0.0, min(1.0, 1.0 - (age_days / decay_days)))


def score_source(
    url: str,
    *,
    published_at: str | None = None,
    citations: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or load_credibility_config()
    domain = normalize_domain(url)
    tier_name, tier_score = tier_for_domain(domain, config)
    if tier_name == "blocklist":
        return {"domain": domain, "tier": tier_name, "score": 0.0}

    weights = config.get("weights", {})
    citation_score = min((citations or 0) / 20, 1.0)
    domain_match_score = 1.0 if tier_name != "unknown" else 0.4

    score = (
        tier_score * float(weights.get("tier", 0.5))
        + recency_score(published_at, config) * float(weights.get("recency", 0.25))
        + citation_score * float(weights.get("citation", 0.15))
        + domain_match_score * float(weights.get("domain_match", 0.1))
    )

    return {
        "domain": domain,
        "tier": tier_name,
        "score": round(max(0.0, min(score, 1.0)), 3),
    }


def passes_credibility(credibility: dict[str, Any], config: dict[str, Any] | None = None) -> bool:
    config = config or load_credibility_config()
    if credibility.get("tier") == "blocklist":
        return False
    return float(credibility.get("score", 0.0)) >= float(config.get("min_score_threshold", 0.35))

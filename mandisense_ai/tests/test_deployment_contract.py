"""The Docker image must contain everything the served features read.

Regression: the image once shipped without `data/observations/` (`.dockerignore` excluded `data/` and the Dockerfile never copied it), so the
deployed trader tools answered "0 prints on record" while every local test passed. These tests pin the contract without needing Docker.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORE = "data/observations/market_observations.parquet"


def _ignored(path: str, rules: list[str]) -> bool:
    """Docker's .dockerignore semantics for the simple rules used here: the last matching rule wins, `!` re-includes."""
    from fnmatch import fnmatchcase

    ignored = False
    for rule in rules:
        negate = rule.startswith("!")
        pattern = rule[1:] if negate else rule
        pattern = pattern.rstrip("/")
        parts = path.split("/")
        # a rule matches the path itself or any of its parent directories
        candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
        if any(fnmatchcase(c, pattern) for c in candidates):
            ignored = not negate
    return ignored


def test_observation_store_is_tracked_and_present():
    assert (ROOT / STORE).exists(), "the trader tools read this file; it must be committed (the daily workflow refreshes it)"


def test_dockerfile_copies_the_observation_store():
    assert STORE in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_dockerignore_does_not_exclude_the_observation_store():
    rules = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not _ignored(STORE, rules)
    # and the rest of data/ stays out of the image
    assert _ignored("data/observations/forecast_ledger.parquet", rules)
    assert _ignored("data/cache.json", rules)

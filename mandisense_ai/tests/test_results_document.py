"""The consolidated results document is generated from artefacts and must agree with them."""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "RESULTS.md"
RES = ROOT / "research" / "results"

pytestmark = pytest.mark.skipif(not DOC.exists(), reason="docs/RESULTS.md not built (python scripts/build_results.py)")


@pytest.fixture(scope="module")
def text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_every_linked_figure_exists(text):
    links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    assert links, "the document should carry figures"
    for link in links:
        assert (DOC.parent / link).exists(), f"missing figure {link}"


def test_no_unfilled_values(text):
    assert not re.search(r"\bnan\b|\bNaN\b|\bNone\b|\{[a-z_]+\}", text), "an unfilled value leaked into the document"


def test_sections_for_each_rubric_element_are_present(text):
    for heading in ("Evaluation protocol", "Decision quality", "revenue floor", "production engine", "Price forecasts", "Against published work",
                    "What did not help", "Sensitivity", "Supply shocks", "Limitations and threats to validity", "Reproduce and sources"):
        assert heading.lower() in text.lower(), f"section missing: {heading}"


def test_headline_numbers_match_the_source_tables(text):
    main = pd.read_csv(RES / "tomato" / "tables" / "main.csv").set_index("method")
    assert f"{main.loc['lgbm_filled', 'revenue']:,.0f}" in text
    assert f"{main.loc['nearest_today', 'revenue']:,.0f}" in text
    cmp_ = pd.read_csv(RES / "tomato" / "tables" / "comparisons.csv")
    row = cmp_[(cmp_["A"] == "lgbm_filled") & (cmp_["B"] == "lgbm_obs")].iloc[0]
    assert f"{row['regret_diff_A_minus_B']:+.0f}" in text


def test_each_studied_crop_with_results_is_reported(text):
    for crop in ("tomato", "onion", "potato", "ginger"):
        if (RES / crop / "tables" / "main.csv").exists():
            assert f"### {crop.capitalize()}" in text


def test_garlic_exclusion_is_explained(text):
    assert "Garlic" in text and "only one mandi" in text


def test_engine_rows_follow_the_artefacts(text):
    for crop in ("tomato", "onion", "potato", "ginger"):
        meta = ROOT / "mandisense_ai" / "models" / "market_choice" / crop / "meta.json"
        if meta.exists():
            bt = json.loads(meta.read_text(encoding="utf-8")).get("backtest", {})
            if bt.get("status") == "OK":
                assert f"{bt['gain_vs_highest_yesterday']['mean']:+.0f}" in text

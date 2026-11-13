"""A later, shorter Agmarknet export is layered on the base history, never swapped in for it."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_farmer_world", ROOT / "scripts" / "build_farmer_world.py")
bfw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bfw)

BASE = """,,,,,All Type of Report (All Grades) for 01-Jan-2021 to 26-Oct-2026,,,,
State/UT,District,Market,Commodity Group,Commodity,Date,Arrival Quantity,Arrival Unit,Modal Price,Price Unit
Karnataka,Kolar,Kolar APMC,Vegetables,Tomato,25-10-2026,100.00,Metric Tonnes,1000.00,Rs./Quintal
Karnataka,Kolar,Bangarpet APMC,Vegetables,Tomato,25-10-2026,300.00,Metric Tonnes,2000.00,Rs./Quintal
Karnataka,Kolar,Kolar APMC,Vegetables,Tomato,26-10-2026,100.00,Metric Tonnes,1000.00,Rs./Quintal

Note:
"""

UPDATE = """,,,,All Type of Report (All Grades) for 26-Oct-2026 to 11-Nov-2026,,,,
State/UT,District,Commodity Group,Commodity,Date,Arrival Quantity,Arrival Unit,Modal Price,Price Unit
Karnataka,Kolar,Vegetables,Tomato,26-10-2026,150.00,Metric Tonnes,1200.00,Rs./Quintal
Karnataka,Kolar,Vegetables,Tomato,27-10-2026,90.00,Metric Tonnes,1100.00,Rs./Quintal

Note:
"""


@pytest.fixture()
def source_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(bfw.world, "SOURCE_DIR", tmp_path)
    (tmp_path / "district_report.csv").write_text(BASE, encoding="utf-8")
    return tmp_path


def test_export_stamp_orders_by_export_time_not_name():
    early = Path("All_Type_of_Report_(All_Grades)_28-10-2026_08-05-01_PM.csv")
    late = Path("All_Type_of_Report_(All_Grades)_13-11-2026_06-27-07_PM.csv")
    assert bfw._export_stamp(late) > bfw._export_stamp(early)  # the names sort the other way


def test_base_alone_keeps_market_rows_and_weights_district_price(source_dir):
    district, market, files = bfw._read_all_history()
    assert files == ["district_report.csv"]
    assert len(market) == 3
    d25 = district[district["date"] == "2026-10-25"].iloc[0]
    assert d25["price"] == pytest.approx((100 * 1000 + 300 * 2000) / 400)


def test_district_update_extends_history_and_wins_on_overlap(source_dir):
    upd = source_dir / "All_Type_of_Report_(All_Grades)_13-11-2026_06-27-07_PM.csv"
    upd.write_text(UPDATE, encoding="utf-8")
    bfw.stage_sources(None, None, [upd])
    district, market, files = bfw._read_all_history()

    assert files == ["district_report.csv", "district_report_update_20261113T182707.csv"]
    assert sorted(district["date"].dt.strftime("%Y-%m-%d")) == ["2026-10-25", "2026-10-26", "2026-10-27"]
    overlap = district[district["date"] == "2026-10-26"].iloc[0]
    assert overlap["price"] == 1200.0 and overlap["arrivals"] == 150.0  # the later export wins
    assert len(market) == 3  # a district-level update cannot invent market rows


PARTIAL_MARKETS = """,,,,,All Type of Report (All Grades) for 26-Oct-2026 to 11-Nov-2026,,,,
State/UT,District,Market,Commodity Group,Commodity,Date,Arrival Quantity,Arrival Unit,Modal Price,Price Unit
Karnataka,Kolar,Kolar APMC,Vegetables,Tomato,27-10-2026,10.00,Metric Tonnes,5000.00,Rs./Quintal
Karnataka,Kolar,Kolar APMC,Vegetables,Tomato,28-10-2026,20.00,Metric Tonnes,900.00,Rs./Quintal

Note:
"""


def test_partial_market_export_extends_markets_but_not_over_district_totals(source_dir):
    district_upd = source_dir / "All_Type_of_Report_(All_Grades)_13-11-2026_06-27-07_PM.csv"
    district_upd.write_text(UPDATE, encoding="utf-8")
    market_upd = source_dir / "All_Type_of_Report_(All_Grades)_13-11-2026_06-58-19_PM.csv"
    market_upd.write_text(PARTIAL_MARKETS, encoding="utf-8")
    bfw.stage_sources(None, None, [district_upd, market_upd])
    district, market, _ = bfw._read_all_history()

    by_day = district.set_index(district["date"].dt.strftime("%Y-%m-%d"))["price"]
    assert by_day["2026-10-27"] == 1100.0   # the full district total, not the one-mandi figure (5000)
    assert by_day["2026-10-28"] == 900.0    # no district row that day, so the market rows fill it
    assert sorted(market["date"].dt.strftime("%Y-%m-%d").unique())[-1] == "2026-10-28"

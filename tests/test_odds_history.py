import csv
import io
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from jarvis.odds_history import (HISTORY_POLICY, ArchivedQuote, archived_decision,
                                 features, parse_price, read_season, replay, write_report)
from jarvis.odds_lab import POLICY, Prices, Snapshot, analyze, example_snapshot


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    columns = list(rows[0])
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def match(home="Hemmalag", away="Bortalag", day="01/08/2024", home_score="2", away_score="0"):
    value = {"Div": "E0", "Date": day, "HomeTeam": home, "AwayTeam": away, "FTHG": home_score,
             "FTAG": away_score, "FTR": "H" if int(home_score) > int(away_score) else "A" if int(away_score) > int(home_score) else "D"}
    for book in ("B365", "BW", "IW", "WH"):
        for suffix, odds in zip(("H", "D", "A"), ("2.5" if book == "B365" else "2.0", "3.4", "3.6")):
            value[book + "C" + suffix] = odds
    return value


def test_archived_math_matches_live_math_without_fabricating_timestamps():
    at = datetime(2026, 11, 3, tzinfo=timezone.utc)
    snapshot = Snapshot.model_validate(example_snapshot(at))
    quotes = [ArchivedQuote(book=q.book, odds=q.odds) for q in snapshot.quotes]
    past, live = archived_decision(quotes, 100000), analyze(snapshot, at, 100000)
    for key in ("selected", "book", "outcome", "paper_odds", "edge_bp", "reference_books"):
        assert past[key] == live[key]
    assert past["quote_timestamps_verified"] is False
    assert past["availability_verified"] is False
    assert "captured_at" not in past and "updated_at" not in past


def test_wins_losses_cost_cut_and_capital_are_integer_and_include_all_rows():
    rows = [match(), match(home="Annat lag", day="02/08/2024", home_score="0", away_score="1")]
    report = replay([("test", csv_bytes(rows))])
    assert report["total"]["matches"] == report["total"]["signals"] == 2
    assert report["total"]["wins"] == report["total"]["losses"] == 1
    assert report["total"]["profit_ore"] == 475
    assert report["final_bankroll_ore"] == 100475
    assert report["max_drawdown_ore"] == 1000
    assert report["total"]["staked_ore"] == 2000
    assert report["allows_real_money"] is False


def test_choices_do_not_depend_on_the_result():
    first, second = match(), match(home_score="0", away_score="5")
    report1, report2 = replay([("test", csv_bytes([first]))]), replay([("test", csv_bytes([second]))])
    assert report1["ledger"][0]["decision"] == report2["ledger"][0]["decision"]
    assert report1["total"]["profit_ore"] > 0 > report2["total"]["profit_ore"]


def test_results_of_same_day_cannot_fund_extra_signals():
    rows = [match(home=f"Hemmalag {i:03}", away=f"Bortalag {i:03}") for i in range(101)]
    report = replay([("test", csv_bytes(rows))])
    assert report["total"]["signals"] == 100
    assert report["total"]["abstentions"] == 1
    assert "Låtsaskapitalet" in report["ledger"][-1]["decision"]["reason"]


def test_missing_prices_abstain_and_aggregates_and_pinnacle_are_excluded():
    row = match()
    row["WHCH"] = ""
    for prefix in ("Max", "Avg", "PS"):
        for suffix in ("H", "D", "A"):
            row[prefix + "C" + suffix] = "3.0"
    report = replay([("test", csv_bytes([row]))])
    assert report["total"]["signals"] == 0
    assert report["total"]["abstentions"] == 1
    checks = report["ledger"][0]["decision"]["checks"]
    assert len(checks) == 3
    assert all(c["book"] not in {"book_ps", "book_avg", "book_max"} for c in checks)
    assert report["ledger"][0]["quote_issues"] == [{"book": "WH", "reason": "missing_or_invalid_prices"}]


def test_no_fallback_to_preclosing_prices_or_fake_complete_books():
    row = match()
    value = {k.replace("C", "") if k.endswith(("CH", "CD", "CA")) else k: v for k, v in row.items()}
    report = replay([("test", csv_bytes([value]))])
    assert report["total"]["signals"] == 0
    assert report["quality"][0]["available_individual_closing_books"] == []


@pytest.mark.parametrize("bad", ["", "NaN", "Infinity", "1", "0", "1000", "2.12345", "secret"])
def test_invalid_prices_are_not_coerced(bad):
    with pytest.raises(ValueError):
        parse_price(bad)


def test_missing_schema_duplicate_rows_and_inconsistent_results_are_visible():
    with pytest.raises(ValueError, match="obligatoriska"):
        read_season(b"HomeTeam,AwayTeam\nX,Y\n", "test")
    with pytest.raises(ValueError, match="Dublett"):
        replay([("test", csv_bytes([match(), match()]))])
    row = match()
    row["FTR"] = "A"
    report = replay([("test", csv_bytes([row]))])
    assert report["total"]["matches"] == 0
    assert len(report["quality"][0]["excluded_rows"]) == 1


def test_full_ledger_and_html_are_local_escaped_and_not_overwritten(tmp_path):
    row = match(home='<img src=x onerror="alert(1)">')
    report = replay([("test", csv_bytes([row]))])
    output = tmp_path / "report"
    write_report(report, output)
    assert (output / "resultat.json").exists()
    assert (output / "alla-matcher.csv").exists()
    assert "<script" not in (output / "rapport.html").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_report(report, output)


def test_input_order_does_not_change_report_and_no_reset_between_seasons():
    rows = [match(), match(home="Annat", day="02/08/2024", home_score="0", away_score="1")]
    first = replay([("test", csv_bytes(rows))])
    reverse = replay([("test", csv_bytes(list(reversed(rows))))])
    assert first["total"] == reverse["total"]
    combined = replay([("a", csv_bytes([rows[0]])), ("b", csv_bytes([rows[1]]))])
    assert combined["final_bankroll_ore"] == first["final_bankroll_ore"]
    assert len(combined["seasons"]) == 2

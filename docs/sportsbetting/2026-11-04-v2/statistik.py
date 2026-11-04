"""Lokala kontrollberäkningar för förstudien. Inga nätverk eller driftändringar."""
from decimal import Decimal
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
from statistics import median, stdev
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from jarvis.odds_history import read_season
from jarvis.odds_lab import normalize_prices


def main():
    report_path = ROOT / "docs/odds-reports/2026-11-03-epl-paper-v1/resultat.json"
    raw = report_path.read_bytes()
    report = json.loads(raw)
    selected = {row["id"]: row for row in report["ledger"] if row["decision"]["selected"]}
    sums, selected_sums = [], []
    inputs = {str(report_path.relative_to(ROOT)): sha256(raw).hexdigest()}
    for season, filename in (("2024/2025", "2425-E0.csv"), ("2025/2026", "2526-E0.csv")):
        path = ROOT / "data/odds-history/2026-11-03-epl-paper-v1" / filename
        source = path.read_bytes()
        inputs[str(path.relative_to(ROOT))] = sha256(source).hexdigest()
        matches, _ = read_season(source, season)
        for match in matches:
            valid = []
            for quote in match["quotes"]:
                probabilities, total = normalize_prices(quote.odds)
                if Decimal("0.95") <= total <= Decimal("1.25"):
                    valid.append((quote.book, probabilities))
            if len(valid) < 4:
                continue
            for book, _ in valid:
                references = [p for name, p in valid if name != book]
                total = sum(median(p[outcome] for p in references) for outcome in ("home", "draw", "away"))
                sums.append(total)
                if match["id"] in selected and book == selected[match["id"]]["decision"]["book"]:
                    selected_sums.append(total)

    def describe(values):
        return {
            "count": len(values),
            "deviation_from_one_above_1e_12": sum(abs(value - 1) > Decimal("1e-12") for value in values),
            "minimum_sum_decimal": str(min(values)),
            "maximum_sum_decimal": str(max(values)),
        }

    power = []
    for edge in (0.01, 0.02, 0.05):
        count = ceil(((1.6448536269514722 + 0.8416212335729143) / edge) ** 2)
        power.append({"hypothetical_edge": edge, "iid_sigma_one_n": count,
                      "seasons_at_38": count / 38, "seasons_at_380": count / 380})
    result = {
        "version": "statistik-forstudie-v2-2026-11-04",
        "evidence": "Körning mot lokala historikfiler; ingen ny strategi eller ekonomisk återspelning.",
        "input_sha256": inputs,
        "all_target_reference_combinations": describe(sums),
        "historically_selected_target_reference_combinations": describe(selected_sums),
        "historical_selected_sample_return_standard_deviation": stdev(row["profit_ore"] / 1000 for row in selected.values()),
        "power_illustration": power,
        "power_assumptions": {"one_sided_alpha": 0.05, "power": 0.8, "sigma": 1,
                              "formula": "ceil(((1.6448536269514722+0.8416212335729143)*sigma/edge)**2)",
                              "limitation": "Oberoende normalapproximation, ej garanterad provstorlek eller verklig fördel."},
        "paid_calls": 0, "real_bets": 0,
    }
    for code_name in ("backend/jarvis/odds_lab.py", "backend/jarvis/odds_history.py"):
        result["input_sha256"][code_name] = sha256((ROOT / code_name).read_bytes()).hexdigest()
    destination = HERE / "statistik.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()

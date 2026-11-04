r"""Lokal kontroll av förstudien. Inga nätverk, databaser, .env eller betalda anrop.

Kör från projektroten: .\.venv\Scripts\python.exe docs/sportsbetting/2026-11-04-v2/kontroll.py audit
baseline används en gång före leveransen; verify jämför dess skyddade filer.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def protected():
    paths = []
    for folder in ("backend", "frontend/src", "frontend/e2e", "tests", "scripts", "docs", "data/odds-history"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and HERE not in path.parents and "__pycache__" not in path.parts:
                paths.append(path)
    for name in ("AGENTS.md", "README.md", "requirements.lock", "frontend/package.json", "frontend/pnpm-lock.yaml"):
        if (ROOT / name).exists():
            paths.append(ROOT / name)
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(paths))}


def baseline():
    path = HERE / "skyddade-filer.json"
    if path.exists():
        raise ValueError("Baslinjen får inte skrivas över.")
    save(path.name, {"scope": "Källkod, tester, tidigare dokument och oddsarkiv; inga credentials eller drift-DB lästa.", "files": protected()})
    print("Baslinje sparad.")


def verify():
    before = json.loads((HERE / "skyddade-filer.json").read_text(encoding="utf-8"))["files"]
    after = protected()
    changed = [p for p, value in before.items() if after.get(p) != value]
    added = sorted(set(after) - set(before))
    result = {"checked_files": len(before), "changed_or_deleted": changed, "added_outside_study": added,
              "passed": not changed and not added,
              "limit": "Byteidentitet, inte bevis på metodgodkännande. Driftdata och hemliga inställningar ingår inte."}
    save("integritetskontroll.json", result)
    assert result["passed"], result
    print(json.dumps(result, ensure_ascii=False))


def audit():
    # Ren oddsberäkning; api/config/DB och nedladdningsscript importeras aldrig.
    sys.path.insert(0, str(ROOT / "backend"))
    from jarvis.odds_history import HISTORY_POLICY, replay
    from jarvis.odds_lab import digest
    archive = ROOT / "data/odds-history/2026-11-03-epl-paper-v1"
    folder = ROOT / "docs/odds-reports/2026-11-03-epl-paper-v1"
    frozen_raw = (archive / "protokoll.json").read_bytes()
    assert sha(archive / "protokoll.json") == (archive / "protokoll.sha256").read_text().strip()
    frozen = json.loads(frozen_raw)
    assert frozen["policy"] == HISTORY_POLICY and frozen["policy_hash"] == digest(HISTORY_POLICY)
    for name, value in frozen["code_hashes"].items():
        assert sha(ROOT / name) == value, name
    assert sha(archive / "hamtning.json") == (archive / "hamtning.sha256").read_text().strip()
    receipts = json.loads((archive / "hamtning.json").read_text(encoding="utf-8"))["sources"]
    inputs = []
    for receipt in receipts:
        path = archive / receipt["filename"]
        assert sha(path) == receipt["sha256"] and path.stat().st_size == receipt["bytes"]
        inputs.append((receipt["season"], path.read_bytes()))
    original = json.loads((folder / "resultat.json").read_text(encoding="utf-8"))
    recalculated = replay(inputs)
    keys = ("total", "seasons", "quality", "ledger", "initial_bankroll_ore", "final_bankroll_ore", "max_drawdown_ore", "uncertainty", "policy_hash")
    equal = {key: recalculated[key] == original[key] for key in keys}
    assert all(equal.values()), equal
    signals = [r for r in original["ledger"] if r["decision"]["selected"]]
    summary = {"evidence": "Verifierat genom helt lokal återspelning av frysta CSV-byte med oförändrad kod och policy.",
               "comparison": equal, "total": recalculated["total"], "seasons": recalculated["seasons"],
               "policy_hash": frozen["policy_hash"], "protocol_sha256": sha(archive / "protokoll.json"),
               "final_bankroll_ore": recalculated["final_bankroll_ore"], "max_drawdown_ore": recalculated["max_drawdown_ore"],
               "uncertainty": recalculated["uncertainty"], "maximum_selected_quoted_odds_x10000": max(r["decision"]["quoted_odds"] for r in signals),
               "minimum_selected_quoted_odds_x10000": min(r["decision"]["quoted_odds"] for r in signals),
               "paid_calls": 0, "network_calls": 0, "database_reads_or_writes": 0,
               "limitations": ["Ingen samtidig historisk oddstillgänglighet verifieras.", "Återspelningen verifierar aritmetik och byte, inte ekonomisk fördel eller framtida frekvens.", "Gamla två säsonger förblir sedda utvecklingsdata."]}
    save("baslinjekontroll.json", summary)
    print(json.dumps({k: summary[k] for k in ("total", "comparison", "final_bankroll_ore", "uncertainty")}, ensure_ascii=False))


def manifest():
    files = {p.name: sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "leveransmanifest.json"}
    save("leveransmanifest.json", {"version": "forstudie-2.0-2026-11-04", "status": "Beslutsunderlag, inget körningstillstånd.", "sha256": files})
    print(f"Leveransmanifest med {len(files)} filer.")


if __name__ == "__main__":
    {"baseline": baseline, "verify": verify, "audit": audit, "manifest": manifest}[sys.argv[1]]()

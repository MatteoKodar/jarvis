"""Engångsanalys för privat bruk: frys -> hämta två fria filer -> räkna offline.

Ingen server, ägardatabas, .env, bookmakerinloggning eller betald integration används.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from jarvis.odds_lab import canonical, digest
from jarvis.odds_history import HISTORY_POLICY, SOURCES, replay, write_report

CODE_FILES = ("backend/jarvis/odds_lab.py", "backend/jarvis/odds_history.py", "scripts/odds_backtest.py", "tests/test_odds_history.py")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def code_hashes():
    return {name: sha((ROOT / name).read_bytes()) for name in CODE_FILES}


def data_folder(path):
    result = Path(path).resolve()
    if not result.is_relative_to((ROOT / "data").resolve()) or result == (ROOT / "data").resolve():
        raise ValueError("Analysens data ska sparas i en ny undermapp till projektets data-mapp.")
    return result


def freeze(folder):
    folder.mkdir(parents=True, exist_ok=False)
    protocol = {"created_utc": datetime.now(timezone.utc).isoformat(), "policy": HISTORY_POLICY,
                "policy_hash": digest(HISTORY_POLICY), "code_hashes": code_hashes(),
                "status": "Lokalt fryst före hämtning av matchfiler; ingen extern förregistrering eller tillåtelse till riktiga spel."}
    (folder / "protokoll.json").write_text(canonical(protocol) + "\n", encoding="utf-8")
    (folder / "protokoll.sha256").write_text(sha((folder / "protokoll.json").read_bytes()) + "\n", encoding="ascii")
    return {"protocol": str(folder / "protokoll.json"), "sha256": sha((folder / "protokoll.json").read_bytes())}


def verify(folder):
    raw = (folder / "protokoll.json").read_bytes()
    if sha(raw) != (folder / "protokoll.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Protokollets kontrollsumma stämmer inte.")
    protocol = json.loads(raw)
    if protocol["policy_hash"] != digest(HISTORY_POLICY) or protocol["policy"] != HISTORY_POLICY or protocol["code_hashes"] != code_hashes():
        raise ValueError("Kod eller regler har ändrats sedan frysningen. Tidigare frysning får inte skrivas över.")
    return protocol


def download(folder):
    verify(folder)
    if (folder / "hamtning.json").exists() or any((folder / source["filename"]).exists() for source in SOURCES):
        raise ValueError("Filer finns redan. Ingen ny hämtning eller överskrivning görs.")
    receipts = []
    for source in SOURCES:
        # Två fasta offentliga CSV-länkar, ingen valfri URL eller credential.
        request = urllib.request.Request(source["url"], headers={"User-Agent": "JarvisPrivatePaperStudy/1.0", "Accept": "text/csv,text/plain"})
        with urllib.request.urlopen(request, timeout=30) as response:
            location = urlsplit(response.url)
            expected = urlsplit(source["url"])
            if location.scheme != "https" or location.hostname not in {"football-data.co.uk", "www.football-data.co.uk"} or location.path != expected.path or location.query:
                raise ValueError("Oväntad slutadress för datasetet.")
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000 or response.status != 200:
                raise ValueError("Datasetet är för stort eller hämtningen misslyckades.")
        if not raw.startswith((b"Div,", b"\xef\xbb\xbfDiv,")):
            raise ValueError("Svaret är inte förväntad fotbolls-CSV.")
        (folder / source["filename"]).write_bytes(raw)
        receipts.append({**source, "bytes": len(raw), "sha256": sha(raw), "downloaded_utc": datetime.now(timezone.utc).isoformat()})
    value = {"sources": receipts, "cost_ore": 0, "paid_calls": 0, "real_bets": 0}
    (folder / "hamtning.json").write_text(canonical(value) + "\n", encoding="utf-8")
    (folder / "hamtning.sha256").write_text(sha((folder / "hamtning.json").read_bytes()) + "\n", encoding="ascii")
    return value


def run(folder, report_path):
    protocol = verify(folder)
    report_folder = Path(report_path).resolve()
    if not report_folder.is_relative_to((ROOT / "docs/odds-reports").resolve()):
        raise ValueError("Rapporten ska ligga under docs/odds-reports/.")
    receipt_raw = (folder / "hamtning.json").read_bytes()
    if sha(receipt_raw) != (folder / "hamtning.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Hämtningsmanifestets kontrollsumma stämmer inte.")
    receipts = json.loads(receipt_raw)["sources"]
    if len(receipts) != len(SOURCES):
        raise ValueError("Ofullständigt underlag; inga säsonger får tyst väljas bort.")
    inputs = []
    for source, receipt in zip(SOURCES, receipts):
        if any(receipt.get(key) != source[key] for key in ("season", "filename", "url")):
            raise ValueError("Källmanifestet matchar inte det förhandsvalda underlaget.")
        raw = (folder / source["filename"]).read_bytes()
        if sha(raw) != receipt["sha256"] or len(raw) != receipt["bytes"]:
            raise ValueError("Datasetets byte matchar inte hämtningsmanifestet.")
        inputs.append((source["season"], raw))
    report = replay(inputs)
    report.update(protocol=protocol, protocol_file_sha256=sha((folder / "protokoll.json").read_bytes()), sources=receipts,
                  report_created_utc=datetime.now(timezone.utc).isoformat())
    write_report(report, report_folder)
    return {"report": str(report_folder / "rapport.html"), "total": report["total"], "seasons": report["seasons"],
            "quality": report["quality"], "final_bankroll_ore": report["final_bankroll_ore"],
            "max_drawdown_ore": report["max_drawdown_ore"], "uncertainty": report["uncertainty"],
            "sources": receipts, "real_bets": 0, "paid_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("freeze", "download", "run"))
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--report-dir")
    args = parser.parse_args()
    folder = data_folder(args.data_dir)
    if args.stage == "freeze":
        value = freeze(folder)
    elif args.stage == "download":
        value = download(folder)
    else:
        if not args.report_dir:
            parser.error("run kräver --report-dir")
        value = run(folder, args.report_dir)
    print(json.dumps(value, ensure_ascii=False, indent=2))

"""Avgränsad historisk återspelning. Inga nätverk, DB-skrivningar eller hittade tidsstämplar."""
import csv
import html
import io
import random
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from itertools import groupby
from pathlib import Path

from pydantic import Field

from .odds_lab import POLICY, Prices, Strict, digest, normalize_prices, select_price_signal

HISTORY_VERSION = "epl-archive-paper-v1"
# Låst före filhämtning. Namngivna firmor; aldrig Max/Avg eller börspriser.
BOOKS = ("1XB", "B365", "BF", "BFD", "BMGM", "BV", "BW", "CL", "GB", "IW", "LB", "PP", "SB", "SJ", "SK", "SO", "SY", "VC", "WH")
SOURCES = (
    {"season": "2024/2025", "filename": "2425-E0.csv", "url": "https://football-data.co.uk/mmz4281/2425/E0.csv"},
    {"season": "2025/2026", "filename": "2526-E0.csv", "url": "https://football-data.co.uk/mmz4281/2526/E0.csv"},
)
HISTORY_POLICY = {
    "version": HISTORY_VERSION, "league": "E0", "sources": list(SOURCES),
    "eligible_books": list(BOOKS), "price_columns": "Endast individuella closing-odds: prefix + C + H/D/A.",
    "excluded": "Pinnacle utesluts på grund av leverantörens varning; Max/Avg och börser utesluts alltid.",
    "selection_policy": POLICY,
    "timing": "Historiskt arkiv, ej framåtriktat test. Offerttid och samtidighet är okända; ingen färskhet fabriceras.",
    "capital": "1 000 SEK en gång; samma saldo över båda säsongerna. Fast insats 10 SEK. Ingen påfyllning.",
    "settlement_order": "Alla beslut inom samma matchdatum låses innan någon av dagens utbetalningar används.",
    "invalid_rows": "Saknad/ogiltig matchidentitet, datum eller slutresultat loggas. Saknade/ogiltiga offerter loggas per firma.",
    "cost_ore": 0, "cost_basis": "Endast kostnadsfria filhämtningar; inga köp, API- eller modellanrop. Ingen påstådd verklig spelvinst.",
    "bootstrap": {"unit": "matchdatum", "samples": 5000, "seed": 20261103, "interval": "2.5–97.5-percentil av ROI, illustrativ osäkerhet, inte en garanti"},
    "tuning": "Inga parameterändringar, säsongsbyten eller bortval efter utfall.",
    "real_money_enabled": False,
}


class ArchivedQuote(Strict):
    book: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    odds: Prices


def parse_price(value):
    try:
        parsed = Decimal(value)
        scaled = parsed * 10000
        if not parsed.is_finite() or scaled != scaled.to_integral_value() or not 10001 <= scaled <= 1000000:
            raise ValueError()
        return int(scaled)
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError("Saknat eller ogiltigt decimalodds.") from None


def features(row, columns):
    """Funktionen får inga slutresultat. Saknade firmor blir inga påhittade offerter."""
    quotes, issues = [], []
    for book in BOOKS:
        names = [book + "C" + suffix for suffix in ("H", "D", "A")]
        if not all(name in columns for name in names):
            continue
        try:
            prices = Prices(**{key: parse_price(row.get(name, "")) for key, name in zip(("home", "draw", "away"), names)})
        except ValueError:
            issues.append({"book": book, "reason": "missing_or_invalid_prices"})
            continue
        quotes.append(ArchivedQuote(book="book_" + book.lower(), odds=prices))
    return quotes, issues


def archived_decision(quotes, available_ore):
    valid, checks = [], []
    for quote in quotes:
        probabilities, total = normalize_prices(quote.odds)
        accepted = Decimal("0.95") <= total <= Decimal("1.25")
        checks.append({"book": quote.book, "accepted": accepted, "overround_bp": int(total * 10000),
                       "reason": None if accepted else "Avvikande marginal; offerten behöver kontrolleras."})
        if accepted:
            valid.append((quote, probabilities))
    decision = select_price_signal(valid, available_ore, checks)
    return {**decision, "quote_timestamps_verified": False, "simultaneous_prices_verified": False,
            "availability_verified": False, "historical_only": True}


def read_season(content, season):
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or [])
    required = {"Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
    if not required <= columns:
        raise ValueError("CSV saknar obligatoriska match- och resultatkolumner.")
    matches, excluded, seen = [], [], set()
    available_books = [book for book in BOOKS if all(book + "C" + suffix in columns for suffix in ("H", "D", "A"))]
    for row_number, row in enumerate(reader, start=2):
        if not any(row.values()):
            continue
        try:
            raw_date = row["Date"].strip()
            match_date = datetime.strptime(raw_date, "%d/%m/%Y" if len(raw_date) == 10 else "%d/%m/%y").date().isoformat()
            home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
            if row["Div"] != "E0" or not home or not away or home.casefold() == away.casefold():
                raise ValueError("Ogiltig matchidentitet eller liga.")
            home_score, away_score = int(row["FTHG"]), int(row["FTAG"])
            if not (0 <= home_score <= 100 and 0 <= away_score <= 100):
                raise ValueError("Ogiltigt resultat.")
            outcome = "H" if home_score > away_score else "A" if away_score > home_score else "D"
            if row["FTR"] != outcome:
                raise ValueError("Resultatkolumnerna motsäger varandra.")
            key = digest([match_date, sorted([home.casefold(), away.casefold()])])
            if key in seen:
                raise ValueError("Dublett; analysen avbryts i stället för att välja en rad.")
            seen.add(key)
            # Skilj prisunderlaget från resultatet innan någon signal väljs.
            price_fields = {name: value for name, value in row.items() if name in {book + "C" + s for book in BOOKS for s in ("H", "D", "A")}}
            quotes, issues = features(price_fields, columns)
            matches.append({"id": key, "season": season, "row_number": row_number, "date": match_date,
                            "home": home, "away": away, "quotes": quotes, "quote_issues": issues,
                            "result": {"home_score": home_score, "away_score": away_score, "outcome": {"H": "home", "D": "draw", "A": "away"}[outcome]}})
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            if "Dublett" in str(exc):
                raise
            excluded.append({"season": season, "row_number": row_number, "reason": str(exc)})
    return matches, {"season": season, "rows": len(matches) + len(excluded), "valid_matches": len(matches),
                     "excluded_rows": excluded, "available_individual_closing_books": available_books}


def _totals(rows):
    selected = [row for row in rows if row["decision"]["selected"]]
    stake = len(selected) * POLICY["stake_ore"]
    profit = sum(row["profit_ore"] for row in selected)
    return {"matches": len(rows), "signals": len(selected), "abstentions": len(rows) - len(selected),
            "wins": sum(row["won"] is True for row in selected), "losses": sum(row["won"] is False for row in selected),
            "staked_ore": stake, "profit_ore": profit, "roi_bp": profit * 10000 // stake if stake else None}


def uncertainty(rows):
    days = defaultdict(lambda: [0, 0])
    for row in rows:
        if row["decision"]["selected"]:
            days[row["date"]][0] += row["profit_ore"]
            days[row["date"]][1] += POLICY["stake_ore"]
    if len(days) < 2:
        return {"unit": "matchdatum", "days_with_signals": len(days), "roi_interval_bp": None}
    policy = HISTORY_POLICY["bootstrap"]
    rng, values, estimates = random.Random(policy["seed"]), list(days.values()), []
    for _ in range(policy["samples"]):
        draw = rng.choices(values, k=len(values))
        estimates.append(sum(x[0] for x in draw) * 10000 // sum(x[1] for x in draw))
    estimates.sort()
    return {"unit": "matchdatum", "days_with_signals": len(days), "samples": policy["samples"], "seed": policy["seed"],
            "roi_interval_bp": [estimates[int(len(estimates) * .025)], estimates[min(len(estimates) - 1, int(len(estimates) * .975))]],
            "limitation": "Illustrativt 95-procentigt dagklustrat bootstrapintervall. Fångar inte felaktiga/asynkrona odds, urvalsfel eller alla tidsberoenden."}


def replay(seasons):
    matches, quality = [], []
    for season, content in seasons:
        current, check = read_season(content, season)
        matches.extend(current)
        quality.append(check)
    matches.sort(key=lambda m: (m["date"], m["home"].casefold(), m["away"].casefold(), m["id"]))
    if len({m["id"] for m in matches}) != len(matches):
        raise ValueError("Samma match förekommer i flera filer.")
    balance, peak, drawdown = POLICY["initial_bankroll_ore"], POLICY["initial_bankroll_ore"], 0
    ledger = []
    for _, day_matches in groupby(matches, key=lambda m: m["date"]):
        group, reserved, prepared = list(day_matches), 0, []
        for match in group:
            # Inget av dagens resultat används för beslut eller återinvestering.
            decision = archived_decision(match["quotes"], balance - reserved)
            if decision["selected"]:
                reserved += POLICY["stake_ore"]
            prepared.append((match, decision))
        for match, decision in prepared:
            won, profit, payout = None, 0, 0
            if decision["selected"]:
                won = decision["outcome"] == match["result"]["outcome"]
                payout = POLICY["stake_ore"] * decision["paper_odds"] // 10000 if won else 0
                profit = payout - POLICY["stake_ore"]
                balance += profit
                peak = max(peak, balance)
                drawdown = max(drawdown, peak - balance)
            ledger.append({k: match[k] for k in ("id", "season", "row_number", "date", "home", "away", "quote_issues", "result")}
                          | {"decision": decision, "won": won, "profit_ore": profit, "payout_ore": payout, "balance_ore": balance})
    total = _totals(ledger)
    reasons = Counter(row["decision"]["reason"] for row in ledger if not row["decision"]["selected"])
    return {"version": HISTORY_VERSION, "policy_hash": digest(HISTORY_POLICY), "policy": HISTORY_POLICY,
            "quality": quality, "total": total,
            "seasons": [{"season": source[0], **_totals([r for r in ledger if r["season"] == source[0]])} for source in seasons],
            "initial_bankroll_ore": POLICY["initial_bankroll_ore"], "final_bankroll_ore": balance,
            "max_drawdown_ore": drawdown, "reported_data_cost_ore": 0, "abstention_reasons": dict(reasons),
            "uncertainty": uncertainty(ledger), "ledger": ledger,
            "real_bets": 0, "paid_calls": 0, "allows_real_money": False,
            "conclusion": "Historiskt räkneutfall, inte verifierad verklig lönsamhet. Framåtriktat test och kontrollerad oddstillgänglighet återstår."}


def write_report(report, folder):
    """Lokal svensk HTML och fullständig CSV; inga externa resurser i rapporten."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    from .odds_lab import canonical
    (folder / "resultat.json").write_text(canonical(report) + "\n", encoding="utf-8")
    with (folder / "alla-matcher.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["season", "date", "home", "away", "selected", "book", "outcome", "quoted_odds", "paper_odds", "edge_bp", "won", "profit_ore", "balance_ore", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["ledger"]:
            writer.writerow({k: row.get(k, row["decision"].get(k, "")) for k in fields})
    money = lambda amount: f"{amount / 100:,.2f}".replace(",", " ").replace(".", ",") + " kr"
    percent = lambda bp: "saknas" if bp is None else f"{bp / 100:.2f}".replace(".", ",") + " %"
    total = report["total"]
    season_rows = "".join(f"<tr><td>{html.escape(s['season'])}</td><td>{s['matches']}</td><td>{s['signals']}</td><td>{s['wins']} / {s['losses']}</td><td>{money(s['profit_ore'])}</td><td>{percent(s['roi_bp'])}</td></tr>" for s in report["seasons"])
    interval = report["uncertainty"]["roi_interval_bp"]
    uncertainty_text = "För få signaldagar för intervall." if interval is None else "Illustrativt 95-procentigt bootstrapintervall för ROI: " + percent(interval[0]) + " till " + percent(interval[1]) + "."
    quality_text = "".join(f"<li>{html.escape(q['season'])}: {q['valid_matches']} giltiga matcher, {len(q['excluded_rows'])} avvisade rader. Closing-kolumner: {html.escape(', '.join(q['available_individual_closing_books']))}.</li>" for q in report["quality"])
    page = f'''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JARVIS – historiskt fotbollstest</title>
<style>body{{background:#0b1421;color:#e6eef5;font:16px/1.7 system-ui;margin:0}}main{{max-width:980px;margin:auto;padding:40px 22px}}h1{{line-height:1.2}}h1 em{{color:#8de2c9;font-style:normal}}p,li{{color:#b3c2d3}}.badge{{color:#ebca88;border:1px solid #77613e;border-radius:6px;padding:7px 12px;display:inline-block;font-size:12px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:28px 0}}article{{padding:20px;background:#132234;border:1px solid #2b4054;border-radius:9px}}article strong{{display:block;font-size:27px}}article small{{color:#9db1c5}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:12px 8px;text-align:left;border-bottom:1px solid #2a3d51}}.scroll{{overflow:auto}}a{{color:#8de2c9}}code{{overflow-wrap:anywhere}}footer{{border-top:1px solid #2b4054;margin-top:30px;font-size:12px;color:#9db1c5}}</style>
<main><span class="badge">HISTORISKT TEST · LÅTSASINSATSER · INGA RIKTIGA SPEL</span><h1>Vad hade reglerna gett?<br><em>Även förluster räknas.</em></h1>
<p>Premier League 2024/2025 och 2025/2026. Förhandslåst prisjämförelse, samma regler i båda säsongerna. Ingen parameteroptimering efter resultaten.</p>
<section class="cards"><article><small>SIMULERAT RESULTAT</small><strong>{money(total['profit_ore'])}</strong><small>Efter 1 % avdrag på decimaloddsen; datakostnad 0 kr.</small></article><article><small>LÅTSASSALDO</small><strong>{money(report['final_bankroll_ore'])}</strong><small>Start 1 000 kr, ingen påfyllning.</small></article><article><small>SIGNALER / MATCHER</small><strong>{total['signals']} / {total['matches']}</strong><small>Fast insats 10 kr. {total['abstentions']} avståenden.</small></article><article><small>AVKASTNING PÅ INSATS</small><strong>{percent(total['roi_bp'])}</strong><small>{money(total['staked_ore'])} simulerat omsatt.</small></article></section>
<h2>Resultat per säsong</h2><div class="scroll"><table><thead><tr><th>Säsong</th><th>Matcher</th><th>Signaler</th><th>Vinster / förluster</th><th>Resultat</th><th>ROI</th></tr></thead><tbody>{season_rows}</tbody></table></div>
<p>Största realiserade nedgång i redovisningsordningen: {money(report['max_drawdown_ore'])}. Alla dagens val görs innan dagens resultat används.</p><h2>Osäkerhet</h2><p>{html.escape(uncertainty_text)} Detta fångar inte felaktiga eller asynkrona odds och bevisar inte framtida lönsamhet.</p>
<h2>Datakontroll</h2><ul>{quality_text}</ul><p>Individuella closing-kolumner används. Max/Avg, börser och Pinnacle används inte. Målbolaget ingår aldrig i sin egen referens.</p>
<p><strong>Begränsning:</strong> arkivet saknar verifierade tidsstämplar per offert. Ingen färskhet har fabricerats. Vi vet inte att alla odds fanns samtidigt eller att en insats hade accepterats.</p>
<h2>Spårbarhet och filer</h2><p><a href="alla-matcher.csv">Alla matcher och avståenden (CSV)</a> · <a href="resultat.json">Fullständig rapport (JSON)</a></p><p><a href="https://football-data.co.uk/data.php">Datakälla</a> · <a href="https://football-data.co.uk/notes.txt">Kolumndefinitioner</a></p><footer>Regelhash: <code>{report['policy_hash']}</code><br>Inga riktiga spel, betalda API-anrop eller insättningar. Ingen automatisk upplåsning av riktiga insatser.</footer></main></html>'''
    (folder / "rapport.html").write_text(page, encoding="utf-8")

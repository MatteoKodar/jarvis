"""Fristående förstudie: lokal aritmetik, inga nätverk eller databasanslutningar.

Kör med projektets Python från valfri katalog. Skriver endast ekonomi.json/ekonomi.md
i denna dokumentmapp. Penningbelopp i JSON är heltalsören; kontinuerliga omsättnings-
behov avrundas uppåt. Detta är scenarier, ingen skattning av framtida fördel.
"""
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / "docs/odds-reports/2026-11-03-epl-paper-v1"
D = Decimal


def ore(value):
    return int(D(str(value)).quantize(D(1), rounding=ROUND_HALF_UP))


def up(value):
    return int(D(str(value)).to_integral_value(rounding=ROUND_CEILING))


def expected_game_net(stake_ore, probability, odds, haircut=D(0), turnover_fee=D(0)):
    return D(stake_ore) * (D(probability) * D(odds) * (1 - haircut) - 1 - turnover_fee)


def required_turnover(goal_ore, fixed_cost_ore, edge):
    return D(goal_ore + fixed_cost_ore) / edge if edge > 0 else None


def check_formulas():
    # Förväntningar får delören; avrundning till öre sker vid presentation.
    assert expected_game_net(1000, D("0.52"), D(2)) == D(40)
    assert expected_game_net(1000, D("0.52"), D(2), D("0.01")) == D("29.6")
    assert expected_game_net(1000, D("0.52"), D(2), D("0.01"), D("0.002")) == D("27.6")
    raw_edge = D("0.52") * 2 - 1
    net_edge = (1 + raw_edge) * D("0.99") - 1 - D("0.002")
    assert 1000 * net_edge == expected_game_net(1000, D("0.52"), D(2), D("0.01"), D("0.002"))
    assert required_turnover(10000, 10000, D(0)) is None
    assert required_turnover(10000, 10000, D("-0.05")) is None
    turnover = required_turnover(10000, 0, D("0.03"))
    assert up(turnover) == 333334
    assert up(turnover / 1000) == 334
    assert D(333) * 1000 * D("0.03") < 10000 <= D(334) * 1000 * D("0.03")


def money(value):
    return f"{value / 100:,.2f}".replace(",", " ").replace(".", ",")


def verify_archive():
    path = ARCHIVE / "resultat.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report["ledger"]
    with (ARCHIVE / "alla-matcher.csv").open(encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(rows) == len(csv_rows) == 760
    wins, net, turnover, balance, counts = 0, 0, 0, 100000, Counter()
    daily = Counter()
    for row, exported in zip(rows, csv_rows):
        for key in ("season", "date", "home", "away"):
            assert row[key] == exported[key]
        dec = row["decision"]
        assert str(dec["selected"]) == exported["selected"]
        profit = 0
        if dec["selected"]:
            assert dec["stake_ore"] == 1000
            assert dec["paper_odds"] == dec["quoted_odds"] * 9900 // 10000
            result = row["result"]
            outcome = "home" if result["home_score"] > result["away_score"] else "away" if result["home_score"] < result["away_score"] else "draw"
            assert outcome == result["outcome"]
            won = dec["outcome"] == outcome
            payout = dec["stake_ore"] * dec["paper_odds"] // 10000 if won else 0
            profit = payout - dec["stake_ore"]
            assert row["payout_ore"] == payout and row["won"] == won
            wins += won
            turnover += dec["stake_ore"]
            counts[dec["outcome"]] += 1
            daily[row["date"]] += dec["stake_ore"]
        assert profit == row["profit_ore"] == int(exported["profit_ore"])
        net += profit
        balance += profit
        assert balance == row["balance_ore"] == int(exported["balance_ore"])
    assert net == report["total"]["profit_ore"] == -23659
    assert turnover == report["total"]["staked_ore"] == 76000
    assert wins == report["total"]["wins"] == 6
    assert balance == report["final_bankroll_ore"] == 76341
    assert sum(counts.values()) == report["total"]["signals"] == 76
    return {
        "evidens": "Verifierat genom lokal omräkning av avräkning och jämförelse JSON/CSV. Ingen ny strategikörning, inga tidsstämplar verifierade.",
        "matches": len(rows), "signals": sum(counts.values()), "wins": wins,
        "staked_ore": turnover, "profit_ore": net,
        "roi_bp_exact": str(D(net) / turnover * 10000),
        "roi_bp_report_floor": report["total"]["roi_bp"],
        "final_bankroll_ore": balance,
        "selected_outcomes": dict(counts),
        "largest_same_day_reservation_ore": max(daily.values()),
        "max_drawdown_report_ore": report["max_drawdown_ore"],
        "bootstrap_report_bp": report["uncertainty"]["roi_interval_bp"],
        "source_sha256": {name: hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest() for name in ("resultat.json", "alla-matcher.csv")},
        "seasons_report": report["seasons"],
    }


def calculate():
    check_formulas()
    # Net edge is an explicit assumption AFTER execution. d is used only to
    # recover the raw edge needed to achieve it; do not subtract d a second time.
    edges = [("negativ", -500), ("noll", 0), ("försiktig", 100), ("positiv", 300), ("optimistisk", 500)]
    scenarios = []
    goals = []
    for name, bp in edges:
        edge = D(bp) / 10000
        raw = (1 + edge) / D("0.99") - 1
        annual_game = ore(D(38) * 1000 * edge)
        scenarios.append({
            "name": name, "net_edge_bp_assumed": bp,
            "result_type": "Förväntade nettobelopp vid antagen edge; inget tak för realiserad slumpvinst eller förlust.",
            "raw_edge_bp_required_before_haircut": str(raw * 10000),
            "odds_haircut_bp_assumed": 100, "turnover_fee_bp_assumed": 0,
            "signals_per_season_reference": 38, "stake_ore": 1000,
            "season_game_net_ore": annual_game,
            "season_project_net_ore": annual_game - 100000,
            "season_economic_net_ore": annual_game - 500000,
            "calendar_year_game_net_ore": annual_game,
            "calendar_year_project_net_ore": annual_game - 120000,
            "calendar_year_economic_net_ore": annual_game - 600000,
            "zero_cost_game_net_at_380_signals_ore": ore(D(380) * 1000 * edge),
        })
        for period, months, frequency, capacity, targets in [
            ("aktiv_matchmånad", 1, D(38) / 10, D(380) / 10, [10000, 50000, 100000]),
            ("kalenderår", 12, D(38), D(380), [120000, 600000, 1200000]),
        ]:
            for target in targets:
                for basis, fixed in [("spelnetto", 0), ("projektnetto", months * 10000), ("ekonomiskt_netto", months * 50000)]:
                    need = required_turnover(target, fixed, edge)
                    needed_signals = up(need / 1000) if need is not None else None
                    goals.append({
                        "scenario": name, "net_edge_bp_assumed": bp,
                        "period": period, "net_goal_ore": target, "net_basis": basis,
                        "data_cost_ore": months * 10000, "ai_cost_ore": 0,
                        "other_cash_cost_ore": 0,
                        "work_hours_assumed": months * 2, "hourly_work_value_ore": 20000,
                        "work_cost_ore": months * 40000,
                        "fixed_paper_stake_ore": 1000,
                        "bound_10_open_at_fixed_stake_ore": 10000,
                        "bound_20_open_at_fixed_stake_ore": 20000,
                        "required_turnover_ore_ceiling": up(need) if need is not None else None,
                        "required_signals_at_10sek": needed_signals,
                        "reference_signals": str(frequency), "upper_match_capacity": str(capacity),
                        "fits_reference_volume": needed_signals <= frequency if needed_signals is not None else False,
                        "fits_one_bet_per_match_ceiling": needed_signals <= capacity if needed_signals is not None else False,
                        "algebraic_stake_at_reference_volume_ore_ceiling": up(need / frequency) if need is not None else None,
                        "algebraic_stake_at_max_match_volume_ore_ceiling": up(need / capacity) if need is not None else None,
                        "warning": "Algebraiska insatser är genomförbarhetsdiagnostik, INTE råd att höja insatsen. Månadstak är ett säsongsgenomsnitt, inget spelschema.",
                    })
    sensitivity = []
    for edge_bp in (100, 300, 500):
        for data_ore in (0, 10000, 30000):
            for ai_ore in (0, 5000):
                for work_ore in (0, 40000):
                    game = ore(D(38) * 1000 * D(edge_bp) / 10000)
                    sensitivity.append({"edge_bp": edge_bp, "annual_signals": 38, "stake_ore": 1000,
                                        "monthly_data_ore": data_ore, "monthly_ai_ore": ai_ore,
                                        "monthly_work_ore": work_ore,
                                        "annual_game_net_ore": game,
                                        "annual_project_net_ore": game - 12 * (data_ore + ai_ore),
                                        "annual_economic_net_ore": game - 12 * (data_ore + ai_ore + work_ore)})
    capital = [{"open_bets": n, "stake_ore": 1000, "bound_ore": n * 1000,
                "paper_capital_ore": 100000, "unbound_before_losses_ore": 100000 - n * 1000,
                "interpretation": "Obesvarade resultat behåller reservationen. Negativt fritt saldo innebär att nästa observation avstår."}
               for n in (1, 10, 20, 100, 101)]
    # Bernoulli at common odds2: Var(net return per unit) = O²p(1-p).
    # Approximate normal one-sided 5% alpha /80% power, iid, known costs:
    # useful for showing calendar infeasibility, not final proof or trial design.
    power = []
    for bp in (100, 300, 500):
        e = D(bp) / 10000
        p = (1 + e) / 2
        var = 4 * p * (1 - p)
        n = up((D("1.644854") + D("0.841621")) ** 2 * var / e ** 2)
        power.append({"edge_bp": bp, "odds_assumed": 2, "iid_variance": str(var),
                      "approx_signals_5pct_one_sided_80pct_power": n,
                      "seasons_at_38": str(D(n) / 38), "seasons_at_hard_380": str(D(n) / 380)})
    return {"version": "ekonomisk-forstudie-v2-2026-11-04", "currency_unit": "heltalsören",
            "evidence": "Alla positiva fördelar, kostnader och tidssamband nedan är scenarioantaganden, inte uppmätta eller ägarbeslutade. Scenariernas nettobelopp är förväntningar, inte realiserade vinster eller vinsttak.",
            "assumptions": {"active_months_per_season": 10, "matches_per_season": 380,
                            "signals_reference": 38, "stake_ore": 1000, "paper_capital_ore": 100000,
                            "monthly_data_cost_ore_assumed": 10000, "monthly_ai_cost_ore_assumed": 0,
                            "monthly_other_cash_cost_ore_assumed": 0,
                            "monthly_work_hours_assumed": 2, "hourly_work_value_ore_assumed": 20000,
                            "calendar_year_subscription_months": 12},
            "verified_archive": verify_archive(), "scenarios": scenarios, "goals": goals,
            "cost_sensitivity": sensitivity, "capital": capital, "approx_power": power}


def markdown(data):
    a = data["verified_archive"]
    lines = ["# Ekonomi och kapacitet – 4 november 2026", "", "Status: förstudie v2, endast simulerade belopp. Ingen datakostnad eller spelbudget godkänns.", "",
             "## Verifierad negativ baslinje", "",
             f"Lokal omräkning av samtliga {a['matches']} JSON-rader och motsvarande CSV-rader: {a['signals']} val, {a['wins']} vinster, omsättning {money(a['staked_ore'])} kr, netto {money(a['profit_ore'])} kr, ROI {D(a['profit_ore']) / a['staked_ore'] * 100:.6f} %. Slutkapital {money(a['final_bankroll_ore'])} kr. Varje utbetalning omräknad från 90-minutersresultat, fast 10 kr och arkivets odds efter 1 % prisavdrag.", "",
             "Detta verifierar rapportens aritmetik och filöverensstämmelse, INTE samtidighet, svensk åtkomst, signalernas sannolikheter eller strategioberoende. Ingen ny strategireplay görs; inga nya slutsatser om vinstförmåga tillförs.", "",
             "Rapportuppgift: max realiserad nedgång 337,15 kr och dagklustrat bootstrapintervall för ROI −80,35 % till +30,63 %. Intervallet löser inte käll- och urvalsfel. Utfallsfördelning verifierad: 55 borta,19 hemma,2 oavgjort.", "",
             "## Formler och antaganden", "",
             "Med s=insats, p=okänd verklig sannolikhet, O=offert, d=prisavdrag och f=extra avgift per omsatt krona: spelnetto i förväntan = s×[p×O×(1−d)−1−f]. Om rå edge g=pO−1 blir nettoedge e=(1+g)×(1−d)−1−f. Projektnetto = spelnetto−data−AI−övriga kontantkostnader. Ekonomiskt netto = projektnetto−timmar×timvärde. Framtida verklig avgiftsmodell måste låsas; omsättningsavgift är bara en av möjliga definitioner.", "",
             "Scenarierna anger e EFTER prisförsämring och avgifter. Tabellen härleder nödvändig g med d=1 % och f=0. Avdraget dras aldrig igen. Positiv e är ett antagande, ingen skattning från historiken. Det gamla −31,1 % utfallet är ingen stabil prognos, därför används −5 % som separat negativt stressantagande.", "",
             "Bas: 38 signaler/säsong från 76/2 historiskt, 10 aktiva matchmånader/säsong som förenklat antagande, 380 matcher/säsong och högst ett valt spel/match. 38 möjliga spel/aktiv månad och 31,67/kalendermånad är kapacitetsgenomsnitt, inte löfte om ett visst månadsschema. Ett kalenderår antas innehålla en säsongs 380 matcher; säsongsövergång kan ändra faktisk fördelning.", "",
             "Kostnadsantagande: data100 kr/månad, AI0 kr (deterministisk beräkning), övrigt0 kr, arbete2 timmar×200 kr/månad. Ingen av dessa är prisoffert eller ägarens budget. Säsong kostas10 månader (1 000 kr kontant +4 000 kr tid); kalenderår12 månader (1 200+4 800 kr). Ingen valutaomräkning, moms eller uppstartstid är inbakad. Faktiska fakturakostnader måste senare ersätta antagandena; annars underskattar modellen totalen. Gratiskällor/tid0 visas separat.", "",
             "## Förväntade scenarionetton vid 38 spel à 10 kr", "",
             "Alla nettobelopp i följande scenario- och måltabeller är matematiska förväntningar vid antagen edge. Ett realiserat resultat kan bli högre eller lägre; 19 och 190 kr är inga tak för slumpmässig vinst eller förlust.", "",
             "| Scenario | Edge efter genomförande | Krävd rå edge före1 % prisavdrag | Spelnetto/säsong | Projektnetto/säsong | Ekonomiskt netto/säsong | Projektnetto/kalenderår | Ekonomiskt netto/kalenderår |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in data["scenarios"]:
        lines.append(f"| {s['name']} | {s['net_edge_bp_assumed']/100:.2f} % | {D(s['raw_edge_bp_required_before_haircut'])/100:.4f} % | {money(s['season_game_net_ore'])} | {money(s['season_project_net_ore'])} | {money(s['season_economic_net_ore'])} | {money(s['calendar_year_project_net_ore'])} | {money(s['calendar_year_economic_net_ore'])} |")
    lines += ["", "Belopp i kr. Vid antagen 1 % nettoedge blir förväntat spelnetto 3,80 kr/säsong; vid 5 % blir det 19,00 kr. Även vid det orealistiska kapacitetstaket 380 signaler och antagen 5 % nettoedge blir förväntat spelnetto 190 kr/säsong före datakostnad/arbetstid. Med 38 signaler är den förenliga datakostnaden för noll förväntat projektnetto vid antagen 5 % edge 19 kr/kalenderår (=1,58 kr/månad) om AI/övrigt kostar 0. Detta är en algebraisk brytpunkt, ingen rekommendation om abonnemang. Realiserad vinst kan avvika kraftigt åt båda håll.", "",
              "## Baklänges från mål – huvudscenario 3 % nettoedge", "",
              "Mål 100/500/1 000 kr är endast exempel. Aktiv månad jämför 3,8 referenssignaler och 38 matcher. Tio sådana aktiva månader innebär säsongsmål 1 000/5 000/10 000 kr. Kalenderår jämför 38 signaler och 380 matcher. Årsmål 1 200/6 000/12 000 kr motsvarar 100/500/1 000 kr per kalendermånad. Kravomsättning T=(mål+kostnader)/e och signaler=tak(T/10kr). För e≤0 finns inget ändligt positivt mål med positiva kostnader. Varje målrads fasta 10 kr insats binder 100/200 kr vid 10/20 samtidiga oavgjorda spel; den bindningen ändras inte för att inkomstmålet höjs.", "",
              "| Period | Mål | Nettobegrepp | Omsättning | Signaler à10kr | Krävd algebraisk insats vid referensvolym | Vid en signal/varje match | Ryms i380matcher/år eller38/aktiv månad? |",
              "|---|---:|---|---:|---:|---:|---:|---|"]
    for g in data["goals"]:
        if g["scenario"] == "positiv":
            lines.append(f"| {g['period']} | {money(g['net_goal_ore'])} | {g['net_basis']} | {money(g['required_turnover_ore_ceiling'])} | {g['required_signals_at_10sek']} | {money(g['algebraic_stake_at_reference_volume_ore_ceiling'])} | {money(g['algebraic_stake_at_max_match_volume_ore_ceiling'])} | {'Ja' if g['fits_one_bet_per_match_ceiling'] else 'Nej'} |")
    lines += ["", "Insatskolumnerna visar varför kalkylen inte ryms vid10kr. De är INTE en föreslagen insatshöjning; hypotetisk acceptans vid sådana belopp är helt obevisad. Högre risk ska inte användas för att rädda kalkylen. Alla fem edgefall, kostnadsnivåer och mål finns maskinläsbart i ekonomi.json.", "",
              "## Kostnader och känslighet", "", "JSON innehåller 36 kombinationer: 1/3/5 % nettoedge; data 0/100/300 kr per månad; AI 0/50 kr; arbetstid 0/400 kr. Vid 38 spel och 10 kr kan en enda månadskostnad 100 kr redan överstiga ett helt års antaget spelnetto flera gånger. Med alla kostnader 0 är spelnetto=projektnetto, men det visar inte att avgiftsfri åtkomst eller ägarens tid faktiskt finns. Ingen betald modell behövs för odds- och kostnadsaritmetik.", "",
              "## Bundet kapital och nedgång", "",
              "Vid10kr fast insats binder10 samtidiga oavgjorda spel100kr och20spel200kr. Olöst resultat släpper inte reservationen.100 öppna spel binder hela1 000kr experimentkapitalet; spel101 måste avstå, även om en positiv förväntan beräknas. Kapitalbehov för bunden exponering är max samtidiga/olösta spel×10kr, utöver reserv för förluster. Betalning av data hör inte till papperskapitalet. Varken1 000kr eller10kr är godkänd verklig budget.", "",
              f"Historiska största dagreservation {money(a['largest_same_day_reservation_ore'])}kr är verifierad genom gruppering av val. Den är ingen prognos för framtida samtidighet. Historisk realiserad nedgång337,15kr är rapportuppgift, inte riskgräns eller framtida maxförlust. Framtida utvärdering ska redovisa nedgång på slutkapital respektive tillgängligt kapital inklusive olösta reservationer; en universell säker kapitalnivå kan inte härledas från detta material.", "",
              "## Kan ett begränsat försök påvisa liten fördel?", "",
              "Illustration, INTE faktisk styrkeberäkning för dessa långskott: oberoende lika stora spel med odds2, ensidigt5 % test och80 % styrka. n≈(1,644854+0,841621)²×4p(1−p)/e², p=(1+e)/2. Klustring, okänd sannolikhet och selektion kan öka behovet. Resultaten:", "",
              "| Antagen edge | Ungefär n | Säsonger vid38 signaler | Säsonger vid högst380 |", "|---|---:|---:|---:|"]
    for p in data["approx_power"]:
        lines.append(f"| {p['edge_bp']/100:.0f}% | {p['approx_signals_5pct_one_sided_80pct_power']} | {D(p['seasons_at_38']):.1f} | {D(p['seasons_at_hard_380']):.1f} |")
    lines += ["", "Hundra spel ger alltså ingen generell bevisgräns. Vid odds2 och p≈0,5 är standardfelet för100 spel omkring10 procentenheter ROI; ett normalt95 % intervall är ungefär ±19,6 procentenheter, före beroenden och urvalsproblem. Långskott4–29 från arkivet kräver annan variansmodell. Begränsad ny insamling kan avgöra tidsriktighet och datatäckning, men kan inte lova statistiskt besked om en liten lönsamhet inom en säsong.", "",
              "## Ekonomiskt beslut", "",
              "**Ekonomiskt orimligt inom den illustrerade ramen som förväntad hållbar inkomst** för mål 100–1 000 kr/månad, en liga, 10 kr pappersinsats och även optimistisk antagen 5 % nettoedge. Det gäller redan före kostnader: 38 spel/säsong ger förväntat spelnetto 19 kr/år i det scenariot. Med 380 spel/säsong blir förväntat spelnetto 190 kr/år, fortfarande under lägsta målet 1 200 kr/år. Detta utesluter inte högre realiserad slumpvinst och är inget tak för enskilda utfall; slutsatsen gäller de beräknade förväntningarna. Positiva fördelar är obevisade och högre insats är inte lösningen i detta uppdrag.", "",
              "**Otillräckligt underlag** om det finns en användbar tidsriktig prisavvikelse över huvud taget. En liten kostnadsfri datakontroll kan ge ett tekniskt beslut, men är inte en investering som denna vinstkalkyl kan motivera med förväntad återbetalning. Betald pilot kräver separat ägarbeslut och högsta faktiska kostnad; ingen budget aktiveras här.", "",
              "## Återskapa och kontrollera", "",
              "Kör projektets Python med denna ekonomi.py. Skriptet läser endast arkiverad JSON/CSV och skriver endast ekonomi.json/ekonomi.md i den nya dokumentmappen. SHA256 för lästa arkivfiler ingår i JSON. Det använder Decimal för ekonomisk aritmetik, uppåtrundar nödvändig omsättning/insats och lagrar pengar som heltalsören. Månadssignalvolym är ett förväntat medelvärde; faktiska signaler är heltal och ojämnt fördelade. Inbyggda assert kontrollerar både arkivavräkning och ekonomiska formler: 52 % vid odds 2 och 10 kr ger 40 öre förväntat brutto, 29,6 öre efter 1 % prisavdrag, 27,6 öre med ytterligare 0,2 % omsättningsavgift; avgiften och prisavdraget dras endast en gång. Noll/negativ edge saknar positiv mållösning, och signalantal avrundas uppåt. Skriptet stoppar vid avvikelse. Kör utan Pythonflaggan -O, som stänger av assert.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = calculate()
    (HERE / "ekonomi.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "ekonomi.md").write_text(markdown(result), encoding="utf-8")
    print(f"Verifierat {result['verified_archive']['signals']} avräkningar; {len(result['goals'])} målrader; {len(result['cost_sensitivity'])} kostnadsfall. Endast lokala dokumentresultat skrivna.")

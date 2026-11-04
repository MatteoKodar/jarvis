# Kopierbart nästa uppdrag: lokal ekonomi- och datakvalitetskontroll

Status: FÖRSLAG FÖR ÄGARENS GRANSKNING, 2026-11-04, version feasibility-offline-v1. Inget bygg- eller insamlingstillstånd skapas genom denna specifikation.

## Uppdrag

Arbeta i JARVIS enligt AGENTS.md. Implementera endast ett lokalt kommandoradsverktyg som läser uttryckligen angivna, redan lokala försöksfiler och skriver en svensk fristående HTML-rapport med ekonomi, datakvalitet och spårbarhet i en NY resultatmapp. Verktyget får inte hämta webbsidor, odds eller resultat, använda .env/credentials, öppna drift-DB, skapa pappersspel, föreslå insatshöjning eller ändra den frysta modellen. Inga API-rutter, frontendflöden, migrationer, schemaläggare eller leverantörsanslutningar ingår.

Det första flödet är: välj lokalt manifest och lokal JSONL-fil → validera samtliga planerade observationsplatser inklusive bortfall → beräkna scenarier → skriv ny rapport och filhashmanifest → visa lyckad/ofullständig/avvisad kontroll. Omtolkning av historiska closing-priser till tidsriktiga offerter ska avvisas. Verktyget ska också kunna köras med enbart syntetiskt material utan observationer.

## Föreslagna filer och ansvar

| Fil | Motiv |
| --- | --- |
| backend/jarvis/odds_feasibility.py | Ren strikt validering och deterministisk Decimal/heltalskalkyl; inga DB-, nätverks-, agent- eller configimporter. Håll tillsammans tills verkligt behov kräver uppdelning. |
| scripts/odds_feasibility.py | Tunn CLI; tillåtna lokala in-/utvägar, storleksgränser, nya kataloger och svensk HTML-export med escaped text. |
| tests/test_odds_feasibility.py | Ekonomiska identiteter, tidsgränser, bortfallsnämnare, importskydd och determinism. |
| docs/odds-feasibility/README.md | Svenska kommandon, format och tolkning med syntetiskt exempel. |
| docs/odds-feasibility/fixtures/manifest.json och observations.jsonl | Endast syntetiska uppgifter, tydligt märkta. Ingen verklig offert eller kontouppgift. |

Återanvänd beräkningsformler och kontroller från denna förstudie och samma skalor som odds_lab: pengar heltalsören, decimalodds ×10 000, sannolikheter per miljon endast som exportformat. Beräkna internt med Decimal; inga binära flyttal för pengar. Återanvänd inte select_price_signal eller POLICY för en ny strategi. Den gamla medianmodellen ska behålla exakt sin version/hash. Kanonisk JSON/SHA-256 från odds_lab kan återanvändas om det förblir en ren import utan config eller DB. Filhash är inte ägarbeslut.

## Datakontrakt feasibility-input-v1

Alla objekt är strikta: okända fält, fel typer, NaN/Infinity, duplicerade JSON-nycklar och bool som heltal avvisas. Max manifest 256 KiB, JSONL 5 MiB och 10 000 rader. Bevara filhash och källans status. Avvisade rader loggas med radnummer/felkod; rapporten är ofullständig och kan aldrig få godkänd datakvalitet. Ingen tyst lagning eller radering.

Manifest:

- schema_version, study_id, status="draft" eller "frozen", created_at med UTC-offset, timezone="Europe/Stockholm"; status frozen kräver en angiven mänsklig decision_ref, men verktyget får inte självt godkänna den.
- observation_window: first_date, last_date och settlement_deadline. Endast ett liganyckelvärde och market="1x2_90min".
- match_registry: varje event_id är unikt som matchidentitet. planned_slots: slot_id, event_id, schedule_version, scheduled_kickoff_at, observation_kind="T60"/"T55", planned_at. slot_id och paret (event_id, observation_kind) är unika; T60 och T55 delar samma event_id. Omplanering är en revisionshändelse för samma slot, inte en ny match eller observationsplats. Saknad JSONL-rad ska skapa missing i rapporten och behålla platsen i nämnaren.
- source_registry: exakt operator_id, svensk_variant, family_id eller null, relation_status="documented"/"unknown", evidence_url, checked_at. Unknown räknas inte som oberoende källa. Saknat källregister spärrar jämförbarhet, inte råloggning.
- economic_assumptions: stake_ore=1000, paper_capital_ore=100000, active_months=10, season_matches_cap=380, historical_signals_reference=38, scenario_list och cost_profiles enligt följande kontrakt. Saknad kostnad är null/unknown, inte automatiskt noll.
- versioner/hashes för tidsregel, prisstress, avgifter, källa och kalkyl; inga pris-/modellprofiler är beslutade här.

Exakt scenarioobjekt: scenario_id (unik), label, evidence="assumption", cost_profile_id och en av två former. kind="net_edge" har endast net_edge_bp (heltal−20 000..1 000 000, uttrycklig nettoränta efter genomförande). kind="from_price" har endast probability_ppm (heltal0..1 000 000), odds_x10000 (10 001..1 000 000), haircut_bp (0..9 999), stake_fee_bp (0..10 000) och win_commission_bp (0..10 000). Inga from_price-fält får finnas i net_edge, eller tvärtom. Sannolikhet och edge är antaganden, inte marknadens sanning. Deriverad förväntan beräknas med Decimal före redovisningsavrundning.

cost_profiles är en lista av unika cost_profile_id med label och cost_periods. Varje kostnadsperiod har period_id, starts_on/ends_on (ISOdatum, inkluderade), active_month_count (positivt heltal), cash_costs och work. cash_costs har en post per kategori data/ai/compute/other: evidence="assumption"/"observed_cost"/"unknown", unit_amount_ore (heltal≥0 eller null endast för unknown), charges_count (heltal≥0) och charge_dates (exakt lika många ISOdatum inom perioden). Total = unit_amount_ore×charges_count; inga parallella månads- och årstotaler får summeras igen. work har evidence, minutes (heltal≥0 eller null) och hourly_value_ore (heltal≥0 eller null); tidsvärde=minutes×hourly_value_ore/60, separat från kontantkostnader. Unknown belopp/tid ger explicit okänt projektnetto/ekonomiskt netto, inte0. Säsongens10 och årets12 abonnemangsdebiteringar är separata rapportperioder, aldrig kostnader som läggs samman till samma netto. Dessa beloppsramar är valideringsgränser, inga budgetgodkännanden.

Varje observationsrad:

- schema_version, study_id, slot_id, event_id, league, home, away, market, scheduled_kickoff_at, schedule_version.
- observation_status="observed"/"missing"/"failed"/"suspended"/"postponed"/"cancelled"/"uncertain"/"not_attempted" och reason_code.
- request_id eller null; source_market_observed_at, received_at, available_for_decision_at, decision_at (alla offsettider eller null vid saknad); råsvarshash eller null med skäl. En framtida import får aldrig fabricera API-tider.
- quotes: operator_id, family_id/relation_status, source_level="api"/"manual_public", odds_x10000 {home,draw,away}, market_status, source_market_observed_at, received_at, public_source_url (utan hemlighet/query). API-tid betyder senast observerat, inte bekräftat prisändringsögonblick.
- manual_check: planned_stratum, source_ref, observed_at, outcome, odds_x10000, match_market_verified, access_level=2 eller null. Hypotetisk användbarhet nivå3 är separat antagande; accepted_stake_ore måste vara null. Nivå4 får inte produceras.
- planned_stake_ore=1000, assumed_delay_seconds=30 och simulated_price_basis="not_simulated" i detta byggsteg. Inga signaler eller valda spel beräknas.

Separata lokala request-receipt-rader (valfria nu, nödvändiga före senare insamling) anger operation_id, endpoint_kind, requested_at, response_at, state, quota_max_reserved, quota_used eller null samt raw_sha256; aldrig apiKey eller full URL med query. Unknown får inte automatiskt klassas om till lyckad/released. Detta uppdrag analyserar kvitton, skickar inga anrop och inför ingen ny dispatch-kind.

En ligabatch får ha samma request_id i flera matchobservationer, men requestkvitto och kvot räknas exakt en gång per unikt operation_id. T60/T55 är observationsplatser och får inte skapa dubbel debitering av samma batch. Ingen strataindelning utifrån en ny signalregel ingår i detta bygge; redan förhandsregistrerad stratumetikett kan visas som obekräftad metadata. Datapilotens senare insamling, tidsorkestrering, kvotreservation och kandidatberäkning kräver ett separat granskat uppdrag.

Ekonomiskt kontrakt: räkna prisförsämring endast i effektiva oddset O_eff=O×(1−h). Avgift definieras separat, exempelvis insatsbaserad f och vinstbaserad c: r=p×[1+(O_eff−1)×(1−c)]−1−f. Fast kostnad dras en gång per faktisk kostnadsperiod. Om scenario redan anger r efter genomförandeförluster får h/f/c inte dras igen; ömsesidigt uteslutande indataformer. Visa spelnetto, projektnetto och ekonomiskt netto separat. Baklängeskalkyl saknar lösning när r≤0. Avrunda behövlig omsättning/antal uppåt och utbetalning nedåt till öre; redovisa avrundningsregel.

## Godkännandekriterier och meningsfulla tester

1. Frysta gamla oddsresultat och kodhashar oförändrade; exakt tio backendroller. Varken API, nätverksbibliotek, DB eller config importeras av det nya verktyget.
2. p=0,52, O=2,00, 10kr ger +0,40kr före kostnader; 1% oddshaircut ger +0,296kr före öresavrundning. Ingen dubbelräkning. ROI≤0 ger ingen positiv baklängeslösning.
3. Noll signaler, negativt saldo, saknad kostnad, bindning och årsabonnemang ger uttrycklig ofullständighet/kapacitetsbrist, inte syntetiskt plus. Fast abonnemang fördelas korrekt mellan aktiv månad och kalenderår.
4. 60 planerade platser med 54 fullständiga rader redovisar 54/60=90%, även om endast giltiga offerter skickas med filen. Alla misslyckanden och no-attempt ingår.
5. Fel match/marknad, offert efter beslut, offertålder121s, mottagning/validering/beslut utanför [t0,t0+30s], UTC-offset saknas och okänd familj flaggas. t0=avspark−3600s för T60 och avspark−3300s för T55. Gränser120s och exakt0/+30s godtas endast med övriga villkor. Source-market-tid krävs; deprecated bookmaker-tid räcker inte.
6. Duplicerade slot-ID:n, matchregister-ID:n, (event_id,observation_kind)-par eller JSON-nycklar, filflykt, symlänk/junction utanför tillåten inrot, redan befintlig utmapp och överstora filer avvisas utan att skriva över något. T60/T55 med samma event_id ska godtas som två skilda platser för en match. Offlineverktyget accepterar inga http(s)-invägar.
7. Resultat är deterministiskt för samma byte/antaganden. HTML-text och länkar kan inte exekvera JavaScript/HTML från importerade data; rapporten fungerar utan externa resurser på390px och1280px.
8. Inga credentials, runtime-db eller .env läses. En testvakt som förbjuder nätverk och drift-DB ska upptäcka försök. Tester använder tmp_path och syntetiskt material.

Kör berörda backendtester plus hela befintliga backendsviten efter denna framtida kodändring. Kör TypeScript/build och befintlig Playwright med isolerade testdata för att säkerställa att appen fortfarande fungerar. Ingen ny app-E2E behövs för CLI:ns interna formler; kontrollera den exporterade HTML-rapporten separat med Playwright. Inga betalda verifieringsanrop.

## Skydd och stopp

Bevara atomär reservation, känd prisversion, tak, beständigt stopp, idempotens, DEMO/LIVE-separation och högst ett kontrollerat sändningsförsök per operation. Befintliga dispatch.authoritative tillåter bara modell/Wikipedia och LIVE; detta uppdrag får inte låtsas att den redan stöder odds eller kringgå den. En framtida oddsadapter kräver ett annat granskad uppdrag med kvotreservation och hemlighetsfri agentgräns. Okänd debitering får inte återförsökas automatiskt. Backendagenter får inga terminalverktyg eller ägarcredentials.

## Insats, beroenden och stoppunkt

Förslag: 16–24 utvecklingstimmar inklusive validering, tester och rapportlayout, inte en offert. Kostnad vid illustrativ200kr/h=3 200–4 800kr; faktisk timvärdering okänd. Inga nya paket krävs utöver befintlig Pythonmiljö. Externa data behövs inte; syntetiskt material räcker för acceptans. Senare datakontroll väntar på ägarens granskning, rättigheter, källfamiljer och ett nytt låst insamlingsfönster; minst28observationsdagar+3avräkningsdagar efter start. Byggtid och väntetid får inte beskrivas som tid till lönsamhet.

Stanna efter lokal rapport och verifiering. Anslut ingen källa och starta inte pilot eller pappersstrategi. Lämna exakta ändrade filer, körda tester, kända brister och rapportlänk till ägaren.

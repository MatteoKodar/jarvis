# Byggspecifikation för JARVIS offlinekontroll

Datum: 6 november 2026. **Förslag för ägarens granskning. Detta bygge är inte genomfört eller aktiverat.**

Bygg ett lokalt kommandoradsverktyg för ekonomi och datakvalitet. Det ska läsa uttryckligen angivna filer, behålla alla planerade observationsplatser och skriva en svensk fristående rapport i en ny resultatmapp. Det ska kunna köras med enbart syntetiska scenarioantaganden. Det får inte hämta data, skapa signaler eller pappersspel, importera appens konfiguration eller öppna driftdata.

Underlag: nulägesgranskningen av `C:\Users\matte\jarvis`, HEAD `0e0707f1d103203c6e21c3d350019c9224b7f57f`, samt den redovisade avgränsade idempotensrättningen. Befintligt kontrakt: `feasibility-input-v1` i `docs/sportsbetting/2026-11-04-v2/IMPLEMENTATIONSUPPDRAG.md`. Namngivning, gränser och felpolicy som preciseras här ska godkännas tillsammans; originaldokumentet ska bevaras som historik.

**Motiv, B:** dagens Oddslabb har en kedja för manuellt importerade matcher, analys och pappersavräkning. Det har inte ett register över alla förhandsplanerade T60/T55-platser, full kostnadsperiodisering eller dokumenterade källfamiljer. Daterade `ekonomi.py` och `statistik.py` innehåller användbar aritmetik men är studieskript med historiska sökvägar och skrivande rapportutdata. De ska inte importeras som produktmoduler. Den frysta medianmodellen ska inte ändras för att göra det nya verktyget.

## 1 Leverans och arbetsordning

| Steg | Syfte och indata | Utdata | Filer | Beroende |
| --- | --- | --- | --- | --- |
| 1 Datakontrakt | Gör v1 entydigt och skriv syntetiska exempel | Formatbeskrivning, felkoder, tre exempelfall | `docs/odds-feasibility/README.md`, `fixtures/` | Ägarens godkännande av denna specifikation |
| 2 Ren kärna | Tolka byte, validera struktur och beräkna scenarier | Deterministiskt analysobjekt | `backend/jarvis/odds_feasibility.py` | Steg 1 |
| 3 Spårbarhet och fullständighet | Koppla alla rader till planerade platser och unika operationer | Kvalitetsredovisning med nämnare och orsaker | Samma rena modul | Steg 2 |
| 4 Lokal CLI och export | Läs endast tillåtna uttryckliga filer; skapa ny mapp | JSON, HTML, filhashar och färdigmarkering | `scripts/odds_feasibility.py` | Steg 2–3 |
| 5 Tester och layout | Prova gränser, fel, determinism och skydd | Testresultat, syntetiska rapporter, nya skärmbilder | `tests/test_odds_feasibility.py`, separat CLI-test vid behov | Steg 1–4 |
| 6 Slutverifiering | Kontrollera regression och oförändrad historik | Leveransmanifest och svensk verifieringsanteckning | Ny daterad verifieringsmapp | Steg 5 |

Arbeta i denna ordning. Undvik nya paket. Håll kärnan i en modul tills dess storlek eller en konkret beroendegräns kräver uppdelning. Ingen ny tjänst, API-route, frontendvy, worker, schemaläggare, databastabell eller migration behövs.

## 2 Steg 1 Datakontrakt

### 2.1 Gemensamma typer och storleksgränser

Alla JSON-objekt har en uttömmande lista över tillåtna fält. Okända fält, duplicerade JSON-nycklar, bool som heltal, numeriska strängar där heltal krävs, NaN/Infinity, ogiltig UTF-8 och fel rottyp ska inte korrigeras automatiskt. JSON-token som inte behövs som heltal avvisas i indatakontraktet; beräkning använder Decimal, inte float.

- UTF-8 utan BOM; manifest högst 256 KiB, observationer högst 5 MiB och 10 000 JSONL-rader. Läs gräns + en byte innan parsning; lita inte enbart på filens tidigare storlek.
- Varje JSONL-rad högst 256 KiB. Tom rad är ett radfel med radnummer, inte en observation som försvinner. Sista raden får sakna radslut.
- ID:n: 1–80 ASCII-tecken `[A-Za-z0-9_-]`; regelversioner 1–80 tecken, textetiketter högst 200, lag högst 100, orsak högst 200, `decision_ref` högst 500. Begränsa matchregister till 1 000, planerade platser till 2 000, källor till 100, offerter per rad till 100, scenarier till 100, kostnadsprofiler till 20 och perioder per profil till 24.
- Datum är verkliga `YYYY-MM-DD`. Tid är RFC 3339 med explicit `Z` eller numerisk offset och högst mikrosekunder. Bar lokal tid och Unix-tal avvisas; normalisera till UTC för jämförelse och lagra källsträngen separat för spårbarhet. Använd Europe/Stockholm för datum som uttryckligen är lokala.
- Pengar är heltalsören, decimalodds är heltal ×10 000, sannolikhet är ppm, räntor/avgifter är baspunkter. Använd inte SEK-float i någon serialiserad kontrollsumma.
- Sökvägar ingår inte i manifestet: CLI väljer varje fil uttryckligen. Manifestet får inte utlösa rekursiv filupptäckt eller öppning av URL:er.

**Acceptans:** gränsen godtas, en byte/rad över gränsen avvisas. Ett minimalt giltigt manifest och en observation ska gå att läsa utan import av app, config, databas eller nätverksklient.

### 2.2 Manifestets fält

Obligatoriska toppfält: `schema_version="feasibility-input-v1"`, `study_id`, `status`, `created_at`, `timezone="Europe/Stockholm"`, `decision_ref`, `observation_window`, `league`, `market="1x2_90min"`, `match_registry`, `planned_slots`, `source_registry`, `economic_assumptions`, `rules`.

| Fält | Typ och regel |
| --- | --- |
| `status` och `decision_ref` | `draft` eller `frozen`; referens är null eller text. `frozen` kräver icke tom text. En referens visar vad filen påstår, inte att verktyget verifierat ett ägarbeslut |
| `observation_window` | Exakt `first_date`, `last_date`, `settlement_deadline`; första ≤ sista datum och deadline efter sista observationsdagens slut i Stockholm |
| `league` | Ett icke tomt liganyckelvärde; inte en lista. Endast denna liga får förekomma i raderna |
| `match_registry` | Lista med exakt `event_id`, `league`, `home`, `away`. Unikt event-ID; liga överensstämmer, två skilda icke tomma lag efter blankstegsnormalisering. Registrera lagens ursprungliga text, ändra inte identitet tyst |
| `planned_slots` | Exakt `slot_id`, `event_id`, `schedule_version`, `scheduled_kickoff_at`, `observation_kind`, `planned_at`. `event_id` måste finnas i registret. `schedule_version` positivt heltal. `observation_kind` är `T60`/`T55`; `planned_at` är den planerade observationstidpunkten t0 |
| `source_registry` | Lista med exakt `operator_id`, `svensk_variant`, `family_id`, `relation_status`, `evidence_url`, `checked_at`. Operatörs-ID unikt. Variant är identifierande text; familj ID eller null; status `documented`/`unknown`. Dokumenterad relation kräver familj, källreferens och offsettid. Okänd relation får inte räknas som oberoende familj |
| `rules` | Exakt `timing`, `price_stress`, `fees`, `sources`, `calculation`; varje post exakt `version` och `sha256` med 64 gemena hextecken. Dessa binder påstått regelunderlag; de godkänner inte en strategi eller extern källa |

Slot-ID och paret `(event_id, observation_kind)` är unika. Samma match får ha **både T60 och T55**. t0 är avspark minus 3 600 respektive 3 300 sekunder; `planned_at` ska vara exakt detta. Lokal t0-dag ska ligga i observationsfönstret. En ändrad avspark innebär en ny `schedule_version` för samma slot i ett separat indataunderlag, inte en extra plats i samma manifest. Verktyget skriver inte om föregående körning.

Ett tomt eller saknat källregister ska inte leda till att indataobservationer försvinner. Tom lista tillåts och gör källjämförbarhet ofullständig. Toppfältet ska finnas. En offert från en operatör som inte finns i registret behålls med kvalitetsbrist och får inte räknas som verifierad familjetäckning.

### 2.3 Ekonomiska antaganden och perioder

`economic_assumptions` har exakt `stake_ore=1000`, `paper_capital_ore=100000`, `active_months=10`, `season_matches_cap=380`, `historical_signals_reference=38`, `scenario_list`, `cost_profiles`. Dessa är låsta illustrativa v1-skalor, inte godkänd spelbudget eller prognos. Verktyget ska inte föreslå högre insats om ekonomin inte går ihop.

Varje scenario har unikt `scenario_id`, `label`, `evidence="assumption"`, `cost_profile_id` och `kind`, med exakt en form:

- `kind="net_edge"`: endast det ytterligare fältet `net_edge_bp`, heltal −20 000 till 1 000 000. Det anger redan justerad nettoavkastning per omsatt insats efter genomförandeförluster.
- `kind="from_price"`: endast `probability_ppm` 0–1 000 000, `odds_x10000` 10 001–1 000 000, `haircut_bp` 0–9 999, `stake_fee_bp` 0–10 000 och `win_commission_bp` 0–10 000.

Former får inte blandas. Refererad kostnadsprofil måste finnas. Saknad sannolikhet blir inte en härledd marknadssannolikhet; det är ett strukturfel för just den scenarioformen.

Varje kostnadsprofil har exakt ett unikt `cost_profile_id`, `label` och `cost_periods`. Varje period har unikt `period_id`, `starts_on`, `ends_on`, `active_month_count`, `cash_costs` och `work`. Datum är inkluderade. Antal aktiva månader är 1–120 och får inte överstiga antalet kalender­månader som perioden berör. Taket är en valideringsgräns, inte ett försökstillstånd.

`cash_costs` är ett objekt med exakt kategorierna `data`, `ai`, `compute`, `other`. Varje kategori har exakt `evidence`, `unit_amount_ore`, `charges_count`, `charge_dates`:

- Evidence är `assumption`, `observed_cost` eller `unknown`.
- Belopp 0–1 000 000 000 öre eller null. Null används när belopp är okänt; `unknown` ska ha null, andra evidence kräver heltal.
- Antal 0–1 200, och lika många angivna debiteringsdatum inom perioden. Samma datum får förekomma flera gånger endast om det representerar flera uttryckligen angivna debiteringar; rapporten visar antalet, inte en deduplicerad datummängd. Samma kategori förekommer bara en gång per period.
- Kostnaden är belopp × antal. Inget extra summerbart fält för månads-, säsongs- eller årstotal tillåts.

`work` har exakt `evidence`, `minutes`, `hourly_value_ore`. Evidence använder samma tre etiketter; `observed_cost` betyder här ägaruppgiven tid/värdering, inte löne- eller fakturaverifiering. Minuter 0–5 256 000 och timvärde 0–1 000 000 000 öre eller null. En okänd post har minst en null; en känd post har två heltal. Tidsvärde är minuter × timvärde /60 och hålls skilt från kontanta kostnader.

Överlappande perioder får finnas som **alternativa redovisningsperioder**, exempelvis tio säsongsdebiteringar respektive tolv kalenderårsdebiteringar. Beräkna och visa varje period för sig. Summera aldrig deras kostnader till ett gemensamt netto. Högst ett definierat säsongsantal 38 och ett kapacitetsfall 380 visas per scenario; periodens volymfördelning ska uttryckligen beskrivas som ett illustrativt medelvärde, aldrig som uppmätta spel eller nytt matchschema.

### 2.4 Observationsrader

Varje JSONL-rad är ett objekt med exakt följande fält:

| Grupp | Fält och typer |
| --- | --- |
| Identitet | `schema_version`, `study_id`, `slot_id`, `event_id`, `league`, `home`, `away`, `market`, `scheduled_kickoff_at`, `schedule_version`; samma värden som manifestets registrerade slot/match, annars kvalitetsbrist |
| Status | `observation_status`: `observed`, `missing`, `failed`, `suspended`, `postponed`, `cancelled`, `uncertain`, `not_attempted`; `reason_code` text eller null. Annan status än observed kräver en orsak |
| Spår | `request_id` ID eller null; `source_market_observed_at`, `received_at`, `available_for_decision_at`, `decision_at`: offsettid eller null; `raw_sha256` hash eller null. Saknad tid/hash redovisas uttryckligen; `reason_code` krävs vid saknad information |
| Offerter | `quotes`: lista, även tom. Varje objekt har exakt `operator_id`, `family_id`, `relation_status`, `source_level`, `odds_x10000`, `market_status`, `source_market_observed_at`, `received_at`, `public_source_url` |
| Manuell kontroll | `manual_check`: null eller objekt enligt nedan |
| Simuleringsgräns | `planned_stake_ore=1000`, `assumed_delay_seconds=30`, `simulated_price_basis="not_simulated"` |

För varje offert är source level `api` eller `manual_public`; marknadsstatus `open`, `suspended`, `closed` eller `unknown`. Oddsobjektet har exakt `home`, `draw`, `away`, vart och ett heltal 10 001–1 000 000 eller null. Null är en tolkningsbar ofullständig offert och behålls som kvalitetsbrist, inte som odds 0. Duplicerad operatör i samma rad är ett strukturfel för raden. Identitet och familj får inte tyst ersättas med manifestets värden om de skiljer sig; logga konflikten och räkna inte offerten som jämförbar.

`manual_check` har exakt `planned_stratum`, `source_ref`, `observed_at`, `outcome`, `odds_x10000`, `match_market_verified`, `access_level`, `accepted_stake_ore`. Stratum är förhandsangiven text eller null, source ref en offentlig referens eller null, observed_at offsettid eller null, outcome `home`/`draw`/`away` eller null, odds ett heltal i samma skala eller null. Verifiering är bool eller null; nivå är 2 eller null; accepterad insats ska vara **null**. Verktyget producerar aldrig nivå 4. En hypotetisk nivå 3 finns endast som ett separat scenarioantagande, inte som observerad acceptans. Ingen ny stratumindelning beräknas från en signalregel.

Offentliga URL-fält är högst 1 000 tecken, endast http(s), utan credentials, query, fragment, kontrolltecken eller ogiltigt värdnamn. De öppnas aldrig. Ogiltig referens ger kvalitetsbrist när övrig rad går att identifiera; länken renderas endast som escaped text. `source_ref` får vara en icke aktiv textreferens med samma längdgräns.

### 2.5 Valfria operationskvitton

CLI kan läsa en separat uttrycklig lokal `--receipts`-JSONL, högst 1 MiB och 10 000 rader. Varje post har exakt `operation_id`, `endpoint_kind`, `requested_at`, `response_at`, `state`, `quota_max_reserved`, `quota_used`, `raw_sha256`. Endpoint kind är en etikett, inte en URL: `sports`, `events`, `odds`, `scores`, `diagnostic`. State är `prepared`, `completed`, `failed`, `unknown`, `cancelled`. Kvot är icke negativa heltal högst 1 000 000; användning får vara null. Response time/hash kan vara null med okänt utfall. Inga nycklar, fullständiga request-URL:er eller response bodies tillåts.

Samma `request_id` får förekomma i flera matchrader och båda tidpunkterna. I v1 betyder det kvittots `operation_id`; det är **inte** slot-ID. Exakt duplicerat kvitto för samma operation räknas en gång och visas med dupliceringsnotering. Olika innehåll under samma operations-ID är en konflikt som gör kvotdelen ofullständig; summan får inte godkännas genom att välja ett av kvittona. Okänd användning stannar okänd; reservation visas separat och är inte en extra faktisk kostnad. Saknat kvitto betyder okänd kvotåtgång när en request refereras, inte noll.

Kvitton innehåller ingen kontantkostnad i detta bygge. De får därför aldrig samtidigt läggas som kontantkostnad utöver `cost_profiles`. Detta undviker dubbelräkning mellan batcher, slots, debiteringar och kvot.

### 2.6 Fyra felklasser och nämnare

| Klass | Exempel | Hantering |
| --- | --- | --- |
| Indata kan inte tolkas | Trasig UTF-8/JSON, dubbla JSON-nycklar | Manifest: avvisa kontrollen. JSONL: registrera radnummer och felkod, fortsätt säkert; datakontroll kan inte bli fullständig |
| Strukturellt ogiltigt | Fel typ, okänt schemafält, dubbelt slot-ID, fel scenariotaggar | Manifestfel avvisar hela kontrollen. Radfel avvisar raden utan att ta bort dess planerade slot. Dubbla observationsplatser i JSONL avvisar hela observationskontrollen; ekonomiscenarier kan fortfarande redovisas separat |
| Tolkningsbart med kvalitetsbrist | För sen offert, unknown familj, fel match/marknad mot registret, null-odds, saknat kvitto | Behåll raden och dess orsak. Slot finns kvar i nämnaren men räknas inte som fullständig |
| Fullständig observation | Struktur, identitet, tider, marknad och registrerade källrelationer uppfyller reglerna | Räkna slot en gång som fullständig. Detta styrker teknisk kvalitet under reglerna, inte sannolikhet, prisacceptans eller ekonomisk edge |

Rader som inte går att knyta till en slot redovisas som extra/avvisade; de ökar aldrig antalet fullständiga platser. Rekonstruera en `missing`-post för varje planerad slot utan en godkänd identifierbar rad. Om en felaktig rad hävdar en slot finns denna slot kvar som ofullständig; radera inte raden ur fellistan.

**Godkännande av steg 1:** formatbeskrivning och exempel har inga odefinierade fält eller dubbla kostnadstotaler; felpolicyn täcker varje typ. Inga produktfunktioner aktiveras genom att exempelmanifestet har `frozen`.

## 3 Steg 2 Ren validering och beräkning

Kärnan ska ta byte eller redan strikt tolkade värden och returnera ett serialiserbart analysresultat med fel. Den ska inte öppna filer, läsa miljövariabler, skapa kataloger, importera config/DB/API/worker eller ha nätverksberoenden. Använd bara standardbiblioteket om det räcker. Import av `jarvis.odds_feasibility` får inte initiera någon app. Lämna `jarvis/__init__.py` utan nya sidoeffekter.

Återanvänd regler och skalor från befintlig kod genom dokumenterade formler. Kanonisk JSON/SHA-256 i `odds_lab.py` är ren vid dagens import, men det är säkrare att ha en liten lokal kanoniseringsfunktion än att binda det nya datakontraktet till den frysta signalmodulen. Återanvänd aldrig `POLICY` eller `select_price_signal`. Importera inte de daterade studiegeneratorerna.

### 3.1 Ekonomiska identiteter

För `from_price`, med p=ppm/1 000 000, O=odds/10 000 och h/f/c=bp/10 000:

```text
O_eff = O × (1 − h)
r = p × [1 + (O_eff − 1) × (1 − c)] − 1 − f
förväntat spelnetto = omsättning × r
projektnetto = spelnetto − periodens kontanta kostnader
ekonomiskt netto = projektnetto − periodens tidsvärde
```

Avgift f är insatsbaserad och c avser positiv vinst. I denna v1-formel krävs `O_eff ≥ 1`; kombinationer som ger lägre effektivt decimalodds avvisas som ogiltigt genomförandescenario. Formeln ska inte ge negativ vinstprovision eller återbetalning genom att `(O_eff−1)` blir negativ.

För `net_edge`: r=net_edge_bp/10 000 direkt. Varken h, f eller c får finnas eller dras en gång till. Kontanta fasta kostnader och arbetstid dras däremot vid respektive netto enligt definitionen.

Unknown kontantbelopp gör projektnetto och ekonomiskt netto okända för berörd period. Unknown tid/timvärde gör ekonomiskt netto okänt men påverkar inte känt spelnetto/projektnetto. Redovisa kända delsummor och saknad komponent; ersätt aldrig null med noll. Även en kostnadspost med noll planerade debiteringar och okänt belopp ska visas som okänt underlag, även om dess matematiska kassaflöde är noll.

Visa minst negativt, noll och positivt syntetiskt scenario. Scenariots p och r är antaganden. Läs inga utfall för att anpassa dem. Verktyget räknar inte fram matchspecifika signaler eller faktiska insatser.

### 3.2 Decimal och avrundning

- Använd `localcontext()` med dokumenterad precision minst 40. Skapa Decimal från heltal eller text, aldrig float. Låt inte processens globala Decimal-kontext påverka resultatet.
- Behåll förväntningar före öresavrundning som decimalsträngar i öre. Vid p=0,52, odds 2 och 1 % haircut ska 29,6 öre finnas kvar; det får inte tidigt bli 29 eller 30.
- Presentera förväntade pengar avrundat till närmaste öre med `ROUND_HALF_UP`, samtidigt som exakt decimalvärde kan granskas. Om en hypotetisk utbetalning visas: avrunda nedåt till heltalsöre, separat från förväntan.
- Nödvändig omsättning och helt antal 10-kronorsinsatser avrundas uppåt. Visa även det oavrundade algebraiska värdet.
- Visa inte ROI vid noll omsättning eller kvalitetstäckning vid noll planerade slots som 0 % eller 100 %; använd null och orsak.

### 3.3 Kapacitet och baklängeskalkyl

Begränsa kalkylen till fast 1 000 öre, referensvolym 38 och säsongstak 380. Separat jämförelse kan visa periodens illustrativa aktiva månadsmedelvärde; detta är ingen ny matchlista. Beräkna inte högre föreslagen insats för att nå ett mål.

Målbelopp får i v1 vara fasta dokumenterade exempel i rapporten: 10 000, 50 000 och 100 000 öre per aktiv månad, med tydlig periodomräkning. De är ingen ägarbudget. Kravomsättning för positivt mål är `(mål + relevanta kända kostnader)/r`. Vid r≤0: ingen positiv ändlig lösning. Vid okända relevanta kostnader: okänd lösning. Vid noll referensvolym: inget insatsbelopp eller divisionsresultat. Markera kapacitetsbrist om nödvändigt antal överstiger periodens uttryckliga tak.

Papperskapitalet är en kapacitetsgräns. Illustrera exempelvis 10, 20 och 100 samtidiga olösta positioner à 1 000 öre. Behåll öppet kapital bundet tills avräkning, men skapa ingen faktisk positionsbok och dra inte en reservation en gång till som förlust. Ett negativt beräknat saldo eller otillräcklig fri kapacitet ska visas, inte repareras med syntetisk intäkt.

**Felhantering och acceptans:** strukturfel får stabil felkod; okända kostnader får stabil null-orsak. Oförutsedda beräkningsfel avbryter kontrollen med ett begripligt fel utan rådata i spårutskrift. Samma indata ska ge samma värden oavsett kördatum och Decimal-kontext.

## 4 Steg 3 Fullständighet tidsordning och spårbarhet

Utgå alltid från `planned_slots`. Nämnaren är dess antal, även vid misslyckande, avbruten match, ingen begäran, okänd familj eller saknad rad. Visa både statusfördelning, fullständiga slots och unika matcher. En match med T60/T55 är en match och två platser.

För varje slot beräknas t0 från den i manifestet registrerade avsparken. Följande ska prövas på gränsen och precis utanför:

1. `received_at`, `available_for_decision_at` och `decision_at` ligger alla inom det slutna intervallet `[t0,t0+30 sekunder]`.
2. `source_market_observed_at ≤ received_at ≤ available_for_decision_at ≤ decision_at`. Särskild offerttid får aldrig ligga efter radens beslut.
3. Offertålder vid beslut 0–120 sekunder, inklusive ändpunkterna. Källtidspridning mellan offerter som räknas som jämförbara högst 60 sekunder.
4. Offertens mottagning får inte föregå dess källtid. Källtiden är senaste observerade marknadspris, inte ett styrkt exakt prisändringsögonblick.
5. Liga, match, lagordning, market och schemaversion ska matcha manifestet. Fel identitet behålls som brist; ingen automatisk omkastning av hemma/borta.

Även matcher med olika event-ID men samma normaliserade lagpar och lokala avsparksdag ska flaggas som möjlig identitetsdubblett. De ska inte tyst slås ihop. Ett manifest med sådan tvetydighet avvisas tills ägaren skiljer matcherna med ett entydigt register; det nya verktyget behöver inte stödja ovanliga dubbelmöten samma dag i v1.

Minst fullständiga, öppna, tidsriktiga 1/X/2-odds och dokumenterade registerrelationer krävs för en fullständig offert. Rapporten visar antal dokumenterade familjer separat från antal operatörer. `unknown` räknas aldrig som en extra oberoende familj. Verktyget beräknar ingen familjemedelmodell eller kandidatsignal. Det kan redovisa att ett förväntat jämförelseunderlag saknar familjer utan att välja ett målbolag eller ett spel.

Historiska closinguppgifter utan källtider blir aldrig fullständiga tidsriktiga offerter genom en importtid. `source_level` är inte ett intyg om att uppgiften verkligen hämtats då. Import kan kontrollera konsistens men inte sanningen i en tidsstämpel. Fabricerade tider får inte skapas av verktyget.

Om ingen observationsfil anges och manifestet har noll planerade slots: status `scenario_only`, kvalitetsandel null, ingen godkänd datagrind. Om manifestet planerar slots men filen saknas: samtliga blir missing och status ofullständig. Alla rader, avvisanden och rekonstruerade missing ska finnas med i maskinläsbar spårbarhet.

**Acceptans:** 54 fullständiga av 60 planerade ger 90 %, oavsett om sex rader saknas eller anger failed. Samma operation i sex slots förbrukar kvot en gång. Okänd kvot får ingen automatisk `completed`/`released`-etikett. Indatahash visar byteidentitet, inte riktiga offerter eller mänskligt godkännande.

## 5 Steg 4 Lokal CLI och säker export

Planerat kommando, först efter bygggodkännande:

```powershell
C:\Users\matte\jarvis\.venv\Scripts\python.exe -B C:\Users\matte\jarvis\scripts\odds_feasibility.py `
  --input-root C:\Users\matte\jarvis\docs\odds-feasibility\fixtures\complete `
  --manifest manifest.json --observations observations.jsonl `
  --output-root C:\Users\matte\jarvis\outputs\odds-feasibility `
  --output run-2026-11-06
```

`--input-root` och `--output-root` är uttryckliga, befintliga absoluta lokala kataloger; relativa indatafiler tolkas enbart mot inroten och `--output` är ett enda nytt katalognamn. Exempel med enbart antaganden utelämnar `--observations`. Kvitton läses endast med `--receipts`.

### 5.1 Sökvägsregler

- Avvisa http(s), `file:` och andra URI:er, UNC/nätverksdiskar, device paths, alternativa dataströmmar, `..`, absoluta underfilsargument och Windows reserverade namn. Läs aldrig `.env`, runtime-DB, backup, `.git` eller credentialfiler. Endast uttrycklig `.json` och `.jsonl` tillåts som indata.
- Verifiera hela den upplösta vägen mot in-/utroten. Avvisa alla symlänkar och Windows reparse points/junctions i vägens befintliga komponenter, även om de för tillfället pekar inom roten. Kontrollera även roten och dess komponenter, inte bara sista filen.
- Öppna endast reguljära lokala filer. Kontrollera slutmål via filhandtag/no-follow där plattformen stöder det före läsning; om säker slutmålsverifiering inte kan utföras ska CLI misslyckas stängt med ett begripligt plattformsfel. På Windows ska filhandtagets slutliga sökväg och lokal disktyp kontrolleras. Säkerhetskontrollen får inte importera appkonfiguration.
- Skriv inte resultat under inroten, i källkodsmapp, `data/` eller befintliga historiska rapportmappar. Utroten är en uttrycklig fristående resultatkatalog. Ingen tidigare resultatmapp får tas bort eller återanvändas.
- Kontrollera gränser under faktisk läsning och beräkna filhash från exakt de lästa byten. Läs inte filen igen för att räkna en annan hash efter att innehållet kan ha ändrats.

### 5.2 Transaktionell rapportexport

Skapa den nya resultatmappen med exklusiv `mkdir(exist_ok=False)`. Skriv först en `.INCOMPLETE`-markering. Skriv utdata till tillfälliga filer i den nya mappen, stäng och synkronisera dem, och flytta dem till slutnamn först när innehållet är färdigt. Skapa färdigmarkeringen **`COMPLETE.json` sist**, med filnamn, byteantal och SHA-256, och ta därefter bort `.INCOMPLETE`. Använd endast egna kända filer vid upprensning; följ inte en ny länk och radera inte rekursivt användarens kataloger.

En export är färdig bara om `COMPLETE.json` finns, `.INCOMPLETE` saknas och filhashar stämmer. Ett färdigt avvisat analysresultat kan ha en komplett export; analysstatus och exportstatus är olika begrepp. Ett avbrott ska lämna tydlig ofärdigmarkering, aldrig utskrift ”rapport klar” eller framgångskod. En ny körning ska kräva en ny utmapp. Testa skrivfel efter första filen och avbrott före färdigmarkören.

### 5.3 Avslutskoder

| Kod | Betydelse |
| --- | --- |
| 0 | Analys och export färdiga: tekniskt fullständiga observationer, eller tydligt märkt scenario_only utan datagrind |
| 2 | CLI-/sökvägs-/säkerhetsfel, saknad indatafil eller befintlig utmapp; ingen färdig rapport |
| 3 | Färdig export med ofullständig kvalitet, radfel eller okända ekonomiska komponenter |
| 4 | Färdig redovisning av avvisat kontrakt/manifest/dubblettkontroll; inga giltighetsanspråk för observationerna |
| 5 | I/O-/exportfel eller oväntat internt fel; ingen färdig export |
| 130 | Kontrollerat avbrott från användaren; ingen färdig export |

Om CLI inte säkert kan skapa en resultatmapp ska fel visas på stderr utan att försöka lägga en rapport i en annan mapp. I avvisningsrapporten visas felkoder och radnummer, inte råa importer som kan innehålla otillåtna credentials. Inga env-värden, API-nycklar eller tracebacks med datainnehåll ska läcka till rapporten.

## 6 Steg 4 Rapportens innehåll och determinism

Leverera `rapport.html`, `analysis.json`, `run-metadata.json`, `input-manifest.json` och `COMPLETE.json`. Ingen rådatafil kopieras automatiskt till resultatet. `input-manifest.json` innehåller relativa filnamn, byteantal och hash för de uttryckligt lästa filerna, inte hemliga fulla URL:er eller kontoinformation.

HTML ska vara svensk, fristående och fungera utan nätverk, CDN, externa fonter, bilder eller script. Escape:a all importerad text, även titlar, fel, länkar och attribut. Visa källreferenser som text eller säkert protokollkontrollerade länkar med `rel="noreferrer noopener"`. Använd ingen `innerHTML` med importerat innehåll. Lägg en restriktiv CSP i dokumentet, med script och externa anslutningar avstängda. CSS kan ligga direkt i dokumentet.

Rapporten ska i ordning visa:

1. Analysstatus, separat datastatus/ekonomistatus och tydlig etikett för syntetiskt scenario eller importerade observationer.
2. Planerade platser, identifierade platser, fullständiga, saknade, statusfördelning och unika matcher. Alla nämnare ska stå utskrivna.
3. Kvalitetsbrister med slot/rad/felkod, tidsgränser och käll-/familjetäckning. Importerade offerter är inte verifierad insatsacceptans.
4. Scenarioantaganden, exakta formler, före/efter avrundning, avgiftsdefinition, spelnetto, projektnetto och ekonomiskt netto per alternativ period.
5. Okända kostnader, kapacitetsbrist, nollnämnare och skäl för ofullständig eller avvisad kontroll.
6. Regel-/format-/kalkylversion, indatahashar och deterministisk analyskontrollsumma. Hashar visar integritet, inte sanning.
7. Tydligt åtskild körningsmetadata och begränsningar: inget tekniskt godkännande är ett ekonomiskt bevis.

`analysis.json` ska vara deterministiskt: sorterade objektnycklar, stabila listordningar efter ID/slot/rad, UTF-8, inga NaN, Decimal som definierade strängar och pengar som heltalsören där avrundning gjorts. Ingen aktuell tid, slump, maskinsökväg eller elapsed time får ligga i analysobjektet. Filordningen inom samma JSONL är en del av filbyten; samma byte och antaganden ska ge exakt samma analysbyte. Semantiskt omordnade rader kan få annan indatahash men samma sakresultat när identiteterna är entydiga.

`run-metadata.json` innehåller körningstid, verktygsversion, plattform och faktisk exitkod. HTML kan visa denna metadata i ett särskilt avsnitt. Determinismkravet gäller analysobjektet och dess hash, inte tidstämpeln i metadata eller HTML-byten som innehåller den.

**Acceptans:** en rapportfil kan öppnas lokalt utan externa förfrågningar; saknade värden är tydliga. Färdig status ska inte kunna förväxlas med positiv ekonomi eller godkänt verkligt datamaterial.

## 7 Steg 5 Tester och syntetiska exempel

Skapa tre tydligt syntetiska exempel i var sin fixturemapp: `complete`, `incomplete`, `rejected`. Complete har giltiga tekniska data med exempelreferenser uttryckligen märkta syntetiska. Incomplete visar bortfall och okända kostnader. Rejected visar exempelvis duplicerat slot-ID. Ingen fixture ska utge sig för att vara hämtad från ett faktiskt bolag. Använd tmp_path för all export.

| Acceptansfall | Förväntat resultat |
| --- | --- |
| p=0,52, O=2,00, insats 1 000 öre, inga avgifter | +40 öre, alltså +0,40 kr, före kostnader |
| Samma med haircut 100 bp | +29,6 öre före öresavrundning, alltså +0,296 kr |
| Nettoedge redan 296 bp | Samma netto utan ett andra pris-/avgiftsavdrag; främmande from_price-fält avvisas |
| Vinstprovision respektive insatsavgift | Varje avgift dras exakt en gång enligt sin egen definition; O_eff under 1 avvisas |
| R=0 eller negativt och positivt mål | Ingen positiv ändlig baklängeslösning; inget divisionsfel |
| 54 kompletta av 60 planerade | 54/60=90 %, både med sex saknade rader och med sex failed/not_attempted |
| T60 och T55 för samma event | Två tillåtna platser, en match |
| Dubbelt slot-ID eller event/kind-par | Avvisad observationskontroll utan radering ur nämnaren |
| Dubbla JSON-nycklar, bool-pengar, fel typer, extra fält | Stabilt struktur-/tolkningsfel, ingen tyst coercion |
| Tidsfönster | t0, t0+30 och offertålder exakt 120 s godtas med övriga villkor; −1 mikrosekund, +30 s+1 mikrosekund, 120 s+1 mikrosekund underkänns |
| Tidsordning | Source efter beslut, received före source, saknad offset och spread över 60 s ger brist/avvisning enligt kontrakt |
| Okänd kostnad/tid | Påverkat netto null med orsak; opåverkade nettobegrepp förblir beräkningsbara |
| Säsong10 respektive kalenderår12 debiteringar | Två alternativa netton, ingen kostnadssumma av båda perioderna |
| Samma operation i flera matcher/slots | Kvot och request räknas en gång; olika kvitto under samma ID blir konflikt; unknown släpps inte automatiskt |
| Closingdata med importtid men utan källtid | Aldrig fullständig tidsriktig offert; inga fabricerade tider |
| Okänd familj och flera operatörer i samma familj | Ingen falsk oberoende familjetäckning |
| Noll platser och scenario_only | Null kvalitetsandel och ingen godkänd datagrind |
| Noll referensvolym, öppet kapital eller negativt saldo | Inga felaktiga kvoter; explicit otillräcklig kapacitet |
| HTML, javascript-länk och attributinjektion i text | Endast escaped text, inga exekverbara script/bilder/events |
| Existerande utmapp, symlänk/junction, URI/UNC, filflykt och ADS | Avvisas, befintliga filer och sentinel oförändrade |
| Filstorlek och radgränser | Exakta gränser accepteras, en enhet över avvisas även om filen växer under läsning |
| Avbrott/skrivfel mitt i export | Ingen giltig COMPLETE-markering eller framgångskod; nästa körning skriver inte över mappen |
| Identiska byte/antaganden två gånger | Identiska analysbyte och analyshash trots olika körningstid |
| Nätverk DB dotenv/config | Vakter blockerar försök; negativa kontrollprov visar att vakterna verkligen upptäcker förbjuden åtkomst |

Testvakterna installeras före första import av den nya modulen. Bevaka nätverksanslutning/DNS, `sqlite3.connect` och öppning av skyddade sökvägar. Kontrollera även att kärnimport inte laddar `jarvis.config`, `jarvis.db`, `jarvis.api`, AI-SDK eller transportbibliotek. CLI får läsa endast valda fixturefiler och skriva i tmp_path. Ett test som bara gör ingenting och sedan påstår ”inga nätanrop” räcker inte; försök ska fångas i ett avsiktligt negativt kontrollprov.

**Godkännande av steg 5:** ovanstående beteenden har aktuella testresultat och minst de tre exempelrapporterna är granskade. Kontraktsfel ska testas via verklig byteparsning och CLI-fel genom filsystemet, inte bara genom interna hjälpfunktioner.

## 8 Steg 6 Slutverifiering

1. Dokumentera ursprungs-HEAD, faktiska lokala ändringar och verktygsversioner. Skapa en ny daterad hashbaslinje före ändring; skriv inte över den gamla studiens manifest.
2. Kör riktade kärn- och CLI-tester. Kör därefter hela backendsviten med dotenv avstängd före import, syntetiska data, temporär DB och nät-/DB-vakt. Installera inte saknade beroenden.
3. Kör TypeScript utan skrivande incremental-data och produktionsbygge till separat utmapp. Oförändrad frontend ska ändå få relevant regression efter integrationen.
4. Kör befintliga Playwrightfall i en isolerad testkopia, med egen portkontroll, egna testprocesser och skärmbilder. Dagens 13 fall skriver explicita historiska paths; ett vanligt `--output` räcker inte. Om Chromium fortfarande saknas: markera E2E blockerad och be om separat installationsbeslut, utan att kalla kontrollen godkänd.
5. Granska exporterad HTML vid **390 och 1280 px**: läsbara rubriker, kostnadstabeller, långa ID/hashar, ofullständiga/avvisade rapporter, tangentbordslänkar och ingen horisontell sidöverströmning. En tabell får ha egen tydlig scrollbehållare. Spara nya skärmbilder under en ny verifieringsmapp.
6. Jämför samtliga tidigare käll-, regel-, migrations-, lås- och historiska rapportfiler med startbaslinjen. `odds_lab.py`, `odds_history.py`, gammal POLICY/version/hash och gamla rapporter ska vara oförändrade. Exakt tio roller ska kvarstå. Ägarens data ska inte läsas för att bevisa detta; redovisa att data inte öppnats.
7. Leverera ändrade filer, testkommandon, status per kontroll, exempelrapport, exitkoder och kvarvarande begränsningar. Avsluta egna processer även vid fel. Ingen commit, push, vanlig appstart eller pilot ingår om det inte beställs separat.

Det historiska manifestet har redan 81 radbrytningsavvikelser och fyra innehållsavvikelser mot dagens rena arbetskopia. Att köra dess skrivande verify för att få ett nytt grönt historiskt resultat är fel verifieringsmetod. Använd den nya baslinjen för oförändrat-skydd och redovisa den historiska skillnaden separat.

## 9 Arbetsintervall och beroenden

**D. Ny bedömning:** cirka **24–40 fokuserade utvecklingstimmar** för en utvecklare med kännedom om projektet, efter kontraktsgodkännande. Antaganden: befintlig Pythonmiljö räcker, inga externa data krävs, browserresursen kan tillhandahållas separat och inget API/UI ska byggas. Ungefär 5–8 timmar kontrakt/exempel, 7–12 kärna/kvalitet, 5–8 CLI/säker export och 7–12 tester/rapport/regression. Detta är ett planeringsintervall, inte uppmätt arbetstid eller offert.

Tidskostnad eller kvot för framtida datainsamling ingår inte. Inget belopp är godkänd budget och ingen uppskattning anger tid till lönsamhet. Privat verktyg kontra tjänst blockerar inte detta offlinebygge; datadelning, rättigheter och publik drift hör till eventuella senare uppdrag.

## 10 Beslutsruta och stoppunkt

**Godkänn ett enda uppdrag:** implementera den lokala offlinekontrollen med det granskade kontraktet, rena beräkningar, säker ny exportmapp och angivna tester.

**Berörda filer:** `backend/jarvis/odds_feasibility.py`, `scripts/odds_feasibility.py`, `tests/test_odds_feasibility.py`, eventuell separat CLI-testfil och `docs/odds-feasibility/` med svenska formatbeskrivningar och syntetiska exempel. En separat ny verifieringsmapp får tillkomma. Ingen annan befintlig produktkomponent behöver ändras utan ett konkret beroendefynd.

**Resultat:** en svensk fristående HTML-rapport och deterministiskt analysobjekt som skiljer teknisk kvalitet, scenarioantaganden, okända kostnader och ekonomiska nettobegrepp. Alla planerade slots och alla fel syns.

**Bevis:** riktade acceptansfall, full backendregression, frontendkontroller, isolerad E2E där resurser finns, HTML vid 390/1280 px och jämförelse mot ny hashbaslinje.

**Utanför:** insamling, leverantörsanslutning, betalda anrop, app-/workerdrift, kundkonton, ny prognosmodell, ändring av fryst modell, signalval, pappersspel, riktiga spel, insatshöjning, commit och publicering.

**Stanna** efter lokal leverans och verifieringsrapport. Saknade resurser ska redovisas som blockerade. Inga positiva ekonomiska scenarier eller tekniskt godkända rapporter får automatiskt starta nästa steg.

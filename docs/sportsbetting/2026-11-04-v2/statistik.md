# Statistik och försöksdesign – förslag v2

Datum: 4 november 2026, Europe/Stockholm. Detta är ett granskningsunderlag, ingen aktiverad modell eller datainsamling. Tids-, urvals- och beslutskriterierna är harmoniserade med huvudplanens v2 efter kritikeromgången; tidigare utkast är inte alternativa försöksvarianter.

## Vad som faktiskt granskats

| Kontroll | Evidensnivå | Resultat och begränsning |
|---|---|---|
| `odds_lab.py`, `odds_history.py`, gamla planen | Läst i kod/dokument | Komponentvis median, enkla bolags-ID:n, fast 10 kr, 5–30 % beräknad avvikelse och 1 % avdrag på decimalodds. Historik använder closingkolumner utan tidsstämpel. |
| Sparad rapport och kvalitetsfil | Uppgift i tidigare rapport, lokalt återläst | 760 matcher, 76 val, 6 vinster, 70 förluster, −23 659 öre. Dagklustrat intervall i rapporten: −80,35 till +30,63 % ROI; det rättar inte datans tidsfel. |
| Separat lokal beräkning av mediansummor från sparade CSV-filer | Verifierat genom körning | 3 820 giltiga kombinationer av målbolag och referenser; 3 425 summerar inte till ett inom 1e−12. Summor 0,9871875911–1,0086042323. För de 76 valda målen: 67 avvikelser; summor 0,9905196496–1,0047122757. Inget alternativt strateginetto beräknades. |
| Standardavvikelse i historiska valda returer | Verifierat genom körning | Stickprovsstandardavvikelse 2,518325 per satsad enhet. Litet, selekterat och historiskt material; ingen låst framtida variansskattning. |
| H1/H2, gränser och pilot nedan | Förslag | Numeriska beslutskriterier, inte skattade sanningar eller ägarbeslut. |

Mediansummorna visar ett konkret matematiskt fel om vektorn presenteras som en sannolikhetsfördelning. Storleken i detta material är liten jämfört med förlusten; fyndet bevisar inte orsaken till −31,1 % ROI. Enkel renormalisering skapar heller inte information marknaden saknat.

Referensbolagen är inte oberoende röster. Samma oddsleverantör, koncern och marknadsföljande kan göra tio varumärken till långt färre informationskällor. År 2024/25 fanns fem kvalificerande closingkolumnfamiljer (`1XB,B365,BF,BW,WH`), året efter sju (`B365,BFD,BMGM,BV,BW,CL,LB`). Dessa är kolumnprefix, inte verifierade oberoende leverantörsfamiljer. Skillnaden kan påverka både urval och resultat. De valda oddsen 4,03–29,00 och 55 bortaval av 76 motiverar separat kontroll av långskott och urvalskalibrering; de bevisar ingen viss felmekanism. Båda säsongerna är sedda utvecklingsdata för all framtida metodselektion.

## Två självständiga hypoteser

**H1, prognos:** En låst referens ger bättre prognoskvalitet än en förhandsvald enkel målprisbaslinje på nya matcher, inklusive de matcher och utfall som signalregeln väljer. Att vektorn summerar till ett är endast en nödvändig strukturkontroll.

**H2, ekonomi:** Samma låsta signalregel ger ekonomiskt relevant pappersnetto på nya matcher efter genomförandestress och samtliga projektkostnader inom fast kapital- och tidsram. H1 godkänner aldrig H2. H2 med ett positivt stickprovsnetto men stor osäkerhet godkänns inte heller.

Brier score och log loss bedömer probabilistiska prognoser; de är inte mått på accepterad åtkomst eller netto. Se den kontrollerade primärkällan [Gneiting och Raftery, 2007](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf), läst 2026-11-04. Påståendet att bättre prognosmått inte automatiskt innebär bättre spelnetto följer av att urval, pris och kostnader också ingår i beslutet; det är vår metodslutsats.

## En enda första huvudidé: A

Undersök ett svenskt målpris vid **T−60 minuter**, inte en ny fotbollsmodell, nya ligor eller fler trösklar. T−55 är en separat datadiagnostik för varaktighet; den får inte förbättra ett tidigare papperspris retroaktivt. Om en senare strategi använder den andra observationen måste dess beslut och kapitalreservation ske först efter den.

Följande är en möjlig enda framtida kandidat, ännu inte implementerad:

1. Exakt en svensk måloperatör och ett liga-ID registreras före första observationen. Välj operatör efter rättigheter och datakvalitet, inte efter historisk vinst. Okänd svensk identitet eller okänd målfamilj ger ingen signal.
2. Kompletta och tidsriktiga 1/X/2-priser krävs. Mottagning, validering och beslut ska ske inom [t0,t0+30 sekunder], där t0=T−60 minuter; observation före t0 används inte. Offertålder vid beslut 0–120 sekunder och spridning mellan godkända källtider högst 60 sekunder. Källtid får inte ligga i framtiden; beslutsunderlaget blir tillgängligt först när svaret mottagits och validerats. För sent svar loggas som bortfall.
3. Frysta familje-ID:n med dokumenterad proveniens. Uteslut målbolaget och hela dess kända familj. Okända samband räknas inte som oberoende familjer. Minst tre återstående dokumenterade familjer; kravet sänks inte om signalantalet blir noll. Detta påstår inte att resterande familjer är statistiskt oberoende.
4. Inom varje bolag: `q_j = (1/O_j) / sum_k(1/O_k)`. Behåll historikens plausibilitetskontroll 0,95–1,25 för summan av inversa odds som ett avvikelsefilter, inte som en kvalitetsgaranti. Inom varje familj medelvärdesbildas de trekomponentsvektorerna med lika bolagsvikt. Medelvärdesbilda sedan familjevektorerna med lika familjevikt. Resultatet ligger i simplex och en familj får inte extra vikt genom fler varumärken. Alla trekomponentsvektorer sparas; ingen power/Shin-variant ingår i första kandidaten.
5. Primär prisstress: `O_papper = floor(O_x10000 × 0,99) / 10000`. Nominell beräknad avvikelse `e = p_j × O_papper − 1`. Välj endast 5,00–30,00 % efter golvavrundning till baspunkter. Bland måloperatörens tre utfall väljs högst e, sedan fast ordning hemma/oavgjort/borta. Detta är en **kandidatsignal** baserad på en prisreferens, inte uppmätt sann fördel.
6. Fast 1 000 öre pappersinsats, högst ett valt utfall och en reservation per match, startkapital 100 000 öre utan påfyllning. Existerande och olösta reservationer dras från tillgängligt kapital. Framtida matchresultat och senare stängningsodds är separerade från beslutsdata.
7. Hypotetisk fördröjning 30 sekunder efter beslut antas för genomförandestress; prisåtkomst under dessa sekunder är okänd. Prisstressen är ett scenario som ersätter, inte kompletterar, ett annat uppmätt prisavdrag. Ändrat observerat pris före beslut kräver en ny beräkning med då tillgänglig information enligt samma regel. Ingen åtkomst före beslut ger inget spel. Saknat resultat efter reserverat spel ger fortsatt olöst exponering.

Trettio sekunders latens och 1 % prisavdrag är uttryckliga antaganden. De får inte kallas empiriskt kalibrerade. T−55-observationer kan senare användas för att undersöka storleken på ett relevant stressantagande, men femminutersförändring är inte ett mått på förändringen under trettio sekunder.

## Datapilotens numeriska beslut

Pilot: första 30 EPL-matcher i kronologisk ordning under 9 november–6 december 2026, lika avspark sorterad på event-ID, därefter högst tre dagar för resultatuppföljning till 9 december 23.59 Europe/Stockholm. Urvalet baseras på startens frysta matchlista. Ingen förlängning för att samla extra signaler. Färre än 30 planerade matcher inom perioden ger otillräckligt underlag. Framflyttningar loggas och räknas enligt huvudplanens ursprungliga urvalsram; inga ersättningsmatcher väljs för att förbättra utfallet. Startvillkor före 9 november krävs, annars startar inte versionen.

- 100 % av planerade observationsrader ska finnas, även misslyckade och tomma.
- Minst 27/30 T−60-observationer ska vara rätt match/marknad och inom tids-/ålderskraven. Separat krävs minst 24/30 med komplett svenskt målpris och minst tre giltiga referensfamiljer. Alla faktiskt använda signaler måste klara tidskraven. 90 % respektive 80 % är praktiska processgränser, inte snäva konfidensintervall för framtida täckning.
- Noll accepterade observationer med fel match, annan marknad, framtida källtid eller okänd målfamilj. Ett sådant fel stoppar användning för signal; rådata får bevaras som märkt avvikelse.
- Förhandsregeln för manuell kontroll är de första åtta kandidatsignalerna och de första åtta utan signal i beslutsordning, samtidiga sorterade på event-ID. Tillhörighet och urval avgörs online före resultat; inget senare hashurval används. Högst sexton kontroller, minst tolv genomförda och minst fyra per stratum krävs. Operatör, marknad, utfall och avspark ska matcha; minst 90 % av de kontrollerade priserna ska ligga inom 1 % relativ decimaloddsavvikelse vid högst 60 sekunder efter API-mottagning. Färre signaler eller otillåtna manuella kontroller ger otillräckligt underlag, ingen ny signalregel eller ersättningsliga. Avvikande priser loggas, aldrig ersätts med bättre retrospektiva priser.
- Rättigheter, svenska målidentiteten eller tillräckliga familjer kan vara okända. Det blockerar signaltestet även om API-fälten ser bra ut. Pilotresultat får då vara noll användbara signaler.

Godkänd pilot betyder endast att processen är tillräckligt lovande för att föreslå ett nytt avgränsat pappersförsök. Den betyder inte godkänd H1/H2, investeringsbudget eller accepterad insatskapacitet. Kostnads-, HTTP- och kreditgränser finns i huvudplanens datapilot; överskridande avslutar perioden med markerat bortfall och inga automatiska återförsök.

## Ett eventuellt framtida prognos- och papperstest

Detta är en möjlig framtida design att granska, inte en beställning att starta testet. Ett eventuellt nytt pappersförsök får registreras och börja tidigast 2027-01-01 och senast 2027-01-15, efter pilotslut, rapport, ny ägargranskning och frysning av kandidaten. Fast slutdatum är 2027-06-30. Pilotmatcher är utvecklingsdata och ingår aldrig i sluttestet. Hela den enda ligans då återstående matchlista registreras innan resultaten öppnas. Högst 380 unika matcher är ett tak för en hel säsong; det finns betydligt färre kvar efter en januaristart, och den faktiska återstående volymen är ännu inte schemaverifierad. Minsta fullurval 150 giltiga matcher och minsta signalurval 100 avgjorda signaler över minst 30 matchdagar är process- och analysgränser, inte bevisnivåer. Nås inte antalen i tid blir slutsatsen otillräckligt underlag, utan selektiv förlängning. Vid historiska 38 signaler per hel säsong är signalgränsen sannolikt inte nåbar i ramen; detta är ett konkret skäl att avstå från att beställa en H2-bekräftelse nu. Datapiloten får föreslås separat för informationsvärdet och inom huvudplanens föreslagna tak 0 kr utlägg, 0 AI-anrop och 12 timmars mänsklig tid (värderad till 2 400 kr).

### H1:s förhandsbestämda analys

Fullurvalets primärmått: multiclass Brier `mean(sum_j(p_j−y_j)^2)` på samma matcher för familjereferensen och måloperatörens marginalnormaliserade vektor. Rapportera parade skillnader, inte två ojämförbara urval. Log loss `−mean(log(p_utfall))` är sekundär; nollprognos ger oändlig förlust och ska inte döljas genom efterhandsklippning. Huvudkandidaten har strikt positiva oddsbaserade sannolikheter.

Kalibrering: fixa intervallen [0;0,10), [0,10;0,25), [0,25;0,50), [0,50;1] före data. Visa antal, medelprognos, observerad frekvens och osäkerhet för varje klass och för det valda utfallet. Tomma eller för små celler märks; ingen efterhandsomgruppering för ett snyggare resultat. Visa även rapportering på oddsintervallen [1;2), [2;4), [4;8), [8;∞) samt täckning och utfallsval. Dessa är diagnostik, inga ytterligare strategier.

Föreslagen sträng H1-grind: punktestimatets Brierförbättring minst 0,002 och nedre ensidiga 95-procentsgränsen för förbättring >0, i hela urvalet **och** i signalurvalet; log loss får inte försämras jämfört med baslinjen i något av dessa urval. Absolut kalibreringsavvikelse i signalurvalet inklusive övre 95-procents osäkerhetsgräns ska vara högst 0,05. Den senare avser den genomsnittliga valda sannolikheten mot vald utfallsfrekvens; intervall- och klassdiagnostiken måste dessutom vara redovisad och får inte dölja systematiska fel. Gränsen är en praktiskt vald tolerans, inte ett bevis att alla sannolikheter är korrekta. Godkänt fullurval men osäkert eller felkalibrerat signalurval ger inte H1-godkännande.

### H2:s förhandsbestämda analys

Primärt projektnetto efter samma prisstress/avgifter samt alla faktiska data-, AI- och beräkningskostnader. Arbetstid redovisas separat som ekonomiskt netto. Ekonomisk relevans sätts illustrativt till **100 kr per aktiv matchmånad**, alltså 1 000 kr per säsong vid antagna tio aktiva månader. Det är inte samma sak som 100 kr per kalendermånad (1 200 kr/år). Varken målet eller arbetstidsvärdet är ägarbeslut.

Förslag för att över huvud taget kalla resultatet robust nog att föreslå ett nytt begränsat försök: punktnetto minst det förhandslåsta proportionella relevansmålet i både huvudfallet och 3 % total prisförsämring; nedre ensidiga 95-procentsgränsen för projektnetto >0 i dessa två prisfall; ingen försörjning av resultatet från olösta exponeringar; maximal realiserad nedgång högst 300 kr och ingen övertrassering av papperskapital. Vid uppnådd nedgång 300 kr stoppas nya beslut; öppna exponeringar bevaras och kan göra slutlig nedgång större, vilket då redovisas som överskridande och inte godkänd riskgrind. Det är fortfarande endast ett pappersbeslut. Taket 300 kr är en föreslagen experimentgräns, inte accepterad riktig riskbudget.

Vid 10 kr och högst 380 val blir omsättningen högst 3 800 kr/säsong. Relevansmålet 1 000 kr kräver minst 26,32 % nettoavkastning före fasta kostnader, och vid 38 val 263,16 %. Därför är den begränsade 10-kronorsramen ekonomiskt svag även om en liten positiv fördel skulle finnas. Ett test kan undersöka data och falsifiera en signal, men kan inte rimligen marknadsföras som vägen till det månatliga målet inom denna volym.

### Osäkerhet, beroenden och stress

En förhandslåst analys kan använda 10 000 parade bootstrapdrag med seed 20261104 och hela Stockholm-matchdatum som primära kluster; samma analys med hela kalenderveckor är beroendekänslighet. Nollsignaldagar och samtliga försök följer med blocken; netto redovisas efter fasta kostnader för den ursprungliga fasta testperioden. Kluster är en beroendeapproximation, inte en garanti; samma lag och marknadsregimer kan ge längre beroenden. Rapportera antal datum och veckor och att intervall med få kluster är osäkra. En känslighetsanalys får inte ersätta primäranalysen med det mest positiva intervallet. Inga inferenser görs på enbart 30-matchspiloten. För modellselektion används endast utvecklingsdata; ett sluttest har en kandidat och en signalregel.

Stressscenarier ska inte väljas efter vinst:

| Scenario | Exakt ändring | Tolkning |
|---|---|---|
| Primärt | 1 % multiplicativt avdrag på decimalodds, ingen särskild enkelspelsavgift antas | Obevisat genomförandeantagande, inte svensk accepterad offert. |
| Pris | 3 % totalt avdrag på ursprungliga decimalodds, ersätter 1 % | Samma valda beslut för utfallsstress; sekundärt kan en separat märkt beslutsregelomprövning visa att ingen signal skulle lagts. Inget retroaktivt bästa val. |
| Icke-slumpmässigt bortfall | De 20 % kandidatsignalerna med högst beräknad avvikelse antas otillgängliga; antal avrundas uppåt, lika edge sorteras på event-ID | Låst rangbaserat stresstest utan resultatfält. Det är en efterhandsdiagnostik av antaget selektivt åtkomstbortfall, ingen påstådd onlineprediktor eller skattad verklig bortfallsfrekvens. |
| Källberoende | En dokumenterad familj i taget tas bort | Diagnostik av känslighet, inte sökning efter den mest lönsamma familjeuppsättningen. Under tre referensfamiljer blir ingen signal i en separat omprövning. |

Prisavdrag och en särskild avgift måste räknas med olika formler och aldrig dubblas. Prognosförbättring och ekonomiskt netto tabelleras separat. Stängningsodds är efterhandsdiagnostik, aldrig tidsriktig input eller sannolikhetsfacit.

## Kan en liten positiv fördel bekräftas i tid?

En egen styrkeillustration antar oberoende enhetsavkastningar med standardavvikelse 1, ensidigt α=0,05 och styrka 0,80. Normalapproximation ger `n ≈ ceil(((1,64485362695 + 0,84162123357) × sigma / effekt)^2)`. Detta är inte en slutlig försöksdimensionering; låga sannolikheter, kluster, drift och skattade stressfel kan kräva mer.

| Sann genomsnittlig edge efter genomförandeförlust, hypotetisk | Ungefärligt n vid sigma=1 | Säsonger vid 38 val | Säsonger vid hårda taket 380 val |
|---|---:|---:|---:|
| 1 % | 61 826 | 1 627,0 | 162,7 |
| 2 % | 15 457 | 406,8 | 40,7 |
| 5 % | 2 474 | 65,1 | 6,5 |

För 100 oberoende sådana spel är den grova tvåsidiga 95-procentshalvbredden 19,6 procentenheter. Historikens skattade standardavvikelse 2,518 är betydligt högre än illustrationens 1; n skulle skala med sigma², men historikens selekterade långskott är inte en legitim framtida planeringsgaranti. Slutsats: en liga och en rimlig kort tidsram kan inte förväntas bekräfta en liten varaktig nettofördel. Föreslå inte större insatser för att dölja detta informationsproblem.

## Beslutsregeln prövad på fem exempel

| Exempel, ej observationer | Beslut |
|---|---|
| ROI +5 %, omsättning 1 000 kr, spelnetto +50 kr och data/AI 100 kr | Projektnetto −50 kr: avsluta ekonomiversionen inom denna ram, även om prognoserna förbättrats. |
| Bra total Brier/kalibrering men signalernas observerade vinstfrekvens klart under förutsagd | H1 klarar inte signalgrinden; inget H2-godkännande. Avsluta kandidaten eller nytt separat utvecklingsuppdrag. |
| Positivt primärnetto som blir negativt vid 3 % total prisstress | Inte robust för föreslagen genomföranderam; avsluta versionen. Ingen efterhandsåtergång till 1 % som enda rapport. |
| Positivt punktnetto men intervallet omfattar stora förluster, eller för få signaler vid slutdatum | Otillräckligt underlag inom ramen. Ingen automatisk förlängning, höjd insats eller bredare liga. |
| H1-grind klarad, relevant positivt netto och positiv nedre gräns, positiv stress, giltig data, budget och nedgång inom tak | Värt att föreslå ett nytt begränsat pappersförsök. Fortfarande ingen rätt till riktiga insatser; faktisk acceptans och kontokapacitet är okända. |

Säkerhets- eller datastopp kan avbryta testet men får inte ometiketteras som lyckad lönsamhetsprövning. Alla stopp, modifieringar, modeller och negativa observationer bevaras. Agenternas enighet är inte evidens.

## Reproduktion av kontrollerna

Huvudplanens slutliga precisering av period och percentiler gäller: antal aktiva månader låses från det före start frysta matchschemat, en hel månad per kalendermånad med minst en planerad urvalsmatch även vid noll signaler. Relevansmålet är100kr gånger detta antal. Samma10 000 datumklusterdrag används för5:e percentilen som nedre ensidig95%gräns och95:e percentilen för övre kalibreringsgräns. Fasta kostnader för originalperioden dras exakt en gång i varje drag; nollsignaldagar ingår. Veckoblock är endast känslighetsanalys och får inte ersätta ett ogynnsamt primärresultat.

`statistik.py` i denna mapp är den fristående körbara versionen. Kör från projektroten med `.\.venv\Scripts\python.exe .\docs\sportsbetting\2026-11-04-v2\statistik.py`. Den läser endast lokala filer och importerar rena beräkningsfunktioner; den sparar `statistik.json` i förstudie­mappen med inputhashar. Den gör inga nätverksanrop och skriver inte driftdata. Följande kodfragment visar samma beräkning; ingen produktkod ändrades av förstudien.

```python
from pathlib import Path
from decimal import Decimal
from statistics import median, stdev
from math import ceil
import json
from jarvis.odds_history import read_season
from jarvis.odds_lab import normalize_prices

r = json.loads(Path('docs/odds-reports/2026-11-03-epl-paper-v1/resultat.json').read_text(encoding='utf-8'))
selected = {x['id']: x for x in r['ledger'] if x['decision']['selected']}
sums, selected_sums = [], []
for season, filename in [('2024/2025', '2425-E0.csv'), ('2025/2026', '2526-E0.csv')]:
    matches, _ = read_season(Path('data/odds-history/2026-11-03-epl-paper-v1', filename).read_bytes(), season)
    for match in matches:
        valid = []
        for quote in match['quotes']:
            p, total = normalize_prices(quote.odds)
            if Decimal('0.95') <= total <= Decimal('1.25'):
                valid.append((quote.book, p))
        if len(valid) < 4:
            continue
        for book, _ in valid:
            refs = [p for name, p in valid if name != book]
            total = sum(median(p[o] for p in refs) for o in ('home', 'draw', 'away'))
            sums.append(total)
            if match['id'] in selected and book == selected[match['id']]['decision']['book']:
                selected_sums.append(total)
for values in (sums, selected_sums):
    print(len(values), sum(abs(v-1) > Decimal('1e-12') for v in values), min(values), max(values))
print(stdev(x['profit_ore']/1000 for x in selected.values()))
for edge in (0.01, 0.02, 0.05):
    print(edge, ceil(((1.6448536269514722 + 0.8416212335729143)/edge)**2))
```

Inga produktkodstester, byggningar eller Playwrightkörningar krävs av just denna dokumentbilaga: inga produktfiler ändras. Kontrollerna ovan är verifiering av förstudieberäkningar, inte test av en ny bettingfunktion.

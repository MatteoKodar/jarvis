# Oddslabb – fotboll med simulerade insatser

Version `football-paper-v1`. Första implementationen 2026-11-03.

## Vad som finns

En separat sida **Oddslabb** i JARVIS. Den gör regelbaserad oddsjämförelse och bokför simulerade insatser. Inga nya agentroller, modellkörningar, bookmakerkonton, betalningar eller spelverktyg har tillkommit. Sidan fungerar endast i DEMO och använder egna tabeller i DEMO-databasen. Riktiga insatser är alltid avstängda; inget positivt resultat aktiverar dem.

**Ingen löpande oddsleverantör är ansluten.** Första versionen har ett syntetiskt exempel och manuell import av verkliga observationer. Detta är en fungerande grund för uppföljning, inte en genomförd framåtriktad lönsamhetsdemonstration. Inga verkliga framåtriktade signaler har samlats in av implementationen. Ett separat historiskt engångstest med verkliga arkivdata genomfördes senare samma dag, se resultat nedan.

## Börja i gränssnittet

1. Starta om JARVIS i DEMO efter uppdateringen. Migration 005 skapar labbets egna tabeller vid vanlig initialisering. Ingen driftdata behövs för verifieringen.
2. Öppna **Oddslabb** och återuppta systemet om det är pausat.
3. Välj **Visa syntetiskt exempel**. Sju påhittade matcher visar fyra signaler, två vinster, två förluster och tre avståenden. Summorna är förutbestämda testdata, inte internetfynd eller ett bevis på avkastning.
4. **Starta observationsserie** skapar en separat tom serie för verkligt material. Det görs inga externa anrop. Serien kan inte raderas eller återställas genom API eller gränssnittet. Exemplet blandas inte med den.
5. Kontrollerad data kan importeras en match i taget. Importmallen innehåller enbart påhittade värden; dessa ska ersättas. Mallens reserverade exempeladresser avvisas vid verklig import.
6. Registrera resultat för rätt marknad efter matchen och komplettera eventuella datakostnader. Exportera hela historiken som JSON.

En import med osäkert nätverkssvar kan upprepas med **Försök samma begäran igen**. Samma åtgärds-ID och innehåll ger en post. Vid inmatningsfel kan begäran stängas innan korrigerat innehåll skickas med nytt ID. Redan sparade observationer och resultat skrivs inte över.

## Marknad och provregler

- Endast fotboll, **1X2 efter 90 minuter inklusive tilläggstid**. Förlängning och straffar ingår inte. Ingen livebetting.
- Låtsaskapital 1 000 SEK, fast simulerad insats 10 SEK. Inga pengar överförs till labbet.
- Decimalodds lagras som heltal gånger 10 000. `25000` betyder `2.5000`. SEK lagras i heltalsören; vinstutbetalning avrundas nedåt till ören.
- Offerten ska innehålla alla tre utfall. Varje kandidat jämförs med minst tre **andra** färska käll-ID:n. Målbolagets offert ingår inte i dess egen referens.
- Referensen är medianen av de andra källornas normaliserade inversa odds: först `(1 / odds)` och därefter division med källans summa för samtliga tre utfall.
- Detta är en marknadsbaserad referens, inte verifierad verklig sannolikhet. Tre käll-ID:n bevisar inte tre oberoende bolag eller informationsursprung.
- Ögonblicksbildens offertålder får vara 0–120 sekunder. Offertsumman godtas för beräkning mellan 95 och 125 procent; övriga offerter avvisas och orsaken loggas.
- Ett försiktighetsavdrag på 1 procent görs på decimaloddset. Beräknad avvikelse efter avdrag ska ligga mellan 5 och 30 procent. Detta är provisoriska, versionsbundna provregler, inte bevisade vinsttrösklar.
- Högst en signal per match: högst beräknad avvikelse, sedan käll-ID och utfall. Om kapitalet inte täcker insatsen avstår systemet.
- Samma lagpar på samma matchdag i Europe/Stockholm blockeras även vid nytt ID, ändrad starttid eller omvänd lagordning. Sådana observationer kan inte användas för en ny signal; ovanliga verkliga dubbelmöten samma dag kräver separat metodhantering.

Samtliga importerade matcher sparas, även avståenden och kapitalbrist. Urvalet av vilka matcher ägaren importerar är däremot inte automatiskt eller oberoende kontrollerat.

## Framåtriktad uppföljning

Den verkliga observationsserien har en fast 30-dagarsperiod från skapandet. Den kan inte förlängas genom nya importer. Resultat och kostnader kan kompletteras efter periodens slut. Minst 100 avgjorda, icke makulerade signaler används som en praktisk granskningsgräns. Detta är **inte** en statistiskt härledd provstorlek eller bevisnivå. Om få signaler uppstår får serien status för lite underlag, även om enstaka vinster finns.

Backend kräver registrering före avspark med mer än en minuts marginal. Fångsttiden får vara högst 60 sekunder gammal och inte ligga i framtiden. Payloaden tillåter inga resultatfält vid oddsimport. Ett slutresultat får inte registreras före passerad ordinarie matchtid eller ha en framtida tidsstämpel. Resultatet avser uttryckligen 90-minutersmarknaden. Makulering återför låtsasinsatsen men tar inte bort datakostnader.

Importen bygger på uppgifter som ägaren lämnar. Backend kan kontrollera struktur, ordning och registreringstid, men inte att oddset verkligen var tillgängligt, att tidsstämpeln är äkta, att bolagen är oberoende eller att resultatkällan är korrekt. Gränssnitt och export märker därför materialet som manuellt importerat och ej oberoende verifierat. Ingen webbadress öppnas av labbet.

Efter hela perioden, tillräckligt antal avgjorda signaler och full uppföljning kan status visa **positivt observationsutfall – fortsatt osäkert**. Riktiga insatser förblir avstängda även då. En kort vinstsvit, ett positivt syntetiskt exempel eller en vald delmängd får aldrig användas som vinstbevis.

## Ekonomi och integritet

Bruttoresultatet räknar avgjorda pappersinsatser. Netto drar av alla angivna datakostnader, även för avstådda matcher. Prenumerations- och andra kostnader som saknas i importen kan kompletteras; lägg inte till samma kostnad två gånger. Kostnader är ägaruppgifter och inte fakturaavstämda. De registreras bara i labbet och ändrar inte JARVIS ordinarie budgetbokföring. Ingen riktig tjänst har köpts.

Disponibelt låtsaskapital drar även av öppna insatser. Netto-ROI använder avgjorda icke makulerade insatser som nämnare; saknas sådana visas inget procenttal. Största nedgång avser realiserat netto inklusive angivna kostnader och är inte en uppskattning av öppna positioners fulla risk.

Migration 005 skapar `odds_lab_runs`, `odds_lab_records` och `odds_lab_actions`. Observation, analysbeslut, resultat och kostnader sparas atomärt. Varje post binds till den föregående med SHA-256 och seriens huvudhash, så ändrade eller saknade poster kan upptäckas. Detta är integritetskontroll, ingen extern attest eller garanti mot en administratör som skriver om hela databasen.

Alla endpoints använder befintlig ägarautentisering, CSRF och Origin-kontroll. Okända schemafält avvisas, webbadresser får inte innehålla credentials eller queryparametrar, importstorleken är begränsad och verkliga spel stöds inte. Paus och nödstopp hindrar nya skrivningar. Läsning och idempotent upprepning av en redan sparad åtgärd fungerar fortsatt. DEMO-/LIVE-databaser hålls åtskilda.

## Nästa utvecklingssteg

Välj och granska en oddsdatakälla med dokumenterad åtkomst, faktisk täckning för 90-minuters-1X2 och en separat resultatkälla. Kontrollera användningsvillkor, uppdateringstid och total datakostnad före anslutning. En framtida betald hämtare behöver samma atomära reservations- och stoppprinciper som andra betalda anrop; denna version har ingen sådan hämtare.

Före en trovärdig lönsamhetsbedömning behövs även ett låst matchurval, automatisk loggning utan efterhandsurval, verifierad oddstillgänglighet, fullständiga kostnader, osäkerhetsanalys och senare data som inte användes för att välja provreglerna. Agenternas eventuella förklaringar måste hållas åtskilda från den deterministiska beräkningen och får inte presenteras som uppmätt sannolikhet.

Tekniskt underlag som lästes vid arbetet: [The Odds API:s officiella format och tidsstämplar](https://the-odds-api.com/liveapi/guides/v4/), [Betfairs förklaring av oddsmarginal](https://www.betfair.com.au/hub/education/overrounds/). Ingen leverantör är vald eller ansluten, inga priser har antagits och dessa sidor utgör inget lönsamhetsbelägg.

## Verifiering

Lokalt verifierat 2026-11-03 med befintliga beroenden, tillfälliga databaser och `PYTHON_DOTENV_DISABLED=1`:

- **168 backendtester godkända**, inklusive 36 nya Odds-labbfall. Slutkörning 68,64 sekunder. Kontroller omfattar bland annat färskhet, marknad/typer, referens utan målbolag, förlust/återbetalning, kostnader, tidsfönster, dubbla åtgärder, samtidighet, återstart, stopp, hashfel, saknade poster, API-skydd och fortsatt spärr för riktiga pengar även vid positivt utfall.
- **TypeScript och Vite-produktionsbygge godkända**, 1 583 moduler. Första försöket hindrades av byggverktygets läsning av överordnade kataloger i sandlådan; samma bygge passerade med utökad katalogåtkomst.
- **10 Playwrighttester godkända**, varav tre nya för Oddslabb och sju befintliga för kontrollcentral/A0. Datorvy 1 440 px och mobilvy 390 px granskades visuellt. Mobiltestet väntar på att sidomenyn lämnat vyn före skärmbilden; ingen horisontell överströmning.
- A0 behåller nio rapporter, femton simulerade steg och noll externa anrop. Exakt tio agentroller bevaras.

Testkommandon: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short`, samt `pnpm run build` och `pnpm run test:e2e` från `frontend`. Inga beroenden installerades, ingen `.env` ändrades och ingen ägardatabas användes för verifieringen. Syntetiska vinster verifierar programberäkningar, aldrig faktisk avkastning.

## Historiskt engångstest med kostnadsfria verkliga data

På ägarens begäran genomfördes 2026-11-03 ett privat historiskt test med låtsasinsatser. Två förhandsvalda, avslutade Premier League-säsonger användes: 2024/2025 och 2025/2026 från Football-Data. Endast två fasta, offentliga CSV-filer hämtades. Ingen kontoanslutning, löpande skrapning, modellträning, betald tjänst eller riktig insats ingick. Leverantören beskriver materialet som avsett för privatpersoners bruk; detta uppdrag publicerar eller säljer inte datasetet.

Kod och regler låstes lokalt **före filhämtningen** i `data/odds-history/2026-11-03-epl-paper-v1/protokoll.json`. Protokollets filhash är `903e76f0067fc2fe9449ef87011e920b1f4d7b8aeec86aacbe57dcc9e5dc13ac`. Råfilerna sparas med byteantal, käll-URL, hämtningstid och SHA-256 i samma mapp, som undantas från Git. Detta är lokal spårbarhet, inte extern förregistrering.

Analysen använder v1:s prisjämförelse, tre andra referenskällor, 5–30 procents avvikelse, en fast insats på 10 SEK och 1 procents avdrag på decimaloddset. Samma låtsaskapital på 1 000 SEK löper genom båda säsongerna utan påfyllning. Alla dagens val görs före dagens resultat används. Slutresultat skickas aldrig till urvalsfunktionen. Individuella closing-kolumner används; inga genomsnitts-/maximakolumner, börser eller Pinnacle. Pinnacle uteslöts före hämtningen på grund av leverantörens varning om inaktuella odds från juli 2025.

**Det historiska testet uppfyller inte v1:s tids- och färskhetskontroller.** Arkivet saknar exakta verifierade offerttider, så inga sådana tidsstämplar har fabricerats. Den delade rena prismatematiken används separat; historiska rader förs aldrig in i framåtriktade serier eller används för att låsa upp något.

| Säsong | Matcher | Låtsasspel | Vinster / förluster | Simulerat resultat |
| --- | ---: | ---: | ---: | ---: |
| 2024/2025 | 380 | 24 | 3 / 21 | +70,56 SEK |
| 2025/2026 | 380 | 52 | 3 / 49 | −307,15 SEK |
| **Totalt** | **760** | **76** | **6 / 70** | **−236,59 SEK** |

Slutsaldo är **763,41 SEK**. Totalt simulerat omsatt 760 SEK ger ROI −31,14 procent. Största realiserade nedgång i redovisningsordningen var 337,15 SEK. Alla 760 rader kunde tolkas; 684 matcher gav avstående. Täckningen var fem individuella closing-firmor första säsongen och sju den andra. Skillnaden i källtäckning begränsar jämförelsen mellan säsongerna.

Ett förhandsvalt, illustrativt dagklustrat bootstrapintervall för ROI blev −80,35 till +30,63 procent (5 000 dragningar, seed 20261103, 61 signaldagar). Intervallet täcker inte felaktiga/asynkrona odds, urvalsfel eller alla tidsberoenden. Varken den positiva första säsongen eller intervallet ger belägg för säker lönsamhet. Ingen parameter ändrades efter utfallet. **Dessa prisregler gav inte positivt utfall i den samlade historiska körningen.**

Utbetalningarna för samtliga 76 val dubbelkontrollerades med en separat Decimal-beräkning direkt från råkolumnerna och slutresultaten. Den gav samma summa, −23 659 öre. Rapporten innehåller både säsonger, förluster och avståenden; inga vinnande delmängder valdes ut.

- [Läs rapporten](odds-reports/2026-11-03-epl-paper-v1/rapport.html)
- [Alla matcher, val och avståenden](odds-reports/2026-11-03-epl-paper-v1/alla-matcher.csv)
- [Fullständig rapport med käll- och kodhashar](odds-reports/2026-11-03-epl-paper-v1/resultat.json)
- [Separat avstämningskontroll](odds-reports/2026-11-03-epl-paper-v1/datakontroll.json)

Återkörning från sparade byte är offline och hämtar ingen ny data. Den skriver till en ny rapportmapp för att bevara den ursprungliga leveransen:

```powershell
.\.venv\Scripts\python.exe scripts/odds_backtest.py run --data-dir data/odds-history/2026-11-03-epl-paper-v1 --report-dir docs/odds-reports/2026-11-03-epl-paper-v1-aterkorning
```

Senaste verifiering efter tillägget: **185 backendtester godkända** (inklusive 17 nya historikfall), **TypeScript/bygge godkänt**, **10 Playwrighttester godkända**. Historikrapporten granskades även i dator- och mobilvy. Inga ägaruppgifter, credentials, budgetposter eller framåtriktade serier användes eller ändrades i engångstestet. Riktiga spel och betalda anrop: **0**.

Nästa metodutveckling måste behandla dessa säsonger som redan sedda data. Eventuella nya regler ska därefter prövas på nytt, förhandsvalt material eller framåtriktade observationer; upprepad justering tills samma två säsonger visar plus är inget oberoende resultat.

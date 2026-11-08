# Verifiering av JARVIS bettingdemo

Byggomgång `betting-demo-v1`. Lokal implementation för `C:\Users\matte\jarvis`, utifrån HEAD `0e0707f1d103203c6e21c3d350019c9224b7f57f` och de befintliga lokala ändringarna. Inga commits eller pushar har gjorts.

## Verifierat resultat

Det fasta demot kan följas från skapad omgång genom analys, ägarbeslut, registrering av hela insatsbatchen och avräkning. Normalflödet, avstående, omladdning och förlorat simuleringssvar har verifierats i en isolerad webbläsarmiljö. Backendtester prövar dessutom alla tillståndsövergångar, samtidighet, återförsök, återställning vid fel, kapitalavstämning och skydd mot framtida resultat.

Detta är en lokalt körd syntetisk arbetsgång. Den är ingen färdig självständig bettingagent och visar ingen verklig lönsamhet. Alla förklaringar kommer från sparade deterministiska analysresultat och märks **Simulerat agentsvar – lokal demologik.** Ingen extern modell eller oddsleverantör anropas. Den nya arbetsgången behöver ingen worker; de äldre agentuppdragen gör det fortfarande.

Startguidens befintliga ingång **Öppna matchdemot** leder till samma sida som navigationens **Bettingdemo**. Äldre agentuppdrag och Oddslabb finns kvar som separata verktyg. Det nya demot skriver inte till deras historik eller JARVIS AI-budget.

## Testresultat

| Kontroll | Faktiskt resultat | Arbetsyta |
| --- | --- | --- |
| `pip check` | Godkänd, exit 0 | Befintlig `.venv`, inga installationer |
| Första riktade nya backendsvit | 51 godkända, 29,18 s | Temporära databaser i testkopian |
| Slutlig full backendsvit | **275 godkända, 140,51 s**, exit 0 | Alla 218 tidigare testfall samt 57 nya fall |
| TypeScript | `tsc --noEmit --incremental false -p tsconfig.json`, exit 0 | Testkopians frontend |
| Produktionsbygge | Vite 7.1.12, 1 594 moduler, exit 0 | Testkopians `frontend/dist` |
| Playwright | **18 godkända**, cirka 1,1 min, exit 0 | Separat API och worker på loopback, temporär DEMO-DB, syntetiskt testkonto |
| Visuell kontroll | Skärmbilder vid 1 440 px och 390 px granskade | Ny daterad mapp, inga gamla skärmbilder levererades över |

Playwright kördes med en redan installerad Google Chrome via `JARVIS_E2E_CHANNEL=chrome`. Ingen browser eller dependency installerades. Standardvalet utan denna variabel är fortfarande Playwrights Chromium. De 18 fallen omfattar 13 äldre fall, den befintliga startguidens uppdaterade test och fyra nya genomgående demotester.

Skärmbilder: [Dator med sparad analys](dator.png) och [mobil med avräknad omgång](mobil.png). Mobiltestet kontrollerar att sidans bredd inte överstiger 390 px. Tabeller får rulla i sin egen behållare.

## Tillstånd och transaktioner

```text
created → analyzed → approved → simulated → settled
              └──→ declined
created → no_bets
```

`no_bets`, `declined` och `settled` är terminala. Inget beständigt `completed` finns. En sammanfattning är en vanlig läsning.

Alla nya skrivningar använder `BEGIN IMMEDIATE` genom befintlig `db.connect(True)`. Kontroll av paus, aktuellt tillstånd, kostnader/insatser/avräkning och det sparade åtgärdssvaret sker inom samma transaktion. Unika nycklar skyddar varje kostnad och varje matchinsats per omgång samt varje övergångsregistrering.

Åtgärds-ID binds till normaliserat innehåll, omgång och operation. Samma begäran ger det tidigare svaret, även efter paus/nödstopp. Ändrat innehåll under samma ID ger konflikt. Två nya ID:n kan inte utföra samma övergång två gånger; exakt ett anrop lyckas. Dessa regler testas även för samtidigt godkännande/avstående och för en paus som konkurrerar med en insatsregistrering.

Backendtesterna injicerar fel mitt i kostnads- och insatsregistrering samt efter första avräknade spelet. Transaktionen återställer samtliga delskrivningar, inklusive ekonomi och åtgärdsregistrering. Testet av otillräckligt kapital verifierar att hela batchen avvisas och att omgången förblir `approved`.

## Kapital och kostnader

Varje omgång äger ett separat startkapital. Belopp från historiska omgångar summeras inte till en plånbok. Varken manuella insättningar, överföringar, insatsredigering eller andra strategier finns i det nya API:t.

```text
spelresultat = avgjorda utbetalningar − deras insatser
netto = spelresultat − simulerade analyskostnader
kapital inklusive öppna insatser = startkapital + netto
tillgängligt kapital = kapital inklusive öppna insatser − öppen insats
```

Kostnader uppstår endast när analysen sparas första gången. Kostnadsnyckeln är `(session_id, event_id, cost_kind)` för analysen; kostnader gäller även avstådda matcher. Att visa, godkänna, simulera eller avräkna debiterar inte analysen igen. Ett nytt åtgärds-ID kan inte starta om analysen i samma omgång. Ett felaktigt scenario med större obligatorisk kostnad än startkapitalet avvisas före skapande.

Standardsjuans observationer, kostnader och resultat återanvänder samma data som äldre `odds_service._synthetic`, utan att återanvända dess redan avräknade serie. De befintliga reglerna och den frysta `POLICY` ändras inte. Ett regressionstest jämför det nya urvalet med äldre v1-beräkning för samtliga sju observationer.

| Steg i standardomgången | Kostnad | Spelresultat | Öppet | Kapital inkl öppet | Tillgängligt |
| --- | ---: | ---: | ---: | ---: | ---: |
| Skapad | 0 öre | 0 öre | 0 öre | 100 000 öre | 100 000 öre |
| Analyserad eller godkänd | 140 öre | 0 öre | 0 öre | 99 860 öre | 99 860 öre |
| Hela insatsbatchen registrerad | 140 öre | 0 öre | 4 000 öre | 99 860 öre | 95 860 öre |
| Avräknad | 140 öre | +950 öre | 0 öre | 100 810 öre | 100 810 öre |
| Avstått efter analys | 140 öre | 0 öre | 0 öre | 99 860 öre | 99 860 öre |

Fyra spel ger två vinster och två förluster. Utbetalningen är 4 950 öre, spelresultatet +950 öre och netto efter kostnader +810 öre. Detta är samma förutbestämda exempel som tidigare, inte konstruerad förbättring eller verklig vinst.

Det oberoende referensfallet har också verifierats genom hela API-arbetsgången: start 100 000 öre, två insatser à 10 000 öre, analyskostnad 1 000 öre, effektivt odds 2,00, en vinst och en förlust. Efter analys finns 99 000 öre tillgängligt. Efter insatsregistrering finns 79 000 tillgängligt och 20 000 öppet. Efter avräkning är utbetalningen 20 000, spelresultatet 0, netto −1 000, öppet 0 och slutkapital 99 000 öre. Avstående efter samma analys lämnar också 99 000 öre och inga insatser. **Detta är endast en separat testfixture, inte ett valbart scenario eller en ändrad standardinsats.**

## Frysta underlag och resultatgräns

Vid skapande sparas scenarioversion, hela regelunderlaget, motor-/förklarings-/avräkningsversioner, startkapital, fast insats, observationer, simulerade tider, kostnadsdefinitioner och separata avräkningsdata. Vid analys sparas kontroller, avståendeskäl, förslag, exakta synliga förklaringar, version och innehållshash. Beslut sparar denna version/hash och verklig beslutstid. Insatser, resultat, utbetalningar och ekonomiska sammanställningar sparas vid sina respektive övergångar.

Det finns två uttryckliga analysgränser: `ScenarioAnalysisInput` och `AnalysisInput`. De tillåter inga resultatfält. Tjänstelagret bygger dessa begränsade objekt **innan** analysfunktionerna anropas. Att ändra framtida resultat ger exakt samma analys, urval, förklaringar och analysens innehållshash. Den interna hela scenariohashen skyddar även avräkningsunderlaget men lämnas inte till analysen.

Alla nya API-svar byggs genom uttryckliga fältlistor. Före `settled` exponeras inga slutresultat, målantal, avräkningsdata eller framtida utbetalningar i detalj, listning, analys-/beslutssvar eller generell `/api/state`. Omgångens historik innehåller övergångar och verkliga tider, inte framtida resultat. Ingen ny generell export finns.

Historiska GET-anrop använder sparad analys, sparade förklaringar och sparade ekonomiska värden; de analyserar eller avräknar inte om något. Ändrad kod/scenariogenerator prövas i ett regressionstest som förbjuder återbyggnad, omanalys och ny avräkning under historikläsning. Äldre skapade omgångar med en framtida otillåten motorversion ska blockeras vid ny analys, inte tyst tolkas med andra regler. Motsvarande spärr finns för avräkningsversionen.

## Klockor och åtkomst

Matchernas gamla syntetiska datum skickas explicit till demots offertkontroller. Ingen systemklocka ändras. Ägarautentisering, sessionsgiltighet, verkliga registreringstider och befintlig verklig import använder fortfarande verklig tid. Ett nytt test för utgången session använder dagens autentiseringslogik; den simulerade matchklockan håller inte sessionen vid liv. Hela äldre importsviten passerar.

Ägarinloggning, CSRF och Origin-skydd är kvar. DEMO-behörighet kontrolleras även vid sparad replay. LIVE-databasen är separat och det nya demot kan inte användas i LIVE. Exakt tio roller kvarstår; ingen modell får terminal, ägarcredentials eller muterande administrationsverktyg.

## Ändrade och nya filer

Nya produktfiler:

- `backend/jarvis/betting_demo.py`: rent scenario, begränsade analysobjekt, beräkning, förklaringar och avräkning.
- `backend/jarvis/betting_demo_service.py`: beständig state machine, åtgärdsidentiteter, transaktioner och fältbegränsade lässvar.
- `backend/migrations/007_betting_demo.sql`: endast nya demotabeller och unikhetsvillkor.
- `frontend/src/BettingDemo.tsx` och `frontend/src/betting-demo.css`: sammanhängande resa, sparad historik och säkert återförsök.

Integrationer i befintliga filer:

- `backend/jarvis/api.py`: autentiserade DEMO-endpoints och samma storleksgräns som Oddslabb. Tidigare idempotensrättning bevarad.
- `frontend/src/main.tsx` och `navigation.ts`: en ny avgränsad demosida. Befintliga lokala tillägg till startguiden bevarade och vidareutvecklade.
- `frontend/src/DemoGuide.tsx` och `demo-guide.css`: befintlig ingång leder till det sammanhängande flödet; äldre separata verktyg ligger i en extra informationsdel.
- `frontend/playwright.config.mjs`: valfri redan installerad browserkanal via miljövariabel; standardinställningen bevarad.
- `README.md`: implementerad resa, kapitalmodell, framtidsgräns och testinstruktion.

Tester:

- `tests/test_betting_demo.py`: 57 fall inklusive den kompletta tillståndsmatrisen.
- `frontend/e2e/betting-demo.spec.ts`: fyra genomgående browserfall.
- `frontend/e2e/demo-guide.spec.ts`: den befintliga lokala guidens test är anpassat till den nya ingången; ett redigerbart äldre agentuppdrag kan fortfarande öppnas utan att arbete startar.

Underlag, bytehashar, slutlig fillista och testloggar finns i denna mapps `evidence/`. Äldre migrationsfiler, den frysta oddsmodellen, gamla oddsrapporter, låsfiler och befintliga lokala rättningar ska vara oförändrade utanför de uttryckliga integrationerna ovan. Alla tidigare lokala ändringar lästes in i testkopian; inga arbetskopior slogs ihop.

## Isolering och kvarvarande gränser

En separat källkopia byggdes under granskningsarbetsytan. Den ursprungliga arbetskopian ändrades först vid överföringen av färdiga verifierade filer. Före varje projektimport sattes `PYTHON_DOTENV_DISABLED=1`, DEMO, avstängda betalda anrop och extern research, temporär datakatalog samt borttagen extern API-nyckel. Bytecode och pytest-cache stängdes av. En audit hook i hela backendsviten nekade externa sockets/DNS, `.env`/skyddade datafiler och SQLite utanför testområdet. Den registrerade **inga förbjudna försök**.

Playwright använde en temporär DEMO-DB, syntetiskt testkonto och den befintliga testserverns separat inneslutna API/worker. Testservern behövdes för äldre testfall; det nya demot skapar inga workeruppgifter. Testkopian gjorde att gamla testskärmbilder endast skrevs över i kopian. Båda testprocesserna avslutades av testserverns teardown, och port 8765 kontrollerades som ledig efteråt. Ingen vanlig appinstans startades för ägaren. Inga ägardata, `.env`, lösenord eller ägarbackuper öppnades.

Inga kontroller är blockerade för den här leveransen. Detta innebär inte att verklig data, faktisk oddstillgänglighet, leverantörskostnader, extern AI, lönsamhet, publik drift eller lastkapacitet är verifierade. `no_bets` och otillräckligt kapital testas med interna syntetiska fixtures; det publika standardscenariot ger alltid fyra förslag och tillräckligt kapital. Inget generellt scenarioverktyg eller individuell insatsredigering finns.

## Ägarens senare test

Ingen app har startats åt dig. När du senare själv startar eller startar om backend med befintlig installation, kör i DEMO och logga in som vanligt. Migration 007 skapar nya demotabeller vid uppstart. Den nya frontendens produktionsfiler ingår i den lokala leveransen.

Välj **Översikt → Öppna matchdemot**, återuppta uttryckligen om paus visas och följ de sex stegen i README. Prova gärna att ladda om efter godkännande, avstå från en annan omgång och öppna den första omgången igen. Kontrollera att varje omgång visar sitt eget kapital. En redan körande backend måste startas om av dig för att läsa den nya koden.

Stoppunkt: lokal implementation och verifiering. Ingen vanlig appstart, extern anslutning, ny AI-modell, oddsinsamling, riktigt spel, installation, commit, push eller publicering ingår.

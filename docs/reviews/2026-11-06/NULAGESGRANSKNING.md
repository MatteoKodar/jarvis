# Teknisk nulägesgranskning av JARVIS

Datum: 6 november 2026, Europe/Stockholm. Mottagare: projektägaren.

Bevislägen: **A** = verifierat genom denna körning; **B** = styrkt genom kodläsning; **C** = dokumentuppgift som inte verifierats på nytt; **D** = hypotes eller öppen fråga. Ett godkänt test gäller den angivna testmiljön och innebär inget belägg för lönsamhet.

## 1 Slutsats och rekommenderat nästa uppdrag

**A/B. JARVIS har en implementerad lokal kontrollcentral, ett beständigt internt granskningsflöde och ett separat papperslabb.** Den granskade basversionen klarade 203 backendtester, TypeScript och ett produktionsbygge. Ingen aktuell webbläsarverifiering kunde göras eftersom det förväntade Chromium-programmet saknas. Modellerna har ingen ansluten oddsfeed eller spelintegration.

**A. Två fel bekräftades trots den gröna befintliga testsviten:** ändrat innehåll med samma åtgärds-ID kvitterades som lyckat för manuella kostnader respektive arbetsomgångar, medan bara den första begäran hade sparats. Efter ägarens senare besked ”du får ändra kod” rättades enbart dessa fel, med regressionstester. Rättningen ändrar inte den frysta oddsmodellen. Slutresultat: **218 godkända backendtester, 98,56 s**. Baslinje och rättad kod redovisas separat nedan.

**B/D. Rekommenderat nästa avgränsade bygge är ett rent offlineverktyg för ekonomi och datakvalitet**, efter granskning av [byggspecifikationen](BYGGSPECIFIKATION.md). Det behövs för planerade observationsplatser, bortfall, källfamiljer och okända kostnader. Dessa behov täcks inte av dagens papperslabb eller historikskript. Det nya verktyget ska analysera uttryckligen angivna lokala filer och skriva en ny rapport, utan att skapa signaler, pappersspel eller externa anrop. Rekommendationen gäller utvecklingsnytta; den lovar ingen ekonomisk avkastning.

## 2 Arbetskopia version och lokala avvikelser

**A. Följande lokala tillstånd kontrollerades innan testkörning och ändring:**

| Arbetskopia | Källkod | Branch och HEAD | Remote | Status före arbetet |
| --- | --- | --- | --- | --- |
| `C:\Users\matte\jarvis` | Ja, backend, frontend, tester och dokumentation | `main`, `0e0707f1d103203c6e21c3d350019c9224b7f57f` | `https://github.com/MatteoKodar/jarvis.git` | Ren, inga relevanta ospårade källfiler |
| `C:\Users\matte\Documents\Codex\2026-11-06\jkag-x20` | Ja | `main`, samma fullständiga HEAD | Samma remote | Ren |
| `C:\Users\matte\OneDrive\Dokument\ChatGPT\Jarvis odds` | Nej; endast `.git` före granskningsarbetet | `master`, ingen commit; `rev-parse --verify HEAD` saknar revision | Ingen remote visades | Tomt repo före granskningsutdata |

**A/B. Underlaget är `C:\Users\matte\jarvis`, eftersom det är ägarens uttryckliga destination och innehåller rätt JARVIS-projekt.** Rotens `AGENTS.md`, README, fotbollsfokus, exakt tio roller och angiven remote överensstämmer. Tillgängliga överordnade regelplatser kontrollerades; ingen ytterligare tillämplig `AGENTS.md` påträffades i denna kopias underkataloger. Den äldre kopian användes endast för versionsinventering, inte för testresultat eller slutsatser om kod.

Git krävde en för kommandot avgränsad `-c safe.directory=C:/Users/matte/jarvis`, eftersom sandlådan kör med ett annat Windowskonto. Ingen global Git-inställning ändrades. Ingen fetch, pull, kloning, commit eller push utfördes. Remote-adressen är lokal konfiguration; GitHubs aktuella innehåll har inte verifierats.

**A. Baslinjen omfattar SHA-256 för 137 versionshanterade filer utanför `data/`, i [baseline.json](evidence/baseline.json).** `.env` och driftdata ingår inte. HEAD är oförändrat efter arbetet, men slutleveransen innehåller avsiktliga arbetskopieändringar i:

- `backend/jarvis/api.py`: kontroll av innehåll vid upprepning av manuell kostnad.
- `backend/jarvis/service.py`: kontroll av mål, tak och uppgiftstyp vid upprepning av arbetsomgång.
- `tests/test_request_identity.py`: nya tester för konflikter, återstart, stopp och samtidighet.
- Denna nya granskningsmapp `docs/reviews/2026-11-06/` med rapport, specifikation och underlag.

Commit-ID ensamt beskriver därför **inte** slutleveransen. [delivery-manifest.json](evidence/delivery-manifest.json) identifierar de rättade filernas byte och jämförelsen med den separat testade kopian. Inga andra befintliga projektfiler ska avvika från granskningsbaslinjen.

**B/C. Dokument och beslut:** samtliga efterfrågade dokument finns i vald kopia: `README.md`, `docs/ODDSLABB-FOTBOLL.md`, `docs/VERIFIERING.md`, v2-planen samt ekonomi, statistik, datakällor, kritikergranskning och implementationsuppdrag under `docs/sportsbetting/2026-11-04-v2/`.

- **B. Aktivt mål:** fotboll, 1X2 efter ordinarie tid och simulerade insatser enligt `focus.py`, `roles.py` och migration 006. Riktiga spel är avstängda.
- **B. Arkiv:** affärsidéresearch, internetskanning, Researchlabb A0 och äldre A1-protokoll. API:t nekar nya A0-körningar; rena arkivhjälpare och tester finns kvar.
- **C. V2-planen:** offlineverktyg, familjeseparerad framtida referens, datapilot och bekräftande studie är förslag. Datum och förslagsstatus ger inget genomförandetillstånd. Den här leveransen aktiverar inget av dem.
- **B/C. Dokumentavvikelser:** README:s snabbstart pekar på en annan äldre mapp; LIVE-avsnittet beskriver Wikipedia-behörigheter som aktiva fotbollsroller inte längre har. Kodens roller saknar det verktyget, och `snapshot().integrations.research` är `false`. Dokumentens äldre testantal är historiska och ska inte ersätta resultat i avsnitt 4.
- **D. Produktfrågan:** privat verktyg eller tjänst för andra är fortfarande öppen. Ett lokalt offlineverktyg kräver inget svar; konton för kunder, prenumerationer och publik drift ingår inte.

## 3 Funktionstabell

Kodvägarna nedan är relativa till `C:\Users\matte\jarvis`. **”UI B” betyder att vyn har lästs i kod; den har inte prövats i webbläsare under granskningen.** Testnamnen anger befintlig täckning, inte att varje tänkbar situation täcks.

| Funktion | Kodväg och UI | Lagring | Befintliga tester | Bevisläge | Begränsning |
| --- | --- | --- | --- | --- | --- |
| Första ägarkonto | `auth.create_first_owner`, `api.setup_owner`; första-start-vy i `main.tsx` | `owner`, `sessions` | `test_first_run.py` | Backend A/B, UI B | Lokal HTTP-origin och loopback; inget fleranvändarsystem |
| Inloggning session utloggning | `auth.login/authenticate`, `/api/login`, `/api/logout`, `api.ts` | Scrypt-hash, hashat sessionstoken, försök per IP | `test_core.py`, `test_first_run.py` | A/B | Proxy, HTTPS-drift och extern säkerhetsrevision inte verifierade |
| Ägarbehörighet Origin CSRF | `auth.authenticate`, `origin_check`, beroenden i `api.py` | Sessionens CSRF och giltighet | `test_csrf_origin_and_extra_fields`, åtkomsttester | A/B | API-skydd verifierat med TestClient; ingen bred penetrationstestning |
| Uppdrag och VD-förslag | `service.start_round/create_proposal`, `worker.finish`; formulär och beslutskort | `tasks`, `runs`, `proposals` | Komplett kedja, omgångsidempotens | A/B | Statuschatten skapar inte modelluppdrag; kodutkast exekveras inte |
| Beslut och revidering | `service.decide/revise`, `/api/proposals/...` | Versionsbundna digest och `approvals` | Dubbelgodkännande, samtidighet, revision, utgång | A/B | Godkännande köar internt arbete; ingen extern handling genomförs |
| Specialist och kritiker | `worker.execute/finish`, `demo.run`, `live.run` | Uppgifter, resultat, rapporter i `files` | `test_complete_chain_and_persistent_result` | DEMO A/B, verklig LIVE D | Högst en specialist följd av kritiker; fasta DEMO-svar |
| Kö och samtidighet | `worker.claim`, `db.connect(True)` | `tasks`, `runs`, lease | Två samtidiga, idempotens, avbrott | A/B | Ingen långvarig belastningsmätning; processpuls betyder inte tillstånd att arbeta |
| Paus nödstopp sena svar | `dispatch.control/authoritative`, `worker.claim/finish/main` | `settings`, `dispatch_control.epoch`, operationer | Stopp före/efter sändningsmarkör, sent resultat efter stopp/återuppta | A/B | Redan skickat leverantörsanrop kan debiteras; avbrott är ingen återbetalning |
| Begränsat schema | `schedule.tick`, `/api/schedule`, `Schedule.tsx` | Schema, versions- och dagsnycklar | `test_schedule.py` | A/B, UI B | 1–7 omgångar, högst sju dagar, ett VD-jobb per dag |
| Budgetreservation och prisprofil | `budget.reserve/totals`, `dispatch.pricing/prepare/checked` | Heltalsören i `reservations`, `costs` | Samtidiga reservationer, prisbyte, gränser | A/B | Konfigurerat pris är inget automatiskt verifierat aktuellt leverantörspris |
| Kostnad återföring okänd debitering | `dispatch.complete/abort_in/recover`, `/api/.../reconcile` | `held/released/settled/unknown/reconciled` | SDK-mock, krasch och avstämning | A/B | Tokenbelopp uppskattas; ägaravstämning läser inte fakturor automatiskt |
| Manuella kostnader och omgångsreplay | `/api/costs`, `service.start_round` | Befintlig post under åtgärds-ID | Tidigare identisk replay; nu även ändrat innehåll | A, rättad | Konflikt kräver att ägaren kontrollerar den redan sparade posten |
| Syntetiskt och framåtriktat Oddslabb | `OddsLab.tsx`, `odds_service.start/_import` | Egna `odds_lab_*` i DEMO | `test_odds_lab.py` | Backend A/B, UI B | Manuell import; ingen feed, planerad fullständighetsnämnare eller familjeregister |
| Referens signal och avräkning | `odds_lab.normalize_prices/select_price_signal/settlement` | Beslut, fasta regler och utfall i hashlänkad historik | Referens utan målbolag, kapital, tidsregler, avräkning | A/B | Komponentmedian är ingen garanterat normaliserad vektor; tre ID:n är inte tre oberoende familjer |
| Resultat kostnader historik export | `odds_service._result/summarize/_load`, API-export | Append-only-poster och huvudhash | Dubbletter, kostnader, stopp, manipulering och saknade poster | A/B | Endast angivna kostnader; hash är integritet, inte uppgifternas sanningshalt |
| Historisk arkivanalys | `odds_history.py`, `scripts/odds_backtest.py` | Lokala rapportfiler, fryst protokoll | `test_odds_history.py` med syntetiska CSV | A/B; gamla verkliga resultat C | Closingdata saknar tidriktiga offerter. Ingen verklig arkivreplay gjordes nu |
| AI och externa källor | `live.py`, `external_http.py`, `research.py`, `dispatch.py` | Sändningsmarkör, resursram, användningskvitto | `test_live_adapter.py` med riktiga SDK-lager och mockad innertransport | Mockflöden A/B, extern drift D | Exakt tio Agents, `tools=[]`, inga handoffs/terminal/credentials; Wikipedia arkiverat för aktiva roller |
| Dokument rapporter och SSE | `documents.py`, `/api/files`, `/api/events`, Reacts dokumentrendering | Tillåtna dokumentfiler, DB-rapporter och händelser | `test_documents.py`, filåtkomsttester | Backend A/B, UI B | Dokumentvyn listar gamla protokoll, inte hela v2-studien; SSE-avbrott över serveromstart inte komplett verifierat |

**B. Säkerhetsgränsen ligger i backend.** Modellen får inga muterande administrationsverktyg. `dispatch.authoritative` godtar endast modell- och Wikipediaoperationer i LIVE och kontrollerar uppgift, fas, lease, epoch, prisprofil och roll från databasen. Den stödjer inte oddsinsamling. DEMO kör `demo.run`; LIVE-fel har ingen automatisk DEMO-fallback.

## 4 Aktuella verifieringsresultat

**A. Verktyg:** Python 3.12.14, Node 24.22.1, pnpm 11.25.0, pytest 9.1.1, TypeScript 5.9.3, Vite 7.1.12 och Playwright 1.56.1. Alla 51 tillämpliga Pythonpaket i låsfilen matchar installerade versionsnummer; `pip check` rapporterade inga trasiga beroenden. Se [tool-versions.json](evidence/tool-versions.json).

**B/A. Isolering före första projektimport:** installerad `python-dotenv` har stöd för `PYTHON_DOTENV_DISABLED=1`, vilket sattes i föräldraprocessen. Även DEMO, avstängda betalda anrop/research, temporär datakatalog, test-origin, testcookie och avstängd bytecode sattes före import; `OPENAI_API_KEY` togs bort. Pytest-plugin-autoladdning och cacheprovider stängdes av. En audit hook nekade `.env`, läsning av originalets `data/`, SQLite utanför granskningsområdet samt externa socket-/DNS-anrop. Loopback tilläts för TestClient/asyncio. Ingen vanlig appserver eller workerprocess startades.

LIVE-testerna sätter själva syntetiska prisuppgifter och testnyckel samt aktiverar LIVE i temporär DB. De granskade transporterna ersätts med mockar; nätvakten ligger kvar. Det är därför korrekt att säga **offlineverifiering av LIVE-koden**, inte att verklig modellåtkomst eller fakturering har verifierats. Två granskade subprocessfall använder samma testdata och avstängd dotenv: CLI-backup av test-DB respektive ett separat anropsskyddstest. Ingen ägarbackup öppnades.

| Kontroll och arbetskatalog | Kommando och utdata | Resultat och exitkod | Felklass eller begränsning |
| --- | --- | --- | --- |
| Beroenden, originalroten | `.venv/Scripts/python.exe -B -m pip check` | A: godkänd, exit 0 | Ingen installation gjord |
| Backend före rättning, originalroten | Pythonrunner → `pytest.main(['-q','-p','no:cacheprovider','--tb=short','--basetemp',TEMP,'--junitxml',EVIDENCE])` | A: **203 passed, 90,72 s**, exit 0 | Testdata och JUnit utanför originalet |
| TypeScript, originalets `frontend` | `node node_modules/typescript/bin/tsc --noEmit --incremental false -p tsconfig.json` | A: godkänd, exit 0 | Ingen tsbuildinfo skrevs |
| Produktionsbygge, samma katalog | `node node_modules/vite/bin/vite.js build --configLoader runner --outDir TEMP/frontend-dist` | A: godkänd, exit 0, 1 590 moduler | Runner laddar samma konfiguration utan att skapa `.vite-temp` i originalets node_modules |
| Playwright-inventering, samma katalog | `node node_modules/@playwright/test/cli.js test --list` | A: 13 testfall i fyra filer, exit 0 | Listning kör inte testfallen |
| Playwright-browser | `chromium.executablePath()` och filkontroll | A: förväntat program saknas | **Miljöfel, E2E blockerad**, ingen testsvit startad |
| Riktad felreproduktion före rättning, originalroten | [reproduction-runner.txt](evidence/reproduction-runner.txt), egen temporär DB | A: ändrad kostnad och omgång gav båda HTTP 200; originaldata låg kvar | Produktfel F01/F02 |
| Backend efter rättning, separat källkopia | [backend-final-runner.txt](evidence/backend-final-runner.txt), motsvarande fulla kommandorad och nya `--basetemp`/JUnit-utdata | A: **218 godkända backendtester, 98,56 s**, exit 0 | Samma versionsbundna källa plus redovisad patch; inte den äldre arbetskopian |
| Riktad felreproduktion efter rättning | Samma runner, ny test-DB och rättad källkopia | A: båda ändrade begärandena ger HTTP 409; första begäran ger HTTP 200 | Databasen innehåller fortfarande endast den första begäran |

Exakta miljövariabler, arbetskataloger och kommandon finns i [KORNINGAR.txt](evidence/KORNINGAR.txt), loggar och JUnit i `evidence/`. Första försöket till felreproduktion använde en alltför strikt nätvakt som även stoppade Windows asyncions interna loopback-socket. Det var ett **fel i granskningsinstrumenteringen**, inte ett produktfel. Den riktade omkörningen tillät endast loopback och gav produktfynden ovan. Inga produkttester ändrades för att få baslinjen grön.

Förväntat Chromium: `C:\Users\matte\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe`. Även listning av browserinstallationer (`install --list`, en inventering utan installation) saknade katalogen `.links`. Inga beroenden eller browserresurser installerades. Dokumentationens tidigare `data/browsers` finns inte i vald kopia. Detta underkänner inte backendtester eller bygget, men de 13 webbläsartesterna och aktuell visuell UI-kontroll förblir **inte verifierade**.

**B. E2E-biverkningar:** `playwright.config.mjs` väljer port 8765 och stoppsignal i projektets `data`; `e2e_server.py` skapar temporär DEMO-DB, testägare och egna server-/workerprocesser. Fyra tester skriver till fasta sökvägar i `docs/screenshots`. Nästa E2E-körning ska därför göras i en särskild testkopia med egen data-/utdatayta och samma källa. `--output` ensamt flyttar inte explicita skärmbildssökvägar. Portinventeringen visade ingen lyssnare på 8765; ingen okänd process stoppades.

### Kontroll av historiska filer och slutläge

**A. Det historiska skyddsmanifestet kan inte behandlas som dagens exakta arbetskopiehash.** Av 102 kontrollerade poster utanför `data/` matchade 17 byte för byte. 81 matchade efter enbart CRLF→LF-normalisering. Fyra hade innehållsavvikelser redan före arbetet: `frontend/e2e/app.spec.ts`, `frontend/src/main.tsx`, `scripts/setup.ps1`, `scripts/start.ps1`. Git-status var ändå ren. Manifestet beskriver alltså en äldre innehållsbaslinje och plattformsberoende byte, inte ett bevis på nytillkommen manipulation. Sex historiska poster under `data/` öppnades inte. Se [protected-classification.json](evidence/protected-classification.json).

Det gamla manifestet och dess resultat skrevs inte över. För den här granskningen används en ny, daterad baslinje. **Slutkontrollen redovisas i delivery-manifest.json: endast de två rättade befintliga kodfilerna får ändras; alla övriga 135 baslinjefiler ska ha samma byte som vid start. Testkopians övriga baslinjefiler kontrollerades som oförändrade före leverans.** Den frysta `odds_lab.py`, `odds_history.py`, befintliga historiska rapporter, låsfiler och migrationer ska vara byteidentiska med dagens startbaslinje. Ingen ny sannolikhetsmodell eller regelversion infördes.

Skapade utdata var temporära syntetiska testdatabaser, en testbackup, JUnit/loggar, en separat testkopia och ett isolerat frontendbygge. Endast rapport, specifikation, hemlighetsfritt underlag och den avgränsade kodrättningen levereras till originalprojektet. Granskningen startade ingen API-/worker-/demoprocess; subprocessarna i testfallen är avslutade när sviten återvänder. Inga testservrar finns att lämna kvar.

## 5 Prioriterade fynd

### F01 Ändrad manuell kostnad kvitterades utan att sparas

**Prioritet P2, produktfel, bevisläge A. Rättat efter tilläggsgodkännande.** Ekonomivyn kan annars ge ägaren fel uppfattning om registrerat belopp och underlag efter ett osäkert nätverkssvar.

- **Kod i granskad HEAD:** `backend/jarvis/api.py:196–204`, särskilt 199–200. Relevant UI: `frontend/src/main.tsx:298–314`, där formuläret behåller samma `costAction` efter fel samtidigt som belopp och kommentar är redigerbara.
- **Utlösare:** första begäran med ID X sparar 100 öre och anteckning A. Svaret försvinner eller klienten återanvänder ID:t. En ny begäran använder X men 300 öre och anteckning B.
- **Förväntat:** samma ID och samma innehåll kan kvittera originalet; ändrat innehåll ska ge HTTP 409 utan skrivning.
- **Observerat före rättning:** båda svaren var HTTP 200 med `ok=true`; endast 100 öre/A låg i databasen. Inget belägg för dubbel extern debitering, men den nya kostnaden kvitterades missvisande.
- **Täckning:** befintligt E2E testar förlorat svar med oförändrat innehåll. Befintliga 203 backendfall fångade inte ändrat belopp/underlag. Nya tester prövar dessa, två samtidiga motstridiga begäranden, identisk replay efter omstart/stopp, fel posttyp och oläsbar metadata.
- **Minsta åtgärd, genomförd:** jämför posttyp, belopp och anteckning mot befintlig post i samma skrivtransaktion. Konflikttexten uppmanar att kontrollera den sparade kostnaden. Ingen historik skrivs om och ingen migration behövs.

### F02 Ändrat mål eller tak kunde kvitteras som gammal arbetsomgång

**Prioritet P2, produktfel, bevisläge A. Rättat efter tilläggsgodkännande.** Ägaren kunde tro att ett nytt mål eller tak hade skickats medan bara den gamla uppgiften fanns.

- **Kod i granskad HEAD:** `backend/jarvis/service.py:30–34`. Relevant UI: `frontend/src/main.tsx:266–276`, där samma `roundAction` behålls när ett försök misslyckas.
- **Utlösare:** en sparad arbetsomgång under ID Y med mål A och tak 100 öre följs av mål B/tak 200 under samma ID.
- **Observerat före rättning:** HTTP 200 och samma uppgifts-ID; originalets mål A/tak 100 behölls. Förväntat är HTTP 409 för den ändrade begäran.
- **Konsekvens:** missvisande kvittens och risk för att granska fel uppdrag. Ingen höjning av det verkligt sparade taket visades i reproduktionen.
- **Täckning:** befintligt `test_round_idempotency` provar bara identiskt innehåll. Nya fall prövar ändrat mål/tak, samtidighet, främmande uppgiftstyp och replay efter omstart/stopp.
- **Minsta åtgärd, genomförd:** jämför sparad VD-/planfas, titel och tak före retur av befintligt ID. Behåll återförsöket som läsning även efter paus eller stopp; inget nytt arbete köas.

### F03 Komponentmedian ger inte alltid en sannolikhetsfördelning

**Prioritet P2 för framtida modellåteranvändning, metodbegränsning, bevisläge A/B. Fryst kod bevarad.** `backend/jarvis/odds_lab.py:175–188` beräknar median separat per utfall; normaliserade källvektorer garanterar inte att deras komponentmedian summerar till ett.

En syntetisk kontroll med prisvektorer `(2,4,4)`, `(4,2,4)`, `(4,4,2)` ger normaliserade referenser vars komponentmedian är `(0,25;0,25;0,25)`, summa **0,75**. Alla tre källornas inversa odds summerar till ett. Vektorn får därför inte användas som en korrekt multiclass-prognos utan en ny, uttryckligt beslutad metod. Nuvarande kod använder ett utfalls median som prisreferens, och dokumentationen betecknar den som en referens, inte verifierad sannolikhet. Kontrollens konsekvens är främst att den gamla modellen inte ska återanvändas som framtida prognosmodell. Den bevisar inte orsaken till arkivets förlust och motiverar ingen efterhandsoptimering av historiken.

`docs/sportsbetting/2026-11-04-v2/statistik.md` beskriver problemet och föreslår en annan familjeseparerad kandidat. Dess tidigare verkliga räknetal är C i denna granskning. Minsta nästa åtgärd är att hålla den frysta modellen oförändrad och förbjuda återanvändning av `select_price_signal` i offlineverktyget. Ingen ny kandidat implementeras nu.

### F04 Historisk hashkontroll behöver en separat aktuell baslinje

**Prioritet P2 för reproducerbar utveckling, bevisläge A/B.** Se `docs/sportsbetting/2026-11-04-v2/kontroll.py:43–52` och avsnitt 4. Funktionen jämför exakta filbyte mot ett äldre manifest och skriver om `integritetskontroll.json`. I dagens Windowsutcheckning skulle en oförändrad startkopia därför inte uppfylla det gamla bytekravet.

Den här granskningen räknade själv om hashvärden utan att köra den skrivande historiska kontrollen. Minsta åtgärd är en ny daterad baslinje och en tydlig skillnad mellan byteidentitet i samma arbetskopia och historisk innehållsjämförelse efter radbrytningsnormalisering. Detta är gjort i granskningsunderlaget. Den äldre baslinjen får inte uppdateras för att få ett grönt historiskt resultat. Fyra innehållsskillnader är redovisade, inte bortförklarade som radbrytningar.

**B/D. Övriga områden:** inga ytterligare konkreta fel reproducerades i granskade åtkomst-, stopp-, reservations-, export- och pappersavräkningsflöden. Sviten och kodläsningen täcker viktiga invarianta regler, men är ingen garanti för alla race, nätavbrott, driftmiljöer eller datakällor. Okända källfamiljer, manuell datans sanningshalt och saknade projektkostnader kvarstår som begränsningar, inte nyupptäckta kodfel.

## 6 Högst tre nästa steg

1. **Granska och acceptera den avgränsade rättningen samt slutför UI-verifieringen när rätt browserresurs finns.** F01/F02 är verifierade och rättade; deras patch ska inte blandas ihop med ny bettingutveckling. Kör E2E i separat testkopia efter ett eget beslut om eventuell browserinstallation. Ingen UI-framgång hävdas innan den är körd.
2. **Godkänn separat offlineverktyget enligt byggspecifikationen.** Det tillför ett datakontrakt och en fullständighetsnämnare som saknas, utan att ansluta insamling eller ändra den frysta modellen. Formler kan återanvändas efter att de har flyttats till ren kod; de daterade studieprogrammen ska inte importeras som produktmoduler eftersom de är knutna till historiska sökvägar och skriver historiska rapportfiler.
3. **Ta först därefter ställning till ett separat datakälle- eller pilotuppdrag.** Kräv rättigheter, namngiven svensk variant, källfamiljer, aktuell kvot och låst urval/tidsfönster. Dagens dispatch stödjer inte odds. Varken datainsamling, ny signalmodell eller någon insats blir tillåten genom dessa dokument.

## 7 Separat byggspecifikation

[BYGGSPECIFIKATION.md](BYGGSPECIFIKATION.md) beskriver ett enda framtida bygge: lokalt ekonomi- och datakvalitetsverktyg. Det innehåller steg i ordning, datatyper, felklasser, beräkning, spårbarhet, lokala sökvägar, export, tester, godkännandekriterier och stoppunkt. Det bygger vidare på `feasibility-input-v1` i det befintliga v2-förslaget, med entydiga preciseringar för granskning. Specifikationen har inte implementerats.

## 8 Öppna beslut och osäkerheter

- **D.** Privat analysverktyg eller tjänst för andra. Det påverkar senare drift, datadelning och användarhantering, men blockerar inte offlinebygget.
- **D.** Val av operatör, dataleverantör, familjer och användningsrätt. Inga leverantörspriser eller villkor från 4 november har omverifierats; de är C, inte aktuella inköpsråd.
- **D.** Om faktisk prisåtkomst, liten prognosfördel eller lönsamhet finns. Dagens programkontroller mäter inget av detta. Historiskt −236,59 SEK är C från den sparade rapporten, inte ett nytt ekonomiskt test.
- **D.** Framtida strikt datakontrakts preciseringar och arbetsintervall ska granskas innan implementation. `frozen`/`decision_ref` i en fil är aldrig verktygets eget godkännande.
- **A/D.** E2E och visuell kontroll är blockerade av saknad Chromium. Publik drift, Linux, verklig modellåtkomst och fakturering är inte prövade här.

## 9 Åtgärder utanför leveransen och beslutsruta

Ingen ny oddsstrategi, insamling, modellträning, extern research, betald verifiering, migration mot ägarens data, normal appstart, publicering, kontoanslutning, browserinstallation, commit eller push ingår. Ingen arbetskopia har flyttats, ersatts eller slagits ihop. Den tillfälliga testkopian skapades enbart för isolerade kontroller enligt uppdragets avsnitt 6.4.

**Vad ägaren föreslås godkänna härnäst:** ett separat bygge av offlineverktyget enligt byggspecifikationen, efter granskning av rättningsdiffen och den kvarvarande UI-begränsningen.

**Filer och komponenter:** en ren `backend/jarvis/odds_feasibility.py`, en tunn `scripts/odds_feasibility.py`, riktade tester och svenska syntetiska format-/exempelfiler. Inga nya API-rutter, frontendflöden, DB-tabeller eller migrationer.

**Beteende:** explicit lokalt manifest och valfria lokala observationer → strikt validering → deterministisk ekonomi och fullständighetsredovisning → svensk fristående HTML och maskinläsbart resultat i en ny mapp.

**Tester:** formler och avrundning, okända kostnader, 54/60 platser, T60/T55, dubbletter, tidsgränser, en operation en gång, HTML-escaping, sökvägsskydd, avbruten export, determinism och vakter mot nät/DB/config; relevant regression samt visuell HTML-kontroll vid 390 och 1280 px.

**Utanför:** feed, dataköp, pilot, signaler, pappersspel, riktiga spel, insatshöjningar, nya modeller och ändring av frysta resultat.

**Stoppunkt:** stanna efter lokal offlineleverans och dokumenterad verifiering. Vid saknade resurser redovisas blockerade kontroller; inga nya installationer eller externa kopplingar görs automatiskt. Denna granskning stannar efter redovisad felrättning, rapport och byggspecifikation.

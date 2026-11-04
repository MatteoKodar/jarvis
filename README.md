# JARVIS · Fotbollsanalys och pappersspel

En lokal kontrollcentral med exakt tio fasta agentroller. React/TypeScript/Vite/Tailwind, Python/FastAPI, SQLite och en separat worker. Svenskt gränssnitt, SEK och Europe/Stockholm.

**Enda aktiva fokus från 2026-11-03:** undersöka om fotbollens 90-minutersodds kan ge en genomförbar fördel efter kostnader. Allmän affärsidéresearch och internetskanning är arkiverade. [Djup research och plan att granska](docs/sportsbetting/2026-11-03/plan.html). Riktiga insatser är avstängda; inget historiskt eller positivt pappersresultat låser upp dem automatiskt.

Fokusbytet omfattar rollinstruktioner, demonstrationsinnehåll och borttagna gamla aktiva researchvyer. Migration 006 tillämpas vid omstart: äldre öppna uppdrag/godkännanden avslutas som arkiverade, gammalt schema stängs av och arbetet pausas. Ett befintligt nödstopp kvarstår. Historiska rapporter, beslut och budgetbelopp bevaras; osäkra reservationer kräver fortfarande avstämning. Ingen oddsanslutning eller ny strategi har implementerats i fokusbytet.

**Börja i DEMO.** Inga API-nycklar behövs. Demoläget använder märkta reproducerbara exempel och gör inga externa AI- eller researchanrop. LIVE har en riktig OpenAI Agents SDK-adapter, men är avstängt tills du konfigurerar det. Ingen del av installationen köper tjänster eller publicerar något.

## Snabbstart på Windows

Öppna PowerShell i projektmappen. Installera Python 3.12+, Node.js 22.12+ och pnpm 11.25.0 om de saknas. Installationsskriptet kan även använda Codex medföljande Python och Node på denna dator.

```powershell
cd 'C:\Users\matte\OneDrive\Documents\ChatGPT\Jarvis2.0'
.\scripts\setup.ps1
.\scripts\start.ps1
```

Om PowerShell blockerar lokala skript kan du köra dem i en separat process:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

`setup.ps1` installerar låsta beroenden, bygger frontend, skapar `.env` om den saknas och frågar efter ett ägarlösenord på minst 12 tecken. **Inget standardlösenord finns.** Körning av setup igen frågar efter ett nytt lösenord och loggar ut befintliga sessioner.

Öppna **http://127.0.0.1:8000** och logga in. Startskriptet skriver loggar till `data/logs`. Låt PowerShell-fönstret vara öppet. Att stänga webbläsaren stoppar inte arbetet. Datorn måste vara vaken.

Om beroenden redan är installerade räcker `scripts/start.ps1`. Saknas ägarkonto kan du välja och upprepa ett lösenord direkt på den lokala första-start-sidan. Detta fungerar endast från loopback med lokal HTTP-origin och kan aldrig skriva över ett befintligt konto. För serverinstallation via HTTPS skapas kontot med CLI-kommandot ovan.

1. Klicka **Återuppta**; första starten är pausad.
2. Välj **Starta arbetsomgång**, skriv ett mål och ange kostnadstak.
3. Workern kör VD-uppgiften och sparar ett förslag.
4. Granska innehåll, mål, risker och det sammanlagda taket för arbete + granskning.
5. **Godkänn**, **Avslå** eller **Begär ändring**. Ändringsbegäran kan följas av en reviderad version som kräver nytt beslut.
6. Godkänt internt analysarbete köas, utförs av en specialist och granskas separat av Kritikern. Rapporter finns under Filer; simulerad fotbollsuppföljning finns i Oddslabb.

Demokritikern blockerar medvetet fortsatt experiment: exemplen saknar verkliga belägg. Det är ett fungerande granskningsbeslut, inte ett programfel.

## Manuell installation och separata processer

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env   # Endast om .env inte redan finns!
cd frontend
pnpm install --frozen-lockfile
pnpm run build
cd ..
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m jarvis.cli owner
```

Backend, PowerShell-fönster 1:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m uvicorn jarvis.api:app --host 127.0.0.1 --port 8000
```

Worker, PowerShell-fönster 2:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m jarvis.worker
```

Frontend ingår i backendens produktionsserver efter byggsteget. För frontendutveckling: sätt `JARVIS_ORIGIN=http://127.0.0.1:5173` i `.env`, starta om backend och kör `pnpm dev` i `frontend` i ett tredje fönster. Vite proxar `/api` till backend. Använd exakt den konfigurerade adressen, inte `localhost` om origin är `127.0.0.1`. Återställ origin till port 8000 när du använder produktionsbygget.

## Funktioner som faktiskt finns

- Tio stabila roller med versionshanterade instruktioner, definierat JSON-resultatformat och backendstyrda verktygsbehörigheter.
- Beständig kö, två samtidiga uppgifter globalt, transaktionella anspråk, unika åtgärds-ID:n och separata körningsposter.
- Kedjan VD → sparat förslag → ägarbeslut → specialist → kritiker → rapport. Inga obegränsade uppdragskedjor.
- Godkännande binds till exakt åtgärd, mål, innehåll, agent, version och båda kostnadstaken via SHA-256. Upprepade beslut köar inte igen. Ändrade versioner kräver nytt beslut.
- Beständig paus och nödstopp, arbetshistorik, worker-puls, autentiserad SSE med händelse-ID och automatisk återanslutning.
- Separata DEMO/LIVE-databaser. Demodata skapas först när en demouppgift utförs.
- Intern fotbollsgranskning med avgränsade uppdrag. Inga affärsidékandidater skapas i det aktiva flödet. Historiska källor och resultat bevaras; demotext framställs aldrig som hämtade odds eller verklig vinst.
- Högst ett aktivt utvecklingsprojekt. Godkända uppgifter för Programmeraren/Designern öppnar projekt; projekt avslutas manuellt efter färdiga uppgifter.
- Atomär budgetreservation i heltalsören, total- och dagstak, låst reserv, tokenbaserade uppskattningar med prisversion/valutakurs, manuella kostnader och ägaravstämning av okända reservationer.
- Begränsade scheman: högst en VD-omgång per dag, 1–7 omgångar, högst sju dagars giltighet. Ägaren förhandsgodkänner målet och taket. Specialistarbete kräver fortfarande separat beslut.
- Ägarinloggning med scrypt, tidsbegränsad HttpOnly-session, SameSite, CSRF-token och Origin-kontroll. Fem felaktiga inloggningsförsök per fem minuter; gränsen sparas i databasen.
- Autentiserad filnedladdning från databas-ID. Inga användarstyrda filsökvägar. Agenttext renderas som text och laddas ned som `.txt`.

## Arkiv: Researchlabb A0 och tidigare protokoll

Det tidigare Researchlabbet är borttaget från den aktiva navigationen och nya A0-körningar nekas av API:t. Sparade arkiv kan fortfarande läsas och exporteras med ägarautentisering. Rena arkivhjälpare och deras tester bevaras för tidigare resultat, inte som ett nytt produktfokus.

Tidigare A0/A1/B-dokument beskriver den äldre inriktningen och är historik. Dokumentläsaren finns kvar med arkivmärkta versioner. Se [tidigare Researchlabb A0](docs/RESEARCHLABB-A0.md) för dess ursprungliga funktioner och begränsningar.

## Oddslabb – fotboll med låtsaspengar

Öppna **Oddslabb** i DEMO för regelbaserad jämförelse av 1X2 efter ordinarie matchtid. Syntetiska exempel hålls åtskilda från en tom, framåtriktad observationsserie. Import, avståenden, simulerade insatser, vinster, förluster och angivna datakostnader sparas med kontrollsummor. **Ingen oddsleverantör är ansluten och inga riktiga spel kan placeras.** Ett positivt exempel är inget vinstbevis. Se [Oddslabb fotboll](docs/ODDSLABB-FOTBOLL.md).

Ett separat historiskt test med verkliga, kostnadsfria arkivdata genomfördes 2026-11-03: 760 Premier League-matcher, 76 låtsasspel à 10 SEK och **−236,59 SEK** i samlat simulerat resultat. Inga riktiga insatser gjordes och ingen regel ändrades efter utfallet. [Rapport och begränsningar](docs/odds-reports/2026-11-03-epl-paper-v1/rapport.html).

## LIVE – konfigurera utan att testa med pengar

Redigera `.env` på serversidan. Lägg aldrig API-nyckeln i frontend eller Git.

```dotenv
JARVIS_MODE=LIVE
OPENAI_API_KEY=din_egen_nyckel
JARVIS_PAID_ENABLED=true
JARVIS_RESEARCH_ENABLED=true
JARVIS_MODEL=modellnamn_från_ditt_API_konto
JARVIS_PRICED_MODEL=samma_modellnamn
JARVIS_INPUT_USD=aktuellt_inpris_per_miljon_token
JARVIS_OUTPUT_USD=aktuellt_utpris_per_miljon_token
JARVIS_USD_SEK=din_dokumenterade_valutakurs
JARVIS_PRICE_VERSION=datum_och_priskälla
```

Ovanstående beskrivande prisvärden måste ersättas med **positiva decimaltal** med punkt. Inget modellnamn eller pris är förvalt. Kontrollera aktuell modellåtkomst och prissättning hos leverantören. Samma verifierade prisprofil används i v1; en agentmodell som inte matchar `JARVIS_PRICED_MODEL` blockeras. `JARVIS_AGENT_MODELS` kan ange modell per agent-ID, men samtliga måste omfattas av prisprofilen.

Starta om backend och worker. Skapa ett separat LIVE-ägarkonto med `python -m jarvis.cli owner`. Budgeten i LIVE börjar separat på 1 000 SEK med 500 SEK låst reserv, 10 SEK/dag och 5 SEK/uppgift. Dessa värden är planeringsgränser, inte pengar på ett konto och inte utlovade driftkostnader.

Varje modellkörning använder `Agent`, `OpenAIResponsesModel` och `Runner.run` från Agents SDK, ett enda modellsteg, högst 2 400 output-token och inga automatiska nätverksomförsök. Innan anrop reserveras en konservativ maximal kostnad för 65 536 input-token och 2 400 output-token. Underlagets UTF-8-storlek, instruktioner och outputschema kontrolleras med marginal före anropet. Om taket inte räcker körs inget modell-anrop. Faktisk rapporterad tokenanvändning bokförs som **uppskattning**, inte verifierad faktura. Tracing är avstängt.

Research är en uttryckligt begränsad [MediaWiki Action API-sökning](https://www.mediawiki.org/wiki/API:Search): en begäran, högst tre svenska Wikipedia-utdrag, fast värd, timeout och svarsstorleksgräns. Backend kontrollerar rollen. Ingen modell får välja godtycklig URL, följa länkkedjor eller köra terminalkommandon. Researcher, Marknadsanalytiker och Marknadsförare kan få detta underlag. Wikipedia är **bakgrundsinformation**, inte bevis på betalningsvilja eller en fullständig konkurrensanalys.

SDK-integrationen följer [OpenAI Agents SDK quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart), [agentdefinitioner](https://developers.openai.com/api/docs/guides/agents/define-agents) och [körning av agenter](https://developers.openai.com/api/docs/guides/agents/running-agents). Exakta installerade versioner finns i `requirements.lock`; frontendversioner i `frontend/package.json` och `pnpm-lock.yaml`.

**Inga betalda LIVE-anrop ingår i testerna eller har gjorts som del av leveransen.** Du behöver själv konfigurera konto och betalningsvillkor.

## Stopp, fel och återstart

- **Paus** stoppar nya uppgifter; redan påbörjade uppgifter får avslutas.
- **Nödstopp** sparas omedelbart och stoppar nya anrop vid backendens anropskontroll. Workern kontrollerar stopp ungefär varje sekund och försöker avbryta aktiva körningar. Ett redan skickat leverantörsanrop kan ändå slutföras och debiteras.
- Stopp ligger kvar efter omstart tills ägaren väljer **Återuppta**.
- En processkrasch ger efter 120 sekunders lease en blockerad uppgift. Osäkra anrop återförsöks aldrig automatiskt. Eventuell reservation behålls som **okänd debitering**.
- Kontrollera leverantörens användningsrapport, öppna Ekonomi och stäm av reservationen med belopp och underlag. Avstämningen märks som gjord av ägaren. Systemet läser inte leverantörsfakturor automatiskt.
- Rätta konfiguration/underlag och starta ett nytt uppdrag när du har granskat en blockerad uppgift. V1 gör inga automatiska förbättringsomgångar (alltså färre än gränsen två).
- Starta inte flera kopior av `start.ps1`. Flera workerprocesser delar visserligen den globala tvåuppgiftsgränsen, men en API-port kan bara bindas en gång.

## Säkerhetskopiering och återställning

SQLite-backupkommandot tar en konsistent kopia även när WAL används. Kör med rätt läge i `.env`:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m jarvis.cli backup --output .\jarvis-demo-backup.sqlite3
```

Kopian innehåller uppgifter, rapportfiler, källor, budget, ägarlösenordshash och sessioner. Förvara den privat. `.env` ingår inte; säkerhetskopiera den separat på ett skyddat ställe. Git innehåller inga driftdata.

Återställ med **backend och worker helt stoppade**:

1. Flytta den nuvarande databasfilen samt eventuella `-wal`/`-shm`-filer till en separat arkivmapp. Behåll dem tills återställningen verifierats.
2. Kopiera säkerhetskopian till `data/demo.sqlite3` eller `data/live.sqlite3`, enligt aktuellt läge. Blanda aldrig lägen.
3. Kör `python -m jarvis.cli owner` med rätt Pythonmiljö för att välja lösenord och ogiltigförklara återställda sessioner.
4. Starta backend och worker, kontrollera budget/reservationer och välj själv när arbetet ska återupptas. Om säkerhetskopian hade aktivt arbete: pausa före normal drift och stäm av osäkra anrop.

Databasmigrationer finns i `backend/migrations`, versionsnummer i `schema_migrations`. De körs automatiskt vid start. Säkerhetskopiera före uppgraderingar.

**OneDrive:** använd helst `JARVIS_DATA_DIR` utanför en synkroniserad mapp vid verklig drift. Kopiera konsistenta säkerhetskopior till synkronisering; synkronisera inte en aktiv SQLite-databas mellan flera datorer.

## Tester

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
pnpm run build
pnpm exec playwright install chromium
pnpm test:e2e
```

Playwright startar sin egen backend och separat worker på port 8765 med en tillfällig DEMO-databas och ett testlösenord som enbart hör till testmiljön. Inga ägardata eller API-nycklar används. Skärmbilder skrivs till `docs/screenshots`.

Se `docs/VERIFIERING.md` för faktiskt körda tester och kvarvarande verifieringsgränser.

## Senare Linuxdrift

Använd en lokal disk för SQLite. Installera Python 3.12+, Node 22.12+ och pnpm, skapa `.venv`, kör låsfilerna och bygg frontend. `pywin32` i Pythonlåset är villkorat till Windows.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
cd frontend && pnpm install --frozen-lockfile && pnpm run build
cd ..
PYTHONPATH=backend .venv/bin/python -m jarvis.cli owner
PYTHONPATH=backend .venv/bin/uvicorn jarvis.api:app --host 127.0.0.1 --port 8000
# Separat process / separat systemd-tjänst:
PYTHONPATH=backend .venv/bin/python -m jarvis.worker
```

Kör API och worker som två systemd-tjänster med samma privat data-katalog, `WorkingDirectory`, miljöfil och oprivilegierad användare. Sätt `Restart=on-failure`. För publik drift behövs HTTPS-reverse-proxy, `JARVIS_ORIGIN=https://din-domän` och `JARVIS_SECURE_COOKIE=true`. Behåll backend på loopback; blockera port 8000 externt. Applikationen nekar icke-lokal origin utan HTTPS/Secure-konfiguration. Linuxdrift och publik installation är dokumenterade men inte testade här.

## Avgränsningar i version 1

- Detta är en kontrollcentral med ett begränsat internt arbetsflöde, inte ett självgående företag.
- Statuschatten läser databasen och använder fasta svenska svarsregler. Fri konversation med modellen sker inte direkt i chatten; skriv uppdrag i arbetsomgångsformuläret. Då kör VD-adaptern i LIVE och ett granskningsbart förslag skapas.
- Modeller saknar egna muterande verktyg och handoffs. Backend styr all delegering och tillåter en specialist följd av en kritiker. Agenter kan inte skapa nya kedjor.
- Researchverktyget täcker endast svenska Wikipedia-utdrag. Inga sökmotor-, kund-, annons-, betalnings- eller publiceringsintegrationer är anslutna. Ett godkännande anges som köat, aldrig som utfört externt.
- Idéer sparas som jämförda kandidater; full experimentlivscykel med genomförda marknadstester är inte ansluten. FAKTA-etiketter visar modellens källstödda påståenden, inte oberoende mänsklig faktaverifiering. TESTRESULTAT från LIVE nedgraderas till antaganden eftersom ingen experimentadapter finns.
- Kod/design sparas som textunderlag i rapporter, exekveras inte och blir inte automatiskt ett byggt separat projekt.
- Ingen automatisk fakturaavstämning, betalning, intäktsverifiering eller valutakursinhämtning. Intäkter höjer aldrig budget.
- Ingen automatisk återkörning av avbrutna anrop. Sparad kö återupptas; osäkert pågående arbete kräver ägargranskning.
- En ägare, inga organisationskonton eller fleranvändarbehörigheter. Ingen pen-testcertifiering.
- Historikvyn söker bland de senaste 300 händelserna. Alla händelser finns kvar i databasen. Övriga listor är avsedda för små lokala arbetsmängder och saknar paginering.

## Projektkarta

```text
backend/jarvis/  API, auth, roller, budget, orkestrering, worker, adaptrar
backend/migrations/  Versionshanterat SQLite-schema
frontend/src/   React/TypeScript och responsiv Tailwind/CSS-design
tests/          Backend- och adaptertester utan betalda anrop
frontend/e2e/   Automatiserade webbläsartester
scripts/        Installation, start och isolerad testserver
docs/           Verifieringsrapport och skärmbilder
```

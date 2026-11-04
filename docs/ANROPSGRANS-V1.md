# Beständig anropsgräns för JARVIS

Implementerad 2026-10-19, version `dispatch-v1`, migration 004. Kontrollen omfattar dagens Responses-anrop och den fasta svenska Wikipedia-sökningen. Den aktiverar inte LIVE, A1 eller B. Researchlabb A0 och dess versionsbundna försöksmaterial ändras inte.

## Anropsväg och ansvar

Workern reserverar en uppgift och skapar en körning med aktuellt stoppnummer. `live.run()` lämnar endast uppgifts-ID och körnings-ID till `dispatch.prepare()`. Modulen läser roll, arbetsfas, status, lease, uppgiftsunderlag, budget och körning från databasen. Inkommande ordböckers roll, kostnadstak och status används inte som befogenheter. Uppgiften och exakt en aktuell körning måste vara pågående; gamla, avslutade och återhämtade körningar nekas.

Förberedelsen kräver LIVE, båda uttryckliga aktiveringsflaggorna, en giltig prisprofil med matchande modell och granskade installerade klientversioner. Endast `model.responses` och `research.wikipedia` stöds. Planering kräver VD och granskning Kritiker. Wikipedia kräver arbetsfasen `work` och rollens uttryckliga `wikipedia_search`-behörighet. Ingen modell får verktyg, handoffs eller administrationsfunktioner.

Modellens kända underlag kontrolleras före reservation. Maxkostnaden reserveras atomärt med befintliga budgetfunktioner **före** Wikipedia. Därmed ger känd modellbudgetbrist noll research- och modellsändningar. Total-, dag- och uppgiftstak samt låst reserv räknas fortsatt i heltalsören. Äldre okända reservationer belastar också dagens utrymme.

Efter research byggs modellens slutliga underlag och storleken kontrolleras igen. För granskningar ingår redan sparade föräldrakällor i den tidiga kontrollen och den frysta konfigurationen. Källor, uppgiftskontext och sökfråga kapas inte tyst. För stora uppgifter eller svar avvisas. Wikipedia tillåter högst tre poster, 100 000 svarsbyte, 300 tecken per titel och 1 500 per rensat utdrag. Modellramen är 65 536 konservativt uppskattade inmatningstoken, med bytebaserad förkontroll inklusive instruktioner, schema och 16 384 bytes marginal, samt högst 2 400 utmatningstoken. Modellsvarets storlek begränsas till 1 000 000 avkodade byte.

HTTP-klienterna använder en beständig transportspärr i `external_http.py`. Före delegationen till den innersta transporten kontrolleras exakt tillåten värd, sökväg, metod och bundet underlag. Modell, instruktioner, utmatningstak, `store=false`, inga verktyg, ingen konversation och frånvaro av strömning kontrolleras också. SDK:t utelämnar `stream` vid vanliga Responses-anrop; det är dess granskade väg för `stream=False`. Inga godtyckliga URL:er eller fria verktyg stöds.

Direktanrop till `research.search()` gör samma förberedelse och modellreservation. När ett fristående researchanrop avslutas avbryts den oanvända modelloperationen och reservationen släpps. Researchresultatet behåller sitt eget tillstånd. Fristående sökning är alltså inte ett återupptagbart förstadium till en senare separat `live.run()` på samma körning. Det ordinarie sammanhängande flödet äger en gemensam reservation hela vägen.

## Identitet och lagring

Operations-ID är SHA-256 över uppgifts-ID, körnings-ID och en fast arbetsflödesplats: `model.responses:1` respektive `research.wikipedia:1`. Ett nytt request-ID eller en annan worker skapar inte en ny plats. Versionen ingår i den frysta kontrollsumman, inte som ett sätt att kringgå samma identitet.

Tabellen `operations` sparar uppgift, körning, typ, plats, gränsversion, stoppnummer, grundunderlagets hash, fryst uppgifts- och rollversion/instruktion, prisprofil, modell, resursram, klientversioner, reservations-ID, slutunderlagets hash, transportunderlagets hash, tider, tillstånd och osäkerhetsorsak. Resultat sparas vid avslut. Credentials och HTTP-auktoriseringshuvuden sparas inte. Resultat och källtext är fortsatt obetrodda data.

Samma identitet med ändrat grundunderlag eller konfiguration avvisas. Slutunderlag får bindas en gång; en ändrad bindning avvisas. Alla upprepade adapterförsök på en redan befintlig operation avvisas, även efter ett lyckat avslut. Sparade leverantörsresultat används inte för automatisk återkörning. En förberedelse som övergivits kan därför också kräva en ny uttrycklig arbetsuppgift efter granskning.

Migration 004 lägger till `dispatch_control`, `operations` och `runs.dispatch_epoch`. Tidigare migrationer, beslut, kostnader och reservationer behålls. Befintliga äldre körningar får `NULL` som stoppnummer och får inte fortsätta med externa anrop. Ägarens driftdata har inte migrerats av verifieringen; migreringen provades i tillfälliga databaser och körs vid vanlig initialisering efter en framtida omstart.

## Tillstånd och reservationer

| Tillstånd | Betydelse | Modellreservation |
| --- | --- | --- |
| `prepared` | Kontrollerad och reserverad; ingen möjlig sändning registrerad | `held` |
| `possible_send` | Sändauktorisering har committats före transportdelegation | `held`, fortfarande helt låst; osäkert utfall tills kvitto sparas |
| `completed` | Fullständigt lokalt behandlat svar och resultat sparat | `settled` för modell; kostnadsuppskattning bokförd en gång |
| `unknown` | Avbrott efter möjlig sändning; inga nya försök | `unknown`, kvar i budgeten tills ägaravstämning |
| `cancelled` | Bevisat avbruten före möjlig sändning; inga nya försök | `released` |

Normal väg är `prepared → possible_send → completed`. Före markeringen får ett avbrott ge `cancelled`; efter markeringen ger avbrott `unknown`. Det finns ingen övergång tillbaka till `prepared`. Wikipedia har egen tillståndspost och ingen betald reservation; dess uttryckliga kostnadsmodell är `FREE` för just den fasta integrationen.

Sparat, fullständigt researchresultat och källposter committas tillsammans. Det förblir `completed` när modellen senare avbryts före sändning, exempelvis vid slutlig storlekskontroll. En modellkostnad bokförs endast en gång och baseras på den frysta prisprofilen och ett giltigt användningskvitto. Ett svar med schemafel, saknad användning, ofullständig status eller oklart utfall antas inte ha kostat noll. Ett semantiskt fel som upptäcks efter giltigt kvitto kan ha en redan bokförd kostnad.

Vid processkrasch kan `possible_send` och en låst `held`-reservation ligga kvar tills workern återhämtar den utgångna leasen. Då blir operation och reservation `unknown`; ingen omkörning sker under väntetiden. Om markeringen aldrig committades får återhämtningen däremot släppa reservationen. Befintlig lease är 120 sekunder, utan ny automatisk omkörning. `worker.fail()` gör samma klassificering.

Ägarens befintliga autentiserade avstämning gäller bara reservation och kostnadsbokföring. Även avstämning till noll återaktiverar aldrig operations-ID:t. Ett nytt uttryckligt arbete behöver föregås av bedömning av det tidigare osäkra utfallet.

## Nödstopp och samtidighet

Förberedelse, sändauktorisering och nödstopp serialiseras genom SQLite `BEGIN IMMEDIATE`. Nödstopp ökar ett beständigt stoppnummer och avslutar väntande operationer enligt om de passerat markeringen. Körningen måste ha samma stoppnummer som systemet. Återuppta ändrar inte gamla körningars nummer och kan inte återställa ett gammalt tillstånd.

Nödstopp som committats **före** sändauktoriseringen hindrar både auktorisering och transport. Auktoriseringen gör den sista giltighetskontrollen i transportens metod, omedelbart före delegationen. Ingen SQLite-skrivtransaktion hålls öppen över nätverksväntan. Två workers kan därför inte auktorisera samma ID två gånger.

Ett försök som redan auktoriserats kan hinna skickas efter att nödstopp committats. Lokal databas och extern leverantör deltar inte i någon gemensam atomär transaktion. Dessa operationer markeras konservativt okända vid stopp; sena svar återaktiverar dem inte. Även krasch mellan commit och transport kan ge okänt tillstånd trots **noll** HTTP-försök.

Paus behåller sitt tidigare beteende: ingen ny uppgift får claimas, medan redan påbörjat arbete får fortsätta. Nödstopp är starkare. Workerns resultatlagring kontrollerar också körningens stoppnummer så att ett sent resultat inte skapar nya arbetssteg efter stopp och återuppta.

## Granskade återförsökslager

Installerade versioner kontrolleras i körningen. Avvikande version blockerar externa anrop tills den granskats; inga paket installerades eller uppgraderades i detta uppdrag.

| Lager | Installerad version | Granskad väg och inställning |
| --- | --- | --- |
| Agents SDK | `openai-agents 0.24.0` | `run_internal/model_retry.py`, `models/openai_responses.py`: `ModelRetrySettings(max_retries=0)`, även kompatibilitetsvägen för `conversation_locked` avstängd; en turn, inga tools/handoffs, tracing avstängd |
| OpenAI SDK | `openai 3.35.1` | `_base_client.py` request-loop: `max_retries=0`; `_client.py`: vanlig API-nyckel som sträng, ingen workload identity eller provider/auth-refresh-väg; fast Responses-bas-URL |
| Modellens HTTP-klient | `httpx2 2.13.1` | Explicit egen `AsyncClient`, `follow_redirects=False`, `trust_env=False`, `auth=None`; ersätter SDK-default som annars följer omdirigeringar |
| Modelltransport | `httpcore2 2.13.1` | `AsyncHTTPTransport(retries=0, http2=False)`, ny transport per operation, en anslutning, ingen keepalive-pool |
| Researchklient | `httpx 0.28.1` | Fast Wikipedia-GET, `follow_redirects=False`, `trust_env=False`, `auth=None` |
| Researchtransport | `httpcore 1.0.9` | `AsyncHTTPTransport(retries=0, http2=False)`, en anslutning och ingen keepalive-pool |

Transporternas `_async/connection.py` återförsöker anslutning endast om dess retry-räknare är positiv. HTTP/1-vägen i `_async/http11.py` skriver headers/body en gång; poolens `ConnectionNotAvailable` gäller tilldelning före headerskrivning. Färsk transport utan delad anslutning eller HTTP/2 undviker vägar för återanvändning och HTTP/2-omsändning. Den beständiga spärren blockerar dessutom en eventuell ny klientdelegation med samma ID, oberoende av SDK-räknare. TLS och vanliga TCP-paketomsändningar räknas inte som nya applikationsanrop.

## Lokal verifiering

`tests/test_live_adapter.py` använder verklig `Runner.run()`, Responses-modell, OpenAI SDK och HTTP-klient. Endast den innersta transporten ersätts vid simulering av HTTP-svar. Ett separat test behåller även verklig HTTP-transport och httpcore2, men ersätter dess anslutningsbackend med lokala anslutningsfel och timeout. Ett annat kontrollerar faktiska transportinställningar. Externa anslutningar och DNS blockeras i de nya testerna; Windows loopback tillåts för testmiljön.

Samtidighet använder events och barriers, inte godtyckliga väntetider. Processbytestestet startar en separat Pythonprocess mot samma tillfälliga databas. Migrationstestet jämför ägarbeslut, förslag, kostnader och okänd reservation före och efter migrationen.

Faktiskt körd slutverifiering 2026-10-19:

- Hela backendsviten: **132 godkända**, 76,40 sekunder. Där ingår 74 anropsgränsfall och de 22 befintliga A0-fallen. A0 behåller nio rapporter, femton simulerade steg och noll externa anrop.
- Riktade anropsgränstester: 71 godkända före slutgranskningen; därefter tre separat godkända regressionsfall för komprimerat svar, payloadbindning och sent workerresultat. Samtliga ingår även i slutkörningen ovan.
- TypeScript och Vite-produktionsbygge: **godkänt** med befintliga beroenden. Byggets första försök hindrades av sandlådans katalogbehörigheter; samma bygge godkändes utanför sandlådan.
- Playwright/Chromium: **7 godkända**, 29,1 sekunder, mot separat testserver och tillfällig DEMO-databas.

Backend kördes från projektroten med `.venv/Scripts/python.exe -m pytest -q --tb=short`. Frontendkommandona var `pnpm run build` och `pnpm run test:e2e` i `frontend`, med befintlig lokal Node-/pnpm-runtime och befintlig Chromium. `PYTHON_DOTENV_DISABLED=1` användes för Pythonverifiering och testserver; befintlig `.env` lästes inte in i verifieringen. Driftens LIVE aktiverades inte, `.env` ändrades inte och inga riktiga modell- eller researchanrop gjordes. Inga beroenden installerades eller uppgraderades.

I tabellen räknas toppnivåanrop till adapter separat från försök att delegera en HTTP-förfrågan till leverantörstransporten. Researchkolumnen visar det extra, obetalda försöket i sammanhängande flöde.

| Lokalt fall | Adapteranrop | Modell-HTTP | Research-HTTP | Slutlig modellreservation |
| --- | ---: | ---: | ---: | --- |
| Lyckat modellsvar + upprepning | 2 | 1 | 0 | `settled`, en kostnad |
| 429, 503, 401, conversation_locked eller omdirigering, vardera + upprepning | 2 | 1 | 0 | `unknown` |
| Anslutningsfel, timeout eller avbrutet svar, vardera + upprepning | 2 | 1 | 0 | `unknown` |
| Schemafel, saknad användning eller ofullständigt svar, vardera + upprepning | 2 | 1 | 0 | `unknown` |
| Två samtidiga modelladaptrar | 2 | 1 | 0 | `settled`, en reservation och en kostnad |
| Modellbudget saknas före research | 1 | 0 | 0 | Ingen reservation |
| Nödstopp före transportauktorisering | 1 | 0 | 0 | `released` |
| Nödstopp efter auktorisering men före delegation | 1 | 1 | 0 | `unknown` |
| Krasch simulerad efter markering, före transport; sedan adapterförsök efter återhämtning | 1 samt direkt markering | 0 | 0 | `unknown`, sedan ägaravstämd; operation fortsatt `unknown` |
| Processbyte efter tidigare markering | 1 i annan process samt direkt markering | 0 | 0 | `unknown` efter återhämtning/avbrott |
| Wikipedia-fel + upprepning av flödet | 2 | 0 | 1 | `released`; research `unknown` |
| Slutligt för stort underlag efter lyckad research | 1 | 0 | 1 | `released`; research `completed` |

## Begränsningar och nästa steg före A1

Garantin gäller **högst ett applikationsförsök till HTTP-sändning per beständigt operations-ID i JARVIS kontrollerade klientkedja**. Den fastställer inte om leverantören tog emot, utförde eller debiterade ett osäkert anrop. En kvitterad tokenkostnad är fortfarande en uppskattning enligt konfigurerad prisversion, inte en verifierad faktura. De lokala svaren verifierar inte verklig debitering, modellkvalitet eller källtillgång.

Det finns ingen automatisk återstart av övergivna operationer och ingen ny generell verktygsplattform. En process som dör före markeringen kan låsa ett logiskt steg tills leasen återhämtats. Wikipedia är endast bakgrundsmaterial, inte verifierad kommersiell evidens. Bytegräns och marginal är en konservativ förkontroll; oväntad faktisk användning utanför ramen leder till manuell avstämning. SDK- eller modelländringar kräver ny granskning och offlineverifiering.

Nästa avgränsade uppgift är att färdigställa och frysa ett separat **fortsatt lokalt** A1-körningsmanifest: källpaket, konkreta modell-/prisversioner, resursramar, bedömningsmetod och godkännandepunkter. Det ska kopplas till den här gränsens operationsplatser och stoppregler innan något uttryckligt beslut om externa försök. Det befintliga versionsbundna protokollet förblir oförändrat och inte körklart.

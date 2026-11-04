# Spårbarhet och projektkontroll A1 v0.2.0

**UTKAST – INTE KÖRKLART.** Leveransdatum 2026-10-20, Europe/Stockholm. Detta är dokumentleveransens revisionsunderlag, inte ett metod-/körningsgodkännande.

## Uppdragets genomförande och versioner

Arbetsordning: registrera status och filhashar; läs AGENTS, tidigare protokoll, A0 och anropsgräns samt relevanta koddelar som text; skriv sju nya dokument; kontrollera dokument och jämför status/filhashar. Inga programmoduler importerades för att läsa konfiguration eller databas.

Den enda tidigare protokollmappen var 2026-10-18-v0.1.0-a5c383c6 med 00, 01 och 02. Bilagor 03–06 saknades trots länkar i 00. De har inte fyllts på retroaktivt. Den ändrade försöksfrågan och designen får en ny metodversion **2026-10-20-v0.2.0**, inte en påhittad redan existerande version.

Git har ingen commit och ingen giltig HEAD: status anger **No commits yet on master**. Suffixet a5c383c6 i den gamla mappen har inte verifierats som en Git-revision och används inte som källkodslås. Alla 116 statusposter före leveransen var redan untracked. Därför kompletteras Gitstatus med en uttrycklig innehållskontroll av 57 tillåtna filer.

Före-snapshot togs **2026-10-19T22:14:57.1085461Z** UTC, vilket är 2026-10-20 i Europe/Stockholm, före första filskrivningen. Efterkontrollen registreras nedan när alla sju filer finns. Läsning av kod är inte detsamma som att dagens anropskedja har testats i detta uppdrag.

## Kravspårning

| Krav i uppdraget | Levererad specifikation | Status |
| --- | --- | --- |
| Dokumentation utan driftändring | Detta dokument, före/efterkontroll | Endast sju nya Markdown-filer avses |
| Samma utkast i S1/S2/RK, nio anrop | 00, 03, 05 | Tre råutkastlås, sex granskningar; inga separata basutkast |
| Granskarens ett tillägg och höjning/sänkning | 03 | N01, passagecitat, deterministiska beroenden och fallback |
| M1/M2 och alla förändringstyper | 02–03 | Parade ämnesrader och separat ingreppsaudit |
| Ny regel och bevarad gammal regel | 00 versionshistorik, 02 sju syntetiska fall | Förslag; kräver beslut före metodfrysning |
| Full mänsklig granskning och realistisk tid | 02 | Alla slutpåståenden, borttagningar, motiveringar, motbelägg, tillägg och avgörande utelämningar |
| Faktisk kostnad och separatdrift | 02, 05 | Delat utkast räknas en gång faktiskt; separatdrift inkluderar det per gren |
| Källurval och privat förhandsreferens | 01, 05 | Förhandsregler och privata gränser; inga verkliga källor/facit |
| Fulla format och instruktioner | 03, 05 | Normativa fält, enums, syntetiska exempel och exakt tillåtna inputskillnader |
| Små framtida koduppdrag | 04 | I01–I05; inget implementerat nu |
| Metod-/körningsfrysning och stopp | 00, 05 | Plan, efterföljande utkastbindning och bedömningslås hålls isär |

## Viktiga skillnader mot tidigare plan

Gemensamt utkast isolerar ett tillskott som den gamla designens olika första svar blandade ihop. Nio anropsplatser ersätter 15 plus möjlig diagnostik. Högst sju original lämnar plats för ett spårbart tillägg. Tillåtna uppgraderingar gör felaktiga avståenden mätbara. Full rapport- och ingreppsgranskning ersätter det gamla stickprovet. Den tidigare 18-timmarsramen ersätts som förslag av **3 798 minuter, 63 timmar 18 minuter**, plus upp till 405 minuter per fullständigt ersättningsämne.

Beslutsregeln har prövats för hand på de sju efterfrågade syntetiska fallen i 02: ofelfritt men bättre RK kan motivera mer prövning; lika nollfel ger otillräckligt underlag; ny allvarlig skada ger avstå för den föreslagna oförändrade fortsättningen; bättre kvalitet kan ändå vara för dyr; olika ämnesvinster ger ingen enkel vinnare; rättat felaktigt avstående är en förbättring; saknat/osäkert svar gör helheten ofullständig.

Inget exempel är ett nytt verkligt mätresultat, en prisuppgift eller ett ägarbeslut.

## Dokument jag skapade

Exakt dessa sju filer under denna nya mapp:

1. [00 Protokoll](00-PROTOKOLL.md)
2. [01 Ämnen och källurval](01-AMNEN-OCH-KALLURVAL.md)
3. [02 Jämförelse och bedömning](02-JAMFORELSE-OCH-BEDOMNING.md)
4. [03 Påståenden och slutleverans](03-PASTAENDEN-OCH-SLUTLEVERANS.md)
5. [04 Implementationsuppdrag](04-IMPLEMENTATIONSUPPDRAG.md)
6. [05 Frysning och integritet](05-FRYSNING-OCH-INTEGRITET.md)
7. [06 Spårbarhet och projektkontroll](06-SPARBARHET-OCH-PROJEKTKONTROLL.md)

Befintliga dokument och kod har inte beställts ändrade. Inga extra schema-/facitfiler, namn på bedömare, faktiska kontrollnycklar, källpaket eller anslutningar skapas.

## Förestatus från Git

Följande är hela den namnlista Git rapporterade före dokumentleveransen. Den innehåller namn på .env.example och en arkivkopia, men deras innehåll har inte lästs. .env, credentials, privata referenser och driftens databaser har inte öppnats eller hashats. Gitstatus ger inga garantier om ignorerade driftfiler; sådana filer ligger utanför denna innehållsinventering.

~~~text
?? .env.example
?? .gitignore
?? .vscode/launch.json
?? AGENTS.md
?? JARVIS-VS-Code.zip
?? JARVIS-VS-Code/.env.example
?? JARVIS-VS-Code/.gitignore
?? JARVIS-VS-Code/.vscode/launch.json
?? JARVIS-VS-Code/AGENTS.md
?? JARVIS-VS-Code/README.md
?? JARVIS-VS-Code/backend/jarvis/__init__.py
?? JARVIS-VS-Code/backend/jarvis/api.py
?? JARVIS-VS-Code/backend/jarvis/auth.py
?? JARVIS-VS-Code/backend/jarvis/budget.py
?? JARVIS-VS-Code/backend/jarvis/cli.py
?? JARVIS-VS-Code/backend/jarvis/config.py
?? JARVIS-VS-Code/backend/jarvis/db.py
?? JARVIS-VS-Code/backend/jarvis/demo.py
?? JARVIS-VS-Code/backend/jarvis/live.py
?? JARVIS-VS-Code/backend/jarvis/models.py
?? JARVIS-VS-Code/backend/jarvis/research.py
?? JARVIS-VS-Code/backend/jarvis/roles.py
?? JARVIS-VS-Code/backend/jarvis/schedule.py
?? JARVIS-VS-Code/backend/jarvis/service.py
?? JARVIS-VS-Code/backend/jarvis/worker.py
?? JARVIS-VS-Code/backend/migrations/001_initial.sql
?? JARVIS-VS-Code/backend/migrations/002_schedule.sql
?? JARVIS-VS-Code/docs/VERIFIERING.md
?? JARVIS-VS-Code/docs/screenshots/desktop.png
?? JARVIS-VS-Code/docs/screenshots/mobile.png
?? JARVIS-VS-Code/frontend/e2e/app.spec.ts
?? JARVIS-VS-Code/frontend/e2e/teardown.mjs
?? JARVIS-VS-Code/frontend/index.html
?? JARVIS-VS-Code/frontend/package.json
?? JARVIS-VS-Code/frontend/playwright.config.mjs
?? JARVIS-VS-Code/frontend/pnpm-lock.yaml
?? JARVIS-VS-Code/frontend/pnpm-workspace.yaml
?? JARVIS-VS-Code/frontend/src/Schedule.tsx
?? JARVIS-VS-Code/frontend/src/main.tsx
?? JARVIS-VS-Code/frontend/src/style.css
?? JARVIS-VS-Code/frontend/src/types.ts
?? JARVIS-VS-Code/frontend/tsconfig.json
?? JARVIS-VS-Code/frontend/vite.config.ts
?? JARVIS-VS-Code/pytest.ini
?? JARVIS-VS-Code/requirements.lock
?? JARVIS-VS-Code/scripts/e2e_server.py
?? JARVIS-VS-Code/scripts/setup.ps1
?? JARVIS-VS-Code/scripts/start.ps1
?? JARVIS-VS-Code/scripts/windows_job.py
?? JARVIS-VS-Code/tests/conftest.py
?? JARVIS-VS-Code/tests/test_core.py
?? JARVIS-VS-Code/tests/test_first_run.py
?? JARVIS-VS-Code/tests/test_live_adapter.py
?? JARVIS-VS-Code/tests/test_schedule.py
?? README.md
?? backend/jarvis/__init__.py
?? backend/jarvis/api.py
?? backend/jarvis/auth.py
?? backend/jarvis/budget.py
?? backend/jarvis/cli.py
?? backend/jarvis/config.py
?? backend/jarvis/db.py
?? backend/jarvis/demo.py
?? backend/jarvis/dispatch.py
?? backend/jarvis/external_http.py
?? backend/jarvis/live.py
?? backend/jarvis/models.py
?? backend/jarvis/poc_a0.py
?? backend/jarvis/poc_service.py
?? backend/jarvis/research.py
?? backend/jarvis/roles.py
?? backend/jarvis/schedule.py
?? backend/jarvis/service.py
?? backend/jarvis/worker.py
?? backend/migrations/001_initial.sql
?? backend/migrations/002_schedule.sql
?? backend/migrations/003_research_a0.sql
?? backend/migrations/004_dispatch.sql
?? docs/ANROPSGRANS-V1.md
?? docs/RESEARCHLABB-A0.md
?? docs/VERIFIERING.md
?? docs/research-poc/2026-10-18-v0.1.0-a5c383c6/00-PROTOKOLL.md
?? docs/research-poc/2026-10-18-v0.1.0-a5c383c6/01-AMNEN-OCH-KALLURVAL.md
?? docs/research-poc/2026-10-18-v0.1.0-a5c383c6/02-JAMFORELSE-OCH-BEDOMNING.md
?? docs/screenshots/desktop.png
?? docs/screenshots/mobile.png
?? docs/screenshots/research-a0-desktop.png
?? docs/screenshots/research-a0-mobile.png
?? frontend/e2e/app.spec.ts
?? frontend/e2e/research-lab.spec.ts
?? frontend/e2e/teardown.mjs
?? frontend/index.html
?? frontend/package.json
?? frontend/playwright.config.mjs
?? frontend/pnpm-lock.yaml
?? frontend/pnpm-workspace.yaml
?? frontend/src/ResearchLab.tsx
?? frontend/src/Schedule.tsx
?? frontend/src/main.tsx
?? frontend/src/research-lab.css
?? frontend/src/style.css
?? frontend/src/types.ts
?? frontend/tsconfig.json
?? frontend/vite.config.ts
?? pytest.ini
?? requirements.lock
?? scripts/e2e_server.py
?? scripts/setup.ps1
?? scripts/start.ps1
?? scripts/windows_job.py
?? tests/conftest.py
?? tests/test_core.py
?? tests/test_first_run.py
?? tests/test_live_adapter.py
?? tests/test_poc_a0.py
?? tests/test_schedule.py
~~~

## Innehållssnapshot före arbetet

Tillåten innehållsinventering: huvudprojektets AGENTS/README, backendkällor/migrationer, tester, frontendkällor/testdefinitioner och uttryckligen valda bygg-/beroendefiler, scripts samt de tre tidigare protokollen och offentlig projektdokumentation. Bara läsning och hashning av dessa filer; ingen kodexekvering. Arkivkopian JARVIS-VS-Code, ZIP, node_modules, .venv, .git-innehåll, data, .env och privata ytor ingår inte.

| Sökväg relativt projektroten | Byte före | SHA-256 före |
| --- | ---: | --- |
| AGENTS.md | 858 | 4f8b512cac41e28a8a4651ed1e26a449284450e24fffa72ae4272adf60d9d4b5 |
| backend/jarvis/__init__.py | 1 | 01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b |
| backend/jarvis/api.py | 13551 | 3f5def82702bd563431ed331a8c9b761418bf24399519eda7b6ad210fda40f2d |
| backend/jarvis/auth.py | 4022 | 8546da8b9d6a72a7f16380cbc63983be4a1fccb2423ddcd0d58332fe4a55c82e |
| backend/jarvis/budget.py | 2348 | f956418afb465d300fc6407bb039b658fbccb8d77501e87bd0811e873d47f2e7 |
| backend/jarvis/cli.py | 1098 | 0d3fa435d116a2f8b003bb580a010defece270acb98992589cadeaabaaba8d3d |
| backend/jarvis/config.py | 1333 | 2dd4adff6bdc73ec74d4099d88c2588bff63ef757f48f67aaf3a4b413df6c821 |
| backend/jarvis/db.py | 1922 | 666c7d171e81cc986e33f8212effd63c76e4fd04f276ba397ecbed5490d38a0c |
| backend/jarvis/demo.py | 2899 | 4328a72a084c3fa7cfcc3ec8679015ecb918b54bf8775b789452fefc737f61f3 |
| backend/jarvis/dispatch.py | 11651 | 2b78ee1bb13c968d891a4e6f5fbab88df36511c659b33762ccd3c13d7de5245a |
| backend/jarvis/external_http.py | 5562 | 4352e258c172da39453637d317c13facdcbd770dda557866516cdd40d521a3fe |
| backend/jarvis/live.py | 2768 | b0d672db73489161a825edac7d22568b5d7a14f4049603a2c1ec95590ac91936 |
| backend/jarvis/models.py | 1747 | 69e654ae75bc4d9b72d57a8e7f9cad145262c913049667bd995ad8f0d83641d1 |
| backend/jarvis/poc_a0.py | 12132 | 0bc0797299767c9ed236c04f2c839df1a32bf788dd389497bf457ae968112791 |
| backend/jarvis/poc_service.py | 3457 | 812cb127b7015c8636b7cfca32a11bf570dc5eba60189855f7df8c40a6f1eb1c |
| backend/jarvis/research.py | 3009 | c3d55fecf34e790f11bd66b9ddc2ea4b4f5393dd0f23002b36224032feb8e75a |
| backend/jarvis/roles.py | 2245 | b76c4e733b6f0c3fe0493c412689af11169f383192c4d131c42b88b2a1659e27 |
| backend/jarvis/schedule.py | 1578 | 8bf14b4649656ca4a1317be1307fd6d7d4aa83ce9b6d0d05dbb611dbc634907b |
| backend/jarvis/service.py | 10052 | 3dab2f3ec9d693907e4640a1cf7921beba9e13fb59af3ca10517ed0776e5b6b6 |
| backend/jarvis/worker.py | 6621 | 393cfa844aa9fea8a13a86150c213cf6b9b3c7d3f1d9d7a1f8ebc5c0130f9158 |
| backend/migrations/001_initial.sql | 3670 | dd6b27acf644c11db3c16ed009f8f947178996e71756c8201f0484f8361e3d20 |
| backend/migrations/002_schedule.sql | 421 | 86ead454b245c26d741cbb7070cfe7f47504f8fa4e7c77c7b6c330eda7b7779e |
| backend/migrations/003_research_a0.sql | 280 | ad2d421fc970d9dced968db78cc551faf9dffceda2dae0c7b5cebff8a88ce28b |
| backend/migrations/004_dispatch.sql | 1108 | 7318d7fd96d17011b1699d0f707414ad2c9f727f7ce222f3f8dc8341553c36a3 |
| docs/ANROPSGRANS-V1.md | 15311 | 19d14e9685abf2140f8d086915007ac36862be4391488498a3a506128e962950 |
| docs/research-poc/2026-10-18-v0.1.0-a5c383c6/00-PROTOKOLL.md | 7941 | ef9066a268d43c65e0b7cb90c539d6e5aeb5ef8201845a65489976291d0cd0fa |
| docs/research-poc/2026-10-18-v0.1.0-a5c383c6/01-AMNEN-OCH-KALLURVAL.md | 12382 | e41298c621eecba6e5aad3861223d67e5931149f3bda9bf17b8599b447042234 |
| docs/research-poc/2026-10-18-v0.1.0-a5c383c6/02-JAMFORELSE-OCH-BEDOMNING.md | 13262 | d2a5876f4691ad69fc36af6ebb484cb101a970a5aa6836250d634b925c300901 |
| docs/RESEARCHLABB-A0.md | 5183 | 5e8a828739a3ed50e014374598c3c57e336c4a635fa84f7e56b34c9749a53edf |
| docs/VERIFIERING.md | 6024 | 90b1eacd79053d598e90ce592d424ab70fd21dd3062e573fb33d31703d9a1a9d |
| frontend/e2e/app.spec.ts | 5438 | d84a02b39798468cab807289e8a687e4f7ce8adb90d7976bbb87a0913d92c7ef |
| frontend/e2e/research-lab.spec.ts | 4940 | 7f9388bd817f93f0ea7e15c9f0a7244aa319a1bbe82a4412d969e1985baa4448 |
| frontend/e2e/teardown.mjs | 409 | 178c1d8ec5f874ff42046ddddf217d205fcd6fb3a4fa0bb6c8f3e94ce888ac96 |
| frontend/package.json | 538 | d8dd54fdf00c6f6b30ef43805266b8ee6d6cbf30b5a128a6b8c7e74fe1c3a947 |
| frontend/playwright.config.mjs | 575 | aacaedba0f1132018f1380e426e8e806f8e038b908e57f4e303dbaf6997c26ea |
| frontend/pnpm-lock.yaml | 49892 | fb1b715963e41d9b5970f1c134bb3cfcaafb5b2988fc7f3bba2e6cb7bf7f0fe8 |
| frontend/src/main.tsx | 34858 | a24c83655fd4f2dcf7d87c911d555162781024b5e7e5d476565ccef4d0a06655 |
| frontend/src/research-lab.css | 8911 | 54655f8071d3540ce83bb75d8ece496e8f43ba181792bc515bf8c454205b9209 |
| frontend/src/ResearchLab.tsx | 11396 | d6ca43500b34c980d9eaa69d75e4e601676e6cee023db8bed8fdab1199b9268b |
| frontend/src/Schedule.tsx | 2079 | b4c719aee79cb941356dacbadc88879c01e866e4a643c1998de9fdeaf533753c |
| frontend/src/style.css | 26367 | 75ab1a620fb222cd734245b1ecb00d19cc1af1220b82e9378540e36feb9ddc20 |
| frontend/src/types.ts | 1955 | 349c8dae7ae0b87696d5e4ae6f8a40123464bb934a5369d28e350b7e04a5c237 |
| frontend/tsconfig.json | 323 | efb0957743d2ff68dfd4243a7c4ec5d204367ae38e0d1f92d204ec23ee7faa22 |
| frontend/vite.config.ts | 236 | 55c1665dc597dd920b43f7f271a1c42d8d2f2f0e0e59ad5928c407f54235dfc9 |
| pytest.ini | 49 | a1bc4529dd413300d58b32e2a4d98903e61bf9138f3f9d7955ab6e04b5104d94 |
| README.md | 15507 | 6a18744a065de457ee484c575445402b4d9e29474ee91418c1366bdae99e275b |
| requirements.lock | 984 | a6e72e6662a2219a722bd6d2a4407873ef0536f2cd33f8549feaf5187c3aa878 |
| scripts/e2e_server.py | 1548 | 1043cd97e092ca0aa7bcb8507d4f7ca0efdb667d8e3698948b38960bb804b9a2 |
| scripts/setup.ps1 | 1843 | 4f7c42912bdc2769427401840eab6b0d43cd8b7dda9212701cc8cd552a897615 |
| scripts/start.ps1 | 1464 | 3b108caab5877039625d7af0a2e7254fefe3da8074477a0703022f8096f51cf4 |
| scripts/windows_job.py | 1756 | aa66a6515e7f6132c1cbe5ccdda901d2278687e25194d5652c93d0cf00d56d65 |
| tests/conftest.py | 939 | 69bfe733654b6c8cff37616b2272afc7aef7287a567f287634a6800ef668d57f |
| tests/test_core.py | 11098 | 3cdeff4c97ad55a76f9563fe31c982d179902397896a51fd44969919d1b58855 |
| tests/test_first_run.py | 1674 | 34d185556ad5ee8217afa7c0939a51fc28f9cf33750bed66ee41a053e172fabe |
| tests/test_live_adapter.py | 26752 | c3746bb39dac503939ae0ee2289493f2478a8822b6cbe394c9cb3c1e98a155a3 |
| tests/test_poc_a0.py | 10509 | 3410fc81b345a2a0a973baf82d01b24ecda61466671927e56d2461bb09a631bb |
| tests/test_schedule.py | 1288 | 6e17842a580da098d7a697570946bd043bfae235155919b6113e2bdc3935f2e8 |

## Efterkontroll

Efter-snapshot: **2026-10-19T22:32:55.9633436Z** UTC (2026-10-20, Europe/Stockholm).

- Git: **116 → 123** statusposter, fortfarande utan commit på master. Alla tidigare 116 namn finns kvar. Exakt de sju ovan angivna nya dokumenten har tillkommit; inga andra tillagda eller borttagna statusposter.
- Innehåll: **57 av 57** inventerade befintliga filer har identiskt byteantal och SHA-256 före och efter. Det omfattar de tre gamla protokollen samt inventerad kod, tester, offentlig dokumentation och bygg-/beroendedefinitioner.
- Dokumentkontroll: lokala Markdown-länkar pekar på befintliga filer. Tio JSON-block har kontrollerats för dokumentens JSON-syntax; inga syntaxfel hittades. Beslutsregelns exempel har granskats som syntetiska handexempel. Detta är dokumentkontroll, **inga JARVIS-tester, byggen eller modellkörningar**.
- Ingen skrivning utanför den nya versionsmappen har gjorts av detta uppdrag. Inga modeller/priser/budgetar eller verkliga referensfakta har lagts in i konfiguration eller driftdata.

Efterstatusens namnset är exakt förelistan plus dessa poster:

~~~text
?? docs/research-poc/2026-10-20-v0.2.0/00-PROTOKOLL.md
?? docs/research-poc/2026-10-20-v0.2.0/01-AMNEN-OCH-KALLURVAL.md
?? docs/research-poc/2026-10-20-v0.2.0/02-JAMFORELSE-OCH-BEDOMNING.md
?? docs/research-poc/2026-10-20-v0.2.0/03-PASTAENDEN-OCH-SLUTLEVERANS.md
?? docs/research-poc/2026-10-20-v0.2.0/04-IMPLEMENTATIONSUPPDRAG.md
?? docs/research-poc/2026-10-20-v0.2.0/05-FRYSNING-OCH-INTEGRITET.md
?? docs/research-poc/2026-10-20-v0.2.0/06-SPARBARHET-OCH-PROJEKTKONTROLL.md
~~~

Dokumentleveransens egna hashvärden 00–05 registreras efter slutlig läsning nedan. Detta dokument 06 saknar avsiktligt egen inbäddad hash för att undvika självreferens. Det kan hashberäknas externt. Leveranshashar är inte frysningsbeslut.

| Nytt dokument | Byte | SHA-256 |
| --- | ---: | --- |
| 00-PROTOKOLL.md | 9450 | cb6b55f4e525cc2ae20d8fc20be35a0c3807fbf507db1928149fc7cc6ec63089 |
| 01-AMNEN-OCH-KALLURVAL.md | 12461 | fc1e8519a787f2e22ee083553e5b41f6e37eaed5095a592634a3546baa118cda |
| 02-JAMFORELSE-OCH-BEDOMNING.md | 18288 | 86ca2a04a751239cbb71daf54e95ee403e6f59da161ef11d74674c945ac0f608 |
| 03-PASTAENDEN-OCH-SLUTLEVERANS.md | 35697 | 99f49dfd8b0c027b0b40ba0137377639f93dddbee270942263e8e8357a33e1c8 |
| 04-IMPLEMENTATIONSUPPDRAG.md | 9142 | 8eccab5ea8ce898f914155f65a0640e072a3c96d0d955ed5ecf5e21c385b0c4a |
| 05-FRYSNING-OCH-INTEGRITET.md | 20477 | 5f6ea8e2919c98caf4dc96574d0ef69f9f86443ed07dfceb44d4437ff1e5892e |

## Kvarvarande mänskliga beslut och verkliga hinder

- Godkänn eller revidera metodförslaget och den nya beslutsregeln före insamling.
- Välj namngiven söktjänst och lås inställningar/frågeexpansion innan någon sökning.
- Utse minst två bedömare och ansvar för insamling, operatör, maskering och privata nycklar; bekräfta realistisk arbetsram.
- Besluta ekonomi-/tidsacceptansgränser, senare faktiska modell-/pris-/valutaversioner och uttrycklig budget.
- Godkänn separat privat förvaring och input-allowlist; samla och lås verkliga källpaket och referenser senare.
- Beställ och granska framtida A1-implementation enligt 04. Dagens A0/anropsgräns är inte en fungerande A1-adapter.
- Kontrollera att hela paketet, utkastet, instruktionerna och verkligt kompilerat schema ryms i den preliminära ramen. Revidera före frysning om så inte är fallet.
- Frys körningsmanifestet och ge separat tillstånd till exakt de nio platserna först när samtliga villkor uppfyllts.

Det här uppdraget stannar efter dokumentleveransen. Inga tester, byggen, installationer, källsökningar, driftmigreringar, LIVE-aktiveringar eller leverantörsanrop har utförts.

**UTKAST – INTE KÖRKLART:** godkännanden, bemanning, verkliga paket och privata referenser, exakta ekonomiska uppgifter, A1-implementation och lokal A1-verifiering saknas.

# Researchlabb A0

Implementerat 2026-10-19. A0 demonstrerar researchflödets struktur med förutbestämda svar och syntetiska källtexter. Det är inte ett genomfört experiment med AI-modeller och utser ingen vinnare.

## Användning

Starta JARVIS som vanligt och logga in. Välj **Researchlabb** i vänstermenyn. I DEMO kan ägaren återuppta systemet och välja **Kör lokal A0-demo**.

En körning sparar tre syntetiska ämnen med tre arbetsflöden vardera:

- S1: ett simulerat Researcher-steg.
- S2: samma ursprungliga exempel följt av simulerad självgranskning.
- RK: samma ursprungliga exempel följt av ett simulerat Kritiker-omdöme.

Det blir nio slutrapporter, femton simulerade steg och noll externa anrop. Kostnaden för dessa lokala demonstrationer är noll öre. De använder ingen worker, inget SDK och inga leverantörsnycklar. Programmerad demonstrationslogik är inte bevis för modellernas förmåga. Ett exempel visar uttryckligen en felaktig kritikerinvändning.

## Spårbarhet och integritet

Varje körning sparar exakt demonstrationsversion, källtexter, rollinstruktioner, indata och utdata per steg, ursprungliga påståenden, omdömen och mekanisk slutleverans. JSON-exporten innehåller samma material och en SHA-256-kontrollsumma över körningens kanoniska JSON (UTF-8, sorterade nycklar, utan extra blanksteg). Kontrollsumman verifieras vid läsning.

Källhänvisningar måste ange ett känt käll-ID, exakt utdrag och giltiga UTF-8-bytepositioner. Det är en strukturell kontroll: den garanterar **inte** att källans betydelse stöder påståendet. Programmet säger aldrig att semantiskt stöd har verifierats.

Granskningen måste omfatta varje påstående exakt en gång. Omdömen kan leda till att påståenden tas bort. Om ett nödvändigt beroende försvinner blir den slutliga rekommendationen Avstå. Ett granskningssteg får inte uppgradera den ursprungliga rekommendationen. Sluttexten byggs enbart från kvarvarande påståenden och aktuella beslut; tidigare löptext återanvänds inte.

Samma åtgärds-ID och underlagshash återger samma sparade körning, även efter ett förlorat nätverkssvar. Det skapar inte ett nytt experiment. Samma åtgärds-ID med annat underlag avvisas. Inga automatiska omförsök görs.

## Lagring och befogenheter

Migration 003 skapar `research_a0_runs`. A0 använder den befintliga DEMO-databasen och samma transaktionella databasgräns som JARVIS. Inga A0-kandidater, syntetiska kostnader eller uppgifter blandas in i verksamhetens vanliga tabeller. En verklig logghändelse registreras när en demonstration har sparats.

Samtliga API-rutter kräver ägarinloggning. Start kräver dessutom CSRF/Origin-kontroll, DEMO och återupptaget system. Paus och nödstopp avvisar nya körningar, medan sparade resultat kan läsas i DEMO. Hela den lokala körningen sparas i en transaktion. Ett misslyckande lämnar inga delrapporter. A0 accepterar inga godtyckliga källsökvägar, kod eller modellnamn.

A0-data läses eller körs inte i LIVE. Tio befintliga roller bevaras. Historiklistan visar de senaste 30 körningarna; arkivet tillåter högst 100 körningar och raderar inget automatiskt.

## Återstående arbete

A1 och B är inte anslutna till labbet. Befintlig LIVE-kod i övriga JARVIS är oförändrad och dess tidigare identifierade begränsningar behöver åtgärdas före riktiga PoC-anrop.

Före A1 återstår bland annat färdigt försöksprotokoll, metod- och körningsfrysning, riktiga kontrollerade källpaket, privat referensmaterial, mänsklig bedömning, driftläges-/dispatchskydd, verifierad prisprofil, resursram och ett uttryckligt godkännande. Det tidigare protokollutkastet är fortsatt **INTE KÖRKLART**; denna implementation ändrar inte dess innehåll eller hashvärden.

B kräver dessutom bredare research, Kritiker-motresearch och budgetreservation före varje betalt sökanrop. Ingen av dessa funktioner aktiveras av A0.

## Verifiering 2026-10-19

- Hela backendtestsviten: **65 godkända**, 33,99 sekunder. Där ingår 22 A0-testfall för bland annat UTF-8-citat, borttagna beroenden, felaktiga kritikerinvändningar, schemafel, DEMO-spärr, paus/nödstopp, samtidiga dubbelstarter, återöppning, export, integritet och autentisering/CSRF.
- TypeScript och Vite-produktionsbygge: **godkänt**. Inga nya beroenden installerades.
- Playwright/Chromium: **7 godkända**, 25,6 sekunder. Tre nya fall täcker A0-flödet, export, sparad körning efter omladdning, återhämtning efter tappat svar, mobilbredd och nödstopp. De fyra befintliga flödestesterna passerade också.
- Datorvy 1440 px och mobilvy 390 px granskades visuellt. Ingen horisontell sidöverströmning i det testade mobilflödet. Vänstermenyn kan rullas på lägre skärmar.

Testerna använde tillfälliga DEMO-databaser. A0-backendtesterna blockerade externa nätverksanslutningar och namnuppslag; lokal loopback tilläts för Windows testmiljö. Inga betalda verifieringsanrop utfördes. Modellsvar, verklig källtillgång, kommersiella belägg och leverantörsdebitering har inte verifierats.

- [Datorvy](screenshots/research-a0-desktop.png)
- [Mobilvy](screenshots/research-a0-mobile.png)

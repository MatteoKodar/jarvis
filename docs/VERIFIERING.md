# Verifiering av JARVIS

Utförd 2026-10-18 på Windows, i denna projektmapp. Alla körningar var lokala. Inga betalda modell-anrop, konton, köp, utskick eller publicering gjordes.

## Körda kontroller

| Kontroll | Resultat |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **43 passed in 20.96s** |
| `pnpm run build` | **Godkänt**: TypeScript och Vite 7.1.12, 1 579 moduler |
| Playwright/Chromium, sista körningen | **4 passed (19.2s)** |
| `python -m pip check` | **No broken requirements found** |
| PowerShells syntaxparser för setup/start | Inga syntaxfel rapporterade |
| Visuell granskning | Skärmbilder av dator 1440 px och mobil 390 px inspekterade |

Den sista frontendbyggnaden gav cirka 245 kB JavaScript och 30 kB CSS före gzip. Bibliotek och transitive beroenden är låsta i `requirements.lock` respektive `frontend/pnpm-lock.yaml`.

Miljöns Python och Node finns inte i den vanliga PATH. Verifieringen använde `.venv/Scripts/python.exe` och Codex medföljande Node/pnpm med absoluta sökvägar. Chromium installerades i den ignorerade katalogen `data/browsers`. `PLAYWRIGHT_BROWSERS_PATH` sattes till den katalogen vid testerna.

## Backendtesternas täckning

- Exakt tio stabila agentroller och SDK-agentdefinitioner.
- Komplett kedja: uppdrag → VD-resultat → förslag → beslut → specialist → kritiker → beständiga rapportfiler.
- Godkänn, avslå och begär ändring; ny version får nytt innehållshash och kräver nytt godkännande.
- Väntande beslut efter ny databasinitialisering och efter SQLite-backup/återställning i separat datakatalog.
- Sekventiella och samtidiga dubbelgodkännanden skapar bara en arbetsuppgift.
- Idempotenta uppdrags-ID:n, utgångna förslag och spärr mot godtycklig extern åtgärdstyp.
- Agent kan inte agera som ägare eller skapa en otillåten roll.
- Två samtidiga budgetreservationer konkurrerar transaktionellt; ingen överbokning av dagstak.
- Avstämning släpper reservationen; ny kalenderdag nollställer inte totalförbrukning.
- Okänd debitering efter krasch håller kvar reservationen tills ägaren stämt av.
- Beständig nödstoppstatus, paus som tillåter aktuell uppgift att avslutas och global gräns på två samtidiga uppgifter.
- DEMO anropar inte LIVE-adaptern; saknad nyckel i LIVE ger fel utan demofallback.
- Obehörig API-, SSE- och filåtkomst nekas; CSRF/Origin kontrolleras; extra privilegiefält avvisas.
- Inloggningsbegränsning överlever omstart; filnedladdning sker som textbilaga; sökvägsförsök nekas.
- Statuschatt kan inte godkänna eller starta externa handlingar.
- Budgetändringar kräver ägare och får inte underskrida redan upptaget utrymme.
- Högst ett aktivt utvecklingsprojekt.
- LIVE-testadaptrar: sparad token-/modell-/pris-/valutametadata, okänd kostnad vid leverantörsfel och avbrott, nödstopp före dispatch samt nekad modell utan matchande prisprofil.
- Researchadapter med simulerat HTTP-svar: fast värd, begränsad mängd, borttagen HTML, sparad URL, tid och källursprung. Otillåtna roller nekas.
- Schema med begränsat antal körningar, beständig en-gång-per-dag-kontroll, paus, slutdatum och högst sju omgångar.
- Första-start-konto: lokal ägare kan skapas utan standardlösenord. Svagt lösenord, främmande Origin, fjärranslutning och försök att ersätta ett befintligt konto nekas.

## Webbläsartesterna

1. Inloggning, återuppta, starta arbetsomgång, granska och godkänna förslag, tre demokandidater och exakt tio agentkort. Skärmbild av översikten.
2. Mobilbredd 390 px utan horisontell sidöverströmning. Inskickad `<script>`/`onerror`-text visas bokstavligt och skapar inga script- eller bildnoder. Mobilskärmbild.
3. Skapa uppdrag, stäng hela webbläsarkontexten, logga in i en ny kontext och observera att separat worker har sparat förslaget.
4. Ägarens budgetändring, skapa/stänga begränsat schema och registrera manuell kostnad. Testet låter backend spara kostnaden men avbryter nätverkssvaret; ett nytt försök ger fortfarande exakt en kostnadspost.

Testservern använder en tillfällig DEMO-databas och ett separat testlösenord, inte ett produktionskonto. Servern och workern stängs automatiskt efter testerna. En tidigare Windows-teardown hängde efter godkända testfall; den rättades med en explicit stoppsignal och processhantering. Slutkörningen avslutades själv med exitkod 0 på 18,3 sekunder.

## Visuell granskning

- [Datorvy](screenshots/desktop.png)
- [Mobilvy](screenshots/mobile.png)

Agentnamn som först blev för korta på mobil ändrades till en läsbar vertikal kortlayout. Anslutningsstatus visas även som text i mobilens statusrad. Inga externa bilder eller typsnitt behövs.

## Ej verifierat / begränsningar

- Ingen riktig OpenAI-körning eller debitering. SDK-adaptern byggs och testas med ersatta svar; faktisk modellåtkomst och leverantörsanvändning måste verifieras separat av ägaren.
- MediaWiki-integrationen testades med HTTP-testadapter, inte ett verkligt nätverksanrop i leveransen. Faktisk tillgänglighet och datakvalitet är inte verifierade.
- Ingen verifierad affärsefterfrågan, betalningsvilja eller intäkt. Demokandidaterna är exempel.
- Ingen Linuxserver, HTTPS-reverse-proxy, publik drift, belastningstestning eller extern säkerhetsrevision.
- Installationsskriptet har syntaxkontrollerats; hela interaktiva installationen inklusive ägarens lösenordsval har inte automatiserats. Motsvarande beroendeinstallation, frontendbygge, API, worker och autentisering har körts i testerna.
- SSE levererade uppdateringar i arbetsflödestesterna; längre nätverksavbrott och fullständig återspelning över serveromstarter har inte ett separat webbläsartest.
- Tillgänglighet har inte genomgått en fullständig extern WCAG-granskning. Minskad rörelse stöds i CSS, textetiketter används och innehåll exekveras inte som HTML.
- Begränsningar i funktionalitet, såsom regelbaserad statuschatt och avsaknad av full experiment-/publiceringslivscykel, listas i README.

# Framtida implementationsuppdrag A1 v0.2.0

**UTKAST – INTE KÖRKLART.** Inget uppdrag i detta dokument implementeras eller testas nu. Varje uppdrag kräver separat beställning; extern körning kräver dessutom körningsfrysning och uttryckligt beslut.

## Kodlästa fynd vid denna dokumentleverans

| Fynd i läst kod | Följd för A1 |
| --- | --- |
| [poc_a0.py](../../../backend/jarvis/poc_a0.py): VERSION=a0-1.0.0, syntetiska data, Report/Review och revise() | A0 har inga riktiga modellanrop. Review saknar tillägg och egna beroenden; revise() kan bara sänka nivån och kan därför inte återanvändas oförändrad |
| [poc_service.py](../../../backend/jarvis/poc_service.py), migration 003 och API:s /api/research-poc/a0 | Lagrar en färdig A0-snapshot. Ingen beständig A1-förgrening eller stegvis anropsbok finns |
| [live.py](../../../backend/jarvis/live.py): make_agents(), run() | Ärver dagens ROLES-instruktioner, använder AgentResult och startar Wikipedia för behörig work-roll. Denna väg uppfyller inte A1:s rena paketindata |
| [models.py](../../../backend/jarvis/models.py): AgentResult/Claim | Har andra fält, inget fryst gemensamt utkast, inga passagecitat/bedömningar enligt A1 |
| [dispatch.py](../../../backend/jarvis/dispatch.py): prepare(), checked(), authorize(), control(), recover() | Har persistent task/run-bindning, pris-/resursfrysning, reservation och stoppnummer. Endast model.responses:1 och research.wikipedia:1 per task/run stöds |
| [external_http.py](../../../backend/jarvis/external_http.py): ModelBoundary, validate_model() | Har ett transportförsök, fasta endpoint-/kroppskontroller och versionsspärr. Kontrollerna är bundna till dagens payload och instruktioner; nytt A1-schema kan inte bara skickas igenom |
| [worker.py](../../../backend/jarvis/worker.py): claim(), finish(), fail() | Vanligt work-resultat köar automatisk Kritikergranskning. Det motsvarar inte ett gemensamt utkast med två isolerade grenar |
| [budget.py](../../../backend/jarvis/budget.py), API reconcile | Heltalsören, held/unknown, total/dag/uppgift/låst reserv samt manuell avstämning finns. Avstämning återöppnar inte en operation |
| [config.py](../../../backend/jarvis/config.py): missing_live() | Nuvarande modellvalidering kräver både paid- och researchflagga. A1 behöver uttryckligt profilskydd mot sökning oberoende av en sådan generell flagga |
| [roles.py](../../../backend/jarvis/roles.py): VERSION=1.0.0, tio poster | Behörighetsrollerna Researcher/Kritiker kan behållas; inga nya agentroller behövs. Metodinstruktioner måste bli uttryckligt frysta profiler |

Detta är statisk kodläsning. Konfigurationens **kod** har lästs som text; modulen har inte importerats, .env har inte lästs och inga databaser har öppnats. Dokumentens äldre testresultat är historiska uppgifter, inte verifiering genomförd i detta uppdrag.

## I01 Strikta A1-format och renderer

Omfattning: separata versionerade A1-datatyper enligt 03, citatkontroll, ny tilläggsregel och gemensam mekanisk renderer. Ingen leverantör, worker eller nytt UI.

Acceptans för ett framtida lokalt uppdrag:

- Avvisa extra fält, felaktiga offset, okända ID, dubbla/utelämnade omdömen, fler än sju original eller ett tillägg.
- Behåll bara stod-poster och eventuellt N01. Ingen textrest från borttagna belägg får finnas i renderertexten.
- Stöd både höjd och sänkt nivå med giltiga nya beroenden; hantera känt borttaget beroende genom avsta-fallback. Okända beroenden är formatfel.
- Visa skillnaden mellan strukturellt godkänt och mänskligt stöd. support_verified är false.
- Bevara A0:s gamla typer, utdata och nio rapporter/femton simulerade steg/noll anrop.
- Lokal verifiering med helt syntetiskt material, inga SDK- eller nätverksanrop.

## I02 Beständigt utkast och nio fasta anropsplatser

Omfattning: ny separat migration och A1-lagring, utan ändring av gamla migrationer eller nollställning av data. Ett experiment har tre ämnesbindningar, tre draftplatser, sex granskningsplatser och nio lokala slutrapportplatser.

Föreslagen liten återanvändningsväg är **en separat auktoritativ uppgift/körning per modellanrop**, behörighetsroll researcher för draft/självgranskning och critic för Kritiker. Därmed kan dagens model.responses:1 återanvändas som logisk modelloperation, men en unik experiment/topic/stage-bindning måste beständigt peka på samma task/run/operation. Ett nytt HTTP-ID eller nytt workeranspråk får inte skapa en ny körning för en redan upptagen experimentplats.

Acceptans:

- Samma skapandeåtgärd och underlag ger samma experiment; ändrat underlag avvisas.
- Råa utkastbyte och validerad struktur sparas före grenar. Båda grenarna binds till samma bytehash.
- Dubblettstart, omstart och samtidiga workers ger inte ett nytt utkast, grenanrop eller dubbel kostnad.
- A1 får en egen arbetsflödesklassning. Normal worker.finish() får inte skapa sina vanliga specialist-/granskningssteg efter ett A1-resultat.
- Ingen modell kan skapa platser, välja prisprofil eller höja tak. Beständig unikhet gäller också efter unknown och ägaravstämning.
- Nödstopp ogiltigförklarar också experimentets väntande platser, inte bara redan skapade uppgifters tillstånd. Återuppta får inte ge den gamla planen nya task/run-ID:n.

## I03 Fryst paketadapter genom befintlig anropsgräns

Omfattning: en backendstyrd, tillåten metodprofil för A1 draft och A1 review. Ingen generell fri systemprompt-/URL-/schemafunktion.

De fullständiga instruktionerna och outputschemahasharna blir auktoritativt frysta profilfält. Rollen används för behörighet, men dagens vanliga ROLES-personas får inte oplanerat läggas till. Granskningsprofilerna får endast den i 03 tillåtna rollmeningsskillnaden.

Acceptans:

- Gå genom dispatch.prepare/bind/authorize och atomär reservation för **varje** anrop. Inget A1-anrop via research.search().
- Validera paket, fullständig input, fryst schema, modell/pris och experimentets stoppnummer före möjlig sändning.
- Utvidga transportens kontroller uttryckligt för den tillåtna A1-profilen. Behåll en sändning, no-retry i relevanta SDK-/HTTP-/transportlager, inga omdirigeringar, tracing av, inga tools/handoffs.
- A1 ska neka sökning även om Researcher normalt har Wikipedia-behörighet och en generell researchflagga är sann. Kopplingen mellan flaggorna är ett känt konfigurationshinder som måste få ett uttryckligt backendbeslut; det får inte lösas genom att kringgå anropsgränsen.
- Bevara prepared/possible_send/completed/unknown/cancelled, stoppnummer, hållna okända reservationer och manuell avstämning.
- Ingen tyst kapning av paket, utkast eller fullständigt granskningssvar. Ogiltigt svar kan ha kostat pengar och får inte bokföras som noll utan grund.
- Spara faktiskt begärd/returnerad modell, exakt schema och slutlig request-body utan credentials. Nuvarande exakta returmodellmatchning får inte lösas upp med en fri aliasregel.

## I04 Privat utvärderingsgräns och export

Omfattning: publik input-allowlist, separat mänsklig utvärderingsyta, beständigt utkastlås, anonymisering och tvåfaslås. Ingen modellbedömning.

Acceptans:

- Ingen privat referensfil, kontrolletikett, nyckel eller lokal hemlig sökväg kan nå en modellprofil.
- Anonymiserad Fas-I-export döljer branch/roll/original-/tilläggs-ID. Hela utvärderingsnyckeln hålls utanför modellens åtkomst.
- Alla påståenden, borttagningar, motiv, motbelägg och tillägg kan bedömas och spåras enligt 02–03.
- Låsta bedömningar är beständiga; rättelser görs som nya versioner med orsak. Avmaskering sker efter Fas-I-låset.
- Separera faktisk försökskostnad från separatdriftskalkyl. Noll användbara och okänd kostnad ger uttryckligt odefinierade kvoter.

## I05 Lokal integration och frysbar leverans

Först efter föregående separata beställningar: kör lokal verifiering med syntetiska paket och ersatta leverantörstransporter genom **verkliga relevanta installerade SDK-lager**. Ingen betald verifiering.

Acceptansen omfattar nio fasta logiska anropsplatser, tre delade utkast, två isolerade grenar, båda körordningarna, omstart/samtidighet, ändrat underlag, stopp före/efter markering, osäker kostnad, manuell avstämning utan återöppning, felaktigt/avbrutet svar, för stort underlag och privat informationsläckage. Räkna adapteranrop och HTTP-försök separat.

Kör då relevanta backendkontroller och därefter hela backendsviten, TypeScript/build och Playwright enligt AGENTS.md. Dessa framtida kontroller ska använda isolerade data och blockerat externt nätverk. Inga tester eller byggen har körts för denna dokumentleverans.

## Stopp före verklig A1

Efter lokal implementation återstår verkliga paket och privata referenser, namngivna bedömare, godkända arbets-/kostnadsramar, exakta modell- och prisversioner, fullständig inputstorlekskontroll, klientgranskning, körningsfrysning och ett uttryckligt ägarbeslut om just nio platser. B kräver ett nytt protokoll och nytt beslut. Detta dokument ger inget genomförandetillstånd.

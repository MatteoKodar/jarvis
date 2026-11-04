# Datakällor och genomförbarhet – v2

Kontroll: 4 november 2026, kl. 19.30–19.34 Europe/Stockholm (CET). Granskare: utvecklingsunderagenten Data. Underlaget är läst offentlig dokumentation, inte verifierade odds, leverantörsanrop, kontotillgång eller insatsacceptans. Inga konton skapades. Ingen hämtare aktiverades. Källregistret finns i `kallor.json`.

## Beslut och ändring mot planen 3 november

Huvudidé A är en tidsbestämd prisjämförelse med en svensk måloperatör och en referens som utesluter dess kända källfamilj. Det går ännu inte att visa att en sådan referens finns samtidigt på gratisnivån. Dokumenterad svensk leverantörstäckning är en möjlighet att testa, inte visad spelbarhet. Första piloten får misslyckas på denna punkt.

Gamla planen gav en övergripande kvotdiskussion och pekade ut källberoenden. V2 gör endpointbudget och tidsschema mer konkreta; här påstås inget aritmetikfel i gamla planen. Den föreslog tio observationsdagar utan låst matchantal och exakt tid. V2 låser ett tak på 30 matcher, två tidpunkter, ett tidsfönster och en kvotkalkyl. Den gör ingen metodjämförelse mellan power/Shin och bygger ingen fotbollsmodell i datasteget.

## Aktuella leverantörsfakta

- The Odds API: gratis 500 krediter/månad, de flesta bolag; 20 000 krediter 30 USD/månad, 100 000 krediter 59 USD/månad. Historik ingår i betalplaner. Ingen SEK-kostnad är verifierad; växling, skatt och betalavgift tillkommer om tillämpligt. [Prislista](https://the-odds-api.com/).
- Dokumentationen listar 13 svenska bolagsnycklar, bland annat `atg_se`, `svenskaspel_se`, `unibet_se`, `betsson` och `nordicbet`. Listning garanterar inte varje match, marknad eller gratisnyckel. [Bolagslista](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html).
- Förhandsodds för huvudmarknader uppdateras enligt leverantören var 60:e sekund. Det är ingen garanterad latens eller offertacceptans. [Uppdatering](https://the-odds-api.com/sports-odds-data/update-intervals.html).
- `h2h` innehåller oavgjort för fotboll. Kontraktet måste dessutom bekräfta ordinarie tid inklusive tilläggstid, inga förlängningar/straffar. [Marknader](https://the-odds-api.com/sports-odds-data/betting-markets.html).
- Villkor daterade 31 augusti 2026 tillåter lagring, analys, presentation och modellträning men förbjuder distribution som fristående rådataprodukt. Intern revisionslagring förefaller förenlig med detta; delning av råfiler till andra eller externa modellleverantörer är inte därmed verifierad. [Datavillkor](https://the-odds-api.com/terms-and-conditions.html).
- API-Football: gratis 100 anrop/dag med begränsade säsonger, Pro 19 USD/månad. Den officiella guiden anger cirka tre timmars uppdatering av förhandsodds och paginering. Det passar inte offertålder två minuter. Eventuell resultatreserv kräver separat verifiering av aktuell EPL-säsong och avräkningsfält. [Priser](https://www.api-football.com/pricing), [guide 13 mars 2026](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide).
- Football-Data avser privat/akademisk användning, manuell eller lätt hämtning högst två gånger/vecka; kommersiell användning och AI-träningsprojekt är inte generellt tillåtna. Befintligt privat arkiv bevaras. Ingen ny insamling eller träning föreslås. [Användningspolicy](https://football-data.co.uk/contact.php). Direkt läsning av data.php gav HTTP 429; contact.php kunde läsas. Sidans övergripande uppdateringsdatum var 3 november 2026; policyns egen versionsdag är okänd.

## Kvotregler lästa i dokumentationen

Sport- och eventlistor kostar 0 krediter. Ligaodds kostar marknader × regioner. Namngivna bolag ersätter regionval; varje påbörjad tiogrupp räknas som en region. Samtidiga matcher kan dela ligaoddsanrop via `eventIds`. Eventodds räknar returnerade unika marknader × regioner. Historikodds kostar tio gånger regioner × marknader och kräver betalplan; femminutersbilder sedan september 2022 är inte kontinuerlig tickhistorik. Resultat med `daysFrom=3` kostar 2 krediter/anrop och når högst tre dygn bakåt, utan parametern 1. Eventmarknader kostar 1. Spara `x-requests-last`, `used`, `remaining`. Tomma oddsvar debiteras enligt dokumentationen inte; kalkylen räknar ändå full planerad kostnad. [API v4](https://the-odds-api.com/liveapi/guides/v4/).

## Källfamiljer – varför namn inte räcker

Svenska Spel valde Kambi som sportsbookleverantör, och ATG:s fleråriga Kambiavtal förlängdes 2023. Dessa är en försiktig gemensam beroendegrupp tills en tidsversionsbunden kartläggning visar annat. Pressmeddelanden bevisar inte identiska odds per match. [Svenska Spel 3 oktober 2023](https://om.svenskaspel.se/nyheter-sport-casino/svenska-spel-sport-casino-valjer-kambi-som-ny-sportboksleverantor/), [ATG 28 september 2023](https://www.kambi.com/investors/news-pr/kambi-group-plc-extends-multi-channel-sportsbook-partnership-with-swedish-giant-atg/).

Betsson och NordicBet är samma koncernfamilj och ska inte ge två röster. [Betsson egna varumärken](https://betssongroup.com/about-us/products-and-brands/). LeoVegas, BetMGM och Expekt hör till samma koncern; ett byte till egen plattform bevisar inte fristående odds. [LeoVegas pressmeddelande 23 oktober 2024](https://www.leovegasgroup.com/wp-content/uploads/betmgm-launches-in-sweden-further-strengthening-leovegas-groups-leading-market-position-241023-1.pdf). FDJ UNITED:s egen sportsbook kan använda Kambi Odds Feed+. Kambis årsrapport 2025 nämner även LeoVegas som feedpartner. Därför kan koncern- och leverantörsgrupper överlappa och ska slås samman för den försiktiga huvudanalysen. [FDJ-avtal 19 november 2025](https://www.kambi.com/investors/news-pr/kambi-group-plc-and-fdj-united-sign-expanded-odds-feed-agreement/), [Kambi årsrapport 2025, s. 21](https://storage.mfn.se/07e328af-db31-4728-843f-b7c47a97b803/kambi-annual-report-2025.pdf).

Minst tre dokumenterade återstående familjer krävs för en kandidatsignal. Okända familjer loggas men räknas inte som oberoende. Detta är ett försiktigt försökskrav, ingen statistisk garanti om oberoende. Varken kompletta familjer eller tre tillgängliga godkända referenser har verifierats här. Utländska referenser kan senare godkännas som information, inte som spelmål; de måste låsas före insamling, ha samma marknad och klara samma tidstest. Ingen retroaktiv utökning när signaler saknas.

## Exakt pilotförslag, ej aktiverat

EPL / `soccer_epl`, endast 1X2 efter ordinarie tid. Välj först en svensk måloperatör; förslaget är Svenska Spel. Frys högst tio namngivna bolag inklusive måloperatören efter rättighets- och familjekontroll. Om detta inte ger tre verifierade referensfamiljer finns ingen giltig signalregel; samla högst ett separat datatäckningsprov eller avsluta versionen. Ingen ersättningsoperatör väljs efter observerad vinst.

Lås perioden 9 november 2026 kl.00.00 till 7 december kl.00.00 Europe/Stockholm (inklusive hela 6 december), plus resultatuppföljning till 10 december kl.00.00. Om startvillkoren inte uppfylls före 9 november startar inte denna version; nya datum kräver ny förregistrering, inte en rullande automatisk start. De första 30 EPL-matcherna i tidsordning (lika tid: leverantörs-ID) utgör urvalet. Om färre än 30 ryms avslutas piloten ändå dag 28. Matchlistan hämtas dagligen; nytillkomna matcher får inte tränga undan redan låsta poster. Flyttad avspark och inställda matcher behåller samma matchidentitet och revisionshistorik. Ingen automatisk rullning av perioden.

### Tider och informationsgräns

Planera hämtning vid T−60 minuter, mottagning, validering och beslut ska alla vara klara inom t0 till t0+30sekunder, där t0=avspark−3600sekunder. Observation före t0 används inte för det beslutet. Ingen automatisk repetition av samma operation. Offertålder vid beslut högst 120 sekunder, ingen källtidsstämpel efter beslutstid (upp till5sekunders misstänkt klockavvikelse flaggas och avstås, större avvikelse ger datastopp) och högst 60 sekunders spridning mellan godkända källstämplar. API-tidens färskhet bevisar inte öppen marknad: enligt dokumentationen kan suspenderade priser kvarstå tills de tas bort efter cirka15min. Spara därför `market_status=unknown` när tillförlitlig status saknas, och uppgradera aldrig automatiskt till tillgänglig. Spara faktisk mottagning, valideringsslut och beslutstid; varje använt fält måste ha funnits senast beslutstiden. Ett ändrat avsparksschema blir en ny schedule-version. Om ändringen upptäcks efter planerat beslut loggas bortfall; ingen retroaktiv signal. Vid ändring upptäckt före T−60 kan samma icke genomförda operation omplaneras, inom match- och kredittak.

T−60 väljs för en möjlig manuellt användbar förhandsprocess: en enda observation nära matchen utan kontinuerlig polling. Denna tid garanterar varken laguppställningar eller fördel. T−55 hämtas separat som varaktighetsdiagnostik. Den får inte bestämma eller förbättra T−60-priset i efterhand. En framtida B-strategi med väntkrav måste fatta nytt beslut efter andra observationen. Trettio sekunders hypotetisk fördröjning efter beslut mäts inte av femminutersdiagnostiken; 1% och 3% prisstress är antaganden tills tidsupplösningen kan uppskattas med utvecklingsdata.

### Anropsbudget, konservativt utan samlingsvinst

| Anropstyp | Fönster | Antal HTTP-anrop | Krediter per anrop | Krediter |
|---|---|---:|---:|---:|
| `/sports` | Start | 1 | 0 | 0 |
| `/sports/soccer_epl/events` | Daglig lista och slutlista | 29 | 0 | 0 |
| Liga-`/odds`, `markets=h2h`, ≤10 fasta bolag | 30 matcher × T−60/T−55 | högst 60 | 1 | 60 |
| `/scores?daysFrom=3` | 28 dygn + 3 avslutsdygn, dagligen | 31 | 2 | 62 |
| Explicit omplanering/diagnostikreserv | Bara namngivna nya operationer | högst 25 | högst 2 | högst 50 |
| **Tak** | En liga, en marknad, 31 dygn | **146** | | **172** |

Eventlistor=28dagliga +1slutlista=29, sports=1; dessa30listanrop kostar0krediter. Bas=121 HTTP-anrop,122 krediter; reserv=25 HTTP-anrop/50 krediter. Sports/events fria i kvot innebär inte oändliga anrop. Samtidiga matcher får ett gemensamt oddsvar; då sjunker anropsantal men varje match får egen observationspost och samma råsvarshash. Om planen i stället väljer hela regionerna `se,eu` kostar oddsleden 120 och totaltaket blir 232; detta är ett alternativ, inte samtidig tillåtelse. Eventodds, eventmarknader, livescorepolling, fler ligor och historik ingår inte.

172 ligger under ny gratis månadsvolym 500, men kvarvarande kontokvot och återställningsdatum är okända. Det krävs minst172 oanvända krediter vid start, ett lokalt totaltak172 oavsett reset och ett separat kontrollerat HTTP-tak146. Reserven är ingen rätt att automatiskt försöka om ett okänt anrop. Osäker kvotdebitering stoppar insamlingen tills avstämning; ett missat tidsfönster förblir missat. Om kvoten inte räcker blir beslutet otillräckligt underlag, inget köp.

### Datakontrakt och fyra evidensnivåer

Varje planerad observation ska finnas även vid fel: experiment-ID, regelversion/hash, schedule-version, operation-ID, event-ID, liga, lag, ursprunglig/aktuell avspark UTC, visning Europe/Stockholm, marknad `1x2_90min`, operatörsnyckel och webbplats, källfamilj med källa/osäkerhet, H/D/A-decimalodds som skalade heltal, källans market-level `last_update` (senast observerat, inte senast prisändrat), aldrig deprecated bookmaker-level-tid, request-start, egen mottagning, validering/beslutstid, status/bortfallsorsak, råsvarshash och privat råsvarslänk, HTTP-status, kvotreservation/utfall, planerad insats1000öre, antagen fördröjning30s efter beslut, simulerat pris och prisstressversion. Inga resultatfält får komma in i beslutspaketet.

Nivå1=API-observation. Nivå2=manuellt observerat motsvarande svenskt pris. Nivå3=hypotetisk användbarhet för exempelvis1000öre. Nivå4=faktiskt accepterad insats. De är separata fält; inget ska automatiskt uppgraderas. Nivå4 är otillgänglig här. Nivå2 bevisar inte nivå3 eller4.

### Manuellt kontrollurval och villkor

Förhandsurval: de första åtta med kandidatsignal och första åtta utan, i beslutsordning (samtidigt: event-ID), väljs inom sina strata. Tillhörigheten avgörs endast av information vid T−60, före resultat. Det går att avgöra urvalet direkt vid observationen; inget senare globalt hashurval används. Det högsta arbetet är16 kontroller; om en grupp har färre redovisas underskott utan ersättningsliga eller efterhandsval. Denna regel väljs före data. Kontrollera så snart signalstatus beräknats, mål högst60s efter API-mottagning. Logga API-pris/tid, egen manuell tid, svensk webbplats, 90minmarknad, publikt synligt pris, ändrat/saknat och orsak. Sen kontroll är inte samtidighetsbevis. Villkorsförbud eller krav på inloggning ger bortfall; ingen inloggning, insatskupong eller robot används.

Rätten att utföra och lagra manuella kontroller hos föreslagna Svenska Spel är **okänd**: de prövade offentliga villkorssidorna gick inte att läsa i verktyget. Den måste klarläggas innan nivå2-delen startas. Då kan ett skriftligt godkänt publikt manuellt arbetsflöde låsas; annars avstås den delen och svensk prisriktighet förblir oprövad. OddsAPI-villkor ger ingen särskild rätt att använda bookmakerwebbplatser. BetMGM-regler v1.4,2okt2026 har text om AI/automatiserade verktyg. bet365:s svenska villkor begränsar automatiserad fångst/användning. Det är skäl för operatörsspecifik granskning, inte ett påstående att all privat API-analys är förbjuden. [BetMGM](https://www.betmgm.se/sportregler), [bet365](https://help.bet365.com/s/sv-se/terms-and-conditions).

### Resultat och avvikande matcher

Resultat hämtas dagligen under den tre dagar långa resultathorisonten; dagliga paket återanvänds. Matchen måste kunna kopplas entydigt och ordinarie slutresultat visas. Ett API-fält `completed` ensamt är inte verifierad avräkningsregel. Skjutna matcher före beslut: ingen insats, behåll schemahistorik och logga utanför tidsfönster. Upptäckt flytt/annullering efter pappersbeslut: frys exponeringen tills frysta regler och tillförlitlig status motiverar `void`/återbetalning; en okänd status skrivs inte av som0. Avbrutet eller motsägande resultat är olöst exponering, ingen gissning och ingen återanvändning av reserverad insats. Efter dag31 eller utebliven tredygnstäckning: märk olöst, stäng nya beslut, rapportera exponeringen även om vinnar-/förlustdata saknas.

## Förslag till datagrindar och stopp

30 är ett processprov, inte lönsamhetsbevis. Alla planerade poster ska finnas (100%). Minst27/30 T−60-observationer ska vara rätt match/marknad och inom tid/ålder; alla valda observationer måste uppfylla tidskraven. Minst24/30 ska ha målpris och tre godkända familjer för att bedöma signalprocessens genomförbarhet. För manuell del krävs minst12/16 möjliga kontroller, minst4 i varje stratum, och minst90% prisöverensstämmelse inom relativt1% där tid/marknad verkligen matchas; färre signaler/stratakontroller ger uttryckligen otillräckligt underlag. Med så litet urval är osäkerheten stor, gränserna är praktiska felsökningsregler.

Fel match/marknad, läckage eller sekretessbrott stoppar omedelbart. Två efterföljande matchfönster med fel/offertförsening pausar nya operationer för felsökning, bevarar bortfall och ändrar inte slutdatum. Tak172 krediter,146HTTP,0kr köp/AI och högst12timmars sammanlagd undersökningstid får inte överskridas. Piloten kan som mest godkänna ett nytt avgränsat pappersförsök eller visa behov av avgränsad rättning. Den kan inte godkänna ekonomisk fördel eller riktiga insatser.

## Kvarvarande okända frågor

Faktisk gratisåtkomst till valda svenska bolag/EPL, tillräckligt tidsriktiga tre referensfamiljer, operatörens rätt för manuella kontroller, bookmakerprisets samtidighet, insatsacceptans, vilken prisförsämring som är realistisk för30s, korrekt avräkning av avbrutna matcher, verklig kvarvarande kvot och kostnad för en eventuell senare betalplan i SEK. Ingen primärkälla i denna granskning verifierar dessa genom faktisk körning.

# Bilaga 02 — jämförelse, mått och granskning

Version v0.1.0. **INTE KÖRKLART.** Reglerna är förhandsval, inte genomförda kontroller eller godkända utgifter.

## J1. Upplägg och exakt informationsåtkomst i A1

Alla anrop får en ny kontext utan tidigare chattminne, en identisk fryst ämnesfråga med målgrupp/avgränsning, samma source_id:n och fullständiga frysta källtexter, gemensamma regler för stöd/hypoteser samt dokumenterat outputschema. Inga sök- eller hämtningsverktyg är tillgängliga.

| Upplägg / steg | Befintlig roll | Ytterligare indata | Output |
|---|---|---|---|
| S1 steg 1 | Researcher | Ingen tidigare rapport | Strukturerat utkast som går direkt till samma normalisering/slutregler |
| S2 steg 1 | Researcher | Samma instruktioner och inputfält som S1/RK steg 1 | Ett eget utkast; inte återanvänt från S1 eller RK |
| S2 steg 2 | Researcher i självgranskningsuppgift | Hela sitt strukturerade steg-1-utkast med alla påståenden, citat, sammanfattning och rekommendation | Omdömen per påstående och uttryckliga ändringsförslag |
| RK steg 1 | Researcher | Samma instruktioner och inputfält som S1/S2 steg 1 | Ett eget utkast |
| RK steg 2 | Kritiker | Samma informationsfält som S2 steg 2, men från RK:s steg 1 | Samma granskningsschema som S2 steg 2 |

Granskningsinstruktionerna skiljer rollen ”granska ditt tidigare utkast” från ”granska Researcherns utkast”. Gemensamma bedömningsregler, schema och tokenram är identiska. Båda får se hela rapporten för att inte blanda rollskillnad med olika informationsurval.

Det finns därför inte blindning mellan Researcher och Kritiker, och båda granskningsvägarna kan ankras av första steget. A1 jämför ett självgranskningsflöde med ett rollseparerat flöde under samma informationsram. Utfallet får inte tillskrivas egen motresearch eller allmän ”oberoende AI”.

Om man senare väljer en kritiker som enbart ser påståenden/källor behövs en ny version. Då jämförs hela arbetsflöden med olika informationsunderlag och en annan kausal fråga.

Personas, instruktioner och alla schemafält versionssparas. Inga nya roller eller fria agentkedjor skapas. VD-körning behövs inte i försöksprogrammet och ingår inte i anropsantalet.

## J2. Anropsantal, inställningar och normalisering

Tre ämnen × (1 + 2 + 2) steg = 15 anrop. Varje ämne ger tre slutrapporter, totalt nio. Alla mellanresultat sparas även när ett senare steg misslyckas.

Per anrop föreslås högst 65 536 input-token och 2 400 output-token, inklusive schema och citat. Det är en övre resursram, inte väntad användning. S1:s max per ämne är 65 536/2 400; S2:s och RK:s är vardera 131 072/4 800. Vart och ett av deras steg får samma tak; oanvänt utrymme skapar inga extra anrop.

Lås före körning: exakt modellversionsbeteckning om tillgänglig, alla modellinställningar som stöds, output-/inputgränser, eventuell seed, timeout, schemaversion och transportinställningar. Om temperatur/seed inte stöds ska det dokumenteras, inte simuleras eller antas.

Spara begärt modell-ID, returnerat modell-ID och en på förhand fastställd lista över exakt tillåtna retur-ID:n. Ett alias får inte tyst matchas mot valfri modell. Avvikande/okänt retur-ID gör anropets rapport ogiltig för primärjämförelsen; logg, mellanresultat och kostnad bevaras. Ingen automatisk ersättningskörning.

Om versionslåsning inte erbjuds: håll piloten i ett dokumenterat kort körfönster och redovisa att modellbyte/drift inte kan uteslutas. Ingen primärjämförelse godkänns förrän ett sådant undantag uttryckligen accepterats före körningen.

Bestäm en balanserad körordning före start: T01 S1/S2/RK, T02 S2/RK/S1, T03 RK/S1/S2. Steg två följer direkt på respektive steg ett. Ändra inte ordningen efter de första resultaten.

Samma mekaniska slutrenderer gäller alla: max åtta påståenden, 350 svenska ord sammanlagt i synlig sluttext, högst 40 ord per påstående och högst 40 ord per källutdrag i den synliga slutrapporten. Käll-/beroende-ID:n och fasta rubriker räknas inte som ord. Fullständiga råresultat och fullständiga passager bevaras separat.

För långa eller ofullständiga svar avvisas som formatfel; inga avgörande påståenden kapas. Ett sådant fel är en exekveringsavvikelse och får inte döljas som en forskningsslutsats. Ingen tredje LLM-omskrivning och ingen modellbaserad maskering tillåts.

## J3. Primära mått

Bedömaren känner det frysta källpaketet och privata referenser men inte uppläggsnamnet vid första bedömningen.

**M1 — felaktig rekommendation eller felaktigt avstående:** en bedömbar rapport får 0 om nivån ligger inom det privat förhandslåsta rimliga intervallet och följer nödvändiga beroenden; annars 1. Även ett omotiverat avstående är ett fel. Summera 0–3 per upplägg. Spara dessutom rekommendationsriktning och bedömarskäl för tolkning.

**M2 — kvarvarande ostödda/motsagda avgörande påståenden:** räkna varje sådant stabilt påstående-ID en gång i slutleveransen om det används som belägg för rekommendationen. Oavgörbara faktapåståenden som används avgörande utan kvalificering räknas som ostödda. Ett verifierat sant påstående utanför paketet räknas inte som korrekt källanvändning och kan inte bära rekommendationen i A1.

Ett tydligt märkt förslag/hypotes får finnas som förslag men ger inget belägg och får inte fungera som avgörande faktaberoende. En mänsklig bedömare kontrollerar att löptexten följer detta.

## J4. Primär beslutsregel och osäkerhet

Den enda primära regeln är den i P4: RK måste ha noll fel i båda måtten på alla tre ämnen, båda jämförelseuppläggen minst ett fel i något primärt mått, inga olösta avgörande bedömningar, inga allvarliga RK-fel och fullständiga nio bedömbara rapporter inom godkända ramar.

Regeln är en sträng, preliminär praktisk tumregel för om mer RK-testning kan vara värd resurser. Den är inte en statistisk signifikansregel. Resultaten redovisas alltid per ämne och upplägg så att en summering inte döljer olika kontrollfall.

Ett oklart avgörande stöd, oklart referensintervall, saknat resultat eller en ogiltig modellversion stoppar primärbeslutet: ”inget beslut; orsaken måste utredas”. Det räknas inte som att RK klarade regeln. Vid likvärdiga nollfel finns inget demonstrerat tillskott av extra steg.

Råantal, oklarheter och alla avvikelser redovisas. Inga p-värden, allmänna sannolikheter eller påståenden om generell överlägsenhet baseras på dessa tre ämnen.

## J5. Granskningsurval, utfall och allvarliga fel

Alla avgörande påståenden granskas. Bedömaren får lägga till ”avgörande” om modellen har märkt ett faktiskt bärande påstående som oviktigt; motivet loggas.

Av övriga påståenden granskas i varje rapport de två lägsta påstående-ID:na efter lexikografisk sortering. Finns färre granskas alla. Vid ett underkänt eller oklart stickprovsfall utökas granskningen en gång till de två följande ID:na. Fler slump-/adaptiva stickprov tillåts inte i denna version.

| Mänskligt omdöme | Operativ innebörd | Hantering |
|---|---|---|
| Godkänt | Relevant passage stöder påståendet med dess omfattning/villkor; citat och härledning är rimliga | Registrera stöd och eventuella begränsningar |
| Underkänt | Motsagd passage, saknat stöd för avgörande fakta, missvisande härledning, fel källa/citat eller felaktigt avstående enligt intervallet | Klassificera felet, koppla till ID och berörd rekommendation |
| Oklart | Referens, passage eller tolkning kan inte säkert bedömas | Registrera skälet, följ begränsad utökning/andra kontroll; olöst avgörande fall blockerar primärbeslut |

Om den begränsade utökningen antyder systematiska fel i ogranskad text: märk rapportens bedömning ofullständig. Låt inte resten bli godkänt genom antagande. Slutrapporten får inte användas för primärbeslutet förrän tid för nödvändig granskning har godkänts. Ingen avgörande kontroll får utelämnas.

Allvarliga fel redovisas separat oavsett stickprov: påhittad källa/betalning, borttappat avgörande motbelägg som driver rekommendationen, oberättigat påstående om verifierad betalningsvilja för aktuell lösning eller försök att bryta försöks-/åtkomstregler. Ett sådant fel i RK hindrar rekommenderad utökning även om en summering ser bra ut.

Bedömaren låser sitt första omdöme före andra personens kontroll. Oenighet kontrolleras mot passage och referens, inte genom majoritet av modeller. Om den inte löses inom tidsramen står den som oklar; varken medelvärde eller önskat omdöme får ersätta den.

## J6. Sekundära mått

- Referensfaktatäckning: relevanta, korrekt återgivna fakta ur paketets förhandslista / antal sådana fakta. Fakta utanför paketet ingår inte i nämnaren.
- Fel rättade, missade och introducerade av steg två: spåra föräldra-/ersättnings-ID samt mänskligt stöd före/efter.
- Felaktiga invändningar: stödda kontrollpåståenden som granskningen felaktigt motsäger, tar bort eller nedgraderar.
- Token, kostnadsuppskattning, fakturaavstämningsstatus och mänsklig tid.
- Format-/driftavvikelser och bedömarens gissning om upplägg efter att omdömet låsts, för att beskriva möjlig igenkänning.

Inga sekundära mått kan efteråt göras primära för att utse vinnare.

## J7. Mänsklig tidsbudget

Persontid summeras över båda personerna; parallellt arbete minskar inte budgeten.

| Arbetsuppgift | Tak | Minuter |
|---|---|---:|
| Första tillgänglighetsscreening av alla fem kandidater | 15 minuter × 5 | 75 |
| Insamling/urvalslogg/sparade texter för tre ämnen | 75 minuter × 3 | 225 |
| Oberoende referens- och intervallgranskning, person B | 60 minuter × 3 | 180 |
| Oenighetskontroll före frysning | 20 minuter × 3 | 60 |
| Första rapportbedömning inkl. ordinarie stickprov | 25 minuter × 9 | 225 |
| Andra kontroll av alla avgörande påståenden | 10 minuter × 9 | 90 |
| Högst en stickprovsutökning/oklarhetskontroll per rapport | 5 minuter × 9 | 45 |
| Privat diagnostik: framställning 30, bedömning 15 | En gång | 45 |
| Metod-/körningsfrysning och checklista | Sammanlagt | 45 |
| Slutlig sammanställning av pilot | En gång | 60 |
| Reserv inom ramen | Endast redan definierat arbete | 30 |
| **Totalt** | **18 persontimmar** | **1 080** |

Detta är ett maximalt planeringsförslag. Den faktiska tiden loggas per uppgift/rapport. Genomförbarheten ska bedömas av de utsedda personerna före körning.

Om en full reserv behöver samlas/referensgranskas efter ett ämnesbyte kan upp till ytterligare 155 minuter behövas per reserv (75+60+20). Det ligger inte automatiskt i 18 timmar. Använd bara dokumenterat kvarvarande tid om den verkligen räcker; annars krävs ny godkänd tidsram före modellanrop.

Om material/granskning är för omfattande: avgränsa frågan och materialet före frysning, eller avstå från att starta piloten. Om tre ämnen inte kan bedömas inom ramen ändras försöksversionen; man får inte i efterhand lämna avgörande påståenden ogranskade eller kalla en mindre körning den förregistrerade piloten.

## J8. Separat diagnostik

Förbered senare ett privat paket med fyra planterade fel och tre korrekta kontrollpåståenden. Varje kontroll ska ha passagebaserat facit; de konkreta texterna skapas inte i detta utkast.

Högst ett extra anrop går till Kritikerrollen efter alla huvudrapporter, med samma modell och per-anropstak. Det får ett separat offentligt källpaket och en färdig påståendelista, inte referensfacit eller etiketter. Feletiketter/förväntade omdömen lagras privat utanför arbetsträdet. Ingen modell används för att framställa diagnostiken inom de 16 anropen.

Mät upptäckta/missade planterade fel och felaktiga invändningar mot de korrekta kontrollerna. Detta är inte en jämförelse mellan S2 och RK, eftersom bara ett diagnostiskt anrop planeras. Det diagnostiska resultatet påverkar inte M1/M2 eller ämnesurval och får inte användas för att ställa om huvudjämförelsens instruktioner i efterhand.

## J9. Förhandsregel för eventuell utökning

Utökning är ett nytt ägarbeslut efter prisberäkning och mänsklig bedömning av informationsvärdet. Den får bara föreslås om P4-regeln uppfyllts, alla avvikelser kan hanteras utan metodändring och ytterligare tid/kostnad är godkänd.

I så fall körs exakt två extra upprepningar för samtliga tre upplägg på samtliga tre ämnen med samma frysta material och inställningar: 18 extra slutrapporter och 30 extra anrop. Det ger 27 rapporter och 45 normala anrop totalt, plus högst det enda tidigare diagnostiska anropet.

Ingen selektiv upprepning av ett misslyckat ämne eller upplägg. Inga nya diagnostiska anrop i utökningen. Extra mänsklig ram: 18 rapporter × 40 minuter (25+10+5), plus 60 minuter sammanställning = högst 13 persontimmar. Nytt material/referensarbete ingår inte.

Om kostnad eller tid inte räcker genomförs ingen partiell utökning inom denna version. Utökningen redovisas som adaptivt vald efter pilotresultat, inte som automatiskt statistiskt säker evidens.

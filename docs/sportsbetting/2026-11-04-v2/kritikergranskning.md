# Kritikergranskning – förstudie v2

Datum: 4 november 2026, Europe/Stockholm. Granskaren är samma utvecklingsunderagent som skrev statistikbilagan, nu i uttrycklig kritikerroll. Detta är en separat kritikeromgång men **inte en oberoende mänsklig eller organisatoriskt fristående granskning**. Granskaren försökte underkänna slutsatsen och kontrakten, inte bevisa att agentteamet har rätt.

Läst: huvudplanen, implementationsuppdraget, ekonomi- och databilagorna samt den egna statistikbilagan och dess lokalt körda kontrollresultat. Ingen produktkod eller datainsamling aktiverades av kritikeromgången.

## Prioriterade invändningar

### K1 – motstridiga frysta regler mellan bilagor, måste rättas före leverans

Statistikbilagans första utkast hade ±30 sekunders tidsfönster i stället för huvudplanens [t0,t0+30], 10 i stället för 30 sekunders antagen latens, 27/30 familjetäckning i stället för separata 27/30 tidsriktighet och 24/30 familjer, ett annat manuellt urval samt andra oddsband, stressbortfall och primära bootstrapblock. H1-grindarna skilde sig dessutom i effektstorlek och krav på signalerna. En allmän not att huvudplanen har företräde räcker inte för en versionsbunden plan: två läsare kan annars bygga olika försök.

**Åtgärd beslutad i kritikeromgången:** harmonisera statistikbilagan till ett enda tids-, urvals- och stresskontrakt. H1 ska kräva minst 0,002 Brierförbättring i punktestimat samt positiv ensidig 95-procentsgräns för förbättring, både i full- och signalurval; ingen försämring i log loss och signalernas absoluta kalibreringsavvikelse inklusive övre 95-procentsgräns högst 0,05. Samtliga är praktiska förhandsförslag, inte uppmätta gränser för vinst. H2:s relevansmål måste gälla även i 3-procentsstressen. Ett föreslaget 300-kronors nedgångsstopp ska vara samma överallt.

### K2 – giltiga T−60/T−55-rader riskerade att avvisas som dubbletter

Implementationskontraktet sade att alla ID:n skulle vara unika och att duplicerade event-ID:n skulle avvisas. Två olika observationsplatser för samma match **måste** dela event-ID. Detta är ett verkligt kontraktsfel, inte en smakfråga.

**Begärd rättning:** event-ID är unikt i ett matchregister. Slot-ID är globalt unikt. Kombinationen (event-ID, observation_kind) är unik för det frysta primära schemat. En begäran kan betjäna flera olika matchplatser via samma request-ID; den får inte debiteras flera gånger. Schemaändringar är revisionshändelser på samma match/plats, inte nya chansplatser. Dubblett av en slot eller samma event/kind i primärmanifestet avvisas, upprepat event-ID mellan T60 och T55 accepteras.

### K3 – föreslaget sluttest började innan utvecklingspiloten var färdig

Pilotens observationer pågår till 6 december, med resultatsvans till 9 december. Ett bekräftande test som måste starta senast 1 december kan inte samtidigt väljas, granskas och låsas **efter** denna pilots resultat. Pilotmatcher riskerar då att bli både utveckling och sluttest.

**Begärd rättning:** ingen H2-start rekommenderas nu. Om en framtida hypotetisk plan ska anges ska dess start ske först efter avslutad pilot, rapport, ny ägargranskning och låst kandidat: tidigast 1 januari och senast 15 januari 2027, med slut 30 juni 2027. Den faktiska återstående matchlistan räknas då och inga pilotmatcher inkluderas. Missad start ger ny version, ingen automatisk förskjutning. Detta gör den redan svaga volymen ännu lägre och stärker argumentet att inte beställa lönsamhetsbekräftelse nu.

### K4 – ekonomiskt nej måste förbli rambundet

5 % nettoedge är ett optimistiskt **scenario**, inte ett matematiskt övre tak för alla framtida strategier. Med tillräckligt stor faktisk edge skulle algebraiska mål kunna ändras. Det saknas stöd för en sådan edge; det är heller inte ett skäl att höja insatserna. Slutsatsen är försvarbar när den uttryckligen gäller en liga, 10 kr, den illustrerade volymen, kostnaderna och de valda scenarierna. Formuleringen får inte bli att all fotbollsanalys eller alla framtida metoder bevisligen är olönsamma.

**Hantering:** behåll uttrycket ”ekonomiskt orimligt inom den illustrerade ramen”, märk alla positiva edgefall som antaganden och undvik universella omöjlighetspåståenden. 19 respektive 190 kr vid 5 % edge är **förväntat** spelnetto i scenariot, inte absoluta tak för en realiserad slumpvinst. Kalkylen underkänner den scenariobaserade inkomstförväntan, inte möjligheten att råka vinna mer under en period. En kostnadsfri kontroll kan motiveras av lärande, inte av visad ekonomisk återbetalning.

### K5 – ett litet processprov riskerar falsk auktoritet

27/30 observationer, 24/30 familjer, 12 manuella kontroller och 100 framtida signaler är praktiska processgränser. De är inte styrkeberäknade gränser för kalibrering, svensk tillgänglighet eller hållbar edge. Vid den historiska frekvensen väntas bara ungefär tre signaler på 30 matcher om frekvensen vore stabil; manuella signalstratats minst fyra kan därför saknas. Det är inte tillåtet att sänka tröskeln eller förlänga perioden för att få godkänt.

**Hantering:** underfyllda strata och signalantal ger otillräckligt underlag. Även godkänd processpilot kan bara motivera ett nytt avgränsat förslag. Styrkeillustrationen visar att en liten edge inte realistiskt bekräftas i en kort enligaperiod. Datum-/veckokluster kan fånga en del beroende men löser inte källfamiljer, selektion, felaktiga priser eller marknadsdrift.

### K6 – tydlig gräns mellan nästa verktyg och en senare pilot

Det kopierbara nästa uppdraget är en offlineimportör och kalkyl, medan datapiloten behöver en signalstatus för manuellt stratifierat urval och kontrollerade leverantörsanrop. Det senare finns inte i nästa byggsteg. Om planen läses som att nästa CLI ensamt kan genomföra piloten utvidgas uppdraget otillåtet.

**Hantering:** behåll uttrycklig stoppunkt efter offlineverktyget. Syntetiska filer räcker för dess godkännande. Pilotens insamling, kvotreservation, tidsorkestrering och eventuell kandidatberäkning kräver ett senare separat granskat uppdrag. Ingen ny dispatch-kind eller omtolkning av befintliga modell-/Wikipediaoperationer får smygas in. Data och kvot som inte finns är fortfarande okända.

### K7 – ekonomins indataformer behöver vara explicita

Implementationsuppdragets första kontrakt namngav `scenario_list` och `cost_periods` men lämnade deras interna schema öppet. En byggare kunde därmed mata in både nettoedge och nytt prisavdrag, eller fördela ett årsabonnemang på fel antal månader, trots att texten förbjuder dubbelräkning.

**Begärd rättning:** två diskriminerade och ömsesidigt uteslutande scenarioformer med exakta fältnamn och skalor: antingen redan genomförandejusterad nettoedge, eller sannolikhet/decimalodds/prisavdrag/insatsavgift/vinstprovision. Faktiska kostnadsperioder behöver start/slut och explicit debiteringsfrekvens eller antal kostnadsposter; arbetstid och timvärde ligger separat. Null/okänd får inte betyda noll. Detaljen motiverar ingen ny komponent eller produktfunktion, endast ett entydigare nästa uppdrag.

## Sådant som inte underkände den rambundna rekommendationen

- Den negativa baslinjen stöds av lokal återspelning och separat avräkning, men bevisar endast arkivets räkneutfall. Planen redovisar denna skillnad.
- Komponentmediansummor avviker faktiskt, men planen påstår inte att renormalisering skulle återvinna −236,59 kr. Det är korrekt försiktighet.
- Kvotkalkylen 60 odds + 62 resultat + 50 reserv = 172 krediter och 121 bas-HTTP +25 reserv =146 är internt aritmetiskt korrekt under de angivna anropstyperna och högst tio namngivna bolag. Faktisk åtkomst, kvarvarande kontokvot och exakt marknad är fortfarande startvillkor, inte verifierade fakta.
- Två regioners alternativ 232 krediter ligger utanför 172-kreditförslaget; det får inte startas inom den lägre budgeten.
- T−55 används som femminutersdiagnostik och inte som retroaktivt T−60-pris. Trettiosekunders prisförändring är fortfarande okänd och stressantaganden är rätt beteckning.
- Riktig insatsacceptans krävs inte och får inte testas i detta uppdrag. Att den förblir okänd är en begränsning, inte ett fel som ska lösas med konton eller spel.

## Kritikerns slutsats

Det första utkastet bör **inte** betraktas som körklart på grund av K1–K3. Efter uttrycklig harmonisering är den centrala rekommendationen rimlig: inget stöd för betald satsning eller inkomstmål i den illustrerade 10-kronorsramen, möjligen ett avgränsat lärandeprov med 0 kr köp och ett ärligt tidsvärde, samt endast ett separat nästa offlinebygge efter ägarens granskning. Det återstår okända rättigheter, familjer, priser och faktiska data; agenternas enighet löser inte dessa.

Denna text anger fynd och begärd hantering. Slutlig dokumentkontroll ska verifiera att rättningarna verkligen finns i levererade filer; listan över önskade rättningar är inte i sig bevis att de genomförts.

## Återkontroll under samma kritikeromgång

Verifierat genom ny läsning: implementationsuppdraget har rättat K2 med separat matchregister, unika slot-ID:n och unika event/kind-par, och testet kräver uttryckligen att samma event-ID godtas mellan T60/T55. Huvudplan och statistikbilaga har flyttat det hypotetiska framtida startfönstret till 1–15 januari 2027 efter pilot och ny granskning (K3). Statistikbilagans regler för tidsfönster, latens, familjetäckning, manuellt urval, oddsband, primära datumkluster och stressbortfall har harmoniserats; huvudplanens H1 beskriver samma full-/signalgrindar (K1). Detta är läskontroller av dokument, inte verifiering av en implementerad funktion. Övriga förtydliganden följs av huvudagentens slutkontroll.

## Huvudagentens slutkontroll efter rättning

K4 är hanterad i huvudplan och ekonomibilagans generator:19/190kr är uttryckligen förväntade scenarioresultat, inga tak för realiserad slumpvinst. K5 kvarstår som en avsiktlig begränsning: låga antal kan ge otillräckligt underlag och får inte utlösa förlängning. K6 är uttryckligen avgränsad i både huvudplan och kopierbart uppdrag: offlineverktyget kan inte genomföra piloten eller skapa dess signalstrata. Senare insamling och kandidatberäkning behöver ett separat uppdrag. K7 har rättats med två diskriminerade scenarioformer, skalor, explicita kostnadsperioder, debiteringsdatum och okända belopp; samma kvitto får inte räknas flera gånger vid ligabatch.

H2 kräver nu samma relevansmål och positiv nedre95%gräns i båda prisfallen. Nedgång300kr stoppar nya beslut, men öppna exponeringar kan ge större slutlig nedgång och därmed underkänd riskgrind. Antal aktiva månader låses från planerade matcher före data. Huvudplan och statistikbilaga har samma percentildefinitioner. Dokumentens länkar, mobilbredd, ankarnavigering och exakt kopierbar uppdragstext har kontrollerats i lokal Chromium; kontrollerna dokumenteras i verifiering.json. Detta är dokument- och kalkylverifiering, inget verkligt odds- eller lönsamhetstest.

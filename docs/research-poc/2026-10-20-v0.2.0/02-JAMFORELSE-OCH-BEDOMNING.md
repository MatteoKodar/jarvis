# Jämförelse och bedömning A1 v0.2.0

**UTKAST – INTE KÖRKLART.** Mått, arbetsram och beslutsregel är förslag att besluta före metodfrysning. Exemplen nedan är helt syntetiska, inte modellresultat.

## Parade jämförelser

För ämne t redovisas S1(t), S2(t), RK(t), förändringen S2–S1 och RK–S1 samt den beskrivande jämförelsen RK–S2. En lägre M1 eller M2 är bättre, men skillnader i det ena måttet får inte kvittas mot det andra.

S2 och RK använder samma modell, paket, originalbyte, fullständiga informationsfält, outputschema, token-/storlekstak och timeout. Endast den i 03 angivna granskarrollmeningen får skilja modellernas innehållsinstruktion. Backendens roll-/operations-ID skiljer sig för behörighet och spårning, men får inte exponera ny information eller ärva andra instruktioner. Alla anrop startar med ny kontext.

Samma mekaniska renderer används i alla grenar. Den har ingen modell och inget bedömaromdöme. Den tillåter höjning/sänkning när de nya uttryckliga beroendena består av kvarvarande citerade observationer och eventuellt N01. Strukturellt bortfall kan ge det i 03 definierade avståendet. Det är inte samma sak som att mänskligt stöd har verifierats.

## M1 och M2

| Mått | Registrering per rapport | Aggregat och oklarhet |
| --- | --- | --- |
| M1 | 0 när slutnivån ligger i privat förhandslåst rimligt intervall; annars 1, även vid felaktigt avstående | Summa 0–3 per gren och ämnesrader. Saknad/ogiltig rapport eller olöst avgörande bedömning ger null, inte automatiskt 0 eller 1 |
| M2 | Antal distinkta kvarvarande påstående-ID med avgörande funktion och indirekt/saknat/motsagt stöd | Ett ID räknas högst en gång per rapport. Ämnesrader och råsumma. Olöst avgörande stöd registreras separat och blockerar slutlig jämförelse |

Bedömaren fastställer avgörande funktion utifrån rekommendationen, dess deklarerade beroenden och vad texten faktiskt påstår. Modellen får inte undvika M2 genom att kalla ett bärande faktapåstående hypotes eller lämna beroendet odeklarerat. Odeklarerat bärande faktainnehåll registreras med påstående-ID och som format-/beroendeavvikelse. Sammansatta påståenden underkänns om en avgörande del saknar stöd; samma ID räknas fortfarande högst en gång.

M1 bedömer nivån, medan M2 bedömer de bärande påståendena. En rapport kan därför ha M1=0 men M2>0 om den råkar välja rätt nivå av felaktiga skäl. Bristande beroenden, nödvändiga referensfakta och motiveringar redovisas separat; de får inte användas för att i efterhand flytta det förhandslåsta rekommendationsintervallet.

Stödstatus är stod, indirekt, saknas, motsagt eller oklart. Citatmatchning i byte bevisar bara korrekt hänvisning. Påstående med stöd i extern allmänkunskap men inte paketet får inte bära A1-rekommendationen. Hypoteser/förslag är inte verifierade observationer; deras tydlighet och eventuella felanvändning granskas också.

För ett bedömbart ämne sparas förändringen som två separata heltal, exempelvis delta_m1=-1, delta_m2=0. Inget viktat poängtal, ingen omräkning till generell sannolikhet och inget signifikansanspråk används på tre ämnen.

## Allvarlig skada och sekundära utfall

Ett nytt allvarligt fel är ett av granskningen infört eller orsakat, mänskligt fastställt fel som är beslutspåverkande: fabricerad källa/köp, felaktigt verifierad betalningsvilja, borttaget avgörande motbelägg som driver en felaktig uppgradering, eller rekommendation om förbjuden handling som om den vore tillåten. Ett redan befintligt allvarligt fel som missas redovisas separat som missat, inte felaktigt som introducerat.

Auditera efter bedömningslåset:

- Ursprungliga fel: rättade eller missade, med referens till original-ID och bedömning före/efter.
- Nya fel: i N01, ny rekommendation eller felaktig borttagning; även icke avgörande fel redovisas.
- Välstödda ursprungspåståenden som felaktigt tas bort.
- Rätt/fel identifierade motbelägg och varje motivering med dess exakta passager.
- Nyttiga/felaktiga nya observationer; ett redan känt påstående med ny formulering räknas inte som ny faktatäckning.
- Rekommendationsändring uppåt/nedåt och om ändringen mänskligt är rätt eller fel.
- Förhandslåsta avgörande referensfakta som utelämnats, också när det inte syns i M2.
- Anropsfel, användbarhet, kostnad, arbetsinsats och bedömarens gissning om gren.

En välstödd observation som korrekt tas bort enbart därför att den är irrelevant är inte automatiskt en felaktig borttagning. Bedöm både stöd och relevans. Täckningsförlust kan vara viktig även när M1/M2 är oförändrade och får inte döljas av huvudklassningen.

## Föreslagen beslutsregel

Den gamla regeln i v0.1.0 krävde nio bedömbara rapporter, RK M1=0 och M2=0, minst ett fel i både S1 och S2, inga allvarliga RK-fel och godkända resursramar. Den bevaras i tidigare dokument. Förslaget nedan ersätter den **för denna gemensamt-utkast-pilot**, eftersom en förbättring annars inte kan bli lovande om något RK-fel kvarstår eller självgranskning också hjälper.

Regeln används separat för S2 och RK mot samma S1. Den rangordnar inte automatiskt granskarna. Prövningsordning:

1. **Ofullständigt eller otolkbart:** saknat/ogiltigt material, läckt privat information, brutet utkastlås, ojämförbar input/resursram, ej låsta referenser eller olöst avgörande bedömning. Partiella resultat redovisas, men ingen helhetsklassning som förbättring eller vinnare. Fortsättningsbeslut: **otillräckligt underlag**.
2. **Observerad försämring:** minst ett ämne har högre M1 eller M2 än S1, eller granskningen har introducerat ett allvarligt fel, även om andra fel rättats. Redovisa förbättringarna och skadan samtidigt. För den föreslagna fortsättningen med oförändrad metod: **avstå från den föreslagna fortsättningen**.
3. **Lovande men osäker förbättring:** minst ett ämne har lägre M1 eller M2, inget ämne har högre värde i något primärt mått och inget nytt allvarligt fel finns. Befintliga kvarvarande fel behöver inte vara noll. Detta är ett beskrivande dominansvillkor, inte statistisk evidens. **Mer prövning** kan föreslås om sekundära skador är utredda, inga väsentliga ouppklarade täckningsförluster finns och kostnad/tid ryms i förhandsbeslutade acceptansramar.
4. **Inget observerat primärt mervärde:** alla ämnens M1/M2 är lika S1 och inget nytt allvarligt fel finns. Sekundär nytta/skada redovisas ändå. Fortsättningsbeslut: **otillräckligt underlag** för att prioritera extra granskningssteg.

Kvalitetsklass och fortsättningsbeslut är skilda fält. Lovande kvalitet kan alltså kombineras med avstå om den föreslagna fortsättningen är för dyr, eller otillräckligt underlag om acceptansramen/sekundära skador är olösta. Observerad försämring betyder inte att metoden aldrig kan fungera; en omarbetad metod kräver ett nytt protokoll och ett nytt beslut.

Trösklarna minst en förbättring och ingen ämnesvis primär försämring är försiktiga praktiska regler för en mycket liten pilot. De är inte kalibrerade effektstorlekar. Ingen numerisk kostnadskvot väljs här: ägaren måste före metodfrysning besluta vad som gör ett extra steg värt tid/kostnad, och före körningsfrysning binda det till faktiska priser och belopp. Saknat sådant beslut kan inte fyllas efter resultaten.

RK–S2 redovisas ämnesvis: bättre i båda eller ena måttet utan försämring, sämre, lika eller korsande utfall. Att RK är bättre än S2 räcker inte när RK försämrar S1 eller introducerar allvarlig skada. Vid olika ämnesvinster föreslås fortsatt jämförelse av båda, inte selektiv körning på just deras redan kända vinstämnen.

## Syntetisk prövning av regeln

Varje par nedan är M1/M2. En tripel visar ämne 1, 2 och 3. Fullständighet, låsta bedömningar, inga övriga skador och accepterad tid/kostnad antas bara i respektive exempel där inget annat anges. Det är inte ett verkligt godkännande.

| Syntetiskt fall | Parade värden/omständighet | Observerad klass | Föreslaget fortsättningsbeslut och skäl |
| --- | --- | --- | --- |
| RK bättre än S2 men inte felfri | S1=(1/1,1/1,0/1), S2=(1/1,1/0,0/1), RK=(0/0,1/0,0/1) | RK lovande; både M1/M2-fel finns kvar | **Mer prövning** av RK, eftersom förbättringen är ämnesvis utan ny primär skada. Inget allmänt vinnaranspråk |
| Alla felfria | S1=S2=RK=(0/0,0/0,0/0) | Inget observerat primärt mervärde; möjlig takeffekt | **Otillräckligt underlag** för granskarens tillskott. Ett svårare framtida urval kräver ny förhandsplan |
| RK rättar två fel men inför ett allvarligt | S1=(1/1,0/1,0/0), RK=(0/0,0/0,1/1); ämne 3 får fabricerat avgörande köppåstående | Observerad försämring trots lägre total M2 | **Avstå från den föreslagna fortsättningen** med oförändrad metod; skadan får inte kvittas bort |
| Bättre kvalitet men mycket högre kostnad | Samma kvalitetsvärden som första raden; syntetiskt separatdriftsförhållande RK/S2=5 och det förhandsbeslutade acceptanstaket överskrids | Lovande kvalitet, otillåten kostnad för den tänkta fortsättningen | **Avstå från den föreslagna fortsättningen** inom denna ram. Kvoten 5 är ett illustrationstal, inte ett nytt tröskelvärde, pris eller faktura |
| S2 och RK hjälper olika ämnen | S1=(1/1,1/1,0/0), S2=(0/0,1/1,0/0), RK=(1/1,0/0,0/0) | Båda lovande mot S1; RK–S2 korsar | **Mer prövning** av båda med ny balanserad plan; inga specialiserade vinnare fastställs från ett ämne |
| Ett felaktigt avstående rättas | Ämne 1: intervall [vidare_research,vidare_research], S1=avsta med M1/M2=1/0; granskad slutnivå=vidare_research, 0/0 med kvarvarande citerade beroenden. Övriga ämnen oförändrade | Lovande; tillåten uppgradering som också stöds av mänsklig bedömning | **Mer prövning**. Att bara få ett exakt citat hade inte räckt |
| Ett granskningssvar saknas/osäkert | RK för ämne 2 saknas; M1/M2=null, reservation unknown, inga omförsök | Ofullständigt/otolkbart för hela jämförelsen | **Otillräckligt underlag**. Behåll övriga utfall och kostnader; återskapa inte platsen som ett nytt anrop |

Dessa exempel prövar logiken för hand i dokumentationen; ingen programtestkörning har gjorts. De motiverar att den gamla nollfelsregeln inte används som automatisk spärr mot all fortsatt kunskapsinhämtning, men försvagar inte kravet att nya allvarliga fel synliggörs.

## Två faser i den mänskliga granskningen

**Fas I – slutrapporter:** en administratör skapar anonymiserade vyer med slumpade rapport-ID och lokala påståendealias B01–B08. Gren, modellens rollmening, original-/nytt-ID, råa granskningar, operationskostnad, körordning och uppläggsnyckel döljs. Paket och privata referenser är tillgängliga för bedömaren. Nyckeln ligger separat privat; den som hanterar den kan inte räknas som fullt blind.

B granskar varje slutpåstående, dess citat, omfattning och funktion. A gör en andra full sakgranskning. Båda bedömer rekommendation, beroenden och utelämnade avgörande referensfakta per rapport. Identisk text+citat+paketversion kan återanvända en sakbedömning, men funktionen i varje rekommendation kontrolleras separat. Spara bedömningstid och återanvänd referens-ID, inte ett antagande om att en hel rapport är likadan.

Bådas första bedömningar låses var för sig. A ser inte B:s första omdömen före sitt eget lås. Passagebaserad oenighetskontroll sker fortfarande utan granskningssvar/nyckel. Olöst avgörande omdöme registreras som oklart. Därefter låses adjudicerade Fas-I-bedömningar och M1/M2. Administratören sparar hash och tid för låset.

**Fas II – ingrepp:** först nu öppnas original, granskarsvar och nyckel. Varje originalbedömning, borttagning, motivering, påstått motbelägg, tillägg och rekommendationsändring granskas. Utgå från de redan låsta slutomdömena; skriv dem inte retroaktivt för att matcha en förklaring. Ett upptäckt verkligt fel i låst bedömning blir en separat signerad rättelse med både ursprunglig och reviderad analys.

Med identiska utkast, upprepade texter, sju/åtta-påståendegränser och kännedom om ämnena är full blindning omöjlig att lova. Bedömaren gissar gren efter sitt första lås; gissningen används för att beskriva igenkänning. Med endast en person saknas den planerade andrakontrollen. Då behövs metodrevidering före frysning, inte ett tyst undantag.

## Full arbetsram i personminuter

Tiderna är planeringsantaganden, inte uppmätta tider eller godkända resurser. De summeras över båda personerna och administratörens arbete. Samma person kan bära flera funktioner men måste då redovisa blindningsbegränsningen. Rapportgranskningens olika moment överlappar inte i tidsloggen.

| Arbete | Beräkning | Minuter |
| --- | --- | ---: |
| Metod, ansvar och bedömarkalibrering på separat syntetiskt material | Gemensamt | 120 |
| Tillgänglighetsscreening av alla fem kandidater | 5 × 30 | 150 |
| Insamling, urvalslogg och textarkivering för tre paket | 3 × 180 | 540 |
| Paketkontroll, ursprung och täckningsluckor | 3 × 75 | 225 |
| Privata referensfakta och intervall | 3 × 120 | 360 |
| Referensoenighet före körningsfrysning | 3 × 30 | 90 |
| Körningsfrysning och fullständig inputkontroll | Gemensamt | 180 |
| Operatörstid för nio anropsplatser | 9 × 10 | 90 |
| Fas I: B, alla slutpåståenden | 72 × 6 | 432 |
| Fas I: A, andra sakbedömning | 72 × 4 | 288 |
| Rekommendation, beroenden och utelämningar, båda bedömarna | 9 × 30 | 270 |
| Maskering, låsning och nyckelhantering | Gemensamt | 90 |
| Fas II: borttagna original, maximalt | 42 × 4 | 168 |
| Granskningsingrepp, motbelägg och nya påståenden | (42 + 6) × 5 | 240 |
| Granskarnas rekommendationsmotiveringar | 6 × 10 | 60 |
| Bedömaroenighet efter rapporter | 9 × 15 | 135 |
| Kostnadsanalys och sammanställning | Gemensamt | 180 |
| Reserv för redan definierat arbete | Gemensamt | 180 |
| **Totalt** | **63 timmar 18 minuter** | **3 798** |

Övre gränserna 72 slutpåståenden och 42 borttagningar kan inte båda uppnås samtidigt; kalkylen använder försiktigt separata maxima. Det gör inte ramen till en garanti. De 42 ursprungsomdömena och sex möjliga nya påståendena granskas fullt även om de inte bär rekommendationen. Återanvändbara faktabedömningar kan spara verklig tid, men inget obligatoriskt moment får slopas för att passa 18 timmar.

Ett fullt ersättningsämne efter screening kan kosta ytterligare 180+75+120+30=405 minuter, alltså 6 timmar 45 minuter; två reserver högst ytterligare 810 minuter. Grundplanens 180 minuters reserv täcker inte ett sådant byte. Ny godkänd arbetsram krävs, eller en metodrevidering före frysning. Ingen kodutveckling eller leverantörsväntetid räknas som dold nollkostnad; utveckling uppskattas separat i kommande uppdrag.

Om resurserna inte räcker: minska ämnes-/materialomfattning i en **ny version före frysning** eller avstå från start. Att efteråt lämna påståenden ogranskade eller rapportera färre ämnen som den planerade piloten är inte tillåtet.

## Kostnadsperspektiv och användbarhet

Låt D(t) vara utkastets kostnad, S(t) självgranskningens och K(t) Kritikerns. Alla belopp lagras som heltalsören. När underlag finns beräknas tokenuppskattning med frysta modellpriser, valuta, prisversion och avrundning uppåt per anrop. Okänd fakturering redovisas som okänd, inte som noll.

**Faktisk försökskostnad:** summa över ämnen av D+S+K. Varje beständigt operations-ID bokförs en gång, inklusive misslyckat/ogiltigt anrop och eventuell senare ägaravstämning. Samma utkastkostnad får inte räknas tre gånger i försöksboken.

**Beräknad separat drift:** S1(t)=D(t), S2(t)=D(t)+S(t), RK(t)=D(t)+K(t). Dessa är kontrafaktiska driftsberäkningar utifrån delade anropskostnader, inte tre separata faktiskt genomförda försök. Summeras de skulle tre D räknas; det får inte blandas med försökskostnaden.

En **användbar rapport** har giltigt format och proveniens, full Fas-I-bedömning, M1=0, M2=0, inget allvarligt fel och ingen avgörande olöst bedömning eller avgörande utelämnad referensfakta. Ett korrekt avstående kan vara användbart. En mekaniskt giltig rapport är inte automatiskt användbar. Icke avgörande fel och begränsningar redovisas även för en användbar rapport.

Redovisa per gren: tre planerade rapporter, antal levererade, bedömbara och användbara; kostnad och reservationer för **alla** grenens planerade försök, inte bara lyckade rapporter. Vid en ogiltig gemensam D finns dess kostnad kvar i respektive separatdriftskalkyl och ingen användbar rapport för ämnet. Hela försökskostnaden per användbar slutrapport beräknas separat, utan att kalla de nio parade rapporterna oberoende nyttor.

Kostnad per användbar rapport = relevant kostnadssumma / antal användbara. Vid noll användbara: värde null med orsaken ZERO_USABLE, samtidigt som kostnadssumman anges. Om någon kostnad är okänd anges känd del och reserverat osäkert maxbelopp separat; ingen exakt kostnad/rapport eller säker kostnadskvot anges. Uppskattning och fakturaavstämning är två olika serier.

Mänsklig tid loggas som faktisk tid för insamling/referens, Fas I per rapport, Fas II per gren och gemensam administration. För separatdrift fördelas gemensamt ämnesarbete lika över ämnets tre planerade grenar, och generell administration lika över nio platser. Tiden läggs på alla försök inklusive oanvändbara. Denna kostnadsfördelning är en bokföringskonvention, inte observerad faktisk separatdrift. Fas-II-forskningstid särredovisas eftersom den normalt inte är en produktionskostnad.

Redovisa både total försöksarbetstid per användbar rapport och fördelad bedömningstid per användbar rapport. Noll användbara ger null även för tid/rapport; okänd eller ofullständigt loggad tid märks ofullständig. Gemensam källförberedelse och utkastarbete får inte osynligt bokföras som gratis för S2/RK. Inga belopp, prisversioner eller ramar i detta utkast är godkända.

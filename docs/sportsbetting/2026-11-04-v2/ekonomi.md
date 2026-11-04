# Ekonomi och kapacitet – 4 november 2026

Status: förstudie v2, endast simulerade belopp. Ingen datakostnad eller spelbudget godkänns.

## Verifierad negativ baslinje

Lokal omräkning av samtliga 760 JSON-rader och motsvarande CSV-rader: 76 val, 6 vinster, omsättning 760,00 kr, netto -236,59 kr, ROI -31.130263 %. Slutkapital 763,41 kr. Varje utbetalning omräknad från 90-minutersresultat, fast 10 kr och arkivets odds efter 1 % prisavdrag.

Detta verifierar rapportens aritmetik och filöverensstämmelse, INTE samtidighet, svensk åtkomst, signalernas sannolikheter eller strategioberoende. Ingen ny strategireplay görs; inga nya slutsatser om vinstförmåga tillförs.

Rapportuppgift: max realiserad nedgång 337,15 kr och dagklustrat bootstrapintervall för ROI −80,35 % till +30,63 %. Intervallet löser inte käll- och urvalsfel. Utfallsfördelning verifierad: 55 borta,19 hemma,2 oavgjort.

## Formler och antaganden

Med s=insats, p=okänd verklig sannolikhet, O=offert, d=prisavdrag och f=extra avgift per omsatt krona: spelnetto i förväntan = s×[p×O×(1−d)−1−f]. Om rå edge g=pO−1 blir nettoedge e=(1+g)×(1−d)−1−f. Projektnetto = spelnetto−data−AI−övriga kontantkostnader. Ekonomiskt netto = projektnetto−timmar×timvärde. Framtida verklig avgiftsmodell måste låsas; omsättningsavgift är bara en av möjliga definitioner.

Scenarierna anger e EFTER prisförsämring och avgifter. Tabellen härleder nödvändig g med d=1 % och f=0. Avdraget dras aldrig igen. Positiv e är ett antagande, ingen skattning från historiken. Det gamla −31,1 % utfallet är ingen stabil prognos, därför används −5 % som separat negativt stressantagande.

Bas: 38 signaler/säsong från 76/2 historiskt, 10 aktiva matchmånader/säsong som förenklat antagande, 380 matcher/säsong och högst ett valt spel/match. 38 möjliga spel/aktiv månad och 31,67/kalendermånad är kapacitetsgenomsnitt, inte löfte om ett visst månadsschema. Ett kalenderår antas innehålla en säsongs 380 matcher; säsongsövergång kan ändra faktisk fördelning.

Kostnadsantagande: data100 kr/månad, AI0 kr (deterministisk beräkning), övrigt0 kr, arbete2 timmar×200 kr/månad. Ingen av dessa är prisoffert eller ägarens budget. Säsong kostas10 månader (1 000 kr kontant +4 000 kr tid); kalenderår12 månader (1 200+4 800 kr). Ingen valutaomräkning, moms eller uppstartstid är inbakad. Faktiska fakturakostnader måste senare ersätta antagandena; annars underskattar modellen totalen. Gratiskällor/tid0 visas separat.

## Förväntade scenarionetton vid 38 spel à 10 kr

Alla nettobelopp i följande scenario- och måltabeller är matematiska förväntningar vid antagen edge. Ett realiserat resultat kan bli högre eller lägre; 19 och 190 kr är inga tak för slumpmässig vinst eller förlust.

| Scenario | Edge efter genomförande | Krävd rå edge före1 % prisavdrag | Spelnetto/säsong | Projektnetto/säsong | Ekonomiskt netto/säsong | Projektnetto/kalenderår | Ekonomiskt netto/kalenderår |
|---|---:|---:|---:|---:|---:|---:|---:|
| negativ | -5.00 % | -4.0404 % | -19,00 | -1 019,00 | -5 019,00 | -1 219,00 | -6 019,00 |
| noll | 0.00 % | 1.0101 % | 0,00 | -1 000,00 | -5 000,00 | -1 200,00 | -6 000,00 |
| försiktig | 1.00 % | 2.0202 % | 3,80 | -996,20 | -4 996,20 | -1 196,20 | -5 996,20 |
| positiv | 3.00 % | 4.0404 % | 11,40 | -988,60 | -4 988,60 | -1 188,60 | -5 988,60 |
| optimistisk | 5.00 % | 6.0606 % | 19,00 | -981,00 | -4 981,00 | -1 181,00 | -5 981,00 |

Belopp i kr. Vid antagen 1 % nettoedge blir förväntat spelnetto 3,80 kr/säsong; vid 5 % blir det 19,00 kr. Även vid det orealistiska kapacitetstaket 380 signaler och antagen 5 % nettoedge blir förväntat spelnetto 190 kr/säsong före datakostnad/arbetstid. Med 38 signaler är den förenliga datakostnaden för noll förväntat projektnetto vid antagen 5 % edge 19 kr/kalenderår (=1,58 kr/månad) om AI/övrigt kostar 0. Detta är en algebraisk brytpunkt, ingen rekommendation om abonnemang. Realiserad vinst kan avvika kraftigt åt båda håll.

## Baklänges från mål – huvudscenario 3 % nettoedge

Mål 100/500/1 000 kr är endast exempel. Aktiv månad jämför 3,8 referenssignaler och 38 matcher. Tio sådana aktiva månader innebär säsongsmål 1 000/5 000/10 000 kr. Kalenderår jämför 38 signaler och 380 matcher. Årsmål 1 200/6 000/12 000 kr motsvarar 100/500/1 000 kr per kalendermånad. Kravomsättning T=(mål+kostnader)/e och signaler=tak(T/10kr). För e≤0 finns inget ändligt positivt mål med positiva kostnader. Varje målrads fasta 10 kr insats binder 100/200 kr vid 10/20 samtidiga oavgjorda spel; den bindningen ändras inte för att inkomstmålet höjs.

| Period | Mål | Nettobegrepp | Omsättning | Signaler à10kr | Krävd algebraisk insats vid referensvolym | Vid en signal/varje match | Ryms i380matcher/år eller38/aktiv månad? |
|---|---:|---|---:|---:|---:|---:|---|
| aktiv_matchmånad | 100,00 | spelnetto | 3 333,34 | 334 | 877,20 | 87,72 | Nej |
| aktiv_matchmånad | 100,00 | projektnetto | 6 666,67 | 667 | 1 754,39 | 175,44 | Nej |
| aktiv_matchmånad | 100,00 | ekonomiskt_netto | 20 000,00 | 2000 | 5 263,16 | 526,32 | Nej |
| aktiv_matchmånad | 500,00 | spelnetto | 16 666,67 | 1667 | 4 385,97 | 438,60 | Nej |
| aktiv_matchmånad | 500,00 | projektnetto | 20 000,00 | 2000 | 5 263,16 | 526,32 | Nej |
| aktiv_matchmånad | 500,00 | ekonomiskt_netto | 33 333,34 | 3334 | 8 771,93 | 877,20 | Nej |
| aktiv_matchmånad | 1 000,00 | spelnetto | 33 333,34 | 3334 | 8 771,93 | 877,20 | Nej |
| aktiv_matchmånad | 1 000,00 | projektnetto | 36 666,67 | 3667 | 9 649,13 | 964,92 | Nej |
| aktiv_matchmånad | 1 000,00 | ekonomiskt_netto | 50 000,00 | 5000 | 13 157,90 | 1 315,79 | Nej |
| kalenderår | 1 200,00 | spelnetto | 40 000,00 | 4000 | 1 052,64 | 105,27 | Nej |
| kalenderår | 1 200,00 | projektnetto | 80 000,00 | 8000 | 2 105,27 | 210,53 | Nej |
| kalenderår | 1 200,00 | ekonomiskt_netto | 240 000,00 | 24000 | 6 315,79 | 631,58 | Nej |
| kalenderår | 6 000,00 | spelnetto | 200 000,00 | 20000 | 5 263,16 | 526,32 | Nej |
| kalenderår | 6 000,00 | projektnetto | 240 000,00 | 24000 | 6 315,79 | 631,58 | Nej |
| kalenderår | 6 000,00 | ekonomiskt_netto | 400 000,00 | 40000 | 10 526,32 | 1 052,64 | Nej |
| kalenderår | 12 000,00 | spelnetto | 400 000,00 | 40000 | 10 526,32 | 1 052,64 | Nej |
| kalenderår | 12 000,00 | projektnetto | 440 000,00 | 44000 | 11 578,95 | 1 157,90 | Nej |
| kalenderår | 12 000,00 | ekonomiskt_netto | 600 000,00 | 60000 | 15 789,48 | 1 578,95 | Nej |

Insatskolumnerna visar varför kalkylen inte ryms vid10kr. De är INTE en föreslagen insatshöjning; hypotetisk acceptans vid sådana belopp är helt obevisad. Högre risk ska inte användas för att rädda kalkylen. Alla fem edgefall, kostnadsnivåer och mål finns maskinläsbart i ekonomi.json.

## Kostnader och känslighet

JSON innehåller 36 kombinationer: 1/3/5 % nettoedge; data 0/100/300 kr per månad; AI 0/50 kr; arbetstid 0/400 kr. Vid 38 spel och 10 kr kan en enda månadskostnad 100 kr redan överstiga ett helt års antaget spelnetto flera gånger. Med alla kostnader 0 är spelnetto=projektnetto, men det visar inte att avgiftsfri åtkomst eller ägarens tid faktiskt finns. Ingen betald modell behövs för odds- och kostnadsaritmetik.

## Bundet kapital och nedgång

Vid10kr fast insats binder10 samtidiga oavgjorda spel100kr och20spel200kr. Olöst resultat släpper inte reservationen.100 öppna spel binder hela1 000kr experimentkapitalet; spel101 måste avstå, även om en positiv förväntan beräknas. Kapitalbehov för bunden exponering är max samtidiga/olösta spel×10kr, utöver reserv för förluster. Betalning av data hör inte till papperskapitalet. Varken1 000kr eller10kr är godkänd verklig budget.

Historiska största dagreservation 30,00kr är verifierad genom gruppering av val. Den är ingen prognos för framtida samtidighet. Historisk realiserad nedgång337,15kr är rapportuppgift, inte riskgräns eller framtida maxförlust. Framtida utvärdering ska redovisa nedgång på slutkapital respektive tillgängligt kapital inklusive olösta reservationer; en universell säker kapitalnivå kan inte härledas från detta material.

## Kan ett begränsat försök påvisa liten fördel?

Illustration, INTE faktisk styrkeberäkning för dessa långskott: oberoende lika stora spel med odds2, ensidigt5 % test och80 % styrka. n≈(1,644854+0,841621)²×4p(1−p)/e², p=(1+e)/2. Klustring, okänd sannolikhet och selektion kan öka behovet. Resultaten:

| Antagen edge | Ungefär n | Säsonger vid38 signaler | Säsonger vid högst380 |
|---|---:|---:|---:|
| 1% | 61820 | 1626.8 | 162.7 |
| 3% | 6864 | 180.6 | 18.1 |
| 5% | 2467 | 64.9 | 6.5 |

Hundra spel ger alltså ingen generell bevisgräns. Vid odds2 och p≈0,5 är standardfelet för100 spel omkring10 procentenheter ROI; ett normalt95 % intervall är ungefär ±19,6 procentenheter, före beroenden och urvalsproblem. Långskott4–29 från arkivet kräver annan variansmodell. Begränsad ny insamling kan avgöra tidsriktighet och datatäckning, men kan inte lova statistiskt besked om en liten lönsamhet inom en säsong.

## Ekonomiskt beslut

**Ekonomiskt orimligt inom den illustrerade ramen som förväntad hållbar inkomst** för mål 100–1 000 kr/månad, en liga, 10 kr pappersinsats och även optimistisk antagen 5 % nettoedge. Det gäller redan före kostnader: 38 spel/säsong ger förväntat spelnetto 19 kr/år i det scenariot. Med 380 spel/säsong blir förväntat spelnetto 190 kr/år, fortfarande under lägsta målet 1 200 kr/år. Detta utesluter inte högre realiserad slumpvinst och är inget tak för enskilda utfall; slutsatsen gäller de beräknade förväntningarna. Positiva fördelar är obevisade och högre insats är inte lösningen i detta uppdrag.

**Otillräckligt underlag** om det finns en användbar tidsriktig prisavvikelse över huvud taget. En liten kostnadsfri datakontroll kan ge ett tekniskt beslut, men är inte en investering som denna vinstkalkyl kan motivera med förväntad återbetalning. Betald pilot kräver separat ägarbeslut och högsta faktiska kostnad; ingen budget aktiveras här.

## Återskapa och kontrollera

Kör projektets Python med denna ekonomi.py. Skriptet läser endast arkiverad JSON/CSV och skriver endast ekonomi.json/ekonomi.md i den nya dokumentmappen. SHA256 för lästa arkivfiler ingår i JSON. Det använder Decimal för ekonomisk aritmetik, uppåtrundar nödvändig omsättning/insats och lagrar pengar som heltalsören. Månadssignalvolym är ett förväntat medelvärde; faktiska signaler är heltal och ojämnt fördelade. Inbyggda assert kontrollerar både arkivavräkning och ekonomiska formler: 52 % vid odds 2 och 10 kr ger 40 öre förväntat brutto, 29,6 öre efter 1 % prisavdrag, 27,6 öre med ytterligare 0,2 % omsättningsavgift; avgiften och prisavdraget dras endast en gång. Noll/negativ edge saknar positiv mållösning, och signalantal avrundas uppåt. Skriptet stoppar vid avvikelse. Kör utan Pythonflaggan -O, som stänger av assert.

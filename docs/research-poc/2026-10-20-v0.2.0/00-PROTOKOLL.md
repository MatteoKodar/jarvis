# JARVIS Research PoC A1 v0.2.0

**UTKAST – INTE KÖRKLART.** Datum: 2026-10-20, Europe/Stockholm. Dokumentation, inte beslut om insamling, implementation eller modellanrop. Inga verkliga paket, referenssvar, modeller, priser eller budgetar har fastställts.

## Försöksfråga och tolkningsgräns

Vilket tillskott ger självgranskning respektive Kritiker till **samma ursprungliga Researcher-utkast**, från samma fasta källpaket? Experimentenheten är ämnets gemensamma utkast. De tre slutrapporterna från ett ämne är parade och beroende observationer, inte tre oberoende försök.

För varje ämne skapas ett utkast en gång. Exakta svarsbitar sparas som UTF-8-byte, liksom den validerade strukturen, deras respektive SHA-256 och ett beständigt utkast-ID. Detta sker före förgreningen. Ingen gren får ändra originalet.

| Gren | Indata efter det gemensamma utkastet | Ytterligare modellsteg | Slutleverans |
| --- | --- | ---: | --- |
| S1 | Det sparade utkastet | 0 | Gemensam mekanisk slutleverans |
| S2 | Samma paket och exakt samma utkast | 1, Researcher i självgranskningsuppgift | Samma slutleveransregler |
| RK | Samma paket och exakt samma utkast | 1, Kritiker | Samma slutleveransregler |

Tre ämnen ger **tre utkast + tre självgranskningar + tre Kritikergranskningar = nio modellanropsplatser och nio planerade slutrapporter**. Ogiltiga eller saknade svar kan ge färre färdiga rapporter; nämnaren nio behålls och bortfallet redovisas. Ingen tionde diagnostik, separata första utkast, automatisk rättning eller ersättningskörning ingår.

Självgranskning är ett nytt anrop med en sparad text, utan tillgång till privat resonemang, chattminne eller ett tidigare SDK-tillstånd. S2 och RK får inte läsa varandras svar. Resultatet gäller dessa instruktioner, utkast, paket och modellinställningar. Det visar inte generell agentintelligens, källupptäckt, egen motresearch eller bästa arbetsflöde i allmänhet.

## Låsta metodförslag

- Tre primära kandidatämnen T01–T03; reserver T04, sedan T05 enligt 01.
- Högst sju originalpåståenden per utkast. Granskaren bedömer alla, får ta bort, föreslå högst ett nytt observationspåstående och föreslå en rekommendation uppåt eller nedåt.
- Ursprunglig påståendetext får inte skrivas om. Ett nytt observationspåstående får stabilt N01 inom sin gren och spåras separat.
- Högst åtta påståenden i en slutrapport. S1 har högst sju; faktisk maximal mängd är därför 69 förekomster. Mänsklig planering reserverar utrymme för 72.
- Samma modell och identiska stödda anropsinställningar för båda granskarna. Modell och pris är ännu **ej valda**.
- Gemensam preliminär ram: 65 536 input-token och 2 400 output-token per anrop. Paket högst 26 000 serialiserade UTF-8-byte, varav källtexter tillsammans högst 18 000 byte; utkast högst 10 000 byte; granskningssvar högst 12 000 byte. Alla gränser är tak, inte löften om att materialet ryms.
- Fullständig indata, inklusive systemtext, uppgiftsinstruktion, schema, utkast, paket och SDK-tillägg, måste storlekskontrolleras. Dagens bytekontroll och 16 384 bytes marginal är inte en A1-tokenisering som redan verifierats.
- För stort underlag eller för liten outputram kräver revidering och ny relevant frysning före körning. Ingen tyst kapning eller extra modellomskrivning.
- Inga verktyg, ingen automatisk Wikipedia, ingen webbsökning, inga handoffs eller verkliga affärshandlingar i A1.

## Förhandsbestämd körordning

De slutliga tre ämnena tilldelas position 1–3 i stigande kandidat-ID efter den låsta bytesregeln. Ordningen blir:

| Position | Anropsplatser i ordning |
| --- | --- |
| 1 | gemensamt utkast, S2, RK |
| 2 | gemensamt utkast, RK, S2 |
| 3 | gemensamt utkast, S2, RK |

En plats körs åt gången. Med tre ämnen går det inte att få exakt lika många förstapositioner: S2 börjar två gånger, RK en. Det är den minsta möjliga obalansen och redovisas som begränsning. Ingen omordning efter resultat. En senare separat replikation måste få en egen förhandslåst ordning och ett nytt beslut; den ingår inte här.

Ett giltigt utkast ska ha sparats innan någon av dess granskningsplatser kan öppnas. Felaktigt utkast blockerar båda grenarna för ämnet; ingen annan Researcher får skriva ett nytt utkast inom samma pilot. Ett saknat granskningssvar får inte fyllas genom en ny anropsidentitet. Vid osäker sändning bevaras reservationen enligt anropsgränsen.

## Primära mått och slutsats

M1 är felaktig rekommendationsnivå, inklusive felaktigt avstående, mot ett privat förhandslåst rimligt intervall. M2 är antal kvarvarande ostödda eller motsagda avgörande påståenden som bär rekommendationen. Oavgjort avgörande stöd markeras och blockerar tolkningsbeslut; det får inte antas vara korrekt.

Redovisa varje ämnes S1-värde och varje granskad grens värde, med parade förändringar. Summeringar får inte ersätta ämnesraderna eller bilda ett sammanvägt poängtal. Även borttagna välstödda påståenden, nya fel, motbelägg, nyttiga tillägg och rättelser av felaktiga avståenden följs.

Den föreslagna beslutsregeln i 02 skiljer observerad försämring, inget observerat primärt mervärde, lovande men osäker förbättring samt ofullständigt/otolkbart resultat. Den gamla regeln om felfritt RK och fel i båda baslinjerna finns kvar i historiken, men föreslås ersatt. Regeln behöver mänskligt beslut **före metodfrysning**.

## Människor, tid och ekonomi

Två personer behöver utses för rollerna insamlare/medbedömare A och referensansvarig/primärbedömare B. Inga personer har utsetts. Båda ska sakgranska samtliga slutpåståenden; därefter granskas ingreppen enligt den separata andra fasen. Bedömningarna av anonymiserade slutrapporter låses innan granskningssvar eller uppläggsnyckel öppnas.

Ny föreslagen ram är **3 798 personminuter = 63 timmar 18 minuter** för tre färdiga ämnen, inklusive 180 minuter reserv. Den är inte godkänd eller bokad. Ett fullt ersättningsämne kan kräva ytterligare 405 minuter. Tid för framtida kodimplementation ingår inte. 02 visar hela kalkylen.

Faktisk anropskostnad omfattar tre utkast och sex granskningar, även misslyckade/ogiltiga försök. Beräknad separat driftkostnad för varje S2/RK-rapport inkluderar dess ursprungliga utkast, utan att utkastet bokförs fler gånger som faktisk försökskostnad. Inga modeller, priser, valutakurser eller godkända belopp har hittats på.

## Frysningar och stoppunkter

1. **Metodfrysning före första källsökningen:** urval, söktjänst, frågor, bytesregel, granskarbefogenheter, instruktioner, format, bedömningsmetod, beslutsregel, ansvar och arbetsram beslutas.
2. **Körningsfrysning före första modellanropet:** verkliga paket och privata referenser är låsta, implementation lokalt verifierad, exakta modell-/pris-/resursuppgifter och hela inputkedjan granskade, anropsplatser och ordning bundna samt explicit ägarbeslut registrerat.
3. **Utkastlås per ämne:** råa svarsbyte och validerad struktur sparas och binds till båda grenarna före deras anrop.
4. **Bedömningslås:** slutrapportsomdömen låses före avmaskering och analys av ingreppen.

Hashar bevisar byteidentitet, inte att ett material är rätt, säkert, metodfryst eller godkänt. Ingen kommande operation får startas av denna dokumentleverans. Nödstopp, paus och osäker debitering måste bevaras i framtida implementation; detaljer finns i 04–05.

## Versionshistorik och dokumentkarta

Inventeringen hittade endast mappen **2026-10-18-v0.1.0-a5c383c6**, med dokument 00–02. De fyra där länkade bilagorna 03–06 finns inte. v0.2.0 är nästa nya metodversion eftersom försöksfråga, anropsantal och befogenheter ändras. Det är inte ett påstående om en mellanliggande v0.1.1. Tidigare filer lämnas orörda.

| Ändring från v0.1.0 | Skäl |
| --- | --- |
| Separata utkast/15 normala anrop blir gemensamt utkast/9 | Isolera granskningsstegets tillskott |
| Högst åtta original blir högst sju plus ett möjligt tillägg | Behålla högst åtta slutpåståenden |
| A0:s rekommendation kan bara sänkas; A1 föreslås tillåta höjning | Kunna rätta ett felaktigt avstående |
| Tidigare nollfelsregel ersätts som förslag, inte retroaktivt | Se förbättring även när fel kvarstår, och ämnesvisa skador |
| Begränsad stickprovskontroll blir full slutpåståendegranskning och separat ingreppsaudit | Mäta både nytta och skada |
| 18 timmar blir 63 timmar 18 minuter | Synliggöra hela den mänskliga arbetsinsatsen |
| Extra diagnostik och automatisk tänkt utökning utgår | Hålla nio fasta anropsplatser och undvika efterhandsanpassning |
| Central anropsgräns finns nu, men A1-adapter saknas | Skilja aktuell kod från framtida förslag |

- [01 Ämnen och källurval](01-AMNEN-OCH-KALLURVAL.md)
- [02 Jämförelse och bedömning](02-JAMFORELSE-OCH-BEDOMNING.md)
- [03 Påståenden, instruktioner och slutleverans](03-PASTAENDEN-OCH-SLUTLEVERANS.md)
- [04 Framtida implementationsuppdrag](04-IMPLEMENTATIONSUPPDRAG.md)
- [05 Frysning och integritet](05-FRYSNING-OCH-INTEGRITET.md)
- [06 Spårbarhet och projektkontroll](06-SPARBARHET-OCH-PROJEKTKONTROLL.md)

**UTKAST – INTE KÖRKLART:** människor och metodval är inte godkända, verkliga paket/referenser saknas, modell/pris/budget är olåsta och A1 är inte implementerat eller verifierat.

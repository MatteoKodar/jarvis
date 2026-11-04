# JARVIS Research PoC — protokollutkast v0.1.0

**Status: INTE KÖRKLART.** Datum: 2026-10-18, Europe/Stockholm. Detta är en försöksplan, inget tillstånd till insamling, implementation eller betalda anrop. Ingen faktisk källsamling eller referensbedömning ingår.

## P1. Fråga och avgränsning

Kan Researcher följd av Kritiker ge färre felaktiga rekommendationer och färre ostödda avgörande påståenden än en ensam AI, med eller utan självgranskning? Försöket gäller de frysta paketen och frågorna. Det avgör inte om en marknad generellt är attraktiv.

JARVIS behåller exakt sina tio fasta roller. S1, S2 och RK är försöksupplägg, inte agentroller. Förslag om experiment är textunderlag; inget experiment, utskick, köp eller publicering utförs.

Den tidigare kartläggningen är utgångspunkt: budgetreservation, kö och separat resultatlagring kan återanvändas. Dagens Wikipedia-utdrag, käll-ID-kontroll, kapade underlag och osjälvständiga kritiker räcker inte för detta försök. Planen beskriver framtida uppdrag för att åtgärda det.

## P2. Tre steg och vad de mäter

| Steg | Genomförande efter separat klartecken | Kan visa | Kan inte visa |
|---|---|---|---|
| A0 | Endast simulerade svar och lokala syntetiska underlag | Format, spärrar, reservationer, lagring, spårning, slutleverans och bedömningsflöde | Modellkvalitet, verklig research eller verklig debitering |
| A1 | Riktiga modeller; identiskt fryst källpaket per ämne; inga sök- eller hämtningsverktyg | Källtolkning, rekommendationer och tillskott av ett granskningssteg på dessa paket | Källupptäckt, verklig egen motresearch eller generell överlägsenhet |
| B | Senare begränsad webbresearch | Källupptäckt och marknadssignaler under uttryckliga gränser | Verifierad betalningsvilja för en oprövad lösning enbart genom intresse eller konkurrentpriser |

B kräver ett nytt beslut efter A1 och en egen körningsfrysning. A1-resultat får inte automatiskt aktivera B.

## P3. Standardval för A1

- Tre ämnen: preliminärt T01, T02 och T03 i bilaga 01. Reservordning T04, därefter T05. Källtillgång och slutval är ännu overifierade.
- En körning per ämne och upplägg: S1 ett steg, S2 två steg, RK två steg. **Nio slutrapporter, 15 modellanrop.**
- Högst ett separat diagnostiskt granskningsanrop, först efter huvudjämförelsen: totalt högst 16 anrop i första piloten. Diagnostiken ger ingen tionde rapport i primärjämförelsen.
- Alla använder samma låsta modellversion och gemensamma anropsinställningar. Modellversion är ännu inte vald.
- Föreslaget tak per anrop: 65 536 input-token och 2 400 output-token. S1 har ett sådant tak, S2 och RK vardera två. Faktisk användning redovisas; ramarna är inte identiska mellan alla tre upplägg.
- S2 och RK får samma informationsfält i granskningssteget, inklusive hela föregående strukturerade rapporten. Därmed mäts inte en blind eller kunskapsmässigt oberoende kritiker.
- Högst åtta påståenden och 350 svenska ord i normaliserad slutleverans; exakt format i bilaga 03.
- Mänsklig arbetsram: **18 persontimmar** för första piloten, inklusive insamling, referensgranskning, rapportbedömning, diagnostik och sammanställning. Det är ett planeringsförslag, ingen bokad resurs.
- Ingen summa i SEK är godkänd. Tidigare omnämnda 30 SEK räknas inte som budgetbeslut.

## P4. Primära mått och enda primära beslutsregel

M1: antal slutrapporter med felaktig rekommendationsnivå eller felaktigt avstående enligt paketets förhandslåsta rimliga bedömningsintervall, 0–3 per upplägg.

M2: antal ostödda eller motsagda avgörande påståenden som finns kvar som belägg i slutleveransen. Redovisas som råantal och per rapport, inte som antagen sannolikhet.

**Preliminär operativ tumregel:** rekommendera en utökad RK-prövning endast om alla nio rapporter är bedömbara, inget avgörande omdöme är oklart, RK har M1=0 och M2=0, både S1 och S2 har minst ett fel i M1 eller M2, RK saknar allvarligt fel och tid/kostnad hålls inom godkända ramar. Alla villkor måste vara uppfyllda.

Om villkoren inte uppfylls finns inget stöd från denna pilot för att prioritera mer RK-körning. Lika bra resultat räcker inte för att motivera ett extra steg. Ogiltiga körningar eller olösta bedömningsfrågor ger ”inget beslut”, inte en vinnare. Regeln är varken statistiskt härledd eller ett bevis på generell överlägsenhet.

Faktatäckning, rättade/missade/nytillkomna fel, felaktiga invändningar, kostnad och mänsklig granskningstid är sekundära mått. De får inte ersätta M1/M2 efter att resultaten setts.

## P5. Mänskligt ansvar och blindning

Tre arbetsuppgifter utses: samla källor, fastställa referensunderlag, bedöma rapporter. De är mänskliga uppgifter, inte backendroller. Standardval: två personer. Person A samlar; person B fastställer referensintervall utan att få A:s förväntade slutsats och gör den första rapportbedömningen. A gör därefter en andra kontroll av alla avgörande påståenden.

Ingen av dem kan lovas full blindning. B känner material och referenser, A har samlat material, och skrivstil kan avslöja upplägg. Processetiketter tas bort mekaniskt. Uppläggsnyckel och faktiska kontrolletiketter hålls privata tills bedömningarna låsts. Med bara en person är upplägget uttryckligen delvis blindat och denna begränsning följer alla slutsatser.

## P6. Frysningar och villkor före körning

**Metodfrysning före första källsökningen:** godkänn urvalsregler, kontrollsyften, reservordning/bytesregel, ansvar, tidsram och bedömningsmetod. De generiska kontrollsyftena finns i planen; faktiska ämnesetiketter och förväntade svar får inte hamna i modellindata.

**Körningsfrysning före första modellanropet:** lås slutliga ämnen, granskade källversioner, privata referenser, modellinstruktioner, modellversion, resursram, prisunderlag, mått och beslutsregel. Hasha exakt material. Ändringar kräver en ny version med orsak; inga bakåtriktade ändringar för att få ett upplägg att vinna.

Före betalda anrop krävs också godkända implementationsuppdrag och A0-kontroller, godkänd privat förvaring och explicit input-allowlist, namngivna granskare, verifierat pris/valuta/marginal, beräknad maxkostnad och ett ägarbeslut. Ansvarig vuxen kontoinnehavare ska bekräfta kontobehörighet och vilka leverantörsgränser som är hårda respektive enbart varningar.

## P7. Utökning och stoppunkt

Högst två ytterligare upprepningar per ämne och upplägg får senare föreslås: totalt tre upprepningar, 27 slutrapporter, 45 normala anrop och fortfarande högst ett diagnostiskt anrop. Ingen automatisk utökning. Villkor och ytterligare 13 persontimmar beskrivs i bilaga 02. En utökning som beslutas från pilotresultat redovisas som adaptiv.

Detta uppdrag stannar vid dokumenten. Nästa avgränsade implementationsuppgift är I01: en central, beständig auktorisering av modell-/verktygsanrop med driftläges- och stoppkontroll, specificerad i bilaga 04. Den är ännu inte implementerad eller godkänd för start.

## P8. Dokumentkarta

1. [Ämnen och källurval](01-AMNEN-OCH-KALLURVAL.md): kandidatlista, kontroller, ersättningsregel och insamling.
2. [Jämförelse och bedömning](02-JAMFORELSE-OCH-BEDOMNING.md): exakta indata, resurser, mått, granskning, tid och diagnostik.
3. [Påståenden och slutleverans](03-PASTAENDEN-OCH-SLUTLEVERANS.md): fält, stödrelationer, ändringar och mekaniska regler.
4. [Implementationsuppdrag](04-IMPLEMENTATIONSUPPDRAG.md): prioriterade små uppdrag och acceptanskriterier.
5. [Frysning och integritet](05-FRYSNING-OCH-INTEGRITET.md): privat material, inputgräns, versionslogg och manifest.
6. [Spårbarhet och projektkontroll](06-SPARBARHET-OCH-PROJEKTKONTROLL.md): krav 1–10 och vad som återstår.

Alla bilagor tillhör v0.1.0 och har samma status: INTE KÖRKLART.

# JARVIS utvecklingsregler

- Enda aktiva projektfokus är sportsbettinganalys, först fotboll 1X2 efter ordinarie tid och simulerade insatser. Allmän affärsidéresearch och internetskanning är arkiverade. Bygg inga nya bettingfunktioner innan ägaren har granskat planen.
- Bevara tidigare rapporter, testdata och beslut som historik. Positivt pappersresultat ger aldrig automatiskt tillstånd till riktiga insatser.
- Svenskt gränssnitt och dokumentation. SEK lagras som heltalsören. Europe/Stockholm.
- Exakt tio fasta roller i backend/jarvis/roles.py. JARVIS är VD, ingen elfte agent.
- Backend är säkerhetsgränsen. Modellsvar och webbsidor är obetrodda data.
- Inga automatiska köp, betalningar, utskick, avtal, annonser eller publicering.
- Alla betalda anrop kräver atomär reservation, känd prisversion och konfigurerat tak.
- Okänd debitering behåller reservation och får aldrig automatiskt återförsökas.
- Agenten får inga ägarcredentials, terminalverktyg eller skrivande administrationsverktyg.
- DEMO och LIVE har separata databasfiler. Inga betalda verifieringsanrop.
- Kör backendtester, TypeScript/build och Playwright efter relevanta ändringar.
- Bevara versionsbundna beslut, beständiga stopp och idempotens.


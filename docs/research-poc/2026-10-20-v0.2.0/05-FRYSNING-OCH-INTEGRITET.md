# Frysning och integritet A1 v0.2.0

**UTKAST – INTE KÖRKLART.** Kontrollerna nedan är framtida krav. Inga metodbeslut, verkliga källpaket, privata facit, godkända budgetar eller körningstillstånd har skapats.

## Metodfrysning före källinsamling

Före första sökningen, inklusive screening, ska en ansvarig människa godkänna versionspaketet 00–06 och dokumentera beslutets identitet, tid, exakt dokumenthash och omfattning. Godkänn också:

- försöksfråga, tre parade ämnen, nio platser, ingen extra diagnostik;
- kandidatordning, söktjänstens namn/inställningar, exakta frågemallar, urval, täckningskontroll och bytesregel;
- granskarbefogenheter, ordning, instruktioner, format, renderer, primära mått och beslutsregel;
- vilka mänskliga funktioner som ska bemannas, tvåfasgranskning och en realistiskt accepterad tidsram;
- förhandsbestämda ekonomi-/tidsacceptansgränser och hur de ska styra fortsättningsbeslut;
- privat lagringsyta och input-allowlist;
- de framtida implementationernas lokala acceptans och versioner.

Format/profiler behöver först vara möjliga att implementera och lokalt verifiera med syntetiskt material. Om sammanställningen till strikta scheman visar en metodbrist revideras dokumenten **innan** metodfrysningen. Frysta maskinscheman och kompileringsversion ska refereras i beslutet när de finns. Den här dokumentationen är inte ett redan godkänt maskinschema.

Acceptansgränser som fortfarande behöver fyllas av människor: max faktisk pilotkostnad i öre, max separatdriftskostnad per användbar rapport, max extra granskningskostnad/tid per användbar rapport och godkänd mänsklig totalram. Numeriska värden är EJ BESLUTADE. De får inte väljas efter modellresultaten. Prisuppgifter binds senare till den frysta ramen före körningsfrysning.

## Körningsfrysning före modellanrop

Efter insamling och privat referensgranskning, före första draftanropet, krävs ett oföränderligt körningsmanifest med:

1. Exakt tre slutliga paket, arkiverade texter, käll-/pakethashar, urvalslogg och alla godkända bytesbeslut.
2. Låsta privata fakta/intervall och kontrollsyften, med godkänd separat lagring; inga olösta avgörande referensfrågor.
3. Godkänd implementation, källfilmanifest/revision och verkligt lokalt verifierad klientkedja. Dagens dokumenterade testresultat ersätter inte denna A1-verifiering.
4. Begärt exakt modell-ID, tillåtet returnerat modell-ID, dokumenterad versionsbindning, alla stödda inställningar och ett avgränsat körfönster. Om versionslåsning saknas behövs ett uttryckligt förhandsbeslut om begränsningen, inte ett tyst modellaliasbyte.
5. Frysta profil-/system-/schemabyte och fullständiga inputexempel som faktiskt ryms. Draftberoende slutinput kontrolleras också när utkastet finns.
6. Känd prisversion, verifieringskälla/datum, valuta och växelkurs, tokenram, konservativ maxkostnad för nio platser samt befintliga total-/dag-/uppgiftstak och låst reserv.
7. Beständigt namngivna nio anropsplatser, ordningsregel, experimentets stoppnummer, operatör och utvärderingsansvar.
8. Ett uttryckligt, autentiserat mänskligt ägarbeslut om dessa hashbundna platser och kostnadsramar.

All kod/metadata som senare tillför modellkontext måste vara med i inputarkivet. Hela dokument 03 eller detta dokument får **inte** skickas som modellprompt; de innehåller även mänskliga utvärderingsexempel som inte tillhör input-allowlisten.

## Manifestformat

Manifestets schema är a1-manifest-0.2.0. Alla fält i det kompletta DRAFT-exemplet är obligatoriska, utan extra fält. Null/tomma bindningar nedan gör det uttryckligen icke körbart.

- status: DRAFT, METHOD_FROZEN, RUN_FROZEN, EVALUATION_LOCKED eller CLOSED.
- method.protocol_files: exakt de sju dokumenten med verkliga hashvärden före metodfrysning. decision_ref är ett beständigt godkännandebeslut, inte själva dokumenthashen.
- instruction_hashes och compiled_schema_hashes har exakt de namngivna nycklarna i exemplet. Vid frysning är alla hashvärden kända. Strikta schemaartefakter arkiveras separat; extra modell-/bedömarscheman får inte tillkomma tyst.
- runtime.client_versions: map med granskade paketnamn och exakta versionssträngar. runtime.model: requested_id, allowed_returned_ids (icke tom lista), version_lock_status (exact eller accepted_drift_risk), exception_decision_ref (null endast vid exact).
- runtime.settings: map med exakt de stödda inställningsnamnen och deras värden; unsupported/utelämnade inställningar dokumenteras i ett separat included/omitted-underlag. Temperatur/seed hittar vi inte på.
- runtime.resource_limits: positiva heltal i exakt angivna token-/bytefält. no_tools måste vara true.
- price_profile: model_id, price_version, currency=USD, input_per_million och output_per_million som positiva decimalsträngar, source_ref, verified_at. fx_profile: usd_sek positiv decimalsträng, source_ref, verified_at. Inga credentials.
- per_call_caps_ore: map från exakt nio slot_id till heltal >=0; övriga *_ore är heltal >=0, bundna till faktiskt godkända gränser. budget_approval_ref är obligatoriskt före RUN_FROZEN.
- acceptance_limits: max_separate_cost_per_usable_ore, max_extra_review_cost_per_usable_ore, max_review_minutes_per_usable som icke negativa heltal; scope beskriver i 1–500 tecken vilken föreslagen fortsättning som bedöms. Noll användbara eller okända kostnader gör grinden unresolved, inte pass.
- topics: exakt tre TopicBinding; calls: exakt nio CallBinding före RUN_FROZEN. Alla ID:n unika där så krävs.
- private_store_approval_ref, operator_ref, evaluation_assessor_refs (minst två mänskliga referenser), run_authorization_ref måste vara beslutade. run_window har earliest/latest som UTC-tider. experiment_epoch är beständigt icke negativt heltal.
- Kodrevision kan saknas i Git, men då krävs ett fullständigt källfilmanifest med filhashar och dess hash. En godtycklig mappsuffix får inte kallas commit.

**TopicBinding:** topic_id T01–T05, package_ref (tillåten offentlig artefakt), package_sha256, private_reference_commitment, draft_slot_id, s1_report_slot_id, self_review_slot_id, critic_slot_id. Den privata referensens sökväg och innehåll ligger inte i den publika modellinputytan.

**CallBinding:** slot_id, topic_id, stage draft/self_review/critic_review, role_id researcher/critic, task_id, run_id, operation_id, parent_draft_slot_id (null för draft), input_profile_hash, max_cost_ore. Backend måste binda dessa beständigt utan möjlig nätverkssändning före auktorisering; den framtida implementationen ska inte kräva att en levande workerlease påbörjas långt före ett mänskligt frysningsbeslut. Experimentets unika logiska slot-ID är planeringsbindningen, och task/run/operation får endast fyllas genom kontrollerad beständig förberedelse. Ofylld teknisk bindning spärrar sändning. Inget nytt ID får ersätta ett tidigare förberett/osäkert ID.

Frysningen av den mänskliga anropsplanen och den efterföljande atomära operativa task/run-bindningen är skilda steg: planens föränderlighet upphör vid RUN_FROZEN; en teknisk bindningshändelse får fylla null-fält enligt planen men aldrig ändra ämne, steg, profil eller tak. Därför tillåts null task/run/operation i den frysta planen tills platsen auktoritativt förbereds; före sändning måste alla vara kända och immutabla. Använd ett append-only händelsearkiv för dessa bindningar, inte omskrivning av det frysta manifestet.

Komplett, avsiktligt ofyllt exempel. Inget modell-ID, pris, valutatal eller godkänd budget har antagits:
~~~json
{
  "schema_version": "a1-manifest-0.2.0",
  "manifest_id": "EX-MANIFEST-DRAFT",
  "protocol_version": "0.2.0",
  "status": "DRAFT",
  "created_at": "2026-10-20T00:00:00Z",
  "timezone": "Europe/Stockholm",
  "method": {
    "decision_ref": null,
    "protocol_files": [
      {
        "path": "00-PROTOKOLL.md",
        "sha256": null
      },
      {
        "path": "01-AMNEN-OCH-KALLURVAL.md",
        "sha256": null
      },
      {
        "path": "02-JAMFORELSE-OCH-BEDOMNING.md",
        "sha256": null
      },
      {
        "path": "03-PASTAENDEN-OCH-SLUTLEVERANS.md",
        "sha256": null
      },
      {
        "path": "04-IMPLEMENTATIONSUPPDRAG.md",
        "sha256": null
      },
      {
        "path": "05-FRYSNING-OCH-INTEGRITET.md",
        "sha256": null
      },
      {
        "path": "06-SPARBARHET-OCH-PROJEKTKONTROLL.md",
        "sha256": null
      }
    ],
    "selection_service": null,
    "instruction_hashes": {
      "system": null,
      "draft": null,
      "self_review": null,
      "critic": null
    },
    "compiled_schema_hashes": {
      "package": null,
      "draft": null,
      "review": null,
      "final": null,
      "assessment": null
    },
    "review_order": [
      "S2-RK",
      "RK-S2",
      "S2-RK"
    ]
  },
  "runtime": {
    "code_revision": null,
    "code_manifest_ref": null,
    "code_manifest_sha256": null,
    "client_versions": null,
    "model": null,
    "settings": null,
    "resource_limits": {
      "max_input_tokens": 65536,
      "max_output_tokens": 2400,
      "max_package_bytes": 26000,
      "max_source_text_bytes": 18000,
      "max_draft_bytes": 10000,
      "max_review_bytes": 12000
    },
    "no_tools": true
  },
  "economics": {
    "price_profile": null,
    "fx_profile": null,
    "per_call_caps_ore": null,
    "total_cap_ore": null,
    "daily_cap_ore": null,
    "per_task_cap_ore": null,
    "locked_reserve_ore": null,
    "budget_approval_ref": null,
    "human_minutes_requested": 3798,
    "human_minutes_approved": null,
    "acceptance_limits": null
  },
  "topics": [],
  "calls": [],
  "private_store_approval_ref": null,
  "operator_ref": null,
  "evaluation_assessor_refs": [],
  "run_authorization_ref": null,
  "run_window": null,
  "experiment_epoch": null
}
~~~
## Utkastlås och händelsearkiv efter körningsfrysning

Ett råutkast finns först efter det gemensamma anropet. Dess hash kan därför inte vara ett förhandskrav för första anropet. Körningsmanifestet fryser platsen och reglerna; append-only-händelser binder därefter råutkast och båda grenar till samma byte. Den frysta grundplanen skrivs inte om som om utfallet var känt före körning.

**InputArchive**, schema a1-input-0.2.0: slot_id, system_utf8, role_instruction_utf8, task_input enligt 03, output_schema (fullständigt JSON Schema-objekt), output_schema_sha256, request_body_utf8, request_body_sha256, compiler_version samt sdk_added_context. Den sista är en lista med objekt location/utf8/sha256 för varje faktiskt automatiskt tillägg, eller tom lista. Samtliga fält krävs. Request-body är den exakta serialiserade kroppen; behörighets-/credentialsheaders sparas aldrig.

**ExecutionEvent**, schema a1-event-0.2.0: event_id, experiment_id, slot_id, occurred_at, task_id, run_id, operation_id, epoch, state, input_archive_ref, request_body_sha256, response_ref, response_sha256, draft_raw_sha256, validated_structure_sha256, usage, cost_estimate_ore, reservation_id, reservation_status, uncertainty, send_attempts_observed. ID/tid/slot/state är obligatoriskt kända; ännu inte producerade datafält är null. state är planned/prepared/possible_send/completed/invalid/unknown/cancelled. usage är null eller input_tokens/output_tokens som heltal >=0. reservation_status är none/held/unknown/released/settled/reconciled. uncertainty är null eller saklig kort orsak utan leverantörshemligheter. send_attempts_observed är 0, 1 eller null när ingen tillförlitlig observation finns, exempelvis processkrasch. En möjlig-sändning-markering bevisar inte att transporten hann starta.

Ett giltigt utkastlås innehåller råa output_text-byte (UTF-8 efter JSON-avkodning av leverantörens textfält, före parsning av utkastets JSON), deras hash och separat validerad canonical struktur/hash. Den ursprungliga HTTP-svarskroppen sparas separat där det är tillåtet. Strängen som båda granskarna får ska efter UTF-8-återkodning ha exakt råutkasthash.

Ingen modell får ta emot råa SDK-fel som nya instruktioner, privata bedömningar eller föregående grenresultat. Fullständiga inputarkiv granskas mot allowlisten och schemahasharna. Ett okänt automatiskt SDK-tillägg stoppar sändning tills relevant profil och frysning reviderats.

## Privat referensformat och separering

**ReferencePacket**, schema a1-reference-0.2.0: package_sha256, synthetic boolean, reference_facts 5–8 poster, recommendation_interval, coverage_gaps, assessor_ids (minst två), locked_at UTC eller null före lås, both_confirmed boolean. Före körning krävs låstid och bekräftelse.

**ReferenceFact:** id F01–F08, text 1–1 000 tecken, citations 1–3 Citation, category package_fact/offer_fact/commercial_assessment, applicability 1–500 tecken, decisive boolean. En kommersiell bedömning ska uttryckligen skiljas från en observerad faktaenhet; intervallet kan använda den men får inte kalla den ett faktiskt köp.

**ReferenceInterval:** min/max ur avsta/vidare_research/billigt_experiment i den ordningen, min<=max; reason; necessary_fact_ids (kända F-ID); commercial_judgement 1–1 000 tecken. **CoverageGap:** id G01–G20, description och decisive boolean.

Följande öppna syntetiska illustration är inte ett verkligt privat facit och får inte skickas till modellen. Den visar sex passagebundna fakta, separat kommersiellt omdöme och ett intervall:
~~~json
{
  "schema_version": "a1-reference-0.2.0",
  "package_sha256": "517ce01ff375b6af4b90b16ef748d738333ed540875e306c4f39649b18eb8fb0",
  "synthetic": true,
  "reference_facts": [
    {
      "id": "F01",
      "text": "Tre grupper anger dubbelarbete.",
      "citations": [
        {
          "source_id": "K01",
          "passage_id": "L01",
          "quote": "Tre grupper anger dubbelarbete.",
          "start_byte": 0,
          "end_byte": 31
        }
      ],
      "category": "package_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": true
    },
    {
      "id": "F02",
      "text": "Ingen betalning har observerats.",
      "citations": [
        {
          "source_id": "K02",
          "passage_id": "L01",
          "quote": "Ingen betalning har observerats.",
          "start_byte": 0,
          "end_byte": 32
        }
      ],
      "category": "package_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": true
    },
    {
      "id": "F03",
      "text": "En fri mall hanterar en del av arbetet.",
      "citations": [
        {
          "source_id": "K03",
          "passage_id": "L01",
          "quote": "En fri mall hanterar en del av arbetet.",
          "start_byte": 0,
          "end_byte": 39
        }
      ],
      "category": "package_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": false
    },
    {
      "id": "F04",
      "text": "Ett verktyg har ett listat pris.",
      "citations": [
        {
          "source_id": "K04",
          "passage_id": "L01",
          "quote": "Ett verktyg har ett listat pris.",
          "start_byte": 0,
          "end_byte": 32
        }
      ],
      "category": "offer_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": false
    },
    {
      "id": "F05",
      "text": "En grupp anger att mallen inte racker.",
      "citations": [
        {
          "source_id": "K05",
          "passage_id": "L01",
          "quote": "En grupp anger att mallen inte racker.",
          "start_byte": 0,
          "end_byte": 38
        }
      ],
      "category": "package_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": false
    },
    {
      "id": "F06",
      "text": "Underlaget visar inte hur vanliga problemen ar.",
      "citations": [
        {
          "source_id": "K06",
          "passage_id": "L01",
          "quote": "Underlaget visar inte hur vanliga problemen ar.",
          "start_byte": 0,
          "end_byte": 47
        }
      ],
      "category": "package_fact",
      "applicability": "Endast det öppna syntetiska paketet.",
      "decisive": true
    }
  ],
  "recommendation_interval": {
    "min": "vidare_research",
    "max": "vidare_research",
    "reason": "Öppet syntetiskt övningsintervall, inte ett verkligt privat facit.",
    "necessary_fact_ids": [
      "F01",
      "F02"
    ],
    "commercial_judgement": "Exemplet visar endast ett researchbehov; verifierad betalningsvilja följer inte av erbjudet pris."
  },
  "coverage_gaps": [
    {
      "id": "G01",
      "description": "Faktisk betalningsvilja för en ny lösning är inte observerad i exemplet.",
      "decisive": true
    }
  ],
  "assessor_ids": [
    "EX-HA",
    "EX-HB"
  ],
  "locked_at": "2026-10-20T00:00:00Z",
  "both_confirmed": true
}
~~~
Verkliga privata referenser, kontrolletiketter, bedömningar och uppläggsnycklar skapas senare utanför arbetsträdet, bilagor, promptcache och automatiskt indexerade mappar. En .gitignore ensam är inte en åtkomstgräns. Ansvarig människa väljer och godkänner lagringsyta och behörigheter; ingen sökväg eller privat fil har skapats nu.

Modellinput får endast läsa det uttryckligt tillåtna Package, råutkast, system-/metodinstruktion och rätt outputschema. Varken referensformatet, dess exempel, kontrollsyfte, rimligt intervall eller en hel dokumentmapp är en tillåten input. Utvärderaren behöver privat åtkomst som modellen inte har.

Blindningsnyckeln kopplar opaka blind_report_id till experiment/topic/branch/finalrapporthash och B-ID till stabila påstående-ID. Den genereras/låses före Fas-I-utlämningen, med en förhandsbestämd privat ordningspermutation för de nio planerade rapportplatserna; saknade platser fylls inte med ersättningar. Ingen verklig permutation eller nyckel har skapats.

Privata åtaganden beräknas som SHA-256 över en privat slumpad 32-byte salt följd av canonical privat artefakt. Salt och innehåll hålls privata för att undvika enkel gissning av ett litet antal etiketter. Åtagandet kan finnas i revisionsunderlaget men ligger ändå utanför modellinput. Det är ett integritetsåtagande, inte mänskligt godkännande.

## Stopp, fel och ändringar

Anropsgränsens **prepared → possible_send → completed/unknown** och pre-send cancelled bevaras. Varje faktisk modellsändning kräver egen atomär reservation enligt sin frysta modell/pris/resursram. Det nioanropsmax som godkänts i planeringen är inte nio förhandsbokförda kostnader; dubbelreservation undviks genom en reservation per beständigt operations-ID.

Nödstopp före auktorisering stoppar transport. Redan auktoriserat försök kan hinna skickas; databas och leverantör är inte atomiska. Gamla experiment-/körningsstoppnummer återaktiveras inte av Återuppta. Paus stoppar nya platser men låter ett påbörjat anrop avslutas; nästa plats väntar.

Unknown ger stopp för återstående externa anrop i denna pilot, ofullständigt resultat och manuell kostnadsavstämning. Ingen automatisk fortsättning eller omsändning. Ett ogiltigt men kostnadsmässigt känt svar redovisas som ogiltigt; andra förhandsplanerade platser får bara fortsätta om deras föräldrautkast finns och alla ursprungliga villkor fortfarande gäller. Ett ogiltigt utkast gör ämnets båda granskningsplatser otillgängliga, utan ersättningsutkast.

Ingen frånvaro av kvitto tolkas som gratis. Manuellt avstämd reservation får inte återöppna samma slot/task/run/operation. En eventuell ny pilot eller återstående del kräver eget dokumenterat beslut och redovisas som separat/ofullständig jämförelse, inte som osynlig reparation.

Efter metodfrysning kräver ändrad försöksfråga, urval, format, instruktion, resursram eller beslutsregel en ny metodversion och bedömning av vilka tidigare insamlingssteg som måste göras om. Efter körningsfrysning kräver ändrade paket/modell/priser/runtime nytt körningsmanifest och nytt beslut innan nya anrop. Befintliga svar, kostnader och stopp består. Inga protokoll skrivs om bakåt för att ett upplägg ska vinna.

Dokumenthashar i 06 beskriver endast den här leveransen. **UTKAST – INTE KÖRKLART:** inget frysningsbeslut, ingen privat lagringsyta, inga verkliga paket/referenser och inget exekverbart A1-körningsmanifest finns.

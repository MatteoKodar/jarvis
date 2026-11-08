import {money, date} from './format';

export const DEMO_REVIEW_VERSION='betting-demo-review-v2';
type Code='KICKOFF_PASSED'|'INSUFFICIENT_FRESH_SOURCES'|'FUTURE_QUOTE'|'STALE_QUOTE'
  |'PROPOSAL_ON_REJECTED_MATCH'|'STALE_OR_FUTURE_SOURCE'|'UNKNOWN_SOURCE'|'PACKET_MISMATCH'
  |'AMOUNT_MISMATCH'|'CONTEXT_MISSING'|'SOURCE_INDEPENDENCE_UNVERIFIED';
const codeText:Record<Code,string>={
  KICKOFF_PASSED:'Matchen har startat vid den simulerade granskningstiden.',
  INSUFFICIENT_FRESH_SOURCES:'För få färska källposter för jämförelsen.',
  FUTURE_QUOTE:'Offerten ligger efter den simulerade granskningstiden.',
  STALE_QUOTE:'Offerten är äldre än den frysta färskhetsgränsen.',
  PROPOSAL_ON_REJECTED_MATCH:'Förslaget gäller en match som underlagskontrollen avvisar.',
  STALE_OR_FUTURE_SOURCE:'Inaktuell eller framtida källa.',
  UNKNOWN_SOURCE:'Förslaget hänvisar till en okänd källa.',
  PACKET_MISMATCH:'Förslaget stämmer inte med matchens underlag.',
  AMOUNT_MISMATCH:'Pris eller insats stämmer inte med de frysta reglerna.',
  CONTEXT_MISSING:'Form, skador och laguppställningar saknas i underlaget.',
  SOURCE_INDEPENDENCE_UNVERIFIED:'Källornas oberoende är inte verifierat.',
};
function reason(code:string){return codeText[code as Code]??`Okänd kod: ${code}`}
function when(value?:string){return value&&Number.isFinite(Date.parse(value))?date(value):'Uppgift saknas'}
function amount(value:unknown){return typeof value==='number'&&Number.isFinite(value)?money(value):'Uppgift saknas'}
function list(value:unknown):unknown[]{return Array.isArray(value)?value:[]}
function count(value:unknown){return Array.isArray(value)?String(value.length):'uppgift saknas'}
function object(value:unknown):Record<string,unknown>{return value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{}}

type Source={book?:string;source_url?:string;updated_at?:string;age_seconds?:number;fresh?:boolean;reason?:string|null};
export type ResearchPacket={event_id?:string;as_of?:string;fresh_count?:number;max_quote_age_seconds?:number;
  minimum_fresh_sources?:number;sources?:Source[];missing_context?:string[];rejections?:string[];packet_hash?:string};
type Step={role_id?:string;role_name?:string;role_version?:string;status?:string;input_hash?:string;output_hash?:string;
  facts?:Record<string,unknown>;limitations?:unknown[]};
type CoreProposal={event_id:string;home:string;away:string;outcome:string;paper_odds:number;stake_ore:number};
export type ReviewPayload={review_version?:string;core_proposal_hash?:string;notice?:string;
  core_analysis?:{proposals?:CoreProposal[]};research?:{version?:string;packets?:ResearchPacket[]};
  review?:{steps?:Step[];findings?:{code?:string;severity?:string;event_id?:string|null}[]}};

export function readableReview(analysis:ReviewPayload){
  const steps=analysis.review?.steps;
  const packets=analysis.research?.packets;
  const originals=analysis.core_analysis?.proposals;
  if(!Array.isArray(steps)||!Array.isArray(packets)||!packets.length||!Array.isArray(originals))return false;
  if(steps.map(step=>step.role_id).join(',')!=='researcher,analyst,finance,critic')return false;
  const candidates=object(steps[1].facts).candidate_event_ids;
  const events=object(steps[0].facts).event_ids;
  return Array.isArray(candidates)&&candidates.length===originals.length&&Array.isArray(events)
    &&events.length===packets.length&&events.every((id,i)=>id===packets[i].event_id);
}

export function ResearchEvidence({packet}:{packet?:ResearchPacket}){
  if(!packet)return <p className="review-unreadable">Sparat researchunderlag saknas för denna match.</p>;
  const sources=Array.isArray(packet.sources)?packet.sources:[];
  return <details className="demo-research" data-testid={'research-'+packet.event_id}>
    <summary>Researchunderlag · {packet.fresh_count??'–'} av {sources.length} färska källposter</summary>
    <p>Simulerad granskning: {when(packet.as_of)}. Färskhet gäller scenariot. Gräns {packet.max_quote_age_seconds??'–'} sekunder; minst {packet.minimum_fresh_sources??'–'} färska källposter behövs.</p>
    <ul className="research-rejections">{(packet.rejections??[]).map(code=><li key={code}>{reason(code)}</li>)}</ul>
    <div className="research-sources"><table><thead><tr><th>Källa / referens, ej hämtad</th><th>Simulerad offerttid</th><th>Ålder</th><th>Färskhet</th></tr></thead>
      <tbody>{sources.map((source,i)=><tr key={String(source.book)+'-'+i}>
        <td><strong>{source.book??'Uppgift saknas'}</strong><code>{source.source_url??'Referens saknas'}</code></td>
        <td>{when(source.updated_at)}</td><td>{typeof source.age_seconds==='number'?source.age_seconds.toLocaleString('sv-SE',{maximumFractionDigits:6})+' s':'–'}</td>
        <td>{source.fresh===true?'Färsk i scenariot':typeof source.reason==='string'?reason(source.reason):'Uppgift saknas'}</td>
      </tr>)}</tbody></table></div>
    <p>Form, skador och laguppställningar saknas i underlaget och ingår inte i beräkningen. Käll-ID:n bevisar inte oberoende källor.</p>
    <details><summary>Underlagets innehållsbindning</summary><code>{packet.packet_hash??'Hash saknas'}</code></details>
  </details>;
}

function StepFacts({step}:{step:Step}){
  const facts=object(step.facts);
  if(facts.kind==='researcher')return <p>{count(facts.event_ids)} matcher granskade. {count(facts.rejected_event_ids)} matcher har avvisningsskäl i underlaget. Källornas färskhet redovisas per match nedan.</p>;
  if(facts.kind==='analyst')return <p><strong>{count(facts.candidate_event_ids)} grundförslag före kritik.</strong> Prisberäkningen använder de frysta offerterna.</p>;
  if(facts.kind==='finance')return <p><strong>Före kritik:</strong> {String(facts.proposal_count??'–')} förslag, {amount(facts.total_stake_ore)} i insats och {amount(facts.simulated_cost_ore)} i simulerade kostnader. Projicerat tillgängligt kapital {amount(facts.projected_available_ore)}.{facts.capital_sufficient===false&&' Kapitalet räcker inte för hela grundbatchen.'}</p>;
  if(facts.kind==='critic'){
    const final=object(facts.final_money);
    return <p><strong>Efter kritik: {count(facts.retained_event_ids)} slutliga förslag.</strong> {count(facts.removed_event_ids)} borttagna. Slutlig insats {amount(final.total_stake_ore)}, simulerad kostnad {amount(final.simulated_cost_ore)}, projicerat tillgängligt kapital {amount(final.projected_available_ore)}.</p>;
  }
  return <p>Sparade fakta kunde inte tolkas. Ingen ny granskning skapas vid läsning.</p>;
}

export function ReviewTrace({workflowVersion,analysis}:{workflowVersion?:string;analysis:ReviewPayload|null}){
  if(workflowVersion===undefined)return <section className="panel betting-review legacy-review" aria-label="Äldre granskningsversion"><h3>Äldre omgång</h3><p>Äldre omgång – skapad före granskningskedjan. Ingen research skapas i efterhand.</p></section>;
  if(workflowVersion!==DEMO_REVIEW_VERSION||(analysis&&analysis.review_version!==DEMO_REVIEW_VERSION))return <section className="panel betting-review" aria-label="Okänd granskningsversion"><h3>Okänd granskningsversion – visas utan rollkedja</h3><p>Det sparade läget kan läsas. Denna version kan inte användas för nya demoövergångar.</p></section>;
  if(!analysis)return <section className="panel betting-review" aria-label="Granskning inför analys"><h3>Nästa steg: granska samma underlag tillsammans.</h3><p>Researchunderlag och fyra regelbaserade granskningssteg sparas när du analyserar omgången.</p></section>;
  const steps=Array.isArray(analysis.review?.steps)?analysis.review.steps:[];
  if(!readableReview(analysis))return <section className="panel betting-review" aria-label="Ofullständig sparad granskning"><h3>Sparad granskning är ofullständig.</h3><p>Ingen ny kedja konstrueras vid läsning. Nya övergångar kräver ett giltigt sparat underlag.</p></section>;
  const findings=Array.isArray(analysis.review?.findings)?analysis.review.findings:[];
  const originals=Array.isArray(analysis.core_analysis?.proposals)?analysis.core_analysis.proposals:[];
  return <section className="panel betting-review" aria-label="Sparad rollgranskning">
    <h3>Så granskades omgången</h3><p className="review-notice">Regelbaserad offline-demo – ingen språkmodell, inga hämtade källor.</p>
    <p>Sparat vid analysen. Beloppen nedan är projektioner före registrering och matchresultat.</p>
    <ol className="review-steps">{steps.map((step,i)=><li key={String(step.role_id)+'-'+i} data-testid={'review-step-'+step.role_id}>
      <header><strong>{i+1}. {step.role_name??'Okänd roll'} · regelkontroll</strong><span className="badge">{step.status==='with_abstentions'?'Förslag togs bort':step.status==='with_limitations'?'Klart med begränsningar':step.status==='completed'?'Klart':'Okänd sparad status'}</span></header>
      <StepFacts step={step}/><ul>{list(step.limitations).filter((v):v is string=>typeof v==='string').map((value,j)=><li key={j}>{value}</li>)}</ul>
    </li>)}</ol>
    <div className="review-findings"><h4>Sparade fynd och begränsningar</h4><ul>{findings.map((finding,i)=><li key={i} className={finding.severity==='blocker'?'review-blocker':''}>
      {finding.event_id&&<strong>{finding.event_id}: </strong>}{typeof finding.code==='string'?reason(finding.code):'Sparad kod saknas'}
    </li>)}</ul><p>För ett borttaget förslag visas det högst prioriterade blockeringsskälet, inte alla möjliga fel.</p></div>
    <details className="review-originals"><summary>Grundförslag före kritik ({originals.length})</summary>
      <ul>{originals.map(p=><li key={p.event_id}>{p.home} – {p.away}: {p.outcome==='home'?'1':p.outcome==='draw'?'X':'2'}, effektivt odds {(p.paper_odds/10000).toFixed(4)}, insats {money(p.stake_ore)}.</li>)}</ul>
      <p>Grundanalysens hash identifierar beräkningen före kritik. Ditt beslut binder den yttre förslagsbatchen inklusive hela granskningen.</p><code>{analysis.core_proposal_hash}</code>
    </details>
    <details><summary>Rollernas sparade versioner och bindningar</summary>{steps.map((step,i)=><div key={i}><p>{step.role_name}: version {step.role_version}</p><small>Input</small><code>{step.input_hash}</code><small>Output</small><code>{step.output_hash}</code></div>)}</details>
  </section>;
}

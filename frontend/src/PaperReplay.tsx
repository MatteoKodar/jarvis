import {useEffect,useRef,useState} from 'react';
import {money,date} from './format';
import exampleInput from '../../tests/fixtures/paper_input_v1.json';
import exampleResults from '../../tests/fixtures/paper_results_v1.json';

type Request=(path:string,body?:unknown,signal?:AbortSignal)=>Promise<unknown>;
type Proposal={event_id:string;book:string;outcome:string;paper_odds:number;stake_ore:number};
type Source={book:string;source_url:string;updated_at:string|null;age_seconds:number|null;fresh:boolean;reason:string|null};
type Quality={event_id:string;blocked_missing_time:boolean;captured_at:string|null;fresh_count:number;
  too_close_to_kickoff:boolean|null;sources:Source[]};
type Projection={proposal_count:number;total_stake_ore:number;declared_data_cost_ore:number;projected_available_ore:number};
type Review={version:string;dataset_id:string;origin:string;source:{name:string;reference_url:string;permission_note:string};
  input_hash:string;report_hash:string;notice:string;limitations:string[];interpretation:Record<string,string>;
  contract:{policy_hash:string;baseline_definition:Record<string,string>};quality:{records:Quality[]};
  candidates:Proposal[];proposals:Proposal[];baseline:Proposal[];findings:{event_id:string;code:string}[];
  money_before:Projection;primary_money:Projection;baseline_money:Projection;
  steps:{role_id:string;name:string;version:string;status:string;input_hash:string;output_hash:string}[];
  core_decisions:{event_id:string;available_capital_ore:number;decision:null|{checks:{book:string;accepted:boolean}[]}}[]};
type Track={summary:Record<string,number>;pending_count:number;void_count:number;roi_bp:number|null;results_without_bet:number};
type Evaluation={version:string;report_hash:string;notice:string;limitations:string[];primary:Track;baseline:Track;evaluation_hash:string};
const codeText:Record<string,string>={MISSING_TIME:'Saknad tid – avstår före analys.',FUTURE_QUOTE:'Offert efter angiven fångsttid.',
  STALE_QUOTE:'Offerten är äldre än den låsta gränsen.',DATA_BLOCKED:'Underlaget är blockerat.',UNKNOWN_SOURCE:'Okänd bok eller referens.',
  UNUSABLE_SOURCE:'En använd källa klarar inte kontrollerna.',REFERENCE_MISMATCH:'Referensmängden stämmer inte.',
  PRICE_MISMATCH:'Priset stämmer inte med den angivna offerten.',STAKE_MISMATCH:'Insatsen avviker från den låsta policyn.',CAPITAL_SHORTFALL:'Kapital saknas.'};
const reason=(code:string)=>codeText[code]??`Okänd kod: ${code}`;
const selectionLimit='En enskild fil kan inte skilja efterhandsurval från förhandsurval. 20 matcher är ett tekniskt batchtak, inget statistiskt underlag.';
const unsigned='Osignerad, öppna checksummor. Ingen verifierad förregistrering eller uppmätt vinstedge.';
const exportLimits=[selectionLimit,'Påhittade fångsttider på stängningsodds kan passera strukturella kontroller.',
  'Filer kan ändras och prövas om; exporten är vald av användaren och inget revisionssäkert arkiv.',
  'Datakostnader är manuellt deklarerade och behöver inte vara fullständiga.',
  'Ingen språkmodell, inga dataleverantörsanrop och inga riktiga insatser.'];

class SessionChanged extends Error {}

async function readJson(file:File,limit:number){
  if(file.size>limit)throw new Error(`Filen är för stor. Högst ${limit} byte tillåts.`);
  const bytes=new Uint8Array(await file.arrayBuffer());
  if(bytes[0]===239&&bytes[1]===187&&bytes[2]===191)throw new Error('UTF-8-BOM stöds inte. Spara JSON som UTF-8 utan BOM.');
  try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)) as unknown}
  catch{throw new Error('Filen måste innehålla giltig JSON kodad som UTF-8.')}
}

function TrackResult({title,track}:{title:string;track:Track}){
  return <article className="paper-track" data-testid={title==='Primär'?'paper-primary':'paper-baseline'}><h4>{title}</h4>
    <p>{track.summary.bet_count} insatser: {track.summary.won_count} vinster, {track.summary.lost_count} förluster, {track.void_count} makulerade, {track.pending_count} öppna.</p>
    <dl>{([['total_stake_ore','Insats'],['payout_ore','Utbetalning'],['game_profit_ore','Spelresultat'],['simulated_cost_ore','Deklarerad datakostnad'],['net_ore','Netto efter kostnad'],['capital_ore','Kapital inklusive öppna insatser'],['available_ore','Tillgängligt kapital'],['open_stake_ore','Öppen insats']] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{money(track.summary[key])}</dd></div>)}</dl>
    <p>ROI före datakostnad: {track.roi_bp===null?'saknas – öppna insatser eller ingen insats':(track.roi_bp/100).toLocaleString('sv-SE',{minimumFractionDigits:2})+' %'}.</p>
    <p>{track.results_without_bet} angivna resultat gäller matcher utan insats i detta spår.</p>
  </article>;
}

export function PaperReplay({request,systemState,mode}:{request:Request;systemState:string;mode:string}){
  const [input,setInput]=useState<unknown|null>(null),[results,setResults]=useState<unknown|null>(null);
  const [inputName,setInputName]=useState(''),[resultName,setResultName]=useState('');
  const [review,setReview]=useState<Review|null>(null),[evaluation,setEvaluation]=useState<Evaluation|null>(null);
  const [busy,setBusy]=useState(''),[error,setError]=useState('');
  const generation=useRef(0),controller=useRef<AbortController|null>(null);
  const reviewSession=useRef<string|null>(null);
  const locked=systemState!=='running'||mode!=='DEMO';
  function cancel(){generation.current++;controller.current?.abort();setBusy('');setError('');return generation.current}
  useEffect(()=>()=>{generation.current++;controller.current?.abort()},[]);
  useEffect(()=>{if(systemState!=='running'||mode!=='DEMO'){generation.current++;controller.current?.abort();setBusy('');setError('')}},[systemState,mode]);
  function clearInput(){const id=cancel();reviewSession.current=null;setInput(null);setResults(null);setReview(null);setEvaluation(null);setInputName('');setResultName('');return id}
  async function sessionToken(signal:AbortSignal){
    try{
      const session=await request('/session',undefined,signal) as {csrf?:unknown};
      if(typeof session?.csrf!=='string'||!session.csrf)throw new Error('Missing session');
      return session.csrf;
    }catch(e){if(signal.aborted)throw e;throw new SessionChanged('Ägarinloggningen kunde inte bekräftas. Filminnet har rensats; logga in och välj fil igen.')}
  }
  async function chooseInput(file?:File){
    const id=clearInput();if(!file)return;
    try{const data=await readJson(file,36000);if(id===generation.current){setInput(data);setInputName(file.name)}}
    catch(e){if(id===generation.current)setError((e as Error).message)}
  }
  async function chooseResults(file?:File){
    const id=cancel();setResults(null);setEvaluation(null);setResultName('');if(!file)return;
    try{const data=await readJson(file,9000);if(id===generation.current){setResults(data);setResultName(file.name)}}
    catch(e){if(id===generation.current)setError((e as Error).message)}
  }
  function loadExample(){clearInput();setInput(structuredClone(exampleInput));setInputName('Påhittat exempel · paper-input-v1.json')}
  function loadExampleResults(){cancel();setEvaluation(null);setResults(structuredClone(exampleResults));setResultName('Påhittade resultat · paper-results-v1.json')}
  async function calculate(kind:'review'|'evaluate'){
    if(locked||input===null||(kind==='evaluate'&&(!review||results===null)))return;
    const expected=review?.report_hash;
    const body=kind==='review'?{input}:{input,results,expected_report_hash:expected};
    const id=cancel();setEvaluation(null);
    if(kind==='review'){setReview(null);setResults(null);setResultName('')}
    if(new TextEncoder().encode(JSON.stringify(body)).length>48000){setError('Begäran är för stor. Högst 48000 byte får skickas.');return}
    const active=new AbortController();controller.current=active;setBusy(kind);
    try{
      const token=await sessionToken(active.signal);
      if(id!==generation.current)return;
      if(kind==='evaluate'&&reviewSession.current!==token)throw new SessionChanged('Ägarinloggningen ändrades. Granska filen igen efter inloggning.');
      let value:unknown;
      try{value=await request('/betting-demo/paper-replay/'+kind,body,active.signal)}
      catch(e){
        if(id!==generation.current||active.signal.aborted)return;
        if(await sessionToken(active.signal)!==token)throw new SessionChanged('Ägarinloggningen ändrades. Filminnet har rensats.');
        throw e;
      }
      if(id!==generation.current)return;
      if(await sessionToken(active.signal)!==token)throw new SessionChanged('Ägarinloggningen ändrades. Filminnet har rensats.');
      if(id!==generation.current)return;
      if(kind==='review'){
        const r=value as Review;
        if(r?.version!=='paper-review-v1'||!/^[0-9a-f]{64}$/.test(r.report_hash)||!Array.isArray(r.quality?.records)||!Array.isArray(r.steps))throw new Error('Okänd eller ofullständig rapportversion.');
        reviewSession.current=token;setReview(r);
      }else{
        const r=value as Evaluation;
        if(r?.version!=='paper-evaluation-v1'||r.report_hash!==expected)throw new Error('Utvärderingen matchar inte den aktuella granskningen.');
        setEvaluation(r);
      }
    }catch(e){if(id===generation.current&&!active.signal.aborted){if(e instanceof SessionChanged)clearInput();setError((e as Error).message)}}
    finally{if(id===generation.current)setBusy('')}
  }
  function download(){
    if(!review)return;
    const payload={version:'paper-export-v1',origin:review.origin,input_hash:review.input_hash,
      policy_hash:review.contract.policy_hash,report_hash:review.report_hash,input,review,
      results:evaluation?results:undefined,evaluation,notice:unsigned,limitations:exportLimits};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download=`paper-review-${review.dataset_id}-${review.report_hash.slice(0,12)}.json`;
    anchor.click();URL.revokeObjectURL(url);
  }
  function matchName(eventId:string){
    const data=input as {records?:{event_id?:string;home?:string;away?:string}[]}|null;
    const row=data?.records?.find(r=>r.event_id===eventId);
    return row?`${row.home} – ${row.away}`:eventId;
  }
  function decisionText(q:Quality){
    if(q.blocked_missing_time)return reason('MISSING_TIME');
    const finding=review?.findings.find(f=>f.event_id===q.event_id);if(finding)return reason(finding.code);
    if(review?.proposals.some(p=>p.event_id===q.event_id))return 'Förslag efter konsistenskontroll.';
    if(q.too_close_to_kickoff)return 'För nära avspark vid angiven fångsttid.';
    const core=review?.core_decisions.find(r=>r.event_id===q.event_id);
    if((core?.decision?.checks.filter(c=>c.accepted).length??0)<4)return 'Färre än fyra prisgodkända källor.';
    if((core?.available_capital_ore??0)<1000)return 'Låtsaskapitalet räcker inte.';
    return 'Ingen avvikelse klarar den låsta policyn.';
  }
  return <details className="panel paper-replay" data-testid="paper-replay"><summary>Granska egna matchdata och återspela med låtsaspengar</summary>
    <h3>Filgranskning · separat från sparade demo-omgångar</h3>
    <p>JSON-filer behandlas i minnet. Ingen språkmodell, hämtad källa eller riktig insats används. Inga affärs- eller demo-omgångar sparas av denna kontroll.</p>
    <p>{unsigned} {selectionLimit}</p>
    <p>Angivna tider och källor kan inte bevisa att ett pris faktiskt fanns före avspark. Filer kan ändras och prövas om; påhittade fångsttider kan passera kontrollerna.</p>
    <p>Deklarerade datakostnader kan vara ofullständiga; inga verkliga debiteringar utförs här.</p>
    <div className="paper-files"><label>Indata · paper-input-v1 · högst 36000 byte<input aria-label="Välj matchdata JSON" type="file" accept=".json,application/json" onChange={e=>{const file=e.target.files?.[0];e.target.value='';void chooseInput(file)}}/></label>
      <label>Separata resultat · paper-results-v1 · högst 9000 byte<input aria-label="Välj resultat JSON" type="file" accept=".json,application/json" disabled={!review} onChange={e=>{const file=e.target.files?.[0];e.target.value='';void chooseResults(file)}}/></label></div>
    <p data-testid="paper-file-state">{inputName||'Ingen indata vald.'}{resultName&&` · ${resultName}`}</p>
    <div className="betting-actions"><button onClick={loadExample}>Ladda påhittat fil-exempel</button>
      <button disabled={locked||!!busy||input===null} onClick={()=>void calculate('review')}>Granska filens underlag</button>
      {review?.origin==='synthetic_fixture'&&review.dataset_id==='synthetic-contract-v1'&&<button onClick={loadExampleResults}>Ladda påhittade resultat</button>}
      <button disabled={locked||!!busy||!review||results===null} onClick={()=>void calculate('evaluate')}>Utvärdera samma underlag</button>
      <button disabled={!review||!!busy} onClick={download}>Exportera filgranskning JSON</button></div>
    {locked&&<p>Återuppta demot för en ny beräkning. Sparade demo-omgångar påverkas inte.</p>}
    {busy&&<p role="status">{busy==='review'?'Granskar filens underlag…':'Räknar om samma indata och avräknar separat…'}</p>}
    {error&&<p role="alert" className="error">{error}</p>}
    {review&&<section aria-label="Importerad pappersgranskning" data-testid="paper-review"><h4>{review.dataset_id}</h4>
      <p><strong>Påstått ursprung:</strong> {review.origin==='synthetic_fixture'?'Påhittat exempel':'Manuellt angivet · ej oberoende verifierat'}.</p>
      <p>{review.source.name}. Referens, ej hämtad: <code>{review.source.reference_url}</code></p><p>Påstått tillstånd: {review.source.permission_note}</p>
      <p>{review.notice}</p><ul>{[...Object.values(review.interpretation),...review.limitations].map((text,i)=><li key={i}>{text}</li>)}</ul>
      <ol className="review-steps">{review.steps.map(step=><li key={step.role_id} data-testid={'paper-step-'+step.role_id}><strong>{step.name} · regelkontroll</strong>
        {step.role_id==='researcher'&&<p>{review.quality.records.length} matcher. {review.quality.records.filter(q=>q.blocked_missing_time).length} med saknad tid.</p>}
        {step.role_id==='analyst'&&<p>{review.candidates.length} grundförslag före kritik.</p>}
        {step.role_id==='finance'&&<p>Före kritik: {review.money_before.proposal_count} förslag, {money(review.money_before.total_stake_ore)} insats. Deklarerad kostnad {money(review.money_before.declared_data_cost_ore)}. Projicerat tillgängligt {money(review.money_before.projected_available_ore)}.</p>}
        {step.role_id==='critic'&&<p>Efter kritik: {review.proposals.length} förslag, {review.findings.length} borttagna. Projicerat tillgängligt {money(review.primary_money.projected_available_ore)}.</p>}
      </li>)}</ol>
      <div className="paper-quality">{review.quality.records.map(q=><details key={q.event_id} data-testid={'paper-quality-'+q.event_id}><summary>{matchName(q.event_id)} · {decisionText(q)}</summary>
        <p>Angiven fångsttid: {q.captured_at?date(q.captured_at):'saknas'}. Avsparksnärhet: {q.too_close_to_kickoff===null?'okänd':q.too_close_to_kickoff?'för nära':'klarar tidsgränsen enligt filen'}.</p>
        <p>{q.fresh_count} källposter klarar ålderskontrollen utifrån angivna tider. Detta är inte verifierad tillgänglighet.{q.blocked_missing_time&&' Ofullständiga tider blockerar hela matchen.'}</p>
        <table className="paper-source-table"><thead><tr><th>Källa / ej hämtad</th><th>Angiven tid / ålder</th><th>Kontroll</th></tr></thead><tbody>{q.sources.map(s=><tr key={s.book}><td>{s.book}<code>{s.source_url}</code></td><td>{s.updated_at?date(s.updated_at):'saknas'}<br/>{s.age_seconds===null?'okänd ålder':s.age_seconds+' s'}</td><td>{s.fresh?'Klarar angiven åldersgräns':reason(s.reason??'MISSING_TIME')}</td></tr>)}</tbody></table>
      </details>)}</div>
      <h4>Slutliga primärförslag · {review.proposals.length}</h4><ul>{review.proposals.map(p=><li key={p.event_id}>{matchName(p.event_id)}: {p.outcome==='home'?'1':p.outcome==='draw'?'X':'2'} hos {p.book}, odds {(p.paper_odds/10000).toFixed(4)}, insats {money(p.stake_ore)}.</li>)}</ul>
      <details><summary>Grundförslag och baslinjens definition</summary><p>{review.candidates.length} grundförslag. Baseline: {review.baseline.length} insatser i egen hypotetisk pott.</p><ul>{Object.values(review.contract.baseline_definition).map((text,i)=><li key={i}>{text}</li>)}</ul></details>
      <details><summary>Versioner och öppna innehållsbindningar</summary><p>{review.version}</p><code>{review.input_hash}</code><code>{review.contract.policy_hash}</code><code>{review.report_hash}</code></details>
    </section>}
    {evaluation&&<section aria-label="Pappersutvärdering" data-testid="paper-evaluation"><h4>Två separata hypotetiska potter</h4><p>{evaluation.notice}</p>
      <div className="paper-tracks"><TrackResult title="Primär" track={evaluation.primary}/><TrackResult title="Baseline · referens, aldrig rekommendation" track={evaluation.baseline}/></div>
      <ul>{evaluation.limitations.map((text,i)=><li key={i}>{text}</li>)}</ul></section>}
  </details>;
}

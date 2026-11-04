import {useEffect, useRef, useState} from 'react';
import {ArrowDownToLine, ArrowRight, Beaker, ChevronRight, FileText, Fingerprint, LockKeyhole, Play, RefreshCw, ShieldCheck} from 'lucide-react';
import './research-lab.css';

type Citation={source_id:string;quote:string;start_byte:number;end_byte:number};
type Claim={id:string;text:string;kind:string;essential:boolean;citations:Citation[]};
type Review={claims:{claim_id:string;status:string;reason:string}[];recommendation:string};
type Report={id:string;topic_id:string;flow:string;name:string;original:{claims:Claim[];recommendation:string;depends_on:string[]};review:Review|null;final:{recommendation:string;claims:Claim[];removed_ids:string[];missing_dependencies:string[];text:string;support_verified:boolean};steps:{role:string;kind:string;input:unknown;output:unknown}[]};
type RunSummary={id:string;created:string;stage:string;version:string;suite_hash:string;report_count:number;simulated_steps:number;external_calls:number;cost_ore:number};
type Run=RunSummary&{packages:{id:string;title:string;question:string;sources:{id:string;title:string;text:string;origin:string;synthetic:boolean}[]}[];reports:Report[]};
type Envelope={run:Run;sha256:string};
type Catalog={version:string;suite_hash:string;mode:string;state:string;topics:{id:string;title:string;question:string}[];runs:RunSummary[]};
type Props={request:(path:string,body?:unknown)=>Promise<unknown>;systemState:string;mode:string;resume:()=>Promise<void>};
const levels:Record<string,string>={avsta:'Avstå',vidare_research:'Vidare research',billigt_experiment:'Billigt experiment'};
const verdicts:Record<string,string>={stod:'Stöd enligt demoomdömet',indirekt:'Indirekt stöd',saknas:'Stöd saknas',motsagt:'Motsagt'};
const date=(value:string)=>new Intl.DateTimeFormat('sv-SE',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Stockholm'}).format(new Date(value));

export function ResearchLab({request,systemState,mode,resume}:Props){
 const [catalog,setCatalog]=useState<Catalog|null>(null),[saved,setSaved]=useState<Envelope|null>(null);
 const [topic,setTopic]=useState('A0-1'),[flow,setFlow]=useState('RK');
 const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const action=useRef<{action_id:string;suite_hash:string}|null>(null);
 const load=async()=>{const result=await request('/research-poc/a0') as Catalog;setCatalog(result);return result};
 useEffect(()=>{let active=true;request('/research-poc/a0').then(value=>{if(active)setCatalog(value as Catalog)}).catch(e=>{if(active)setError((e as Error).message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[request]);
 const operate=async(fn:()=>Promise<void>)=>{setBusy(true);setError('');try{await fn()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const start=()=>operate(async()=>{if(!catalog)return;if(!action.current)action.current={action_id:crypto.randomUUID(),suite_hash:catalog.suite_hash};const result=await request('/research-poc/a0/runs',action.current) as Envelope;setSaved(result);action.current=null;await load()});
 const open=(id:string)=>operate(async()=>{setSaved(await request('/research-poc/a0/runs/'+id) as Envelope)});
 const run=saved?.run,selected=run?.reports.find(r=>r.topic_id===topic&&r.flow===flow),material=run?.packages.find(p=>p.id===topic);
 if(loading)return <section className="panel" aria-busy="true">Hämtar Researchlabb…</section>;
 return <div className="research-lab">
  <section className="lab-intro panel">
   <div><span className="eyebrow">RESEARCH PROOF OF CONCEPT / A0</span><h2>Från påstående<br/>till prövbart underlag.</h2><p>Följ tre arbetsflöden, granska källutdrag och se hur ett omdöme ändrar slutresultatet.</p><span className="lab-simulation"><Beaker size={15}/> SIMULERADE SVAR · SYNTETISKA KÄLLOR</span></div>
   <div className="lab-start"><div className="lab-spec"><span><strong>03</strong>exempel</span><span><strong>09</strong>slutrapporter</span><span><strong>00</strong>externa anrop</span></div><button className="primary" disabled={!catalog||busy||mode!=='DEMO'||systemState!=='running'} onClick={start}><Play size={15}/>{busy?'Arbetar lokalt…':action.current?'Hämta samma A0-körning igen':'Kör lokal A0-demo'}</button><small>0,00 kr · 15 simulerade steg · inget modellanrop</small></div>
  </section>
  <div className="lab-stages" aria-label="Forskningsprototypens steg"><div className="current"><span>A0</span><div><strong>Pröva arbetsflödet</strong><small>Lokala, förutbestämda exempel</small></div><Beaker size={18}/></div><div><span>A1</span><div><strong>Jämför riktiga modeller</strong><small>Fast källpaket · inte körklart</small></div><LockKeyhole size={16}/></div><div><span>B</span><div><strong>Undersök verkliga källor</strong><small>Webbresearch · inte anslutet</small></div><LockKeyhole size={16}/></div></div>
  {mode!=='DEMO'&&<p className="notice">A0 är endast tillgängligt i DEMO. Labbet kan inte aktivera LIVE.</p>}
  {mode==='DEMO'&&systemState!=='running'&&<div className="notice lab-state"><ShieldCheck size={18}/><span>{systemState==='stopped'?'Nödstopp är aktivt.':'Systemet är pausat.'} Tidigare resultat kan läsas. Återuppta för att starta en ny lokal demonstration.</span><button disabled={busy} onClick={()=>operate(resume)}>Återuppta</button></div>}
  {error&&<p role="alert" className="error lab-error">{error}</p>}
  <div className="lab-workspace">
   <aside className="panel lab-library"><div className="panel-header"><h2>Demounderlag</h2><span className="badge amber">A0</span></div><p>Påhittade fall för att testa programmet. De är inga marknadsfynd.</p>
    <div className="lab-topic-list">{catalog?.topics.map((item,index)=><button key={item.id} className={topic===item.id?'active':''} onClick={()=>setTopic(item.id)} aria-pressed={topic===item.id}><span>0{index+1}</span><div><strong>{item.title}</strong><small>{item.question}</small></div><ChevronRight size={15}/></button>)}</div>
    <div className="lab-archive-heading"><h3>Sparade körningar</h3><button aria-label="Uppdatera körningslistan" className="text-button" disabled={busy} onClick={()=>operate(async()=>{await load()})}><RefreshCw size={15}/></button></div>
    {catalog?.runs.length?<div className="lab-run-list">{catalog.runs.map((item,index)=><button key={item.id} disabled={busy} aria-pressed={run?.id===item.id} onClick={()=>open(item.id)}><FileText size={15}/><span><strong>{date(item.created)}</strong><small>{item.report_count} rapporter · {item.id.slice(0,8)}{index===0?' · senaste':''}</small></span></button>)}</div>:<p className="lab-empty-note">Ingen A0-körning sparad ännu.</p>}
   </aside>
   <section className="panel lab-results" aria-label="A0-resultat">
    {!run||!selected||!material?<div className="lab-empty"><span className="lab-empty-icon"><Beaker size={34}/></span><span className="eyebrow">BÖRJA MED EN LOKAL DEMONSTRATION</span><h2>Gör granskningen synlig.</h2><p>Starta A0 för att se nio sparade rapporter, deras källor och vad som händer när ett avgörande påstående tas bort.</p><div><span>Ensam AI</span><ArrowRight size={16}/><span>Självgranskning</span><ArrowRight size={16}/><span>Researcher + Kritiker</span></div><small>Demonstrationen utser ingen vinnare och mäter inte AI-modellers kvalitet.</small></div>:<>
     <div className="lab-result-heading"><div><span className="eyebrow">SPARAD A0-KÖRNING / {material.id}</span><h2>{material.title}</h2><small>{date(run.created)} · {run.version}</small></div><a className="button lab-download" href={'/api/research-poc/a0/runs/'+run.id+'/export'} download><ArrowDownToLine size={15}/> Exportera körning</a></div>
     <div className="lab-flow-tabs" role="group" aria-label="Jämför arbetsflöden">{(['S1','S2','RK'] as const).map(key=><button key={key} aria-pressed={flow===key} className={flow===key?'active':''} onClick={()=>setFlow(key)}><small>{key}</small><span>{key==='S1'?'Ensam AI':key==='S2'?'Självgranskning':'Researcher + Kritiker'}</span></button>)}</div>
     <div className="lab-comparison"><div><small>URSPRUNGLIG BEDÖMNING</small><strong>{levels[selected.original.recommendation]}</strong><span>{selected.original.claims.length} påståenden</span></div><ArrowRight size={20}/><div><small>EFTER {selected.review?'DEMOOMDÖME':'ETT STEG'}</small><strong>{levels[selected.final.recommendation]}</strong><span>{selected.final.claims.length} kvar · {selected.final.removed_ids.length} borttagna</span></div></div>
     <p className="lab-caution">Omdömena är förutbestämda exempel, inte faktaverifiering. Ett av fallen innehåller medvetet en felaktig invändning från Kritikern.</p>
     <h3 className="lab-section-heading">Påståenden och spårbar granskning</h3>
     <div className="lab-claims">{selected.original.claims.map(claim=>{const review=selected.review?.claims.find(c=>c.claim_id===claim.id),removed=selected.final.removed_ids.includes(claim.id);return <article key={claim.id} className={removed?'lab-claim removed':'lab-claim'}><header><span className="badge">{claim.id}</span><span className="badge">{claim.kind==='observation'?'Observation':claim.kind==='hypotes'?'Hypotes':'Förslag'}</span>{claim.essential&&<span className="lab-essential">Bärande påstående</span>}</header><p>{claim.text}</p>{claim.citations.map((citation,i)=><details key={i}><summary>Källutdrag · {citation.source_id}</summary><blockquote>{citation.quote}</blockquote><small>UTF-8-byte {citation.start_byte}–{citation.end_byte} · exakt citat kontrollerat av programmet, betydelsen inte verifierad.</small></details>)}<div className="lab-verdict"><span className={'badge '+(removed?'amber':'')}>{review?verdicts[review.status]:'Ingen granskning i S1'}</span><strong>{removed?'Tas bort ur slutleveransen':'Kvar i slutleveransen'}</strong></div>{review&&<p className="lab-reason">{review.reason}</p>}</article>})}</div>
     <section className="lab-final" aria-label="Mekanisk slutleverans"><h3>Mekanisk slutleverans</h3><p>Byggd från kvarvarande påståenden. Ingen modell har skrivit om rapporten.</p><pre>{selected.final.text}</pre></section>
     <details className="lab-source-details"><summary>Källpaket · {material.sources.length} syntetiska texter</summary>{material.sources.map(source=><article key={source.id}><h4>{source.id} · {source.title}</h4><p>{source.text}</p><small>Ursprung: {source.origin} · påhittat demonstrationsmaterial</small></article>)}</details>
     <details className="lab-source-details"><summary>Exakta indata och utdata · {selected.steps.length} simulerade steg</summary><pre>{JSON.stringify(selected.steps,null,2)}</pre></details>
     <div className="lab-integrity"><Fingerprint size={17}/><div><strong>Sparad version och kontrollsumma</strong><small>{saved.sha256}</small><small>Kontrollerad mot databasposten vid läsning. Verifierar integritet, inte sanningshalt.</small></div></div>
    </>}
   </section>
  </div>
  <section className="panel lab-next"><span className="square-icon"><ShieldCheck size={17}/></span><div><h3>Nästa milstolpe: ett verkligt jämförelseförsök</h3><p>A1 kräver verifierade källpaket, fryst metod, säkra anropsgränser, aktuell prisprofil och ett uttryckligt ägarbeslut. Inga betalda funktioner kan startas härifrån.</p></div><span className="badge amber">A1 INTE KÖRKLART</span></section>
 </div>
}

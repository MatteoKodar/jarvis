import {useEffect, useRef, useState} from 'react';
import {ArrowRight, CheckCheck, CircleHelp, Flag, History, LockKeyhole, RefreshCw} from 'lucide-react';
import {money, date} from './format';
import './betting-demo.css';
import {ResearchEvidence,ReviewTrace,readableReview,DEMO_REVIEW_VERSION,type ReviewPayload} from './DemoReview';
import {PaperReplay} from './PaperReplay';

type Status = 'created'|'analyzed'|'no_bets'|'approved'|'declined'|'simulated'|'settled';
type Summary = {initial_capital_ore:number;game_profit_ore:number;simulated_cost_ore:number;net_ore:number;capital_ore:number;open_stake_ore:number;available_ore:number;total_stake_ore:number;payout_ore:number;bet_count:number;settled_count:number;won_count:number;lost_count:number};
type Header = {workflow_version?:string;id:string;state:Status;created_at:string;updated_at:string;scenario_version:string;rules_version:string;explanation_version:string;initial_capital_ore:number;stake_ore:number;summary:Summary};
type Proposal = {event_id:string;home:string;away:string;outcome:string;book:string;paper_odds:number;stake_ore:number;explanation:string};
type Analysis = ReviewPayload & {proposal_version:number;proposal_hash:string;total_stake_ore:number;simulated_cost_ore:number;proposals:Proposal[];matches:{event_id:string;simulated_analysis_at:string;explanation:string;notice:string;decision:{selected:boolean;reason:string;checks:{book:string;accepted:boolean;reason:string|null}[]}}[];messages:{role_id:string;notice:string;text:string}[]};
type Observation = {event_id:string;home:string;away:string;starts_at:string;captured_at:string;quotes:{book:string;updated_at:string;odds:{home:number;draw:number;away:number}}[]};
type Session = Header & {observations:Observation[];analysis:Analysis|null;decision:{value:string;recorded_at:string;proposal_version:number;proposal_hash:string}|null;costs:{event_id:string;cost_kind:string;amount_ore:number;recorded_at:string;simulated_at:string}[];bets:{event_id:string;state:string;stake_ore:number;paper_odds:number;outcome:string;return_ore?:number;profit_ore?:number}[];results?:{event_id:string;status:string;home_score:number;away_score:number;simulated_finished_at:string}[];history:{operation:string;to_state:Status;recorded_at:string}[]};
type Catalog = {sessions:Header[]};
type Pending = {path:string;body:Record<string,unknown>};
type Props = {request:(path:string,body?:unknown,signal?:AbortSignal)=>Promise<unknown>;systemState:string;mode:string;resume:()=>Promise<void>};
const PENDING_KEY = 'jarvis-betting-demo-pending-v1';
const SELECTED_KEY = 'jarvis-betting-demo-selected-v1';
const labels:Record<Status,string> = {created:'Omgång skapad',analyzed:'Analys sparad',no_bets:'Inga spel uppfyllde reglerna',approved:'Batchen godkänd',declined:'Du avstod från låtsasinsatserna',simulated:'Låtsasinsatserna är öppna',settled:'Omgången är avräknad'};
const outcomes:Record<string,string> = {home:'1 · Hemmaseger',draw:'X · Oavgjort',away:'2 · Bortaseger'};

function storedPending():{pending:Pending|null;blocked:boolean} {
  try {
    const value = JSON.parse(sessionStorage.getItem(PENDING_KEY) || 'null') as Pending|null;
    if(value===null)return {pending:null,blocked:false};
    if (value && /^\/betting-demo\/sessions(?:\/[a-f0-9]{32}\/(?:analyze|decision|simulate|settle))?$/.test(value.path)
        && typeof value.body?.action_id === 'string') return {pending:value,blocked:false};
  } catch { /* An unreadable store is not evidence that no request is pending. */ }
  return {pending:null,blocked:true};
}

function pendingSessionId(item:Pending|null) {
  return item?.path.match(/^\/betting-demo\/sessions\/([a-f0-9]{32})\//)?.[1];
}

export function BettingDemo({request,systemState,mode,resume}:Props) {
  const [catalog,setCatalog] = useState<Catalog>({sessions:[]});
  const [session,setSession] = useState<Session|null>(null);
  const [initialStorage] = useState(storedPending);
  const [pending,setPending] = useState<Pending|null>(initialStorage.pending);
  const [storageBlocked,setStorageBlocked] = useState(initialStorage.blocked);
  const [confirmedId,setConfirmedId] = useState<string|null>(null);
  const pendingRef = useRef(pending);
  const selected = useRef<string|null>(null);
  const working = useRef(false);
  const [busy,setBusy] = useState(false), [loading,setLoading] = useState(true), [error,setError] = useState('');
  const mounted = useRef(true);

  const load = async (id?:string) => {
    const list = await request('/betting-demo/sessions') as Catalog;
    const preferred = id || selected.current;
    const found = list.sessions.find(s=>s.id===preferred)?.id;
    if(id&&!found)throw new Error('Den bekräftade eller valda omgången saknas i det sparade läget. Försök hämta samma omgång igen.');
    const chosen = found || list.sessions[0]?.id;
    const data = chosen ? await request('/betting-demo/sessions/'+chosen) as Session : null;
    if(chosen&&data?.id!==chosen)throw new Error('Fel omgång hämtades. Försök hämta samma omgång igen.');
    if (!mounted.current) return;
    selected.current = chosen || null;
    try { if(chosen)sessionStorage.setItem(SELECTED_KEY,chosen); } catch { /* Backend history remains available. */ }
    setCatalog(list); setSession(data);
  };

  useEffect(()=>{
    mounted.current = true;
    try { selected.current = sessionStorage.getItem(SELECTED_KEY); } catch { /* Use latest saved session. */ }
    if(mode==='DEMO')void load().catch(e=>{if(mounted.current)setError((e as Error).message)}).finally(()=>{if(mounted.current)setLoading(false)});
    else setLoading(false);
    return ()=>{mounted.current=false};
  },[request,mode]);

  const forget = (item:Pending|null) => {
    if(!mounted.current || !item || pendingRef.current!==item)return false;
    try {
      const stored=sessionStorage.getItem(PENDING_KEY);
      if(stored!==null){
        if(stored!==JSON.stringify(item))return false;
        sessionStorage.removeItem(PENDING_KEY);
      }
    }catch{return false}
    pendingRef.current=null; setPending(null);
    setConfirmedId(null);
    return true;
  };
  const perform = async () => {
    if(working.current || !pendingRef.current)return;
    if(confirmedId){await read(undefined,true);return}
    working.current=true; setBusy(true); setError('');
    let acknowledged=false;
    try {
      const item=pendingRef.current;
      const response=await request(item.path,item.body) as {id:string};
      acknowledged=true;setConfirmedId(response.id);
      selected.current=response.id;
      await load(response.id);
      if(!forget(item)&&mounted.current)setError('Backend har bekräftat begäran, men webbläsaren kan inte rensa den sparade återförsöksposten. Nya åtgärder är spärrade tills posten kan rensas.');
    } catch(e) {
      setError(acknowledged
        ? 'Backend har bekräftat begäran, men det sparade läget kunde inte hämtas. Uppdatera läget innan du fortsätter.'
        : (e as Error).message);
      // Unknown POST outcomes retain their exact request. A read never retries a POST.
      if(!acknowledged)await load().catch(()=>undefined);
    } finally {working.current=false;setBusy(false)}
  };
  const send = (path:string,body:Record<string,unknown>={}) => {
    if(working.current || pendingRef.current || storageBlocked)return;
    const item={path,body:{...body,action_id:crypto.randomUUID()}};
    try { sessionStorage.setItem(PENDING_KEY,JSON.stringify(item)); }
    catch {setError('Webbläsaren kan inte bevara återförsöket. Ingen begäran skickades. Tillåt sessionslagring för denna sida.');return}
    pendingRef.current=item;setPending(item);void perform();
  };
  const read = async (id?:string,clear=false) => {
    if(working.current)return;
    if(clear&&!confirmedId&&!pendingSessionId(pendingRef.current)){setError('Hämta det tidigare svaret med samma begäran innan återförsöksposten kan rensas.');return}
    working.current=true;setBusy(true);setError('');
    try {
      if(storageBlocked){
        const stored=storedPending();
        setStorageBlocked(stored.blocked);
        if(stored.blocked)setError('Den sparade begäran kan fortfarande inte läsas. Inga nya åtgärder tillåts.');
        else {pendingRef.current=stored.pending;setPending(stored.pending);setConfirmedId(null)}
      }
      const item=pendingRef.current;
      await load(confirmedId || pendingSessionId(item) || id || undefined);
      if(clear&&!forget(item)&&mounted.current)setError('Webbläsaren kan inte rensa den sparade begäran. Den finns kvar och nya åtgärder är spärrade.');
    }catch(e){setError((e as Error).message)}finally{working.current=false;setBusy(false)}
  };
  const bound = session?.analysis ? {proposal_version:session.analysis.proposal_version,proposal_hash:session.analysis.proposal_hash} : {};
  const write = (operation:string,body:Record<string,unknown>={}) => {if(session)send(`/betting-demo/sessions/${session.id}/${operation}`,body)};
  const locked = busy || !!pending || storageBlocked || systemState!=='running' || mode!=='DEMO';
  const terminal = session && ['no_bets','declined','settled'].includes(session.state);
  const unsupportedReview=!!session&&session.workflow_version!==undefined&&session.workflow_version!==DEMO_REVIEW_VERSION;
  const incompleteReview=session?.workflow_version===DEMO_REVIEW_VERSION&&!!session.analysis&&!readableReview(session.analysis);
  const writeLocked=locked||unsupportedReview||!!incompleteReview;

  if(mode!=='DEMO')return <section className="panel">Bettingdemot kräver DEMO. Riktiga spel är avstängda.</section>;
  if(loading)return <section className="panel">Läser sparade demo-omgångar…</section>;
  return <div className="betting-demo">
    <section className="panel betting-hero">
      <div><span className="eyebrow">DEMO UNDER UTVECKLING</span><h2>Från odds till avräkning.</h2><p>Sju påhittade matcher. Ett beslut för hela batchen. Följ låtsaspengarna genom varje steg.</p><div className="betting-chips"><span className="badge amber">Påhittade matcher och odds</span><span className="badge"><LockKeyhole size={12}/> Inga riktiga spel</span></div></div>
      <div><Flag size={30} aria-hidden="true"/><strong>Eget låtsaskapital för denna omgång.</strong><p>1 000 kr vid start · 10 kr per föreslaget spel.<br/>Ingen gemensam plånbok eller överföring.</p><button className="primary" disabled={locked} onClick={()=>send('/betting-demo/sessions')}>{session?'Skapa ny demo-omgång':'Skapa demo-omgång'} <ArrowRight size={15}/></button></div>
    </section>
    {error&&<div className="error-banner" role="alert">{error}</div>}
    {storageBlocked&&<section className="panel betting-retry" aria-label="Lagringskontroll krävs"><h3>Den sparade begäran kan inte kontrolleras.</h3><p>Backendhistoriken går att läsa, men nya åtgärder är spärrade eftersom en tidigare begäran kan finnas kvar. En lagringskontroll skickar ingen begäran på nytt.</p><button disabled={busy} onClick={()=>void read()}>Kontrollera sessionslagringen</button></section>}
    {pending&&<section className="panel betting-retry" aria-label={confirmedId?'Bekräftad begäran':'Osäker begäran'}><h3>{confirmedId?'Backend har bekräftat begäran.':'Begäran kan redan ha sparats.'}</h3><p>{confirmedId?`Åtgärden är sparad för omgång ${confirmedId.slice(0,8)}. Det visade läget kan vara inaktuellt. Nya åtgärder är spärrade tills denna omgång har hämtats och återförsöksposten har rensats.`:pendingSessionId(pending)?'Samma åtgärds-ID och innehåll finns kvar även efter omladdning. Kontrollera sparat läge för begärans omgång innan du stänger begäran, eller försök samma begäran igen.':'Samma åtgärds-ID och innehåll finns kvar även efter omladdning. Sparat läge går att läsa, men för att häva spärren måste du försöka samma begäran igen och hämta det tidigare svaret.'}</p><div className="betting-actions">{!confirmedId&&<button disabled={busy} onClick={()=>void perform()}>Försök samma begäran igen</button>}<button disabled={busy} onClick={()=>void read()}>Hämta sparat läge</button><button disabled={busy||(!confirmedId&&!pendingSessionId(pending))} onClick={()=>void read(undefined,true)}>Stäng begäran efter kontroll</button></div></section>}
    {systemState!=='running'&&<section className="panel betting-paused"><p>{systemState==='stopped'?'Nödstopp är aktivt.':'Arbetet är pausat.'} Sparade omgångar går att läsa. Nya åtgärder kräver att du återupptar.</p><button disabled={busy} onClick={()=>{setError('');void resume().catch(e=>setError((e as Error).message))}}>Återuppta demot</button></section>}
    <PaperReplay request={request} systemState={systemState} mode={mode}/>
    <div className="betting-layout"><aside className="panel betting-history"><h3><History size={17}/> Sparade omgångar</h3><p>Varje rad har sitt eget kapital. Historiken summeras inte till en plånbok.</p>{catalog.sessions.length===0?<p>Ingen omgång skapad ännu.</p>:catalog.sessions.map((s,i)=><button key={s.id} disabled={busy||!!pending} className={s.id===session?.id?'selected':''} onClick={()=>void read(s.id)}><strong>Omgång {catalog.sessions.length-i}</strong><span>{labels[s.state]}</span><small>{date(s.created_at)}</small><small>{money(s.summary.available_ore)} tillgängligt i denna omgång</small></button>)}</aside>
      <div className="betting-content">{!session?<section className="panel betting-empty"><Flag size={34}/><h3>Börja med en ny demo-omgång.</h3><p>Ingenting skapas bara av att öppna sidan. Demot körs direkt i backend och behöver ingen worker eller extern AI.</p></section>:<>
        <section className="panel betting-progress"><div className="betting-section-title"><div><span className="eyebrow">OMGÅNG {session.id.slice(0,8)}</span><h3 aria-live="polite">{labels[session.state]}</h3></div><button disabled={busy} onClick={()=>void read()} aria-label="Uppdatera sparat demoläge"><RefreshCw size={16}/></button></div><ol>{['Skapa','Analysera','Besluta','Registrera insatser','Avräkna'].map((step,i)=><li key={step} className={i <= ({created:0,analyzed:1,no_bets:1,approved:2,declined:2,simulated:3,settled:4}[session.state])?'reached':''}><span>{i+1}</span>{step}</li>)}</ol><p>Simulerade matchtider hålls skilda från verkliga registreringstider. Ingen bakgrundsprocess eller extern språkmodell kör denna demo.</p></section>
        <section className="panel betting-capital" aria-label="Omgångens låtsaskapital"><h3>Eget låtsaskapital för denna omgång.</h3><div className="betting-money">{([['available_ore','Tillgängligt kapital'],['open_stake_ore','Öppen insats'],['capital_ore','Kapital inklusive öppna insatser'],['game_profit_ore','Spelresultat'],['simulated_cost_ore','Simulerade kostnader'],['net_ore','Netto efter kostnader']] as const).map(([key,label])=><article key={key}><small>{label}</small><strong data-testid={'demo-'+key}>{money(session.summary[key])}</strong></article>)}</div><details><summary>Så stäms pengarna av</summary><p>Spelresultat = avgjorda utbetalningar − deras insatser. Netto = spelresultat − simulerade kostnader. Kapital inklusive öppna insatser = startkapital + netto. Tillgängligt kapital = detta kapital − öppna insatser.</p><p>Startkapital {money(session.initial_capital_ore)}. Registrerade insatser {money(session.summary.total_stake_ore)}. Avräknad utbetalning {money(session.summary.payout_ore)}. Alla belopp beräknas i heltalsören. Vinstutbetalning avrundas nedåt till ören; det effektiva oddset får inget andra prisavdrag.</p></details></section>
        <ReviewTrace workflowVersion={session.workflow_version} analysis={session.analysis}/>
        <section className="panel betting-next">
          {session.state==='created'&&<><h3>Granska underlaget och analysera.</h3><p>Inga kostnader eller insatser är ännu bokförda. När analysen sparas bokförs 20 simulerade öre för var och en av de sju matcherna, totalt 1,40 kr.</p><button className="primary" disabled={writeLocked} onClick={()=>write('analyze')}>Analysera de sju matcherna <ArrowRight size={15}/></button></>}
          {session.state==='analyzed'&&<><h3>Ett beslut för hela förslagsbatchen.</h3><p>{session.analysis?.proposals.length} förslag à {money(session.stake_ore)}. Total insats <strong>{money(session.analysis?.total_stake_ore||0)}</strong>. Analyskostnaden {money(session.summary.simulated_cost_ore)} är redan bokförd och kvarstår om du avstår. Godkännande registrerar ännu inga insatser.</p><div className="betting-actions"><button className="primary" disabled={writeLocked} onClick={()=>write('decision',{...bound,decision:'approved'})}><CheckCheck size={15}/> Godkänn hela låtsasbatchen <span aria-hidden="true" data-testid="approve-batch-total">{money(session.analysis?.total_stake_ore||0)}</span></button><button disabled={writeLocked} onClick={()=>write('decision',{...bound,decision:'declined'})}>Avstå från batchen</button></div></>}
          {session.state==='approved'&&<><h3>Godkänd batch. Inga insatser registrerade ännu.</h3><p>Backend kontrollerar kapital för hela batchen i samma transaktion. Antingen registreras alla insatser eller ingen.</p><button className="primary" disabled={writeLocked} onClick={()=>write('simulate',bound)}>Registrera låtsasinsatser</button></>}
          {session.state==='simulated'&&<><h3>Insatserna är öppna.</h3><p>{money(session.summary.open_stake_ore)} är bundna. De syntetiska resultaten är ännu inte visade eller avräknade. Nästa steg avgör hela omgången samtidigt.</p><button className="primary" disabled={writeLocked} onClick={()=>write('settle')}>Visa och avräkna simulerade resultat</button></>}
          {terminal&&<><span className="eyebrow">SAMMANFATTNING</span><h3>{labels[session.state]}</h3><p>{session.state==='settled'?`${session.summary.won_count} vinster och ${session.summary.lost_count} förluster. Slutkapital ${money(session.summary.capital_ore)} efter ${money(session.summary.simulated_cost_ore)} i simulerade kostnader.`:session.state==='declined'?'Inga insatser registrerades. Den sparade analysens simulerade kostnader kvarstår.':'Inga förslag klarade de frysta reglerna. Inga insatser registrerades; analyskostnaderna kvarstår.'}</p><p>Att läsa sammanfattningen ändrar inget. En ny omgång får ett separat startkapital och behåller denna historik.</p></>}
        </section>
        {session.analysis&&<section className="panel betting-proposals"><h3>Den sparade förslagsbatchen</h3>{session.analysis.proposals.length===0?<p>Inga spelförslag.</p>:<div className="betting-table"><table><thead><tr><th>Match</th><th>Utfall</th><th>Effektivt odds</th><th>Fast insats</th></tr></thead><tbody>{session.analysis.proposals.map(p=><tr key={p.event_id}><td>{p.home} – {p.away}</td><td>{outcomes[p.outcome]}</td><td>{(p.paper_odds/10000).toFixed(4)}</td><td>{money(p.stake_ore)}</td></tr>)}</tbody></table></div>}<details><summary>Beslutsbindning och begränsningar</summary><p>Förslagsversion {session.analysis.proposal_version}. Hashen binder exakt det sparade underlaget och förklaringarna; den bevisar inte att odds eller resultat är verkliga.</p><code>{session.analysis.proposal_hash}</code>{session.decision&&<p>Ägarbeslut {session.decision.value==='approved'?'godkänt':'avstått'}, registrerat {date(session.decision.recorded_at)}.</p>}<p>Medianen av andra källors normaliserade priser är en marknadsreferens, ingen verifierad sannolikhet. Käll-ID:n är inte oberoende källfamiljer.</p></details></section>}
        <section className="panel betting-matches"><h3>Sju påhittade matcher och odds</h3><div className="betting-match-list">{session.observations.map(o=>{const a=session.analysis?.matches.find(m=>m.event_id===o.event_id);const b=session.bets.find(v=>v.event_id===o.event_id);const result=session.results?.find(r=>r.event_id===o.event_id);return <article key={o.event_id} className="betting-match"><header><strong>{o.home} – {o.away}</strong><span className="badge">{b?.state==='won'?'Vinst':b?.state==='lost'?'Förlust':b?.state==='open'?'Öppen låtsasinsats':a?(a.decision.selected?'Spelförslag':'Avstå'):'Ej analyserad'}</span></header><small>Simulerad avspark {date(o.starts_at)} · 1X2 efter ordinarie tid</small>{a&&<><p className="betting-agent-label">{a.notice}</p><p>{a.explanation}</p></>}{a&&session.workflow_version===DEMO_REVIEW_VERSION&&session.analysis?.review_version===DEMO_REVIEW_VERSION&&<ResearchEvidence packet={session.analysis.research?.packets?.find(p=>p.event_id===o.event_id)}/>}{result&&<p className="betting-result"><strong>Simulerat resultat {result.home_score}–{result.away_score}</strong>{b&&<> · utbetalning {money(b.return_ore||0)} · spelresultat {money(b.profit_ore||0)}</>}</p>}<details><summary>Visa odds och offertkontroller</summary><p>Simulerad fångsttid {date(o.captured_at)}. Effektiva odds i förslagen innehåller ett prisavdrag på 1 %.</p><div className="betting-table"><table><thead><tr><th>Källa</th><th>1</th><th>X</th><th>2</th><th>Offerttid</th></tr></thead><tbody>{o.quotes.map(q=><tr key={q.book}><td>{q.book}</td><td>{(q.odds.home/10000).toFixed(4)}</td><td>{(q.odds.draw/10000).toFixed(4)}</td><td>{(q.odds.away/10000).toFixed(4)}</td><td>{date(q.updated_at)}</td></tr>)}</tbody></table></div>{a&&<ul>{a.decision.checks.map(c=><li key={c.book}>{c.book}: {c.accepted?'Godtagen för prisberäkning':c.reason}</li>)}</ul>}</details></article>})}</div></section>
        {session.analysis&&<section className="panel betting-agent-notes"><h3>Simulerade agentsvar</h3>{session.analysis.messages.map(m=><article key={m.role_id}><strong>{m.role_id==='finance'?'Ekonom / Risk':'Kritiker / Kvalitetskontroll'}</strong><small>{m.notice}</small><p>{m.text}</p></article>)}</section>}
        <section className="panel betting-audit"><details><summary>Registreringshistorik och versioner</summary><p>{session.scenario_version} · {session.rules_version} · {session.explanation_version}</p><ol>{session.history.map(h=><li key={h.operation}>{date(h.recorded_at)} — {labels[h.to_state]}</li>)}</ol><p>Detta är verkliga registreringstider. Matchernas simulerade tider visas separat.</p></details></section>
      </>}</div>
    </div>
    <div className="betting-disclaimer"><CircleHelp size={20}/><p>Alla matcher, odds, agentsvar och kostnader är simulerade. Demot körs lokalt utan worker och externa AI-anrop. Ett positivt utfall visar arbetsflödet, aldrig bevisad lönsamhet. Demokapitalet påverkar inte JARVIS AI-budget.</p></div>
  </div>;
}

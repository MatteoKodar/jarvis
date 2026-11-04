import React, { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { LayoutDashboard, Users, MessageSquare, CheckCheck, Compass, Kanban, Wallet, Files, History, Settings, Play, Pause, Square, ArrowUpRight, ArrowRight, ChevronRight, Activity, Radio, ShieldCheck, X, Send, Download, Search, LogOut, Menu, Cpu, CircleHelp, AlertTriangle, Beaker, BookOpen } from 'lucide-react';
import type { State, Agent, Task, Proposal } from './types';
import './style.css';
import { Schedule } from './Schedule';
import { OddsLab } from './OddsLab';
import { request as api, setCsrfToken } from './api';
import { date, money } from './format';
import { Modal } from './components/Modal';
import { TaskDetails } from './components/TaskDetails';
import { DocumentLibrary } from './documents/DocumentLibrary';
import { useNavigation, type Page } from './navigation';
const statuses: Record<string, string> = {
  queued: 'Planerad',
  running: 'Pågår',
  approval: 'Väntar på godkännande',
  review: 'Granskning',
  done: 'Klar',
  blocked: 'Blockerad',
  pending: 'Väntar på beslut',
  approved: 'Godkänt · köat',
  rejected: 'Avslaget',
  changes: 'Ändring begärd',
  superseded: 'Ersatt version',
  paused: 'Pausat',
  stopped: 'Nödstoppat',
  active: 'Aktivt',
  closed: 'Avslutat'
};
const nav = [['Översikt', LayoutDashboard], ['Agentteam', Users], ['Chatta med JARVIS', MessageSquare], ['Förslag & beslut', CheckCheck], ['Oddslabb', Activity], ['Projekt & uppgifter', Kanban], ['Ekonomi', Wallet], ['Filer', Files], ['Dokument', BookOpen], ['Historik', History], ['Inställningar', Settings]] as const;
function Badge({
  children,
  tone = ''
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={'badge ' + tone}>{children}</span>;
}
function Empty({
  children
}: {
  children: ReactNode;
}) {
  return <div className="empty"><Compass size={26} /><p>{children}</p></div>;
}
function App() {
  const {
    route,
    navigate
  } = useNavigation();
  const page = route.page;
  const [authenticated, setAuthenticated] = useState(false),
    [checking, setChecking] = useState(true),
    [password, setPassword] = useState('');
  const [firstRun, setFirstRun] = useState(false),
    [confirmPassword, setConfirmPassword] = useState('');
  const [data, setData] = useState<State | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [connected, setConnected] = useState(false),
    [mobile, setMobile] = useState(false);
  const [agent, setAgent] = useState<Agent | null>(null),
    [task, setTask] = useState<Task | null>(null),
    [round, setRound] = useState(false),
    [goal, setGoal] = useState(''),
    [cap, setCap] = useState('5'),
    [chat, setChat] = useState(''),
    [filter, setFilter] = useState('');
  const [decision, setDecision] = useState<{
      p: Proposal;
      value: string;
    } | null>(null),
    [note, setNote] = useState(''),
    [edit, setEdit] = useState<Proposal | null>(null),
    [editTitle, setEditTitle] = useState('');
  const [manual, setManual] = useState(false),
    [amount, setAmount] = useState(''),
    [reconcile, setReconcile] = useState<string | null>(null);
  const [limits, setLimits] = useState<Record<string, string>>({});
  const [roundAction, setRoundAction] = useState(''),
    [costAction, setCostAction] = useState('');
  const refresh = async () => {
    const s = await api<State>('/state');
    setData(s);
    return s;
  };
  useEffect(() => {
    api<{
      csrf: string;
    }>('/session').then(s => {
      setCsrfToken(s.csrf);
      setAuthenticated(true);
    }).catch(async () => {
      const setup = await api<{
        needed: boolean;
        allowed: boolean;
      }>('/setup');
      setFirstRun(setup.needed && setup.allowed);
    }).catch(e => setError(e.message)).finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    refresh().catch(e => setError(e.message));
    const stream = new EventSource('/api/events');
    stream.onopen = () => setConnected(true);
    stream.onerror = () => setConnected(false);
    stream.addEventListener('update', () => refresh().catch(() => setConnected(false)));
    const poll = setInterval(() => refresh().catch(() => setConnected(false)), 8000);
    return () => {
      stream.close();
      clearInterval(poll);
    };
  }, [authenticated]);
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError('');
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const go = (p: Page) => {
    navigate(p);
    setFilter('');
    setMobile(false);
  };
  const submitLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (firstRun && password !== confirmPassword) {
      setError('Lösenorden matchar inte.');
      return;
    }
    setBusy(true);
    try {
      const s = await api<{
        csrf: string;
      }>(firstRun ? '/setup' : '/login', {
        password
      });
      setCsrfToken(s.csrf);
      setPassword('');
      setAuthenticated(true);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (checking) return <div className="loading">JARVIS <span>Kontrollerar anslutning…</span></div>;
  if (!authenticated) return <main className="login"><div className="login-art"><div className="brand-mark">J</div><span className="eyebrow">FOOTBALL RESEARCH / CONTROL CENTER</span><h1>Fotboll.<br /><em>Belägg före insats.</em></h1><p>Tio specialister. Ett gemensamt mål.<br />Du behåller kontrollen över varje viktigt beslut.</p><div className="login-chips"><Badge>10 fasta roller</Badge><Badge>Budgetspärr</Badge><Badge>Ägarbeslut</Badge></div></div><form onSubmit={submitLogin} className="login-form"><ShieldCheck size={32} className="cyan" /><h2>Välkommen till JARVIS</h2><p>{firstRun ? 'Första starten: välj ditt ägarlösenord, minst 12 tecken.' : 'Logga in till din kontrollcentral.'}</p><label>Ägarlösenord<input type="password" minLength={firstRun ? 12 : 1} maxLength={256} autoComplete={firstRun ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} required autoFocus /></label>{firstRun && <label>Upprepa lösenordet<input type="password" autoComplete="new-password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} minLength={12} maxLength={256} required /></label>}<button className="primary" disabled={busy}>{firstRun ? 'Skapa konto och öppna' : 'Öppna kontrollcentralen'} <ArrowRight size={17} /></button>{error && <p role="alert" className="error">{error}</p>}<small>{firstRun ? 'Lösenordet sparas skyddat på din dator. Inget standardlösenord används.' : <>Glömt lösenordet? Återställ lokalt med <code>python -m jarvis.cli owner</code>.</>}</small></form></main>;
  if (!data) return <div className="loading">{error || 'Hämtar kontrollcentralen…'}</div>;
  const d = data,
    b = d.settings,
    pending = d.proposals.filter(p => p.status === 'pending'),
    working = d.tasks.filter(t => t.status === 'running').length;
  const openRound = () => {
    setGoal(b.goal);
    setCap(String(b.per_task / 100));
    setRoundAction(crypto.randomUUID());
    setRound(true);
  };
  const selectedAgent = agent ? d.agents.find(a => a.id === agent.id) || agent : null;
  const selectedTask = task ? d.tasks.find(t => t.id === task.id) || task : null;
  const control = (state: string) => act(() => api('/control', {
    state
  }));
  const taskList = (items: Task[]) => items.length ? <div className="task-list">{items.map(t => <button key={t.id} className="task-row" onClick={() => setTask(t)}><span className={'task-dot ' + t.status} /><span><strong>{t.title}</strong><small>{d.agents.find(a => a.id === t.agent_id)?.name} · {date(t.created)}</small></span><Badge>{statuses[t.status]}</Badge><ChevronRight size={16} /></button>)}</div> : <Empty>Inga uppgifter här ännu. Starta en avgränsad arbetsomgång.</Empty>;
  const proposalCard = (p: Proposal) => <article className="proposal-card" key={p.id}><div className="row"><Badge tone={p.status === 'pending' ? 'amber' : ''}>{statuses[p.status]}</Badge><small>VERSION {p.version}</small></div><h3>{p.payload.title}</h3><p>{p.payload.purpose}</p><dl><dt>Ansvarig</dt><dd>{d.agents.find(a => a.id === p.payload.agent_id)?.name}</dd><dt>Mål</dt><dd>{p.payload.target}</dd><dt>Innehåll</dt><dd>{p.payload.content}</dd><dt>Färdigkriterier</dt><dd>{p.payload.criteria}</dd><dt>Kostnadstak</dt><dd>{money(p.payload.cap)} arbete + {money(p.payload.review_cap)} granskning</dd><dt>Risker</dt><dd>{p.payload.risks}</dd><dt>Alternativ</dt><dd>{p.payload.alternatives}</dd><dt>Vid godkännande</dt><dd>{p.payload.effect}</dd><dt>Giltigt till</dt><dd>{date(p.expires)}</dd></dl><button className="text-button" onClick={() => setTask(d.tasks.find(t => t.id === p.task_id) || null)}>Visa uppgift och underlag <ArrowUpRight size={15} /></button>{p.note && <p className="notice">Ägarkommentar: {p.note}</p>}{p.status === 'pending' && <div className="actions"><button disabled={busy || new Date(p.expires) < new Date()} className="primary" onClick={() => {
        setNote('');
        setDecision({
          p,
          value: 'approved'
        });
      }}>Godkänn</button><button disabled={busy} onClick={() => {
        setNote('');
        setDecision({
          p,
          value: 'changes'
        });
      }}>Begär ändring</button><button disabled={busy} className="danger-text" onClick={() => {
        setNote('');
        setDecision({
          p,
          value: 'rejected'
        });
      }}>Avslå</button></div>}{p.status === 'changes' && <button onClick={() => {
      setEdit(p);
      setEditTitle(p.payload.title);
      setCap(String(p.payload.cap / 100));
    }}>Skapa reviderad version</button>}</article>;
  return <div className="shell"><aside className={mobile ? 'sidebar open' : 'sidebar'}><a className="brand" href="#" onClick={e => {
        e.preventDefault();
        go('Översikt');
      }}><span className="brand-mark">J</span><span>JARVIS<small>FOOTBALL RESEARCH</small></span></a><div className="workspace-tag"><span className="tiny-orbit" /> Din kontrollcentral <Badge>V1.0</Badge></div><span className="nav-label">ARBETSYTA</span><nav>{nav.map(([name, Icon], i) => <React.Fragment key={name}>{name === 'Ekonomi' && <span className="nav-label secondary-label">SYSTEM</span>}<button className={page === name ? 'nav-item selected' : 'nav-item'} onClick={() => go(name)}><Icon size={18} /><span>{name}</span>{name === 'Förslag & beslut' && pending.length > 0 && <b className="count">{pending.length}</b>}</button></React.Fragment>)}</nav><div className="sidebar-bottom"><div className="safe-box"><ShieldCheck size={18} /><div><strong>Du har sista ordet</strong><small>Externa handlingar avstängda</small></div></div><button className="profile" onClick={() => act(async () => {
          await api('/logout', {});
          setAuthenticated(false);
          setData(null);
        })}><span className="avatar">Ä</span><span>Ägare<small>Lokal arbetsyta</small></span><LogOut size={16} /></button></div></aside>
 <div className="main-wrap"><header className="topbar"><button className="mobile-toggle" aria-label="Öppna meny" onClick={() => setMobile(!mobile)}><Menu size={20} /></button><div className="breadcrumbs">Arbetsyta <ChevronRight size={14} /><strong>{page}</strong></div><div className="top-status"><Badge tone={d.mode === 'DEMO' ? 'amber' : 'cyan'}>{d.mode}</Badge><span className={connected ? 'connection' : 'connection offline'}><i />{connected ? 'Ansluten' : 'Återansluter'}</span><span className="state-label">{b.state === 'running' ? 'Arbete tillåtet' : statuses[b.state]}</span><button className="decision-top" onClick={() => go('Förslag & beslut')}><CheckCheck size={16} />{pending.length} beslut</button></div></header>
 <main className="content"><div className="page-heading"><div><div className="eyebrow">JARVIS / {page === 'Översikt' ? 'MISSION CONTROL' : 'FOOTBALL RESEARCH'}</div><h1>{page === 'Översikt' ? 'Fotbollsanalys före riktiga insatser.' : page}</h1><p>{page === 'Översikt' ? 'Fotbollsodds, datakvalitet och simulerade resultat. Inga riktiga spel.' : ({
                Agentteam: 'Tio fasta specialister. Tydliga uppdrag och begränsade behörigheter.',
                Oddslabb: 'Jämför odds, granska underlaget och följ upp pappersresultaten.',
                Ekonomi: 'Planeringsbudget i SEK. Inga pengar har överförts till programmet.',
                'Förslag & beslut': 'Granska exakt vad som föreslås innan nästa steg får köras.',
                'Chatta med JARVIS': 'Fråga om läget. Databassvar utan AI-kostnad.'
              } as Record<string, string>)[page] || 'Följ arbetet och behåll kontrollen.'}</p></div>{page === 'Översikt' && <button className="primary" disabled={busy} onClick={openRound}><Play size={15} /> Starta arbetsomgång</button>}</div>
 {error && <div role="alert" className="error-banner"><AlertTriangle size={18} />{error}<button aria-label="Stäng felmeddelande" onClick={() => setError('')}><X size={16} /></button></div>}
 {d.mode === 'DEMO' && <div className="demo-strip"><span><span className="demo-dot" /> DEMOMILJÖ</span><p>Utforska arbetsflödet med märkta exempel. Inga AI-anrop eller verkliga kostnader.</p><button onClick={() => go('Inställningar')}>Om LIVE <ArrowUpRight size={14} /></button></div>}
 {page === 'Översikt' && <><div className="metrics"><article><span>AGENTTEAM <Users size={17} /></span><div>10 <small>specialister</small></div><p><i className="cyan-dot" />{working} arbetar <span>· {10 - working} {b.state === 'running' ? 'väntar' : 'pausade'}</span></p></article><article><span>ATT TA STÄLLNING TILL <CheckCheck size={17} /></span><div>{pending.length.toString().padStart(2, '0')} <small>beslut väntar</small></div><p>{pending.length ? 'Ditt godkännande behövs' : 'Inga beslut väntar just nu'}</p></article><article><span>ANVÄNDBAR BUDGET <Wallet size={17} /></span><div>{money(b.available)}</div><p>{money(b.locked)} i låst reserv</p></article><article><span>REGISTRERAD ANVÄNDNING <Activity size={17} /></span><div>{money(b.spent)}</div><p>{money(b.reserved)} reserverat <span>· totalt</span></p></article></div>
 <div className="overview-grid"><section className="panel mission"><div className="panel-header"><h2><span className="square-icon"><Compass size={17} /></span>Aktuellt uppdrag</h2><Badge tone={b.state === 'running' ? 'cyan' : 'amber'}>{b.state === 'running' ? 'Redo för arbete' : statuses[b.state]}</Badge></div><span className="eyebrow">HUVUDMÅL</span><h2 className="mission-goal">{b.goal}</h2><p>Granska odds. Följ upp låtsasinsatser.<br />Gå vidare först när underlaget håller.</p><div className="workflow"><span className="active">01 <b>Undersök</b></span><ChevronRight size={16} /><span>02 <b>Jämför</b></span><ChevronRight size={16} /><span>03 <b>Besluta</b></span></div><div className="next-step"><span className="tiny-orbit" /><div><small>NÄSTA STEG</small><strong>{pending.length ? 'Granska förslagen och välj om arbetet ska fortsätta.' : b.state !== 'running' ? 'Återuppta arbetet när du är redo.' : 'Starta ett uppdrag eller invänta köade uppgifter.'}</strong></div></div><div className="mission-controls"><button disabled={busy || b.state === 'running'} onClick={() => control('running')}><Play size={15} />Återuppta</button><button disabled={busy || b.state !== 'running'} onClick={() => control('paused')}><Pause size={15} />Pausa</button><button className="stop" disabled={busy || b.state === 'stopped'} onClick={() => control('stopped')}><Square size={13} />Nödstopp</button></div><small className="muted">Paus stoppar nya uppgifter. Nödstopp försöker även avbryta pågående anrop.</small></section>
 <section className="panel attention"><div className="panel-header"><h2>Din uppmärksamhet</h2><Badge tone="amber">{pending.length}</Badge></div>{pending.length ? <><div className="attention-symbol"><CheckCheck size={25} /></div><small className="eyebrow">FÖRSLAG ATT GRANSKA</small><h3>{pending[0].payload.title}</h3><p>{pending[0].payload.purpose}</p><div className="cost-line"><span>Maximalt nästa steg</span><strong>{money(pending[0].payload.cap + pending[0].payload.review_cap)}</strong></div><button className="wide" onClick={() => go('Förslag & beslut')}>Granska förslag <ArrowRight size={16} /></button></> : <><div className="attention-symbol"><ShieldCheck size={28} /></div><h3>Inget väntar på ditt beslut.</h3><p>När teamet har ett konkret nästa steg hittar du underlag, risker och kostnadstak här.</p><div className="quiet-note">Inget utförs externt utan en ansluten integration och rätt behörighet.</div></>}</section>
 <section className="panel team-panel"><div className="panel-header"><h2>Teamet, samlat</h2><button className="text-button" onClick={() => go('Agentteam')}>Alla agenter <ArrowUpRight size={15} /></button></div><div className="team-mini">{d.agents.map((a, i) => <button key={a.id} onClick={() => setAgent(a)}><span className={'agent-symbol color-' + i % 4}>{i === 0 ? <Cpu size={20} /> : String(i + 1).padStart(2, '0')}</span><strong>{a.name.split(' / ')[0]}</strong><small><i className={a.status === 'Arbetar' ? 'cyan-dot' : 'gray-dot'} />{a.status}</small></button>)}</div></section>
 <section className="panel feed"><div className="panel-header"><h2>Senaste aktivitet</h2><button className="text-button" onClick={() => go('Historik')}>Historik <ArrowUpRight size={15} /></button></div>{d.events.length ? <div className="timeline">{d.events.slice(0, 5).map(e => <button key={e.id} onClick={() => e.task_id && setTask(d.tasks.find(t => t.id === e.task_id) || null)}><span className="timeline-dot" /><div><p>{e.message}</p><small>{date(e.created)}</small></div></button>)}</div> : <Empty>Här visas registrerade händelser när du börjar arbeta.</Empty>}</section>
 <section className="panel full-width"><div className="panel-header"><h2>Senaste arbetsresultat</h2><button className="text-button" onClick={() => go('Projekt & uppgifter')}>Alla uppgifter <ArrowUpRight size={15} /></button></div>{taskList(d.tasks.filter(t => t.result).slice(0, 3))}</section></div></>}
 {page === 'Agentteam' && <div className="agent-grid">{d.agents.map((a, i) => <button className="agent-card" key={a.id} onClick={() => setAgent(a)}><div className="row"><span className={'agent-symbol color-' + i % 4}>{String(i + 1).padStart(2, '0')}</span><Badge tone={a.status === 'Arbetar' ? 'cyan' : ''}>{a.status}</Badge></div><h2>{a.name}</h2><p>{a.task?.title || 'Ingen aktiv uppgift'}</p><div className="agent-result"><small>SENASTE RESULTAT</small><p>{a.latest || 'Inget resultat sparat ännu.'}</p></div><footer><span>{money(a.usage)} registrerat</span><ArrowUpRight size={17} /></footer></button>)}</div>}
 {page === 'Chatta med JARVIS' && <section className="panel chat-panel"><div className="panel-header"><h2><Cpu size={20} /> VD / JARVIS</h2><Badge tone="cyan">Databasansluten</Badge></div><div className="chat-messages">{!d.messages.length && <div className="chat-welcome"><span className="brand-mark">J</span><h2>Vad vill du veta?</h2><p>Jag visar registrerad status. Nya uppdrag startar du med arbetsomgångsknappen.</p><div className="suggestions">{['Vad jobbar ni med?', 'Vad saknas i oddsunderlaget?', 'Hur mycket har ni använt?'].map(q => <button key={q} onClick={() => act(() => api('/chat', {
                  message: q
                }))}>{q}<ArrowUpRight size={14} /></button>)}</div></div>}{d.messages.map(m => <div className={'message ' + m.role} key={m.id}><small>{m.role === 'user' ? 'DU' : 'JARVIS · STATUSSVAR'}</small><p>{m.content}</p><time>{date(m.created)}</time></div>)}</div><form className="chat-form" onSubmit={e => {
            e.preventDefault();
            const message = chat;
            act(async () => {
              await api('/chat', {
                message
              });
              setChat('');
            });
          }}><input aria-label="Meddelande till JARVIS" placeholder="Fråga om läget, idéerna eller budgeten…" maxLength={2000} value={chat} onChange={e => setChat(e.target.value)} required /><button className="primary" aria-label="Skicka meddelande" disabled={busy}><Send size={18} /></button></form><div className="chat-footer"><small>Statuschatten använder inga AI-anrop. Beslut fattas under Förslag & beslut.</small><button onClick={openRound}>Starta arbetsomgång <ArrowRight size={14} /></button></div></section>}
 {page === 'Förslag & beslut' && <>{d.proposals.length ? <div className="proposals-grid">{d.proposals.map(proposalCard)}</div> : <section className="panel"><Empty>Inga förslag ännu. Starta en arbetsomgång så tar VD fram ett granskningsbart nästa steg.</Empty><button className="primary empty-action" onClick={openRound}>Starta arbetsomgång</button></section>}</>}
 {page === 'Projekt & uppgifter' && <><section className="panel project-list"><div className="panel-header"><h2>Utvecklingsprojekt</h2><Badge>Högst 1 aktivt</Badge></div>{d.projects.length ? d.projects.map(p => <div className="row" key={p.id}><strong>{p.title}</strong><Badge>{statuses[p.state]}</Badge>{p.state === 'active' && <button disabled={busy} onClick={() => act(() => api('/projects/' + p.id + '/close', {}))}>Avsluta projekt</button>}</div>) : <p className="muted">Inget utvecklingsprojekt startat. Research kan utföras utan att ett utvecklingsprojekt skapas.</p>}</section><div className="kanban">{['queued', 'running', 'approval', 'review', 'done', 'blocked'].map(status => <section key={status}><h3>{statuses[status]} <span>{d.tasks.filter(t => t.status === status).length}</span></h3>{d.tasks.filter(t => t.status === status).map(t => <button className="kanban-card" key={t.id} onClick={() => setTask(t)}><small>{d.agents.find(a => a.id === t.agent_id)?.name}</small><h4>{t.title}</h4><footer><span>{money(t.cap)} tak</span><ArrowUpRight size={15} /></footer></button>)}</section>)}</div></>}
 {page === 'Ekonomi' && <><div className="metrics finance-metrics">{[['Total planeringsbudget', b.total], ['Låst reserv', b.locked], ['Registrerad förbrukning', b.spent], ['Reserverat', b.reserved], ['Tillgängligt', b.available]].map(([label, value]) => <article key={label}><span>{label}</span><div>{money(Number(value))}</div></article>)}</div><div className="notice"><Wallet size={18} />Betalningar ej anslutna. Inga intäkter registreras automatiskt. Manuella poster är ägaruppgifter.</div><section className="panel"><div className="panel-header"><h2>Kostnadsposter</h2><button onClick={() => {
                setManual(true);
                setCostAction(crypto.randomUUID());
                setNote('');
                setAmount('');
              }}>Registrera kostnad</button></div>{d.costs.length ? <div className="table-scroll"><table><thead><tr><th>Datum</th><th>Agent / uppgift</th><th>Typ</th><th>Belopp</th><th>Underlag</th></tr></thead><tbody>{d.costs.map(c => <tr key={c.id}><td>{date(c.created)}</td><td><button className="text-button" onClick={() => setTask(d.tasks.find(t => t.id === c.task_id) || null)}>{d.agents.find(a => a.id === c.agent_id)?.name || 'Manuell post'}</button></td><td>{c.kind === 'estimate' ? 'API-uppskattning' : c.kind === 'manual' ? 'Manuell · ej verifierad' : 'Avstämd av ägaren'}</td><td>{money(c.amount)}</td><td><details><summary>Visa underlag</summary><pre>{JSON.stringify(JSON.parse(c.metadata), null, 2)}</pre></details></td></tr>)}</tbody></table></div> : <Empty>Inga kostnader registrerade.</Empty>}</section><section className="panel sources"><div className="panel-header"><h2>Aktiva reservationer</h2></div>{d.reservations.length ? d.reservations.map(r => <div className="reservation" key={r.id}><span>{money(r.amount)} · {r.status === 'unknown' ? 'Okänd debitering – kontroll krävs' : 'Reserverat för pågående anrop'}</span>{r.status === 'unknown' && <button onClick={() => {
                setReconcile(r.id);
                setNote('');
                setAmount('');
              }}>Stäm av mot leverantör</button>}</div>) : <p className="muted">Inga öppna reservationer.</p>}</section></>}
 {page === 'Filer' && <section className="panel"><div className="panel-header"><h2>Sparade leveranser</h2><Badge>{d.files.length} filer</Badge></div>{d.files.length ? <div className="file-grid">{d.files.map(f => <article key={f.id}><Files size={25} /><h3>{f.name}</h3><p>{d.tasks.find(t => t.id === f.task_id)?.title}</p><small>{date(f.created)}</small><a className="button" href={'/api/files/' + f.id} download><Download size={16} />Ladda ner textunderlag</a></article>)}</div> : <Empty>Rapporter och kodutkast visas här när en uppgift har gett ett resultat.</Empty>}</section>}
 {page === 'Historik' && <section className="panel"><div className="panel-header"><h2>Händelser & beslut</h2><div className="search"><Search size={16} /><input aria-label="Sök historik" placeholder="Sök i historiken…" value={filter} onChange={e => setFilter(e.target.value)} /></div></div><div className="history-list">{d.events.filter(e => (e.message + ' ' + e.kind).toLowerCase().includes(filter.toLowerCase())).map(e => <div key={e.id}><time>{date(e.created)}</time><Badge>{e.kind}</Badge><button className="text-button" onClick={() => e.task_id && setTask(d.tasks.find(t => t.id === e.task_id) || null)}>{e.message}</button></div>)}</div><small className="muted">Visar de senaste 300 händelserna. Samtliga bevaras i databasen.</small></section>}
 {page === 'Inställningar' && <div className="settings-grid"><section className="panel"><h2>Budgetgränser</h2><p>Endast ägaren kan ändra dessa gränser. Alla belopp anges i SEK.</p><form onSubmit={e => {
              e.preventDefault();
              act(() => api('/settings', Object.fromEntries(['total', 'locked', 'daily', 'per_task'].map(k => [k, Math.round(Number(limits[k] ?? b[k as keyof typeof b]) / (limits[k] === undefined ? 100 : 1) * 100)]))));
            }}>{Object.entries({
                total: 'Total budget',
                locked: 'Låst reserv',
                daily: 'Dagligt kostnadstak',
                per_task: 'Kostnadstak per uppgift'
              }).map(([k, label]) => <label key={k}>{label}<input type="number" min="0" step="0.01" value={limits[k] ?? Number(b[k as keyof typeof b]) / 100} onChange={e => setLimits({
                  ...limits,
                  [k]: e.target.value
                })} required /></label>)}<button className="primary" disabled={busy}>Spara budgetgränser</button></form></section><section className="panel"><h2>Körläge & integrationer</h2><Badge tone="amber">{d.mode}</Badge><p>Byt läge i serverns .env och starta om backend och worker. DEMO och LIVE använder olika databaser och ägarkonton.</p><h3>LIVE-konfiguration</h3>{d.live_missing.length ? <ul className="config-list">{d.live_missing.map(m => <li key={m}><AlertTriangle size={14} />{m}</li>)}</ul> : <p>Obligatoriska konfigurationsfält är ifyllda. Kontoåtkomst och faktisk debitering har inte verifierats här.</p>}<p>Agentmodeller, prisversion, valutakurs och källinställningar anges serversidigt i .env. V1 kräver en gemensam verifierad prisprofil.</p><hr /><p><strong>Oddsdata:</strong> ingen löpande leverantör är ansluten. Wikipedia och den gamla affärsidéresearchen är arkiverade. Oddslabb använder märkta exempel och manuella observationer.</p><p><strong>Arbetsschema:</strong> begränsade VD-omgångar kan förhandsgodkännas nedan.</p><p><strong>Avstängt:</strong> betalningar, köp, annonser, publicering, utskick och avtal.</p></section></div>}
 {page === 'Dokument' && <DocumentLibrary route={route} navigate={navigate} />}
 {page === 'Oddslabb' && <OddsLab request={api} systemState={b.state} mode={d.mode} resume={() => control('running')} />}
 {page === 'Inställningar' && <Schedule value={d.schedule} busy={busy} save={v => act(() => api('/schedule', v))} />}
 <footer className="system-footer"><span><Radio size={14} />{d.worker.online ? 'Worker ansluten' : 'Worker saknas eller svarar inte'}{d.worker.heartbeat && ' · senast ' + date(d.worker.heartbeat * 1000)}</span><span>EUROPE / STOCKHOLM <span className="footer-divider">/</span> JARVIS 1.0</span></footer>
 </main></div>
 {round && <Modal title="Starta en arbetsomgång" onClose={() => setRound(false)}><form onSubmit={e => {
        e.preventDefault();
        act(async () => {
          await api('/rounds', {
            goal,
            cap: Math.round(Number(cap) * 100),
            action_id: roundAction
          });
          setRound(false);
        });
      }}><p>VD tar fram ett förslag. Specialistarbete väntar på ditt separata godkännande.</p><label>Vad ska teamet undersöka?<textarea value={goal} onChange={e => setGoal(e.target.value)} minLength={5} maxLength={2000} required rows={4} /></label><label>VD-uppgiftens kostnadstak (SEK)<input type="number" min="0" max={b.per_task / 100} step="0.01" value={cap} onChange={e => setCap(e.target.value)} required /></label>{b.state !== 'running' && <div className="notice">Arbetet är {statuses[b.state].toLowerCase()}. <button type="button" disabled={busy} onClick={() => control('running')}>Återuppta</button></div>}<button className="primary" disabled={busy || b.state !== 'running'}>Skapa uppdrag <ArrowRight size={16} /></button></form></Modal>}
 {selectedAgent && <Modal title={selectedAgent.name} onClose={() => setAgent(null)}><Badge>{selectedAgent.status}</Badge><p>Stabilt ID: {selectedAgent.id} · Instruktionsversion {selectedAgent.version}</p><h3>Uppdrag & instruktioner</h3><p className="pre-wrap">{selectedAgent.instructions}</p><h3>Tillåtna verktyg</h3><p>{selectedAgent.tools.join(', ') || 'Inga externa verktyg'}</p><p className="muted">Verktyg anropas av backend efter behörighetskontroll, inte fritt av modellen.</p><h3>Resultatformat</h3><p>{selectedAgent.output_format}</p><h3>Uppgiftshistorik · {money(selectedAgent.usage)}</h3>{taskList(d.tasks.filter(t => t.agent_id === selectedAgent.id))}</Modal>}
 {selectedTask && <Modal title="Uppgiftsdetaljer" onClose={() => setTask(null)}><Badge>{statuses[selectedTask.status]}</Badge><TaskDetails task={selectedTask} data={d} openTask={setTask} /></Modal>}
 {decision && <Modal title={decision.value === 'approved' ? 'Godkänn exakt nästa steg' : decision.value === 'changes' ? 'Begär en ändring' : 'Avslå förslaget'} onClose={() => setDecision(null)}><h3>{decision.p.payload.title}</h3><p>{decision.p.payload.effect}</p><p><strong>Totalt tak: {money(decision.p.payload.cap + decision.p.payload.review_cap)}</strong> · version {decision.p.version}</p><p className="muted">Godkänt betyder köat. Arbetet börjar bara när systemet är återupptaget och budgeten tillåter det.</p><label>Kommentar<textarea rows={3} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} /></label><button className="primary" disabled={busy} onClick={() => act(async () => {
        await api('/proposals/' + decision.p.id + '/decision', {
          version: decision.p.version,
          digest: decision.p.digest,
          decision: decision.value,
          note
        });
        setDecision(null);
      })}>Bekräfta {decision.value === 'approved' ? 'godkännande' : decision.value === 'changes' ? 'ändringsbegäran' : 'avslag'}</button></Modal>}
 {edit && <Modal title="Revidera förslag" onClose={() => setEdit(null)}><form onSubmit={e => {
        e.preventDefault();
        act(async () => {
          await api('/proposals/' + edit.id + '/revise', {
            title: editTitle,
            cap: Math.round(Number(cap) * 100)
          });
          setEdit(null);
        });
      }}><p>En ny version skapas. Den kräver ett nytt godkännande.</p><label>Föreslagen åtgärd<textarea value={editTitle} onChange={e => setEditTitle(e.target.value)} minLength={5} required /></label><label>Tak per uppgift (SEK)<input type="number" min="0" max={b.per_task / 100} step="0.01" value={cap} onChange={e => setCap(e.target.value)} required /></label><button className="primary" disabled={busy}>Spara ny version</button></form></Modal>}
 {(manual || reconcile) && <Modal title={manual ? 'Registrera manuell kostnad' : 'Stäm av okänd debitering'} onClose={() => {
      setManual(false);
      setReconcile(null);
    }}><form onSubmit={e => {
        e.preventDefault();
        act(async () => {
          await api(manual ? '/costs' : '/reservations/' + reconcile + '/reconcile', {
            amount: Math.round(Number(amount) * 100),
            note,
            ...(manual ? {
              action_id: costAction
            } : {})
          });
          setManual(false);
          setReconcile(null);
        });
      }}><p>{manual ? 'Posten märks som manuellt registrerad.' : 'Kontrollera leverantörens faktura eller användningsrapport först. Ange vad som kontrollerats.'}</p><label>Belopp (SEK)<input type="number" min={manual ? '0.01' : '0'} step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required /></label><label>Underlag / kommentar<textarea value={note} onChange={e => setNote(e.target.value)} minLength={manual ? 3 : 10} required /></label><button className="primary" disabled={busy}>Spara</button></form></Modal>}
 </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);

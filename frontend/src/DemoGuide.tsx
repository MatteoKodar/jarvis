import {ArrowRight, Bot, CheckCheck, Activity} from 'lucide-react';
import type {State} from './types';
import type {Page} from './navigation';
import './demo-guide.css';

export const DEMO_GOAL = 'Granska tidsstämplar, oddsunderlag och kostnader för fotbollens 1X2-marknad. Visa vad som saknas innan en simulerad signal kan bedömas.';

type Props = {data:State;busy:boolean;prepareRound:()=>void;navigate:(page:Page)=>void};

export function DemoGuide({data,busy,prepareRound,navigate}:Props) {
  return <section className="panel demo-guide" aria-labelledby="demo-guide-title">
    <header className="demo-guide-heading"><div><span className="eyebrow">DEMO UNDER UTVECKLING</span><h2 id="demo-guide-title">Så testar vi bettingagentens arbetsflöde</h2></div><span className="badge amber">Påhittade matcher och odds</span></header>
    <p>Följ en sammanhängande demo: sju påhittade matcher → lokal analys → ditt batchbeslut → låtsasinsatser → simulerade resultat och ekonomi. Den visar arbetsgången, inte bevisad lönsamhet.</p>
    <div className="demo-guide-state" role="status"><strong>{data.settings.state==='running'?'Nya demoåtgärder är tillåtna.':data.settings.state==='stopped'?'Nödstopp är aktivt.':'Arbetet är pausat.'}</strong>{' '}Du kan alltid läsa sparade omgångar. Demot körs direkt i backend och behöver ingen worker.</div>
    <div className="demo-guide-cards">
      <article><Bot size={22} aria-hidden="true"/><h3>1. Skapa och analysera</h3><p>Varje omgång får 1 000 kr i eget låtsaskapital. Analysen sparar fyra förslag, tre avståenden och 1,40 kr i simulerade kostnader.</p><small>Inga insatser registreras när du bara öppnar eller analyserar omgången.</small><button disabled={busy} onClick={()=>navigate('Bettingdemo')}>Öppna matchdemot <ArrowRight size={15}/></button></article>
      <article><CheckCheck size={22} aria-hidden="true"/><h3>2. Besluta om hela batchen</h3><p>Granska match, utfall, effektivt odds, insats och kostnader. Godkänn exakt den sparade batchen eller avstå.</p><small>Godkännande registrerar ännu inga insatser. Analyskostnaderna kvarstår även om du avstår.</small></article>
      <article><Activity size={22} aria-hidden="true"/><h3>3. Registrera och avräkna</h3><p>Registrera hela låtsasbatchen och avräkna sedan samtliga spel. Följ öppna insatser, vinster, förluster och netto efter kostnader.</p><small>Omladdning behåller läget. En ny omgång raderar inte historiken och delar inte kapital med gamla omgångar.</small></article>
    </div>
    <p className="demo-guide-note">Simulerade agentsvar – lokal demologik. Inga externa AI-anrop eller riktiga spel görs. Agenternas svar är förskrivna i DEMO och bygger på det sparade analysresultatet.</p>
    <details className="demo-guide-advanced"><summary>Separata agentuppdrag och äldre Oddslabb</summary><p>Det äldre VD → specialist → kritiker-flödet finns kvar som ett separat verktyg och kräver worker. Det kör inte det nya demots insatser. Äldre Oddslabb behåller sina tidigare serier och manuella observationer.</p><div className="demo-guide-actions"><button disabled={busy} onClick={prepareRound}>Förbered demo-uppdrag <ArrowRight size={15}/></button><button disabled={busy} onClick={()=>navigate('Förslag & beslut')}>Öppna agentförslag</button><button disabled={busy} onClick={()=>navigate('Filer')}>Se agentrapporter</button><button disabled={busy} onClick={()=>navigate('Oddslabb')}>Öppna äldre Oddslabb</button></div></details>
  </section>;
}

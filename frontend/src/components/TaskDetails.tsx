import type {State, Task} from '../types';
import {date, money} from '../format';

type Result = {
  summary: string;
  rationale: string;
  claims: {kind: string; text: string; source_ids: string[]}[];
};

export function TaskDetails({task, data, openTask}: {
  task: Task; data: State; openTask: (task: Task | null) => void;
}) {
  const result: Result | null = task.result ? JSON.parse(task.result) : null;
  const sources = data.sources.filter(source => source.task_id === task.id);
  const events = data.events.filter(event => event.task_id === task.id);

  return <>
    <h2>{task.title}</h2>
    <dl>
      <dt>Ansvarig</dt><dd>{data.agents.find(agent => agent.id === task.agent_id)?.name}</dd>
      <dt>Kostnadstak</dt><dd>{money(task.cap)}</dd>
      <dt>Färdigkriterier</dt><dd>{task.criteria}</dd>
      <dt>Beroende</dt>
      <dd>{task.parent_id
        ? <button onClick={() => openTask(data.tasks.find(parent => parent.id === task.parent_id) ?? null)}>Visa föregående uppgift</button>
        : 'Inget'}</dd>
    </dl>
    {task.error && <p className="error">{task.error}</p>}
    {result && <>
      <h3>Sparat resultat</h3><p className="pre-wrap">{result.summary}</p>
      <h3>Kort beslutsmotivering</h3><p>{result.rationale}</p>
      {result.claims.map((claim, index) => <div className="claim" key={index}>
        <span className="badge">{claim.kind}</span><p>{claim.text}</p>
        {claim.source_ids.map(id => <small key={id}>{data.sources.find(source => source.id === id)?.title ?? id}</small>)}
      </div>)}
    </>}
    <h3>Arbetslogg</h3>
    {events.map(event => <p key={event.id}><small>{date(event.created)}</small> · {event.message}</p>)}
    <h3>Källor</h3>
    {sources.map(source => <p key={source.id}>
      <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> · {source.claim}
    </p>)}
    <details><summary>Underlag</summary><pre>{task.context}</pre></details>
  </>;
}

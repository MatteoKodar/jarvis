import {useEffect, useMemo, useState} from 'react';
import {ArrowLeft, ArrowRight, BookOpen, Search} from 'lucide-react';
import {request} from '../api';
import type {DocumentLocation, Page, Route} from '../navigation';
import {DocumentContent} from './DocumentContent';
import {parseMarkdown} from './markdown';
import './documents.css';

type DocumentInfo = {id: string; title: string; file_name: string};
type Version = {id: string; title: string; documents: DocumentInfo[]};
type Document = {id: string; version: string; file_name: string; content: string; sha256: string};
type Props = {route: Route; navigate: (page: Page, location?: DocumentLocation) => void};

function documentHref(location: DocumentLocation) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(location)) if (value) query.set(key, value);
  return '#/dokument?' + query.toString();
}

export function DocumentLibrary({route, navigate}: Props) {
  const [versions, setVersions] = useState<Version[]>([]);
  const [content, setContent] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const version = versions.find(item => item.id === (route.version ?? versions[0]?.id));
  const selected = version?.documents.find(item => item.id === (route.document ?? version.documents[0]?.id));
  const position = version?.documents.findIndex(item => item.id === selected?.id) ?? -1;
  const blocks = useMemo(() => parseMarkdown(content?.content ?? ''), [content]);
  const headings = blocks.filter(block => block.kind === 'heading');

  useEffect(() => {
    const controller = new AbortController();
    request<{versions: Version[]}>('/documents', undefined, controller.signal)
      .then(value => setVersions(value.versions))
      .catch(error => { if (!controller.signal.aborted) setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!version || !selected) return;
    const controller = new AbortController();
    setLoading(true);
    setContent(null);
    setError('');
    setQuery('');
    request<Document>(`/documents/${version.id}/${selected.id}`, undefined, controller.signal)
      .then(value => setContent(value))
      .catch(error => { if (!controller.signal.aborted) setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [version?.id, selected?.id]);

  useEffect(() => {
    if (!content) return;
    if (route.section) {
      const heading = document.getElementById(route.section);
      heading?.scrollIntoView({block: 'start'});
      heading?.focus({preventScroll: true});
    } else window.scrollTo(0, 0);
  }, [content, route.section]);

  const location = {version: version?.id, document: selected?.id};
  const searchResults = useMemo(() => {
    const term = query.trim().toLocaleLowerCase('sv');
    if (term.length < 2) return [];
    let section = '';
    return blocks.flatMap(block => {
      if (block.kind === 'heading') section = block.id;
      const text = block.kind === 'table' ? block.rows.flat().join(' ') : block.kind === 'list' ? block.items.join(' ') : block.text;
      const offset = text.toLocaleLowerCase('sv').indexOf(term);
      return offset < 0 ? [] : [{section, text: text.slice(Math.max(0, offset - 45), offset + 120)}];
    });
  }, [blocks, query]);

  const resolveLink = (href: string) => {
    const target = version?.documents.find(item => item.file_name === href);
    if (target) return documentHref({version: version?.id, document: target.id});
    if (href.startsWith('#')) return documentHref({...location, section: href.slice(1)});
    // Code paths and unsupported URL schemes are displayed as plain text.
    return /^https?:\/\//i.test(href) ? href : null;
  };

  const openNeighbour = (offset: number) => {
    const target = version?.documents[position + offset];
    if (target) navigate('Dokument', {version: version?.id, document: target.id});
  };

  return <div className="document-library">
    <section className="panel document-toolbar">
      <div><BookOpen size={20}/><strong>Projektdokument</strong><span className="badge amber">Utkast · inte körklart</span></div>
      <label>Version
        <select aria-label="Version" value={version?.id ?? ''} onChange={event => navigate('Dokument', {version: event.target.value})}>
          {!version && <option value="">Välj version</option>}
          {versions.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
      </label>
    </section>

    <div className="document-layout">
      <aside className="panel document-navigation">
        <nav aria-label="Dokument i versionen">
          <h2>Dokument</h2>
          {version?.documents.map((item, index) => <a key={item.id}
            href={documentHref({version: version.id, document: item.id})}
            aria-current={item.id === selected?.id ? 'page' : undefined}>
            <span>{String(index + 1).padStart(2, '0')}</span>{item.title}
          </a>)}
        </nav>
        <details open className="document-toc">
          <summary>Innehållsförteckning</summary>
          <nav aria-label="Innehållsförteckning">
            {headings.filter(heading => heading.level <= 3).map(heading => <a key={heading.id}
              className={heading.level > 1 ? 'document-subheading' : ''}
              href={documentHref({...location, section: heading.id})}
              aria-current={route.section === heading.id ? 'location' : undefined}>
              {heading.text}
            </a>)}
          </nav>
        </details>
      </aside>

      <section className="panel document-reader" aria-label="Dokumentläsare" aria-busy={loading}>
        <div className="document-reader-heading">
          <p>{selected ? `${position + 1} av ${version?.documents.length} · ${selected.title}` : 'Välj ett dokument'}</p>
          <label className="document-search"><Search size={16}/><input aria-label="Sök i dokumentet" placeholder="Sök i dokumentet…" value={query} onChange={event => setQuery(event.target.value)}/></label>
        </div>
        {query.trim().length >= 2 && <div className="document-search-results" aria-live="polite">
          <p>{searchResults.length} träffar{searchResults.length > 30 ? ' · visar de första 30' : ''}</p>
          {searchResults.slice(0, 30).map((result, index) => <a key={index} href={documentHref({...location, section: result.section})}>{result.text}</a>)}
        </div>}
        {error && <p role="alert" className="error">{error}</p>}
        {loading && <p role="status">Hämtar dokument…</p>}
        {!loading && !error && (!version || !selected) && <p>Dokumentet finns inte i den valda versionen. Välj ett dokument i menyn.</p>}
        {!loading && !error && content && content.version === version?.id && content.id === selected?.id && <>
          <article className="document-body"><DocumentContent blocks={blocks} resolveLink={resolveLink}/></article>
          <footer className="document-paging">
            <button disabled={position <= 0} onClick={() => openNeighbour(-1)}><ArrowLeft size={16}/> Föregående dokument</button>
            <button disabled={position >= (version?.documents.length ?? 0) - 1} onClick={() => openNeighbour(1)}>Nästa dokument <ArrowRight size={16}/></button>
          </footer>
          <details className="document-source"><summary>Dokumentets original</summary><p>{content.file_name}</p><small>SHA-256: {content.sha256}</small><pre>{content.content}</pre></details>
        </>}
      </section>
    </div>
  </div>;
}

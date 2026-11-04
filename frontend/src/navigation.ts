import {useCallback, useEffect, useState} from 'react';

const pages = {
  oversikt: 'Översikt', agenter: 'Agentteam', chatt: 'Chatta med JARVIS',
  forslag: 'Förslag & beslut', oddslabb: 'Oddslabb',
  projekt: 'Projekt & uppgifter', ekonomi: 'Ekonomi',
  filer: 'Filer', dokument: 'Dokument', historik: 'Historik', installningar: 'Inställningar',
} as const;

export type Page = typeof pages[keyof typeof pages];
export type DocumentLocation = {version?: string; document?: string; section?: string};
export type Route = DocumentLocation & {page: Page};

function readRoute(): Route {
  const [path, query] = window.location.hash.slice(1).split('?');
  const page = pages[path?.replace(/^\//, '') as keyof typeof pages] ?? 'Översikt';
  const params = new URLSearchParams(query);
  return {page, version: params.get('version') ?? undefined,
    document: params.get('document') ?? undefined, section: params.get('section') ?? undefined};
}

export function useNavigation() {
  const [route, setRoute] = useState(readRoute);
  useEffect(() => {
    const update = () => setRoute(readRoute());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);

  const navigate = useCallback((page: Page, location: DocumentLocation = {}) => {
    const slug = Object.entries(pages).find(([, label]) => label === page)![0];
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(location)) if (value) params.set(key, value);
    const query = params.size ? '?' + params.toString() : '';
    window.location.hash = '/' + slug + query;
    setRoute(readRoute());
  }, []);

  return {route, navigate};
}

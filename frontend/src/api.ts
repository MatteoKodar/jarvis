let csrfToken = '';

export function setCsrfToken(value: string) {
  csrfToken = value;
}

export async function request<T = unknown>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api' + path, {
    credentials: 'same-origin',
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === 'string'
      ? error.detail
      : `Begäran misslyckades (${response.status}). Försök igen när servern svarar.`);
  }

  return response.json();
}

// Only document structure is parsed. Text is rendered by React, never as HTML.
export type Block =
  | {kind: 'heading'; level: number; id: string; text: string}
  | {kind: 'code'; language: string; text: string}
  | {kind: 'table'; rows: string[][]}
  | {kind: 'list'; ordered: boolean; items: string[]}
  | {kind: 'paragraph'; text: string};

export function parseMarkdown(content: string): Block[] {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  const headings = new Map<string, number>();
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }

    const fence = /^\s*(`{3,}|~{3,})(\w*)/.exec(line);
    if (fence) {
      const code: string[] = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith(fence[1])) code.push(lines[index++]);
      index++;
      blocks.push({kind: 'code', language: fence[2], text: code.join('\n')});
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const slug = heading[2].toLocaleLowerCase('sv').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '') || 'avsnitt';
      const count = (headings.get(slug) ?? 0) + 1;
      headings.set(slug, count);
      blocks.push({kind: 'heading', level: heading[1].length, id: count === 1 ? slug : `${slug}-${count}`, text: heading[2]});
      index++;
      continue;
    }

    if (line.trim().startsWith('|') && /^\s*\|[\s:|\-]+\|\s*$/.test(lines[index + 1] ?? '')) {
      const cells = (value: string) => value.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
      const rows = [cells(line)];
      index += 2;
      while (index < lines.length && lines[index].trim().startsWith('|')) rows.push(cells(lines[index++]));
      blocks.push({kind: 'table', rows});
      continue;
    }

    const list = /^(?:[-*]|\d+\.)\s+/.exec(line);
    if (list) {
      const ordered = /^\d/.test(line);
      const pattern = ordered ? /^\d+\.\s+/ : /^[-*]\s+/;
      const items: string[] = [];
      while (index < lines.length && pattern.test(lines[index])) items.push(lines[index++].replace(pattern, ''));
      blocks.push({kind: 'list', ordered, items});
      continue;
    }

    const paragraph = [line];
    index++;
    while (index < lines.length && lines[index].trim() && !/^(#{1,6}\s|[-*]\s|\d+\.\s|\s*`{3,}|\s*~{3,}|\s*\|)/.test(lines[index])) {
      paragraph.push(lines[index++]);
    }
    blocks.push({kind: 'paragraph', text: paragraph.join('\n')});
  }
  return blocks;
}

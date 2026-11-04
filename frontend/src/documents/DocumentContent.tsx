import {Fragment, type ReactNode} from 'react';
import type {Block} from './markdown';

type LinkHandler = (href: string) => string | null;

function Inline({text, resolveLink}: {text: string; resolveLink: LinkHandler}) {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return <>{tokens.map((token, index): ReactNode => {
    if (token.startsWith('**') && token.endsWith('**')) return <strong key={index}>{token.slice(2, -2)}</strong>;
    if (token.startsWith('`') && token.endsWith('`')) return <code key={index}>{token.slice(1, -1)}</code>;
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
    if (link) {
      const href = resolveLink(link[2]);
      return href ? <a href={href} key={index}>{link[1]}</a> : <span key={index}>{link[1]}</span>;
    }
    return <Fragment key={index}>{token}</Fragment>;
  })}</>;
}

export function DocumentContent({blocks, resolveLink}: {blocks: Block[]; resolveLink: LinkHandler}) {
  return <>{blocks.map((block, index) => {
    if (block.kind === 'heading') {
      const Tag = `h${Math.min(block.level + 1, 6)}` as 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
      return <Tag key={block.id} id={block.id} tabIndex={-1}><Inline text={block.text} resolveLink={resolveLink}/></Tag>;
    }
    if (block.kind === 'code') {
      const code = <pre><code>{block.text}</code></pre>;
      return block.text.split('\n').length > 16
        ? <details className="document-example" key={index}><summary>Visa {block.language === 'json' ? 'JSON-exempel' : 'exempel'} ({block.text.split('\n').length} rader)</summary>{code}</details>
        : <Fragment key={index}>{code}</Fragment>;
    }
    if (block.kind === 'table') return <div className="document-table" key={index}><table>
      <thead><tr>{block.rows[0].map((cell, i) => <th key={i}><Inline text={cell} resolveLink={resolveLink}/></th>)}</tr></thead>
      <tbody>{block.rows.slice(1).map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}><Inline text={cell} resolveLink={resolveLink}/></td>)}</tr>)}</tbody>
    </table></div>;
    if (block.kind === 'list') {
      const Tag = block.ordered ? 'ol' : 'ul';
      return <Tag key={index}>{block.items.map((item, i) => <li key={i}><Inline text={item} resolveLink={resolveLink}/></li>)}</Tag>;
    }
    return <p key={index}><Inline text={block.text} resolveLink={resolveLink}/></p>;
  })}</>;
}

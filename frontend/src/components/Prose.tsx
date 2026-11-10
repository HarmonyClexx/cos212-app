// The tiny subset of markdown the lessons are written in (content lives in backend/app/content):
// blank-line paragraphs, "- " bullets, "1. " steps, and inline **bold**, *italic* and `code`.

import type { ReactNode } from 'react'

export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/g)
  return (
    <>
      {parts.map((p, i): ReactNode => {
        if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <strong key={i}>{p.slice(2, -2)}</strong>
        if (p.startsWith('`') && p.endsWith('`') && p.length > 2) return <code key={i}>{p.slice(1, -1)}</code>
        if (p.startsWith('*') && p.endsWith('*') && p.length > 2) return <em key={i}>{p.slice(1, -1)}</em>
        return p
      })}
    </>
  )
}

export function Prose({ text }: { text: string }) {
  const blocks = text.trim().split(/\n\s*\n/)
  return (
    <div className="prose">
      {blocks.map((block, i) => {
        const lines = block.split('\n')
        if (lines.every((l) => l.startsWith('- '))) {
          return <ul key={i}>{lines.map((l, j) => <li key={j}><Inline text={l.slice(2)} /></li>)}</ul>
        }
        if (lines.every((l) => /^\d+\.\s/.test(l))) {
          return <ol key={i}>{lines.map((l, j) => <li key={j}><Inline text={l.replace(/^\d+\.\s/, '')} /></li>)}</ol>
        }
        return <p key={i}><Inline text={lines.join(' ')} /></p>
      })}
    </div>
  )
}

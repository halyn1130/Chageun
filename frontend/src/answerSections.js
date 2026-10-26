// Presentation only: keep the model's wording and evidence unchanged.
const headings = {
  '무슨 뜻': ['meaning', '어떤 신호인가요?'],
  '어떤 신호인가요?': ['meaning', '어떤 신호인가요?'],
  '왜 중요한지': ['caution', '주의할 점'],
  '주의할 점': ['caution', '주의할 점'],
  '지금 할 일': ['steps', '이렇게 해주세요'],
  '이렇게 해주세요': ['steps', '이렇게 해주세요'],
}

export function splitAnswer(text = '') {
  const pattern = /(?:^|\n|[ \t]+)(무슨 뜻|어떤 신호인가요\?|왜 중요한지|주의할 점|지금 할 일|이렇게 해주세요)[ \t]*[:：][ \t]*/g
  const matches = [...text.matchAll(pattern)]
  if (!matches.length) return { intro: text, sections: [] }
  const sections = matches.flatMap((match, i) => {
    const content = text.slice(match.index + match[0].length, matches[i + 1]?.index ?? text.length).trim()
    if (!content) return []
    const [kind, title] = headings[match[1]]
    // Only turn an explicit, sequential list into steps; never split decimals or invent steps.
    const markers = [...content.matchAll(/(?:^|\n|[ \t]+)(\d+)[).][ \t]+/g)]
    const numbered = kind === 'steps' && markers.length && markers[0].index === 0
      && markers.every((m, n) => Number(m[1]) === n + 1)
    const items = numbered ? markers.map((m, n) => content.slice(m.index + m[0].length, markers[n + 1]?.index ?? content.length).trim()) : []
    return [{ kind, title, content, items: items.every(Boolean) ? items : [] }]
  })
  return { intro: text.slice(0, matches[0].index).trim(), sections }
}

export function sourceLabel(sources = []) {
  const titles = sources.map(source => source.title || '')
  if (titles.length && titles.every(title => /설명서|매뉴얼|manual/i.test(title))) return '매뉴얼에서 확인하기'
  if (titles.length && titles.every(title => /법|시행령|시행규칙/.test(title))) return '법령에서 확인하기'
  return '근거 자료 확인하기'
}

// Layout only: recognise explicit sequential markers, never decimals, dates or units.
export function answerBlocks(text = '') {
  // Blank lines before numbered steps belong to the same list, not separate paragraphs.
  const normalized = String(text || '').replace(/\n[ \t]*\n(?=[ \t]*(?:\(\d+\)|\d+[.)][ \t]+|[①②③④⑤⑥⑦⑧⑨⑩]))/g, '\n')
  return normalized.split(/\n\s*\n/).filter(part => part.trim()).flatMap(part => {
    const content = part.trim()
    const markers = [...content.matchAll(/(?:^|[\s:：])(?:\((\d+)\)|(\d+)[.)]|([①②③④⑤⑥⑦⑧⑨⑩]))[ \t]*/g)]
      .filter(m => m[1] || m[3] || /\s/.test(content[m.index + m[0].length] || '') || /[ \t]$/.test(m[0]))
    const number = m => Number(m[1] || m[2] || '①②③④⑤⑥⑦⑧⑨⑩'.indexOf(m[3]) + 1)
    const sequential = markers.length >= 2 && markers.every((m, i) => number(m) === i + 1)
    if (sequential) {
      const intro = content.slice(0, markers[0].index).trim()
      const items = markers.map((m, i) => content.slice(m.index + m[0].length, markers[i + 1]?.index ?? content.length).trim())
      if (items.every(Boolean)) return [...(intro ? [{ type: 'paragraph', text: intro }] : []), { type: 'ordered', items }]
    }
    const lines = content.split('\n')
    if (lines.length > 1 && lines.every(line => /^\s*[-•*]\s+\S/.test(line))) {
      return [{ type: 'unordered', items: lines.map(line => line.replace(/^\s*[-•*]\s+/, '')) }]
    }
    return [{ type: 'paragraph', text: content }]
  })
}

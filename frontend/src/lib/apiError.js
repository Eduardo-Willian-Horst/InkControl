export function formatApiError(data) {
  if (!data || typeof data !== 'object') return 'Erro desconhecido.'
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) return data.detail.map(String).join(' ')
  const parts = []
  for (const [key, val] of Object.entries(data)) {
    if (key === 'detail') continue
    if (typeof val === 'string') parts.push(`${key}: ${val}`)
    else if (Array.isArray(val)) parts.push(`${key}: ${val.join(' ')}`)
    else if (val && typeof val === 'object') parts.push(`${key}: ${JSON.stringify(val)}`)
  }
  return parts.length ? parts.join(' ') : 'Não foi possível concluir a operação.'
}

export function nextPathFromDrfUrl(url) {
  if (!url) return null
  try {
    const u = new URL(url)
    return `${u.pathname}${u.search}`
  } catch {
    return null
  }
}

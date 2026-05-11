import { apiFetch } from '../api/client'
import { nextPathFromDrfUrl } from './apiError'

export async function fetchAllPaginated(firstPath) {
  const out = []
  let path = firstPath
  while (path) {
    const data = await apiFetch(path)
    out.push(...(data.results ?? []))
    path = data.next ? nextPathFromDrfUrl(data.next) : null
  }
  return out
}

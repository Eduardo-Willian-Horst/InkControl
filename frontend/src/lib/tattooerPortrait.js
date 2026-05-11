export function tattooerPortraitSrc(tattooerId, name) {
  const seed = encodeURIComponent(String(tattooerId ?? '') + (name || ''))
  return `https://api.dicebear.com/7.x/notionists-neutral/svg?seed=${seed}`
}

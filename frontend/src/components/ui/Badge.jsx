import './Badge.css'

export function Badge({ children, variant = 'default', className = '' }) {
  const extra =
    variant === 'outline' ? ' ds-badge--outline' : variant === 'muted' ? ' ds-badge--muted' : ''
  return <span className={`ds-badge${extra} ${className}`.trim()}>{children}</span>
}

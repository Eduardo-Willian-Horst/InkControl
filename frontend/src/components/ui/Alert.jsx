import './Alert.css'

export function Alert({ children, variant = 'neutral', className = '' }) {
  return (
    <div
      role="alert"
      className={`ds-alert ds-alert--${variant} ${className}`.trim()}
    >
      {children}
    </div>
  )
}

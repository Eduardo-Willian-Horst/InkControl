import './Button.css'

const VARIANTS = ['primary', 'secondary', 'ghost', 'danger']

export function Button({
  children,
  variant = 'primary',
  size,
  className = '',
  type = 'button',
  ...props
}) {
  const v = VARIANTS.includes(variant) ? variant : 'primary'
  const sizeClass = size === 'sm' ? ' ds-btn--sm' : ''
  return (
    <button
      type={type}
      className={`ds-btn ds-btn--${v}${sizeClass} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  )
}

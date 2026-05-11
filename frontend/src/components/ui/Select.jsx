import './Input.css'

export function Select({ id, className = '', children, ...props }) {
  return (
    <select id={id} className={`ds-input ${className}`.trim()} {...props}>
      {children}
    </select>
  )
}

import './Input.css'

export function Field({ label, hint, id, children, className = '' }) {
  return (
    <div className={`ds-field ${className}`.trim()}>
      {label ? (
        <label className="ds-field__label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      {children}
      {hint ? <span className="ds-field__hint">{hint}</span> : null}
    </div>
  )
}

export function Input({ id, className = '', ...props }) {
  return <input id={id} className={`ds-input ${className}`.trim()} {...props} />
}

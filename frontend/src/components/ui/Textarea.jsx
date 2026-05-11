import './Input.css'
import './Textarea.css'

export function Textarea({ id, className = '', ...props }) {
  return <textarea id={id} className={`ds-input ds-textarea ${className}`.trim()} {...props} />
}

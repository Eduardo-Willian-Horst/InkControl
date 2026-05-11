import './Spinner.css'

export function Spinner({ large, className = '', ...rest }) {
  return (
    <span
      className={`ds-spinner${large ? ' ds-spinner--lg' : ''} ${className}`.trim()}
      {...rest}
    />
  )
}

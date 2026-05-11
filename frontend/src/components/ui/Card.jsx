import './Card.css'

export function Card({ children, className = '' }) {
  return <div className={`ds-card ${className}`.trim()}>{children}</div>
}

export function CardHeader({ children, className = '' }) {
  return <div className={`ds-card__header ${className}`.trim()}>{children}</div>
}

export function CardBody({ children, className = '' }) {
  return <div className={`ds-card__body ${className}`.trim()}>{children}</div>
}

export function CardFooter({ children, className = '' }) {
  return <div className={`ds-card__footer ${className}`.trim()}>{children}</div>
}

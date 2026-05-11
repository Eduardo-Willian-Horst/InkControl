import './Table.css'

export function TableWrap({ children }) {
  return <div className="ds-table-wrap">{children}</div>
}

export function Table({ children }) {
  return (
    <table className="ds-table">
      <tbody>{children}</tbody>
    </table>
  )
}

export function TableWithHead({ head, children }) {
  return (
    <table className="ds-table">
      <thead>
        <tr>{head}</tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}

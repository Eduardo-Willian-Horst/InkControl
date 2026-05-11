import { Button } from './Button'
import './PaginationBar.css'

export function PaginationBar({ count, pageSize, page, onPageChange, loading }) {
  const totalPages = Math.max(1, Math.ceil((count || 0) / pageSize))
  const canPrev = page > 1
  const canNext = page < totalPages

  return (
    <div className="ds-pagination">
      <span className="ds-pagination__meta">
        Página {page} de {totalPages} ({count ?? 0} registros)
      </span>
      <div className="ds-pagination__actions">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={!canPrev || loading}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={!canNext || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima
        </Button>
      </div>
    </div>
  )
}

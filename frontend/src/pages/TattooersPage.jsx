import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import { ROLES } from '../lib/constants'
import { tattooerPortraitSrc } from '../lib/tattooerPortrait'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Field, Input } from '../components/ui/Field'
import { PaginationBar } from '../components/ui/PaginationBar'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'
import './tattooers-vitrine.css'

const PAGE_SIZE = 10

export function TattooersPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isStudio = user?.role === ROLES.studio
  const isClient = user?.role === ROLES.client

  const [q, setQ] = useState('')
  const [isActive, setIsActive] = useState(isStudio ? '' : 'true')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ count: 0, results: [] })

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      const params = new URLSearchParams()
      params.set('page', String(page))
      if (q.trim()) params.set('q', q.trim())
      if (isActive === 'true' || isActive === 'false') params.set('is_active', isActive)
      try {
        const res = await apiFetch(`/api/tattooers/?${params.toString()}`)
        if (!cancelled) setData({ count: res.count ?? 0, results: res.results ?? [] })
      } catch (e) {
        if (!cancelled) setError(e.message ?? String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [page, q, isActive, reloadKey])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setReloadKey((k) => k + 1)
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">{isClient ? 'Profissionais' : 'Tatuadores'}</h1>
          <p className="ic-vitrine-intro ic-page__lede">
            {isClient
              ? 'Toque em um perfil para ver detalhes e agendar sua sessão com quem faz o seu estilo.'
              : 'Vitrine do estúdio. Clientes escolhem o profissional e agendam a partir da página de cada um.'}
          </p>
        </div>
        {isStudio ? (
          <Button type="button" onClick={() => navigate('/tatuadores/novo')}>
            Cadastrar tatuador
          </Button>
        ) : null}
      </div>

      <form className="ic-vitrine-toolbar" onSubmit={handleSearch}>
        <Field label="Buscar" id="tattooers-q">
          <Input
            id="tattooers-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nome, estilo ou contato"
          />
        </Field>
        {isStudio ? (
          <Field label="Mostrar" id="tattooers-active">
            <Select
              id="tattooers-active"
              value={isActive}
              onChange={(e) => setIsActive(e.target.value)}
            >
              <option value="">Ativos e inativos</option>
              <option value="true">Só ativos</option>
              <option value="false">Só inativos</option>
            </Select>
          </Field>
        ) : null}
        <Button type="submit" variant="secondary">
          Buscar
        </Button>
      </form>

      {error ? (
        <div className="ic-mt-4">
          <Alert variant="error">{error}</Alert>
        </div>
      ) : null}

      {loading ? (
        <div className="ic-loading-block">
          <Spinner large role="status" aria-label="Carregando profissionais" />
        </div>
      ) : null}

      {!loading && !error && data.results.length === 0 ? (
        <p className="ic-muted">Nenhum profissional encontrado com esses critérios.</p>
      ) : null}

      {!loading && !error && data.results.length > 0 ? (
        <>
          <div className="ic-vitrine-grid">
            {data.results.map((row) => {
              const src = tattooerPortraitSrc(row.id, row.name)
              const first = row.name?.split(' ')[0] || row.name
              return (
                <div key={row.id} className="ic-vitrine-card-wrap">
                  <Link to={`/tatuadores/${row.id}`} className="ic-vitrine-card">
                    <span className="ic-vitrine-card__media">
                      <img
                        src={src}
                        alt={`Retrato ilustrativo de ${row.name}`}
                        width={320}
                        height={400}
                        loading="lazy"
                        decoding="async"
                      />
                    </span>
                    <span className="ic-vitrine-card__body">
                      <span className="ic-vitrine-card__name">{row.name}</span>
                      <span className="ic-vitrine-card__style">{row.artistic_style}</span>
                      <span className="ic-vitrine-card__cta">Ver perfil de {first}</span>
                    </span>
                  </Link>
                  {isStudio ? (
                    <div className="ic-vitrine-admin">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/tatuadores/${row.id}/editar`)}
                      >
                        Editar
                      </Button>
                      {!row.is_active ? <span className="ic-muted">Inativo</span> : null}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
          <PaginationBar
            count={data.count}
            pageSize={PAGE_SIZE}
            page={page}
            loading={loading}
            onPageChange={setPage}
          />
        </>
      ) : null}
    </>
  )
}

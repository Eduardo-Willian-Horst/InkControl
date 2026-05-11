import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'

function toInputTime(value) {
  if (!value) return ''
  const s = String(value)
  return s.length >= 5 ? s.slice(0, 5) : s
}

export function StudioSettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [opensAt, setOpensAt] = useState('')
  const [closesAt, setClosesAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      try {
        const data = await apiFetch('/api/studio-settings/')
        if (!cancelled) {
          setOpensAt(toInputTime(data.opens_at))
          setClosesAt(toInputTime(data.closes_at))
        }
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
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await apiFetch('/api/studio-settings/', {
        method: 'PATCH',
        body: JSON.stringify({
          opens_at: opensAt.length === 5 ? `${opensAt}:00` : opensAt,
          closes_at: closesAt.length === 5 ? `${closesAt}:00` : closesAt,
        }),
      })
    } catch (e) {
      setError(e.message ?? String(e))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando horário do estúdio" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Horário do estúdio</h1>
          <p className="ic-page__lede">
            Define o expediente usado para validar novos agendamentos e a regra dos 30 minutos
            antes do fechamento.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2>Expediente</h2>
        </CardHeader>
        <CardBody>
          {error ? (
            <div className="ic-mb-2">
              <Alert variant="error">{error}</Alert>
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            <Field label="Abertura" id="st-open">
              <Input
                id="st-open"
                type="time"
                required
                value={opensAt}
                onChange={(e) => setOpensAt(e.target.value)}
              />
            </Field>
            <Field label="Fechamento" id="st-close">
              <Input
                id="st-close"
                type="time"
                required
                value={closesAt}
                onChange={(e) => setClosesAt(e.target.value)}
              />
            </Field>
            <div className="ic-form-actions">
              <Button type="submit" variant="primary" disabled={saving}>
                {saving ? 'Salvando…' : 'Salvar'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </>
  )
}

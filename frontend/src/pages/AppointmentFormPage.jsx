import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import {
  APPOINTMENT_KIND_LABELS,
  APPOINTMENT_STATUS_LABELS,
  ROLES,
  STATUS_TRANSITIONS,
} from '../lib/constants'
import { formatDateTime, fromDatetimeLocalValue, toDatetimeLocalValue } from '../lib/format'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { tattooerPortraitSrc } from '../lib/tattooerPortrait'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Select } from '../components/ui/Select'
import { Textarea } from '../components/ui/Textarea'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'
import './tattooers-vitrine.css'

function clientPkFromAppointment(a) {
  if (a?.client && typeof a.client === 'object') return String(a.client.id)
  return a?.client != null ? String(a.client) : ''
}

function tattooerPkFromAppointment(a) {
  if (a?.tattooer && typeof a.tattooer === 'object') return String(a.tattooer.id)
  return a?.tattooer != null ? String(a.tattooer) : ''
}

function tattooerBriefFromAppointment(a) {
  if (a?.tattooer && typeof a.tattooer === 'object') return a.tattooer
  return null
}

export function AppointmentFormPage() {
  const { id: appointmentId, tattooerId: tattooerIdFromUrl } = useParams()
  const isNew = !appointmentId
  const navigate = useNavigate()

  const [me, setMe] = useState(null)
  const [presetTattooer, setPresetTattooer] = useState(null)
  const [tattooers, setTattooers] = useState([])
  const [updatedAt, setUpdatedAt] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState('')

  const [clients, setClients] = useState([])

  const [clientId, setClientId] = useState('')
  const [tattooerId, setTattooerId] = useState('')
  const [scheduledLocal, setScheduledLocal] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('requested')
  const [appointmentKind, setAppointmentKind] = useState('service')
  const [referenceImageFile, setReferenceImageFile] = useState(null)
  const [referenceImageUrl, setReferenceImageUrl] = useState('')
  const [healthSummary, setHealthSummary] = useState(null)

  const [changeRequests, setChangeRequests] = useState([])
  const [crKey, setCrKey] = useState(0)
  const [proposedLocal, setProposedLocal] = useState('')
  const [crBusyId, setCrBusyId] = useState(null)
  const [baseline, setBaseline] = useState(null)

  const fromTattooerPage = Boolean(tattooerIdFromUrl)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      setLoading(true)
      setError('')
      try {
        const user = await apiFetch('/api/auth/me/')
        if (cancelled) return
        setMe(user)

        if (fromTattooerPage && tattooerIdFromUrl) {
          const t = await apiFetch(`/api/tattooers/${tattooerIdFromUrl}/`)
          if (cancelled) return
          setPresetTattooer(t)
          setTattooerId(String(t.id))
        } else if (!isNew) {
          setPresetTattooer(null)
        } else {
          setPresetTattooer(null)
        }

        if (user.role === ROLES.studio) {
          try {
            const c = await fetchAllPaginated('/api/clients/?page=1')
            if (!cancelled) setClients(c.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setClients([])
          }
          try {
            const tlist = await fetchAllPaginated('/api/tattooers/?page=1')
            if (!cancelled) setTattooers(tlist.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setTattooers([])
          }
        } else if (user.role === ROLES.tattooer) {
          try {
            const c = await fetchAllPaginated('/api/clients/?page=1')
            if (!cancelled) setClients(c.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setClients([])
          }
          setTattooers([])
        } else {
          setClients([])
          setTattooers([])
        }

        if (!isNew && appointmentId) {
          const a = await apiFetch(`/api/appointments/${appointmentId}/`)
          if (cancelled) return
          setClientId(clientPkFromAppointment(a))
          setTattooerId(tattooerPkFromAppointment(a))
          setScheduledLocal(toDatetimeLocalValue(a.scheduled_at))
          setDescription(a.description ?? '')
          setStatus(a.status ?? 'requested')
          setAppointmentKind(a.appointment_kind ?? 'service')
          setUpdatedAt(a.updated_at ?? '')
          setReferenceImageUrl(a.reference_image ?? '')
          setHealthSummary(a.health_summary ?? null)
          setBaseline({
            scheduled_at: a.scheduled_at,
            description: a.description ?? '',
            appointment_kind: a.appointment_kind ?? 'service',
            tattooer: Number(tattooerPkFromAppointment(a)),
            client: Number(clientPkFromAppointment(a)),
            status: a.status ?? 'requested',
            duration_minutes: a.duration_minutes ?? 60,
          })
          const brief = tattooerBriefFromAppointment(a)
          if (brief) {
            setPresetTattooer(brief)
          } else if (tattooerPkFromAppointment(a)) {
            const t = await apiFetch(`/api/tattooers/${tattooerPkFromAppointment(a)}/`)
            if (!cancelled) setPresetTattooer(t)
          }
        }
      } catch (e) {
        if (!cancelled) setError(e.message ?? String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    boot()
    return () => {
      cancelled = true
    }
  }, [appointmentId, fromTattooerPage, isNew, tattooerIdFromUrl])

  useEffect(() => {
    if (isNew || !appointmentId) return undefined
    let cancelled = false
    async function run() {
      try {
        const res = await apiFetch(`/api/appointment-change-requests/?appointment=${appointmentId}`)
        if (!cancelled) setChangeRequests(res.results ?? [])
      } catch {
        if (!cancelled) setChangeRequests([])
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [appointmentId, isNew, crKey])

  const isTattooer = me?.role === ROLES.tattooer
  const isStudio = me?.role === ROLES.studio
  const isClient = me?.role === ROLES.client
  const canDelete = isStudio && !isNew

  const showTattooerSelect = !(fromTattooerPage && isNew) && !isClient
  const showClientPicker = (isStudio || (isTattooer && !isNew)) && !isClient

  const statusOptions = useMemo(() => {
    if (isNew) return ['requested']
    const next = STATUS_TRANSITIONS[status] ?? []
    const uniq = new Set([status, ...next])
    return Array.from(uniq)
  }, [isNew, status])

  function goBack() {
    if (fromTattooerPage && tattooerIdFromUrl) {
      navigate(`/tatuadores/${tattooerIdFromUrl}`)
      return
    }
    navigate('/agendamentos')
  }

  async function reloadAppointmentDetail() {
    if (!appointmentId) return
    const a = await apiFetch(`/api/appointments/${appointmentId}/`)
    setClientId(clientPkFromAppointment(a))
    setTattooerId(tattooerPkFromAppointment(a))
    setScheduledLocal(toDatetimeLocalValue(a.scheduled_at))
    setDescription(a.description ?? '')
    setStatus(a.status ?? 'requested')
    setUpdatedAt(a.updated_at ?? '')
    setReferenceImageUrl(a.reference_image ?? '')
    setHealthSummary(a.health_summary ?? null)
    setAppointmentKind(a.appointment_kind ?? 'service')
    const brief = tattooerBriefFromAppointment(a)
    if (brief) setPresetTattooer(brief)
    setBaseline({
      scheduled_at: a.scheduled_at,
      description: a.description ?? '',
      appointment_kind: a.appointment_kind ?? 'service',
      tattooer: Number(tattooerPkFromAppointment(a)),
      client: Number(clientPkFromAppointment(a)),
      status: a.status ?? 'requested',
      duration_minutes: a.duration_minutes ?? 60,
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (!isNew && !isStudio && me) {
        if (!baseline) {
          setError('Aguarde o carregamento dos dados antes de salvar.')
          setSaving(false)
          return
        }
        if (status !== baseline.status) {
          await apiFetch(`/api/appointments/${appointmentId}/`, {
            method: 'PATCH',
            body: JSON.stringify({ status }),
          })
        }
        const scheduledIso = fromDatetimeLocalValue(scheduledLocal)
        const proposedChanges = {}
        if (scheduledIso !== baseline.scheduled_at) {
          proposedChanges.scheduled_at = scheduledIso
        }
        if (description !== baseline.description) {
          proposedChanges.description = description
        }
        if (appointmentKind !== baseline.appointment_kind) {
          proposedChanges.appointment_kind = appointmentKind
        }
        if (Number(tattooerId) !== baseline.tattooer) {
          proposedChanges.tattooer = Number(tattooerId)
        }
        const hasImage = Boolean(referenceImageFile)
        const hasAgenda = Object.keys(proposedChanges).length > 0 || hasImage
        const statusChanged = status !== baseline.status
        if (!statusChanged && !hasAgenda) {
          setError('Nenhuma alteração para salvar.')
          setSaving(false)
          return
        }
        if (hasAgenda) {
          const fd = new FormData()
          fd.append('appointment', String(appointmentId))
          fd.append('proposed_changes', JSON.stringify(proposedChanges))
          if (hasImage) {
            fd.append('proposed_reference_image', referenceImageFile)
          }
          await apiFetch('/api/appointment-change-requests/', { method: 'POST', body: fd })
        }
        navigate('/agendamentos')
        return
      }

      if (isStudio && !isNew) {
        const scheduled_at = fromDatetimeLocalValue(scheduledLocal)
        const useMultipart = Boolean(referenceImageFile)
        if (useMultipart) {
          const fd = new FormData()
          fd.append('tattooer', String(Number(tattooerId)))
          fd.append('scheduled_at', scheduled_at)
          fd.append('description', description)
          fd.append('status', status)
          fd.append('appointment_kind', appointmentKind)
          fd.append('client', String(Number(clientId)))
          fd.append('reference_image', referenceImageFile)
          await apiFetch(`/api/appointments/${appointmentId}/`, {
            method: 'PUT',
            body: fd,
          })
        } else {
          await apiFetch(`/api/appointments/${appointmentId}/`, {
            method: 'PUT',
            body: JSON.stringify({
              tattooer: Number(tattooerId),
              scheduled_at,
              description,
              status,
              appointment_kind: appointmentKind,
              client: Number(clientId),
            }),
          })
        }
        navigate('/agendamentos')
        return
      }

      const scheduled_at = fromDatetimeLocalValue(scheduledLocal)
      const useMultipart = Boolean(referenceImageFile)
      if (useMultipart) {
        const fd = new FormData()
        fd.append('tattooer', String(Number(tattooerId)))
        fd.append('scheduled_at', scheduled_at)
        fd.append('description', description)
        fd.append('status', status)
        fd.append('appointment_kind', appointmentKind)
        if (!(isClient && isNew)) {
          fd.append('client', String(Number(clientId)))
        }
        fd.append('reference_image', referenceImageFile)
        if (isNew) {
          await apiFetch('/api/appointments/', { method: 'POST', body: fd })
        }
      } else {
        const body = {
          tattooer: Number(tattooerId),
          scheduled_at,
          description,
          status,
          appointment_kind: appointmentKind,
        }
        if (!(isClient && isNew)) {
          body.client = Number(clientId)
        }
        if (isNew) {
          await apiFetch('/api/appointments/', { method: 'POST', body: JSON.stringify(body) })
        }
      }
      navigate('/agendamentos')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!canDelete) return
    if (!window.confirm('Excluir este agendamento?')) return
    setRemoving(true)
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/`, { method: 'DELETE' })
      navigate('/agendamentos')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setRemoving(false)
    }
  }

  async function handleCancelAppointment() {
    if (isNew) return
    if (!window.confirm('Cancelar este agendamento?')) return
    setCancelling(true)
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/cancel/`, { method: 'POST' })
      await reloadAppointmentDetail()
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCancelling(false)
    }
  }

  async function handleProposeChange(e) {
    e.preventDefault()
    if (!appointmentId || !proposedLocal.trim()) return
    setSaving(true)
    setError('')
    try {
      const scheduled_at = fromDatetimeLocalValue(proposedLocal)
      await apiFetch('/api/appointment-change-requests/', {
        method: 'POST',
        body: JSON.stringify({
          appointment: Number(appointmentId),
          proposed_changes: { scheduled_at },
        }),
      })
      setProposedLocal('')
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleAcceptChange(id) {
    setCrBusyId(id)
    setError('')
    try {
      await apiFetch(`/api/appointment-change-requests/${id}/accept/`, { method: 'POST' })
      await reloadAppointmentDetail()
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCrBusyId(null)
    }
  }

  async function handleRejectChange(id) {
    setCrBusyId(id)
    setError('')
    try {
      await apiFetch(`/api/appointment-change-requests/${id}/reject/`, { method: 'POST' })
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCrBusyId(null)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando agendamento" />
      </div>
    )
  }

  const portrait = presetTattooer
    ? tattooerPortraitSrc(presetTattooer.id, presetTattooer.name)
    : ''

  const canExplicitCancel =
    !isNew && status !== 'cancelled' && status !== 'done' && (isStudio || isClient || isTattooer)

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">
            {isNew && fromTattooerPage && presetTattooer
              ? `Agendar com ${presetTattooer.name}`
              : isNew
                ? 'Novo agendamento'
                : 'Agendamento'}
          </h1>
          <p className="ic-page__lede">
            {isTattooer && !isNew
              ? 'Atualize o status diretamente. Alterações em data, descrição, modalidade ou imagem geram uma solicitação para o cliente ou estúdio aceitar.'
              : isClient && isNew
                ? 'Escolha data e horário. O estúdio confirma orçamento e detalhes finais.'
                : !isNew && !isStudio && isClient
                  ? 'Alterações em data, descrição, modalidade ou imagem são enviadas como solicitação; a outra parte precisa aceitar antes de valer.'
                  : 'Datas em conflito com o mesmo tatuador são bloqueadas automaticamente.'}
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={goBack}>
          Voltar
        </Button>
      </div>

      {isNew && fromTattooerPage && presetTattooer ? (
        <div className="ic-profile-hero ic-mb-2">
          <div className="ic-profile-hero__media ic-profile-hero__media--compact">
            <img src={portrait} alt="" decoding="async" />
          </div>
          <div>
            <p className="ic-muted ic-mb-2">{presetTattooer.artistic_style}</p>
            <p className="ic-muted">Contato: {presetTattooer.contact}</p>
          </div>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <h2>{isNew ? 'Solicitação' : 'Detalhes'}</h2>
        </CardHeader>
        <CardBody>
          {error ? (
            <div className="ic-mb-2">
              <Alert variant="error">{error}</Alert>
            </div>
          ) : null}

          {!isNew && updatedAt ? (
            <p className="ic-muted ic-mb-2">Última atualização: {formatDateTime(updatedAt)}</p>
          ) : null}

          {!isNew && healthSummary?.has_alerts ? (
            <div className="ic-mb-2">
              <Alert variant="error">
                <strong>Ficha de saúde (resumo):</strong>{' '}
                {healthSummary.allergies_preview ? (
                  <span> Alergias: {healthSummary.allergies_preview}</span>
                ) : null}{' '}
                {healthSummary.chronic_diseases_preview ? (
                  <span> Condições: {healthSummary.chronic_diseases_preview}</span>
                ) : null}
              </Alert>
            </div>
          ) : null}

          {!isNew && referenceImageUrl ? (
            <div className="ic-mb-2">
              <p className="ic-muted ic-mb-2">Imagem de referência</p>
              <img
                src={referenceImageUrl}
                alt="Referência do agendamento"
                className="ic-appt-ref-thumb"
              />
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            {isTattooer && !isNew ? null : (
              <>
                {isClient && isNew ? (
                  <p className="ic-muted ic-mb-2">Você está agendando em seu próprio nome.</p>
                ) : null}

                {showClientPicker ? (
                  <>
                    {clients.length > 0 ? (
                      <Field label="Cliente" id="a-client">
                        <Select
                          id="a-client"
                          required
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                        >
                          <option value="">Selecione</option>
                          {clients.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name} — {c.email}
                            </option>
                          ))}
                        </Select>
                      </Field>
                    ) : isStudio ? (
                      <div className="ic-mb-2">
                        <Alert variant="error">
                          Não há clientes cadastrados. Cadastre um cliente em Clientes antes de
                          agendar.
                        </Alert>
                      </div>
                    ) : null}
                  </>
                ) : null}

                {presetTattooer && (fromTattooerPage || !showTattooerSelect) ? (
                  <Field label="Profissional" id="a-tattooer-ro">
                    <Input id="a-tattooer-ro" value={presetTattooer.name} disabled />
                  </Field>
                ) : showTattooerSelect ? (
                  tattooers.length > 0 ? (
                    <Field label="Profissional" id="a-tattooer">
                      <Select
                        id="a-tattooer"
                        required
                        value={tattooerId}
                        onChange={(e) => setTattooerId(e.target.value)}
                      >
                        <option value="">Selecione</option>
                        {tattooers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name} — {t.artistic_style}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  ) : isStudio ? (
                    <div className="ic-mb-2">
                      <Alert variant="error">
                        Não há profissionais cadastrados. Cadastre um tatuador antes de agendar.
                      </Alert>
                    </div>
                  ) : null
                ) : null}

                <Field label="Data e hora" id="a-when">
                  <Input
                    id="a-when"
                    type="datetime-local"
                    required
                    value={scheduledLocal}
                    onChange={(e) => setScheduledLocal(e.target.value)}
                  />
                </Field>
              </>
            )}

            {isTattooer && !isNew ? (
              <Field label="Modalidade" id="a-kind-t">
                <Select
                  id="a-kind-t"
                  value={appointmentKind}
                  onChange={(e) => setAppointmentKind(e.target.value)}
                >
                  <option value="service">{APPOINTMENT_KIND_LABELS.service}</option>
                  <option value="consultation">{APPOINTMENT_KIND_LABELS.consultation}</option>
                </Select>
              </Field>
            ) : null}

            {isTattooer && !isNew ? (
              <Field label="Imagem de referência (opcional)" id="a-img-t">
                <Input
                  id="a-img-t"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setReferenceImageFile(e.target.files?.[0] ?? null)}
                />
              </Field>
            ) : !isTattooer || isNew ? (
              <Field label="Imagem de referência (opcional)" id="a-img">
                <Input
                  id="a-img"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setReferenceImageFile(e.target.files?.[0] ?? null)}
                />
              </Field>
            ) : null}

            <Field label="O que você quer fazer / referência" id="a-desc">
              <Textarea
                id="a-desc"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descreva a tatuagem, tamanho, local do corpo…"
              />
            </Field>

            {isNew || !(isTattooer && !isNew) ? (
              <Field label="Modalidade" id="a-kind">
                <Select
                  id="a-kind"
                  value={appointmentKind}
                  onChange={(e) => setAppointmentKind(e.target.value)}
                >
                  <option value="service">{APPOINTMENT_KIND_LABELS.service}</option>
                  <option value="consultation">{APPOINTMENT_KIND_LABELS.consultation}</option>
                </Select>
              </Field>
            ) : null}

            {!isNew ? (
              <Field label="Status" id="a-status">
                <Select
                  id="a-status"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {statusOptions.map((s) => (
                    <option key={s} value={s}>
                      {APPOINTMENT_STATUS_LABELS[s] ?? s}
                    </option>
                  ))}
                </Select>
              </Field>
            ) : null}

            <div className="ic-form-actions">
              <Button type="submit" variant="primary" disabled={saving || removing || cancelling}>
                {saving ? 'Salvando…' : 'Salvar'}
              </Button>
              <Button type="button" variant="ghost" disabled={saving || removing} onClick={goBack}>
                Voltar à lista
              </Button>
              {canExplicitCancel ? (
                <Button
                  type="button"
                  variant="danger"
                  disabled={saving || removing || cancelling}
                  onClick={handleCancelAppointment}
                >
                  {cancelling ? 'Cancelando…' : 'Cancelar agendamento'}
                </Button>
              ) : null}
              {canDelete ? (
                <Button
                  type="button"
                  variant="danger"
                  disabled={saving || removing}
                  onClick={handleDelete}
                >
                  {removing ? 'Excluindo…' : 'Excluir'}
                </Button>
              ) : null}
            </div>
          </form>
        </CardBody>
      </Card>

      {!isNew ? (
        <Card className="ic-mt-4">
          <CardHeader>
            <h2>Solicitações de alteração</h2>
          </CardHeader>
          <CardBody>
            <ul className="ic-cr-list">
              {changeRequests.map((cr) => (
                <li key={cr.id} className="ic-cr-list__item">
                  <div>
                    <strong>{cr.proposed_summary ?? 'Alteração'}</strong>
                    <span className="ic-muted"> — {cr.requested_by_display}</span>
                    {cr.proposed_scheduled_at ? (
                      <div className="ic-muted">
                        Horário proposto: {formatDateTime(cr.proposed_scheduled_at)}
                      </div>
                    ) : null}
                    <div className="ic-muted">
                      Status: {cr.status === 'pending' ? 'Pendente' : cr.status === 'accepted' ? 'Aceito' : 'Recusado'}
                    </div>
                  </div>
                  <div className="ic-inline-actions">
                    {cr.status === 'pending' && cr.can_respond ? (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          variant="primary"
                          disabled={crBusyId === cr.id}
                          onClick={() => handleAcceptChange(cr.id)}
                        >
                          Aceitar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={crBusyId === cr.id}
                          onClick={() => handleRejectChange(cr.id)}
                        >
                          Recusar
                        </Button>
                      </>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>

            <form className="ic-mt-4" onSubmit={handleProposeChange}>
              <Field label="Novo horário sugerido" id="a-cr-when">
                <Input
                  id="a-cr-when"
                  type="datetime-local"
                  value={proposedLocal}
                  onChange={(e) => setProposedLocal(e.target.value)}
                />
              </Field>
              <Button type="submit" variant="secondary" disabled={saving}>
                Enviar pedido de alteração
              </Button>
            </form>
          </CardBody>
        </Card>
      ) : null}
    </>
  )
}

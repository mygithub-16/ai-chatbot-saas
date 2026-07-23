import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { readJsonResponse } from '../utils/http'
import { emitToast } from '../utils/toast'

const emptyBusinessForm = {
  id: null,
  name: '',
  business_name: '',
  business_description: '',
  services_products: '',
  faqs: '',
  policies: '',
  tone_style: 'friendly and professional',
  personality_prompt: '',
  owner_email: '',
  lead_capture_enabled: true,
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value || 0))
}

function formatPercent(value) {
  const numericValue = Number(value || 0)
  return `${Number.isFinite(numericValue) ? numericValue.toFixed(1) : '0.0'}%`
}

function toFormState(business) {
  return {
    id: business.id,
    name: business.name || '',
    business_name: business.business_name || '',
    business_description: business.business_description || '',
    services_products: business.services_products || '',
    faqs: business.faqs || '',
    policies: business.policies || '',
    tone_style: business.tone_style || 'friendly and professional',
    personality_prompt: business.personality_prompt || '',
    owner_email: business.owner_email || '',
    lead_capture_enabled: Boolean(business.lead_capture_enabled),
  }
}

export default function AnalyticsDashboard({ authToken, onLogout }) {
  const [overview, setOverview] = useState(null)
  const [funnel, setFunnel] = useState(null)
  const [leads, setLeads] = useState(null)
  const [activity, setActivity] = useState([])
  const [businessPerformance, setBusinessPerformance] = useState([])
  const [adminBusinesses, setAdminBusinesses] = useState([])
  const [recentLeads, setRecentLeads] = useState([])
  const [businessForm, setBusinessForm] = useState(emptyBusinessForm)
  const [loading, setLoading] = useState(true)
  const [savingBusiness, setSavingBusiness] = useState(false)
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')

  const authHeaders = useMemo(() => {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`, // Essential structure matching backend admin_route_guard split pattern
      'X-User-Id': '1' // Passes user identification index
    }
  }, [authToken])

  const loadAnalytics = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const [overviewResponse, funnelResponse, leadsResponse, activityResponse, businessesResponse, adminBusinessesResponse] = await Promise.all([
        fetch('/analytics/overview', { headers: authHeaders }),
        fetch('/analytics/funnel', { headers: authHeaders }),
        fetch('/analytics/leads', { headers: authHeaders }),
        fetch('/analytics/activity', { headers: authHeaders }),
        fetch('/analytics/businesses', { headers: authHeaders }),
        fetch('/admin/businesses', { headers: authHeaders }),
      ])

      if ([overviewResponse, funnelResponse, leadsResponse, activityResponse, businessesResponse, adminBusinessesResponse].some((response) => response.status === 401)) {
        throw new Error('Admin authentication required')
      }

      const overviewPayload = await readJsonResponse(overviewResponse)
      const funnelPayload = await readJsonResponse(funnelResponse)
      const leadsPayload = await readJsonResponse(leadsResponse)
      const activityPayload = await readJsonResponse(activityResponse)
      const businessesPayload = await readJsonResponse(businessesResponse)
      const adminBusinessesPayload = await readJsonResponse(adminBusinessesResponse)

      setOverview(overviewPayload)
      setFunnel(funnelPayload)
      setLeads(leadsPayload)
      setRecentLeads(Array.isArray(leadsPayload?.recent_leads) ? leadsPayload.recent_leads : [])
      setActivity(Array.isArray(activityPayload?.activity) ? activityPayload.activity : [])
      setBusinessPerformance(Array.isArray(businessesPayload?.businesses) ? businessesPayload.businesses : [])
      setAdminBusinesses(Array.isArray(adminBusinessesPayload?.businesses) ? adminBusinessesPayload.businesses : [])
    } catch (loadError) {
      setError(loadError.message || 'Failed to load analytics')
      emitToast({
        title: 'Analytics load failed',
        message: loadError.message || 'Please refresh and try again.',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [authHeaders])

  useEffect(() => {
    loadAnalytics()
  }, [loadAnalytics])

  const overviewCards = [
    { label: 'Page views', value: overview?.page_views },
    { label: 'Demo starts', value: overview?.demo_starts },
    { label: 'Demo completions', value: overview?.demo_completions },
    { label: 'Leads', value: overview?.leads },
    { label: 'Conversion', value: formatPercent(overview?.overall_conversion_rate) },
  ]

  const funnelRows = funnel?.stages || []
  const biggestDropOff = funnel?.biggest_dropoff_stage || null
  const leadCards = [
    { label: 'Hot', value: leads?.hot },
    { label: 'Warm', value: leads?.warm },
    { label: 'Cold', value: leads?.cold },
    { label: 'Average score', value: leads?.average_score ? leads.average_score.toFixed(1) : '0.0' },
  ]

  const handleBusinessFieldChange = (fieldName, value) => {
    setBusinessForm((current) => ({
      ...current,
      [fieldName]: value,
    }))
  }

  const handleSelectBusiness = (business) => {
    setBusinessForm(toFormState(business))
    setSaveMessage('')
  }

  const handleResetBusinessForm = () => {
    setBusinessForm(emptyBusinessForm)
    setSaveMessage('')
  }

  const handleBusinessSubmit = async (event) => {
    event.preventDefault()
    setSavingBusiness(true)
    setError('')
    setSaveMessage('')

    try {
      const endpoint = businessForm.id ? `/admin/businesses/${businessForm.id}` : '/admin/businesses'
      const method = businessForm.id ? 'PATCH' : 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: authHeaders,
        body: JSON.stringify({
          name: businessForm.name,
          business_name: businessForm.business_name || businessForm.name,
          business_description: businessForm.business_description,
          services_products: businessForm.services_products,
          faqs: businessForm.faqs,
          policies: businessForm.policies,
          tone_style: businessForm.tone_style,
          personality_prompt: businessForm.personality_prompt,
          owner_email: businessForm.owner_email || null,
          lead_capture_enabled: businessForm.lead_capture_enabled,
        }),
      })

      const payload = await readJsonResponse(response)

      if (!response.ok) {
        throw new Error(payload.detail || 'Unable to save business')
      }

      setSaveMessage(businessForm.id ? 'Business updated.' : 'Business created.')
      emitToast({
        title: businessForm.id ? 'Business updated' : 'Business created',
        message: 'Your admin record has been saved.',
        tone: 'success',
      })
      await loadAnalytics()
      if (payload?.business) {
        setBusinessForm(toFormState(payload.business))
      } else {
        handleResetBusinessForm()
      }
    } catch (submitError) {
      setError(submitError.message || 'Unable to save business')
      emitToast({
        title: 'Save failed',
        message: submitError.message || 'Unable to save business.',
        tone: 'error',
      })
    } finally {
      setSavingBusiness(false)
    }
  }

  if (loading) {
    return (
      <main className="page-section analytics-page">
        <section className="analytics-header">
          <div className="skeleton-heading-block">
            <div className="skeleton skeleton-line skeleton-eyebrow" />
            <div className="skeleton skeleton-line skeleton-title" />
            <div className="skeleton skeleton-line skeleton-subtitle" />
          </div>
          <div className="skeleton skeleton-button" />
        </section>
        <section className="dashboard-grid">
          {Array.from({ length: 5 }).map((_, index) => (
            <article key={index} className="dashboard-card">
              <div className="skeleton skeleton-line skeleton-card-label" />
              <div className="skeleton skeleton-line skeleton-metric" />
            </article>
          ))}
        </section>
        <section className="analytics-layout">
          <div className="skeleton-panel" />
          <div className="skeleton-panel" />
        </section>
      </main>
    )
  }

  return (
    <main className="page-section analytics-page">
      <section className="analytics-header">
        <div>
          <div className="section-eyebrow">Admin dashboard</div>
          <h1>Real-time analytics</h1>
          <p>Protected operator view for funnel, lead quality, business performance, and business setup.</p>
        </div>

        <button className="secondary-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </section>

      {error ? <div className="analytics-banner">{error}</div> : null}
      {loading ? <div className="analytics-banner">Loading analytics…</div> : null}
      {saveMessage ? <div className="analytics-banner success">{saveMessage}</div> : null}

      <section className="dashboard-grid">
        {overviewCards.map((card) => (
          <article key={card.label} className="dashboard-card">
            <span className="card-label">{card.label}</span>
            <strong className="metric-value">{formatNumber(card.value)}</strong>
          </article>
        ))}
      </section>

      <section className="analytics-layout">
        <article className="analytics-panel">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Business setup</span>
              <h2>Define the AI context</h2>
            </div>
            <button className="secondary-button compact" onClick={handleResetBusinessForm} type="button">
              New business
            </button>
          </div>

          <div className="business-selector">
            {adminBusinesses.length ? (
              adminBusinesses.map((business) => (
                <button
                  key={business.id}
                  type="button"
                  className={`business-selector-item ${businessForm.id === business.id ? 'active' : ''}`}
                  onClick={() => handleSelectBusiness(business)}
                >
                  <strong>{business.business_name || business.name}</strong>
                  <span>{business.tone_style || 'friendly and professional'}</span>
                </button>
              ))
            ) : (
              <p className="empty-state">No businesses yet. Create one below.</p>
            )}
          </div>

          <form className="business-form" onSubmit={handleBusinessSubmit}>
            <div className="form-grid">
              <label>
                <span>Business name</span>
                <input
                  value={businessForm.name}
                  onChange={(event) => handleBusinessFieldChange('name', event.target.value)}
                  placeholder="ECHURA Salon"
                  required
                />
              </label>
              <label>
                <span>Display name</span>
                <input
                  value={businessForm.business_name}
                  onChange={(event) => handleBusinessFieldChange('business_name', event.target.value)}
                  placeholder="ECHURA Salon"
                />
              </label>
            </div>

            <label>
              <span>Business description</span>
              <textarea
                value={businessForm.business_description}
                onChange={(event) => handleBusinessFieldChange('business_description', event.target.value)}
                placeholder="What does the business do?"
                rows={3}
              />
            </label>

            <label>
              <span>Services / products</span>
              <textarea
                value={businessForm.services_products}
                onChange={(event) => handleBusinessFieldChange('services_products', event.target.value)}
                placeholder="Haircuts, styling, beard trims..."
                rows={3}
              />
            </label>

            <div className="form-grid">
              <label>
                <span>FAQs</span>
                <textarea
                  value={businessForm.faqs}
                  onChange={(event) => handleBusinessFieldChange('faqs', event.target.value)}
                  placeholder="Opening hours, turnaround times..."
                  rows={3}
                />
              </label>
              <label>
                <span>Policies</span>
                <textarea
                  value={businessForm.policies}
                  onChange={(event) => handleBusinessFieldChange('policies', event.target.value)}
                  placeholder="Deposits, refunds, booking rules..."
                  rows={3}
                />
              </label>
            </div>

            <div className="form-grid">
              <label>
                <span>Tone / style</span>
                <input
                  value={businessForm.tone_style}
                  onChange={(event) => handleBusinessFieldChange('tone_style', event.target.value)}
                  placeholder="warm, friendly, and reassuring"
                />
              </label>
              <label>
                <span>Owner email</span>
                <input
                  type="email"
                  value={businessForm.owner_email}
                  onChange={(event) => handleBusinessFieldChange('owner_email', event.target.value)}
                  placeholder="owner@business.com"
                />
              </label>
            </div>

            <label>
              <span>Personality prompt</span>
              <textarea
                value={businessForm.personality_prompt}
                onChange={(event) => handleBusinessFieldChange('personality_prompt', event.target.value)}
                placeholder="You are a friendly salon assistant..."
                rows={3}
              />
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={businessForm.lead_capture_enabled}
                onChange={(event) => handleBusinessFieldChange('lead_capture_enabled', event.target.checked)}
              />
              <span>Lead capture enabled</span>
            </label>

            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={savingBusiness}>
                {savingBusiness ? 'Saving...' : businessForm.id ? 'Update business' : 'Create business'}
              </button>
            </div>
          </form>
        </article>

        <article className="analytics-panel">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Funnel</span>
              <h2>Conversion stages</h2>
            </div>
            {biggestDropOff ? <span className="status-pill warning">Biggest drop-off: {biggestDropOff}</span> : null}
          </div>

          <div className="funnel-list">
            {funnelRows.map((stage) => (
              <div key={stage.stage} className="funnel-row">
                <div>
                  <strong>{stage.stage}</strong>
                  <p>{formatNumber(stage.count)} events</p>
                </div>
                <div className="funnel-meta">
                  <span>{formatPercent(stage.conversion_rate_from_previous)}</span>
                  <small>drop-off {formatPercent(stage.dropoff_rate)}</small>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="analytics-panel full-width">
        <div className="panel-header">
          <div>
            <span className="section-eyebrow">Recent leads</span>
            <h2>Latest submissions</h2>
          </div>
        </div>

        <div className="business-list compact">
          {recentLeads.length ? (
            recentLeads.map((lead) => (
              <div key={lead.id} className="business-row">
                <div>
                  <strong>{lead.name}</strong>
                  <p>
                    {lead.business_type || 'lead'} • {lead.source || 'unknown'}
                  </p>
                </div>
                <span>
                  {lead.status || 'NEW'} · {lead.buying_probability ?? 0}%
                </span>
              </div>
            ))
          ) : (
            <p className="empty-state">No leads yet.</p>
          )}
        </div>
      </section>

      <section className="analytics-layout">
        <article className="analytics-panel">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Leads</span>
              <h2>Lead quality</h2>
            </div>
          </div>

          <div className="lead-grid">
            {leadCards.map((card) => (
              <div key={card.label} className="lead-chip">
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="analytics-panel">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Activity</span>
              <h2>Recent events</h2>
            </div>
          </div>

          <div className="activity-feed">
            {activity.length ? (
              activity.map((event) => (
                <div key={event.id ?? `${event.event_name}-${event.timestamp}`} className="activity-item">
                  <strong>{event.event_name}</strong>
                  <span>{event.timestamp}</span>
                </div>
              ))
            ) : (
              <p className="empty-state">No recent events yet.</p>
            )}
          </div>
        </article>
      </section>

      <section className="analytics-panel full-width">
        <div className="panel-header">
          <div>
            <span className="section-eyebrow">Business performance</span>
            <h2>Business comparison</h2>
          </div>
        </div>

        <div className="business-list compact">
          {businessPerformance.length ? (
            businessPerformance.map((business) => (
              <div key={business.id} className="business-row">
                <div>
                  <strong>{business.name}</strong>
                  <p>{business.category || 'business'}</p>
                </div>
                <span>{formatPercent(business.conversion_rate)}</span>
              </div>
            ))
          ) : (
            <p className="empty-state">No business data yet.</p>
          )}
        </div>
      </section>
    </main>
  )
}

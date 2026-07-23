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
  lead_capture_enabled: true,
  plan: 'starter',
  subscription_status: 'trial',
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
    lead_capture_enabled: Boolean(business.lead_capture_enabled),
    plan: business.plan || 'starter',
    subscription_status: business.subscription_status || 'trial',
  }
}

export default function ClientDashboard({ authToken, onLogout }) {
  const [activeTab, setActiveTab] = useState('tuning') // tuning, analytics, leads, widget, billing
  const [business, setBusiness] = useState(null)
  const [businessForm, setBusinessForm] = useState(emptyBusinessForm)
  const [analytics, setAnalytics] = useState(null)
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingSettings, setSavingSettings] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Sandbox Chat State
  const [sandboxMessages, setSandboxMessages] = useState([])
  const [sandboxInput, setSandboxInput] = useState('')
  const [sandboxLoading, setSandboxLoading] = useState(false)
  const [sandboxSessionId] = useState(() => `sandbox-${Math.random().toString(36).substring(2)}-${Date.now()}`)

  // Paystack Billing State
  const [paymentInitializing, setPaymentInitializing] = useState(false)

  const authHeaders = useMemo(() => {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    }
  }, [authToken])

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [businessRes, leadsRes, analyticsRes] = await Promise.all([
        fetch('/api/client/business', { headers: authHeaders }),
        fetch('/api/client/leads', { headers: authHeaders }),
        fetch('/api/client/analytics', { headers: authHeaders }),
      ])

      if (businessRes.status === 401 || leadsRes.status === 401) {
        throw new Error('Authentication expired. Please log in again.')
      }

      const businessData = await readJsonResponse(businessRes)
      const leadsData = await readJsonResponse(leadsRes)
      const analyticsData = await readJsonResponse(analyticsRes)

      if (businessData.business) {
        setBusiness(businessData.business)
        setBusinessForm(toFormState(businessData.business))
      }
      if (Array.isArray(leadsData.leads)) {
        setLeads(leadsData.leads)
      }
      if (analyticsData.totals) {
        setAnalytics(analyticsData)
      }
    } catch (loadError) {
      setError(loadError.message || 'Failed to fetch dashboard data')
      emitToast({
        title: 'Dashboard load failed',
        message: loadError.message || 'Please refresh and try again.',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [authHeaders])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Handle Paystack live payment callback redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const ref = params.get('reference')

    if (ref && business) {
      // Real Paystack callback — webhook already updated the plan in DB, just refresh.
      setSuccessMessage('Payment completed! Your subscription is being updated.')
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash)
      loadData()
    }
  }, [business, loadData])

  // Handle Google Calendar connected callback redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const calConnected = params.get('calendar_connected')
    if (calConnected === 'true') {
      setSuccessMessage('Google Calendar connected successfully!')
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash)
      loadData()
    }
  }, [loadData])

  const handleFieldChange = (fieldName, value) => {
    setBusinessForm((current) => ({
      ...current,
      [fieldName]: value,
    }))
  }

  const handleSettingsSubmit = async (event) => {
    event.preventDefault()
    setSavingSettings(true)
    setError('')
    setSuccessMessage('')
    try {
      const response = await fetch('/api/client/business', {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify(businessForm),
      })
      const payload = await readJsonResponse(response)
      if (!response.ok) throw new Error(payload.detail || 'Unable to update chatbot configuration.')
      
      setSuccessMessage('AI reception guidelines updated successfully!')
      emitToast({
        title: 'Settings saved',
        message: 'Your chatbot guidelines are live.',
        tone: 'success',
      })
      setBusiness(payload.business)
      setBusinessForm(toFormState(payload.business))
      
      // Reset sandbox since backend rules changed
      setSandboxMessages([
        { role: 'assistant', content: `Hi! I've been updated with your new context guidelines. Ask me any question to test my settings.` }
      ])
    } catch (submitError) {
      setError(submitError.message || 'Failed to update settings')
      emitToast({
        title: 'Update failed',
        message: submitError.message || 'Unable to save chatbot settings.',
        tone: 'error',
      })
    } finally {
      setSavingSettings(false)
    }
  }

  const sendSandboxMessage = async (event) => {
    event.preventDefault()
    const text = sandboxInput.trim()
    if (!text || sandboxLoading) return

    setSandboxMessages((prev) => [...prev, { role: 'user', content: text }])
    setSandboxInput('')
    setSandboxLoading(true)

    try {
      const response = await fetch('/api/widget/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sandboxSessionId,
          business_ref: `custom:${businessForm.id}`,
          business_name: businessForm.business_name || businessForm.name,
          business_id: businessForm.id,
        })
      })
      const data = await readJsonResponse(response)
      if (!response.ok) throw new Error(data.detail || 'Could not fetch response')

      const assistantReply = data.response || data.reply || data.message
      if (!assistantReply) throw new Error(data.detail || 'The assistant returned an empty response.')
      setSandboxMessages((prev) => [...prev, { role: 'assistant', content: assistantReply }])
      emitToast({
        title: 'Sandbox reply',
        message: 'The assistant responded with the current configuration.',
        tone: 'success',
      })
    } catch (err) {
      setSandboxMessages((prev) => [...prev, { role: 'assistant', content: err.message || 'The assistant is unavailable right now.' }])
      emitToast({
        title: 'Sandbox error',
        message: err.message || 'The test assistant could not respond.',
        tone: 'error',
      })
    } finally {
      setSandboxLoading(false)
    }
  }

  // Handle plan upgrades using Paystack Redirect Checkout
  const handleUpgradeClick = async (planName) => {
    setError('')
    setSuccessMessage('')
    setPaymentInitializing(true)
    try {
      // Callback URL should point to this client-dashboard, including activeTab=billing so it re-opens the billing page
      const callbackUrl = `${window.location.origin}${window.location.pathname}?plan=${planName}#client-dashboard`
      
      const response = await fetch('/api/client/billing/initialize-paystack', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          plan: planName,
          callback_url: callbackUrl,
        }),
      })

      const data = await readJsonResponse(response)
      if (!response.ok) throw new Error(data.detail || 'Failed to initialize payment session.')

      if (data.authorization_url) {
        // Redirect to Paystack secure checkout host
        window.location.href = data.authorization_url
      } else {
        throw new Error('Payment gateway did not return a valid checkout URL.')
      }
    } catch (err) {
      setError(err.message || 'Payment service unavailable')
      emitToast({
        title: 'Payment setup failed',
        message: err.message || 'Please try again later.',
        tone: 'error',
      })
      setPaymentInitializing(false)
    }
  }

  // Google Calendar Integration
  const [calendarConnecting, setCalendarConnecting] = useState(false)

  const handleConnectCalendar = async () => {
    setCalendarConnecting(true)
    setError('')
    setSuccessMessage('')
    try {
      const response = await fetch('/auth/google-calendar/authorize', {
        headers: authHeaders
      })
      const data = await readJsonResponse(response)
      if (!response.ok) throw new Error(data.detail || 'Failed to initialize calendar link.')
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      } else {
        throw new Error('Google Calendar service did not return authorization URL.')
      }
    } catch (err) {
      setError(err.message || 'Calendar service unavailable')
      emitToast({
        title: 'Calendar connection failed',
        message: err.message || 'Please try again later.',
        tone: 'error',
      })
      setCalendarConnecting(false)
    }
  }

  const handleDisconnectCalendar = async () => {
    setCalendarConnecting(true)
    setError('')
    setSuccessMessage('')
    try {
      const response = await fetch('/api/client/calendar/disconnect', {
        method: 'POST',
        headers: authHeaders
      })
      const data = await readJsonResponse(response)
      if (!response.ok) throw new Error(data.detail || 'Failed to disconnect calendar.')
      setSuccessMessage('Google Calendar disconnected successfully.')
      emitToast({
        title: 'Calendar disconnected',
        message: 'Google Calendar is no longer linked.',
        tone: 'success',
      })
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to disconnect calendar')
      emitToast({
        title: 'Disconnect failed',
        message: err.message || 'The calendar could not be disconnected.',
        tone: 'error',
      })
    } finally {
      setCalendarConnecting(false)
    }
  }

  const embedScriptCode = businessForm.id 
    ? `<script src="${window.location.origin}/widget/embed.js" data-business-id="custom:${businessForm.id}"></script>`
    : ''

  const copyEmbedCode = async () => {
    if (!embedScriptCode) {
      emitToast({
        title: 'Nothing to copy',
        message: 'Create a business first to generate the widget snippet.',
        tone: 'warning',
      })
      return
    }

    try {
      await navigator.clipboard.writeText(embedScriptCode)
      emitToast({
        title: 'Copied',
        message: 'Embed snippet copied to your clipboard.',
        tone: 'success',
      })
    } catch {
      emitToast({
        title: 'Copy failed',
        message: 'Your browser blocked clipboard access.',
        tone: 'error',
      })
    }
  }

  if (loading) {
    return (
      <main className="page-section client-dashboard-page">
        <section className="analytics-header">
          <div className="skeleton-heading-block">
            <div className="skeleton skeleton-line skeleton-eyebrow" />
            <div className="skeleton skeleton-line skeleton-title" />
            <div className="skeleton skeleton-line skeleton-subtitle" />
          </div>
          <div className="skeleton skeleton-button" />
        </section>
        <div className="dashboard-skeleton-grid">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card wide" />
          <div className="skeleton-card wide" />
        </div>
      </main>
    )
  }

  return (
    <main className="page-section client-dashboard-page" style={{ position: 'relative' }}>
      <section className="analytics-header">
        <div>
          <div className="section-eyebrow">Client Portal</div>
          <h1>{businessForm.business_name || businessForm.name || 'Chatbot Dashboard'}</h1>
          <div className="dashboard-header-status">
            <span className="status-item">
              <span className="pulsing-dot"></span>
              <span>AI Agent Online</span>
            </span>
            <span className="status-item">
              <span>Plan: <strong>{businessForm.plan?.toUpperCase()}</strong></span>
            </span>
            <span className="status-item">
              <span>Total Leads: <strong>{leads.length}</strong></span>
            </span>
            {analytics?.totals?.page_views ? (
              <span className="status-item">
                <span>Total Views: <strong>{formatNumber(analytics.totals.page_views)}</strong></span>
              </span>
            ) : null}
          </div>
        </div>

        <button className="secondary-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </section>

      {error ? <div className="analytics-banner" style={{ margin: '1rem 0' }}>{error}</div> : null}
      {successMessage ? <div className="analytics-banner success" style={{ margin: '1rem 0' }}>{successMessage}</div> : null}

      {/* Tabs Menu */}
      <div className="glass-tab-nav">
        <nav className="topbar-actions">
          <button className={`nav-link ${activeTab === 'tuning' ? 'active' : ''}`} onClick={() => setActiveTab('tuning')} type="button">
            Chatbot Settings & Sandbox
          </button>
          <button className={`nav-link ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')} type="button">
            Analytics
          </button>
          <button className={`nav-link ${activeTab === 'leads' ? 'active' : ''}`} onClick={() => setActiveTab('leads')} type="button">
            Qualified Leads ({leads.length})
          </button>
          <button className={`nav-link ${activeTab === 'widget' ? 'active' : ''}`} onClick={() => setActiveTab('widget')} type="button">
            Embed Widget
          </button>
          <button className={`nav-link ${activeTab === 'billing' ? 'active' : ''}`} onClick={() => setActiveTab('billing')} type="button">
            Billing Plans
          </button>
        </nav>
      </div>

      {/* Tab: Tuning Settings & Sandbox */}
      {activeTab === 'tuning' && (
        <section className="analytics-layout" style={{ gridTemplateColumns: '1.2fr 0.8fr' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <article className="analytics-panel">
              <div className="panel-header">
              <div>
                <span className="section-eyebrow">Settings Customizer</span>
                <h2>Tune Chatbot Guidelines</h2>
              </div>
            </div>

            <form className="business-form" onSubmit={handleSettingsSubmit} style={{ marginTop: '1.5rem' }}>
              <div className="form-grid">
                <label>
                  <span>Business Display Name</span>
                  <input
                    value={businessForm.business_name}
                    onChange={(event) => handleFieldChange('business_name', event.target.value)}
                    placeholder="E.g. ECHURA Salon"
                  />
                </label>
                <label>
                  <span>Primary Tone</span>
                  <select 
                    value={businessForm.tone_style} 
                    onChange={(event) => handleFieldChange('tone_style', event.target.value)}
                  >
                    <option value="warm, friendly, and reassuring">Warm & Reassuring</option>
                    <option value="professional, structured, and polite">Professional & Structured</option>
                    <option value="concise, direct, and helpful">Concise & Direct</option>
                    <option value="witty, charismatic, and enthusiastic">Witty & Enthusiastic</option>
                  </select>
                </label>
              </div>

              {/* Section: Business Identity */}
              <div style={{ marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-light)' }}>Business Identity</span>
                <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0 1.25rem' }} />
              </div>

              <label>
                <span>Short Description</span>
                <textarea
                  value={businessForm.business_description}
                  onChange={(event) => handleFieldChange('business_description', event.target.value)}
                  placeholder="Describe your business model briefly..."
                  rows={2}
                />
              </label>

              {/* Section: AI Behavior */}
              <div style={{ marginBottom: '0.5rem', marginTop: '1rem' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-light)' }}>Services & Knowledge</span>
                <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0 1.25rem' }} />
              </div>

              <label>
                <span>Services Menu & Pricing</span>
                <textarea
                  value={businessForm.services_products}
                  onChange={(event) => handleFieldChange('services_products', event.target.value)}
                  placeholder="E.g. Haircut ($35), Styling ($45), Facial ($60)..."
                  rows={3}
                />
              </label>

              <div className="form-grid">
                <label>
                  <span>Frequently Asked Questions (FAQs)</span>
                  <textarea
                    value={businessForm.faqs}
                    onChange={(event) => handleFieldChange('faqs', event.target.value)}
                    placeholder="E.g. We are open Tue-Sun 9am-6pm. Walk-ins accepted when available."
                    rows={4}
                  />
                </label>
                <label>
                  <span>Booking Policies</span>
                  <textarea
                    value={businessForm.policies}
                    onChange={(event) => handleFieldChange('policies', event.target.value)}
                    placeholder="E.g. 24h cancellation notice required. Hair color bookings need deposit."
                    rows={4}
                  />
                </label>
              </div>

              {/* Section: Receptionist AI Behavior */}
              <div style={{ marginBottom: '0.5rem', marginTop: '1rem' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-light)' }}>Receptionist AI</span>
                <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0 1.25rem' }} />
              </div>

              <label>
                <span>Receptionist System Instructions</span>
                <textarea
                  value={businessForm.personality_prompt}
                  onChange={(event) => handleFieldChange('personality_prompt', event.target.value)}
                  placeholder="Configure custom rules, like: 'Encourage users to book hair coloring sessions'..."
                  rows={3}
                />
              </label>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={businessForm.lead_capture_enabled}
                  onChange={(event) => handleFieldChange('lead_capture_enabled', event.target.checked)}
                />
                <span>Enable automatic client contact qualification & bookings</span>
              </label>

              <div className="form-actions">
                <button className="primary-button" type="submit" disabled={savingSettings}>
                  {savingSettings ? 'Applying Guidelines...' : 'Apply Live Guidelines'}
                </button>
              </div>
            </form>
          </article>

          {/* Google Calendar Panel */}
          <article className="analytics-panel">
            <div className="panel-header">
              <div>
                <span className="section-eyebrow">Calendar Sync</span>
                <h2>Google Calendar Integration</h2>
              </div>
            </div>
            <div style={{ marginTop: '1.5rem', display: 'grid', gap: '1rem' }}>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                Sync your chatbot bookings directly with Google Calendar to view client bookings alongside your daily schedule.
              </p>
              
              {business?.has_calendar_connected ? (
                <div style={{ display: 'grid', gap: '1rem', padding: '1.25rem', border: '1px solid var(--success-border)', backgroundColor: 'var(--success-bg)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '600', color: 'var(--success)' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    Google Calendar Connected
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    <strong>Active Calendar:</strong> {business.calendar_id || 'primary'}
                  </div>
                  <button className="secondary-button" onClick={handleDisconnectCalendar} disabled={calendarConnecting} type="button" style={{ width: 'fit-content', marginTop: '0.5rem' }}>
                    {calendarConnecting ? 'Disconnecting...' : 'Disconnect Calendar'}
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '1rem', padding: '1.25rem', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '600', color: 'var(--text-light)' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                    No Google Calendar Connected
                  </div>
                  <button className="primary-button" onClick={handleConnectCalendar} disabled={calendarConnecting} type="button" style={{ width: 'fit-content', marginTop: '0.5rem' }}>
                    {calendarConnecting ? 'Connecting...' : 'Connect Google Calendar'}
                  </button>
                </div>
              )}
            </div>
          </article>
        </div>

          {/* Sandbox panel */}
          <article className="analytics-panel" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <div>
                <span className="section-eyebrow">Interactive Testing</span>
                <h2>Chatbot Sandbox</h2>
              </div>
              <button 
                type="button" 
                className="secondary-button compact" 
                onClick={() => setSandboxMessages([])}
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
              >
                Reset Chat
              </button>
            </div>
            
            <div className="chat-window" style={{ flex: 1, minHeight: '380px', maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {sandboxMessages.map((msg, i) => (
                  <div key={i} className={`chat-bubble ${msg.role}`}>
                    {msg.content}
                  </div>
                ))}
                {sandboxLoading && (
                  <div className="chat-bubble assistant typing">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                )}
              </div>
              
              {sandboxMessages.length <= 1 && (
                <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-light)', display: 'block', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>💡 QUICK TEST SUGGESTIONS</span>
                  <div className="prompt-row" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    <button type="button" onClick={() => setSandboxInput("What services do you offer?")} style={{ fontSize: '0.78rem' }}>What services do you offer?</button>
                    <button type="button" onClick={() => setSandboxInput("How can I book an appointment?")} style={{ fontSize: '0.78rem' }}>How can I book?</button>
                    <button type="button" onClick={() => setSandboxInput("What are your business hours?")} style={{ fontSize: '0.78rem' }}>What are your hours?</button>
                  </div>
                </div>
              )}
            </div>

            <form className="chat-form" onSubmit={sendSandboxMessage}>
              <input
                value={sandboxInput}
                onChange={(e) => setSandboxInput(e.target.value)}
                placeholder="Type your test message here..."
                disabled={sandboxLoading}
              />
              <button className="primary-button" type="submit" disabled={sandboxLoading}>
                Test
              </button>
            </form>
          </article>
        </section>
      )}

      {/* Tab: Analytics */}
      {activeTab === 'analytics' && analytics && (
        <section style={{ display: 'grid', gap: '2rem' }}>

          {/* KPI Hero Cards */}
          <div className="kpi-grid">
            <article className="kpi-card">
              <span className="kpi-card-icon">💬</span>
              <span className="kpi-card-label">Conversations</span>
              <span className="kpi-card-value">{formatNumber(analytics.totals.demo_starts)}</span>
              <span className="kpi-card-sub">{formatNumber(analytics.totals.page_views)} total page views</span>
            </article>
            <article className="kpi-card">
              <span className="kpi-card-icon">🎯</span>
              <span className="kpi-card-label">Leads Captured</span>
              <span className="kpi-card-value">{formatNumber(analytics.totals.leads)}</span>
              <span className="kpi-card-sub">{formatNumber(analytics.totals.demo_completions)} completed chats</span>
            </article>
            <article className="kpi-card">
              <span className="kpi-card-icon">📈</span>
              <span className="kpi-card-label">Conversion Rate</span>
              <span className="kpi-card-value">{formatPercent(analytics.totals.conversion_rate)}</span>
              <span className="kpi-card-sub">Leads ÷ page views</span>
            </article>
            <article className="kpi-card">
              <span className="kpi-card-icon">⭐</span>
              <span className="kpi-card-label">Avg Lead Score</span>
              <span className="kpi-card-value">{analytics.totals.avg_lead_score}%</span>
              <span className="kpi-card-sub">Across {analytics.totals.leads} leads</span>
            </article>
          </div>

          {/* Detail Panels */}
          <div className="analytics-layout">
            <article className="analytics-panel">
              <div className="panel-header">
                <div>
                  <span className="section-eyebrow">Segmentation</span>
                  <h2>Lead Pipeline breakdown</h2>
                </div>
              </div>
              <div className="lead-grid" style={{ marginTop: '1rem' }}>
                <div className="lead-chip" style={{ borderLeft: '3px solid var(--error)' }}>
                  <span>HOT pipeline (High Buying Intent)</span>
                  <strong style={{ color: 'var(--error)' }}>{analytics.lead_quality.HOT}</strong>
                </div>
                <div className="lead-chip" style={{ borderLeft: '3px solid var(--warning)' }}>
                  <span>WARM pipeline (Medium Intent)</span>
                  <strong style={{ color: 'var(--warning)' }}>{analytics.lead_quality.WARM}</strong>
                </div>
                <div className="lead-chip" style={{ borderLeft: '3px solid var(--success)' }}>
                  <span>COLD pipeline (Exploring)</span>
                  <strong style={{ color: 'var(--success)' }}>{analytics.lead_quality.COLD}</strong>
                </div>
                <div className="lead-chip" style={{ borderLeft: '3px solid var(--accent)' }}>
                  <span>Average pipeline Score</span>
                  <strong style={{ color: 'var(--accent)' }}>{analytics.totals.avg_lead_score}%</strong>
                </div>
              </div>
            </article>

            <article className="analytics-panel">
              <div className="panel-header">
                <div>
                  <span className="section-eyebrow">Audit log</span>
                  <h2>Recent Activity</h2>
                </div>
              </div>
              <div className="activity-feed" style={{ maxHeight: '280px', overflowY: 'auto' }}>
                {analytics.recent_activity?.length ? (
                  analytics.recent_activity.map((act) => (
                    <div key={act.id} className="activity-item" style={{ padding: '0.6rem' }}>
                      <strong>{act.event_name.replace('_', ' ').toUpperCase()}</strong>
                      <span>{new Date(act.timestamp).toLocaleTimeString()}</span>
                    </div>
                  ))
                ) : (
                  <p className="empty-state">No visitor events recorded yet.</p>
                )}
              </div>
            </article>
          </div>
        </section>
      )}

      {/* Tab: Leads */}
      {activeTab === 'leads' && (
        <article className="analytics-panel full-width">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Pipeline list</span>
              <h2>Latest Leads from AI chat</h2>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', overflowX: 'auto' }}>
            {leads.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Customer Name</th>
                    <th>Contact Number</th>
                    <th>Interest Details</th>
                    <th>Capture Source</th>
                    <th>Buying score</th>
                    <th>Priority Level</th>
                    <th>Date Captured</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((l) => (
                    <tr key={l.id}>
                      <td style={{ fontWeight: 'bold' }}>{l.name}</td>
                      <td>{l.contact || 'None'}</td>
                      <td>
                        {l.metadata_json?.service || 'Consultation'} 
                        {l.metadata_json?.date ? ` (Date: ${l.metadata_json.date} @ ${l.metadata_json.time || 'TBD'})` : ''}
                      </td>
                      <td><small>{l.source}</small></td>
                      <td>{l.buying_probability}%</td>
                      <td>
                        <span className={`status-pill ${l.status === 'HOT' ? 'warning' : ''}`}>
                          {l.status}
                        </span>
                      </td>
                      <td><small>{new Date(l.created_at).toLocaleDateString()}</small></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state" style={{ padding: '2rem', textAlign: 'center' }}>
                No customer leads captured yet. Enable chat widget and direct visitors to convert them into leads.
              </p>
            )}
          </div>
        </article>
      )}

      {/* Tab: Widget */}
      {activeTab === 'widget' && (
        <article className="analytics-panel full-width">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Embed Options</span>
              <h2>Add Chat Widget to Your Website</h2>
            </div>
          </div>
          
          <div style={{ marginTop: '1.5rem', display: 'grid', gap: '1.5rem' }}>
            <p>Paste the following script snippet immediately before the closing <code>&lt;/body&gt;</code> tag of your website HTML code. This launches a responsive floating customer assistant widget loaded directly with your settings guidelines.</p>
            
            <div style={{ position: 'relative', background: 'var(--bg-app)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', overflowX: 'auto', whiteSpace: 'pre' }}>
              <code>{embedScriptCode}</code>
            </div>

            <div>
              <button className="primary-button" onClick={copyEmbedCode}>
                Copy Snippet to Clipboard
              </button>
            </div>
          </div>
        </article>
      )}

      {/* Tab: Billing */}
      {activeTab === 'billing' && (
        <section style={{ display: 'grid', gap: '2rem' }}>
          <div className="analytics-panel full-width">
            <div className="panel-header">
              <div>
                <span className="section-eyebrow">Plans & Pricing</span>
                <h2>Subscription Manager</h2>
              </div>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1.5rem', marginTop: '2rem' }}>
              
              {/* Starter Plan */}
              <article className="dashboard-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', border: businessForm.plan === 'starter' ? '2px solid var(--accent)' : '' }}>
                <span className="card-label">Starter Plan</span>
                <strong style={{ fontSize: '2.2rem', margin: '0.5rem 0' }}>$29<span style={{ fontSize: '1rem', fontWeight: 'normal' }}>/month</span></strong>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', flex: 1 }}>Best for small startups needing basic booking qualification and auto-FAQ assistance.</p>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', lineHeight: '1.8' }}>
                  <li>1 Chatbot Integration</li>
                  <li>1,000 Chats/month capacity</li>
                  <li>Basic FAQ tuning settings</li>
                  <li>Simple Lead Capture List</li>
                </ul>
                {businessForm.plan === 'starter' ? (
                  <span className="status-pill" style={{ textAlign: 'center', display: 'block' }}>Current Active Plan</span>
                ) : (
                  <button className="secondary-button" onClick={() => handleUpgradeClick('starter')}>Select Starter</button>
                )}
              </article>

              {/* Growth Plan */}
              <article className="dashboard-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', border: businessForm.plan === 'growth' ? '2px solid var(--accent)' : '' }}>
                <span className="card-label">Growth Plan</span>
                <strong style={{ fontSize: '2.2rem', margin: '0.5rem 0' }}>$79<span style={{ fontSize: '1rem', fontWeight: 'normal' }}>/month</span></strong>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', flex: 1 }}>Perfect for scaling businesses wanting custom guidelines, pipelines, and insights.</p>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', lineHeight: '1.8' }}>
                  <li>5 Chatbot Integrations</li>
                  <li>10,000 Chats/month capacity</li>
                  <li>Full guideline settings tuner</li>
                  <li>Advanced Lead Scoring pipelines</li>
                  <li>Real-time dashboard analytics</li>
                </ul>
                {businessForm.plan === 'growth' ? (
                  <span className="status-pill" style={{ textAlign: 'center', display: 'block' }}>Current Active Plan</span>
                ) : (
                  <button className="primary-button" onClick={() => handleUpgradeClick('growth')}>Upgrade to Growth</button>
                )}
              </article>

              {/* Scale Plan */}
              <article className="dashboard-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', border: businessForm.plan === 'scale' ? '2px solid var(--accent)' : '' }}>
                <span className="card-label">Scale Plan</span>
                <strong style={{ fontSize: '2.2rem', margin: '0.5rem 0' }}>$199<span style={{ fontSize: '1rem', fontWeight: 'normal' }}>/month</span></strong>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', flex: 1 }}>Best for high volume operators with dedicated service teams and complex guidelines.</p>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', lineHeight: '1.8' }}>
                  <li>25 Chatbot Integrations</li>
                  <li>50,000 Chats/month capacity</li>
                  <li>All advanced tuning options</li>
                  <li>Priority backend processor speeds</li>
                  <li>Extended analytics logging</li>
                </ul>
                {businessForm.plan === 'scale' ? (
                  <span className="status-pill" style={{ textAlign: 'center', display: 'block' }}>Current Active Plan</span>
                ) : (
                  <button className="secondary-button" onClick={() => handleUpgradeClick('scale')}>Upgrade to Scale</button>
                )}
              </article>

            </div>
          </div>
        </section>
      )}

      {/* Paystack Redirecting Spinner Overlay */}
      {paymentInitializing && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 99999, display: 'grid', placeItems: 'center', backgroundColor: 'rgba(23,32,42,0.6)', backdropFilter: 'blur(4px)' }}>
          <article className="auth-panel" style={{ width: '400px', padding: '2.5rem', textAlign: 'center' }}>
            <span className="section-eyebrow" style={{ color: '#09a5db' }}>Paystack Secure Gateway</span>
            <h2 style={{ marginTop: '0.5rem' }}>Redirecting to Checkout</h2>
            <p style={{ fontSize: '0.95rem', color: '#61706e', marginTop: '1rem' }}>
              Please wait while we connect you to our secure payment gateway to complete your subscription...
            </p>
            <div style={{ display: 'inline-block', width: '2.5rem', height: '2.5rem', border: '3px solid rgba(9,165,219,0.2)', borderTopColor: '#09a5db', borderRadius: '50%', animation: 'spin 1s linear infinite', marginTop: '1.5rem' }}></div>
          </article>
        </div>
      )}
    </main>
  )
}


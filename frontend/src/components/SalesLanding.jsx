import React, { useEffect, useMemo, useState } from 'react'
import { readJsonResponse } from '../utils/http'
import { emitToast } from '../utils/toast'

const starters = [
  'Hi, I want to book an appointment tomorrow at 2pm.',
  'What services do you offer?',
  'Can I get a quote and speak to someone today?',
]

function createSessionId() {
  return `session-${Math.random().toString(36).slice(2)}-${Date.now()}`
}

export default function SalesLanding() {
  const [businesses, setBusinesses] = useState([])
  const [selectedBusinessRef, setSelectedBusinessRef] = useState('')
  const [sessionId] = useState(createSessionId)
  const [message, setMessage] = useState(starters[0])
  const [chatLog, setChatLog] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingBusinesses, setLoadingBusinesses] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/businesses')
      .then(readJsonResponse)
      .then((payload) => {
        const options = Array.isArray(payload.businesses) ? payload.businesses : []
        setBusinesses(options)
        if (options[0]) setSelectedBusinessRef(String(options[0].id))
      })
      .catch(() => {
        setBusinesses([])
      })
      .finally(() => setLoadingBusinesses(false))
  }, [])

  const selectedBusiness = useMemo(
    () => businesses.find((business) => String(business.id) === selectedBusinessRef),
    [businesses, selectedBusinessRef],
  )

  const sendMessage = async (event) => {
    event.preventDefault()
    const cleanMessage = message.trim()
    if (!cleanMessage) return

    setLoading(true)
    setError('')
    setChatLog((current) => [...current, { role: 'user', content: cleanMessage }])
    try {
      const response = await fetch('/api/widget/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: cleanMessage,
          session_id: sessionId,
          business_id: selectedBusiness?.id,
          business_name: selectedBusiness?.business_name,
        }),
      })
      const payload = await readJsonResponse(response)
      if (!response.ok) throw new Error(payload.detail || 'The assistant could not reply')
      const assistantReply = payload.response || payload.reply || payload.message
      if (!assistantReply) throw new Error(payload.detail || 'The assistant returned an empty response.')
      setChatLog((current) => [...current, { role: 'assistant', content: assistantReply }])
      setMessage('')
    } catch (chatError) {
      setError(chatError.message || 'Unable to send message')
      emitToast({
        title: 'Message failed',
        message: chatError.message || 'Please try again.',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-section sales-page">
      
      {/* Hero Section */}
      <section className="hero-band">
        <div className="hero-copy">
          <div className="section-eyebrow">Smart AI receptionists for local businesses</div>
          <h1>ECHURA</h1>
          <p>Launch a 24/7 business chatbot that qualifies leads, books customers, and answers inquiries automatically from one gorgeous dashboard. No code required.</p>
          <div className="hero-actions hero-actions--spacious">
            <a className="primary-button" href="#client-login">Start Free 14-Day Trial</a>
            <a className="secondary-button" href="#client-login">Live Settings Tuner</a>
          </div>
        </div>

        {/* Live Demo Console */}
        <div className="demo-console">
          <div className="panel-header">
            <div>
              <span className="section-eyebrow">Try out the demo</span>
              <h2 className="panel-title">{selectedBusiness?.business_name || 'Business assistant'}</h2>
            </div>
          </div>

          <label className="select-label">
            <span>Choose a demo profile to test:</span>
            {loadingBusinesses ? (
              <div className="skeleton-input" aria-hidden="true" />
            ) : businesses.length ? (
              <select value={selectedBusinessRef} onChange={(event) => setSelectedBusinessRef(event.target.value)}>
                {businesses.map((business) => (
                  <option key={business.business_ref || business.id} value={business.business_ref || business.id}>
                    {business.business_name || business.name}
                  </option>
                ))}
              </select>
            ) : (
              <div className="empty-state-card empty-state-card--compact">
                <div className="empty-state-art" aria-hidden="true">✨</div>
                <p>Demo profiles are loading slowly right now. Please try again in a moment.</p>
              </div>
            )}
          </label>

          <div className="chat-window" style={{ flex: 1, minHeight: '380px', maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {loadingBusinesses ? (
                <div className="chat-skeleton-stack" aria-hidden="true">
                  <div className="skeleton bubble bubble-assistant" />
                  <div className="skeleton bubble bubble-user short" />
                  <div className="skeleton bubble bubble-assistant" />
                </div>
              ) : chatLog.length ? (
                chatLog.map((entry, index) => (
                  <div key={`${entry.role}-${index}`} className={`chat-bubble ${entry.role}`}>
                    {entry.content}
                  </div>
                ))
              ) : (
                <div className="empty-state-card">
                  <div className="empty-state-art" aria-hidden="true">💬</div>
                  <p>Send a message below to test client-side lead capture and workflow memory.</p>
                </div>
              )}
              {loading && (
                <div className="chat-bubble assistant typing">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              )}
            </div>

            {chatLog.length <= 1 && !loading && (
              <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-light)', display: 'block', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>QUICK TEST SUGGESTIONS</span>
                <div className="prompt-row" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {starters.map((starter) => (
                    <button key={starter} type="button" onClick={() => setMessage(starter)} disabled={loading}>{starter}</button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {error ? <div className="analytics-banner" style={{ margin: '1rem 0' }}>{error}</div> : null}

          <form className="chat-form" onSubmit={sendMessage}>
            <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Type your test message here..." disabled={loading} />
            <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Sending...' : 'Test'}</button>
          </form>
        </div>
      </section>

      {/* Value Propositions / Features Section */}
      <section className="section-stack">
        <div className="section-intro">
          <span className="section-eyebrow">Features Built for Growth</span>
          <h2>Everything you need to automate bookings</h2>
          <p>ECHURA operates behind a clear system designed to help you capture higher intent clients while you sleep.</p>
        </div>

        <div className="feature-grid">
          <article className="dashboard-card feature-card">
            <div className="feature-badge">1</div>
            <h3>No-Code Customizer</h3>
            <p>Configure services, FAQs, guidelines, and custom policies in plain English. The AI updates its context immediately.</p>
          </article>
          <article className="dashboard-card feature-card">
            <div className="feature-badge">2</div>
            <h3>Automated Lead Pipeline</h3>
            <p>Our system scores booking inquiries into HOT, WARM, and COLD leads based on urgency and purchase intent.</p>
          </article>
          <article className="dashboard-card feature-card">
            <div className="feature-badge">3</div>
            <h3>Sleek Embeddable Widget</h3>
            <p>Add a fully responsive floating assistant to your website in seconds by copying and pasting a single script tag.</p>
          </article>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="section-stack">
        <div className="section-intro">
          <span className="section-eyebrow">Pricing Plans</span>
          <h2>Simple, predictable pricing</h2>
          <p>Start free on a 14-day trial. Cancel or switch plans at any time.</p>
        </div>

        <div className="pricing-grid">
          
          {/* Starter Card */}
          <article className="dashboard-card pricing-card">
            <div>
              <span className="card-label">Starter</span>
              <strong className="price-value">$29<span>/mo</span></strong>
              <p>Ideal for solo professionals starting to automate bookings.</p>
            </div>
            <hr />
            <ul>
              <li>1 Chatbot Integration</li>
              <li>1,000 Chats capacity/month</li>
              <li>Basic FAQ tuner settings</li>
              <li>Captured Leads Table View</li>
            </ul>
            <a className="secondary-button" href="#client-login">Start Starter Trial</a>
          </article>

          {/* Growth Card */}
          <article className="dashboard-card pricing-card pricing-card--featured">
            <div>
              <span className="card-label card-label-accent">Growth (Most Popular)</span>
              <strong className="price-value">$79<span>/mo</span></strong>
              <p>Best for growing businesses wanting complete tuner controls.</p>
            </div>
            <hr />
            <ul>
              <li>5 Chatbot Integrations</li>
              <li>10,000 Chats capacity/month</li>
              <li>Full guidelines customization</li>
              <li>Advanced Lead Qualification & Scoring</li>
              <li>Real-time performance analytics</li>
            </ul>
            <a className="primary-button" href="#client-login">Start Growth Trial</a>
          </article>

          {/* Scale Card */}
          <article className="dashboard-card pricing-card">
            <div>
              <span className="card-label">Scale</span>
              <strong className="price-value">$199<span>/mo</span></strong>
              <p>For high volume businesses with strict custom guidelines.</p>
            </div>
            <hr />
            <ul>
              <li>25 Chatbot Integrations</li>
              <li>50,000 Chats capacity/month</li>
              <li>Priority backend performance</li>
              <li>Dedicated customer success contact</li>
              <li>Extended analytics histories</li>
            </ul>
            <a className="secondary-button" href="#client-login">Start Scale Trial</a>
          </article>

        </div>
      </section>

    </main>
  )
}




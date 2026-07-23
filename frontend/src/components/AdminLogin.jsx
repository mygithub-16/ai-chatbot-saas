import React, { useState } from 'react'
import { readJsonResponse } from '../utils/http'
import { emitToast } from '../utils/toast'

export default function AdminLogin({ onSuccess }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const payload = await readJsonResponse(response)
      if (!response.ok) throw new Error(payload.detail || 'Invalid admin credentials')
      onSuccess(payload.access_token)
      emitToast({
        title: 'Welcome back',
        message: 'You are now signed in to the operator dashboard.',
        tone: 'success',
      })
    } catch (loginError) {
      setError(loginError.message || 'Unable to sign in')
      emitToast({
        title: 'Sign in failed',
        message: loginError.message || 'Please check your credentials.',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-section auth-page">
      <section className="auth-panel">
        <div className="section-eyebrow">Admin</div>
        <h1>Sign in</h1>
        <p>Access analytics, businesses, and customer conversion data.</p>
        {error ? <div className="analytics-banner">{error}</div> : null}
        <form className="business-form" onSubmit={handleSubmit}>
          <label>
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            <span>Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}

import React, { useState } from 'react'
import { readJsonResponse } from '../utils/http'
import { emitToast } from '../utils/toast'

export default function ClientAuth({ onSuccess, onBack }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    const endpoint = isRegister ? '/auth/register' : '/auth/login'
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const payload = await readJsonResponse(response)
      
      if (!response.ok) {
        throw new Error(payload.detail || 'Authentication failed. Please check your credentials.')
      }

      // Success! Pass access token, user metadata and business metadata
      onSuccess(payload.access_token, payload.user, payload.business)
      emitToast({
        title: isRegister ? 'Trial ready' : 'Signed in',
        message: isRegister ? 'Your account is ready to customize.' : 'Welcome back to your client portal.',
        tone: 'success',
      })
    } catch (authError) {
      setError(authError.message || 'Unable to connect to server')
      emitToast({
        title: 'Authentication failed',
        message: authError.message || 'Please try again.',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-section auth-page">
      <section className="auth-panel">
        <button className="secondary-button compact auth-back" onClick={onBack} type="button">
          ← Back
        </button>
        
        <div className="section-eyebrow">Client Portal</div>
        <h1>{isRegister ? 'Create Account' : 'Sign In'}</h1>
        <p>
          {isRegister 
            ? 'Start your 14-day free trial. Setup your AI receptionist in under 2 minutes.' 
            : 'Access your chatbot customizer, leads list, and business analytics.'}
        </p>

        {error ? <div className="analytics-banner">{error}</div> : null}

        <form className="business-form" onSubmit={handleSubmit}>
          <label>
            <span>Email Address</span>
            <input 
              type="email" 
              value={email} 
              onChange={(event) => setEmail(event.target.value)} 
              placeholder="name@business.com"
              required 
            />
          </label>
          
          <label>
            <span>Password</span>
            <input 
              type="password" 
              value={password} 
              onChange={(event) => setPassword(event.target.value)} 
              placeholder="••••••••"
              required 
            />
          </label>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Processing...' : isRegister ? 'Start Free Trial' : 'Sign In'}
          </button>
        </form>

        <div className="auth-switch">
          {isRegister ? (
            <span>
              Already have an account?{' '}
              <button 
                type="button" 
                onClick={() => { setIsRegister(false); setError(''); }}
                className="inline-link-button"
              >
                Log in
              </button>
            </span>
          ) : (
            <span>
              Don't have an account yet?{' '}
              <button 
                type="button" 
                onClick={() => { setIsRegister(true); setError(''); }}
                className="inline-link-button"
              >
                Sign up free
              </button>
            </span>
          )}
        </div>
      </section>
    </main>
  )
}

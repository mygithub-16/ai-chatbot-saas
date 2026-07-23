import React, { useEffect, useState } from 'react'
import AdminLogin from './components/AdminLogin'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import SalesLanding from './components/SalesLanding'
import ClientAuth from './components/ClientAuth'
import ClientDashboard from './components/ClientDashboard'

function getRouteFromHash() {
  const hash = window.location.hash
  if (hash === '#analytics') {
    return 'analytics'
  }
  if (hash === '#admin') {
    return 'admin'
  }
  if (hash === '#client-login') {
    return 'client-login'
  }
  if (hash === '#client-dashboard') {
    return 'client-dashboard'
  }
  return 'home'
}

export default function App() {
  const [route, setRoute] = useState(getRouteFromHash())
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem('adminToken') ?? '')
  const [clientToken, setClientToken] = useState(() => localStorage.getItem('clientToken') ?? '')
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') ?? 'light')
  const [toasts, setToasts] = useState([])
  const [scrolled, setScrolled] = useState(() => window.scrollY > 8)

  useEffect(() => {
    if (theme === 'dark') {
      document.body.classList.add('dark-theme')
    } else {
      document.body.classList.remove('dark-theme')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash())
    const onStorageChange = () => {
      setAdminToken(localStorage.getItem('adminToken') ?? '')
      setClientToken(localStorage.getItem('clientToken') ?? '')
    }

    const onScroll = () => {
      setScrolled(window.scrollY > 8)
    }

    window.addEventListener('hashchange', onHashChange)
    window.addEventListener('storage', onStorageChange)
    window.addEventListener('scroll', onScroll, { passive: true })
    const onToast = (event) => {
      const detail = event.detail || {}
      const id = detail.id || `${Date.now()}-${Math.random().toString(36).slice(2)}`
      const toast = {
        id,
        title: detail.title || '',
        message: detail.message || '',
        tone: detail.tone || 'info',
      }

      setToasts((current) => [...current, toast])

      window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== id))
      }, detail.duration || 3600)
    }

    window.addEventListener('app-toast', onToast)
    return () => {
      window.removeEventListener('hashchange', onHashChange)
      window.removeEventListener('storage', onStorageChange)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('app-toast', onToast)
    }
  }, [])

  const goHome = () => {
    window.location.hash = ''
    setRoute('home')
  }

  const goClientLogin = () => {
    window.location.hash = '#client-login'
    setRoute('client-login')
  }

  const goClientDashboard = () => {
    window.location.hash = '#client-dashboard'
    setRoute('client-dashboard')
  }

  const goAdminLogin = () => {
    window.location.hash = '#admin'
    setRoute('admin')
  }

  const goAdminDashboard = () => {
    window.location.hash = '#analytics'
    setRoute('analytics')
  }

  const handleAdminLoginSuccess = (token) => {
    localStorage.setItem('adminToken', token)
    setAdminToken(token)
    goAdminDashboard()
  }

  const handleAdminLogout = () => {
    localStorage.removeItem('adminToken')
    setAdminToken('')
    goAdminLogin()
  }

  const handleClientLoginSuccess = (token, user, business) => {
    localStorage.setItem('clientToken', token)
    setClientToken(token)
    goClientDashboard()
  }

  const handleClientLogout = () => {
    localStorage.removeItem('clientToken')
    setClientToken('')
    goClientLogin()
  }

  return (
    <div className="app-shell">
      <div className="bg-gradient-overlay" aria-hidden="true" />
      <header
        className={`topbar glass-surface ${scrolled ? 'topbar--scrolled' : ''}`}
        style={{ position: 'fixed', top: 0, left: 0, right: 0, width: '100%' }}
      >
        <button className="brand" onClick={goHome} type="button">
          <span>ECHURA</span>
          <small>AI Chatbot SaaS</small>
        </button>

        <nav className="topbar-actions">
            <button className={`nav-link ${route === 'home' ? 'active' : ''}`} onClick={goHome} type="button">
            Home
          </button>
          
          {clientToken ? (
            <>
              <button className={`nav-link ${route === 'client-dashboard' ? 'active' : ''}`} onClick={goClientDashboard} type="button">
                My Chatbot Dashboard
              </button>
              <button className="nav-link" onClick={handleClientLogout} type="button">
                Sign Out
              </button>
            </>
          ) : adminToken ? (
            <>
              <button className={`nav-link ${route === 'analytics' ? 'active' : ''}`} onClick={goAdminDashboard} type="button">
                Operator Dashboard
              </button>
              <button className="nav-link" onClick={handleAdminLogout} type="button">
                Sign Out
              </button>
            </>
          ) : (
            <>
              <button className={`nav-link ${route === 'client-login' ? 'active' : ''}`} onClick={goClientLogin} type="button">
                Sign In / Free Trial
              </button>
              <button className={`nav-link ${route === 'admin' ? 'active' : ''}`} onClick={goAdminLogin} type="button">
                Operator View
              </button>
            </>
          )}
          
          <button
            className="secondary-button theme-toggle"
            onClick={toggleTheme}
            type="button"
            title="Toggle Theme"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </nav>
      </header>

      <div className="app-shell__content">
        <div key={route} className="route-transition">
          {route === 'analytics' ? (
            adminToken ? (
              <AnalyticsDashboard authToken={adminToken} onLogout={handleAdminLogout} />
            ) : (
              <AdminLogin onSuccess={handleAdminLoginSuccess} />
            )
          ) : route === 'admin' ? (
            <AdminLogin onSuccess={handleAdminLoginSuccess} />
          ) : route === 'client-login' ? (
            <ClientAuth onSuccess={handleClientLoginSuccess} onBack={goHome} />
          ) : route === 'client-dashboard' ? (
            clientToken ? (
              <ClientDashboard authToken={clientToken} onLogout={handleClientLogout} />
            ) : (
              <ClientAuth onSuccess={handleClientLoginSuccess} onBack={goHome} />
            )
          ) : (
            <SalesLanding />
          )}
        </div>
      </div>
      
      <footer className="app-footer glass-surface">
        <p>&copy; {new Date().getFullYear()} ECHURA AI Chatbot SaaS. All rights reserved.</p>
        <div className="footer-links">
          <a href="#admin">Global Operator Portal</a>
        </div>
      </footer>

      <div className="toast-viewport" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.tone}`}>
            <div className="toast-mark" aria-hidden="true" />
            <div className="toast-copy">
              {toast.title ? <strong>{toast.title}</strong> : null}
              {toast.message ? <span>{toast.message}</span> : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

import React from 'react'

export default function MapsWidget({ address }) {
  if (!address || typeof address !== 'string' || !address.trim()) {
    return (
      <div className="maps-placeholder" style={{ padding: '2rem', border: '1px dashed rgba(23,32,42,0.15)', borderRadius: '8px', textAlign: 'center', color: '#61706e', fontSize: '0.9rem' }}>
        No address provided. Please configure a business address in Settings.
      </div>
    )
  }

  // URL-encode to prevent query parameter injection or security vulnerabilities
  const encodedAddress = encodeURIComponent(address.trim())
  
  // Use VITE_GOOGLE_MAPS_API_KEY if configured in environment, otherwise fallback to search query embed
  const apiKey = import.meta.env?.VITE_GOOGLE_MAPS_API_KEY
  const embedUrl = apiKey
    ? `https://www.google.com/maps/embed/v1/place?key=${apiKey}&q=${encodedAddress}`
    : `https://maps.google.com/maps?q=${encodedAddress}&t=&z=15&ie=UTF8&iwloc=&output=embed`

  return (
    <div className="maps-widget-container" style={{ position: 'relative', overflow: 'hidden', paddingBottom: '56.25%', height: 0, borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', border: '1px solid rgba(23,32,42,0.06)' }}>
      <iframe
        title="Google Maps Location"
        src={embedUrl}
        width="100%"
        height="100%"
        style={{ position: 'absolute', top: 0, left: 0, border: 0, width: '100%', height: '100%' }}
        allowFullScreen=""
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        sandbox="allow-scripts allow-same-origin allow-popups"
      />
    </div>
  )
}

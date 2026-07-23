# Dev Log

## 2026-06-16 Recovery Rebuild

- Restored recovered VS Code Local History snapshots for `main.py`, `ai.py`, `auth.py`, `App.jsx`, and `AnalyticsDashboard.jsx`.
- Rebuilt SQLAlchemy database/session layer.
- Rebuilt models for users, businesses, leads, events, and conversation sessions.
- Repaired the admin business serializer in `main.py`.
- Rebuilt missing React components, stylesheet, Dockerfiles, and support modules.
- Local verification could not run because Python, Node, and npm are not available on PATH in this shell.

## 2026-07-12 UI Polish Sprint

Modernized the entire frontend layout, spacing, components, and typography to deliver a premium, high-end SaaS feel inspired by Stripe, Vercel, and Linear.

### Improvements & Design Justifications:
- **Typography Overhaul:** Loaded `Plus Jakarta Sans` for headers and copy, and `JetBrains Mono` for embed code blocks. Improves reading hierarchy and looks premium compared to generic fallback sans-serif fonts.
- **Removed Multi-color Glows:** Removed heavy box-shadows using neon red, green, and blue glows on chat bubbles, auth panels, and dashboard grids. Replaced with sharp, thin borders (`var(--border-color)`) and soft grayscale shadows (`var(--shadow-md)`) to align with professional SaaS UI standards.
- **Accented Design System:** Consolidated visual aesthetics around a single primary accent color (Indigo/Violet `#4f46e5`) for active nav links, primary buttons, user bubbles, and active controls.
- **Polished Hero & Landing Page:** Polished `SalesLanding.jsx` spacing and column sizes. Cleaned pricing cards (Starter, Growth, Scale) to render cleanly in an auto-stretching card grid.
- **Dashboard & Table Polishing:** Polished `ClientDashboard.jsx` to render calendar status alerts cleanly with soft alerts. Removed inline border table overrides to use the main table classes defined in `styles.css` for consistent table spacing and hover reactions.
- **Responsive Layout Adjustments:** Upgraded navigation and dashboard grid columns to wrap cleanly on medium and narrow screen viewports, ensuring absolute responsive consistency.
- **Dark Theme Toggle Switch:** Implemented dark mode toggling directly in `App.jsx`, saving preferences to `localStorage`. Set up variables under `body.dark-theme` for background, card background, typography colors, select options, buttons, and form inputs to ensure seamless visual transition.
- **Verified Build:** Verified compile validity using `npm run build` — built successfully.
- **Button Contrast Fixes:** 
  - Styled all default/unclassed `<button>` elements to automatically use `--bg-card` and `--text-main` instead of relying on default browser backgrounds with inherited white text in dark mode.
  - Formatted the prompt suggestions on the landing page into modern capsule pills (`.prompt-row button`).
  - Removed remaining hardcoded old brand color `#185d5b` from all dashboard active card borders and auth link buttons, replacing them with dynamic `var(--accent)`.

## 2026-07-12 UI Polish Sprint v2

Refined the client dashboard into a premium, high-density SaaS experience with improved visual hierarchy, better use of screen real estate, and a more interactive feel.

### Improvements & Design Justifications:
- **Wider Content Layout:** Expanded `.page-section` max-width from `1200px` to `1440px`, reducing excessive whitespace on larger screens and giving the dashboard a more premium, information-dense feel.
- **Dashboard Header Status Bar:** Replaced the plain header subtext with a live status strip showing a pulsing green "AI Agent Online" indicator dot, current plan badge, total leads count, and total page views — all as inline `.status-item` chips. Gives operators an instant operational overview without navigating to the Analytics tab.
- **Pulsing Online Indicator:** Added `.pulsing-dot` CSS animation (scale + glow keyframe at 1.8s cycle) to communicate live system status at a glance, inspired by production monitoring dashboards.
- **Chat Sandbox Upgrade:** Redesigned the Chatbot Sandbox panel with:
  - A "Reset Chat" secondary button in the panel header.
  - Animated typing indicator (three bouncing dots using `@keyframes typing-dots`) replacing the plain "Thinking..." text.
  - Quick Test Suggestions chips shown beneath the initial welcome message to help operators start testing immediately.
- **Analytics KPI Hero Cards:** Replaced the 5-column small stat grid with 4 large KPI cards (Conversations, Leads Captured, Conversion Rate, Avg Lead Score). Each card features an icon, large bold value, and contextual sub-label — matching the data-forward design language of tools like Stripe Dashboard and Linear.
- **Form Section Groups:** Added labeled section dividers (Business Identity, Services & Knowledge, Receptionist AI) with hairline `<hr>` separators within the chatbot settings form, breaking up the single long form into logical visual groups.
- **Button Padding Increase:** Bumped `.primary-button`, `.secondary-button`, `.nav-link` padding from `0.5rem 1rem` to `0.6rem 1.25rem` for a more solid, clickable feel.
- **KPI Grid Responsive Rules:** Added `@media` breakpoints so the 4-column KPI grid collapses to 2 columns at `≤992px` and remains 2-column at `≤768px`. Header status bar stacks vertically on mobile.
- **Hardcoded Color Cleanup:** Replaced remaining `#61706e` green-gray color in the Calendar integration panel with `var(--text-muted)` for full dark-mode compatibility.
- **Verified Build:** `npm run build` compiled successfully with 0 errors in 549ms.

## 2026-07-12 Glassmorphism Sprint

Layered a consistent frosted-glass (glassmorphism) treatment across all UI surfaces for a premium, depth-rich visual identity.

### Design Tokens Added:
- `--bg-glass` — semi-transparent panel background (light: `rgba(255,255,255,0.72)`, dark: `rgba(24,24,27,0.65)`)
- `--bg-glass-hover` — elevated glass on hover
- `--border-glass` — **fixed**: light mode now uses a visible `rgba(12,13,14,0.09)` dark border (was invisible white-on-white); dark mode uses `rgba(255,255,255,0.08)`
- `--shadow-glass` — soft diffused depth shadow for glass surfaces

### Glass Applied To:
- **Navbar (`.topbar`):** Upgraded to `blur(24px) saturate(180%)` for a stronger frosted bar with gradient-border glow and shadow lift.
- **All Cards & Panels:** `.analytics-panel`, `.dashboard-card`, `.auth-panel`, `.demo-console` — all use `blur(12px) saturate(160%)` glass backgrounds.
- **KPI Hero Cards:** `blur(12px) saturate(160%)` glass with hover elevation.
- **Tab Navigation:** Wrapped in a new `.glass-tab-nav` pill container with `blur(16px) saturate(180%)`, rounded corners, and inset shadow.
- **Secondary Buttons:** Frosted `blur(8px)` glass background.
- **Inputs/Textareas/Selects:** Glass background with `blur(6px)` for depth inside form panels.
- **Chat Window:** Glass inset with `blur(8px)` for the sandbox message area.
- **Status-Item Chips:** Header status bar chips now use `blur(10px)` frosted glass pills.
- **Status Pills:** `.status-pill` and `.status-pill.warning` both get `blur(8px)` glass with border.
- **List Rows:** `.business-selector-item`, `.funnel-row`, `.activity-item`, `.lead-chip` all use glass background.
- **Alert Banners:** `.analytics-banner` error and success states get `blur(10px)` frosted treatment.
- **Background Gradient:** Strengthened body radial gradients (violet 6%, amber 4%) so glass blur surfaces have visible depth behind them.
- **Verified Build:** `npm run build` compiled successfully in 381ms.






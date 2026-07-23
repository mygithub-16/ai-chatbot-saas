# Autonomous Business System

The app is structured around a self-serve business onboarding flow:

- A business profile defines services, FAQs, policies, tone, and personality prompt.
- The chatbot uses that profile as context for replies.
- Events are captured for page views, demo starts, demo completions, leads, and business creation.
- Analytics converts those events into funnel and lead-quality views.

The current rebuild keeps the automation conservative and transparent. Real billing, email, CRM, and scheduler integrations should be added behind explicit service adapters.

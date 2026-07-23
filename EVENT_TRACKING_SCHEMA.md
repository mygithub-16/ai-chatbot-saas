# Event Tracking Schema

Events are stored in the `events` table.

| Field | Type | Notes |
| --- | --- | --- |
| `event_name` | string | Canonical names include `page_view`, `demo_started`, `demo_completed`, `lead_submitted`, `business_created`. |
| `timestamp` | datetime | Defaults to UTC now. |
| `session_id` | string | Browser/demo session key. |
| `user_id` | integer | Optional user reference. |
| `business_id` | integer | Optional business reference. |
| `metadata_json` | object | Flexible event details. |

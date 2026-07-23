from __future__ import annotations

import re
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db import get_db, SessionLocal
from backend.models import Business, ConversationSession, Lead, Event
from backend.ai import (
    classify_booking_message as ai_classify_booking_message,
    extract_booking_entities as ai_extract_booking_entities,
    generate_booking_reply as ai_generate_booking_reply,
    generate_response as ai_generate_response,
    get_service_menu as ai_get_service_menu,
)

router = APIRouter(tags=["Chat Widget"])


class WidgetChatPayload(BaseModel):
    message: str = Field(min_length=1)
    business_id: Optional[int] = None
    business_name: Optional[str] = None
    business_ref: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None


def get_business_by_ref(db: Session, business_id: Optional[int], business_name: Optional[str], business_ref: Optional[str]) -> Optional[Business]:
    if business_ref:
        if business_ref.startswith("custom:") or business_ref.startswith("demo:"):
            try:
                extracted_id = int(business_ref.split(":", 1)[1])
                b = db.query(Business).filter(Business.id == extracted_id).first()
                if b:
                    return b
            except ValueError:
                pass
        try:
            extracted_id = int(business_ref)
            b = db.query(Business).filter(Business.id == extracted_id).first()
            if b:
                return b
        except ValueError:
            pass

    if business_id is not None:
        b = db.query(Business).filter(Business.id == business_id).first()
        if b:
            return b

    if business_name:
        b = db.query(Business).filter(Business.business_name == business_name).first()
        if b:
            return b

    return db.query(Business).order_by(Business.created_at.asc()).first()


@router.get("/widget/embed.js")
def get_widget_embed_js():
    js_content = """(function() {
  var scriptTag = document.currentScript || document.querySelector('script[src*="embed.js"]');
  var businessId = scriptTag ? scriptTag.getAttribute('data-business-id') : null;
  if (!businessId) {
    console.error("ECHURA Widget: Missing data-business-id attribute on script tag.");
    return;
  }
  var baseUrl = window.location.origin;
  var container = document.createElement('div');
  container.id = 'echura-chat-widget';
  container.style.position = 'fixed';
  container.style.bottom = '20px';
  container.style.right = '20px';
  container.style.zIndex = '999999';
  container.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  
  var button = document.createElement('button');
  button.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
  button.style.width = '60px';
  button.style.height = '60px';
  button.style.borderRadius = '50%';
  button.style.backgroundColor = '#185d5b';
  button.style.color = '#ffffff';
  button.style.border = 'none';
  button.style.boxShadow = '0 4px 16px rgba(24,93,91,0.3)';
  button.style.cursor = 'pointer';
  button.style.display = 'flex';
  button.style.alignItems = 'center';
  button.style.justifyContent = 'center';
  button.style.transition = 'all 0.2s ease-in-out';
  
  var iframe = document.createElement('iframe');
  iframe.src = baseUrl + '/widget/' + businessId;
  iframe.style.width = '380px';
  iframe.style.height = '580px';
  iframe.style.border = 'none';
  iframe.style.borderRadius = '16px';
  iframe.style.boxShadow = '0 12px 36px rgba(0,0,0,0.18)';
  iframe.style.display = 'none';
  iframe.style.position = 'absolute';
  iframe.style.bottom = '75px';
  iframe.style.right = '0';
  iframe.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
  iframe.style.transform = 'translateY(12px)';
  iframe.style.opacity = '0';
  
  var isOpen = false;
  button.onclick = function() {
    isOpen = !isOpen;
    if (isOpen) {
      iframe.style.display = 'block';
      setTimeout(function() {
        iframe.style.opacity = '1';
        iframe.style.transform = 'translateY(0)';
      }, 10);
      button.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
    } else {
      iframe.style.opacity = '0';
      iframe.style.transform = 'translateY(12px)';
      setTimeout(function() { iframe.style.display = 'none'; }, 250);
      button.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
    }
  };
  container.appendChild(iframe);
  container.appendChild(button);
  document.body.appendChild(container);
})();"""
    return Response(content=js_content, media_type="application/javascript")


@router.get("/widget/{business_ref}")
def get_widget_iframe_page(business_ref: str, db: Session = Depends(get_db)):
    business = get_business_by_ref(db, None, None, business_ref)
    b_name = business.business_name if business else "Virtual Assistant"
    b_desc = business.business_description if business else "AI Virtual Assistant"
    b_id = str(business.id) if business else "1"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chat Assistant</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8fafc;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .chat-header {{
      background: #185d5b;
      color: white;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .status-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px rgba(16,185,129,0.6);
    }}
    .chat-header h3 {{
      margin: 0;
      font-size: 15px;
      font-weight: 600;
    }}
    .chat-header p {{
      margin: 2px 0 0;
      font-size: 11px;
      opacity: 0.85;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 280px;
    }}
    .chat-messages {{
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f1f5f9;
    }}
    .message {{
      max-width: 82%;
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.45;
      animation: fadeIn 0.2s ease-out;
      word-wrap: break-word;
    }}
    .message.assistant {{
      background: #ffffff;
      color: #0f172a;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .message.user {{
      background: #185d5b;
      color: #ffffff;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }}
    .chat-input-area {{
      padding: 12px 14px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
    }}
    .chat-input {{
      flex: 1;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 13.5px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .chat-input:focus {{
      border-color: #185d5b;
    }}
    .send-btn {{
      background: #185d5b;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 0 16px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
    }}
    .send-btn:hover {{
      background: #124644;
    }}
    .send-btn:disabled {{
      opacity: 0.6;
      cursor: not-allowed;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
  </style>
</head>
<body>
  <div class="chat-header">
    <div class="status-dot"></div>
    <div>
      <h3>{b_name}</h3>
      <p>{b_desc}</p>
    </div>
  </div>
  <div class="chat-messages" id="messages">
    <div class="message assistant">
      Hi! I'm the virtual assistant for {b_name}. How can I assist you today?
    </div>
  </div>
  <form class="chat-input-area" id="chat-form">
    <input type="text" class="chat-input" id="chat-input" placeholder="Type a message or request a booking..." autocomplete="off">
    <button type="submit" class="send-btn" id="send-btn">Send</button>
  </form>

  <script>
    var messagesContainer = document.getElementById('messages');
    var chatForm = document.getElementById('chat-form');
    var chatInput = document.getElementById('chat-input');
    var sendBtn = document.getElementById('send-btn');
    var businessRef = "{business_ref}";
    var businessId = "{b_id}";
    var businessName = "{b_name}";

    var sessionKey = 'echura_session_' + businessRef;
    var sessionId = localStorage.getItem(sessionKey);
    if (!sessionId) {{
      sessionId = 'widget-session-' + Math.random().toString(36).substring(2) + '-' + Date.now();
      localStorage.setItem(sessionKey, sessionId);
    }}

    function appendMessage(role, content) {{
      var msg = document.createElement('div');
      msg.className = 'message ' + role;
      msg.textContent = content;
      messagesContainer.appendChild(msg);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }}

    chatForm.onsubmit = function(e) {{
      e.preventDefault();
      var message = chatInput.value.trim();
      if (!message) return;

      appendMessage('user', message);
      chatInput.value = '';
      chatInput.disabled = true;
      sendBtn.disabled = true;

      fetch('/api/widget/chat', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          message: message,
          session_id: sessionId,
          business_ref: businessRef,
          business_name: businessName,
          business_id: isNaN(parseInt(businessId)) ? null : parseInt(businessId)
        }})
      }})
      .then(function(r) {{ return r.json(); }})
      .then(function(data) {{
        const reply = data.response || data.reply || data.message || 'Thank you for your message.';
        appendMessage('assistant', reply);
      }})
      .catch(function(err) {{
        appendMessage('assistant', 'Our virtual receptionist is temporarily unavailable right now.');
      }})
      .finally(function() {{
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
      }});
    }};
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@router.post("/demo/chat")
@router.post("/chat")
@router.post("/api/widget/chat")
def widget_chat(payload: WidgetChatPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    session_id = payload.session_id or "widget-session"
    business = get_business_by_ref(db, payload.business_id, payload.business_name, payload.business_ref)
    
    if not business:
        return {
            "ok": True,
            "response": "Hello! How can I help you today?",
            "conversation_state": {},
        }

    b_name = business.business_name or business.name
    b_context = {
        "business_description": business.business_description or "",
        "services_products": business.services_products or "",
        "faqs": business.faqs or "",
        "policies": business.policies or "",
        "tone_style": business.tone_style or "friendly and professional",
    }

    conversation_session = db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()
    if conversation_session is None:
        conversation_session = ConversationSession(
            session_id=session_id,
            user_id=payload.user_id,
            business_id=business.id,
            intent=None,
            status="collecting",
            workflow_state_json={},
            slots_json={},
            missing_slots_json=[],
            history_json=[],
        )
        db.add(conversation_session)
        db.commit()
        db.refresh(conversation_session)

    # Simplified response generation
    response_text = ai_generate_response(
        message=payload.message,
        business_name=b_name,
        business_personality_prompt=business.personality_prompt or "",
        conversation_context=f"Business Description: {b_context['business_description']}\nServices: {b_context['services_products']}\nFAQs: {b_context['faqs']}",
        business_context=b_context,
    ) or "Thank you for reaching out! How else can I assist you?"

    # Record event
    event = Event(
        event_name="demo_completed",
        timestamp=conversation_session.updated_at,
        session_id=session_id,
        business_id=business.id,
        user_id=payload.user_id,
        metadata_json={"message_len": len(payload.message), "source": "widget_chat"},
    )
    db.add(event)
    db.commit()

    return {
        "ok": True,
        "response": response_text,
        "business": {"id": business.id, "name": b_name},
    }

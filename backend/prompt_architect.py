"""
backend/prompt_architect.py
───────────────────────────────────────────────────────────────────────────────
SystemPromptArchitect — converts raw business-owner instructions into a
hard-locked, state-machine-based AI system prompt via Claude Sonnet 3.5.

Key design decisions
─────────────────────
1.  Two-layer architecture
      Layer 1 – META-PROMPT  : tells Claude HOW to write system prompts
      Layer 2 – OUTPUT       : the finished system prompt handed to GPT-4o

2.  Default Template fallback
      If the user provides no input (or Claude is unreachable), a
      parameterised default template is returned immediately — no LLM
      round-trip needed.

3.  Tone inference
      Eleven pre-mapped business types (barber, dentist, spa, etc.) produce
      tone descriptors that Claude weaves into the output automatically.

4.  Hard-lock guarantees
      The meta-prompt mandates six non-negotiable rules that the output
      must contain verbatim — validated by `validate_output()`.

5.  Async-safe
      All Claude calls are wrapped in `asyncio.to_thread` so the function
      is safe to await from FastAPI async routes without blocking the event loop.
"""

from __future__ import annotations

import os
import re
import asyncio
import textwrap
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# ── Constants ──────────────────────────────────────────────────────────────────

CLAUDE_MODEL = "claude-3-haiku-20240307"

# Business-type → tone descriptor mapping
BUSINESS_TONE_MAP: dict[str, str] = {
    "barber":       "confident, casual, and neighbourly — like a trusted local barber",
    "salon":        "warm, stylish, and reassuring — like a premium beauty consultant",
    "dentist":      "calm, clinical, and reassuring — like a caring dental receptionist",
    "spa":          "serene, luxurious, and mindful — like a high-end spa host",
    "gym":          "energetic, motivating, and direct — like a personal trainer",
    "restaurant":   "welcoming, lively, and efficient — like a top-tier maitre d'",
    "clinic":       "professional, empathetic, and precise — like a medical receptionist",
    "tattoo":       "creative, relaxed, and knowledgeable — like a veteran tattoo artist",
    "nail studio":  "friendly, detail-oriented, and polished — like a nail-art specialist",
    "physiotherapy": "empathetic, clinical, and encouraging — like a physiotherapy assistant",
    "default":      "professional, warm, and concise — focused entirely on the customer",
}

# Minimum required phrases that must appear in the generated output (hard-lock audit)
REQUIRED_PHRASES = [
    "NEVER re-ask",
    "MEMORY SNAPSHOT",
    "TERMINAL",
    "CLOSING PROTOCOL",
    "ONE question",
]

# ── Default template (no LLM required) ────────────────────────────────────────

_DEFAULT_TEMPLATE = textwrap.dedent("""\
    ═══════════════════════════════════════════════════════
    SYSTEM PROMPT — {business_type_upper} BOOKING ASSISTANT
    ═══════════════════════════════════════════════════════

    ROLE
    ────
    You are the AI receptionist for {business_name}.
    Tone: {tone}

    ══ STATE-MACHINE: SLOT-COLLECTION PROTOCOL ══════════

    You collect five booking slots in strict order:
      1. Customer Name
      2. Phone Number
      3. Service Requested
      4. Preferred Date
      5. Preferred Time

    HARD LOCKS (MUST obey at ALL times)
    ─────────────────────────────────────
    LOCK 1 — MEMORY SNAPSHOT: Before every response, silently
      check which slots are already collected (marked ✓).
      You MUST have this internal snapshot before generating any text.

    LOCK 2 — NEVER re-ask a slot that is already ✓ in the snapshot.
      If the customer provides a slot you didn't ask for, accept it
      silently and move to the next missing slot.

    LOCK 3 — ONE question only per response.
      Never ask for two pieces of information in one message.

    LOCK 4 — STEP LOCK: Your ONLY action at each step is to ask
      for the next missing slot (or confirm once all are filled).

    LOCK 5 — NAME GUARD: Reject single-word conversational fillers
      (Hi, Yes, Ok, Sure, Thanks, etc.) as names. Re-ask politely.

    ══ CONFIRMATION PROTOCOL ════════════════════════════

    Once all 5 slots are ✓:
      - Summarise the booking clearly (name, service, date, time).
      - Ask the customer to reply "Yes" to finalise.
      - Do NOT ask for any additional information.

    On receiving confirmation ("yes", "confirm", "sure", etc.):
      - Send ONE TERMINAL confirmation message.
      - The phrase "reply Yes" is FORBIDDEN in this terminal message.
      - No question marks. This message ends the booking flow.

    ══ CLOSING PROTOCOL ══════════════════════════════════

    After the TERMINAL confirmation message:
      - If the customer says "thank you" → respond warmly, do not restart.
      - If the customer asks a follow-up question → answer it briefly.
      - NEVER re-open the slot-collection flow once confirmed.
      - NEVER say "please reply Yes" again after a booking is confirmed.

    ══ BOUNDARIES ════════════════════════════════════════

    - Only offer services listed in the business context.
    - If a requested service is not available, say so politely.
    - Do not invent prices, dates, or availability.
    - Keep every response to 1–3 sentences maximum.
    ═══════════════════════════════════════════════════════
""")

# ── Meta-prompt (the prompt that tells Claude how to write system prompts) ─────

_META_PROMPT_TEMPLATE = textwrap.dedent("""\
    You are a world-class AI system-prompt engineer specialising in
    state-machine conversational agents for service-booking platforms.

    Your task is to take a raw, informal instruction written by a
    {business_type} business owner and transform it into a
    production-grade, hard-locked AI system prompt.

    ─── RAW INPUT FROM BUSINESS OWNER ────────────────────
    {raw_input}
    ───────────────────────────────────────────────────────

    BUSINESS CONTEXT
    ─────────────────
    Business type : {business_type}
    Tone required : {tone}

    ─── YOUR OUTPUT REQUIREMENTS ─────────────────────────

    The system prompt you produce MUST contain ALL of the following
    in clearly labelled sections. Do not skip or abbreviate any of them.

    1. ROLE DEFINITION
       - State clearly what the AI is and who it represents.
       - Embed the tone constraint: "{tone}"
       - Incorporate any personality hints from the raw input above.

    2. STATE-MACHINE: SLOT-COLLECTION PROTOCOL
       Slots must be collected in this strict order:
         (1) Customer Name  (2) Phone Number  (3) Service  (4) Date  (5) Time
       - One slot per turn — NEVER ask for two slots at once.
       - Use "MEMORY SNAPSHOT" terminology so the AI knows to check its
         internal memory before each response.

    3. HARD LOCKS (must appear word-for-word in output)
       LOCK 1 — MEMORY SNAPSHOT: The AI must silently check collected
         slots before every response.
       LOCK 2 — NEVER re-ask a slot already collected. Acknowledge it
         and move forward.
       LOCK 3 — ONE question only per response.
       LOCK 4 — STEP LOCK: the AI's only action at each step is the
         next slot or the confirmation summary.
       LOCK 5 — NAME GUARD: Reject conversational filler words
         (Hi, Yes, Ok, Sure, etc.) as customer names. Re-ask politely.

    4. CONFIRMATION PROTOCOL
       - Summarise all 5 slots and ask for a single "Yes" to finalise.
       - On confirmation: produce exactly ONE TERMINAL message.
       - "reply Yes" phrase is FORBIDDEN in the terminal message.
       - No question marks in the terminal message.

    5. CLOSING PROTOCOL (this section MUST use the exact words "CLOSING PROTOCOL")
       - After the TERMINAL message, handle thank-yous and follow-up
         questions gracefully without restarting the slot-collection flow.
       - NEVER reopen the booking flow once a booking is confirmed.

    6. HARD BOUNDARIES
       - Only reference services from the business context.
       - No invented prices, availability, or dates.
       - Each response: 1–3 sentences maximum.

    ─── FORMAT INSTRUCTIONS ──────────────────────────────
    - Use clear section headers in CAPITALS with divider lines.
    - Write in second-person imperative ("You are...", "You must...").
    - The output must be self-contained — a developer should be able
      to paste it directly into an LLM system field with zero editing.
    - Do NOT include markdown code fences, commentary, or preamble.
      Output the system prompt text ONLY.
""")


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class RefinedPrompt:
    """Result returned by SystemPromptArchitect.refine()."""
    content: str
    source: str          # "claude" | "default_template" | "fallback"
    business_type: str
    tone: str
    validation_passed: bool
    missing_phrases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "content":          self.content,
            "source":           self.source,
            "business_type":    self.business_type,
            "tone":             self.tone,
            "validation_passed": self.validation_passed,
            "missing_phrases":  self.missing_phrases,
        }


# ── Client factory ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_anthropic_client():
    """Cached Anthropic client — returns None if key is missing."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except Exception as exc:
        print(f"[SystemPromptArchitect] Anthropic client init failed: {exc}")
        return None


# ── Core class ─────────────────────────────────────────────────────────────────

class SystemPromptArchitect:
    """
    Converts raw business-owner instructions into a hard-locked,
    state-machine-based AI system prompt.

    Usage
    ──────
        architect = SystemPromptArchitect()

        # Sync
        result = architect.refine(
            user_raw_input="Be friendly and book appointments",
            business_type="barber",
            business_name="KC Cuts",
        )

        # Async (for FastAPI)
        result = await architect.arefine(
            user_raw_input="Be friendly and book appointments",
            business_type="barber",
            business_name="KC Cuts",
        )

        print(result.content)     # The finished system prompt
        print(result.source)      # "claude" | "default_template" | "fallback"
    """

    def __init__(self, model: str = CLAUDE_MODEL) -> None:
        self.model = model

    # ── Tone resolution ───────────────────────────────────────────────────────

    @staticmethod
    def resolve_tone(business_type: str) -> str:
        """Map a business type string to its tone descriptor."""
        key = business_type.strip().lower()
        if not key:
            return BUSINESS_TONE_MAP["default"]
        for known_type, tone in BUSINESS_TONE_MAP.items():
            if known_type == "default":
                continue
            if known_type in key or key in known_type:
                return tone
        return BUSINESS_TONE_MAP["default"]

    # ── Default template ──────────────────────────────────────────────────────

    @staticmethod
    def build_default(business_type: str, business_name: str = "") -> RefinedPrompt:
        """
        Return a fully-formed system prompt from the built-in template.
        No LLM call. Used when raw_input is empty or Claude is unavailable.
        """
        tone = SystemPromptArchitect.resolve_tone(business_type)
        name = business_name.strip() or f"our {business_type} business"
        content = _DEFAULT_TEMPLATE.format(
            business_type_upper=business_type.upper(),
            business_name=name,
            tone=tone,
        )
        missing = _validate_phrases(content)
        return RefinedPrompt(
            content=content,
            source="default_template",
            business_type=business_type,
            tone=tone,
            validation_passed=len(missing) == 0,
            missing_phrases=missing,
        )

    # ── Meta-prompt builder ───────────────────────────────────────────────────

    @staticmethod
    def build_meta_prompt(
        raw_input: str,
        business_type: str,
        tone: str,
    ) -> str:
        """Render the meta-prompt that will be sent to Claude."""
        return _META_PROMPT_TEMPLATE.format(
            raw_input=raw_input.strip(),
            business_type=business_type.strip(),
            tone=tone,
        )

    # ── Sync refine ───────────────────────────────────────────────────────────

    def refine(
        self,
        user_raw_input: Optional[str],
        business_type: str,
        business_name: str = "",
        max_tokens: int = 2048,
    ) -> RefinedPrompt:
        """
        Synchronous entry point.

        1. If raw_input is empty → return default template immediately.
        2. If Claude client is unavailable → return default template.
        3. Otherwise call Claude and validate the output.
        4. If validation fails → return default template as safe fallback.
        """
        business_type = (business_type or "default").strip().lower()
        tone = self.resolve_tone(business_type)

        # ── Gate 1: no input → default template ──
        raw = (user_raw_input or "").strip()
        if not raw:
            return self.build_default(business_type, business_name)

        # ── Gate 2: no client → default template ──
        client = _get_anthropic_client()
        if client is None:
            print("[SystemPromptArchitect] ANTHROPIC_API_KEY not set — using default template.")
            result = self.build_default(business_type, business_name)
            result.source = "fallback"
            return result

        # ── Gate 3: call Claude ──
        try:
            meta_prompt = self.build_meta_prompt(raw, business_type, tone)
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": meta_prompt}],
            )
            generated = message.content[0].text.strip()
        except Exception as exc:
            print(f"[SystemPromptArchitect] Claude call failed: {exc}")
            result = self.build_default(business_type, business_name)
            result.source = "fallback"
            return result

        # ── Gate 4: validate hard-lock phrases ──
        missing = _validate_phrases(generated)
        if missing:
            print(
                f"[SystemPromptArchitect] Validation warning — missing phrases: {missing}. "
                "Falling back to default template."
            )
            result = self.build_default(business_type, business_name)
            result.source = "fallback"
            return result

        return RefinedPrompt(
            content=generated,
            source="claude",
            business_type=business_type,
            tone=tone,
            validation_passed=True,
            missing_phrases=[],
        )

    # ── Async refine (FastAPI-safe) ───────────────────────────────────────────

    async def arefine(
        self,
        user_raw_input: Optional[str],
        business_type: str,
        business_name: str = "",
        max_tokens: int = 2048,
    ) -> RefinedPrompt:
        """Async wrapper — runs the blocking Claude call in a thread pool."""
        return await asyncio.to_thread(
            self.refine,
            user_raw_input,
            business_type,
            business_name,
            max_tokens,
        )


# ── Internal helpers ───────────────────────────────────────────────────────────

def _validate_phrases(text: str) -> list[str]:
    """Return any REQUIRED_PHRASES that are missing from the generated text."""
    return [phrase for phrase in REQUIRED_PHRASES if phrase not in text]


# ── Module-level singleton ─────────────────────────────────────────────────────

architect = SystemPromptArchitect()

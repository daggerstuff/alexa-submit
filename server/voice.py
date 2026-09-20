"""Voice rendering helpers: SSML for Alexa read-back and spoken summaries.

The server returns plain prose (`content`, `summary`) plus parallel SSML fields
(`ssml`, `spoken_summary`) so a voice adapter can hand the SSML straight to TTS
without re-parsing punctuation. Only the portable SSML subset that Alexa and
most TTS engines share is used: ``<speak>``, ``<prosody>``, and ``<break>``.
"""

from __future__ import annotations

_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
}

NEUTRAL_PROSODY = 'rate="medium" pitch="medium"'

# emotional_state -> prosody attributes. Values are constrained to the SSML
# enumerations Alexa accepts (rate/pitch/volume). Unlisted states read in the
# neutral voice; the table intentionally covers the states the scenario library
# and persona policy actually emit, with the emotionally loaded ones that change
# how a line should sound.
EMOTION_PROSODY: dict[str, str] = {
    # Agitated / distressed: faster, higher.
    "anxious": 'rate="fast" pitch="high"',
    "worried": 'rate="fast" pitch="high"',
    "scared": 'rate="fast" pitch="high"',
    "afraid": 'rate="fast" pitch="high"',
    "fearful": 'rate="fast" pitch="high"',
    "frightened": 'rate="fast" pitch="high"',
    "alarmed": 'rate="fast" pitch="high"',
    "distressed": 'rate="fast" pitch="high"',
    "urgent": 'rate="fast" pitch="high"',
    "overwhelmed": 'rate="fast" pitch="high"',
    "frustrated": 'rate="fast" pitch="high"',
    # Low / withdrawn: slower, lower, softer.
    "guarded": 'rate="slow" pitch="low" volume="soft"',
    "reflective": 'rate="slow" pitch="low"',
    "flat": 'rate="slow" pitch="low"',
    "withdrawn": 'rate="slow" pitch="low" volume="soft"',
    "down": 'rate="slow" pitch="low"',
    "hopeless": 'rate="slow" pitch="low"',
    "despondent": 'rate="slow" pitch="low"',
    "miserable": 'rate="slow" pitch="low"',
    "exhausted": 'rate="slow" pitch="low"',
    "tired": 'rate="slow" pitch="low"',
    # Calm / positive: medium, warm.
    "calm": 'rate="medium" pitch="medium"',
    "concerned": 'rate="medium" pitch="medium"',
    "reassured": 'rate="medium" pitch="medium"',
    "relieved": 'rate="medium" pitch="medium"',
    "hopeful": 'rate="medium" pitch="medium"',
    "tender": 'rate="slow" pitch="low" volume="soft"',
}


def ssml_escape(text: str) -> str:
    """Escape XML special characters so plain prose is valid SSML."""
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def prosody_for(emotional_state: str | None) -> str:
    """Return the prosody attributes for an emotional state; neutral by default."""
    if not emotional_state:
        return NEUTRAL_PROSODY
    return EMOTION_PROSODY.get(emotional_state.strip().lower(), NEUTRAL_PROSODY)


def speak(content: str, emotional_state: str | None = None) -> str:
    """Wrap patient prose in SSML with emotion-driven prosody."""
    attrs = prosody_for(emotional_state)
    return f"<speak><prosody {attrs}>{ssml_escape(content)}</prosody></speak>"


def spoken_evaluation(overall_score: int, max_score: int, summary: str) -> str:
    """A score-prefixed SSML read-back of the evaluator's coaching takeaway."""
    return speak(f"You scored {overall_score} out of {max_score}. {summary}", "calm")

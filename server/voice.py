"""Voice rendering helpers: SSML for Alexa read-back and spoken summaries.

The server returns plain prose (`content`, `summary`) plus parallel SSML fields
(`ssml`, `spoken_summary`) so a voice adapter can hand the SSML straight to TTS
without re-parsing punctuation. Only the portable SSML subset that Alexa and
most TTS engines share is used: ``<speak>``, ``<prosody>``, and ``<break>``.
"""

from __future__ import annotations

import re

_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
}

# Control characters that are illegal in XML 1.0 and therefore in SSML. They can
# appear in LLM-generated prose; strip them rather than emitting invalid SSML.
_XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

NEUTRAL_PROSODY = 'rate="medium" pitch="medium"'

# emotional_state -> prosody attributes. Values are constrained to the SSML
# enumerations Alexa accepts (rate/pitch/volume). Every state the scenario
# library and the persona policy emit is mapped here (tests/test_voice.py
# enforces that invariant so a new scenario cannot silently fall back to
# neutral); truly unknown states read in the neutral voice.
EMOTION_PROSODY: dict[str, str] = {
    # High arousal / distress — faster, higher.
    "afraid": 'rate="fast" pitch="high"',
    "alarmed": 'rate="fast" pitch="high"',
    "anxious": 'rate="fast" pitch="high"',
    "distressed": 'rate="fast" pitch="high"',
    "fearful": 'rate="fast" pitch="high"',
    "frightened": 'rate="fast" pitch="high"',
    "frustrated": 'rate="fast" pitch="high"',
    "overwhelmed": 'rate="fast" pitch="high"',
    "scared": 'rate="fast" pitch="high"',
    "shaken": 'rate="fast" pitch="high"',
    "urgent": 'rate="fast" pitch="high"',
    "worried": 'rate="fast" pitch="high"',
    "unsettled": 'rate="medium" pitch="high"',
    # Low / withdrawn — slower, lower, often softer.
    "ambivalent": 'rate="slow" pitch="low"',
    "ashamed": 'rate="slow" pitch="low" volume="soft"',
    "despondent": 'rate="slow" pitch="low"',
    "discouraged": 'rate="slow" pitch="low"',
    "down": 'rate="slow" pitch="low"',
    "embarrassed": 'rate="slow" pitch="low" volume="soft"',
    "exhausted": 'rate="slow" pitch="low"',
    "flat": 'rate="slow" pitch="low"',
    "guarded": 'rate="slow" pitch="low" volume="soft"',
    "guilty": 'rate="slow" pitch="low" volume="soft"',
    "hopeless": 'rate="slow" pitch="low"',
    "in pain": 'rate="slow" pitch="low"',
    "lonely": 'rate="slow" pitch="low"',
    "miserable": 'rate="slow" pitch="low"',
    "nauseated": 'rate="slow" pitch="low"',
    "reflective": 'rate="slow" pitch="low"',
    "regretful": 'rate="slow" pitch="low"',
    "sensitive": 'rate="slow" pitch="low" volume="soft"',
    "tender": 'rate="slow" pitch="low" volume="soft"',
    "tired": 'rate="slow" pitch="low"',
    "uncertain": 'rate="slow" pitch="low"',
    "unsteady": 'rate="slow" pitch="low"',
    "withdrawn": 'rate="slow" pitch="low" volume="soft"',
    # Calm / positive / neutral — medium.
    "calm": 'rate="medium" pitch="medium"',
    "casual": 'rate="medium" pitch="medium"',
    "concerned": 'rate="medium" pitch="medium"',
    "confused": 'rate="medium" pitch="medium"',
    "defensive": 'rate="medium" pitch="medium"',
    "familiar": 'rate="medium" pitch="medium"',
    "hopeful": 'rate="medium" pitch="medium"',
    "reassured": 'rate="medium" pitch="medium"',
    "relieved": 'rate="medium" pitch="medium"',
    "unaware": 'rate="medium" pitch="medium"',
    "uncomfortable": 'rate="medium" pitch="medium"',
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
    """Wrap patient prose in SSML with emotion-driven prosody.

    XML-illegal control characters are stripped so the result is always valid
    SSML regardless of what an LLM or author put in the source prose.
    """
    attrs = prosody_for(emotional_state)
    cleaned = _XML_ILLEGAL.sub("", content)
    return f"<speak><prosody {attrs}>{ssml_escape(cleaned)}</prosody></speak>"


def spoken_evaluation(overall_score: int, max_score: int, summary: str) -> str:
    """A score-prefixed SSML read-back of the evaluator's coaching takeaway."""
    return speak(f"You scored {overall_score} out of {max_score}. {summary}", "calm")

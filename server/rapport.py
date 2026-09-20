from __future__ import annotations

from server.scenarios import ScenarioDefinition, matches_term

# Bounds for the per-session rapport score. The patient starts at 0 and each
# turn moves at most one step: a warm turn (+1) earns trust, a dismissive or
# rushed turn (-1) erodes it.
RAPPORT_FLOOR = -3
RAPPORT_CEILING = 3

# Phrases that signal warmth, empathy, or checking in. Kept phrase-based (matched
# via matches_term, i.e. word-start prefixes) so single clinical words don't
# accidentally move the meter.
RAPPORT_POSITIVE = (
    "how are you",
    "how are you feeling",
    "how are you doing",
    "i'm sorry",
    "i am sorry",
    "that sounds",
    "that must be",
    "must be hard",
    "must be scary",
    "must be frightening",
    "i understand",
    "i hear you",
    "thank you",
    "thanks for",
    "is it okay",
    "okay if i",
    "would it be okay",
    "if i may",
    "take your time",
    "you're doing",
    "you are doing",
    "i'm here",
    "i am here",
    "tell me more",
    "i can imagine",
)

# Phrases that signal coldness, rushing, or dismissal. Scenario `pitfalls` are
# also treated as negative rapport (see rapport_delta), so authoring stays
# scenario-local while this list covers the generic case.
RAPPORT_NEGATIVE = (
    "calm down",
    "you're fine",
    "you are fine",
    "you'll be fine",
    "you will be fine",
    "it's nothing",
    "it is nothing",
    "not a big deal",
    "no big deal",
    "hurry up",
    "make it quick",
    "be quick",
    "i don't have time",
    "i do not have time",
    "no time for",
    "whatever",
    "be quiet",
    "just answer",
    "overreact",
    "being dramatic",
    "so dramatic",
    "get to the point",
)


def rapport_delta(text: str, scenario: ScenarioDefinition) -> int:
    """Return the rapport change for one practitioner utterance.

    Dismissive language (scenario pitfalls or the generic negative lexicon)
    outweighs warmth: a brusque turn erodes trust even if it also said "sorry".
    """
    lowered = text.lower()
    if any(matches_term(term, lowered) for term in RAPPORT_NEGATIVE) or any(
        matches_term(term, lowered) for term in scenario.pitfalls
    ):
        return -1
    if any(matches_term(term, lowered) for term in RAPPORT_POSITIVE):
        return 1
    return 0


def clamp_rapport(value: int) -> int:
    """Clamp a rapport value into the session bounds."""
    return max(RAPPORT_FLOOR, min(RAPPORT_CEILING, value))

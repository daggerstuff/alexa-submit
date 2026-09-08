from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisclosureRule:
    fact_id: str
    trigger_terms: tuple[str, ...]
    response: str
    emotional_state: str


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    name: str
    trigger_terms: tuple[str, ...]
    rationale: str
    max_score: int = 4


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    version: str
    title: str
    opening: str
    disclosures: tuple[DisclosureRule, ...]
    metrics: tuple[MetricDefinition, ...]
    safety_terms: tuple[str, ...]


CHEST_PAIN_BASIC = ScenarioDefinition(
    scenario_id="chest-pain-basic",
    version="1.1.0",
    title="Adult with acute chest pressure",
    opening="Hello. I have been having pressure in my chest and I am worried.",
    disclosures=(
        DisclosureRule(
            "chest-pressure",
            ("where", "location", "pain", "pressure"),
            "It feels like pressure right in the middle of my chest. It started about 30 minutes ago.",
            "anxious",
        ),
        DisclosureRule(
            "radiation",
            ("radiat", "arm", "jaw", "back"),
            "It seems to move into my left arm, especially when the pressure gets worse.",
            "worried",
        ),
        DisclosureRule(
            "dyspnea",
            ("breath", "shortness", "dyspnea"),
            "I am a little short of breath, but I can still speak in full sentences.",
            "concerned",
        ),
        DisclosureRule(
            "history-medications",
            ("medication", "medicine", "history", "medical", "allerg"),
            "I take a blood-pressure medicine. I have high blood pressure, but no known medication allergies.",
            "calm",
        ),
        DisclosureRule(
            "smoking-history",
            ("smoke", "smoking", "tobacco"),
            "I used to smoke, but I quit around five years ago.",
            "reflective",
        ),
    ),
    metrics=(
        MetricDefinition(
            "rapport",
            "Introduction and consent",
            ("name", "consent", "permission"),
            "Introduces self and establishes permission or rapport.",
        ),
        MetricDefinition(
            "symptoms",
            "Symptom characterization",
            ("where", "when", "started", "pressure", "radiat", "severity", "scale"),
            "Explores onset, location, character, or severity.",
        ),
        MetricDefinition(
            "risk",
            "Associated symptoms and risk",
            ("breath", "history", "medication", "allerg", "smok", "risk"),
            "Checks associated symptoms, history, medications, or risk factors.",
        ),
        MetricDefinition(
            "escalation",
            "Safety escalation",
            ("emergency", "911", "urgent", "help", "ecg", "monitor"),
            "Recognizes the need for urgent escalation in a concerning presentation.",
        ),
        MetricDefinition(
            "closed_loop",
            "Shared next-step confirmation",
            ("understand", "questions", "next step", "plan", "agree"),
            "Checks understanding and confirms the immediate next step.",
        ),
    ),
    safety_terms=(
        "collapse",
        "unresponsive",
        "severe",
        "can't breathe",
        "cannot breathe",
    ),
)

ABDOMINAL_PAIN_BASIC = ScenarioDefinition(
    scenario_id="abdominal-pain-basic",
    version="1.0.0",
    title="Adult with acute abdominal pain",
    opening="Hi. My stomach has been hurting since last night and I cannot sleep.",
    disclosures=(
        DisclosureRule(
            "pain-location",
            ("where", "location", "pain", "hurt", "stomach"),
            "The pain is mostly in the lower right side of my abdomen. It has been aching for about twelve hours.",
            "uncomfortable",
        ),
        DisclosureRule(
            "pain-quality",
            ("describe", "feel", "sharp", "dull", "aching", "type"),
            "It started as a dull ache but has gotten sharper over the last few hours.",
            "worried",
        ),
        DisclosureRule(
            "appetite",
            ("eat", "food", "appetite", "hungry", "nausea", "sick"),
            "I have not eaten since yesterday afternoon. I feel nauseous but have not vomited.",
            "uncomfortable",
        ),
        DisclosureRule(
            "fever",
            ("fever", "temperature", "hot", "chills", "sweat"),
            "I felt a little warm this morning but I do not have a thermometer to check.",
            "concerned",
        ),
        DisclosureRule(
            "bowel",
            ("bowel", "stool", "diarrhea", "constipation", "bathroom", "toilet"),
            "My bowel movements have been normal. No diarrhea or blood.",
            "calm",
        ),
        DisclosureRule(
            "medical-history",
            ("history", "medical", "surgery", "appendix", "medication", "allerg"),
            "I had my appendix removed when I was fifteen. I take no regular medications and have no drug allergies.",
            "calm",
        ),
    ),
    metrics=(
        MetricDefinition(
            "rapport",
            "Introduction and consent",
            ("name", "consent", "permission"),
            "Introduces self and establishes permission or rapport.",
        ),
        MetricDefinition(
            "symptoms",
            "Symptom characterization",
            ("where", "when", "started", "right", "left", "sharp", "dull", "describe"),
            "Explores onset, location, character, or severity.",
        ),
        MetricDefinition(
            "associated",
            "Associated symptoms",
            ("nausea", "vomit", "fever", "appetite", "bowel", "eat", "chills"),
            "Checks for nausea, vomiting, fever, appetite changes, and bowel changes.",
        ),
        MetricDefinition(
            "history",
            "Medical and surgical history",
            ("history", "surgery", "appendix", "medication", "allerg"),
            "Checks prior surgical history, medications, and allergies.",
        ),
        MetricDefinition(
            "escalation",
            "Safety escalation",
            ("emergency", "hospital", "urgent", "help", "surgery", "appendicitis"),
            "Recognizes the possibility of a surgical abdomen and the need for urgent evaluation.",
        ),
        MetricDefinition(
            "closed_loop",
            "Shared next-step confirmation",
            ("understand", "questions", "next step", "plan", "agree"),
            "Checks understanding and confirms the immediate next step.",
        ),
    ),
    safety_terms=(
        "collapse",
        "unresponsive",
        "severe",
        "blood",
        "fainting",
        "cannot move",
    ),
)

DEPRESSION_SCREENING_BASIC = ScenarioDefinition(
    scenario_id="depression-screening-basic",
    version="1.0.0",
    title="Adult with low mood and fatigue",
    opening="I have just been feeling really tired and down lately. I do not know what is wrong with me.",
    disclosures=(
        DisclosureRule(
            "mood-duration",
            ("how long", "when", "started", "long", "weeks", "months"),
            "It has been going on for about two months now. It just keeps getting harder to get through the day.",
            "down",
        ),
        DisclosureRule(
            "mood-quality",
            ("feel", "sad", "down", "depress", "mood", "hopeless"),
            "I feel sad most of the time. Nothing seems to make me happy anymore. Sometimes I wonder if things will ever get better.",
            "despondent",
        ),
        DisclosureRule(
            "sleep",
            ("sleep", "tired", "fatigue", "energy", "exhaust"),
            "I have trouble falling asleep and then I wake up at four in the morning and cannot get back to sleep. I am exhausted all day.",
            "exhausted",
        ),
        DisclosureRule(
            "appetite",
            ("eat", "food", "appetite", "weight", "hungry"),
            "I have lost my appetite. My clothes are looser, maybe ten pounds in the last month.",
            "flat",
        ),
        DisclosureRule(
            "interest",
            ("interest", "enjoy", "hobby", "fun", "activity", "social"),
            "I used to love gardening and seeing my friends, but I just do not have the energy or interest for any of it anymore.",
            "withdrawn",
        ),
        DisclosureRule(
            "substance",
            ("alcohol", "drink", "drug", "substance", "smoke", "caffeine"),
            "I have been having a glass of wine most evenings, maybe two. It helps me relax. I do not use any other substances.",
            "guarded",
        ),
        DisclosureRule(
            "support",
            ("support", "family", "friend", "alone", "live", "help"),
            "I live alone. My daughter calls sometimes, but I do not want to burden her with this.",
            "lonely",
        ),
    ),
    metrics=(
        MetricDefinition(
            "rapport",
            "Introduction and consent",
            ("name", "consent", "permission"),
            "Introduces self and establishes permission or rapport.",
        ),
        MetricDefinition(
            "mood",
            "Mood assessment",
            ("sad", "down", "depress", "mood", "feel", "hopeless", "happy"),
            "Explores the quality, duration, and severity of the mood disturbance.",
        ),
        MetricDefinition(
            "somatic",
            "Somatic symptoms",
            ("sleep", "tired", "fatigue", "energy", "appetite", "weight", "eat"),
            "Screens for sleep disturbance, fatigue, and appetite or weight changes.",
        ),
        MetricDefinition(
            "risk",
            "Risk and safety assessment",
            ("harm", "suicide", "kill", "hurt", "die", "death", "plan", "thought"),
            "Assesses suicidal ideation, intent, plan, and access to means.",
        ),
        MetricDefinition(
            "function",
            "Functional impact and support",
            (
                "interest",
                "enjoy",
                "work",
                "social",
                "support",
                "family",
                "alone",
                "live",
            ),
            "Evaluates impact on daily functioning, interests, and social support.",
        ),
        MetricDefinition(
            "closed_loop",
            "Shared next-step confirmation",
            (
                "understand",
                "questions",
                "next step",
                "plan",
                "agree",
                "help",
                "resource",
            ),
            "Checks understanding and confirms the immediate next step or referral.",
        ),
    ),
    safety_terms=(
        "kill",
        "suicide",
        "end it",
        "hurt myself",
        "not worth",
        "die",
        "death",
        "plan",
    ),
)

SCENARIOS: dict[str, ScenarioDefinition] = {
    CHEST_PAIN_BASIC.scenario_id: CHEST_PAIN_BASIC,
    ABDOMINAL_PAIN_BASIC.scenario_id: ABDOMINAL_PAIN_BASIC,
    DEPRESSION_SCREENING_BASIC.scenario_id: DEPRESSION_SCREENING_BASIC,
}


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario: {scenario_id}") from exc

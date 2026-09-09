"""Predefined observable tests, mapped only to confirmed agent capabilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    query: str
    source_lang: str
    target_lang: str
    confirmed_capability: str
    note: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "confirmed_capability": self.confirmed_capability,
            "note": self.note,
        }


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "basic-advice",
        "Simple agricultural advice",
        "What crops are suitable for this season in Maharashtra?",
        "en",
        "en",
        "The voice agent can answer agricultural queries.",
        "This checks a normal end-to-end response; it does not prove a particular tool was used.",
    ),
    Scenario(
        "weather-hindi",
        "Hindi weather question",
        "नासिक में मौसम कैसा है",
        "hi",
        "hi",
        "The agent exposes weather forecast and forward-geocoding tools and supports Hindi.",
        "A response may use zero, one, or multiple tools; only the final API behavior is observable here.",
    ),
    Scenario(
        "document-search",
        "Document / knowledge search candidate",
        "How can I manage pests in soybean?",
        "en",
        "en",
        "The agent exposes Marqo-backed document and video search tools.",
        "Use this to observe response quality and latency, not to assert that retrieval ran.",
    ),
    Scenario(
        "mandi-prices",
        "Mandi price candidate",
        "What are the mandi prices for soybean near Nashik?",
        "en",
        "en",
        "The agent exposes a mandi-price tool and location tools.",
        "The agent decides whether location details are sufficient and whether to call tools.",
    ),
    Scenario(
        "government-schemes",
        "Government scheme candidate",
        "Which agricultural schemes could a farmer in Maharashtra explore?",
        "en",
        "en",
        "The agent exposes scheme-code and scheme-information tools.",
        "This is an observable scenario, not a guarantee that a scheme tool will run.",
    ),
    Scenario(
        "warehouse",
        "Warehouse information candidate",
        "Find warehouse information near Nashik.",
        "en",
        "en",
        "The agent exposes warehouse data and forward-geocoding tools.",
        "A more precise location may be requested by the API.",
    ),
    Scenario(
        "agri-services",
        "Agricultural services candidate",
        "Where can I find a soil testing laboratory near Nashik?",
        "en",
        "en",
        "The agent exposes agricultural-services and location tools.",
        "This tests the final response only; internal Beckn calls are not visible to this client.",
    ),
    Scenario(
        "staff-contact",
        "Agricultural staff contact candidate",
        "How can I contact agricultural department staff near Nashik?",
        "en",
        "en",
        "The agent exposes an agricultural-staff contact tool.",
        "The answer may ask for more location detail before it can help.",
    ),
    Scenario(
        "terms",
        "Agricultural terminology",
        "What does kharif mean in farming?",
        "en",
        "en",
        "The agent exposes a fuzzy agricultural-terms search tool.",
        "Use this as a controlled terminology test, not proof of a specific tool call.",
    ),
)


def list_scenarios() -> list[dict[str, str]]:
    return [scenario.as_dict() for scenario in SCENARIOS]


def get_scenario(scenario_id: str) -> Scenario:
    for scenario in SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"Unknown scenario: {scenario_id}")

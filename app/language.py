"""Conservative, local-only response-language observations."""

from __future__ import annotations

import re


DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")


def detect_response_language(text: str) -> dict[str, object]:
    """Describe the visible script without claiming Hindi versus Marathi certainty."""
    devanagari_count = len(DEVANAGARI.findall(text))
    latin_count = len(LATIN.findall(text))
    meaningful = devanagari_count + latin_count

    if meaningful == 0:
        return {
            "classification": "unknown",
            "label": "No confidently classifiable script",
            "confidence": "low",
            "devanagari_characters": devanagari_count,
            "latin_characters": latin_count,
        }
    if devanagari_count >= 3 and devanagari_count > latin_count * 1.25:
        return {
            "classification": "devanagari",
            "label": "Devanagari script (could be Hindi or Marathi)",
            "confidence": "medium",
            "devanagari_characters": devanagari_count,
            "latin_characters": latin_count,
        }
    if latin_count >= 3 and latin_count > devanagari_count * 1.25:
        return {
            "classification": "latin",
            "label": "Latin script (likely English, but not guaranteed)",
            "confidence": "medium",
            "devanagari_characters": devanagari_count,
            "latin_characters": latin_count,
        }
    return {
        "classification": "mixed",
        "label": "Mixed or ambiguous script",
        "confidence": "low",
        "devanagari_characters": devanagari_count,
        "latin_characters": latin_count,
    }


def assess_requested_target(text: str, target_lang: str) -> dict[str, object]:
    observation = detect_response_language(text)
    classification = observation["classification"]
    if classification == "unknown":
        result = "unknown"
    elif target_lang == "en" and classification == "latin":
        result = "appears-consistent"
    elif target_lang in {"hi", "mr"} and classification == "devanagari":
        result = "appears-consistent-script-only"
    elif classification == "mixed":
        result = "uncertain"
    else:
        result = "appears-different"
    return {**observation, "requested_target_lang": target_lang, "assessment": result}

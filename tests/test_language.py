from app.language import assess_requested_target, detect_response_language


def test_detects_devanagari_but_does_not_claim_hindi_or_marathi() -> None:
    result = detect_response_language("आज नाशिकमध्ये पाऊस पडेल")
    assert result["classification"] == "devanagari"
    assert "Hindi or Marathi" in result["label"]


def test_english_target_can_be_assessed_as_consistent() -> None:
    result = assess_requested_target("The weather should remain dry.", "en")
    assert result["assessment"] == "appears-consistent"


def test_mixed_response_is_explicitly_uncertain() -> None:
    result = assess_requested_target("आज weather ठीक है", "hi")
    assert result["assessment"] == "uncertain"

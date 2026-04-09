from src.helpers.safety_layer import check_emergency, inject_disclaimer


def test_emergency_detected_for_chest_pain():
    assert check_emergency("I have severe chest pain") is True


def test_emergency_detected_for_stroke():
    assert check_emergency("I think I am having a stroke") is True


def test_no_emergency_for_mild_symptom():
    assert check_emergency("I have a mild headache") is False


def test_disclaimer_injected():
    result = inject_disclaimer("Some medical info")
    assert "does NOT diagnose" in result
    assert "healthcare provider" in result


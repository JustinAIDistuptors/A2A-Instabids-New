from instabids.agents.job_classifier import classify

def test_basic_text():
    res = classify("We want a full kitchen remodel")
    assert res["category"] == "RENOVATION" and res["confidence"] > 0.3

def test_emergency_edge():
    res = classify("leak urgent burst pipe")
    assert res["category"] == "REPAIR"

def test_low_confidence_fallback():
    res = classify("blorb flarble")
    assert res["category"] == "OTHER"
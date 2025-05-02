from instabids.agents.bidcard_agent import create_bid_card

def test_classifier_basic():
    project = {"id": "p1", "description": "Burst pipe leak urgent"}
    card, conf = create_bid_card(project, {})
    assert card["category"] == "repair"
    assert 0.6 <= conf <= 1
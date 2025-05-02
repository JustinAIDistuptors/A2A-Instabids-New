from instabids.agents.bidcard_agent import create_bid_card

def test_confidence_threshold():
    proj = {"id": "p1", "title": "Fix roof", "description": "Need roof repair"}
    card, conf = create_bid_card(proj, {})
    assert card["category"] == "repair"
    assert conf >= 0.6
from instabids.agents.bidcard_agent import create_bid_card

def test_classifier_basic():
    project = {
        "id": "p1", 
        "description": "Burst pipe leak urgent",
        "budget_range": "$1000-$2000",
        "timeline": "ASAP",
        "group_bidding": True
    }
    card, conf = create_bid_card(project, {})
    
    # Check classification
    assert card["category"] == "repair"
    assert 0.6 <= conf <= 1
    
    # Check new fields
    assert card["budget_range"] == "$1000-$2000"
    assert card["timeline"] == "ASAP"
    assert card["group_bidding"] == True

def test_missing_fields_handled():
    # Test with minimal project data
    project = {"id": "p2", "description": "Kitchen renovation"}
    card, conf = create_bid_card(project, {})
    
    # Check classification
    assert card["category"] == "renovation"
    
    # Check that missing fields don't cause errors
    assert card["budget_range"] is None
    assert card["timeline"] is None
    assert card["group_bidding"] is False
"""Tests for the enhanced job classifier module."""
import pytest
from instabids.agents.job_classifier import classify, _score

def test_classify_renovation():
    """Test classification of renovation projects."""
    # Strong renovation signal
    result = classify("I want to remodel my kitchen with new cabinets and countertops")
    assert result["category"] == "RENOVATION"
    assert result["confidence"] > 0.3  # Reasonable confidence

def test_classify_repair():
    """Test classification of repair projects."""
    # Strong repair signal
    result = classify("I have a leak in my roof that needs to be fixed")
    assert result["category"] == "REPAIR"
    assert result["confidence"] > 0.3

def test_classify_installation():
    """Test classification of installation projects."""
    # Strong installation signal
    result = classify("I need to install a new dishwasher in my kitchen")
    assert result["category"] == "INSTALLATION"
    assert result["confidence"] > 0.3

def test_classify_maintenance():
    """Test classification of maintenance projects."""
    # Strong maintenance signal
    result = classify("I need regular lawn mowing service for the summer")
    assert result["category"] == "MAINTENANCE"
    assert result["confidence"] > 0.3

def test_classify_construction():
    """Test classification of construction projects."""
    # Strong construction signal
    result = classify("I want to build a deck in my backyard")
    assert result["category"] == "CONSTRUCTION"
    assert result["confidence"] > 0.3

def test_classify_weak_signal():
    """Test classification with weak signals."""
    # Ambiguous or weak signal should return OTHER with low confidence
    result = classify("I need some help with my home")
    assert result["category"] == "OTHER"
    assert result["confidence"] < 0.25  # Below the confidence threshold

def test_classify_vision_boost():
    """Test boost from vision tags."""
    # Text with weak signal but vision tag should influence result
    result = classify("I need help with my yard", vision_tags=["grass", "lawnmower"])
    assert result["category"] == "MAINTENANCE"
    assert result["confidence"] >= 0.4  # Vision boost increases confidence

def test_classify_mixed_signals():
    """Test classification with mixed signals."""
    # Text with multiple category signals
    result = classify("I need to repair my kitchen cabinets and install a new sink")
    # Should choose the stronger match based on keyword density
    assert result["category"] in ["REPAIR", "INSTALLATION"]
    assert result["confidence"] > 0.2

def test_score_function():
    """Test the internal scoring function directly."""
    cat, score = _score("build a new deck", [])
    assert cat == "CONSTRUCTION"
    assert score > 0
    
    cat, score = _score("mow my lawn weekly", ["grass"])
    assert cat == "MAINTENANCE"
    assert score > 0
    
    # Vision hint boost with weak text signal
    cat, score = _score("help with my home", ["rubble"])
    assert cat == "REPAIR"  # Vision hint should influence when text is weak
    assert score >= 0.4

def test_confidence_rounding():
    """Test that confidence values are properly rounded."""
    result = classify("I need to install a new light fixture")
    # Confidence should be rounded to 3 decimal places
    assert isinstance(result["confidence"], float)
    # Convert to string and check decimal places
    confidence_str = str(result["confidence"])
    decimal_part = confidence_str.split('.')[-1]
    assert len(decimal_part) <= 3
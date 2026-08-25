from app.services.investigator import investigate

def test_abstain_and_provenance_are_mechanical():
    result=investigate("What caused churn?", [{"type":"causal_analysis","estimated_effect":2}], {"status":"ABSTAIN"})
    assert result["intent"]=="causal" and "no recommendation" in result["explanation"] and result["provenance"][0]["id"] in result["explanation"]
    assert "Insufficient evidence" in investigate("show sales", [], {"status":"REVIEW"})["explanation"]

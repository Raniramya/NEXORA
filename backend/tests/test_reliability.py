import numpy as np
from app.services.reliability import ECDSModel, calibration_report, decision_gate, ood_indicator, selective_metrics

def test_calibration_ecds_gate_and_ood():
    p=np.array([.1,.2,.8,.9]*25); y=np.array([0,0,1,1]*25); report=calibration_report(p,y); assert report["brier_score"] < .1
    model=ECDSModel().fit(np.c_[p,1-p],y); score=float(model.predict([[.9,.1]])[0]); assert score>.5
    evidence={"predictive_estimate":1,"predictive_uncertainty":.1,"model_validation_performance":.9,"data_quality":90,"sample_size":100,"provenance_references":["run"]}
    assert decision_gate(None,evidence)["status"]=="UNCALIBRATED"
    assert decision_gate(score,{**evidence,"ood_indicator":ood_indicator([[0],[1]],[10])})["status"]=="ABSTAIN"
    assert selective_metrics(p,y,.5)["coverage"]==.5

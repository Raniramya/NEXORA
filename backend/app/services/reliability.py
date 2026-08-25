from dataclasses import dataclass, asdict
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


def calibration_report(probabilities, labels, bins=10):
    p=np.asarray(probabilities); y=np.asarray(labels); edges=np.linspace(0,1,bins+1); rows=[]; ece=0.0
    for lo,hi in zip(edges[:-1],edges[1:]):
        mask=(p>=lo)&((p<hi) if hi<1 else (p<=hi))
        if mask.any():
            conf=float(p[mask].mean()); acc=float(y[mask].mean()); weight=float(mask.mean()); rows.append({"lower":float(lo),"upper":float(hi),"confidence":conf,"accuracy":acc,"count":int(mask.sum())}); ece+=weight*abs(conf-acc)
    return {"brier_score":float(brier_score_loss(y,p)),"expected_calibration_error":float(ece),"bins":rows}


def ood_indicator(train_features, observation, z_threshold=3.0):
    train=np.asarray(train_features,float); obs=np.asarray(observation,float); z=np.abs((obs-train.mean(0))/np.where(train.std(0)==0,1,train.std(0)))
    return {"is_ood":bool((z>z_threshold).any()),"max_z_score":float(z.max())}


def completeness(record):
    required=["predictive_estimate","predictive_uncertainty","model_validation_performance","data_quality","sample_size","provenance_references"]
    missing=[x for x in required if record.get(x) is None]
    return {"complete":not missing,"missing":missing,"fraction":(len(required)-len(missing))/len(required)}


class ECDSModel:
    def __init__(self): self.model=None
    def fit(self, features, correct): self.model=LogisticRegression(max_iter=1000).fit(features,correct); return self
    def predict(self, features): return None if self.model is None else self.model.predict_proba(features)[:,1]


def decision_gate(ecd_score, evidence, recommend_threshold=.8, review_threshold=.6):
    if ecd_score is None: return {"status":"UNCALIBRATED","reasons":["No empirically trained ECDS model."]}
    if not completeness(evidence)["complete"] or evidence.get("ood_indicator",{}).get("is_ood"): return {"status":"ABSTAIN","reasons":["Incomplete evidence or out-of-distribution input."]}
    return {"status":"RECOMMEND" if ecd_score>=recommend_threshold else "REVIEW" if ecd_score>=review_threshold else "ABSTAIN","reasons":[]}


def selective_metrics(scores, correct, threshold):
    s=np.asarray(scores); y=np.asarray(correct); keep=s>=threshold
    return {"coverage":float(keep.mean()),"abstention_rate":float(1-keep.mean()),"selective_accuracy":float(y[keep].mean()) if keep.any() else None,"selective_risk":float(1-y[keep].mean()) if keep.any() else None}

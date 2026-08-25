import re
from uuid import uuid4

INTENTS={"causal|caused|cause":"causal","counterfactual":"counterfactual","predict|forecast":"predictive","why|diagnos":"diagnostic","recommend|decision":"prescriptive"}

def classify_intent(question):
    q=question.lower()
    return next((v for k,v in INTENTS.items() if re.search(k,q)),"descriptive")

def provenance(evidence):
    return [{"id":f"ev-{uuid4()}","type":item.get("type","calculation"),"payload":item} for item in evidence]

class LLMProvider:
    def explain(self, payload): raise NotImplementedError

class DeterministicProvider(LLMProvider):
    def explain(self,payload):
        status=payload["reliability"]["status"]
        ids=", ".join(x["id"] for x in payload["provenance"])
        if not payload["evidence"]: return "Insufficient evidence. No recommendation was produced."
        if status in {"ABSTAIN","UNCALIBRATED"}: return f"{status}: no recommendation. Evidence references: {ids}."
        return f"Evidence-based {payload['intent']} finding. Review evidence references: {ids}."

def investigate(question,evidence,reliability,provider=None):
    graph=provenance(evidence); payload={"question":question,"intent":classify_intent(question),"evidence":evidence,"uncertainty":[x.get("uncertainty") for x in evidence],"reliability":reliability,"provenance":graph}
    return {**payload,"explanation":(provider or DeterministicProvider()).explain(payload)}

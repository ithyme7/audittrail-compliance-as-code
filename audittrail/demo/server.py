from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

import audittrail
from audittrail import RiskLevel, trace_inference


class PredictRequest(BaseModel):
    features: List[float]


app = FastAPI(title="AuditTrail FastAPI Demo")


audittrail.init(project="fastapi-demo", risk_level=RiskLevel.HIGH, output_dir="./demo_output")


@trace_inference(require_human_review_threshold=0.85)
def model_predict(features: List[float]):
    # Dummy model: returns simple probabilities
    return [0.2, 0.8]


@app.post("/predict")
def predict(req: PredictRequest):
    proba = model_predict(req.features)
    return {"probabilities": proba, "prediction": int(proba[1] > proba[0])}

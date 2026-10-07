from contextlib import asynccontextmanager
import math
import os

from fastapi import FastAPI, HTTPException
from google.cloud import storage
import joblib
import pandas as pd
from pydantic import BaseModel

MODEL_KEY = "artifacts/current/model.joblib"
MODEL_PATH = os.path.expanduser("~/models/model.joblib")
FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def download_model():
    """Download the approved model from GCS before serving requests."""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    client = storage.Client()
    blob = client.bucket(os.environ["ARTIFACT_BUCKET"]).blob(MODEL_KEY)
    blob.download_to_filename(MODEL_PATH)
    print("Model downloaded from cloud storage.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    download_model()
    app.state.model = joblib.load(MODEL_PATH)
    yield


app = FastAPI(lifespan=lifespan)


class ScoreRequest(BaseModel):
    features: list[float]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/score")
def score(req: ScoreRequest):
    if len(req.features) != len(FEATURE_NAMES):
        raise HTTPException(status_code=400, detail="Expected 10 features (adult income)")
    if not all(math.isfinite(value) for value in req.features):
        raise HTTPException(status_code=400, detail="Features must be finite numbers")
    inputs = pd.DataFrame([req.features], columns=FEATURE_NAMES)
    prediction = int(app.state.model.predict(inputs)[0])
    label = "thu_nhap_cao" if prediction == 1 else "thu_nhap_thap"
    return {"prediction": prediction, "label": label}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

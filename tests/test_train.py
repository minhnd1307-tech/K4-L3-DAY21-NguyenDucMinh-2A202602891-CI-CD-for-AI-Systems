import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.train import train

FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def _make_temp_data(tmp_path):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.random((200, len(FEATURE_NAMES))), columns=FEATURE_NAMES)
    df["target"] = rng.integers(0, 2, size=200)
    train_path = tmp_path / "train.csv"
    eval_path = tmp_path / "holdout.csv"
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)
    return str(train_path), str(eval_path)


@pytest.fixture
def training_run(tmp_path, monkeypatch):
    # Keep test models, reports and MLflow history away from CP1 artifacts.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", (tmp_path / "mlruns").as_uri())
    train_path, eval_path = _make_temp_data(tmp_path)
    f1 = train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )
    return f1, eval_path


def test_train_returns_float(training_run):
    f1, _ = training_run
    assert isinstance(f1, float)
    assert 0.0 <= f1 <= 1.0


def test_report_file_created(training_run):
    f1, _ = training_run
    report = json.loads(Path("outputs/report.json").read_text())
    assert report["f1_score"] == f1
    assert 0.0 <= report["accuracy"] <= 1.0
    assert 0.0 <= report["positive_ratio"] <= 1.0
    assert report["best_threshold"] in {i / 20 for i in range(2, 19)}
    assert report["best_threshold_f1"] >= report["f1_at_0_5"] == f1
    detail = Path("outputs/detail.txt").read_text()
    assert all(label in detail for label in ["precision", "recall", "thu_nhap_thap", "thu_nhap_cao"])


def test_model_file_created(training_run):
    _, eval_path = training_run
    model = joblib.load("models/model.joblib")
    df = pd.read_csv(eval_path)
    predictions = model.predict(df.drop(columns=["target"]))
    assert predictions.shape == (40,)
    assert set(predictions) <= {0, 1}

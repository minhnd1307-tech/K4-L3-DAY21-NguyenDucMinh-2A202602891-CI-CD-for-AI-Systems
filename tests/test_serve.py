import json
from pathlib import Path
import shutil
from unittest.mock import Mock

from fastapi.testclient import TestClient
import joblib
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from src import serve


@pytest.fixture
def cloud_model(tmp_path, monkeypatch):
    source = tmp_path / "cloud-model.joblib"
    model = DummyClassifier(strategy="constant", constant=1)
    model.fit(pd.DataFrame([[0] * 10, [1] * 10], columns=serve.FEATURE_NAMES), [0, 1])
    joblib.dump(model, source)
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setattr(serve, "MODEL_PATH", str(tmp_path / "models" / "model.joblib"))
    client = Mock()
    blob = client.bucket.return_value.blob.return_value
    blob.download_to_filename.side_effect = lambda path: shutil.copyfile(source, path)
    monkeypatch.setattr(serve.storage, "Client", lambda: client)
    return client


def test_startup_health_and_prediction(cloud_model):
    with TestClient(serve.app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        response = client.post("/score", json={"features": [0] * 10})
        assert response.status_code == 200
        assert response.json() == {"prediction": 1, "label": "thu_nhap_cao"}
    cloud_model.bucket.assert_called_once_with("test-bucket")
    cloud_model.bucket.return_value.blob.assert_called_once_with(serve.MODEL_KEY)
    assert Path(serve.MODEL_PATH).is_file()


@pytest.mark.parametrize("features", [[], [0] * 9, [0] * 11, [float("nan")] * 10, [float("inf")] * 10])
def test_invalid_features_are_rejected(cloud_model, features):
    with TestClient(serve.app) as client:
        response = client.post("/score", content=json.dumps({"features": features}), headers={"Content-Type": "application/json"})
        assert response.status_code == 400


def test_startup_fails_when_download_fails(cloud_model):
    cloud_model.bucket.return_value.blob.return_value.download_to_filename.side_effect = RuntimeError("Cloud unavailable")
    with pytest.raises(RuntimeError, match="Cloud unavailable"):
        with TestClient(serve.app):
            pass

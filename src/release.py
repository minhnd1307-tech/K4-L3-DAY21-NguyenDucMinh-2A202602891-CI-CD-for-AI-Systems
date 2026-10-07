"""Publish only a model that does not reduce the currently deployed F1."""
import json
import math
import os

from google.api_core.exceptions import NotFound
from google.cloud import storage


def publish_model(bucket, report_path="outputs/report.json", model_path="models/model.joblib"):
    with open(report_path) as file:
        report = json.load(file)
    new_f1 = float(report["f1_score"])
    if not math.isfinite(new_f1) or not 0.65 <= new_f1 <= 1.0:
        raise ValueError("Candidate F1 must be finite and in [0.65, 1.0]")
    current = bucket.blob("artifacts/current/report.json")
    try:
        old_f1 = float(json.loads(current.download_as_text())["f1_score"])
    except NotFound:
        print("First deployment: no previous report.")
    else:
        if not math.isfinite(old_f1) or not 0.0 <= old_f1 <= 1.0:
            raise ValueError("Current model report has invalid F1; deployment blocked")
        print(f"Current F1: {old_f1:.6f}; candidate F1: {new_f1:.6f}")
        if new_f1 < old_f1:
            raise ValueError("F1 regression: deployment cancelled; current model preserved")
    bucket.blob("artifacts/current/model.joblib").upload_from_filename(model_path)
    current.upload_from_filename(report_path)
    print("Approved model and report uploaded.")


if __name__ == "__main__":
    publish_model(storage.Client().bucket(os.environ["ARTIFACT_BUCKET"]))

import json
from unittest.mock import Mock

from google.api_core.exceptions import Forbidden, NotFound
import pytest

from src.release import publish_model


def make_release(tmp_path, old_f1):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({"f1_score": 0.75, "accuracy": 0.87}))
    current, model = Mock(), Mock()
    if old_f1 is None:
        current.download_as_text.side_effect = NotFound("No previous model")
    else:
        current.download_as_text.return_value = json.dumps({"f1_score": old_f1})
    bucket = Mock()
    bucket.blob.side_effect = lambda key: current if key.endswith("report.json") else model
    return bucket, current, model, str(report_path)


@pytest.mark.parametrize("old_f1", [None, 0.70, 0.75])
def test_first_equal_or_better_model_is_published(tmp_path, old_f1):
    bucket, current, model, report_path = make_release(tmp_path, old_f1)
    publish_model(bucket, report_path, "candidate.joblib")
    model.upload_from_filename.assert_called_once_with("candidate.joblib")
    current.upload_from_filename.assert_called_once_with(report_path)


@pytest.mark.parametrize("old_f1", [0.80, float("nan"), float("inf"), 1.1])
def test_regression_or_invalid_current_metrics_preserve_model(tmp_path, old_f1):
    bucket, current, model, report_path = make_release(tmp_path, old_f1)
    with pytest.raises(ValueError):
        publish_model(bucket, report_path, "candidate.joblib")
    model.upload_from_filename.assert_not_called()
    current.upload_from_filename.assert_not_called()


def test_permission_error_is_not_treated_as_first_deployment(tmp_path):
    bucket, current, model, report_path = make_release(tmp_path, None)
    current.download_as_text.side_effect = Forbidden("Access denied")
    with pytest.raises(Forbidden):
        publish_model(bucket, report_path, "candidate.joblib")
    model.upload_from_filename.assert_not_called()
    current.upload_from_filename.assert_not_called()

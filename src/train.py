import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

# Quality gate uses F1 for the positive income class.
F1_THRESHOLD = 0.65


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho GradientBoostingClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia (holdout).

    Tra ve:
        f1 (float): diem F1 cua lop duong (thu nhap > 50K) tren tap holdout.
    """

    # Doc du lieu huan luyen va danh gia
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    # Tach dac trung (X) va nhan (y)
    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    positive_ratio = float(y_train.mean())
    print(f"Positive class ratio: {positive_ratio:.4%} (reference: 24.8%)")
    if round(abs(positive_ratio - 0.248), 12) > 0.05:
        print("WARNING: DATA DRIFT - positive class ratio differs by more than 5 percentage points.")

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    mlflow.set_experiment("adult_income_experiment")

    with mlflow.start_run():

        # Ghi nhan cac sieu tham so
        mlflow.log_params(params)

        # Khoi tao va huan luyen GradientBoostingClassifier
        # Goi y: su dung random_state=42 de dam bao tinh tai tao
        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        # Du doan tren tap holdout va tinh chi so
        # Chu y: f1_score o day tinh cho LOP DUONG (target = 1), khong dung average.
        preds = model.predict(X_eval)
        f1 = float(f1_score(y_eval, preds))
        acc = float(accuracy_score(y_eval, preds))

        probabilities = model.predict_proba(X_eval)[:, 1]
        threshold_scores = [
            (i / 20, float(f1_score(y_eval, probabilities > i / 20, zero_division=0)))
            for i in range(2, 19)
        ]
        best_threshold, best_threshold_f1 = max(
            threshold_scores, key=lambda result: (result[1], -abs(result[0] - 0.5))
        )
        report = {
            "f1_score": f1, "accuracy": acc, "positive_ratio": positive_ratio,
            "f1_at_0_5": f1, "best_threshold": best_threshold,
            "best_threshold_f1": best_threshold_f1,
        }
        # The gate and serving keep the default threshold; the scan is exploratory.
        mlflow.log_metrics(report)
        mlflow.sklearn.log_model(model, "model")

        # In ket qua ra man hinh
        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f}")

        # Luu metrics ra file outputs/report.json
        # File nay duoc doc boi GitHub Actions o Buoc 2
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/report.json", "w") as f:
            json.dump(report, f)
        detail = (
            "Confusion matrix (rows=true, columns=predicted; labels=[0, 1]):\n"
            + str(confusion_matrix(y_eval, preds, labels=[0, 1])) + "\n\n"
            + classification_report(
                y_eval, preds, labels=[0, 1],
                target_names=["thu_nhap_thap", "thu_nhap_cao"], digits=4, zero_division=0,
            )
        )
        with open("outputs/detail.txt", "w") as f:
            f.write(detail)
        print(detail)
        print(f"Best scanned threshold: {best_threshold:.2f}; F1: {best_threshold_f1:.4f}")
        mlflow.log_artifact("outputs/report.json")
        mlflow.log_artifact("outputs/detail.txt")

        # Luu mo hinh ra file models/model.joblib
        # File nay duoc upload len cloud storage o Buoc 2
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.joblib")

    # Tra ve f1
    return f1


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)

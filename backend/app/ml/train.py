"""Train the hybrid ensemble: Random Forest + XGBoost + Gaussian Naive Bayes.

Run:  python -m app.ml.train      (from the backend/ folder)
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from .features import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES
from .generate_data import generate

BASE = Path(__file__).resolve().parents[2]
DATA_PATH = BASE / "data" / "rockfall_dataset.csv"
MODEL_DIR = BASE / "models"
MODEL_PATH = MODEL_DIR / "rockfall_ensemble.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"

ENSEMBLE_WEIGHTS = [0.4, 0.4, 0.2]  # RF, XGB, NB


def build_pipeline() -> Pipeline:
    pre = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])
    rf = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=3,
                                class_weight="balanced", random_state=42, n_jobs=-1)
    xgb = XGBClassifier(n_estimators=350, max_depth=4, learning_rate=0.05, subsample=0.9,
                        colsample_bytree=0.9, eval_metric="logloss", random_state=42)
    nb = GaussianNB()
    ensemble = VotingClassifier([("rf", rf), ("xgb", xgb), ("nb", nb)],
                                voting="soft", weights=ENSEMBLE_WEIGHTS)
    return Pipeline([("pre", pre), ("model", ensemble)])


def _scores(y, proba):
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred), 4),
        "recall": round(recall_score(y, pred), 4),
        "f1": round(f1_score(y, pred), 4),
        "roc_auc": round(roc_auc_score(y, proba), 4),
    }


def train() -> dict:
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
    else:
        df = generate()
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(DATA_PATH, index=False)

    X, y = df[ALL_FEATURES], df["rockfall"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    pipe = build_pipeline()
    pipe.fit(X_tr, y_tr)

    metrics = {"ensemble": _scores(y_te, pipe.predict_proba(X_te)[:, 1])}
    X_te_t = pipe.named_steps["pre"].transform(X_te)
    for name, est in pipe.named_steps["model"].named_estimators_.items():
        metrics[name] = _scores(y_te, est.predict_proba(X_te_t)[:, 1])

    # feature importance from the forest + boosted trees (averaged)
    feat_names = pipe.named_steps["pre"].get_feature_names_out()
    est = pipe.named_steps["model"].named_estimators_
    imp = (est["rf"].feature_importances_ + est["xgb"].feature_importances_) / 2
    importance = sorted(
        ({"feature": f.split("__", 1)[1], "importance": round(float(v), 4)} for f, v in zip(feat_names, imp)),
        key=lambda d: -d["importance"],
    )

    info = {
        "n_samples": int(len(df)),
        "positive_rate": round(float(y.mean()), 4),
        "ensemble_weights": dict(zip(["rf", "xgb", "nb"], ENSEMBLE_WEIGHTS)),
        "metrics": metrics,
        "feature_importance": importance,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(info, indent=2))
    return info


if __name__ == "__main__":
    result = train()
    print(json.dumps(result["metrics"], indent=2))
    print(f"Model saved to {MODEL_PATH}")

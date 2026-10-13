"""Hybrid predictor: ML ensemble probability fused with the Fuzzy AHP score."""
from __future__ import annotations

import json
from functools import lru_cache

import joblib
import pandas as pd

from . import fuzzy_ahp
from .features import ALL_FEATURES, topography_from_slope
from .train import METRICS_PATH, MODEL_PATH, train

ML_WEIGHT = 0.6     # share of the ML ensemble in the final score
FAHP_WEIGHT = 0.4   # share of the expert Fuzzy AHP score


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        train()
    model = joblib.load(MODEL_PATH)
    # single-row inference is faster without the thread-pool overhead
    for est in model.named_steps["model"].estimators_:
        if hasattr(est, "n_jobs"):
            est.n_jobs = 1
    return model


def model_info() -> dict:
    load_model()
    info = json.loads(METRICS_PATH.read_text())
    info["fuzzy_ahp"] = {
        "weights": fuzzy_ahp.WEIGHTS,
        "sub_weights": fuzzy_ahp.SUB_WEIGHTS,
        "consistency_ratio": fuzzy_ahp.consistency_ratio(),
    }
    info["fusion"] = {"ml_weight": ML_WEIGHT, "fahp_weight": FAHP_WEIGHT}
    return info


def risk_level(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MODERATE"
    return "LOW"


def recommendations(level: str, factors: dict) -> list[dict]:
    recs: list[dict] = []
    if level in ("CRITICAL", "HIGH"):
        recs.append({"severity": "critical", "icon": "warning", "title": "Immediate evacuation recommended",
                     "detail": "Suspend all mining operations and implement emergency protocols"})
        recs.append({"severity": "critical", "icon": "sensor", "title": "Install additional monitoring sensors",
                     "detail": "Deploy real-time displacement and vibration sensors"})
    elif level == "MODERATE":
        recs.append({"severity": "warning", "icon": "warning", "title": "Restrict access to affected benches",
                     "detail": "Limit personnel and heavy machinery below the unstable face"})
    if factors["soil_moisture"]["level"] == "High" or factors["pore_pressure"]["level"] == "High":
        recs.append({"severity": "warning", "icon": "water", "title": "Improve slope drainage",
                     "detail": "Clear drains and install horizontal drain holes to reduce pore pressure"})
    if factors["blast_recency"]["level"] != "Low":
        recs.append({"severity": "warning", "icon": "blast", "title": "Review blasting schedule",
                     "detail": "Use controlled / pre-split blasting and reduce charge per delay near the face"})
    if factors["crack_width"]["level"] == "High" or factors["displacement_rate"]["level"] == "High":
        recs.append({"severity": "warning", "icon": "crack", "title": "Inspect tension cracks",
                     "detail": "Map crack extent and check the displacement trend for acceleration"})
    recs.append({"severity": "info", "icon": "chart", "title": "Continuous monitoring recommended",
                 "detail": "Regular data updates will improve prediction accuracy"})
    return recs


def assess(inputs: dict) -> dict:
    """inputs: raw readings (see schemas.AssessmentInput)."""
    x = dict(inputs)
    if "days_since_blast" not in x or x["days_since_blast"] is None:
        x["days_since_blast"] = fuzzy_ahp.days_since(x.get("last_blasting"))
    x["vegetation"] = str(x["vegetation"]).lower()
    x["soil_type"] = str(x["soil_type"]).lower()

    model = load_model()
    ml_prob = float(model.predict_proba(pd.DataFrame([{k: x[k] for k in ALL_FEATURES}]))[0, 1])
    fahp = fuzzy_ahp.fahp_score(x)

    overall = ML_WEIGHT * ml_prob * 100 + FAHP_WEIGHT * fahp["total"]
    # distribute the hybrid score across criteria in proportion to their Fuzzy AHP contribution,
    # so the four component tiles always add up to the overall score
    scale = overall / fahp["total"] if fahp["total"] else 0
    components = {c: round(v["contribution"] * scale, 1) for c, v in fahp["criteria"].items()}
    overall = round(sum(components.values()), 1)
    level = risk_level(overall)
    f = fahp["factors"]

    return {
        "overall_score": overall,
        "risk_level": level,
        "ml_probability": round(ml_prob, 4),
        "fahp_score": fahp["total"],
        "components": components,
        "criteria": fahp["criteria"],
        "risk_factors": [
            {"label": f"Topography: {topography_from_slope(x['slope_angle'])}", "key": "slope_angle",
             "value": x["slope_angle"], "unit": "°", "risk": f["slope_angle"]["risk"], "level": f["slope_angle"]["level"]},
            {"label": f"Vegetation: {x['vegetation']}", "key": "vegetation", "value": x["vegetation"],
             "risk": f["vegetation"]["risk"], "level": f["vegetation"]["level"]},
            {"label": f"Seismic Activity: {x['seismic_activity']:.2f}", "key": "seismic_activity",
             "value": x["seismic_activity"], "risk": f["seismic_activity"]["risk"], "level": f["seismic_activity"]["level"]},
            {"label": f"Crack Width: {x['crack_width']:.1f} mm", "key": "crack_width", "value": x["crack_width"],
             "risk": f["crack_width"]["risk"], "level": f["crack_width"]["level"]},
            {"label": f"Displacement: {x['displacement_rate']:.2f} mm/day", "key": "displacement_rate",
             "value": x["displacement_rate"], "risk": f["displacement_rate"]["risk"], "level": f["displacement_rate"]["level"]},
        ],
        "environment": {
            "annual_rainfall": round(x["annual_rainfall"], 1),
            "soil_moisture": round(x["soil_moisture"], 1),
            "soil_type": x["soil_type"],
            "pore_pressure": round(x["pore_pressure"], 1),
            "last_blasting": x.get("last_blasting"),
            "days_since_blast": round(x["days_since_blast"], 1),
        },
        "recommendations": recommendations(level, f),
        "inputs": x,
    }

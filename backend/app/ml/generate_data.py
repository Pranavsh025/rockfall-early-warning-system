"""Generate a synthetic but physically-motivated rockfall dataset.

Each row is one bench/slope sector observation. The label `rockfall` is drawn
from a latent hazard that mirrors known triggers of open-pit slope failure:
steep faces, wet ground (rainfall, moisture, pore pressure), seismic / blast
vibration, active cracking and accelerating displacement.

Replace this with real monitoring data (slope radar, piezometers, rain gauges,
blast logs) when available — the training script only needs the same columns.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from .features import SOIL_TYPES, VEGETATION_LEVELS

VEG_RISK = {"dense": 0.0, "moderate": 0.35, "sparse": 0.7, "barren": 1.0}
SOIL_RISK = {"rocky": 0.1, "loamy": 0.4, "mixed": 0.55, "sandy": 0.7, "clay": 0.85}


def generate(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    df = pd.DataFrame({
        "slope_angle": rng.uniform(10, 75, n),
        "annual_rainfall": rng.gamma(2.2, 450, n).clip(0, 3500),
        "soil_moisture": rng.beta(2, 4, n) * 60,
        "seismic_activity": rng.gamma(1.6, 0.9, n).clip(0, 6),
        "days_since_blast": rng.exponential(25, n).clip(0, 365),
        "crack_width": rng.gamma(1.3, 4, n).clip(0, 60),
        "displacement_rate": rng.gamma(1.2, 1.5, n).clip(0, 25),
        "pore_pressure": rng.normal(60, 30, n).clip(0, 200),
        "human_impact": rng.uniform(0, 10, n),
        "vegetation": rng.choice(VEGETATION_LEVELS, n, p=[0.15, 0.3, 0.35, 0.2]),
        "soil_type": rng.choice(SOIL_TYPES, n),
    })

    # wetter ground drives moisture and pore pressure up (correlated features)
    df["soil_moisture"] = (df["soil_moisture"] + df["annual_rainfall"] / 120).clip(0, 70)
    df["pore_pressure"] = (df["pore_pressure"] + df["soil_moisture"] * 0.8).clip(0, 220)

    blast_recency = np.exp(-df["days_since_blast"] / 7)  # vibration effect fades in ~a week
    hazard = (
        2.6 * ((df["slope_angle"] - 35) / 25)
        + 1.2 * (df["annual_rainfall"] / 1500)
        + 1.4 * (df["soil_moisture"] / 35)
        + 1.0 * (df["pore_pressure"] / 120)
        + 1.1 * (df["seismic_activity"] / 2.5)
        + 1.0 * blast_recency
        + 1.8 * (df["crack_width"] / 15)
        + 2.2 * (df["displacement_rate"] / 6)
        + 0.25 * (df["human_impact"] / 10)
        + 0.9 * df["vegetation"].map(VEG_RISK)
        + 0.8 * df["soil_type"].map(SOIL_RISK)
        - 6.6
    )
    hazard += rng.normal(0, 0.8, n)  # measurement noise / unobserved geology
    prob = 1 / (1 + np.exp(-hazard))
    df["rockfall"] = (rng.uniform(0, 1, n) < prob).astype(int)
    return df.round(3)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "data" / "rockfall_dataset.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    data.to_csv(out, index=False)
    print(f"Saved {len(data)} rows to {out} (positive rate {data.rockfall.mean():.2%})")

"""Fuzzy AHP (Buckley geometric-mean method) + fuzzy membership risk scoring.

1. Criteria weights come from a pairwise comparison matrix of triangular fuzzy
   numbers (l, m, u), aggregated with Buckley's geometric mean and defuzzified
   with the centroid method.
2. Every raw measurement is fuzzified into Low / Moderate / High membership
   grades and defuzzified to a 0-1 risk value — this is what makes the score
   interpretable ("seismic: moderate", "soil moisture: high").
"""
from __future__ import annotations

import math
from datetime import date, datetime

CRITERIA = ["geological", "environmental", "seismic", "human_impact"]

# Triangular fuzzy pairwise comparisons: row criterion vs column criterion.
# Expert judgement for open-pit slopes: environmental (water) is the dominant
# trigger, geology is the predisposing factor, then seismic/blasting, then human.
_T = {
    "eq": (1, 1, 1),
    "slight": (1, 1.5, 2),
    "moderate": (1, 2, 3),
    "strong": (2, 3, 4),
    "vstrong": (3, 4, 5),
}


def _inv(t):
    l, m, u = t
    return (1 / u, 1 / m, 1 / l)


_PAIRS = {
    ("environmental", "geological"): _T["slight"],
    ("environmental", "seismic"): _T["moderate"],
    ("environmental", "human_impact"): _T["vstrong"],
    ("geological", "seismic"): _T["slight"],
    ("geological", "human_impact"): _T["strong"],
    ("seismic", "human_impact"): _T["moderate"],
}


def pairwise_matrix():
    n = len(CRITERIA)
    M = [[_T["eq"]] * n for _ in range(n)]
    for i, a in enumerate(CRITERIA):
        for j, b in enumerate(CRITERIA):
            if (a, b) in _PAIRS:
                M[i][j] = _PAIRS[(a, b)]
                M[j][i] = _inv(_PAIRS[(a, b)])
    return M


def fuzzy_ahp_weights() -> dict[str, float]:
    M = pairwise_matrix()
    n = len(M)
    # Buckley: fuzzy geometric mean of each row
    r = [tuple(math.prod(M[i][j][k] for j in range(n)) ** (1 / n) for k in range(3)) for i in range(n)]
    total = [sum(ri[k] for ri in r) for k in range(3)]
    # fuzzy weight w_i = r_i ⊗ (Σr)^-1  -> (l/Σu, m/Σm, u/Σl)
    fuzzy_w = [(ri[0] / total[2], ri[1] / total[1], ri[2] / total[0]) for ri in r]
    crisp = [sum(w) / 3 for w in fuzzy_w]  # centroid defuzzification
    s = sum(crisp)
    return {c: round(w / s, 4) for c, w in zip(CRITERIA, crisp)}


def consistency_ratio() -> float:
    """Saaty CR computed on the defuzzified (middle) matrix."""
    M = pairwise_matrix()
    n = len(M)
    A = [[M[i][j][1] for j in range(n)] for i in range(n)]
    gm = [math.prod(row) ** (1 / n) for row in A]
    w = [g / sum(gm) for g in gm]
    lam = sum(sum(A[i][j] * w[j] for j in range(n)) / w[i] for i in range(n)) / n
    ci = (lam - n) / (n - 1)
    ri = {3: 0.58, 4: 0.90, 5: 1.12}[n]
    return round(ci / ri, 4)


WEIGHTS = fuzzy_ahp_weights()

# local (sub-criterion) weights inside each criterion
SUB_WEIGHTS = {
    "geological": {"slope_angle": 0.35, "displacement_rate": 0.30, "crack_width": 0.25, "soil_type": 0.10},
    "environmental": {"soil_moisture": 0.30, "annual_rainfall": 0.30, "pore_pressure": 0.25, "vegetation": 0.15},
    "seismic": {"seismic_activity": 0.6, "blast_recency": 0.4},
    "human_impact": {"human_impact": 1.0},
}

# (low_end, mid, high_start): below low_end fully Low, above high_start fully High
_BREAKS = {
    "slope_angle": (25, 42, 60),
    "displacement_rate": (0.5, 3, 8),
    "crack_width": (2, 8, 20),
    "soil_moisture": (12, 25, 40),
    "annual_rainfall": (500, 1200, 2200),
    "pore_pressure": (40, 90, 150),
    "seismic_activity": (0.5, 2.0, 3.5),
    "blast_recency": (0.1, 0.4, 0.8),
    "human_impact": (1, 4, 8),
}
_CATEGORY_RISK = {
    "vegetation": {"dense": 0.05, "moderate": 0.4, "sparse": 0.6, "barren": 0.95},
    "soil_type": {"rocky": 0.1, "loamy": 0.4, "mixed": 0.5, "sandy": 0.7, "clay": 0.9},
}


def memberships(value: float, breaks) -> dict[str, float]:
    a, b, c = breaks
    low = 1.0 if value <= a else max(0.0, (b - value) / (b - a)) if value < b else 0.0
    high = 1.0 if value >= c else max(0.0, (value - b) / (c - b)) if value > b else 0.0
    if value <= a or value >= c:
        mid = 0.0
    elif value <= b:
        mid = (value - a) / (b - a)
    else:
        mid = (c - value) / (c - b)
    return {"low": round(low, 3), "moderate": round(mid, 3), "high": round(high, 3)}


def defuzzify(mu: dict[str, float]) -> float:
    s = sum(mu.values()) or 1.0
    return (0.1 * mu["low"] + 0.5 * mu["moderate"] + 0.95 * mu["high"]) / s


def level_from_risk(r: float) -> str:
    return "Low" if r < 0.35 else "Moderate" if r < 0.65 else "High"


def blast_recency(days: float) -> float:
    return math.exp(-days / 7)


def days_since(last_blasting: str | None, fallback: float = 30.0) -> float:
    if not last_blasting:
        return fallback
    try:
        d = datetime.fromisoformat(str(last_blasting)).date()
    except ValueError:
        return fallback
    return float(min(max((date.today() - d).days, 0), 365))


def factor_risks(x: dict) -> dict[str, dict]:
    """Per-sub-criterion fuzzy risk (0-1) with membership grades."""
    out = {}
    values = dict(x)
    values["blast_recency"] = blast_recency(x["days_since_blast"])
    for name, br in _BREAKS.items():
        mu = memberships(float(values[name]), br)
        r = defuzzify(mu)
        out[name] = {"value": float(values[name]), "membership": mu, "risk": round(r, 4), "level": level_from_risk(r)}
    for name, table in _CATEGORY_RISK.items():
        r = table.get(str(x[name]).lower(), 0.5)
        out[name] = {"value": x[name], "membership": None, "risk": r, "level": level_from_risk(r)}
    return out


def fahp_score(x: dict) -> dict:
    """Return criterion risks (0-1), weighted contributions and total (0-100)."""
    fr = factor_risks(x)
    criteria = {}
    total = 0.0
    for c, subs in SUB_WEIGHTS.items():
        risk = sum(fr[s]["risk"] * w for s, w in subs.items())
        contrib = WEIGHTS[c] * risk * 100
        total += contrib
        criteria[c] = {"weight": WEIGHTS[c], "risk": round(risk, 4), "contribution": round(contrib, 2)}
    return {"total": round(total, 2), "criteria": criteria, "factors": fr}


if __name__ == "__main__":
    print("Fuzzy AHP weights:", WEIGHTS)
    print("Consistency ratio:", consistency_ratio())

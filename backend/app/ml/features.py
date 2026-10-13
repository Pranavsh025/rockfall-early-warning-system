"""Feature definitions shared by data generation, training and inference."""

NUMERIC_FEATURES = [
    "slope_angle",          # degrees (bench/face slope)
    "annual_rainfall",      # mm
    "soil_moisture",        # %
    "seismic_activity",     # local magnitude / vibration index (0-6)
    "days_since_blast",     # days since last blasting (capped at 365)
    "crack_width",          # mm (tension-crack gauge)
    "displacement_rate",    # mm/day (slope radar / prism)
    "pore_pressure",        # kPa (piezometer)
    "human_impact",         # 0-10 index (workers, machinery, haul traffic in zone)
]

CATEGORICAL_FEATURES = ["vegetation", "soil_type"]

VEGETATION_LEVELS = ["dense", "moderate", "sparse", "barren"]
SOIL_TYPES = ["rocky", "loamy", "mixed", "sandy", "clay"]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def topography_from_slope(slope: float) -> str:
    if slope < 15:
        return "flat"
    if slope < 30:
        return "gentle"
    if slope < 45:
        return "moderate"
    if slope < 60:
        return "steep"
    return "very steep"

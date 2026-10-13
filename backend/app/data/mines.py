"""Monitored open-pit mines (Indian sites) with baseline sensor readings.

Coordinates are approximate pit locations. The `zones` list gives each mine a
few monitored slope sectors that are drawn on the map.
"""

MINES = [
    {
        "id": "jharia", "name": "Jharia Coalfield", "location": "Dhanbad", "state": "Jharkhand",
        "mineral": "Coal", "lat": 23.7465, "lng": 86.4120,
        "baseline": {"slope_angle": 44, "vegetation": "sparse", "seismic_activity": 1.64, "annual_rainfall": 130,
                     "soil_moisture": 22.4, "soil_type": "mixed", "last_blasting": None,
                     "crack_width": 28.0, "displacement_rate": 12.0, "pore_pressure": 150, "human_impact": 0.0},
    },
    {
        "id": "gevra", "name": "Gevra Opencast Mine", "location": "Korba", "state": "Chhattisgarh",
        "mineral": "Coal", "lat": 22.3350, "lng": 82.5960,
        "baseline": {"slope_angle": 38, "vegetation": "moderate", "seismic_activity": 1.1, "annual_rainfall": 1450,
                     "soil_moisture": 27.0, "soil_type": "loamy", "last_blasting": None,
                     "crack_width": 6.0, "displacement_rate": 1.8, "pore_pressure": 70, "human_impact": 6.5},
    },
    {
        "id": "malanjkhand", "name": "Malanjkhand Copper Project", "location": "Balaghat", "state": "Madhya Pradesh",
        "mineral": "Copper", "lat": 22.0130, "lng": 80.7010,
        "baseline": {"slope_angle": 52, "vegetation": "barren", "seismic_activity": 2.3, "annual_rainfall": 1550,
                     "soil_moisture": 31.0, "soil_type": "rocky", "last_blasting": None,
                     "crack_width": 11.0, "displacement_rate": 4.2, "pore_pressure": 110, "human_impact": 5.0},
    },
    {
        "id": "rampura", "name": "Rampura Agucha Mine", "location": "Bhilwara", "state": "Rajasthan",
        "mineral": "Zinc-Lead", "lat": 25.8330, "lng": 74.7330,
        "baseline": {"slope_angle": 48, "vegetation": "barren", "seismic_activity": 0.9, "annual_rainfall": 600,
                     "soil_moisture": 9.5, "soil_type": "sandy", "last_blasting": None,
                     "crack_width": 4.5, "displacement_rate": 1.2, "pore_pressure": 35, "human_impact": 4.0},
    },
    {
        "id": "bailadila", "name": "Bailadila Iron Ore Mine", "location": "Dantewada", "state": "Chhattisgarh",
        "mineral": "Iron Ore", "lat": 18.6600, "lng": 81.2100,
        "baseline": {"slope_angle": 58, "vegetation": "moderate", "seismic_activity": 1.4, "annual_rainfall": 1700,
                     "soil_moisture": 34.0, "soil_type": "clay", "last_blasting": None,
                     "crack_width": 9.0, "displacement_rate": 3.1, "pore_pressure": 125, "human_impact": 5.5},
    },
    {
        "id": "neyveli", "name": "Neyveli Lignite Mine II", "location": "Cuddalore", "state": "Tamil Nadu",
        "mineral": "Lignite", "lat": 11.5430, "lng": 79.4830,
        "baseline": {"slope_angle": 30, "vegetation": "sparse", "seismic_activity": 0.4, "annual_rainfall": 1250,
                     "soil_moisture": 29.0, "soil_type": "sandy", "last_blasting": None,
                     "crack_width": 2.5, "displacement_rate": 0.8, "pore_pressure": 85, "human_impact": 7.0},
    },
    {
        "id": "talcher", "name": "Talcher Coalfield", "location": "Angul", "state": "Odisha",
        "mineral": "Coal", "lat": 20.9500, "lng": 85.2330,
        "baseline": {"slope_angle": 36, "vegetation": "sparse", "seismic_activity": 0.8, "annual_rainfall": 1420,
                     "soil_moisture": 24.0, "soil_type": "mixed", "last_blasting": None,
                     "crack_width": 5.0, "displacement_rate": 1.5, "pore_pressure": 65, "human_impact": 6.0},
    },
    {
        "id": "sukinda", "name": "Sukinda Chromite Valley", "location": "Jajpur", "state": "Odisha",
        "mineral": "Chromite", "lat": 21.0000, "lng": 85.7700,
        "baseline": {"slope_angle": 47, "vegetation": "barren", "seismic_activity": 1.2, "annual_rainfall": 1550,
                     "soil_moisture": 30.0, "soil_type": "clay", "last_blasting": None,
                     "crack_width": 8.0, "displacement_rate": 2.6, "pore_pressure": 105, "human_impact": 4.5},
    },
]

# Recent blasts are relative to "today" so the demo always looks live
_BLAST_DAYS_AGO = {"jharia": 1, "gevra": 2, "malanjkhand": 1, "rampura": 12, "bailadila": 4, "neyveli": 30, "talcher": 6, "sukinda": 9}

# Long-term monthly rainfall normals (mm) used to draw rainfall trends — monsoon-shaped
MONTHLY_NORMALS = {
    "jharia": [15, 20, 25, 30, 60, 220, 330, 320, 250, 80, 10, 5],
    "gevra": [12, 15, 12, 10, 18, 210, 420, 410, 230, 50, 8, 4],
    "malanjkhand": [18, 20, 15, 8, 15, 220, 460, 440, 240, 45, 12, 6],
    "rampura": [5, 4, 3, 3, 10, 60, 210, 200, 80, 10, 3, 2],
    "bailadila": [8, 10, 15, 30, 60, 250, 420, 430, 280, 120, 20, 5],
    "neyveli": [30, 15, 10, 25, 50, 50, 70, 110, 120, 240, 320, 190],
    "talcher": [10, 20, 20, 25, 60, 220, 360, 380, 240, 90, 20, 5],
    "sukinda": [12, 20, 25, 30, 70, 230, 330, 350, 260, 140, 30, 8],
}


def zones_for(mine: dict) -> list[dict]:
    """Four slope sectors (N/E/S/W walls) around the pit centre."""
    d = 0.006
    return [
        {"id": f"{mine['id']}-n", "name": "North Wall", "lat": mine["lat"] + d, "lng": mine["lng"], "offset": 0.08},
        {"id": f"{mine['id']}-e", "name": "East Wall", "lat": mine["lat"], "lng": mine["lng"] + d, "offset": -0.05},
        {"id": f"{mine['id']}-s", "name": "South Wall", "lat": mine["lat"] - d, "lng": mine["lng"], "offset": 0.02},
        {"id": f"{mine['id']}-w", "name": "West Wall", "lat": mine["lat"], "lng": mine["lng"] - d, "offset": -0.10},
    ]

# Rockfall Prediction & Early Warning System for Open-Pit Mines

An end-to-end Agentic AI system that predicts potential rockfalls before they happen.
Winner — Agentic AI Hackathon 2025 (Ulster University).

- **Hybrid ML model** — Random Forest + XGBoost + Naïve Bayes (soft-voting ensemble) fused with **Fuzzy AHP** for clear, interpretable risk levels
- **FastAPI backend** — real-time predictions, PDF reports, and an autonomous **monitoring agent** that pushes live alerts over WebSocket
- **React + Mapbox dashboard** — mine risk cards, map of mine zones, rainfall trends and live risk alerts

```
rockfall-system/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI routes + WebSocket
│   │   ├── agent.py           perceive → reason → act monitoring agent
│   │   ├── report.py          PDF report (ReportLab)
│   │   ├── schemas.py         request models
│   │   ├── data/mines.py      monitored mines, baselines, rainfall normals
│   │   └── ml/
│   │       ├── features.py
│   │       ├── generate_data.py   synthetic training data
│   │       ├── train.py           RF + XGBoost + NB ensemble
│   │       ├── fuzzy_ahp.py       Buckley Fuzzy AHP + fuzzy membership scoring
│   │       └── predictor.py       hybrid fusion + recommendations
│   ├── data/                  rockfall_dataset.csv
│   ├── models/                rockfall_ensemble.joblib, metrics.json
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   ├── hooks/useLiveFeed.js
    │   └── components/  AssessmentView, RiskCard, MonitorView, MapCanvas, NewAssessmentModal
    └── package.json
```

## Run it

Needs **Python 3.10+** and **Node 18+**.

**1. Backend** (terminal 1)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate      macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python -m app.ml.train            # optional — the API trains automatically if no model exists
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

**2. Frontend** (terminal 2)

```bash
cd frontend
npm install
cp .env.example .env              # optional: add VITE_MAPBOX_TOKEN
npm run dev
```

Open http://localhost:5173

Without a Mapbox token the map uses free OpenFreeMap tiles through MapLibre (same API). Add `VITE_MAPBOX_TOKEN` to `.env` to use Mapbox.

## How the score works

1. **ML ensemble** — `P(rockfall)` from a soft-voting ensemble (weights RF 0.4, XGBoost 0.4, NB 0.2) over slope angle, rainfall, soil moisture, pore pressure, seismic activity, days since blasting, crack width, displacement rate, human activity, vegetation and soil type.
2. **Fuzzy AHP** — criteria weights from a triangular-fuzzy pairwise comparison matrix (Buckley geometric mean, centroid defuzzification, CR ≈ 0.001):

   | Criterion | Weight |
   |---|---|
   | Environmental (rain, moisture, pore pressure, vegetation) | 0.398 |
   | Geological (slope, displacement, cracks, soil type) | 0.287 |
   | Seismic (seismic magnitude, blast recency) | 0.210 |
   | Human impact | 0.105 |

   Each reading is fuzzified into Low / Moderate / High membership grades, which gives the factor labels on the dashboard.
3. **Fusion** — `overall = 0.6 × ML × 100 + 0.4 × FuzzyAHP`. The overall score is split across the four criteria in proportion to their Fuzzy AHP contribution, so the four tiles add up to the overall score.
4. **Levels** — LOW < 35 ≤ MODERATE < 60 ≤ HIGH < 85 ≤ CRITICAL.

Test-set results on the bundled dataset (`models/metrics.json`): ensemble ROC-AUC 0.871 / accuracy 0.794, vs RF 0.865, XGBoost 0.868, NB 0.849.

## The monitoring agent

`app/agent.py` runs every 8 s for each mine:

- **Perceive** — reads the latest sensor values (currently a realistic simulated stream: rain events, blasts, displacement drift)
- **Reason** — runs the hybrid model and compares with the previous state
- **Act** — raises alerts on escalation, de-escalation or a rapid rise (with a 1-minute cooldown per mine), and pushes them to every dashboard via `ws://…/ws/alerts`

To connect real sensors, replace `MonitoringAgent._simulate_readings` with your feed (slope radar, piezometers, rain gauges, blast logs).

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service + agent status |
| GET | `/api/mines` | All mines with live scores and zone scores |
| GET | `/api/mines/{id}/assessment` | Full assessment + score history |
| GET | `/api/mines/{id}/rainfall` | Last 12 months rainfall vs normal |
| GET | `/api/mines/{id}/report` | PDF report |
| POST | `/api/predict` | Assess custom readings |
| POST | `/api/report` | PDF report for custom readings |
| GET | `/api/alerts` | Recent alerts |
| GET | `/api/model/info` | Metrics, feature importance, AHP weights |
| WS | `/ws/alerts` | Live ticks + alerts |

## Note on data

The training data in `backend/data/` is synthetic, generated from known rockfall triggers (`app/ml/generate_data.py`). Mine coordinates are approximate. Retrain with real monitoring data by replacing the CSV (same columns) and running `python -m app.ml.train`. The output is decision support; operational decisions need a qualified geotechnical engineer.

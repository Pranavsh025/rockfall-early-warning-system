"""Agentic monitoring loop.

The agent runs a perceive → reason → act cycle for every monitored mine:
  * perceive: pull the latest sensor readings (simulated stream here — swap
    `_simulate_readings` for your real IoT / SCADA feed)
  * reason:   run the hybrid ML + Fuzzy AHP assessment and compare it with the
              previous state (escalation, threshold crossing, fast rise)
  * act:      raise alerts with recommended actions and push them to every
              connected dashboard over WebSocket
"""
from __future__ import annotations

import asyncio
import random
import uuid
from collections import deque
from datetime import date, datetime, timedelta, timezone

from fastapi import WebSocket

from .data.mines import _BLAST_DAYS_AGO, MINES, zones_for
from .ml.predictor import assess

LEVEL_RANK = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
TICK_SECONDS = 8
ALERT_COOLDOWN_TICKS = 8  # ~1 minute between alerts for the same mine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MonitoringAgent:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.readings: dict[str, dict] = {}
        self.assessments: dict[str, dict] = {}
        self.history: dict[str, deque] = {}
        self.alerts: deque = deque(maxlen=200)
        self.clients: set[WebSocket] = set()
        self.running = False
        self.ticks = 0
        self.last_alert_tick: dict[str, int] = {}
        for m in MINES:
            r = dict(m["baseline"])
            if r["last_blasting"] is None:
                r["last_blasting"] = (date.today() - timedelta(days=_BLAST_DAYS_AGO.get(m["id"], 10))).isoformat()
            self.readings[m["id"]] = r
            self.history[m["id"]] = deque(maxlen=60)
            self._evaluate(m, initial=True)

    # ---------------------------------------------------------------- perceive
    def _simulate_readings(self, mine: dict) -> None:
        r, b, rng = self.readings[mine["id"]], mine["baseline"], self.rng

        def revert(key, strength=0.15, noise=0.0, lo=0.0, hi=None):
            v = r[key] + (b[key] - r[key]) * strength + rng.gauss(0, noise)
            r[key] = round(min(max(v, lo), hi) if hi is not None else max(v, lo), 3)

        storm = rng.random() < 0.025
        if storm:  # a rain event: rainfall, moisture and pore pressure jump
            mm = rng.uniform(10, 45)
            r["annual_rainfall"] = round(r["annual_rainfall"] + mm, 1)
            r["soil_moisture"] = round(min(r["soil_moisture"] + mm / 6, 70), 2)
            r["pore_pressure"] = round(r["pore_pressure"] + mm / 2, 1)
        revert("soil_moisture", 0.12, 0.3, 0, 80)
        revert("pore_pressure", 0.12, 1.5, 0, 300)
        revert("annual_rainfall", 0.08, 0.0, 0)
        revert("seismic_activity", 0.3, 0.12, 0, 7)
        revert("displacement_rate", 0.2, 0.15 + r["soil_moisture"] / 400, 0, 60)
        revert("crack_width", 0.05, 0.15, 0, 150)
        revert("human_impact", 0.2, 0.3, 0, 10)
        if rng.random() < 0.004:  # production blast
            r["last_blasting"] = date.today().isoformat()
            r["seismic_activity"] = round(r["seismic_activity"] + rng.uniform(0.5, 1.5), 2)

    # ------------------------------------------------------------------ reason
    def _evaluate(self, mine: dict, initial: bool = False) -> dict | None:
        prev = self.assessments.get(mine["id"])
        a = assess(self.readings[mine["id"]])
        a["mine"] = {k: mine[k] for k in ("id", "name", "location", "state", "mineral", "lat", "lng")}
        a["timestamp"] = _now()
        a["zones"] = [
            {**z, "score": round(min(max(a["overall_score"] * (1 + z["offset"]), 0), 100), 1)} for z in zones_for(mine)
        ]
        self.assessments[mine["id"]] = a
        self.history[mine["id"]].append({"t": a["timestamp"], "score": a["overall_score"]})
        if initial or prev is None:
            if a["risk_level"] in ("HIGH", "CRITICAL"):
                return self._alert(mine, a, f"{a['risk_level'].title()} rockfall risk detected at startup")
            return None

        old, new = LEVEL_RANK[prev["risk_level"]], LEVEL_RANK[a["risk_level"]]
        # cooldown: avoid alert spam when a score hovers around a threshold
        cooling = self.ticks - self.last_alert_tick.get(mine["id"], -999) < ALERT_COOLDOWN_TICKS
        if cooling and not (a["risk_level"] == "CRITICAL" and new > old):
            return None
        if new > old:
            return self._alert(mine, a, f"Risk escalated {prev['risk_level']} → {a['risk_level']}")
        if new < old:
            return self._alert(mine, a, f"Risk eased {prev['risk_level']} → {a['risk_level']}", severity="info")
        if a["overall_score"] - prev["overall_score"] >= 8:
            return self._alert(mine, a, f"Rapid risk increase (+{a['overall_score'] - prev['overall_score']:.1f} pts)")
        return None

    # --------------------------------------------------------------------- act
    def _alert(self, mine: dict, a: dict, message: str, severity: str | None = None) -> dict:
        sev = severity or {"CRITICAL": "critical", "HIGH": "critical", "MODERATE": "warning"}.get(a["risk_level"], "info")
        top = max(a["criteria"].items(), key=lambda kv: kv[1]["contribution"])[0]
        alert = {
            "id": uuid.uuid4().hex[:10],
            "timestamp": a["timestamp"],
            "mine_id": mine["id"],
            "mine_name": mine["name"],
            "severity": sev,
            "risk_level": a["risk_level"],
            "score": a["overall_score"],
            "message": message,
            "driver": top.replace("_", " "),
            "action": a["recommendations"][0]["title"],
        }
        self.alerts.appendleft(alert)
        self.last_alert_tick[mine["id"]] = self.ticks
        return alert

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def summary(self) -> list[dict]:
        return [
            {**a["mine"], "overall_score": a["overall_score"], "risk_level": a["risk_level"], "zones": a["zones"],
             "timestamp": a["timestamp"]}
            for a in self.assessments.values()
        ]

    async def tick(self) -> None:
        new_alerts = []
        for m in MINES:
            self._simulate_readings(m)
            alert = self._evaluate(m)
            if alert:
                new_alerts.append(alert)
        self.ticks += 1
        await self.broadcast({"type": "tick", "timestamp": _now(), "mines": self.summary()})
        for al in new_alerts:
            await self.broadcast({"type": "alert", "alert": al})

    async def run(self) -> None:
        self.running = True
        while self.running:
            await asyncio.sleep(TICK_SECONDS)
            try:
                await self.tick()
            except Exception as exc:  # keep the agent alive
                print("agent tick failed:", exc)


agent = MonitoringAgent(seed=7)

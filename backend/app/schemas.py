from typing import Literal, Optional

from pydantic import BaseModel, Field


class AssessmentInput(BaseModel):
    """Raw readings for one slope sector. Defaults are a 'typical' sector."""
    mine_name: str = Field("Custom Site", description="Display name for the report")
    location: str = Field("—")
    slope_angle: float = Field(40, ge=0, le=90, description="Slope / face angle in degrees")
    vegetation: Literal["dense", "moderate", "sparse", "barren"] = "sparse"
    seismic_activity: float = Field(1.0, ge=0, le=9, description="Seismic / vibration magnitude")
    annual_rainfall: float = Field(1200, ge=0, le=6000, description="mm")
    soil_moisture: float = Field(25, ge=0, le=100, description="%")
    soil_type: Literal["rocky", "loamy", "mixed", "sandy", "clay"] = "mixed"
    last_blasting: Optional[str] = Field(None, description="ISO date of last blast, e.g. 2026-10-10")
    days_since_blast: Optional[float] = Field(None, ge=0, le=365)
    crack_width: float = Field(5, ge=0, le=200, description="mm")
    displacement_rate: float = Field(1.5, ge=0, le=100, description="mm/day")
    pore_pressure: float = Field(70, ge=0, le=500, description="kPa")
    human_impact: float = Field(3, ge=0, le=10, description="0-10 activity index")

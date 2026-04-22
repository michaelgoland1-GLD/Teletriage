from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class CreatePatientRequest(BaseModel):
    source: str = "patient_web"
    name: str
    age: int = 0
    sex: str = "Tidak disebutkan"
    pregnancy: bool = False
    chief_complaint: str = ""
    symptoms: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    vitals: Dict[str, Any] = Field(default_factory=dict)
    photo_meta: Dict[str, Any] = Field(default_factory=dict)
    image_path: Optional[str] = None
    location_text: str = ""
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_accuracy: Optional[float] = None
    emergency_phone: str = ""
    tracking_token: Optional[str] = None
    # Additional data for enhanced triage
    additional_data: Dict[str, Any] = Field(default_factory=dict)

class ReviewRequest(BaseModel):
    status: str
    notes: str = ""
    reviewed_by: str = ""
    video_recommended: Optional[bool] = None
    video_requested: Optional[bool] = None
    video_room_id: Optional[str] = None
    video_status: Optional[str] = None
    video_requested_at: Optional[str] = None
    video_joined_at: Optional[str] = None

class VideoStateRequest(BaseModel):
    video_recommended: Optional[bool] = None
    video_requested: Optional[bool] = None
    video_room_id: Optional[str] = None
    video_status: Optional[str] = None
    video_requested_at: Optional[str] = None
    video_joined_at: Optional[str] = None

class GPSUpdateRequest(BaseModel):
    patient_id: str
    tracking_token: str
    lat: float
    lon: float
    accuracy: Optional[float] = None

class UserCreateRequest(BaseModel):
    username: str
    display_name: str
    password: str
    role: str = "admin"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

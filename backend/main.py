from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.db import (
    init_db, create_patient, list_patients, get_patient, update_patient_fields,
    update_gps, dashboard_summary, list_users, get_user, create_user, record_status_history, delete_patient
)
from backend.schemas import (
    LoginRequest, CreatePatientRequest, ReviewRequest, VideoStateRequest, GPSUpdateRequest, UserCreateRequest, TokenResponse
)
from backend.security import verify_password, hash_password, create_token, verify_token
from backend.triage import triage_engine
from realtime.websocket import manager
from config.settings import APP_TITLE, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD, VIDEO_CALL_PREFIX

app = FastAPI(title=APP_TITLE, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def make_video_room_id(patient_id: str) -> str:
    patient_id = str(patient_id or "").strip()
    return f"{VIDEO_CALL_PREFIX}_{patient_id}" if patient_id else ""


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "teletriage-local-backend"}


@app.get("/summary")
def summary() -> Dict[str, Any]:
    return dashboard_summary()


@app.get("/users")
def users() -> List[Dict[str, Any]]:
    return list_users()


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> Dict[str, Any]:
    user = get_user(payload.username)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Username atau password salah.")
    token = create_token({"sub": user["username"], "role": user["role"]}, expires_in_seconds=12 * 3600)
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/auth/me")
def me(token: str = Query(...)) -> Dict[str, Any]:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid.")
    user = get_user(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return user


@app.post("/auth/users")
def add_user(payload: UserCreateRequest, token: str = Query(...)) -> Dict[str, Any]:
    auth = verify_token(token)
    if not auth or auth.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak.")
    if get_user(payload.username):
        raise HTTPException(status_code=400, detail="Username sudah ada.")
    user = create_user(payload.username, payload.display_name, payload.role, hash_password(payload.password), must_change_password=False)
    return user


@app.get("/patients")
def patients(status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_patients(status=status, search=search)


@app.get("/patients/{patient_id}")
def patient(patient_id: str) -> Dict[str, Any]:
    p = get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan.")
    return p


@app.post("/patients")
async def create_patient_endpoint(payload: CreatePatientRequest) -> Dict[str, Any]:
    tracking_token = payload.tracking_token or secrets.token_urlsafe(24)
    triage = triage_engine(
        symptoms=payload.symptoms,
        vital_signs=payload.vitals,
        risk_factors=payload.risk_factors,
        photo_analysis=payload.photo_meta,
        age=payload.age,
        complaint=payload.chief_complaint,
        pregnancy=payload.pregnancy,
        additional_data=payload.additional_data,
    )
    video_recommended = triage.level in (1, 2) or triage.ambulance_now
    record = {
        "patient_id": f"PT-{secrets.token_hex(4).upper()}",
        "tracking_token": tracking_token,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": None,
        "source": payload.source,
        "name": payload.name,
        "age": payload.age,
        "sex": payload.sex,
        "pregnancy": payload.pregnancy,
        "chief_complaint": payload.chief_complaint,
        "symptoms": payload.symptoms,
        "risk_factors": payload.risk_factors,
        "vitals": payload.vitals,
        "photo_meta": payload.photo_meta,
        "image_path": payload.image_path,
        "location_text": payload.location_text,
        "gps_lat": payload.gps_lat,
        "gps_lon": payload.gps_lon,
        "gps_accuracy": payload.gps_accuracy,
        "emergency_phone": payload.emergency_phone,
        "triage": triage.__dict__,
        "status": "NEW",
        "reviewed_by": None,
        "reviewed_at": None,
        "notes": "",
        "video_recommended": bool(video_recommended),
        "video_requested": bool(video_recommended),
        "video_room_id": "",
        "video_status": "REQUESTED" if video_recommended else "NONE",
        "video_requested_at": datetime.now().isoformat(timespec="seconds") if video_recommended else None,
        "video_joined_at": None,
    }
    record["video_room_id"] = make_video_room_id(record["patient_id"]) if video_recommended else ""
    created = create_patient(record)
    await manager.broadcast({"event": "patient_created", "patient_id": record["patient_id"]})
    return created


@app.patch("/patients/{patient_id}")
async def update_patient(patient_id: str, payload: ReviewRequest) -> Dict[str, Any]:
    existing = get_patient(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan.")
    updates = {
        "status": payload.status,
        "notes": payload.notes,
        "reviewed_by": payload.reviewed_by,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    for field in ("video_recommended", "video_requested", "video_room_id", "video_status", "video_requested_at", "video_joined_at"):
        value = getattr(payload, field, None)
        if value is not None:
            updates[field] = value
    if payload.status in {"REVIEWED", "REFERRED", "ARRIVED", "CLOSED"}:
        updates["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    updated = update_patient_fields(patient_id, updates)
    record_status_history(patient_id, payload.status, payload.notes, payload.reviewed_by)
    await manager.broadcast({"event": "patient_updated", "patient_id": patient_id, "status": payload.status})
    return updated


@app.delete("/patients/{patient_id}")
async def delete_patient_endpoint(patient_id: str) -> Dict[str, str]:
    existing = get_patient(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan.")
    if existing.get("status") not in {"REVIEWED", "REFERRED", "ARRIVED", "CLOSED"}:
        raise HTTPException(status_code=400, detail="Hanya pasien yang sudah ditangani (status REVIEWED/CLOSED/dll) yang bisa dihapus.")
    deleted = delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Gagal menghapus pasien.")
    await manager.broadcast({"event": "patient_deleted", "patient_id": patient_id})
    return {"message": "Pasien berhasil dihapus."}


@app.post("/patients/{patient_id}/video")
async def update_patient_video(patient_id: str, payload: VideoStateRequest) -> Dict[str, Any]:
    existing = get_patient(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan.")
    updates: Dict[str, Any] = {"updated_at": datetime.now().isoformat(timespec="seconds")}
    for field in ("video_recommended", "video_requested", "video_room_id", "video_status", "video_requested_at", "video_joined_at"):
        value = getattr(payload, field, None)
        if value is not None:
            updates[field] = value
    updated = update_patient_fields(patient_id, updates)
    await manager.broadcast({"event": "video_updated", "patient_id": patient_id, "video_status": updates.get("video_status", existing.get("video_status", "NONE"))})
    return updated

@app.post("/gps/update")
async def gps_update(payload: GPSUpdateRequest) -> Dict[str, Any]:
    updated = update_gps(payload.patient_id, payload.tracking_token, payload.lat, payload.lon, payload.accuracy)
    if not updated:
        raise HTTPException(status_code=404, detail="Token atau pasien tidak valid.")
    await manager.broadcast({
        "event": "gps_update",
        "patient_id": payload.patient_id,
        "lat": payload.lat,
        "lon": payload.lon,
        "accuracy": payload.accuracy,
    })
    return {"success": True, "message": "GPS updated successfully"}


@app.get("/map-data")
def map_data() -> List[Dict[str, Any]]:
    return [p for p in list_patients() if p.get("gps_lat") is not None and p.get("gps_lon") is not None]


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/debug/default-admin")
def default_admin() -> Dict[str, Any]:
    return {"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASSWORD}

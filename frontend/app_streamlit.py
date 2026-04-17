from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium
import folium
import streamlit.components.v1 as components

from config.settings import (
    APP_ICON, APP_TITLE, API_BASE_URL, AUTO_REFRESH_SECONDS, DEFAULT_EMERGENCY_PHONE,
    UPLOAD_DIR, GPS_PUSH_SECONDS, ORGANIZATION_DEFAULT, VIDEO_CALL_BASE_URL, VIDEO_CALL_PREFIX,
)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: Dict[str, Any]) -> Any:
    r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def api_patch(path: str, payload: Dict[str, Any]) -> Any:
    r = requests.patch(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def ensure_state() -> None:
    st.session_state.setdefault("page", "home")
    st.session_state.setdefault("admin_token", None)
    st.session_state.setdefault("current_patient", None)
    st.session_state.setdefault("patient_tracking", None)


def now_title() -> None:
    st.title(f"{APP_ICON} {ORGANIZATION_DEFAULT}")
    st.caption("Teletriage pre-hospital untuk pasien, admin IGD, dan review riwayat.")


def short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def save_uploaded_photo(uploaded_file) -> tuple[Optional[str], Dict[str, Any]]:
    if uploaded_file is None:
        return None, {}
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{short_id()}_{uploaded_file.name}"
    path = UPLOAD_DIR / file_name
    path.write_bytes(uploaded_file.getbuffer())
    try:
        img = Image.open(path).convert("RGB")
        width, height = img.size
        return str(path), {"ok": True, "width": width, "height": height, "file_name": file_name}
    except Exception as exc:
        return str(path), {"ok": False, "error": str(exc)}


def gps_tracker_component(patient_id: str, tracking_token: str) -> None:
    js = f"""
    <script>
    const API_BASE = "{API_BASE_URL}";
    const PATIENT_ID = "{patient_id}";
    const TRACKING_TOKEN = "{tracking_token}";
    const PUSH_SECONDS = {GPS_PUSH_SECONDS};

    async function pushLocation() {{
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition(async (pos) => {{
            try {{
                const payload = {{
                    patient_id: PATIENT_ID,
                    tracking_token: TRACKING_TOKEN,
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                }};
                await fetch(API_BASE + "/gps/update", {{
                    method: "POST",
                    headers: {{"Content-Type": "application/json"}},
                    body: JSON.stringify(payload)
                }});
            }} catch (e) {{
                console.log(e);
            }}
        }}, (err) => console.log(err), {{enableHighAccuracy: true, maximumAge: 0, timeout: 10000}});
    }}

    pushLocation();
    setInterval(pushLocation, PUSH_SECONDS * 1000);
    </script>
    """
    components.html(js, height=0)


def make_video_room_id(patient_id: str) -> str:
    patient_id = str(patient_id or "").strip()
    return f"{VIDEO_CALL_PREFIX}_{patient_id}" if patient_id else ""


def video_call_url(room_id: str) -> str:
    room_id = str(room_id or "").strip()
    return f"{VIDEO_CALL_BASE_URL.rstrip('/')}/{room_id}" if room_id else ""


def show_video_link(label: str, url: str) -> None:
    if not url:
        return
    try:
        st.link_button(label, url, use_container_width=True)
    except Exception:
        st.markdown(f"[{label}]({url})")


def video_call_required(triage: Dict[str, Any]) -> bool:
    if not triage:
        return False
    return int(triage.get("level", 5)) in (1, 2) or bool(triage.get("ambulance_now"))


def home_page() -> None:
    now_title()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👤 Login / Pasien", use_container_width=True):
            st.session_state.page = "patient"
            st.rerun()
    with col2:
        if st.button("🧑‍⚕️ Login / Admin IGD", use_container_width=True):
            st.session_state.page = "admin"
            st.rerun()
    with col3:
        if st.button("📘 Panduan", use_container_width=True):
            st.session_state.page = "guide"
            st.rerun()
    st.info("Pilih peran untuk masuk ke alur pasien atau dashboard IGD.")
    st.markdown("### Fitur utama")
    st.write("• Pasien: input gejala, lokasi, foto, dan triase")
    st.write("• Admin: review, riwayat, peta pasien, dan status")
    st.write("• Local backend: FastAPI + SQLite + realtime GPS background")


def guide_page() -> None:
    now_title()
    st.markdown("### Panduan")
    st.write("1. Pasien isi data dan klik proses teletriase.")
    st.write("2. Sistem menghitung level triase secara konservatif.")
    st.write("3. Admin login untuk memantau pasien baru dan riwayat.")
    st.write("4. GPS dikirim background ke backend saat sesi pasien aktif.")
    st.write("5. Riwayat review memisahkan pasien yang sudah ditangani.")
    if st.button("⬅️ Kembali"):
        st.session_state.page = "home"
        st.rerun()


def patient_page() -> None:
    now_title()
    st.subheader("Pasien / Keluarga Pasien")
    if st.button("⬅️ Kembali ke beranda"):
        st.session_state.page = "home"
        st.rerun()

    current = st.session_state.current_patient
    if current:
        p = current
        st.success(f"Sesi aktif: {p['patient_id']} | Level {p['triage']['level']}")
        gps_tracker_component(p["patient_id"], p["tracking_token"])
        triage = p["triage"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Level", triage["level"])
        c2.metric("Label", triage["label"])
        c3.metric("Skor", triage["score"])
        c4.metric("Ambulans", "YA" if triage["ambulance_now"] else "TIDAK")
        st.info(triage["urgency_text"])
        st.write("**Ringkasan:**", triage["summary"])
        st.write("**Tindakan:**", triage["recommended_action"])
        if triage.get("red_flags"):
            st.markdown("**Red flags:**")
            for flag in triage["red_flags"]:
                st.error(flag)
        st.markdown("### Data tersimpan")
        st.json(p)
        if p.get("video_recommended"):
            st.error("Kondisi darurat terdeteksi. Video call IGD direkomendasikan.")
            show_video_link("▶ Mulai Video Call IGD", video_call_url(p.get("video_room_id") or make_video_room_id(p["patient_id"])))
        if st.button("Reset sesi pasien"):
            st.session_state.current_patient = None
            st.session_state.patient_tracking = None
            st.rerun()
        return

    with st.form("patient_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Nama pasien")
            age = st.number_input("Umur", min_value=0, max_value=120, value=30, step=1)
            sex = st.selectbox("Jenis kelamin", ["Laki-laki", "Perempuan", "Lainnya / tidak ingin menyebutkan"])
        with c2:
            complaint = st.text_area("Keluhan utama", height=120)
            pregnancy = st.checkbox("Sedang hamil / kemungkinan hamil", value=False)
        with c3:
            emergency_phone = st.text_input("Nomor darurat", value=DEFAULT_EMERGENCY_PHONE)

        st.markdown("### Gejala")
        symptoms = st.multiselect("Pilih gejala", [
            "Nyeri dada", "Sesak napas", "Bibir kebiruan", "Pingsan / hampir pingsan", "Kejang sedang berlangsung",
            "Kejang sudah berhenti", "Lemah satu sisi tubuh", "Bicara pelo / sulit bicara", "Wajah mencong",
            "Perdarahan hebat", "Luka terbuka berat", "Trauma / kecelakaan", "Nyeri hebat", "Demam tinggi",
            "Muntah berulang", "Dehidrasi berat", "Alergi berat / bengkak wajah", "Ruam menyeluruh / gatal hebat",
            "Nyeri perut hebat", "Hamil dengan perdarahan / nyeri hebat", "Penurunan kesadaran",
            "Kebingungan / perubahan perilaku", "Sulit menelan / tersedak", "Luka bakar luas", "Keluhan lain"
        ])
        custom_symptom = st.text_input("Gejala lain (opsional)")
        if custom_symptom.strip():
            symptoms = symptoms + [custom_symptom.strip()]

        risk_factors = st.multiselect("Faktor risiko", [
            "Riwayat penyakit jantung", "Riwayat stroke / TIA", "Diabetes", "Hipertensi",
            "Asma / PPOK", "Gangguan ginjal", "Hamil", "Usia lanjut", "Tidak ada faktor risiko yang diketahui"
        ])
        if "Tidak ada faktor risiko yang diketahui" in risk_factors and len(risk_factors) > 1:
            risk_factors = [x for x in risk_factors if x != "Tidak ada faktor risiko yang diketahui"]

        st.markdown("### Pemeriksaan awal")
        mode = st.radio("Mode input", ["Awam / keluarga pasien"], horizontal=True)
        vitals: Dict[str, Any] = {}
        if mode == "Awam / keluarga pasien":
            v1, v2, v3 = st.columns(3)
            with v1:
                temp = st.number_input("Suhu tubuh (°C)", min_value=30.0, max_value=45.0, value=36.8, step=0.1)
                bp_known = st.checkbox("Tekanan darah diketahui", value=True)
                if bp_known:
                    sbp = st.number_input("Sistolik (mmHg)", min_value=0, max_value=300, value=120, step=1)
                    dbp = st.number_input("Diastolik (mmHg)", min_value=0, max_value=200, value=80, step=1)
                else:
                    sbp = None
                    dbp = None
            with v2:
                hr = st.number_input("Detak jantung / menit", min_value=0, max_value=250, value=80, step=1)
                spo2_known = st.checkbox("Saturasi oksigen diketahui", value=False)
                spo2 = st.number_input("SpO2 (%)", min_value=0, max_value=100, value=98, step=1) if spo2_known else None
                pain_score = st.slider("Nyeri (0-10)", 0, 10, 0)
            with v3:
                breath_simple = st.radio("Sesak napas?", ["Tidak", "Ya, ringan", "Ya, sedang", "Ya, berat"])
                conscious_simple = st.radio("Kesadaran", ["Ya, sadar penuh", "Agak bingung / mengantuk", "Tidak sadar / sulit dibangunkan"])
                gcs = 15 if conscious_simple == "Ya, sadar penuh" else (12 if conscious_simple == "Agak bingung / mengantuk" else 7)
                rr = None
            if spo2 is None:
                breath_score = 0 if breath_simple == "Tidak" else 1 if breath_simple == "Ya, ringan" else 2 if breath_simple == "Ya, sedang" else 3
                spo2 = 98 if breath_score == 0 else 95 if breath_score == 1 else 92 if breath_score == 2 else 88
            vitals = {"spo2": spo2, "heart_rate": hr, "respiratory_rate": rr, "sbp": sbp, "dbp": dbp, "temperature": temp, "gcs": gcs, "pain_score": pain_score}

        uploaded_file = st.file_uploader("Foto kondisi pasien (opsional)", type=["jpg", "jpeg", "png", "webp"])
        submit = st.form_submit_button("🔍 Proses Teletriase", type="primary")

    if submit:
        if not name.strip():
            st.error("Nama pasien wajib diisi.")
            return
        if not complaint.strip() and not symptoms:
            st.error("Isi keluhan utama atau pilih gejala minimal satu.")
            return
        photo_path = None
        photo_meta: Dict[str, Any] = {}
        if uploaded_file is not None:
            photo_path, photo_meta = save_uploaded_photo(uploaded_file)
        payload = {
            "source": "patient_web",
            "name": name.strip(),
            "age": int(age),
            "sex": sex,
            "pregnancy": pregnancy,
            "chief_complaint": complaint.strip(),
            "symptoms": symptoms,
            "risk_factors": risk_factors,
            "vitals": vitals,
            "photo_meta": photo_meta,
            "image_path": photo_path,
            "emergency_phone": emergency_phone.strip() or DEFAULT_EMERGENCY_PHONE,
        }
        result = api_post("/patients", payload)
        st.session_state.current_patient = result
        st.session_state.patient_tracking = {"patient_id": result["patient_id"], "tracking_token": result["tracking_token"]}
        st.success("Data tersimpan dan triase selesai.")
        if result.get("video_recommended"):
            st.error("Kondisi darurat terdeteksi. Video call IGD direkomendasikan.")
            show_video_link("▶ Mulai Video Call IGD", video_call_url(result.get("video_room_id") or make_video_room_id(result["patient_id"])))
        st.rerun()


def draw_map(patients: List[Dict[str, Any]]) -> None:
    points = [p for p in patients if p.get("gps_lat") is not None and p.get("gps_lon") is not None]
    if not points:
        st.info("Belum ada lokasi pasien yang tersimpan.")
        return
    first = points[0]
    m = folium.Map(location=[first["gps_lat"], first["gps_lon"]], zoom_start=12)
    for p in points:
        triage = p.get("triage", {})
        level = int(triage.get("level", 5))
        color = "red" if level == 1 else "orange" if level == 2 else "green" if level >= 4 else "blue"
        popup = f"{p.get('patient_id')} | {p.get('name')} | Level {level} | {p.get('status')}"
        folium.Marker([p["gps_lat"], p["gps_lon"]], tooltip=p.get("name"), popup=popup, icon=folium.Icon(color=color, icon="info-sign")).add_to(m)
    st_folium(m, width=900, height=520)


def render_patient_card(p: Dict[str, Any], context: str) -> None:
    triage = p.get("triage", {})
    unique = f"{context}_{p.get('patient_id')}_{p.get('created_at')}"
    with st.expander(f"{triage.get('emoji', '⚪')} {p.get('patient_id')} | {p.get('name')} | {triage.get('label')}", expanded=triage.get("level", 5) in (1, 2)):
        c1, c2, c3, c4 = st.columns(4)
        c1.write(f"**Umur:** {p.get('age')}")
        c2.write(f"**Jenis kelamin:** {p.get('sex')}")
        c3.write(f"**Status:** {p.get('status')}")
        c4.write(f"**Waktu:** {p.get('created_at')}")
        st.write("**Keluhan utama:**", p.get("chief_complaint", "-"))
        st.write("**Lokasi:**", p.get("location_text", "-"))
        if p.get("gps_lat") is not None or p.get("gps_lon") is not None:
            st.write(f"**GPS:** {p.get('gps_lat')}, {p.get('gps_lon')}")
        st.write("**Gejala:**", ", ".join(p.get("symptoms", [])) or "-")
        st.write("**Faktor risiko:**", ", ".join(p.get("risk_factors", [])) or "-")
        st.write("**Hasil triage:**", triage.get("urgency_text", "-"))
        st.write("**Tindakan:**", triage.get("recommended_action", "-"))
        if triage.get("red_flags"):
            st.markdown("**Red flags:**")
            for flag in triage.get("red_flags", []):
                st.error(flag)
        if p.get("photo_meta"):
            st.markdown("**Analisis foto:**")
            st.json(p["photo_meta"])
        if p.get("image_path") and Path(p["image_path"]).exists():
            st.image(p["image_path"], caption="Foto pasien", use_container_width=True)

        if video_call_required(triage):
            st.markdown("**Video Call Darurat:**")
            room_id = p.get("video_room_id") or make_video_room_id(p.get("patient_id", ""))
            st.warning("Kasus ini otomatis memenuhi kriteria video call.")
            st.write(f"Room ID: `{room_id}`")
            show_video_link("▶ Join Video Call", video_call_url(room_id))
            if st.button("Tandai Video Call Dimulai", key=f"video_start_{unique}"):
                api_post(f"/patients/{p['patient_id']}/video", {"video_status": "ACTIVE", "video_joined_at": datetime.now().isoformat(timespec='seconds')})
                st.success("Status video call diperbarui.")
                st.rerun()

        current_note = p.get("notes", "")
        note_key = f"note_{unique}"
        status_key = f"status_{unique}"
        reviewer_key = f"reviewer_{unique}"
        save_key = f"save_{unique}"

        new_note = st.text_area("Tulis catatan", value=current_note, key=note_key, height=120)
        coln1, coln2, coln3 = st.columns(3)
        with coln1:
            update_status = st.selectbox(
                "Update status",
                ["NEW", "IN_REVIEW", "REVIEWED", "REFERRED", "ARRIVED", "CLOSED"],
                index=["NEW", "IN_REVIEW", "REVIEWED", "REFERRED", "ARRIVED", "CLOSED"].index(p.get("status", "NEW")) if p.get("status", "NEW") in ["NEW", "IN_REVIEW", "REVIEWED", "REFERRED", "ARRIVED", "CLOSED"] else 0,
                key=status_key,
            )
        with coln2:
            reviewer = st.text_input("Reviewed by", value=p.get("reviewed_by") or "", key=reviewer_key)
        with coln3:
            save_btn = st.button("Simpan perubahan", key=save_key)
        if save_btn:
            api_patch(f"/patients/{p['patient_id']}", {"status": update_status, "notes": new_note, "reviewed_by": reviewer})
            st.success("Perubahan disimpan.")
            st.rerun()


def admin_page() -> None:
    now_title()
    st.subheader("Admin IGD")
    if st.button("⬅️ Kembali ke beranda"):
        st.session_state.page = "home"
        st.rerun()

    if not st.session_state.admin_token:
        st.markdown("### Login admin")
        with st.form("admin_login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Masuk")
        if login_submit:
            try:
                result = api_post("/auth/login", {"username": username, "password": password})
                st.session_state.admin_token = result["access_token"]
                st.success("Login berhasil.")
                st.rerun()
            except Exception as exc:
                st.error(f"Login gagal: {exc}")
        return

    st_autorefresh(interval=AUTO_REFRESH_SECONDS * 1000, key="admin_refresh")

    try:
        summary = api_get("/summary")
        patients = api_get("/patients")
    except Exception as exc:
        st.error(f"Gagal mengambil data backend: {exc}")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", summary["total"])
    m2.metric("Baru", summary["new"])
    m3.metric("Review", summary["reviewed"])
    m4.metric("Urgent", summary["urgent"])
    m5.metric("GPS aktif", summary["gps"])

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        filter_mode = st.selectbox("Filter data", ["Semua", "Belum Review", "Riwayat Review", "IN_REVIEW"])
    with col_b:
        search_query = st.text_input("Cari nama / ID / keluhan")
    with col_c:
        only_urgent = st.checkbox("Hanya level 1-2", value=False)

    if filter_mode == "Belum Review":
        filtered = [p for p in patients if p.get("status") == "NEW"]
    elif filter_mode == "Riwayat Review":
        filtered = [p for p in patients if p.get("status") in {"REVIEWED", "REFERRED", "ARRIVED", "CLOSED"}]
    elif filter_mode == "IN_REVIEW":
        filtered = [p for p in patients if p.get("status") == "IN_REVIEW"]
    else:
        filtered = patients

    if only_urgent:
        filtered = [p for p in filtered if int(p.get("triage", {}).get("level", 5)) in (1, 2)]
    if search_query:
        q = search_query.lower()
        filtered = [p for p in filtered if q in f"{p.get('patient_id','')} {p.get('name','')} {p.get('chief_complaint','')}".lower()]

    st.caption(f"Menampilkan {len(filtered)} dari {len(patients)} data pasien.")

    if st.button("🔄 Refresh data", key="manual_refresh"):
        st.rerun()

    st.markdown("### Peta pasien")
    draw_map(filtered)

    st.markdown("### Daftar pasien")
    for p in filtered:
        render_patient_card(p, context=filter_mode)

    st.markdown("---")
    st.markdown("### Riwayat operasional")
    st.info("Pasien yang sudah diubah status ke REVIEWED / REFERRED / ARRIVED / CLOSED akan masuk ke riwayat review.")

    st.markdown("### Pengaturan / keamanan")
    with st.expander("Lihat data akun admin"):
        try:
            users = api_get("/users")
            st.table([{"username": u["username"], "display_name": u["display_name"], "role": u["role"], "must_change_password": bool(u.get("must_change_password", 0))} for u in users])
        except Exception as exc:
            st.error(str(exc))

    if st.button("Logout", key="logout_btn"):
        st.session_state.admin_token = None
        st.session_state.page = "home"
        st.rerun()


def main() -> None:
    ensure_state()
    page = st.session_state.page
    if page == "home":
        home_page()
    elif page == "patient":
        patient_page()
    elif page == "admin":
        admin_page()
    elif page == "guide":
        guide_page()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()

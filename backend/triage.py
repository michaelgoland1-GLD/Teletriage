# from __future__ import annotations

# from dataclasses import dataclass
# from typing import Any, Dict, List, Optional

# from PIL import Image, ImageOps, ImageStat

# TRIAGE_LABELS = {
#     1: "ESI 1-RESUSITASI / DARURAT SEKALI",
#     2: "ESI 2-SANGAT MENDESAK",
#     3: "ESI 3-MENDESAK SEDANG",
#     4: "ESI 4-RINGAN",
#     5: "ESI 5-SANGAT RINGAN",
# }

# TRIAGE_COLORS_HINT = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}

# @dataclass
# class TriageResult:
#     level: int
#     label: str
#     emoji: str
#     urgency_text: str
#     summary: str
#     recommended_action: str
#     ambulance_now: bool
#     red_flags: List[str]
#     factors: List[str]
#     score: int
#     evidence: List[str]


# def _to_float(value: Any) -> Optional[float]:
#     try:
#         if value is None or value == "":
#             return None
#         return float(value)
#     except Exception:
#         return None


# def normalize_text_items(items: List[str]) -> List[str]:
#     return [str(i).strip().lower() for i in items if str(i).strip()]


# def analyze_photo(image_file) -> Dict[str, Any]:
#     try:
#         img = Image.open(image_file).convert("RGB")
#         img = ImageOps.exif_transpose(img)
#         width, height = img.size
#         stat = ImageStat.Stat(img)
#         r_mean, g_mean, b_mean = stat.mean
#         gray = ImageOps.grayscale(img)
#         gray_stat = ImageStat.Stat(gray)
#         brightness = gray_stat.mean[0]
#         contrast = gray_stat.stddev[0]
#         red_dominance = max(0.0, r_mean - ((g_mean + b_mean) / 2.0))
#         blue_dominance = max(0.0, b_mean - ((r_mean + g_mean) / 2.0))
#         quality_flags = []
#         if min(width, height) < 300:
#             quality_flags.append("Resolusi gambar rendah")
#         if brightness < 40:
#             quality_flags.append("Gambar terlalu gelap")
#         if contrast < 15:
#             quality_flags.append("Kontras gambar rendah")
#         visual_clues = []
#         if red_dominance > 18:
#             visual_clues.append("Warna merah dominan terlihat pada foto")
#         if blue_dominance > 10:
#             visual_clues.append("Warna kebiruan dominan terlihat pada foto")
#         return {
#             "ok": True,
#             "width": width,
#             "height": height,
#             "brightness": round(brightness, 2),
#             "contrast": round(contrast, 2),
#             "quality_flags": quality_flags,
#             "visual_clues": visual_clues,
#             "red_dominance": round(red_dominance, 2),
#             "blue_dominance": round(blue_dominance, 2),
#         }
#     except Exception as exc:
#         return {"ok": False, "error": str(exc), "quality_flags": ["Gagal membaca foto"], "visual_clues": []}


# def triage_engine(
#     symptoms: List[str],
#     vital_signs: Dict[str, Any],
#     risk_factors: List[str],
#     photo_analysis: Optional[Dict[str, Any]] = None,
#     age: Optional[int] = None,
#     complaint: str = "",
#     pregnancy: bool = False,
# ) -> TriageResult:
#     symptoms_n = normalize_text_items(symptoms)
#     risks_n = normalize_text_items(risk_factors)
#     complaint_n = complaint.strip().lower()

#     score = 0
#     evidence: List[str] = []
#     red_flags: List[str] = []

#     def add_score(points: int, reason: str) -> None:
#         nonlocal score
#         score += points
#         evidence.append(reason)

#     spo2 = _to_float(vital_signs.get("spo2"))
#     rr = _to_float(vital_signs.get("respiratory_rate"))
#     hr = _to_float(vital_signs.get("heart_rate"))
#     sbp = _to_float(vital_signs.get("sbp"))
#     dbp = _to_float(vital_signs.get("dbp"))
#     temp = _to_float(vital_signs.get("temperature"))
#     gcs = _to_float(vital_signs.get("gcs"))
#     pain = _to_float(vital_signs.get("pain_score"))

#     if spo2 is not None:
#         if spo2 < 90:
#             add_score(8, f"SpO2 sangat rendah ({spo2}%)")
#             red_flags.append("SpO2 < 90%")
#         elif spo2 < 94:
#             add_score(4, f"SpO2 rendah ({spo2}%)")

#     if rr is not None:
#         if rr > 30:
#             add_score(6, f"Frekuensi napas sangat tinggi ({rr}/menit)")
#             red_flags.append("Tachypnea berat")
#         elif rr < 8:
#             add_score(7, f"Frekuensi napas sangat rendah ({rr}/menit)")
#             red_flags.append("Bradypnea berat")

#     if hr is not None:
#         if hr > 130:
#             add_score(4, f"Nadi sangat cepat ({hr}/menit)")
#         elif hr < 40:
#             add_score(6, f"Nadi sangat lambat ({hr}/menit)")
#             red_flags.append("Bradycardia berat")

#     if sbp is not None:
#         if sbp < 90:
#             add_score(6, f"Sistolik rendah ({sbp} mmHg)")
#             red_flags.append("Hipotensi")
#         elif sbp > 220:
#             add_score(4, f"Sistolik sangat tinggi ({sbp} mmHg)")

#     if dbp is not None and dbp > 130:
#         add_score(3, f"Diastolik sangat tinggi ({dbp} mmHg)")

#     if temp is not None and temp >= 40.0:
#         add_score(4, f"Demam sangat tinggi ({temp}°C)")

#     if gcs is not None:
#         if gcs <= 8:
#             add_score(8, f"Penurunan kesadaran berat (GCS {gcs})")
#             red_flags.append("GCS rendah")
#         elif gcs <= 12:
#             add_score(4, f"Penurunan kesadaran sedang (GCS {gcs})")

#     if pain is not None and pain >= 8:
#         add_score(3, f"Nyeri sangat berat ({pain}/10)")

#     if "nyeri dada" in symptoms_n or "chest pain" in complaint_n:
#         add_score(5, "Keluhan nyeri dada")
#         red_flags.append("Chest pain")
#         evidence.append("Perlu evaluasi sindrom koroner akut bila gejala konsisten")

#     if "sesak napas" in symptoms_n or "bibir kebiruan" in symptoms_n:
#         add_score(5, "Gejala gangguan napas")
#         red_flags.append("Gangguan napas")

#     if any(x in symptoms_n for x in ["pingsan / hampir pingsan", "penurunan kesadaran"]):
#         add_score(6, "Sinkop / penurunan kesadaran")
#         red_flags.append("Altered consciousness")

#     if any(x in symptoms_n for x in ["kejang sedang berlangsung", "kejang sudah berhenti"]):
#         add_score(5, "Riwayat kejang")
#         if "kejang sedang berlangsung" in symptoms_n:
#             red_flags.append("Active seizure")

#     if any(x in symptoms_n for x in ["lemah satu sisi tubuh", "bicara pelo / sulit bicara", "wajah mencong"]):
#         add_score(6, "Tanda neurologis fokal / FAST positif")
#         red_flags.append("Stroke suspected")

#     if any(x in symptoms_n for x in ["perdarahan hebat", "luka terbuka berat", "trauma / kecelakaan", "luka bakar luas"]):
#         add_score(5, "Trauma atau perdarahan signifikan")
#         red_flags.append("Trauma / hemorrhage")

#     if any(x in symptoms_n for x in ["alergi berat / bengkak wajah", "ruam menyeluruh / gatal hebat"]):
#         add_score(5, "Reaksi alergi berat mungkin")
#         red_flags.append("Anaphylaxis suspected")

#     if any(x in symptoms_n for x in ["nyeri perut hebat", "hamil dengan perdarahan / nyeri hebat"]):
#         add_score(4, "Nyeri abdomen / obstetri berisiko")
#         if pregnancy:
#             red_flags.append("Pregnancy-related emergency")

#     if any(x in symptoms_n for x in ["demam tinggi", "muntah berulang", "dehidrasi berat"]):
#         add_score(3, "Sistemik / risiko dehidrasi / infeksi")

#     if age is not None and age >= 65:
#         add_score(1, "Usia lanjut meningkatkan risiko")
#     if "riwayat penyakit jantung" in risks_n:
#         add_score(2, "Riwayat penyakit jantung")
#     if "riwayat stroke / tia" in risks_n:
#         add_score(2, "Riwayat stroke / TIA")
#     if "diabetes" in risks_n:
#         add_score(1, "Diabetes")
#     if "hipertensi" in risks_n:
#         add_score(1, "Hipertensi")
#     if "asma / ppok" in risks_n:
#         add_score(1, "Asma / PPOK")
#     if pregnancy:
#         add_score(2, "Kehamilan meningkatkan kewaspadaan")

#     if photo_analysis and photo_analysis.get("ok"):
#         if photo_analysis.get("quality_flags"):
#             evidence.extend([f"Foto: {x}" for x in photo_analysis["quality_flags"]])
#         if photo_analysis.get("visual_clues"):
#             evidence.extend([f"Foto: {x}" for x in photo_analysis["visual_clues"]])
#         if photo_analysis.get("blue_dominance", 0) > 12:
#             add_score(2, "Petunjuk visual kebiruan pada foto")
#         if photo_analysis.get("red_dominance", 0) > 20 and any(x in symptoms_n for x in ["perdarahan hebat", "luka terbuka berat", "trauma / kecelakaan"]):
#             add_score(2, "Petunjuk visual merah dominan + trauma/perdarahan")

#     if (
#         any(x in red_flags for x in ["SpO2 < 90%", "GCS rendah", "Stroke suspected", "Anaphylaxis suspected", "Trauma / hemorrhage", "Active seizure"])
#         or (pain is not None and pain >= 9 and ("nyeri dada" in symptoms_n or "sesak napas" in symptoms_n))
#         or (sbp is not None and sbp < 90 and (hr is not None and hr > 120))
#     ):
#         level = 1
#     elif score >= 8 or any(x in red_flags for x in ["Chest pain", "Gangguan napas", "Altered consciousness", "Pregnancy-related emergency"]):
#         level = 2
#     elif score >= 4:
#         level = 3
#     elif score >= 2:
#         level = 4
#     else:
#         level = 5

#     ambulance_now = level in (1, 2)

#     if level == 1:
#         urgency_text = "Ambulans / IGD segera. Prioritas resusitasi."
#         action_lines = [
#             "Hubungi ambulans / layanan gawat darurat sekarang.",
#             "Pastikan jalan napas, pernapasan, dan sirkulasi.",
#             "Jangan tinggalkan pasien sendirian.",
#             "Siapkan lokasi, usia, gejala, obat yang diminum, dan waktu mulai gejala.",
#         ]
#         summary = "Pasien tampak sangat berisiko mengalami kegawatan kritis."
#     elif level == 2:
#         urgency_text = "Segera ke IGD / ambulans bila kondisi memburuk."
#         action_lines = [
#             "Rujuk ke IGD segera dengan pengawasan ketat.",
#             "Pantau napas, kesadaran, dan nyeri.",
#             "Kurangi aktivitas dan siapkan transportasi medis.",
#         ]
#         summary = "Pasien berisiko tinggi dan membutuhkan penilaian darurat cepat."
#     elif level == 3:
#         urgency_text = "Perlu evaluasi klinis segera, tetapi tidak selalu ambulans."
#         action_lines = [
#             "Segera konsultasi ke fasilitas kesehatan terdekat.",
#             "Pantau perburukan gejala.",
#             "Jika muncul nyeri dada, sesak napas, pingsan, atau lemah satu sisi, naikkan ke darurat.",
#         ]
#         summary = "Pasien membutuhkan penilaian medis dalam waktu singkat."
#     elif level == 4:
#         urgency_text = "Keluhan ringan-sedang, evaluasi terjadwal."
#         action_lines = [
#             "Disarankan kontrol/telekonsultasi.",
#             "Bila gejala memburuk, ulangi triase.",
#         ]
#         summary = "Pasien cenderung stabil saat ini."
#     else:
#         urgency_text = "Keluhan ringan, edukasi dan observasi mandiri."
#         action_lines = [
#             "Monitor gejala.",
#             "Cari bantuan medis jika muncul red flag.",
#         ]
#         summary = "Pasien tampak paling rendah risiko saat ini."

#     if not evidence:
#         evidence.append("Tidak ada red flag mayor terdeteksi dari input awal")

#     return TriageResult(
#         level=level,
#         label=TRIAGE_LABELS[level],
#         emoji=TRIAGE_COLORS_HINT[level],
#         urgency_text=urgency_text,
#         summary=summary,
#         recommended_action=" ".join(action_lines),
#         ambulance_now=ambulance_now,
#         red_flags=red_flags,
#         factors=evidence,
#         score=score,
#         evidence=evidence,
#     )






from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PIL import Image, ImageOps, ImageStat

# ==========================================
# KONFIGURASI MEDIS & ESI (MUDAH DIUBAH)
# ==========================================

TRIAGE_LABELS = {
    1: "ESI 1 - RESUSITASI / DARURAT SEKALI",
    2: "ESI 2 - SANGAT MENDESAK / RISIKO TINGGI",
    3: "ESI 3 - MENDESAK SEDANG (Butuh >= 2 Sumber Daya)",
    4: "ESI 4 - RINGAN (Butuh 1 Sumber Daya)",
    5: "ESI 5 - SANGAT RINGAN (Tidak Butuh Sumber Daya)",
}

TRIAGE_COLORS_HINT = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}

# Parameter tanda vital berdasarkan kategori usia
VITAL_THRESHOLDS = {
    "infant": {"hr_high": 160, "hr_low": 80, "rr_high": 50, "rr_low": 20},  # < 1 thn
    "toddler": {"hr_high": 140, "hr_low": 70, "rr_high": 40, "rr_low": 20}, # 1 - 3 thn
    "child": {"hr_high": 120, "hr_low": 60, "rr_high": 30, "rr_low": 16},   # 4 - 12 thn
    "adult": {"hr_high": 100, "hr_low": 50, "rr_high": 20, "rr_low": 12},   # > 12 thn
}

# Kata kunci negasi untuk NLP ringan
NEGATION_WORDS = r"\b(tidak|tanpa|menyangkal|bukan|belum|gada|ngga|nggak)\b"

# ESI 1: Kondisi mengancam nyawa segera
ESI_1_FLAGS = [
    "henti napas", "henti jantung", "pingsan total", "tidak sadar", 
    "kejang sedang berlangsung", "perdarahan hebat", "luka terbuka berat"
]

# ESI 2: Risiko tinggi, disorientasi, atau nyeri hebat
ESI_2_FLAGS = [
    "nyeri dada", "sesak napas", "lemah satu sisi", "bicara pelo",
    "wajah mencong", "nyeri perut hebat", "hamil dengan perdarahan", "kejang sudah berhenti",
    "sakit kepala hebat", "mual parah", "kelelahan ekstrem", "halusinasi", "delusi"
]

# Prediksi kebutuhan sumber daya (Resource) IGD untuk penentuan ESI 3-5
RESOURCE_ESTIMATE = {
    "nyeri dada": 3, "nyeri perut": 2, "trauma": 2, "sesak napas": 2, "muntah berulang": 2,
    "patah tulang": 2, "keseleo": 1, "luka robek": 1, "luka bakar kecil": 1,
    "demam": 0, "batuk pilek": 0, "sakit tenggorokan": 0, "gatal": 0
}

# ==========================================
# STRUKTUR DATA UTAMA
# ==========================================

@dataclass
class TriageResult:
    level: int
    label: str
    emoji: str
    score: int
    urgency_text: str
    summary: str
    recommended_action: str
    ambulance_now: bool
    red_flags: List[str]
    estimated_resources: int
    evidence: List[str]


# ==========================================
# FUNGSI UTILITAS LINGKUNGAN
# ==========================================

def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None

def get_age_category(age: Optional[int]) -> str:
    if age is None: return "adult"
    if age < 1: return "infant"
    if age <= 3: return "toddler"
    if age <= 12: return "child"
    return "adult"

def has_symptom(text: str, symptom: str) -> bool:
    """Mendeteksi gejala dengan mempertimbangkan kata negasi di sekitarnya."""
    text_lower = text.lower()
    # Cari symptom, lalu cek apakah 3 kata sebelumnya ada kata negasi
    pattern = rf"(?:{NEGATION_WORDS}\s+(?:\w+\s+){{0,3}})?({symptom})"
    matches = re.finditer(pattern, text_lower)
    
    for match in matches:
        full_match = match.group(0)
        # Jika dalam full_match TIDAK ada kata negasi, berarti gejala positif
        if not re.search(NEGATION_WORDS, full_match):
            return True
    return False

def check_symptom_list(symptoms_raw: List[str], complaint: str, target_list: List[str]) -> List[str]:
    """Mengembalikan daftar gejala yang terdeteksi valid (tanpa negasi)."""
    combined_text = " ".join([str(s) for s in symptoms_raw]) + " " + str(complaint)
    found = []
    for symptom in target_list:
        if has_symptom(combined_text, symptom):
            found.append(symptom)
    return found


# ==========================================
# MODUL ANALISIS GAMBAR
# ==========================================

def analyze_photo(image_file) -> Dict[str, Any]:
    try:
        img = Image.open(image_file).convert("RGB")
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        
        # Crop area tengah gambar (50%) untuk meminimalkan false positive dari background
        left = width * 0.25
        top = height * 0.25
        right = width * 0.75
        bottom = height * 0.75
        center_img = img.crop((left, top, right, bottom))
        
        stat = ImageStat.Stat(center_img)
        r_mean, g_mean, b_mean = stat.mean
        
        gray = ImageOps.grayscale(center_img)
        gray_stat = ImageStat.Stat(gray)
        brightness = gray_stat.mean[0]
        contrast = gray_stat.stddev[0]
        
        red_dominance = max(0.0, r_mean - ((g_mean + b_mean) / 2.0))
        blue_dominance = max(0.0, b_mean - ((r_mean + g_mean) / 2.0))
        
        quality_flags = []
        if min(width, height) < 300:
            quality_flags.append("Resolusi gambar rendah")
        if brightness < 40:
            quality_flags.append("Gambar terlalu gelap")
        if contrast < 15:
            quality_flags.append("Kontras gambar rendah")
            
        visual_clues = []
        if red_dominance > 25:
            visual_clues.append("Warna merah dominan di area fokus (indikasi perdarahan/kemerahan)")
        if blue_dominance > 15:
            visual_clues.append("Warna kebiruan dominan di area fokus (indikasi sianosis/memar)")
            
        return {
            "ok": True,
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "quality_flags": quality_flags,
            "visual_clues": visual_clues,
            "red_dominance": round(red_dominance, 2),
            "blue_dominance": round(blue_dominance, 2),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "quality_flags": ["Gagal membaca foto"], "visual_clues": []}


# ==========================================
# ENGINE TELETRIAGE ESI (EMERGENCY SEVERITY INDEX)
# ==========================================

def triage_engine(
    symptoms: List[str],
    vital_signs: Dict[str, Any],
    risk_factors: List[str],
    photo_analysis: Optional[Dict[str, Any]] = None,
    age: Optional[int] = None,
    complaint: str = "",
    pregnancy: bool = False,
) -> TriageResult:
    
    evidence: List[str] = []
    red_flags: List[str] = []
    age_cat = get_age_category(age)
    thresholds = VITAL_THRESHOLDS[age_cat]
    
    # 1. Parsing Tanda Vital
    spo2 = _to_float(vital_signs.get("spo2"))
    rr = _to_float(vital_signs.get("respiratory_rate"))
    hr = _to_float(vital_signs.get("heart_rate"))
    sbp = _to_float(vital_signs.get("sbp"))
    gcs = _to_float(vital_signs.get("gcs"))
    pain = _to_float(vital_signs.get("pain_score"))
    
    # 2. Pengumpulan Tanda Bahaya (Flags) berdasarkan Vital
    if spo2 is not None and spo2 < 90:
        red_flags.append("SpO2 < 90%")
        evidence.append(f"Hipoksia berat ({spo2}%)")
        
    if gcs is not None and gcs <= 8:
        red_flags.append("GCS <= 8")
        evidence.append(f"Koma / Penurunan kesadaran berat (GCS {gcs})")
        
    if sbp is not None and sbp < 90 and age_cat == "adult":
        red_flags.append("Hipotensi (Dewasa)")
        evidence.append(f"Tekanan darah sistolik rendah ({sbp} mmHg)")

    # 2.5. Pengumpulan Faktor Risiko yang Meningkatkan Skor
    risk_boost = 0
    if risk_factors:
        risks_n = [str(r).strip().lower() for r in risk_factors]
        if "riwayat penyakit jantung" in risks_n or "riwayat stroke" in risks_n:
            risk_boost += 1
            evidence.append("Riwayat kardiovaskular meningkatkan risiko")
        if "diabetes" in risks_n or "hipertensi" in risks_n:
            risk_boost += 1
            evidence.append("Riwayat metabolik meningkatkan risiko")
        if "merokok" in risks_n or "obesitas" in risks_n:
            risk_boost += 1
            evidence.append("Faktor gaya hidup berisiko terdeteksi")
        if pregnancy:
            risk_boost += 1
            evidence.append("Kehamilan meningkatkan kewaspadaan")

    # 3. Pengumpulan Tanda Bahaya dari Teks Keluhan & Gejala (Tanpa Negasi)
    esi_1_symptoms = check_symptom_list(symptoms, complaint, ESI_1_FLAGS)
    esi_2_symptoms = check_symptom_list(symptoms, complaint, ESI_2_FLAGS)
    
    if esi_1_symptoms:
        red_flags.extend(esi_1_symptoms)
        evidence.append(f"Indikasi kritis terdeteksi: {', '.join(esi_1_symptoms)}")
        
    if esi_2_symptoms:
        evidence.append(f"Indikasi risiko tinggi terdeteksi: {', '.join(esi_2_symptoms)}")

    if pregnancy and check_symptom_list(symptoms, complaint, ["perdarahan", "nyeri"]):
        evidence.append("Kehamilan dengan penyulit terdeteksi")
        esi_2_symptoms.append("Kehamilan berisiko")

    # 4. Integrasi Bukti Visual dari Foto
    if photo_analysis and photo_analysis.get("ok"):
        if photo_analysis.get("visual_clues"):
            evidence.extend([f"Foto: {x}" for x in photo_analysis["visual_clues"]])
            # Up-triage logic based on visual
            if photo_analysis.get("blue_dominance", 0) > 15:
                esi_2_symptoms.append("Sianosis (Visual)")
            if photo_analysis.get("red_dominance", 0) > 25 and check_symptom_list(symptoms, complaint, ["trauma", "kecelakaan", "luka"]):
                esi_2_symptoms.append("Perdarahan aktif dicurigai (Visual)")

    # 5. ESTIMASI SUMBER DAYA (Resources) untuk ESI 3, 4, 5
    # Menghitung estimasi maksimal dari keluhan yang dicocokkan
    estimated_resources = 0
    combined_text_for_resources = " ".join([str(s) for s in symptoms]) + " " + complaint.lower()
    
    for key_symptom, res_count in RESOURCE_ESTIMATE.items():
        if has_symptom(combined_text_for_resources, key_symptom):
            estimated_resources = max(estimated_resources, res_count)
            evidence.append(f"Gejala '{key_symptom}' diprediksi butuh {res_count} sumber daya IGD")
            
    # Usia lanjut / bayi yang demam membutuhkan lebih banyak evaluasi (lab/observasi)
    if (age is not None and age >= 65) or age_cat in ["infant", "toddler"]:
        if estimated_resources == 0 and has_symptom(combined_text_for_resources, "demam"):
            estimated_resources = 1
            evidence.append("Pasien risiko usia (Geriatri/Pediatri) dengan demam diprediksi butuh evaluasi medis")

    # 6. PENENTUAN LEVEL ESI (DECISION TREE LOGIC)
    
    # ESI 1: Intervensi Penyelamatan Nyawa Segera?
    if any(x in red_flags for x in ["SpO2 < 90%", "GCS <= 8"]) or len(esi_1_symptoms) > 0:
        level = 1
        
    # ESI 2: Situasi Risiko Tinggi, Disorientasi, Nyeri Hebat?
    elif (
        len(esi_2_symptoms) > 0 
        or (pain is not None and pain >= 8) 
        or "Hipotensi (Dewasa)" in red_flags
        or (spo2 is not None and spo2 < 94) # Hypoxia ringan
    ):
        level = 2
        
    # ESI 3, 4, 5: Berdasarkan Kebutuhan Sumber Daya (Resources)
    else:
        if estimated_resources >= 2 or risk_boost >= 2:
            level = 3
            # Cek Danger Zone Vitals untuk up-triage ESI 3 ke 2
            if (hr is not None and (hr > thresholds["hr_high"] or hr < thresholds["hr_low"])) or \
               (rr is not None and (rr > thresholds["rr_high"] or rr < thresholds["rr_low"])) or \
               risk_boost >= 3:
                level = 2
                evidence.append(f"Pasien ESI 3 di-up-triage ke ESI 2 karena tanda vital tidak stabil atau risiko tinggi (boost: {risk_boost})")
        elif estimated_resources == 1 or risk_boost == 1:
            level = 4
        else:
            level = 5

    # 7. Finalisasi Hasil
    ambulance_now = level in (1, 2)

    if level == 1:
        urgency_text = "Ambulans / IGD SEGERA. Prioritas Resusitasi."
        action_lines = [
            "Hubungi ambulans atau bawa ke IGD rumah sakit terdekat SEKARANG.",
            "Pastikan jalan napas pasien terbuka.",
            "Siapkan data medis pasien untuk diserahkan ke tenaga medis."
        ]
        summary = "Pasien dalam kondisi kritis yang mengancam nyawa."
    elif level == 2:
        urgency_text = "Segera ke IGD / Fasilitas Kesehatan. Risiko Tinggi."
        action_lines = [
            "Bawa pasien ke IGD terdekat tanpa penundaan.",
            "Jangan berikan makanan/minuman jika pasien tidak sadar penuh atau dicurigai butuh operasi.",
            "Pantau kesadaran dan napas secara ketat selama perjalanan."
        ]
        summary = "Pasien berisiko mengalami perburukan cepat."
    elif level == 3:
        urgency_text = "Perlu evaluasi klinis segera (Poliklinik Urgent / IGD)."
        action_lines = [
            "Segera periksakan ke klinik atau IGD terdekat.",
            "Bila keluhan memburuk mendadak (misal jadi sesak napas), segera hubungi layanan darurat."
        ]
        summary = "Pasien butuh evaluasi diagnostik (Lab/Radiologi) dalam waktu dekat."
    elif level == 4:
        urgency_text = "Evaluasi terjadwal (Poliklinik/Klinik)."
        action_lines = [
            "Lakukan pemeriksaan ke dokter poliklinik atau fasilitas primer.",
            "Bisa melakukan telekonsultasi dengan dokter umum terlebih dahulu."
        ]
        summary = "Kondisi cenderung stabil, butuh pemeriksaan ringan."
    else:
        urgency_text = "Perawatan mandiri / Observasi."
        action_lines = [
            "Istirahat cukup dan monitor gejala di rumah.",
            "Minum obat bebas yang sesuai gejala (jika tidak ada alergi).",
            "Hubungi dokter jika tidak membaik dalam beberapa hari."
        ]
        summary = "Pasien stabil, tidak memerlukan tindakan diagnostik khusus saat ini."

    if not evidence:
        evidence.append("Tidak terdeteksi parameter yang memicu peringatan khusus.")

    score = max(1, 6 - level)

    return TriageResult(
        level=level,
        label=TRIAGE_LABELS[level],
        emoji=TRIAGE_COLORS_HINT[level],
        score=score,
        urgency_text=urgency_text,
        summary=summary,
        recommended_action=" ".join(action_lines),
        ambulance_now=ambulance_now,
        red_flags=list(set(red_flags + esi_1_symptoms)), # Gabungkan semua red flags unik
        estimated_resources=estimated_resources,
        evidence=evidence,
    )






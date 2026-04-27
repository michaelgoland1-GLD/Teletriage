"""
Clinical syndrome detection layer for production-grade triage.
Replaces direct symptom-to-triage mapping with syndrome-based reasoning.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from clinical_scoring import calculate_qsofa, calculate_wells, calculate_heart_score

@dataclass
class SyndromeResult:
    """Clinical syndrome detection result."""
    name: str
    score: float
    reasons: List[str]
    explanation: str = ""  # Explainable AI: why this diagnosis was chosen
    
    def __str__(self):
        return f"{self.name} (score: {self.score:.2f})"

def detect_syndromes(data: Dict[str, Any]) -> List[SyndromeResult]:
    """
    Detect clinical syndromes from patient data.
    Returns sorted list by confidence score (highest first).
    """
    syndromes = []
    
    symptoms = [s.lower() for s in data.get("symptoms", [])]
    risk_factors = [r.lower() for r in data.get("risk_factors", [])]
    medications = [m.lower() for m in data.get("medications", [])]
    past_history = [h.lower() for h in data.get("past_medical_history", [])]
    
    # Extract vitals safely
    heart_rate = _safe_int(data.get("heart_rate"))
    blood_pressure = str(data.get("blood_pressure", "")).lower()
    
    # --- ACUTE CORONARY SYNDROME (ACS) - Dynamic Scoring ---
    acs_symptoms = ["nyeri dada", "nyeri dada berat", "nyeri dada menyebar", 
                    "nyeri dada seperti ditindih", "nyeri epigastrium", "nyeri ulu hati"]
    acs_risks = ["diabetes", "riwayat penyakit jantung", "hipertensi", "kolesterol tinggi"]
    
    if (any(sym in symptoms for sym in acs_symptoms) and 
        any(risk in risk_factors for risk in acs_risks)):
        reasons = []
        
        # Count symptom matches
        symptom_count = sum(1 for sym in acs_symptoms if sym in symptoms)
        if symptom_count >= 1:
            reasons.append("chest pain symptoms")
        
        # Count risk factors
        risk_count = sum(1 for risk in acs_risks if risk in risk_factors)
        if risk_count >= 1:
            reasons.append("cardiac risk factors")
        
        # Dynamic confidence: base 0.60 + symptom strength + risk factors
        acs_confidence = 0.60
        acs_confidence += min(0.20, symptom_count * 0.10)  # Max 0.20 from symptoms
        acs_confidence += min(0.15, risk_count * 0.05)  # Max 0.15 from risks
        
        # Boost for severe symptoms
        if "nyeri dada berat" in symptoms or "nyeri dada seperti ditindih" in symptoms:
            acs_confidence += 0.10
        
        # Boost with HEART score
        heart_score, heart_interp = calculate_heart_score(data)
        if heart_score >= 7:
            acs_confidence = min(0.98, acs_confidence + 0.10)
            reasons.append("high HEART score")
        elif heart_score >= 4:
            acs_confidence = min(0.95, acs_confidence + 0.05)
            reasons.append("moderate HEART score")
        
        # Generate explanation
        explanation = f"ACS dipilih karena pasien memiliki gejala nyeri dada (count: {symptom_count}) dan faktor risiko kardiovaskular (count: {risk_count}). "
        if heart_score >= 7:
            explanation += f"HEART score tinggi ({heart_score}) memperkuat diagnosis ACS. "
        elif heart_score >= 4:
            explanation += f"HEART score sedang ({heart_score}) mendukung diagnosis ACS. "
        explanation += f"Confidence {acs_confidence:.2f} berdasarkan kombinasi gejala, risiko, dan skor klinis."
        
        syndromes.append(SyndromeResult(
            "ACS", 
            min(0.98, acs_confidence),  # Cap at 0.98
            reasons,
            explanation
        ))
    
    # --- SEPSIS (qSOFA-based) ---
    # qSOFA criteria: Altered mental status, RR >= 22, SBP <= 100
    sepsis_mental = ["bingung", "kebingungan", "perubahan perilaku", "delirium", 
                     "tidak sadar", "disorientasi"]
    sepsis_resp = ["napas cepat", "napas pendek", "sesak napas", "bernafas cepat"]
    sepsis_infection_sources = [
        "infeksi", "luka terbuka", "operasi baru", "imunokompromais",
        "infeksi saluran kemih", "infeksi paru", "pneumonia", "infeksi kulit",
        "luka operasi", "kanker", "kemoterapi", "dialisis"
    ]
    
    sepsis_qsofa_score = 0
    sepsis_reasons = []
    
    # qSOFA 1: Altered mental status
    if any(sym in symptoms for sym in sepsis_mental):
        sepsis_qsofa_score += 1
        sepsis_reasons.append("altered mental status")
    
    # qSOFA 2: Respiratory rate >= 22 (proxy: rapid breathing symptoms)
    if any(sym in symptoms for sym in sepsis_resp):
        sepsis_qsofa_score += 1
        sepsis_reasons.append("rapid breathing")
    
    # qSOFA 3: Systolic BP <= 100
    bp_systolic = _safe_int(blood_pressure.split("/")[0]) if "/" in blood_pressure else None
    if bp_systolic and bp_systolic <= 100:
        sepsis_qsofa_score += 1
        sepsis_reasons.append("hypotension")
    
    # Heart rate > 100 (additional sepsis indicator)
    if heart_rate and heart_rate > 100:
        sepsis_qsofa_score += 1
        sepsis_reasons.append("tachycardia")
    
    # Fever or hypothermia
    if any(sym in symptoms for sym in ["demam tinggi", "menggigil", "demam"]):
        sepsis_qsofa_score += 1
        sepsis_reasons.append("fever")
    
    # Infection source must be present
    infection_source = any(risk in risk_factors for risk in sepsis_infection_sources)
    if infection_source:
        sepsis_reasons.append("infection source")
    
    # Calculate sepsis confidence based on qSOFA + infection source
    if sepsis_qsofa_score >= 2 and infection_source:
        # High confidence sepsis
        sepsis_confidence = 0.85 + (sepsis_qsofa_score - 2) * 0.05
        sepsis_confidence = min(0.95, sepsis_confidence)
        
        # Boost with clinical qSOFA score
        qsofa_score, qsofa_interp = calculate_qsofa(data)
        if qsofa_score >= 2:
            sepsis_confidence = min(0.98, sepsis_confidence + 0.05)
            sepsis_reasons.append("high qSOFA score")
        
        # Generate explanation
        explanation = f"Sepsis dipilih karena qSOFA score {sepsis_qsofa_score} (>=2) dengan sumber infeksi terdeteksi. "
        if qsofa_score >= 2:
            explanation += f"qSOFA klinis tinggi ({qsofa_score}) memperkuat diagnosis sepsis. "
        explanation += f"Confidence {sepsis_confidence:.2f} berdasarkan kriteria qSOFA dan sumber infeksi."
        
        syndromes.append(SyndromeResult(
            "Sepsis", 
            sepsis_confidence, 
            sepsis_reasons,
            explanation
        ))
    elif sepsis_qsofa_score >= 1 and infection_source:
        # Possible sepsis - lower confidence
        explanation = f"Possible Sepsis dipertimbangkan karena qSOFA score {sepsis_qsofa_score} dengan sumber infeksi. Confidence 0.65 (sedang)."
        
        syndromes.append(SyndromeResult(
            "Possible Sepsis", 
            0.65, 
            sepsis_reasons,
            explanation
        ))
    
    # --- PULMONARY EMBOLISM (PE) - Dynamic Scoring ---
    pe_symptoms = ["sesak napas mendadak", "sesak napas berat", "nyeri dada pleuritik", 
                  "nyeri dada saat bernapas", "batuk darah", "hemoptisis"]
    pe_risks = ["obesitas", "immobilisasi", "operasi besar", "kontrasepsi oral", 
                "riwayat pembekuan darah", "kanker"]
    
    if (any(sym in symptoms for sym in pe_symptoms) and 
        any(risk in risk_factors for risk in pe_risks)):
        reasons = []
        
        symptom_count = sum(1 for sym in pe_symptoms if sym in symptoms)
        if "sesak napas" in " ".join(symptoms):
            reasons.append("acute dyspnea")
        if any(sym in symptoms for sym in ["nyeri dada pleuritik", "nyeri dada saat bernapas"]):
            reasons.append("pleuritic chest pain")
        
        risk_count = sum(1 for risk in pe_risks if risk in risk_factors)
        if risk_count >= 1:
            reasons.append("PE risk factors")
        
        # Dynamic confidence
        pe_confidence = 0.55
        pe_confidence += min(0.25, symptom_count * 0.08)
        pe_confidence += min(0.15, risk_count * 0.05)
        
        # Boost for critical symptoms
        if "batuk darah" in symptoms or "hemoptisis" in symptoms:
            pe_confidence += 0.10
        
        # Boost with Wells score
        wells_score, wells_interp = calculate_wells(data)
        if wells_score >= 4:
            pe_confidence = min(0.95, pe_confidence + 0.10)
            reasons.append("high Wells score")
        elif wells_score >= 2:
            pe_confidence = min(0.90, pe_confidence + 0.05)
            reasons.append("moderate Wells score")
        
        # Generate explanation
        explanation = f"Pulmonary Embolism dipilih karena gejala sesak napas mendadak (count: {symptom_count}) dan faktor risiko PE (count: {risk_count}). "
        if wells_score >= 4:
            explanation += f"Wells score tinggi ({wells_score}) memperkuat diagnosis PE. "
        elif wells_score >= 2:
            explanation += f"Wells score sedang ({wells_score}) mendukung diagnosis PE. "
        explanation += f"Confidence {pe_confidence:.2f} berdasarkan kombinasi gejala, risiko, dan skor Wells."
        
        syndromes.append(SyndromeResult(
            "Pulmonary Embolism", 
            min(0.95, pe_confidence),
            reasons,
            explanation
        ))
    
    # --- ECTOPIC PREGNANCY - Dynamic Scoring ---
    if data.get("sex", "").lower() == "perempuan":
        ectopic_symptoms = ["nyeri perut bagian bawah", "nyeri perut satu sisi", 
                          "perdarahan vagina", "spotting", "pingsan", "syok"]
        ectopic_risks = ["hamil", "telat haid", "riwayat kehamilan ektopik", 
                       "kb spiral", "infeksi pelvik"]
        
        if (any(sym in symptoms for sym in ectopic_symptoms) and 
            any(risk in risk_factors for risk in ectopic_risks)):
            reasons = []
            
            symptom_count = sum(1 for sym in ectopic_symptoms if sym in symptoms)
            if any(sym in symptoms for sym in ["nyeri perut bagian bawah", "nyeri perut satu sisi"]):
                reasons.append("lower abdominal pain")
            if any(sym in symptoms for sym in ["perdarahan vagina", "spotting"]):
                reasons.append("vaginal bleeding")
            
            risk_count = sum(1 for risk in ectopic_risks if risk in risk_factors)
            if any(risk in risk_factors for risk in ["hamil", "telat haid"]):
                reasons.append("pregnancy status")
            
            # Dynamic confidence
            ectopic_confidence = 0.70
            ectopic_confidence += min(0.20, symptom_count * 0.07)
            ectopic_confidence += min(0.10, risk_count * 0.05)
            
            # Boost for critical symptoms
            if "pingsan" in symptoms or "syok" in symptoms:
                ectopic_confidence += 0.15
            
            # Generate explanation
            explanation = f"Ectopic Pregnancy dipilih karena nyeri perut bawah (count: {symptom_count}) dan status kehamilan. "
            if "pingsan" in symptoms or "syok" in symptoms:
                explanation += "Gejala kritis (pingsan/syok) meningkatkan kecurigaan. "
            explanation += f"Confidence {ectopic_confidence:.2f} berdasarkan gejala obstetri dan risiko."
            
            syndromes.append(SyndromeResult(
                "Ectopic Pregnancy", 
                min(0.95, ectopic_confidence),
                reasons,
                explanation
            ))
    
    # --- DIABETIC KETOACIDOSIS (DKA) - Dynamic Scoring ---
    dka_symptoms = ["muntah berulang", "mual hebat", "nyeri perut", 
                   "napas cepat", "napas dalam", "bau aseton napas", "dehidrasi"]
    dka_medications = ["insulin", "metformin", "glibenklamid", "glimepiride"]
    dka_risks = ["diabetes", "diabetes tipe 1", "diabetes tipe 2"]
    
    if (any(sym in symptoms for sym in dka_symptoms) and 
        any(risk in risk_factors for risk in dka_risks)):
        reasons = []
        
        symptom_count = sum(1 for sym in dka_symptoms if sym in symptoms)
        if any(sym in symptoms for sym in ["muntah berulang", "mual hebat"]):
            reasons.append("GI symptoms")
        if any(sym in symptoms for sym in ["napas cepat", "napas dalam"]):
            reasons.append("kussmaul breathing")
        
        risk_count = sum(1 for risk in dka_risks if risk in risk_factors)
        if any(risk in risk_factors for risk in dka_risks):
            reasons.append("diabetes history")
        
        # Dynamic confidence
        dka_confidence = 0.65
        dka_confidence += min(0.20, symptom_count * 0.07)
        dka_confidence += min(0.10, risk_count * 0.05)
        
        # Boost for classic DKA signs
        if "bau aseton napas" in symptoms:
            dka_confidence += 0.10
        if any(med in medications for med in dka_medications):
            dka_confidence += 0.05
        
        # Generate explanation
        explanation = f"DKA dipilih karena gejala metabolik (count: {symptom_count}) dan riwayat diabetes. "
        if "bau aseton napas" in symptoms:
            explanation += "Bau aseton napas (tanda klasik DKA) terdeteksi. "
        explanation += f"Confidence {dka_confidence:.2f} berdasarkan gejala DKA dan riwayat diabetes."
        
        syndromes.append(SyndromeResult(
            "DKA", 
            min(0.90, dka_confidence),
            reasons,
            explanation
        ))
    
    # --- STROKE - Dynamic Scoring ---
    stroke_symptoms = ["lemah satu sisi", "lemah tangan", "lemah kaki", "wajah mencong", 
                      "bicara pelo", "sulit bicara", "penglihatan ganda", "pusing berat"]
    stroke_risks = ["hipertensi", "diabetes", "riwayat stroke", "fibrilasi atrial", 
                   "merokok", "obesitas"]
    
    if (any(sym in symptoms for sym in stroke_symptoms) and 
        any(risk in risk_factors for risk in stroke_risks)):
        reasons = []
        
        symptom_count = sum(1 for sym in stroke_symptoms if sym in symptoms)
        if any(sym in symptoms for sym in ["lemah satu sisi", "lemah tangan", "lemah kaki"]):
            reasons.append("focal weakness")
        if any(sym in symptoms for sym in ["wajah mencong", "bicara pelo", "sulit bicara"]):
            reasons.append("facial droop/speech changes")
        
        risk_count = sum(1 for risk in stroke_risks if risk in risk_factors)
        if risk_count >= 1:
            reasons.append("stroke risk factors")
        
        # Dynamic confidence
        stroke_confidence = 0.60
        stroke_confidence += min(0.25, symptom_count * 0.08)
        stroke_confidence += min(0.15, risk_count * 0.05)
        
        # Boost for classic FAST symptoms
        if any(sym in symptoms for sym in ["wajah mencong", "bicara pelo", "sulit bicara"]):
            stroke_confidence += 0.10
        
        # Generate explanation
        explanation = f"Stroke dipilih karena gejala neurologis fokal (count: {symptom_count}) dan faktor risiko vaskular (count: {risk_count}). "
        if any(sym in symptoms for sym in ["wajah mencong", "bicara pelo", "sulit bicara"]):
            explanation += "Gejala FAST positif terdeteksi. "
        explanation += f"Confidence {stroke_confidence:.2f} berdasarkan gejala stroke dan risiko vaskular."
        
        syndromes.append(SyndromeResult(
            "Stroke", 
            min(0.90, stroke_confidence),
            reasons,
            explanation
        ))
    
    # --- APPENDICITIS (Pattern-Based) ---
    # Classic pattern: RLQ pain + migration + systemic symptoms
    appendicitis_pattern = [
        "nyeri perut kanan bawah", "nyeri perut sekitar pusar lalu pindah kanan bawah",
        "nyeri perut memburuk saat batuk", "nyeri perut saat bergerak"
    ]
    appendicitis_systemic = ["demam", "mual", "muntah", "nafsu makan hilang", "lemah"]
    
    appendicitis_score = 0.0
    appendicitis_reasons = []
    
    # Check for classic RLQ pain (required)
    if "nyeri perut kanan bawah" in " ".join(symptoms):
        appendicitis_score += 0.4
        appendicitis_reasons.append("RLQ pain")
    
    # Check for pain migration (strong indicator)
    if any(sym in symptoms for sym in ["nyeri perut sekitar pusar lalu pindah kanan bawah", 
                                          "nyeri perut pindah ke kanan bawah"]):
        appendicitis_score += 0.3
        appendicitis_reasons.append("pain migration")
    
    # Check for systemic symptoms
    systemic_count = sum(1 for sym in appendicitis_systemic if sym in symptoms)
    if systemic_count >= 2:
        appendicitis_score += 0.2
        appendicitis_reasons.append("systemic inflammation")
    
    # Check for rebound tenderness equivalent
    if any(sym in symptoms for sym in ["nyeri perut saat ditekan", "nyeri perut saat dilepas"]):
        appendicitis_score += 0.1
        appendicitis_reasons.append("peritoneal signs")
    
    if appendicitis_score >= 0.5:
        # Generate explanation
        explanation = f"Appendicitis dipilih karena pola nyeri perut kanan bawah (score: {appendicitis_score:.2f}). "
        if "nyeri perut sekitar pusar lalu pindah kanan bawah" in " ".join(symptoms):
            explanation += "Migrasi nyeri dari pusar ke kanan bawah terdeteksi (tanda klasik). "
        if systemic_count >= 2:
            explanation += f"Gejala sistemik ({systemic_count} tanda) mendukung diagnosis. "
        explanation += f"Confidence {min(0.85, appendicitis_score):.2f} berdasarkan pola klinis appendicitis."
        
        syndromes.append(SyndromeResult(
            "Appendicitis", 
            min(0.85, appendicitis_score),  # Cap at 0.85
            appendicitis_reasons,
            explanation
        ))
    
    # --- CHOLECYSTITIS (Pattern-Based) ---
    cholecystitis_pattern = [
        "nyeri perut kanan atas", "nyeri perut sebelah kanan atas",
        "nyeri perut setelah makan berlemak", "nyeri perut setelah makan"
    ]
    cholecystitis_systemic = ["demam", "mual", "muntah", "kuning", "kulit kuning"]
    
    cholecystitis_score = 0.0
    cholecystitis_reasons = []
    
    if any(sym in symptoms for sym in cholecystitis_pattern):
        cholecystitis_score += 0.4
        cholecystitis_reasons.append("RUQ pain")
    
    if any(sym in symptoms for sym in ["nyeri perut setelah makan berlemak", 
                                          "nyeri perut setelah makan"]):
        cholecystitis_score += 0.3
        cholecystitis_reasons.append("postprandial pain")
    
    if any(sym in symptoms for sym in ["kuning", "kulit kuning", "mata kuning"]):
        cholecystitis_score += 0.2
        cholecystitis_reasons.append("jaundice")
    
    if any(sym in symptoms for sym in cholecystitis_systemic):
        cholecystitis_score += 0.1
        cholecystitis_reasons.append("systemic symptoms")
    
    if cholecystitis_score >= 0.5:
        # Generate explanation
        explanation = f"Cholecystitis dipilih karena nyeri perut kanan atas (score: {cholecystitis_score:.2f}). "
        if any(sym in symptoms for sym in ["nyeri perut setelah makan berlemak", "nyeri perut setelah makan"]):
            explanation += "Nyeri postprandial terdeteksi (tanda klasik). "
        if any(sym in symptoms for sym in ["kuning", "kulit kuning", "mata kuning"]):
            explanation += "Jaundice terdeteksi (tanda komplikasi). "
        explanation += f"Confidence {min(0.80, cholecystitis_score):.2f} berdasarkan pola klinis cholecystitis."
        
        syndromes.append(SyndromeResult(
            "Cholecystitis", 
            min(0.80, cholecystitis_score),
            cholecystitis_reasons,
            explanation
        ))
    
    # --- PERFORATED ULCER (Pattern-Based) ---
    ulcer_pattern = [
        "nyeri perut mendadak hebat", "nyeri perut seperti ditusuk",
        "perut kaku", "perut papan", "nyeri perut seluruh perut"
    ]
    
    if any(sym in symptoms for sym in ulcer_pattern):
        ulcer_score = 0.7
        ulcer_reasons = ["acute abdominal pain"]
        
        if any(sym in symptoms for sym in ["perut kaku", "perut papan"]):
            ulcer_score += 0.2
            ulcer_reasons.append("abdominal rigidity")
        
        if any(sym in symptoms for sym in ["riwayat maag", "riwayat tukak lambung"]):
            ulcer_score += 0.1
            ulcer_reasons.append("ulcer history")
        
        # Generate explanation
        explanation = f"Perforated Ulcer dipilih karena nyeri perut mendadak hebat (score: {ulcer_score:.2f}). "
        if any(sym in symptoms for sym in ["perut kaku", "perut papan"]):
            explanation += "Rigidity abdominal terdeteksi (tanda perforasi). "
        if any(sym in symptoms for sym in ["riwayat maag", "riwayat tukak lambung"]):
            explanation += "Riwayat ulcer terdeteksi. "
        explanation += f"Confidence {min(0.95, ulcer_score):.2f} berdasarkan tanda perforasi viscus."
        
        syndromes.append(SyndromeResult(
            "Perforated Ulcer", 
            min(0.95, ulcer_score),
            ulcer_reasons,
            explanation
        ))
    
    # Return sorted by confidence score (highest first)
    return sorted(syndromes, key=lambda x: x.score, reverse=True)

def _safe_int(value: Any) -> int:
    """Safely convert value to int, return None if invalid."""
    try:
        if value is None or value == "":
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

# Test cases for validation
if __name__ == "__main__":
    # Test ACS case
    acs_case = {
        "symptoms": ["nyeri dada berat"],
        "risk_factors": ["diabetes", "hipertensi"],
        "medications": ["aspirin"],
        "past_medical_history": [],
        "heart_rate": 95,
        "blood_pressure": "140/90",
        "sex": "laki-laki"
    }
    
    # Test Ectopic case
    ectopic_case = {
        "symptoms": ["nyeri perut bagian bawah", "spotting"],
        "risk_factors": ["hamil"],
        "medications": [],
        "past_medical_history": [],
        "heart_rate": 100,
        "blood_pressure": "110/70",
        "sex": "perempuan"
    }
    
    # Test Sepsis case
    sepsis_case = {
        "symptoms": ["bingung", "demam tinggi"],
        "risk_factors": ["infeksi"],
        "medications": [],
        "past_medical_history": [],
        "heart_rate": 120,
        "blood_pressure": "90/60",
        "sex": "laki-laki"
    }
    
    print("=== SYNDROME ENGINE TEST RESULTS ===")
    for i, (case, name) in enumerate([(acs_case, "ACS"), (ectopic_case, "Ectopic"), (sepsis_case, "Sepsis")]):
        print(f"\n{name} Case:")
        syndromes = detect_syndromes(case)
        for syndrome in syndromes:
            print(f"  - {syndrome.name}: {syndrome.score:.2f} ({', '.join(syndrome.reasons)})")

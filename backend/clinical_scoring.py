"""
Clinical scoring engine for triage decision support.
Calculates validated clinical scores from existing patient data.
"""

from typing import Dict, Any, Tuple

def _safe_int(value: Any) -> int:
    """Safely convert value to int, return None if invalid."""
    try:
        if value is None or value == "":
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

def calculate_qsofa(data: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate qSOFA score for sepsis screening.
    qSOFA criteria (each = 1 point):
    1. Respiratory rate ≥ 22 breaths/min (proxy: rapid breathing symptoms)
    2. Altered mental status (GCS < 15 or confusion symptoms)
    3. Systolic blood pressure ≤ 100 mmHg
    
    Returns: (score, interpretation)
    """
    score = 0
    
    # Extract data
    symptoms = [s.lower() for s in data.get("symptoms", [])]
    gcs = _safe_int(data.get("gcs"))
    blood_pressure = str(data.get("blood_pressure", "")).lower()
    
    # qSOFA 1: Respiratory rate ≥ 22 (proxy symptoms)
    rapid_breathing = ["napas cepat", "napas pendek", "sesak napas", "bernafas cepat", "takipnea"]
    if any(sym in symptoms for sym in rapid_breathing):
        score += 1
    
    # qSOFA 2: Altered mental status
    altered_mental = ["bingung", "kebingungan", "disorientasi", "tidak sadar", "delirium"]
    if gcs and gcs < 15:
        score += 1
    elif any(sym in symptoms for sym in altered_mental):
        score += 1
    
    # qSOFA 3: Systolic BP ≤ 100
    if "/" in blood_pressure:
        try:
            systolic = int(blood_pressure.split("/")[0])
            if systolic <= 100:
                score += 1
        except (ValueError, IndexError):
            pass
    
    # Interpretation
    if score >= 2:
        interpretation = "High risk of sepsis"
    elif score == 1:
        interpretation = "Moderate risk of sepsis"
    else:
        interpretation = "Low risk of sepsis"
    
    return score, interpretation

def calculate_wells(data: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate Wells Score for pulmonary embolism risk assessment.
    Wells criteria (each = 1 point unless noted):
    1. Clinical signs of DVT (leg swelling, pain)
    2. Heart rate > 100
    3. Immobilization or surgery in past 4 weeks
    4. Previously diagnosed DVT or PE
    5. Hemoptysis (coughing blood)
    6. Cancer (active or treated within 6 months)
    7. PE is as likely or more likely than alternative diagnosis (3 points)
    
    Returns: (score, interpretation)
    """
    score = 0
    
    # Extract data
    symptoms = [s.lower() for s in data.get("symptoms", [])]
    risk_factors = [r.lower() for r in data.get("risk_factors", [])]
    past_history = [h.lower() for h in data.get("past_medical_history", [])]
    heart_rate = _safe_int(data.get("heart_rate"))
    
    # Wells 1: Clinical signs of DVT
    dvt_signs = ["nyeri kaki", "bengkak kaki", "bengkak tungkai", "nyeri tungkai"]
    if any(sym in symptoms for sym in dvt_signs):
        score += 1
    
    # Wells 2: Heart rate > 100
    if heart_rate and heart_rate > 100:
        score += 1
    
    # Wells 3: Immobilization or surgery in past 4 weeks
    immobilization = ["immobilisasi", "operasi baru", "operasi besar", "bedah rest"]
    if any(risk in risk_factors for risk in immobilization):
        score += 1
    
    # Wells 4: Previously diagnosed DVT or PE
    thrombosis_history = ["riwayat pembekuan darah", "riwayat dvt", "riwayat pe", "deep vein thrombosis"]
    if any(hist in past_history for hist in thrombosis_history):
        score += 1
    
    # Wells 5: Hemoptysis
    hemoptysis = ["batuk darah", "hemoptisis", "darah saat batuk"]
    if any(sym in symptoms for sym in hemoptysis):
        score += 1
    
    # Wells 6: Cancer
    cancer = ["kanker", "malignancy", "tumor ganas"]
    if any(risk in risk_factors for risk in cancer) or any(hist in past_history for hist in cancer):
        score += 1
    
    # Wells 7: PE as likely or more likely than alternative (3 points)
    # This is clinical judgment - we'll use symptom pattern as proxy
    pe_pattern = ["sesak napas mendadak", "nyeri dada pleuritik", "nyeri dada saat bernapas"]
    if any(sym in symptoms for sym in pe_pattern):
        score += 3
    
    # Interpretation
    if score >= 7:
        interpretation = "High probability of PE"
    elif score >= 4:
        interpretation = "Moderate probability of PE"
    elif score >= 2:
        interpretation = "Low probability of PE"
    else:
        interpretation = "Unlikely PE"
    
    return score, interpretation

def calculate_heart_score(data: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate HEART Score for acute coronary syndrome risk assessment.
    HEART criteria (each = 0, 1, or 2 points):
    
    H - History (chest pain characteristics):
        0: Non-anginal pain
        1: Possibly anginal
        2: Clearly anginal
    
    E - ECG (electrocardiogram):
        0: Normal
        1: Non-specific repolarization disturbance
        2: Significant ST deviation
    
    A - Age:
        0: <45 years
        1: 45-64 years
        2: ≥65 years
    
    R - Risk factors:
        0: No risk factors
        1: 1-2 risk factors
        2: ≥3 risk factors or known atherosclerotic disease
    
    T - Troponin:
        0: Normal
        1: 1-3x upper limit of normal
        2: >3x upper limit of normal
    
    Returns: (score, interpretation)
    """
    score = 0
    
    # Extract data
    symptoms = [s.lower() for s in data.get("symptoms", [])]
    risk_factors = [r.lower() for r in data.get("risk_factors", [])]
    past_history = [h.lower() for h in data.get("past_medical_history", [])]
    age = _safe_int(data.get("age"))
    
    # H - History (chest pain characteristics)
    clearly_anginal = ["nyeri dada berat", "nyeri dada seperti ditindih", "nyeri dada menyebar"]
    possibly_anginal = ["nyeri dada", "nyeri dada ringan", "nyeri ulu hati", "nyeri epigastrium"]
    non_anginal = ["nyeri dada saat bernapas", "nyeri dada pleuritik", "nyeri dada saat ditekan"]
    
    if any(sym in symptoms for sym in clearly_anginal):
        score += 2
    elif any(sym in symptoms for sym in possibly_anginal):
        score += 1
    elif any(sym in symptoms for sym in non_anginal):
        score += 0
    elif "nyeri dada" in " ".join(symptoms):
        score += 1  # Default to possibly anginal if chest pain present
    
    # E - ECG (we don't have ECG data, assume normal = 0)
    # In real clinical setting, this would require ECG input
    score += 0
    
    # A - Age
    if age and age >= 65:
        score += 2
    elif age and age >= 45:
        score += 1
    else:
        score += 0
    
    # R - Risk factors
    cardiac_risks = ["diabetes", "hipertensi", "kolesterol tinggi", "riwayat penyakit jantung", 
                     "merokok", "obesitas", "family history heart disease"]
    atherosclerotic = ["riwayat penyakit jantung", "riwayat miokard infark", "riwayat stroke"]
    
    risk_count = sum(1 for risk in cardiac_risks if risk in risk_factors or risk in past_history)
    has_atherosclerotic = any(hist in past_history for hist in atherosclerotic)
    
    if has_atherosclerotic or risk_count >= 3:
        score += 2
    elif risk_count >= 1:
        score += 1
    else:
        score += 0
    
    # T - Troponin (we don't have troponin data, assume normal = 0)
    # In real clinical setting, this would require lab input
    score += 0
    
    # Interpretation
    if score >= 7:
        interpretation = "High risk of ACS"
    elif score >= 4:
        interpretation = "Moderate risk of ACS"
    else:
        interpretation = "Low risk of ACS"
    
    return score, interpretation

def get_clical_score_summary(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Calculate all clinical scores and return human-readable summaries.
    Used for internal decision support, not for user display.
    """
    qsofa_score, qsofa_interp = calculate_qsofa(data)
    wells_score, wells_interp = calculate_wells(data)
    heart_score, heart_interp = calculate_heart_score(data)
    
    return {
        "qsofa": qsofa_interp,
        "wells": wells_interp,
        "heart": heart_interp
    }

# Test cases for validation
if __name__ == "__main__":
    print("=== CLINICAL SCORING ENGINE TEST RESULTS ===")
    
    # Test Sepsis case
    sepsis_case = {
        "symptoms": ["bingung", "demam tinggi", "menggigil"],
        "risk_factors": ["infeksi", "diabetes"],
        "medications": [],
        "past_medical_history": [],
        "heart_rate": 115,
        "blood_pressure": "90/60",
        "spo2": 92,
        "gcs": 13,
        "sex": "perempuan",
        "age": 75
    }
    
    # Test PE case
    pe_case = {
        "symptoms": ["sesak napas mendadak", "nyeri dada pleuritik"],
        "risk_factors": ["obesitas", "kontrasepsi oral"],
        "medications": ["pil kb"],
        "past_medical_history": [],
        "heart_rate": 110,
        "blood_pressure": "100/65",
        "spo2": 89,
        "gcs": 15,
        "sex": "perempuan",
        "age": 35
    }
    
    # Test ACS case
    acs_case = {
        "symptoms": ["nyeri dada berat", "mual"],
        "risk_factors": ["diabetes", "hipertensi", "riwayat penyakit jantung"],
        "medications": ["aspirin", "metformin"],
        "past_medical_history": ["diabetes tipe 2"],
        "heart_rate": 95,
        "blood_pressure": "140/90",
        "spo2": 98,
        "gcs": 15,
        "sex": "laki-laki",
        "age": 65
    }
    
    for case, name in [(sepsis_case, "Sepsis"), (pe_case, "PE"), (acs_case, "ACS")]:
        print(f"\n{name} Case:")
        scores = get_clical_score_summary(case)
        print(f"  qSOFA: {scores['qsofa']}")
        print(f"  Wells: {scores['wells']}")
        print(f"  HEART: {scores['heart']}")

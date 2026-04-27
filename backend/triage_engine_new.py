"""
Production-grade triage engine with syndrome-based clinical reasoning.
Replaces fuzzy matching with clinical logic and safety guardrails.
"""

from typing import Dict, Any, List
from dataclasses import dataclass

from text_matching import check_symptom_list, check_medical_terms
from syndrome_engine import detect_syndromes, SyndromeResult
from medication_rules import detect_medication_risks, has_high_risk_medications
from treatment_engine import generate_action_plan
from clinical_scoring import calculate_qsofa, calculate_wells, calculate_heart_score

@dataclass
class TriageResult:
    """Production-grade triage result with multi-diagnosis support."""
    triage_level: str
    action: str
    syndrome: str = None
    confidence: float = 0.0
    reasons: List[str] = None
    specialist: str = None
    ambulance_required: bool = False
    medication_warnings: List[str] = None
    action_plan: Dict[str, Any] = None
    explanation: str = ""  # Explainable AI: why this triage decision was made
    differential_diagnosis: List[str] = None  # Top 3 syndromes
    rule_out: List[str] = None  # Syndromes to rule out
    data_completeness: str = "Lengkap"  # Data completeness status
    data_recommendations: List[str] = None  # Recommended additional data
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
        if self.medication_warnings is None:
            self.medication_warnings = []
        if self.action_plan is None:
            self.action_plan = {}
        if self.differential_diagnosis is None:
            self.differential_diagnosis = []
        if self.rule_out is None:
            self.rule_out = []
        if self.data_recommendations is None:
            self.data_recommendations = []

def emergency_guardrail(data: Dict[str, Any]) -> bool:
    """
    Safety guardrail - force EMERGENCY for critical vital signs.
    """
    # Check blood pressure for hypertensive crisis
    bp = str(data.get("blood_pressure", "")).lower()
    if "190/" in bp or "200/" in bp or "180/" in bp:
        return True
    
    # Check heart rate for extreme tachycardia/bradycardia
    hr = _safe_int(data.get("heart_rate"))
    if hr and (hr > 130 or hr < 40):
        return True
    
    # Check oxygen saturation
    spo2 = _safe_int(data.get("spo2"))
    if spo2 and spo2 < 85:
        return True
    
    # Check GCS for critical neurological impairment
    gcs = _safe_int(data.get("gcs"))
    if gcs and gcs <= 8:
        return True
    
    # Check for critical symptoms
    critical_symptoms = ["pingsan", "henti napas", "henti jantung", "kejang sedang berlangsung"]
    symptoms = [s.lower() for s in data.get("symptoms", [])]
    
    if any(sym in " ".join(symptoms) for sym in critical_symptoms):
        return True
    
    return False

def map_specialist(syndrome: str) -> str:
    """
    Map syndrome to appropriate medical specialist.
    """
    specialist_mapping = {
        "ACS": "Cardiology / Sp.JP",
        "Sepsis": "Internal Medicine / Sp.PD", 
        "Possible Sepsis": "Internal Medicine / Sp.PD",
        "Pulmonary Embolism": "Pulmonology / Sp.P",
        "Ectopic Pregnancy": "OB-GYN / Sp.OG",
        "DKA": "Internal Medicine / Endocrinology",
        "Stroke": "Neurology / Sp.S",
        "Appendicitis": "General Surgery / Sp.B",
        "Cholecystitis": "General Surgery / Sp.B",
        "Perforated Ulcer": "General Surgery / Sp.B",
        "Aortic Dissection": "Cardiology / Vascular Surgery",
        "Myocardial Infarction": "Cardiology / ICU"
    }
    
    return specialist_mapping.get(syndrome, "General Physician / Emergency Medicine")

def triage_engine(data: Dict[str, Any]) -> TriageResult:
    """
    Production-grade triage engine with syndrome-based reasoning and data-awareness.
    """
    
    # Step 0: Check data completeness
    data_check = check_data_completeness(data)
    
    # Step 1: Emergency guardrail check (bypass data penalty for critical cases)
    if emergency_guardrail(data):
        return TriageResult(
            triage_level="EMERGENCY",
            action="Immediate ED referral with ambulance",
            syndrome="Critical Vital Signs",
            confidence=1.0,
            reasons=["Critical vital signs or symptoms detected"],
            specialist="Emergency Medicine / ICU",
            ambulance_required=True,
            action_plan=generate_action_plan("Critical Vital Signs"),
            data_completeness=data_check['status'],
            data_recommendations=data_check['recommendations']
        )
    
    # Step 2: Detect syndromes
    syndromes = detect_syndromes(data)
    
    # Step 3: Handle no syndrome detected
    if not syndromes:
        # Check for general urgent symptoms
        symptoms = [s.lower() for s in data.get("symptoms", [])]
        urgent_symptoms = ["nyeri dada", "sesak napas", "pusing berat", "muntah berulang"]
        
        # Apply data awareness
        reasons = []
        if data_check['status'] != "Lengkap":
            reasons.append("Informasi masih terbatas")
        
        if any(sym in " ".join(symptoms) for sym in urgent_symptoms):
            reasons.append("Urgent symptoms but no clear syndrome")
            confidence = max(0.2, 0.4 - data_check['confidence_penalty'])
            return TriageResult(
                triage_level="URGENT", 
                action="Same-day medical evaluation",
                confidence=confidence,
                reasons=reasons,
                specialist="General Physician / Emergency Medicine",
                action_plan=generate_action_plan("Unknown Syndrome"),
                data_completeness=data_check['status'],
                data_recommendations=data_check['recommendations']
            )
        
        reasons.append("No clear syndrome or urgent symptoms")
        confidence = max(0.1, 0.3 - data_check['confidence_penalty'])
        return TriageResult(
            triage_level="NON-URGENT",
            action="Outpatient evaluation within 24-48 hours", 
            confidence=confidence,
            reasons=reasons,
            specialist="General Physician",
            action_plan=generate_action_plan("Unknown Syndrome"),
            data_completeness=data_check['status'],
            data_recommendations=data_check['recommendations']
        )
    
    # Step 4: Process top syndrome and multi-diagnosis
    top_syndrome = syndromes[0]
    
    # Multi-diagnosis: top 3 syndromes
    top_3_syndromes = syndromes[:3]
    differential_diagnosis = [s.name for s in top_3_syndromes]
    
    # Rule out: syndromes with very low confidence (< 0.3)
    rule_out = [s.name for s in syndromes if s.score < 0.3]
    
    # Step 4.5: Apply clinical scoring decision support
    # Calculate clinical scores
    qsofa_score, qsofa_interp = calculate_qsofa(data)
    wells_score, wells_interp = calculate_wells(data)
    heart_score, heart_interp = calculate_heart_score(data)
    
    # Decision support: prioritize syndromes with high clinical scores
    clinical_boost = 0.0
    clinical_reasons = []
    
    # qSOFA ≥ 2 → prioritize Sepsis
    if qsofa_score >= 2 and top_syndrome.name in ["Sepsis", "Possible Sepsis"]:
        clinical_boost += 0.05
        clinical_reasons.append("high qSOFA supports sepsis diagnosis")
    elif qsofa_score >= 2 and top_syndrome.name not in ["Sepsis", "Possible Sepsis"]:
        # High qSOFA but syndrome not sepsis - consider sepsis as alternative
        clinical_boost -= 0.02
        clinical_reasons.append("high qSOFA suggests sepsis consideration")
    
    # Wells Score high → prioritize PE
    if wells_score >= 4 and top_syndrome.name == "Pulmonary Embolism":
        clinical_boost += 0.05
        clinical_reasons.append("high Wells score supports PE diagnosis")
    elif wells_score >= 7 and top_syndrome.name != "Pulmonary Embolism":
        # Very high Wells but syndrome not PE - consider PE as alternative
        clinical_boost -= 0.02
        clinical_reasons.append("high Wells score suggests PE consideration")
    
    # HEART Score high → prioritize ACS
    if heart_score >= 7 and top_syndrome.name == "ACS":
        clinical_boost += 0.05
        clinical_reasons.append("high HEART score supports ACS diagnosis")
    elif heart_score >= 7 and top_syndrome.name != "ACS":
        # Very high HEART but syndrome not ACS - consider ACS as alternative
        clinical_boost -= 0.02
        clinical_reasons.append("high HEART score suggests ACS consideration")
    
    # Step 5: Determine triage level with clinical modifiers
    # Base triage level from syndrome score
    base_score = top_syndrome.score
    
    # Apply vital sign modifiers to prevent overtriage
    hr = _safe_int(data.get("heart_rate"))
    bp = str(data.get("blood_pressure", "")).lower()
    spo2 = _safe_int(data.get("spo2"))
    
    # Downgrade modifier: stable vitals for moderate syndromes
    vital_modifier = 0.0
    if base_score < 0.90:  # Only for moderate cases
        if hr and 60 <= hr <= 100 and spo2 and spo2 >= 95:
            # Normal HR and O2 - downgrade moderate cases
            vital_modifier = -0.10
    
    # Upgrade modifier: abnormal vitals for borderline cases
    if base_score >= 0.70 and base_score < 0.85:
        if hr and hr > 110 or (spo2 and spo2 < 92):
            # Abnormal vitals - upgrade borderline cases
            vital_modifier = 0.10
    
    adjusted_score = max(0.0, min(1.0, base_score + vital_modifier + clinical_boost))
    
    # Determine triage level with adjusted score
    if adjusted_score >= 0.90:
        triage_level = "EMERGENCY"
        action = "Immediate ED referral with ambulance"
        ambulance_required = True
    elif adjusted_score >= 0.70:
        triage_level = "URGENT" 
        action = "Same-day specialist referral"
        ambulance_required = False
    else:
        triage_level = "NON-URGENT"
        action = "Outpatient specialist referral"
        ambulance_required = False
    
    # Step 6: Get specialist recommendation
    specialist = map_specialist(top_syndrome.name)
    
    # Step 7: Generate action plan
    action_plan = generate_action_plan(top_syndrome.name)
    
    # Step 8: Check medication risks
    medications = data.get("medications", [])
    med_risks = detect_medication_risks(medications)
    med_warnings = []
    
    if med_risks.get("SGLT2"):
        med_warnings.append("SGLT2 inhibitor - monitor for euglycemic DKA")
    if med_risks.get("ANTICOAG"):
        med_warnings.append("Anticoagulant - increased bleeding risk")
    if med_risks.get("INSULIN"):
        med_warnings.append("Insulin - monitor for hypoglycemia")
    if med_risks.get("OCP"):
        med_warnings.append("Oral contraceptive - consider thromboembolic risk")
    
    # Step 8: Combine reasons
    all_reasons = top_syndrome.reasons.copy()
    all_reasons.extend(clinical_reasons)  # Add clinical scoring reasons
    if has_high_risk_medications(medications):
        all_reasons.append("High-risk medications detected")
    
    # Step 8.5: Apply data awareness
    if data_check['status'] != "Lengkap":
        all_reasons.append("Informasi masih terbatas")
    
    # Apply confidence penalty for incomplete data
    final_confidence = max(0.1, adjusted_score - data_check['confidence_penalty'])
    
    # Step 9: Generate explanation for triage decision
    explanation = f"Triage level {triage_level} ditentukan berdasarkan diagnosis utama {top_syndrome.name} dengan confidence {final_confidence:.2f}. "
    explanation += f"Diagnosis didukung oleh: {', '.join(top_syndrome.reasons)}. "
    if clinical_reasons:
        explanation += f"Skor klinis memperkuat diagnosis: {', '.join(clinical_reasons)}. "
    if len(differential_diagnosis) > 1:
        explanation += f"Diagnosis diferensial yang dipertimbangkan: {', '.join(differential_diagnosis[1:])}. "
    if rule_out:
        explanation += f"Diagnosis yang dapat di-rule out: {', '.join(rule_out)}. "
    if data_check['status'] != "Lengkap":
        explanation += f"Data pasien {data_check['status'].lower()} (completeness: {data_check['completeness_score']:.0%}). "
    explanation += f"Keputusan triage berdasarkan kombinasi gejala, faktor risiko, skor klinis (qSOFA/Wells/HEART), dan tanda vital."
    
    return TriageResult(
        triage_level=triage_level,
        action=action,
        syndrome=top_syndrome.name,
        confidence=final_confidence,  # Use final confidence with data awareness
        reasons=all_reasons,
        specialist=specialist,
        ambulance_required=ambulance_required,
        medication_warnings=med_warnings,
        action_plan=action_plan,
        explanation=explanation,
        differential_diagnosis=differential_diagnosis,
        rule_out=rule_out,
        data_completeness=data_check['status'],
        data_recommendations=data_check['recommendations']
    )

def _safe_int(value: Any) -> int:
    """Safely convert value to int, return None if invalid."""
    try:
        if value is None or value == "":
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

def check_data_completeness(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check data completeness and provide recommendations.
    Returns: {
        'completeness_score': float (0-1),
        'status': str ('Lengkap', 'Terbatas', 'Sangat Terbatas'),
        'recommendations': List[str],
        'confidence_penalty': float
    }
    """
    recommendations = []
    missing_count = 0
    total_checks = 0
    
    # Check symptoms (critical)
    symptoms = data.get("symptoms", [])
    total_checks += 1
    if not symptoms or len(symptoms) == 0:
        missing_count += 1
        recommendations.append("Sebutkan gejala yang Anda rasakan (contoh: nyeri dada, sesak napas, demam)")
    
    # Check vital signs (important)
    vital_signs = ["heart_rate", "blood_pressure", "spo2"]
    for vital in vital_signs:
        total_checks += 1
        if not data.get(vital):
            missing_count += 1
    if not data.get("heart_rate"):
        recommendations.append("Tambahkan detak jantung (bpm) untuk penilaian yang lebih akurat")
    if not data.get("blood_pressure"):
        recommendations.append("Tambahkan tekanan darah (contoh: 120/80)")
    if not data.get("spo2"):
        recommendations.append("Tambahkan kadar oksigen darah (%) untuk cek kesehatan paru")
    
    # Check risk factors (important)
    risk_factors = data.get("risk_factors", [])
    total_checks += 1
    if not risk_factors or len(risk_factors) == 0:
        missing_count += 1
        recommendations.append("Sebutkan faktor risiko (contoh: diabetes, hipertensi, merokok) untuk diagnosis lebih tepat")
    
    # Check age (moderately important)
    total_checks += 1
    if not data.get("age"):
        missing_count += 1
        recommendations.append("Tambahkan usia untuk penilaian risiko yang lebih akurat")
    
    # Check sex (moderately important)
    total_checks += 1
    if not data.get("sex"):
        missing_count += 1
        recommendations.append("Tambahkan jenis kelamin untuk diagnosis yang lebih spesifik")
    
    # Calculate completeness score
    completeness_score = 1.0 - (missing_count / total_checks) if total_checks > 0 else 0.0
    
    # Determine status
    if completeness_score >= 0.8:
        status = "Lengkap"
        confidence_penalty = 0.0
    elif completeness_score >= 0.5:
        status = "Terbatas"
        confidence_penalty = 0.10  # Reduce confidence by 10%
    else:
        status = "Sangat Terbatas"
        confidence_penalty = 0.20  # Reduce confidence by 20%
    
    return {
        'completeness_score': completeness_score,
        'status': status,
        'recommendations': recommendations,
        'confidence_penalty': confidence_penalty
    }

def get_triage_summary(result: TriageResult) -> str:
    """Get human-readable triage summary."""
    if result.triage_level == "EMERGENCY":
        return f"EMERGENCY - {result.syndrome or 'Critical Condition'} detected with {result.confidence:.0%} confidence"
    elif result.triage_level == "URGENT":
        return f"URGENT - {result.syndrome or 'Urgent Condition'} suspected with {result.confidence:.0%} confidence"
    else:
        return f"NON-URGENT - {result.syndrome or 'Routine Condition'} with {result.confidence:.0%} confidence"

# Test cases for validation
if __name__ == "__main__":
    # Test ACS case
    acs_case = {
        "symptoms": ["nyeri dada berat"],
        "risk_factors": ["diabetes", "hipertensi"],
        "medications": ["aspirin", "metformin"],
        "past_medical_history": ["riwayat penyakit jantung"],
        "heart_rate": 95,
        "blood_pressure": "140/90",
        "spo2": 98,
        "gcs": 15,
        "sex": "laki-laki"
    }
    
    # Test Ectopic case
    ectopic_case = {
        "symptoms": ["nyeri perut bagian bawah", "spotting"],
        "risk_factors": ["hamil"],
        "medications": ["pil kb"],
        "past_medical_history": [],
        "heart_rate": 100,
        "blood_pressure": "110/70", 
        "spo2": 97,
        "gcs": 15,
        "sex": "perempuan"
    }
    
    # Test Critical vitals (guardrail)
    critical_case = {
        "symptoms": ["pusing ringan"],
        "risk_factors": [],
        "medications": [],
        "past_medical_history": [],
        "heart_rate": 140,  # Should trigger guardrail
        "blood_pressure": "120/80",
        "spo2": 95,
        "gcs": 15,
        "sex": "laki-laki"
    }
    
    print("=== TRIAGE ENGINE TEST RESULTS ===")
    for i, (case, name) in enumerate([(acs_case, "ACS"), (ectopic_case, "Ectopic"), (critical_case, "Critical Vitals")]):
        print(f"\n{name} Case:")
        result = triage_engine(case)
        print(f"  Level: {result.triage_level}")
        print(f"  Syndrome: {result.syndrome}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Action: {result.action}")
        print(f"  Specialist: {result.specialist}")
        print(f"  Ambulance: {result.ambulance_required}")
        print(f"  Reasons: {', '.join(result.reasons)}")
        if result.medication_warnings:
            print(f"  Med Warnings: {', '.join(result.medication_warnings)}")

"""
Debug script to identify why sepsis case is failing.
"""

from triage_engine_new import emergency_guardrail, triage_engine

# Sepsis test case
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

print("=== DEBUGGING SEPSIS CASE ===")
print(f"Heart Rate: {sepsis_case['heart_rate']}")
print(f"Blood Pressure: {sepsis_case['blood_pressure']}")
print(f"SpO2: {sepsis_case['spo2']}")
print(f"GCS: {sepsis_case['gcs']}")

print("\n--- Guardrail Check ---")
guardrail_result = emergency_guardrail(sepsis_case)
print(f"Guardrail Triggered: {guardrail_result}")

print("\n--- Full Triage Engine ---")
triage_result = triage_engine(sepsis_case)
print(f"Syndrome: {triage_result.syndrome}")
print(f"Confidence: {triage_result.confidence}")
print(f"Action: {triage_result.action}")

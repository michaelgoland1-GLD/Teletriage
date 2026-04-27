"""
Medication risk detection for clinical triage.
Parses medications to identify high-risk drug categories.
"""

from typing import List, Dict, Set

# High-risk medication categories
SGLT2_LIST = [
    "empagliflozin", "dapagliflozin", "canagliflozin", "ertugliflozin",
    "jardiance", "farxiga", "invokana", "steglatro"
]

OCP_LIST = [
    "pil kb", "kontrasepsi oral", "oral contraceptive", "microgynon",
    "yasmin", "diane", "novinet", "lodrina"
]

ANTICOAG_LIST = [
    "warfarin", "coumadin", "heparin", "enoxaparin",
    "rivaroxaban", "xarelto", "apixaban", "eliquis",
    "dabigatran", "pradaxa"
]

INSULIN_LIST = [
    "insulin", "humalog", "novolog", "lantus", "levemir",
    "actrapid", "mixtard"
]

DIABETES_MEDS_LIST = [
    "metformin", "glimepiride", "glibenklamid", "pioglitazone",
    "sitagliptin", "vildagliptin", "linagliptin"
]

ANTIBIOTIC_LIST = [
    "amoxicillin", "azithromycin", "ciprofloxacin", "levofloxacin",
    "clindamycin", "vancomycin", "meropenem"
]

def detect_medication_risks(medications: List[str]) -> Dict[str, bool]:
    """
    Parse medication list to identify high-risk categories.
    Returns dictionary of risk flags.
    """
    if not medications:
        return {
            "SGLT2": False,
            "OCP": False,
            "ANTICOAG": False,
            "INSULIN": False,
            "DIABETES_MEDS": False,
            "ANTIBIOTIC": False
        }
    
    risk_flags = {
        "SGLT2": False,
        "OCP": False,
        "ANTICOAG": False,
        "INSULIN": False,
        "DIABETES_MEDS": False,
        "ANTIBIOTIC": False
    }
    
    # Convert all medications to lowercase for matching
    med_lower = [med.lower().strip() for med in medications]
    
    for med in med_lower:
        # Check SGLT2 inhibitors
        if any(sglt2 in med for sglt2 in SGLT2_LIST):
            risk_flags["SGLT2"] = True
        
        # Check oral contraceptives
        if any(ocp in med for ocp in OCP_LIST):
            risk_flags["OCP"] = True
        
        # Check anticoagulants
        if any(anticoag in med for anticoag in ANTICOAG_LIST):
            risk_flags["ANTICOAG"] = True
        
        # Check insulin
        if any(insulin in med for insulin in INSULIN_LIST):
            risk_flags["INSULIN"] = True
        
        # Check diabetes medications
        if any(dm in med for dm in DIABETES_MEDS_LIST):
            risk_flags["DIABETES_MEDS"] = True
        
        # Check antibiotics
        if any(abx in med for abx in ANTIBIOTIC_LIST):
            risk_flags["ANTIBIOTIC"] = True
    
    return risk_flags

def get_medication_categories(medications: List[str]) -> List[str]:
    """
    Get list of medication categories for a patient.
    """
    risk_flags = detect_medication_risks(medications)
    categories = []
    
    if risk_flags["SGLT2"]:
        categories.append("SGLT2 Inhibitor")
    if risk_flags["OCP"]:
        categories.append("Oral Contraceptive")
    if risk_flags["ANTICOAG"]:
        categories.append("Anticoagulant")
    if risk_flags["INSULIN"]:
        categories.append("Insulin")
    if risk_flags["DIABETES_MEDS"]:
        categories.append("Diabetes Medication")
    if risk_flags["ANTIBIOTIC"]:
        categories.append("Antibiotic")
    
    return categories

def has_high_risk_medications(medications: List[str]) -> bool:
    """
    Check if patient is on any high-risk medications.
    """
    risk_flags = detect_medication_risks(medications)
    return any([
        risk_flags["SGLT2"],
        risk_flags["ANTICOAG"],
        risk_flags["INSULIN"]
    ])

def get_medication_warnings(medications: List[str]) -> List[str]:
    """
    Get specific warnings for high-risk medications.
    """
    risk_flags = detect_medication_risks(medications)
    warnings = []
    
    if risk_flags["SGLT2"]:
        warnings.append("SGLT2 inhibitor - monitor for euglycemic DKA")
    
    if risk_flags["ANTICOAG"]:
        warnings.append("Anticoagulant - increased bleeding risk")
    
    if risk_flags["INSULIN"]:
        warnings.append("Insulin - monitor for hypoglycemia")
    
    if risk_flags["OCP"]:
        warnings.append("Oral contraceptive - consider thromboembolic risk")
    
    return warnings

# Test cases for validation
if __name__ == "__main__":
    test_cases = [
        {
            "name": "SGLT2 Patient",
            "medications": ["empagliflozin", "metformin"],
            "expected": {"SGLT2": True, "DIABETES_MEDS": True}
        },
        {
            "name": "OCP Patient", 
            "medications": ["pil kb", "vitamin c"],
            "expected": {"OCP": True}
        },
        {
            "name": "Anticoag Patient",
            "medications": ["warfarin", "aspirin"],
            "expected": {"ANTICOAG": True}
        },
        {
            "name": "No Meds",
            "medications": [],
            "expected": {"SGLT2": False, "OCP": False, "ANTICOAG": False}
        }
    ]
    
    print("=== MEDICATION RULES TEST RESULTS ===")
    for case in test_cases:
        print(f"\n{case['name']}: {case['medications']}")
        result = detect_medication_risks(case['medications'])
        
        # Check if expected keys match
        expected_keys = {k: v for k, v in case['expected'].items() if v}
        result_keys = {k: v for k, v in result.items() if v}
        
        status = "✅" if expected_keys == result_keys else "❌"
        print(f"  {status} Expected: {expected_keys}")
        print(f"  {status} Result: {result_keys}")
        
        # Show categories
        categories = get_medication_categories(case['medications'])
        if categories:
            print(f"  Categories: {', '.join(categories)}")
        
        # Show warnings
        warnings = get_medication_warnings(case['medications'])
        if warnings:
            print(f"  Warnings: {', '.join(warnings)}")

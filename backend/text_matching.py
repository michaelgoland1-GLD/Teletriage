"""
Production-grade text matching for clinical triage system.
Replaces fuzzy partial matching with exact phrase matching + negation handling.
"""

from typing import List

# Clinical negations that invalidate symptoms
NEGATIONS = [
    "tidak", "tanpa", "menyangkal", "bukan", "belum", 
    "gada", "ngga", "nggak", "enggak", "tak", "jangan",
    "no", "denies", "denied", "negative", "normal"
]

def normalize_text(text: str) -> str:
    """Normalize text for consistent matching."""
    if not text:
        return ""
    return text.lower().strip()

def contains_phrase(text: str, phrase: str) -> bool:
    """Check if phrase exists as complete term in text."""
    if not text or not phrase:
        return False
    
    # Add spaces to avoid partial word matches
    text_normalized = f" {normalize_text(text)} "
    phrase_normalized = f" {normalize_text(phrase)} "
    
    return phrase_normalized in text_normalized

def is_negated(text: str, symptom: str) -> bool:
    """Check if symptom is negated in the text."""
    text = normalize_text(text)
    symptom = normalize_text(symptom)
    
    for neg in NEGATIONS:
        # Check for negation patterns around the symptom
        neg_patterns = [
            f"{neg} {symptom}",
            f"{symptom} {neg}",
            f"{neg} ada {symptom}",
            f"{symptom} tidak ada"
        ]
        
        for pattern in neg_patterns:
            if pattern in text:
                return True
    
    return False

def check_symptom_list(text: str, symptom_list: List[str]) -> List[str]:
    """
    Replace fuzzy partial matching approach with exact phrase matching.
    Only accept symptoms that are NOT negated.
    """
    text = normalize_text(text)
    matched = []
    
    for symptom in symptom_list:
        if contains_phrase(text, symptom) and not is_negated(text, symptom):
            matched.append(symptom)
    
    return matched

def check_medical_terms(text: str, term_list: List[str]) -> List[str]:
    """
    Generic medical term checker (for risk factors, medications, etc).
    """
    text = normalize_text(text)
    matched = []
    
    for term in term_list:
        if contains_phrase(text, term):
            matched.append(term)
    
    return matched

# Test cases for validation
if __name__ == "__main__":
    # Test negation handling
    test_cases = [
        ("nyeri dada", ["nyeri dada", "sesak napas"], ["nyeri dada"]),
        ("tidak ada nyeri dada", ["nyeri dada", "sesak napas"], []),
        ("sesak napas tapi tidak ada nyeri dada", ["nyeri dada", "sesak napas"], ["sesak napas"]),
        ("napas cepat", ["henti napas", "sesak napas"], ["sesak napas"]),  # Should NOT match henti napas
        ("henti napas", ["henti napas", "sesak napas"], ["henti napas"]),
    ]
    
    print("=== TEXT MATCHING TEST RESULTS ===")
    for i, (text, symptoms, expected) in enumerate(test_cases):
        result = check_symptom_list(text, symptoms)
        status = "✅" if result == expected else "❌"
        print(f"{status} Test {i+1}: '{text}' -> {result} (expected: {expected})")

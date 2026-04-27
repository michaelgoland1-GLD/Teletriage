"""
Test suite for data-awareness feature.
Tests that the system handles incomplete data gracefully while still producing diagnosis and triage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from triage_engine_new import triage_engine, check_data_completeness

def test_complete_data():
    """Test that complete data produces full confidence."""
    print("\n=== TEST 1: Complete Data Scenario ===")
    
    # Complete data case
    complete_case = {
        "symptoms": ["nyeri dada berat"],
        "risk_factors": ["diabetes", "hipertensi"],
        "medications": ["aspirin", "metformin"],
        "past_medical_history": ["riwayat penyakit jantung"],
        "heart_rate": 95,
        "blood_pressure": "140/90",
        "spo2": 98,
        "gcs": 15,
        "age": 45,
        "sex": "laki-laki"
    }
    
    data_check = check_data_completeness(complete_case)
    result = triage_engine(complete_case)
    
    assert data_check['status'] == "Lengkap", f"Complete data should be 'Lengkap', got {data_check['status']}"
    assert data_check['confidence_penalty'] == 0.0, "Complete data should have no penalty"
    assert result.data_completeness == "Lengkap", f"Result should have 'Lengkap' status, got {result.data_completeness}"
    assert len(result.data_recommendations) == 0, "Complete data should have no recommendations"
    assert "Informasi masih terbatas" not in result.reasons, "Complete data should not have limited info message"
    
    print(f"✅ PASSED: Complete data handled correctly")
    print(f"   Status: {result.data_completeness}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Recommendations: {len(result.data_recommendations)}")
    return True

def test_missing_vitals():
    """Test that missing vitals reduces confidence and adds recommendations."""
    print("\n=== TEST 2: Missing Vitals Scenario ===")
    
    # Missing vital signs
    missing_vitals_case = {
        "symptoms": ["nyeri dada"],
        "risk_factors": ["diabetes"],
        "medications": ["metformin"],
        "age": 50,
        "sex": "laki-laki"
        # Missing: heart_rate, blood_pressure, spo2
    }
    
    data_check = check_data_completeness(missing_vitals_case)
    result = triage_engine(missing_vitals_case)
    
    assert data_check['status'] in ["Terbatas", "Sangat Terbatas"], f"Missing vitals should be limited, got {data_check['status']}"
    assert data_check['confidence_penalty'] > 0, "Missing vitals should have confidence penalty"
    assert result.data_completeness in ["Terbatas", "Sangat Terbatas"], f"Result should reflect limited data"
    assert len(result.data_recommendations) > 0, "Missing vitals should have recommendations"
    assert "Informasi masih terbatas" in result.reasons, "Should have limited info message"
    
    print(f"✅ PASSED: Missing vitals handled correctly")
    print(f"   Status: {result.data_completeness}")
    print(f"   Confidence penalty: {data_check['confidence_penalty']:.2f}")
    print(f"   Recommendations: {len(result.data_recommendations)}")
    print(f"   Sample recommendations: {result.data_recommendations[:2]}")
    return True

def test_minimal_data():
    """Test that minimal data still produces diagnosis with reduced confidence."""
    print("\n=== TEST 3: Minimal Data Scenario ===")
    
    # Only symptoms, no other data
    minimal_case = {
        "symptoms": ["nyeri dada"]
    }
    
    data_check = check_data_completeness(minimal_case)
    result = triage_engine(minimal_case)
    
    assert data_check['status'] == "Sangat Terbatas", f"Minimal data should be very limited, got {data_check['status']}"
    assert data_check['confidence_penalty'] > 0, "Minimal data should have confidence penalty"
    assert result.data_completeness == "Sangat Terbatas", f"Result should reflect very limited data"
    assert len(result.data_recommendations) > 0, "Minimal data should have recommendations"
    assert result.syndrome is not None or result.triage_level in ["URGENT", "NON-URGENT"], "Should still produce diagnosis or triage"
    assert "Informasi masih terbatas" in result.reasons, "Should have limited info message"
    
    print(f"✅ PASSED: Minimal data still produces diagnosis")
    print(f"   Status: {result.data_completeness}")
    print(f"   Triage level: {result.triage_level}")
    print(f"   Syndrome: {result.syndrome}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Recommendations count: {len(result.data_recommendations)}")
    return True

def test_no_symptoms():
    """Test that missing symptoms adds recommendation and reduces confidence."""
    print("\n=== TEST 4: No Symptoms Scenario ===")
    
    # Vitals only, no symptoms
    no_symptoms_case = {
        "heart_rate": 100,
        "blood_pressure": "120/80",
        "spo2": 97,
        "age": 35,
        "sex": "perempuan"
    }
    
    data_check = check_data_completeness(no_symptoms_case)
    result = triage_engine(no_symptoms_case)
    
    assert data_check['status'] in ["Terbatas", "Sangat Terbatas"], f"No symptoms should be limited"
    assert len(result.data_recommendations) > 0, "No symptoms should have recommendations"
    assert any("gejala" in rec.lower() for rec in result.data_recommendations), "Should recommend symptoms"
    assert "Informasi masih terbatas" in result.reasons, "Should have limited info message"
    
    print(f"✅ PASSED: No symptoms handled correctly")
    print(f"   Status: {result.data_completeness}")
    print(f"   Triage level: {result.triage_level}")
    print(f"   Recommendations: {len(result.data_recommendations)}")
    return True

def test_critical_vitals_override():
    """Test that critical vitals bypass data penalty (safety first)."""
    print("\n=== TEST 5: Critical Vitals Override Scenario ===")
    
    # Critical vitals with missing other data
    critical_case = {
        "symptoms": ["pusing ringan"],
        "heart_rate": 140,  # Critical
        "age": 30
        # Missing: blood_pressure, spo2, risk_factors, sex
    }
    
    data_check = check_data_completeness(critical_case)
    result = triage_engine(critical_case)
    
    # Critical vitals should still trigger EMERGENCY despite missing data
    assert result.triage_level == "EMERGENCY", "Critical vitals should force EMERGENCY"
    assert result.syndrome == "Critical Vital Signs", "Should be critical vital signs syndrome"
    assert result.confidence == 1.0, "Critical cases should have full confidence (safety override)"
    assert result.ambulance_required == True, "Critical cases should require ambulance"
    
    print(f"✅ PASSED: Critical vitals override data penalty")
    print(f"   Triage level: {result.triage_level}")
    print(f"   Syndrome: {result.syndrome}")
    print(f"   Confidence: {result.confidence:.2f} (safety override)")
    print(f"   Data completeness: {result.data_completeness}")
    return True

def test_recommendations_simple_language():
    """Test that recommendations use simple, lay-friendly language."""
    print("\n=== TEST 6: Simple Language Recommendations ===")
    
    incomplete_case = {
        "symptoms": ["nyeri dada"]
    }
    
    data_check = check_data_completeness(incomplete_case)
    
    # Check that recommendations are simple and understandable
    for rec in data_check['recommendations']:
        assert len(rec) < 100, f"Recommendation should be concise: {rec}"
        # Should not use medical jargon
        assert "qSOFA" not in rec, "Should not use clinical scoring terms in user recommendations"
        assert "Wells" not in rec, "Should not use clinical scoring terms in user recommendations"
        assert "HEART" not in rec, "Should not use clinical scoring terms in user recommendations"
    
    print(f"✅ PASSED: Recommendations use simple language")
    print(f"   Sample recommendations: {data_check['recommendations'][:3]}")
    return True

def run_all_tests():
    """Run all data-awareness tests."""
    print("\n" + "="*60)
    print("DATA-AWARENESS FEATURE TESTS")
    print("="*60)
    
    tests = [
        test_complete_data,
        test_missing_vitals,
        test_minimal_data,
        test_no_symptoms,
        test_critical_vitals_override,
        test_recommendations_simple_language
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {test.__name__}")
            print(f"   Error: {str(e)}")
    
    print("\n" + "="*60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 ALL DATA-AWARENESS TESTS PASSED!")
        print("✅ System handles incomplete data gracefully")
        print("✅ Diagnosis and triage still produced with incomplete data")
        print("✅ Confidence reduced for incomplete data")
        print("✅ 'Informasi masih terbatas' message added")
        print("✅ Data recommendations provided in simple language")
        print("✅ Critical cases bypass data penalty (safety first)")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

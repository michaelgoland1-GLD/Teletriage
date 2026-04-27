"""
Test runner for production-grade triage engine.
Runs all test cases and validates results against expected outcomes.
"""

import json
from triage_engine_new import triage_engine, TriageResult

def load_test_cases():
    """Load test cases from JSON file."""
    try:
        with open('test_cases.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: test_cases.json not found")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in test_cases.json: {e}")
        return []

def run_tests():
    """Run all test cases and report results."""
    test_cases = load_test_cases()
    
    if not test_cases:
        return
    
    print("🚀 PRODUCTION-GRADE TRIAGE ENGINE TEST SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0
    total = len(test_cases)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📋 TEST CASE {i}: {case['name']}")
        print("-" * 40)
        
        # Run triage engine
        result = triage_engine(case)
        
        # Validate results
        syndrome_match = result.syndrome == case['expected_syndrome']
        triage_match = result.triage_level == case['expected_triage']
        specialist_match = result.specialist == case['expected_specialist']
        
        # Validate action_plan structure
        action_plan_valid = (
            hasattr(result, 'action_plan') and 
            result.action_plan is not None and
            'immediate' in result.action_plan and
            'hospital' in result.action_plan and
            'specialist' in result.action_plan
        )
        
        # Print results
        print(f"Expected Syndrome: {case['expected_syndrome']}")
        print(f"Actual Syndrome:   {result.syndrome}")
        print(f"Syndrome Match:    {'✅' if syndrome_match else '❌'}")
        
        print(f"Expected Triage:  {case['expected_triage']}")
        print(f"Actual Triage:    {result.triage_level}")
        print(f"Triage Match:     {'✅' if triage_match else '❌'}")
        
        print(f"Expected Specialist: {case['expected_specialist']}")
        print(f"Actual Specialist:   {result.specialist}")
        print(f"Specialist Match:  {'✅' if specialist_match else '❌'}")
        
        print(f"Action Plan Valid:  {'✅' if action_plan_valid else '❌'}")
        if action_plan_valid:
            immediate = result.action_plan.get('immediate', [])
            specialist_ap = result.action_plan.get('specialist', '')
            print(f"  Immediate Actions: {', '.join(immediate[:2])}")
            print(f"  Action Plan Specialist: {specialist_ap}")
        
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Action: {result.action}")
        print(f"Ambulance: {result.ambulance_required}")
        
        if result.medication_warnings:
            print(f"Med Warnings: {', '.join(result.medication_warnings)}")
        
        # Overall test result
        test_passed = syndrome_match and triage_match and specialist_match and action_plan_valid
        if test_passed:
            print(f"🎯 RESULT: ✅ PASSED")
            passed += 1
        else:
            print(f"🎯 RESULT: ❌ FAILED")
            failed += 1
        
        print("=" * 40)
    
    # Summary
    print(f"\n📊 TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total}")
    print(f"Passed:      {passed} ✅")
    print(f"Failed:      {failed} ❌")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Production-ready triage engine.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review and fix issues.")
    
    return passed, failed, total

def validate_critical_requirements():
    """Validate critical requirements are met."""
    print("\n🔍 CRITICAL REQUIREMENTS VALIDATION")
    print("=" * 60)
    
    # Test 1: No fuzzy matching false positives
    print("1. Testing fuzzy matching false positives...")
    from text_matching import check_symptom_list
    
    false_positive_test = "napas cepat"
    symptoms = ["henti napas", "sesak napas"]
    result = check_symptom_list(false_positive_test, symptoms)
    
    if "henti napas" in result:
        print("   ❌ FAILED: False positive detected in fuzzy matching")
        return False
    else:
        print("   ✅ PASSED: No false positives in text matching")
    
    # Test 2: Negation handling
    print("2. Testing negation handling...")
    negation_test = "tidak ada nyeri dada"
    symptoms = ["nyeri dada", "sesak napas"]
    result = check_symptom_list(negation_test, symptoms)
    
    if "nyeri dada" in result:
        print("   ❌ FAILED: Negation not handled properly")
        return False
    else:
        print("   ✅ PASSED: Negation handled correctly")
    
    # Test 3: Syndrome detection
    print("3. Testing syndrome detection...")
    from syndrome_engine import detect_syndromes
    
    sepsis_case = {
        "symptoms": ["bingung", "demam tinggi"],
        "risk_factors": ["infeksi"],
        "medications": [],
        "past_medical_history": [],
        "heart_rate": 120,
        "blood_pressure": "90/60",
        "sex": "laki-laki"
    }
    
    syndromes = detect_syndromes(sepsis_case)
    if not syndromes or syndromes[0].name != "Sepsis":
        print("   ❌ FAILED: Sepsis not detected correctly")
        return False
    else:
        print("   ✅ PASSED: Sepsis detected correctly")
    
    # Test 4: Medication parsing
    print("4. Testing medication parsing...")
    from medication_rules import detect_medication_risks
    
    med_test = ["empagliflozin", "metformin"]
    risks = detect_medication_risks(med_test)
    
    if not risks.get("SGLT2"):
        print("   ❌ FAILED: SGLT2 not detected")
        return False
    else:
        print("   ✅ PASSED: SGLT2 detected correctly")
    
    # Test 5: Emergency guardrail
    print("5. Testing emergency guardrail...")
    from triage_engine_new import emergency_guardrail
    
    critical_case = {
        "heart_rate": 140,
        "blood_pressure": "200/110",
        "symptoms": ["pusing ringan"]
    }
    
    if not emergency_guardrail(critical_case):
        print("   ❌ FAILED: Emergency guardrail not triggered")
        return False
    else:
        print("   ✅ PASSED: Emergency guardrail triggered correctly")
    
    print("\n🎯 ALL CRITICAL REQUIREMENTS VALIDATED ✅")
    return True

if __name__ == "__main__":
    # Validate critical requirements first
    if not validate_critical_requirements():
        print("\n❌ CRITICAL REQUIREMENTS FAILED - Fix before running full test suite")
        exit(1)
    
    # Run full test suite
    run_tests()

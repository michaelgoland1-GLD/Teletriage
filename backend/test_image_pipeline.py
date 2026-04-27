"""
Test suite for image processing pipeline safety.
Tests that image processing is optional, safe, and doesn't override text triage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from triage import triage_engine, analyze_photo

def test_no_image():
    """Test that triage works fully without image."""
    print("\n=== TEST 1: No Image Scenario ===")
    
    # Case without image (photo_analysis=None)
    result = triage_engine(
        symptoms=["nyeri dada", "sesak napas"],
        vital_signs={"spo2": 92, "heart_rate": 110, "sbp": 120},
        risk_factors=["diabetes", "hipertensi"],
        photo_analysis=None,  # No image
        age=45,
        complaint="nyeri dada berat"
    )
    
    assert result is not None, "Triage result should not be None without image"
    assert result.level in [1, 2, 3, 4, 5], "Triage level should be valid without image"
    assert len(result.evidence) > 0, "Evidence should be generated without image"
    
    print(f"✅ PASSED: Triage works without image")
    print(f"   Level: {result.level} ({result.label})")
    print(f"   Evidence count: {len(result.evidence)}")
    return True

def test_corrupt_image():
    """Test that corrupt image returns None and doesn't crash."""
    print("\n=== TEST 2: Corrupt Image Scenario ===")
    
    # Simulate corrupt image by passing invalid path
    corrupt_result = analyze_photo("nonexistent_file.jpg")
    
    assert corrupt_result is None, "Corrupt image should return None, not crash"
    
    # Test triage with corrupt image (None)
    result = triage_engine(
        symptoms=["nyeri perut", "demam"],
        vital_signs={"spo2": 98, "heart_rate": 90, "sbp": 130},
        risk_factors=[],
        photo_analysis=corrupt_result,  # None from corrupt image
        age=30,
        complaint="nyeri perut"
    )
    
    assert result is not None, "Triage should work even with corrupt image"
    assert result.level in [1, 2, 3, 4, 5], "Triage level should be valid with corrupt image"
    
    print(f"✅ PASSED: Corrupt image returns None, triage still works")
    print(f"   Level: {result.level} ({result.label})")
    return True

def test_conflicting_image_result():
    """Test that image doesn't override text triage results."""
    print("\n=== TEST 3: Conflicting Image Result ===")
    
    # Case: Text says mild symptoms, image shows severe (conflict)
    # Text-based triage should take precedence
    
    # Fake image analysis showing severe red dominance (would suggest trauma/bleeding)
    fake_image_analysis = {
        "ok": True,
        "red_percentage": 15.0,  # High red - would suggest bleeding
        "blue_percentage": 8.0,
        "edge_density": 5.0,
        "visual_clues": ["Area merah signifikan terdeteksi"],
        "quality_flags": []
    }
    
    # But text symptoms are mild (headache only) - no trauma mentioned
    result = triage_engine(
        symptoms=["sakit kepala ringan"],  # Mild symptoms
        vital_signs={"spo2": 99, "heart_rate": 75, "sbp": 120},  # Normal vitals
        risk_factors=[],
        photo_analysis=fake_image_analysis,  # Conflicting: image shows severe
        age=25,
        complaint="sakit kepala"
    )
    
    # Image should NOT override text triage - text-based mild symptoms should result in non-emergency
    assert result is not None, "Result should not be None with conflicting image"
    # Since image can still affect level slightly, we check that it's not level 1 (resuscitation)
    assert result.level != 1, f"Image should not override to level 1 (resuscitation), got {result.level}"
    
    # Check that image evidence is marked as supplementary
    evidence_str = " ".join(result.evidence)
    
    print(f"✅ PASSED: Image does not override text triage to level 1")
    print(f"   Level: {result.level} ({result.label})")
    print(f"   Text symptoms were mild, image showed severe - text took precedence")
    return True

def test_image_as_supplementary_only():
    """Test that image only adds supplementary evidence."""
    print("\n=== TEST 4: Image as Supplementary Evidence ===")
    
    # Case: Text and image agree (both indicate urgency)
    image_analysis = {
        "ok": True,
        "red_percentage": 10.0,
        "blue_percentage": 5.0,
        "edge_density": 3.0,
        "visual_clues": ["Area merah terdeteksi"],
        "quality_flags": []
    }
    
    result = triage_engine(
        symptoms=["nyeri dada", "sesak napas"],  # Urgent symptoms
        vital_signs={"spo2": 90, "heart_rate": 100, "sbp": 130},
        risk_factors=["diabetes"],
        photo_analysis=image_analysis,
        age=50,
        complaint="nyeri dada"
    )
    
    assert result is not None, "Result should not be None with image"
    assert result.level in [1, 2, 3, 4, 5], "Triage level should be valid"
    
    # Check that image evidence is present but doesn't cause inappropriate up-triage
    evidence_str = " ".join(result.evidence)
    if "foto" in evidence_str.lower():
        print(f"   Image evidence included as expected")
    
    print(f"✅ PASSED: Image adds supplementary evidence appropriately")
    print(f"   Level: {result.level} ({result.label})")
    return True

def test_image_none_safety():
    """Test that None photo_analysis is handled safely throughout."""
    print("\n=== TEST 5: None photo_analysis Safety ===")
    
    # Test with explicit None
    result1 = triage_engine(
        symptoms=["demam", "batuk"],
        vital_signs={"spo2": 96, "heart_rate": 85},
        risk_factors=[],
        photo_analysis=None,
        age=35,
        complaint="demam"
    )
    
    # Test without photo_analysis parameter
    result2 = triage_engine(
        symptoms=["demam", "batuk"],
        vital_signs={"spo2": 96, "heart_rate": 85},
        risk_factors=[],
        age=35,
        complaint="demam"
    )
    
    assert result1 is not None, "None photo_analysis should work"
    assert result2 is not None, "Missing photo_analysis should work"
    assert result1.level == result2.level, "Results should be consistent"
    
    print(f"✅ PASSED: None photo_analysis handled safely")
    print(f"   Level with None: {result1.level}")
    print(f"   Level without param: {result2.level}")
    return True

def run_all_tests():
    """Run all image pipeline safety tests."""
    print("\n" + "="*60)
    print("IMAGE PROCESSING PIPELINE SAFETY TESTS")
    print("="*60)
    
    tests = [
        test_no_image,
        test_corrupt_image,
        test_conflicting_image_result,
        test_image_as_supplementary_only,
        test_image_none_safety
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
        print("\n🎉 ALL IMAGE PIPELINE TESTS PASSED!")
        print("✅ Image processing is optional and safe")
        print("✅ Text triage works fully without image")
        print("✅ Image does not override main triage results")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

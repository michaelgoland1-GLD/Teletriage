import sys
sys.path.append('.')
from backend.triage import triage_engine

# Test enhanced medical staff estimation
test_cases = [
    {
        'name': 'Nyeri Dada (High Resource)',
        'symptoms': ['nyeri dada'],
        'complaint': 'nyeri dada hebat',
        'expected': {'dokter_umum': 1, 'dokter_spesialis': 1, 'perawat': 2, 'total': 4}
    },
    {
        'name': 'Demam (Low Resource)',
        'symptoms': ['demam'],
        'complaint': 'demam',
        'expected': {'dokter_umum': 1, 'dokter_spesialis': 0, 'perawat': 1, 'total': 2}
    },
    {
        'name': 'Trauma (High Resource)',
        'symptoms': ['trauma'],
        'complaint': 'luka berat',
        'expected': {'dokter_umum': 1, 'dokter_spesialis': 1, 'perawat': 2, 'total': 4}
    }
]

print('=== ENHANCED MEDICAL STAFF ESTIMATION TEST ===')
for case in test_cases:
    result = triage_engine(
        symptoms=case['symptoms'],
        vital_signs={'spo2': 98, 'heart_rate': 80},
        risk_factors=[],
        photo_analysis=None,
        age=30,
        complaint=case['complaint'],
        pregnancy=False,
        additional_data={}
    )
    
    print(f'\n{case["name"]}:')
    print(f'  Expected: {case["expected"]}')
    print(f'  Actual: {result.medical_staff_breakdown}')
    print(f'  Match: {result.medical_staff_breakdown == case["expected"]}')
    print(f'  Level: {result.level}')

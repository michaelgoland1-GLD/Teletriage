import sys
sys.path.append('.')
from backend.triage import detect_medical_entities, recommend_specialist

# Test berbagai kondisi pasien untuk analisis spesialis recommendation
test_cases = [
    {
        'name': 'Kasus Cardiac',
        'symptoms': ['nyeri dada', 'sesak napas'],
        'complaint': 'nyeri dada hebat',
        'level': 1,
        'age': 55
    },
    {
        'name': 'Kasus Neurological',
        'symptoms': ['pingsan', 'kelemahan'],
        'complaint': 'pingsan tiba-tiba',
        'level': 1,
        'age': 45
    },
    {
        'name': 'Kasus Respiratory',
        'symptoms': ['sesak napas', 'batuk'],
        'complaint': 'sesak napas berat',
        'level': 1,
        'age': 30
    },
    {
        'name': 'Kasus Mixed',
        'symptoms': ['nyeri dada', 'pingsan'],
        'complaint': 'nyeri dada dan pingsan',
        'level': 1,
        'age': 60
    },
    {
        'name': 'Kasus Pediatric',
        'symptoms': ['demam', 'sesak'],
        'complaint': 'demam tinggi sesak',
        'level': 1,
        'age': 3
    }
]

print('=== ANALISIS SPESIALIS RECOMMENDATION ===')
for case in test_cases:
    print(f'\n{case["name"]}:')
    entities = detect_medical_entities(case['symptoms'], case['complaint'])
    specialists = recommend_specialist(entities, case['level'], case['age'])
    print(f'  Gejala: {case["symptoms"]} + "{case["complaint"]}"')
    print(f'  Entities detected: {entities}')
    print(f'  Specialists: {specialists}')
    print(f'  Count: {len(specialists)}')

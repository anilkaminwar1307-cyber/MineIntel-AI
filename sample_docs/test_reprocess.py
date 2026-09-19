import requests

docs = requests.get('http://localhost:8000/api/documents').json().get('items', [])
for d in docs:
    doc_id = d['id']
    name = d['original_filename']
    res = requests.post(f"http://localhost:8000/api/documents/{doc_id}/reprocess").json()
    status = res.get('status')
    facts = requests.get(f"http://localhost:8000/api/documents/{doc_id}/facts").json()
    print(f"[{name}] Status: {status} | Facts Extracted: {len(facts)}")
    for f in facts[:3]:
        print(f"   -> {f['metric_name']}: {f['numeric_value']} {f['unit']} ({f['subsidiary']} {f['reporting_period']}) [conf: {f['confidence_score']}]")

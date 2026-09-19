import requests

docs = requests.get('http://localhost:8000/api/documents').json().get('items', [])
if docs:
    d = docs[0]
    print('Filename:', d.get('original_filename'))
    print('Status:', d.get('status'))
    print('Error:', d.get('processing_error'))
    print('Message:', d.get('processing_message'))
    logs = requests.get(f"http://localhost:8000/api/documents/{d['id']}/processing-log").json()
    print('Logs:', logs)

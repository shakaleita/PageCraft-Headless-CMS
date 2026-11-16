"""Insert optional synthetic demonstration records (safe to rerun)."""
from fastapi.testclient import TestClient
from main import app

SEEDS = [{'slug': 'welcome', 'title': 'Welcome to PageCraft', 'body': 'This is a demonstration content page.'}, {'slug': 'about', 'title': 'About our platform', 'body': 'A versioned headless CMS starter.'}]
client=TestClient(app)
if client.get('/api/items').json():
    print('Existing records found; skipping seed.')
else:
    for record in SEEDS:
        result=client.post('/api/items',json=record)
        result.raise_for_status()
    print('Added',len(SEEDS),'synthetic sample records.')

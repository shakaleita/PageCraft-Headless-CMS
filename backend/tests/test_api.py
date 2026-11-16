import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['ok']

def test_initial_list():
    r=client.get('/api/items')
    assert r.status_code==200 and isinstance(r.json(),list)

def test_summary():
    r=client.get('/api/summary')
    assert r.status_code==200 and isinstance(r.json(),list)


# v0.3 regression tests
def test_revision_diff_and_published_sitemap():
    p=client.post('/api/items',json={'slug':'qa-landing','title':'Version one','body':'Before'}).json()
    assert not any(x['slug']=='qa-landing' for x in client.get('/api/sitemap').json())
    assert client.put(f"/api/items/{p['id']}",json={'slug':'qa-landing','title':'Version two','body':'After'}).status_code==200
    diff=client.get(f"/api/pages/{p['id']}/diff/1/2").json()['diff']
    assert '-Before' in diff and '+After' in diff
    assert client.patch(f"/api/items/{p['id']}").status_code==200
    assert any(x['slug']=='qa-landing' for x in client.get('/api/sitemap').json())
    assert client.post(f"/api/restore/{p['id']}/1").status_code==200
    assert client.get(f"/api/pages/{p['id']}/diff/1/99").status_code==404


import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
os.environ['OWNER_SETUP_TOKEN']='test-only-setup-token-1234567890123'
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)
assert client.post('/api/auth/register',json={'username':'qaowner','password':'DemoPassword123!','setup_token':'test-only-setup-token-1234567890123'}).status_code==201
assert client.post('/api/auth/login',json={'username':'qaowner','password':'DemoPassword123!'}).status_code==200

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



def test_v05_slug_rules_and_public_index():
    assert client.post('/api/items',json={'slug':'INVALID SLUG','title':'Bad','body':'bad'}).status_code==422
    p=client.post('/api/items',json={'slug':'release-notes','title':'Release Notes','body':'Synthetic content'}).json()
    assert not any(x['slug']=='release-notes' for x in client.get('/api/public-index').json())
    assert client.patch(f"/api/items/{p['id']}").status_code==200
    assert any(x['slug']=='release-notes' for x in client.get('/api/public-index').json())

def test_v05_authentication():
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/items').status_code==401
        assert anonymous.post('/api/auth/register',json={'username':'intruder','password':'DemoPassword123!','setup_token':'bad'}).status_code==403

# v0.6 request-origin and owner audit regression
def test_v06_audit_record_and_cross_site_guard():
    attempted=client.post('/api/__audit_probe_404')
    assert attempted.status_code==404
    audit=client.get('/api/auth/audit')
    assert audit.status_code==200
    assert any(row['method']=='POST' and row['path']=='/api/__audit_probe_404'
               and row['status_code']==404 for row in audit.json())
    assert client.get('/api/auth/audit',params={'limit':201}).status_code==422
    blocked=client.post('/api/__audit_probe_404',headers={'sec-fetch-site':'cross-site'})
    assert blocked.status_code==403

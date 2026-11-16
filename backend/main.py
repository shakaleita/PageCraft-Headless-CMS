APP_TITLE = 'PageCraft'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import sqlite3, os
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.environ.get("APP_DB", str(Path(__file__).parent / "app.db")))
app = FastAPI(title=APP_TITLE, version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])

@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]

def setup(sql):
    with db() as con:
        con.executescript(sql)

@app.get("/api/health")
def health():
    return {"ok": True, "service": APP_TITLE}


setup("""CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY,slug TEXT NOT NULL UNIQUE,title TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Draft',version INTEGER NOT NULL DEFAULT 1);CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,page_id INTEGER NOT NULL,version INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,changed_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(page_id) REFERENCES pages(id));""")
from pydantic import Field
class Page(BaseModel):
    slug:str=Field(min_length=2,max_length=90,pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*\\Z')
    title:str=Field(min_length=1,max_length=200)
    body:str=Field(max_length=100000)
    status:str='Draft'

@app.get('/api/items')
def items():
    with db() as c:return rows(c.execute('SELECT * FROM pages ORDER BY id DESC'))
@app.post('/api/items',status_code=201)
def create_item(d:Page):
    if not d.slug.strip() or not d.title.strip():raise HTTPException(422,'Slug and title required')
    try:
        with db() as c:
            cur=c.execute('INSERT INTO pages(slug,title,body,status) VALUES(?,?,?,?)',(d.slug,d.title,d.body,'Draft'))
            id=cur.lastrowid
            c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,1,d.title,d.body))
            return dict(c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone())
    except sqlite3.IntegrityError:raise HTTPException(409,'Slug already exists')
@app.patch('/api/items/{id}')
def publish(id:int):
    with db() as c:
        cur=c.execute("UPDATE pages SET status=CASE WHEN status='Draft' THEN 'Published' ELSE 'Draft' END WHERE id=?",(id,))
        if not cur.rowcount:raise HTTPException(404,'Page not found')
        return dict(c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone())
@app.put('/api/items/{id}')
def edit(id:int,d:Page):
    with db() as c:
        existing=c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone()
        if not existing:raise HTTPException(404,'Page not found')
        version=existing['version']+1
        c.execute('UPDATE pages SET title=?,body=?,version=? WHERE id=?',(d.title,d.body,version,id))
        c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,version,d.title,d.body))
        return {'id':id,'version':version}
@app.get('/api/revisions/{id}')
def revisions(id:int):
    with db() as c:return rows(c.execute('SELECT * FROM revisions WHERE page_id=? ORDER BY version DESC',(id,)))
@app.post('/api/restore/{id}/{version}')
def restore(id:int,version:int):
    with db() as c:
        r=c.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(id,version)).fetchone()
        p=c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone()
        if not r or not p:raise HTTPException(404,'Revision not found')
        latest=p['version']+1
        c.execute('UPDATE pages SET title=?,body=?,version=? WHERE id=?',(r['title'],r['body'],latest,id))
        c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,latest,r['title'],r['body']))
        return {'id':id,'version':latest}
@app.get('/api/public/{slug}')
def public(slug:str):
    with db() as c:p=c.execute("SELECT slug,title,body FROM pages WHERE slug=? AND status='Published'",(slug,)).fetchone()
    if not p:raise HTTPException(404,'Page not published')
    return dict(p)
@app.get('/api/summary')
def summary():
    with db() as c:return rows(c.execute('SELECT status AS label,COUNT(*) AS value FROM pages GROUP BY status'))


# v0.3: revision comparison and published sitemap
import difflib

@app.get('/api/pages/{page_id}/diff/{old_version}/{new_version}')
def compare_revisions(page_id: int, old_version: int, new_version: int):
    with db() as con:
        old=con.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(page_id,old_version)).fetchone()
        new=con.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(page_id,new_version)).fetchone()
        if not old or not new:
            raise HTTPException(404,'Revision not found')
        previous=(old['title']+'\n'+old['body']).splitlines(keepends=True)
        current=(new['title']+'\n'+new['body']).splitlines(keepends=True)
        changes=list(difflib.unified_diff(previous,current,fromfile=f'v{old_version}',tofile=f'v{new_version}'))
        return {'page_id':page_id,'from':old_version,'to':new_version,'diff':''.join(changes)}

@app.get('/api/sitemap')
def sitemap():
    with db() as con:
        return rows(con.execute("SELECT slug,title,version FROM pages WHERE status='Published' ORDER BY slug"))

)
    title:str=Field(min_length=1,max_length=200)
    body:str=Field(max_length=100000)
    status:str='Draft'
@app.get('/api/items')
def items():
    with db() as c:return rows(c.execute('SELECT * FROM pages ORDER BY id DESC'))
@app.post('/api/items',status_code=201)
def create_item(d:Page):
    if not d.slug.strip() or not d.title.strip():raise HTTPException(422,'Slug and title required')
    try:
        with db() as c:
            cur=c.execute('INSERT INTO pages(slug,title,body,status) VALUES(?,?,?,?)',(d.slug,d.title,d.body,'Draft'))
            id=cur.lastrowid
            c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,1,d.title,d.body))
            return dict(c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone())
    except sqlite3.IntegrityError:raise HTTPException(409,'Slug already exists')
@app.patch('/api/items/{id}')
def publish(id:int):
    with db() as c:
        cur=c.execute("UPDATE pages SET status=CASE WHEN status='Draft' THEN 'Published' ELSE 'Draft' END WHERE id=?",(id,))
        if not cur.rowcount:raise HTTPException(404,'Page not found')
        return dict(c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone())
@app.put('/api/items/{id}')
def edit(id:int,d:Page):
    with db() as c:
        existing=c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone()
        if not existing:raise HTTPException(404,'Page not found')
        version=existing['version']+1
        c.execute('UPDATE pages SET title=?,body=?,version=? WHERE id=?',(d.title,d.body,version,id))
        c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,version,d.title,d.body))
        return {'id':id,'version':version}
@app.get('/api/revisions/{id}')
def revisions(id:int):
    with db() as c:return rows(c.execute('SELECT * FROM revisions WHERE page_id=? ORDER BY version DESC',(id,)))
@app.post('/api/restore/{id}/{version}')
def restore(id:int,version:int):
    with db() as c:
        r=c.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(id,version)).fetchone()
        p=c.execute('SELECT * FROM pages WHERE id=?',(id,)).fetchone()
        if not r or not p:raise HTTPException(404,'Revision not found')
        latest=p['version']+1
        c.execute('UPDATE pages SET title=?,body=?,version=? WHERE id=?',(r['title'],r['body'],latest,id))
        c.execute('INSERT INTO revisions(page_id,version,title,body) VALUES(?,?,?,?)',(id,latest,r['title'],r['body']))
        return {'id':id,'version':latest}
@app.get('/api/public/{slug}')
def public(slug:str):
    with db() as c:p=c.execute("SELECT slug,title,body FROM pages WHERE slug=? AND status='Published'",(slug,)).fetchone()
    if not p:raise HTTPException(404,'Page not published')
    return dict(p)
@app.get('/api/summary')
def summary():
    with db() as c:return rows(c.execute('SELECT status AS label,COUNT(*) AS value FROM pages GROUP BY status'))


# v0.3: revision comparison and published sitemap
import difflib

@app.get('/api/pages/{page_id}/diff/{old_version}/{new_version}')
def compare_revisions(page_id: int, old_version: int, new_version: int):
    with db() as con:
        old=con.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(page_id,old_version)).fetchone()
        new=con.execute('SELECT * FROM revisions WHERE page_id=? AND version=?',(page_id,new_version)).fetchone()
        if not old or not new:
            raise HTTPException(404,'Revision not found')
        previous=(old['title']+'\n'+old['body']).splitlines(keepends=True)
        current=(new['title']+'\n'+new['body']).splitlines(keepends=True)
        changes=list(difflib.unified_diff(previous,current,fromfile=f'v{old_version}',tofile=f'v{new_version}'))
        return {'page_id':page_id,'from':old_version,'to':new_version,'diff':''.join(changes)}

@app.get('/api/sitemap')
def sitemap():
    with db() as con:
        return rows(con.execute("SELECT slug,title,version FROM pages WHERE status='Published' ORDER BY slug"))


@app.get('/api/public-index')
def published_index():
    with db() as con:
        return rows(con.execute("SELECT slug,title,version FROM pages WHERE status='Published' ORDER BY slug"))

from security import install_auth
install_auth(app,DB)

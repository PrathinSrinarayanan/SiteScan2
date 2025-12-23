import sqlite3
import json
from pathlib import Path

DB_PATH = Path("data/sitescan.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    filename TEXT,
    image_path TEXT,
    qr_path TEXT,
    ocr_text TEXT,
    labels TEXT,
    reconstruction_path TEXT,
    metadata TEXT,
    created_at TEXT
);
'''

CREATE_CHANGES_SQL = '''
CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT,
    change_type TEXT,
    payload TEXT,
    changed_at TEXT
);
'''

CREATE_JOBS_SQL = '''
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT,
    job_type TEXT,
    params TEXT,
    status TEXT,
    result TEXT,
    progress INTEGER,
    created_at TEXT,
    updated_at TEXT
);
'''


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute(CREATE_SQL)
    conn.execute(CREATE_CHANGES_SQL)
    conn.execute(CREATE_JOBS_SQL)
    conn.commit()
    return conn


def insert_artifact(conn, record):
    sql = '''INSERT OR REPLACE INTO artifacts
    (id, filename, image_path, qr_path, ocr_text, labels, reconstruction_path, metadata, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    conn.execute(sql, (
        record.get('id'),
        record.get('filename'),
        record.get('image_path'),
        record.get('qr_path'),
        record.get('ocr_text'),
        json.dumps(record.get('labels', [])),
        record.get('reconstruction_path'),
        json.dumps(record.get('metadata', {})),
        record.get('created_at')
    ))
    conn.commit()
    # record a change
    try:
        payload = json.dumps(record)
        conn.execute('INSERT INTO changes (artifact_id, change_type, payload, changed_at) VALUES (?, ?, ?, ?)',
                     (record.get('id'), 'upsert', payload, record.get('created_at') or timestamp()))
        conn.commit()
    except Exception:
        pass


def get_artifact(conn, id_):
    cur = conn.cursor()
    cur.execute('SELECT * FROM artifacts WHERE id=?', (id_,))
    row = cur.fetchone()
    if not row:
        return None
    keys = ['id','filename','image_path','qr_path','ocr_text','labels','reconstruction_path','metadata','created_at']
    obj = dict(zip(keys, row))
    obj['labels'] = json.loads(obj['labels']) if obj['labels'] else []
    obj['metadata'] = json.loads(obj['metadata']) if obj['metadata'] else {}
    return obj


def list_artifacts(conn, limit=100):
    cur = conn.cursor()
    cur.execute('SELECT id, filename, image_path, created_at FROM artifacts ORDER BY created_at DESC LIMIT ?', (limit,))
    return cur.fetchall()


def search_artifacts(conn, query=None, site=None, spot=None, limit=200):
    cur = conn.cursor()
    sql = 'SELECT id, filename, image_path, created_at FROM artifacts WHERE 1=1 '
    params = []
    if query:
        sql += ' AND (id LIKE ? OR filename LIKE ? OR metadata LIKE ?) '
        q = f"%{query}%"
        params.extend([q, q, q])
    if site:
        sql += ' AND metadata LIKE ? '
        params.append(f"%\"site\": \"{site}\"%")
    if spot:
        sql += ' AND metadata LIKE ? '
        params.append(f"%\"spot\": \"{spot}\"%")
    sql += ' ORDER BY created_at DESC LIMIT ? '
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def list_changes(conn, artifact_id=None, limit=200):
    cur = conn.cursor()
    if artifact_id:
        cur.execute('SELECT artifact_id, change_type, payload, changed_at FROM changes WHERE artifact_id=? ORDER BY changed_at DESC LIMIT ?', (artifact_id, limit))
    else:
        cur.execute('SELECT artifact_id, change_type, payload, changed_at FROM changes ORDER BY changed_at DESC LIMIT ?', (limit,))
    return cur.fetchall()


def create_job(conn, artifact_id, job_type, params=None):
    now = timestamp()
    cur = conn.cursor()
    cur.execute('INSERT INTO jobs (artifact_id, job_type, params, status, result, progress, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (artifact_id, job_type, json.dumps(params or {}), 'pending', None, 0, now, now))
    conn.commit()
    return cur.lastrowid


def update_job(conn, job_id, status=None, result=None, progress=None):
    now = timestamp()
    cur = conn.cursor()
    parts = []
    params = []
    if status is not None:
        parts.append('status=?')
        params.append(status)
    if result is not None:
        parts.append('result=?')
        params.append(result)
    if progress is not None:
        parts.append('progress=?')
        params.append(progress)
    if not parts:
        return False
    params.extend([now, job_id])
    sql = 'UPDATE jobs SET ' + ','.join(parts) + ', updated_at=? WHERE id=?'
    cur.execute(sql, params)
    conn.commit()
    return True


def get_pending_jobs(conn, limit=10):
    cur = conn.cursor()
    cur.execute('SELECT id, artifact_id, job_type, params FROM jobs WHERE status IN ("pending","running") ORDER BY created_at ASC LIMIT ?', (limit,))
    return cur.fetchall()


def get_job(conn, job_id):
    cur = conn.cursor()
    cur.execute('SELECT id, artifact_id, job_type, params, status, result, progress, created_at, updated_at FROM jobs WHERE id=?', (job_id,))
    return cur.fetchone()


def merge_db_file(conn, other_db_path):
    # Merge another sqlite DB file into this DB by copying artifacts not present
    try:
        other = sqlite3.connect(str(other_db_path))
        cur = other.cursor()
        cur.execute('SELECT id, filename, image_path, qr_path, ocr_text, labels, reconstruction_path, metadata, created_at FROM artifacts')
        rows = cur.fetchall()
        for row in rows:
            aid = row[0]
            if not get_artifact(conn, aid):
                record = dict(zip(['id','filename','image_path','qr_path','ocr_text','labels','reconstruction_path','metadata','created_at'], row))
                # ensure JSON fields are strings
                try:
                    json.loads(record.get('labels') or '[]')
                except Exception:
                    record['labels'] = '[]'
                try:
                    json.loads(record.get('metadata') or '{}')
                except Exception:
                    record['metadata'] = '{}'
                insert_artifact(conn, record)
        other.close()
        return True
    except Exception:
        return False


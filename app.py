import streamlit as st
from db import get_conn, insert_artifact, get_artifact, list_artifacts, search_artifacts, list_changes, merge_db_file, create_job, get_pending_jobs, update_job, get_job
from utils import generate_id, timestamp, save_image_file, run_ocr, recognize_image, generate_qr, reconstruct_stub, image_to_datauri, generate_reconstruction_genai, generate_reconstruction_huggingface
import os, json, threading, time

st.set_page_config(page_title='SiteScan', layout='wide')

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root { --theme: #2D5F4C; --muted:#e9f1ec; --card-radius:12px; }
html, body, [data-testid='stAppViewContainer'] { background: linear-gradient(180deg, #f6faf6 0%, #f2f6f2 100%); font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; color:#213a31 }
.top-nav { background:var(--theme); color:#fff; padding:12px 28px; display:flex; align-items:center; gap:18px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }
.brand { font-family:Merriweather, serif; font-weight:700; font-size:18px }
.nav-item { color:rgba(255,255,255,0.95); margin-right:12px; font-weight:600 }
.main-container{ max-width:1100px; margin:22px auto }
.hero { text-align:center; margin-bottom:18px }
.card { background:#fff; border-radius:12px; padding:22px; box-shadow:0 12px 28px rgba(17,24,39,0.06); margin-bottom:18px }
.form-spacing { margin-top:12px }
.uploader { border:2px dashed rgba(45,95,76,0.22); border-radius:8px; min-height:200px; display:flex; align-items:center; justify-content:center; background:linear-gradient(180deg, rgba(45,95,76,0.02), transparent); }
.accent { color:var(--theme); font-weight:700 }
.small-muted { color:#96a89d; font-size:12px }
.save-btn { background:#9bb0a6; color:#fff; padding:10px 14px; border-radius:10px; border:none; font-weight:700 }
@media (max-width:900px){ .main-container{ padding:12px } }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# Top nav
st.markdown("""
<div class="top-nav">
  <div class="brand">SiteScan</div>
  <div class="nav-item">Capture</div>
  <div class="nav-item">Gallery</div>
  <div class="nav-item">Notes</div>
  <div style="flex:1"></div>
  <div class="nav-item">Quick Note</div>
</div>
""", unsafe_allow_html=True)

conn = get_conn()

st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.markdown('<div class="hero"><h1 style="font-family:Merriweather, serif; color:#214b39;">SiteScan</h1><div style="color:#5e7a6a">Capture and preserve archaeological discoveries</div></div>', unsafe_allow_html=True)

cols = st.columns([1, 0.02, 1])
with cols[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('New Discovery')
    upload = st.file_uploader('Artifact Photo', type=['png','jpg','jpeg','tif'])
    site_name = st.text_input('Site name', value='')
    spot = st.text_input('Digging spot / context', value='')
    fragile = st.checkbox('Fragile', value=False)
    tags = st.text_input('Tags (comma separated)', value='')
    notes = st.text_area('Quick notes', value='')
    if st.button('Create artifact record'):
        if not upload:
            st.error('Please upload an image')
        else:
            aid = generate_id()
            img_path = save_image_file(upload, aid)
            ocr_text = run_ocr(img_path)
            try:
                labels = recognize_image(img_path)
            except Exception:
                labels = []
            qr_path = generate_qr(aid, base_url=st.query_params.get('base_url', [None])[0])
            recon_path = reconstruct_stub(img_path, aid)
            record = {
                'id': aid,
                'filename': upload.name,
                'image_path': img_path,
                'qr_path': qr_path,
                'ocr_text': ocr_text,
                'labels': labels,
                'reconstruction_path': recon_path,
                'metadata': {
                    'site': site_name,
                    'spot': spot,
                    'fragile': fragile,
                    'tags': [t.strip() for t in tags.split(',') if t.strip()],
                    'notes': notes
                },
                'created_at': timestamp()
            }
            insert_artifact(conn, record)
            st.success(f'Artifact created: {aid}')
    st.markdown('</div>', unsafe_allow_html=True)

with cols[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('Artifacts')
    q = st.text_input('Search by ID, site, filename, tags', value='')
    rows = []
    if q.strip():
        rows = search_artifacts(conn, query=q, limit=200)
    else:
        rows = list_artifacts(conn, limit=200)
    for r in rows:
        aid, fname, imgpath, created = r
        cols_inner = st.columns([1,3,1])
        with cols_inner[0]:
            try:
                st.image(imgpath, width=120)
            except Exception:
                st.write('No image')
        with cols_inner[1]:
            st.write(f'**{fname or aid}**')
            if st.button('Open', key=f'open-{aid}'):
                st.experimental_set_query_params(id=aid)
                st.experimental_rerun()
        with cols_inner[2]:
            st.write(created)
    st.markdown('</div>', unsafe_allow_html=True)

# Detail view
params = st.query_params
if 'id' in params:
    aid = params['id'][0]
    rec = get_artifact(conn, aid)
    if rec:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Artifact: {aid}")
        left, right = st.columns([2,1])
        with left:
            try:
                st.image(rec['image_path'], use_column_width=True)
            except Exception:
                st.write('Image not available')
            edited = st.text_area('Edit OCR result before saving', value=rec.get('ocr_text',''))
            if st.button('Save OCR'):
                rec['ocr_text'] = edited
                insert_artifact(conn, rec)
                st.success('OCR updated')
            st.subheader('Recognition')
            st.write(rec.get('labels', []))
            st.subheader('Metadata')
            st.json(rec.get('metadata', {}))
            note = st.text_area('Add note', '')
            if st.button('Add note'):
                md = rec.get('metadata', {})
                notes_val = md.get('notes','') + '\n' + note if md.get('notes') else note
                md['notes'] = notes_val
                rec['metadata'] = md
                insert_artifact(conn, rec)
                st.success('Note added')
        with right:
            st.image(rec.get('qr_path'), caption='QR code')
            st.write('Reconstruction')
            st.image(rec.get('reconstruction_path'))
            if st.button('Regenerate reconstruction'):
                new_recon = reconstruct_stub(rec['image_path'], aid)
                rec['reconstruction_path'] = new_recon
                insert_artifact(conn, rec)
                st.experimental_rerun()
            if st.button('Generate AI reconstruction (GenAI)'):
                job_id = create_job(conn, aid, 'genai_reconstruct', {'method': os.environ.get('GENAI_PROVIDER')})
                st.success(f'Job submitted (id={job_id})')
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader('Change history')
        changes = list_changes(conn, artifact_id=aid, limit=50)
        for c in changes:
            try:
                payload = json.loads(c[2]) if isinstance(c[2], str) else c[2]
            except Exception:
                payload = c[2]
            st.write(f"{c[3]} — {c[1]}")
            st.json(payload)
        st.markdown('</div>', unsafe_allow_html=True)

# Sidebar: jobs and sync
with st.sidebar:
    st.header('Jobs')
    if st.button('Refresh jobs'):
        st.experimental_rerun()
    jobs = get_pending_jobs(conn, limit=50)
    for j in jobs:
        jid, artid, jtype, params = j
        jinfo = get_job(conn, jid)
        if jinfo:
            st.write(f'Job {jid} — {artid} — {jinfo[4]} — {jinfo[6] or 0}%')
    st.markdown('---')
    st.header('Sync / Export')
    if st.button('Export DB (.db)'):
        dbfile = 'data/sitescan.db'
        with open(dbfile, 'rb') as f:
            st.download_button('Download DB file', data=f, file_name='sitescan.db')
    import_file = st.file_uploader('Import DB (merge)', type=['db'])
    if import_file is not None:
        tmp = 'data/_import_tmp.db'
        with open(tmp, 'wb') as f:
            f.write(import_file.getbuffer())
        ok = merge_db_file(conn, tmp)
        if ok:
            st.success('Imported and merged records')
        else:
            st.error('Import failed')

st.markdown('</div>', unsafe_allow_html=True)

# start a lightweight in-process job worker if not already
def start_worker_once():
    if 'worker_started' in st.session_state:
        return
    def worker():
        c = get_conn()
        while True:
            pending = get_pending_jobs(c, limit=5)
            if not pending:
                time.sleep(2)
                continue
            for job in pending:
                jid, artid, jtype, params = job
                update_job(c, jid, status='running', progress=5)
                rec = get_artifact(c, artid)
                if not rec:
                    update_job(c, jid, status='failed', result='artifact missing')
                    continue
                method = (json.loads(params).get('method') if params else None) or os.environ.get('GENAI_PROVIDER')
                result_path = None
                try:
                    if method == 'replicate':
                        result_path = generate_reconstruction_genai(rec['image_path'], artid)
                    elif method in ('huggingface','hf'):
                        result_path = generate_reconstruction_huggingface(rec['image_path'], artid)
                    else:
                        result_path = reconstruct_stub(rec['image_path'], artid)
                    if result_path:
                        rec['reconstruction_path'] = result_path
                        insert_artifact(c, rec)
                        update_job(c, jid, status='succeeded', result=result_path, progress=100)
                    else:
                        update_job(c, jid, status='failed', result='no result')
                except Exception as e:
                    update_job(c, jid, status='failed', result=str(e))
            time.sleep(1)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    st.session_state['worker_started'] = True

start_worker_once()
import streamlit as st
from db import get_conn, insert_artifact, get_artifact, list_artifacts
from utils import generate_id, timestamp, save_image_file, run_ocr, recognize_image, generate_qr, reconstruct_stub, image_to_datauri
from utils import generate_reconstruction_genai, get_replicate_latest_version, generate_reconstruction_huggingface
from db import create_job, get_pending_jobs, update_job, get_job
import threading
import time
import os
import json
from urllib.parse import urlencode

st.set_page_config(page_title='SiteScan 2.0', layout='wide')

# Inject custom CSS to mimic screenshot theme and layout
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root { --theme: #2D5F4C; --accent:#2D5F4C; --muted:#e9f1ec; --card-radius:12px; --text:#2b3f35 }
html, body, [data-testid='stAppViewContainer'] {
    background: linear-gradient(180deg, #f6faf6 0%, #f2f6f2 100%);
    font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    color: var(--text);
}
/* Top navigation bar */
.top-nav {
    background: var(--theme);
    color: white;
    padding: 14px 28px;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    display:flex; align-items:center; gap:18px; position:sticky; top:0; z-index:9999;
}
.top-nav .brand { font-family: Merriweather, serif; font-weight:700; font-size:20px; color:white; margin-right:18px; }
.top-nav .nav-item { color: rgba(255,255,255,0.95); margin-right:12px; font-weight:600; }
.top-nav .nav-item:hover { opacity:0.95; text-decoration:underline; }

/* Centered main container */
.main-container { max-width:1100px; margin:28px auto; }
.main-container .card { max-width:720px; margin: 22px auto; }
.card { background: white; border-radius: var(--card-radius); padding:26px 26px 30px 26px; box-shadow: 0 12px 28px rgba(17,24,39,0.08); }
.card h2 { color: var(--text); font-family: Merriweather, serif; }

/* Form styles */
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div>div {
    border-radius:10px !important; border:1px solid #e2efe6 !important; padding:10px !important;
}
.stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus { outline: 2px solid rgba(45,95,76,0.12) !important; }
.stButton>button { background:var(--theme) !important; color:white !important; border-radius:10px !important; padding:10px 16px !important; box-shadow: none !important; }
.stButton>button:hover { filter:brightness(0.95); }
.stFileUploader>div>label { border:2px dashed rgba(45,95,76,0.22) !important; border-radius:10px !important; padding:28px !important; background: linear-gradient(180deg, rgba(45,95,76,0.02), transparent); min-height:220px; display:flex; align-items:center; justify-content:center; }
.stFileUploader>div>label .stButton, .stFileUploader>div>label input { display:none !important; }
.stFileUploader>div>label:before { content: ''; display:block; width:72px; height:72px; background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="%232D5F4C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2" ry="2"></rect><path d="M16 3l-2 3h-4l-2-3"></path><circle cx="12" cy="13" r="3"></circle></svg>') ; background-repeat:no-repeat; background-position:center; margin-bottom:8px; }
.stFileUploader>div>label .uploader-text { display:block; color:var(--theme); margin-top:10px; font-weight:600; }

/* Accent elements */
.badge, .info { background: var(--theme); color: white; padding:6px 10px; border-radius:8px; font-weight:600; }
.small-accent { color: var(--theme); }

/* Sidebar tweaks */
.css-1lcbmhc.e1fqkh3o2 { background: linear-gradient(180deg, #f6faf6, #f2f6f2); }

/* Make QR and recon captions use theme */
.stImage>figcaption { color: var(--theme) !important; }

/* Small responsive adjustments */
@media (max-width:900px) { .main-container { padding:12px; } .top-nav { padding:10px; } .main-container .card { margin:12px; } }
</style>
""", unsafe_allow_html=True)

# Render top nav (matches screenshots)
st.markdown("""
<div class="top-nav">
    <div class="brand">SiteScan</div>
    <div class="nav-item">Capture</div>
    <div class="nav-item">Gallery</div>
    <div class="nav-item">Notes</div>
    <div style="flex:1"></div>
    <div class="nav-item">Quick Note</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-container">', unsafe_allow_html=True)

conn = get_conn()

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<h1 style="margin:0; font-family:Merriweather, serif;">SiteScan</h1><p style="margin-top:6px; color:#476a57;">Capture and preserve archaeological discoveries</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# open main card for content
st.markdown('<div class="card" style="margin-top:18px;">', unsafe_allow_html=True)

# Sidebar: upload / scan
st.sidebar.header('Scan / Upload')
upload = st.sidebar.file_uploader('Upload artifact image (photo or scan)', type=['png','jpg','jpeg','tif'])
site_name = st.sidebar.text_input('Site name', value='Unnamed Site')
spot = st.sidebar.text_input('Digging spot / context', value='')
fragile = st.sidebar.checkbox('Fragile', value=False)
tags = st.sidebar.text_input('Tags (comma separated)', value='')
notes = st.sidebar.text_area('Quick notes', value='')

# simple edit control: editing restricted unless password is provided
try:
    AUTH_PASSWORD = st.secrets.get('AUTH_PASSWORD', None)
except Exception:
    AUTH_PASSWORD = None
edit_pw = st.sidebar.text_input('Editor password (if set)', type='password')
can_edit = True if (AUTH_PASSWORD is None or edit_pw == AUTH_PASSWORD) else False
if not can_edit:
    st.sidebar.warning('Editing is restricted — provide correct password to edit records')

if upload is not None:
    if st.sidebar.button('Create artifact record'):
        aid = generate_id()
        img_path = save_image_file(upload, aid)
        ocr_text = run_ocr(img_path)
        labels = recognize_image(img_path)
        qr_path = generate_qr(aid, base_url=st.query_params.get('base_url', [None])[0])
        recon_path = reconstruct_stub(img_path, aid)
        record = {
            'id': aid,
            'filename': upload.name,
            'image_path': img_path,
            'qr_path': qr_path,
            'ocr_text': ocr_text,
            'labels': labels,
            'reconstruction_path': recon_path,
            'metadata': {
                'site': site_name,
                'spot': spot,
                'fragile': fragile,
                'tags': [t.strip() for t in tags.split(',') if t.strip()],
                'notes': notes
            },
            'created_at': timestamp()
        }
        insert_artifact(conn, record)
        st.success(f'Artifact created: {aid}')
        st.image(img_path, caption='Uploaded image')
        st.image(qr_path, caption='QR Code')
        st.image(recon_path, caption='AI Reconstruction (estimated)')

# Main area: search / list
st.header('Artifacts')
q = st.text_input('Search by ID, site, filename, tags', value='')
site_filter = st.selectbox('Filter by site', options=[''] + sorted(list({json.loads(r[3])['site'] for r in list_artifacts(conn, limit=500) if r and r[3]})) if False else [''])
spot_filter = st.text_input('Filter by spot', value='')
rows = []
if q.strip() or site_filter or spot_filter:
    rows = search_artifacts(conn, query=q or None, site=site_filter or None, spot=spot_filter or None, limit=500)
else:
    rows = list_artifacts(conn, limit=200)
filtered = rows

cols = st.columns(3)
for i, item in enumerate(filtered):
    aid, fname, imgpath, created = item
    col = cols[i % 3]
    with col:
        col.image(imgpath, use_column_width=True)
        if col.button('Open', key=f'open-{aid}'):
            st.experimental_set_query_params(id=aid)
            st.experimental_rerun()
        col.write(aid)
        col.write(fname)

# Detail view
params = st.experimental_get_query_params()
if 'id' in params:
    aid = params['id'][0]
    rec = get_artifact(conn, aid)
    if rec:
        st.header(f"Artifact: {aid}")
        left, right = st.columns([2,1])
        with left:
            st.image(rec['image_path'], caption='Artifact Image', use_column_width=True)
            st.subheader('OCR')
            edited = st.text_area('Edit OCR result before saving', value=rec.get('ocr_text',''))
            if st.button('Save OCR'):
                if can_edit:
                    rec['ocr_text'] = edited
                    insert_artifact(conn, rec)
                    st.success('OCR updated')
                else:
                    st.error('Not authorized to edit')
            st.subheader('Recognition')
            st.write(rec.get('labels', []))
            st.subheader('Metadata')
            st.json(rec.get('metadata', {}))
            st.subheader('Notes')
            note = st.text_area('Add note', '')
            if st.button('Add note'):
                if can_edit:
                    md = rec.get('metadata', {})
                    notes = md.get('notes','') + '\n' + note if md.get('notes') else note
                    md['notes'] = notes
                    rec['metadata'] = md
                    insert_artifact(conn, rec)
                    st.success('Note added')
                else:
                    st.error('Not authorized to edit')
        with right:
            st.image(rec.get('qr_path'), caption='QR code')
            st.write('Reconstruction (estimated)')
            st.image(rec.get('reconstruction_path'))
            if st.button('Regenerate reconstruction'):
                if can_edit:
                    new_recon = reconstruct_stub(rec['image_path'], aid)
                    rec['reconstruction_path'] = new_recon
                    insert_artifact(conn, rec)
                    st.experimental_rerun()
                else:
                    st.error('Not authorized to regenerate')

            # GenAI reconstruction using provider (Replicate) if configured
            import os
            if os.environ.get('GENAI_PROVIDER') == 'replicate' and os.environ.get('GENAI_TOKEN') and os.environ.get('GENAI_MODEL_VERSION'):
                    if st.button('Generate AI reconstruction (GenAI)'):
                        if can_edit:
                            # submit job instead of synchronous call
                            job_id = create_job(conn, aid, 'genai_reconstruct', {'method': os.environ.get('GENAI_PROVIDER')})
                            st.success(f'Job submitted (id={job_id}). Refresh or view Jobs to see progress.')
                            st.experimental_rerun()
                        else:
                            st.error('Not authorized to generate')

        # Jobs panel
        st.sidebar.header('Jobs')
        if st.sidebar.button('Refresh jobs'):
            st.experimental_rerun()
        jobs = get_pending_jobs(conn, limit=50)
        for j in jobs:
            jid, artid, jtype, params = j
            st.sidebar.write(f'Job {jid} — artifact {artid} — {jtype}')
            jinfo = get_job(conn, jid)
            if jinfo:
                st.sidebar.write(f'Status: {jinfo[4]}, progress: {jinfo[6] or 0}%')


    # Background worker: process pending jobs (singleton across reruns)
    def _start_background_worker():
        def worker():
            c = get_conn()
            while True:
                pending = get_pending_jobs(c, limit=5)
                if not pending:
                    time.sleep(2)
                    continue
                for job in pending:
                    jid, artid, jtype, params = job
                    # mark running
                    update_job(c, jid, status='running', progress=5)
                    # fetch artifact
                    rec = get_artifact(c, artid)
                    if not rec:
                        update_job(c, jid, status='failed', result='artifact not found')
                        continue
                    method = (json.loads(params).get('method') if params else None) or os.environ.get('GENAI_PROVIDER')
                    result_path = None
                    try:
                        if method == 'replicate':
                            # ensure we have a model version; try to auto-resolve if not set
                            mv = os.environ.get('GENAI_MODEL_VERSION')
                            if not mv:
                                mv = get_replicate_latest_version('stability-ai/stable-diffusion')
                                if mv:
                                    os.environ['GENAI_MODEL_VERSION'] = mv
                            update_job(c, jid, progress=15)
                            result_path = generate_reconstruction_genai(rec['image_path'], artid)
                        elif method == 'huggingface' or method == 'hf':
                            update_job(c, jid, progress=10)
                            result_path = generate_reconstruction_huggingface(rec['image_path'], artid)
                        else:
                            # fallback to local heuristic stub
                            update_job(c, jid, progress=10)
                            result_path = reconstruct_stub(rec['image_path'], artid)
                        if result_path:
                            rec['reconstruction_path'] = result_path
                            insert_artifact(c, rec)
                            update_job(c, jid, status='succeeded', result=result_path, progress=100)
                        else:
                            update_job(c, jid, status='failed', result='no result from provider', progress=0)
                    except Exception as e:
                        update_job(c, jid, status='failed', result=str(e), progress=0)
                time.sleep(1)

        # ensure only one worker thread starts
        if 'site_worker_started' not in st.session_state:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            st.session_state['site_worker_started'] = True


    _start_background_worker()

    st.subheader('Change history')
    changes = list_changes(conn, artifact_id=aid, limit=50)
    for c in changes:
        try:
            payload = json.loads(c[2]) if isinstance(c[2], str) else c[2]
        except Exception:
            payload = c[2]
        st.write(f"{c[3]} — {c[1]}")
        st.json(payload)

# Export / import DB for simple offline sync
st.sidebar.header('Sync / Export')
if st.sidebar.button('Export DB (.db)'):
    dbfile = 'data/sitescan.db'
    with open(dbfile, 'rb') as f:
        st.sidebar.download_button('Download DB file', data=f, file_name='sitescan.db')

import_file = st.sidebar.file_uploader('Import DB (merge)', type=['db'])
if import_file is not None:
    # write temp file and attempt merge
    tmp = 'data/_import_tmp.db'
    with open(tmp, 'wb') as f:
        f.write(import_file.getbuffer())
    ok = None
    try:
        ok = merge_db_file(conn, tmp)
    except Exception:
        ok = False
    if ok:
        st.sidebar.success('Imported and merged records (new records added)')
    else:
        st.sidebar.error('Import failed — file may be invalid')

st.sidebar.markdown('---')
st.sidebar.markdown('Theme color: #2D5F4C')

# close main container
st.markdown('</div>', unsafe_allow_html=True)


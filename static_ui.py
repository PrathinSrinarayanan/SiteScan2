import streamlit as st

st.set_page_config(page_title='SiteScan - Mock UI', layout='wide')

static_html = r"""
<div style="font-family:Inter, system-ui, -apple-system, 'Segoe UI', Roboto;">
  <div style="background:#2D5F4C;color:#fff;padding:14px 28px;position:sticky;top:0;z-index:9999;display:flex;align-items:center;">
    <div style="font-family:Merriweather, serif;font-weight:700;font-size:18px;margin-right:20px;">SiteScan</div>
    <div style="display:flex;gap:12px;align-items:center;font-weight:600;opacity:0.95;"> 
      <div style="padding:6px 10px;border-radius:8px;background:rgba(255,255,255,0.03)">Capture</div>
      <div>Gallery</div>
      <div>Notes</div>
    </div>
    <div style="flex:1"></div>
    <div style="font-weight:600;">Quick Note</div>
  </div>

  <div style="max-width:1100px;margin:28px auto;text-align:center;">
    <h1 style="font-family:Merriweather, serif;color:#214b39;margin:16px 0 6px 0;font-size:42px;">SiteScan</h1>
    <p style="margin:0;color:#5e7a6a;">Capture and preserve archaeological discoveries</p>
  </div>

  <div style="max-width:720px;margin:28px auto;background:#fff;border-radius:12px;padding:22px 28px;box-shadow:0 12px 28px rgba(17,24,39,0.08)">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;border-bottom:1px solid #eef6f0;padding-bottom:12px">
      <div style="width:36px;height:36px;border-radius:8px;background:#f3faf6;display:flex;align-items:center;justify-content:center;color:var(--theme)">📷</div>
      <div style="font-weight:700;color:#214b39;font-size:18px">New Discovery</div>
    </div>

    <div style="margin-top:12px">
      <label style="display:block;font-size:13px;color:#5d6f66;margin-bottom:6px">Artifact Photo *</label>
      <div style="border:2px dashed rgba(45,95,76,0.22);border-radius:8px;min-height:200px;display:flex;align-items:center;justify-content:center;background:linear-gradient(180deg, rgba(45,95,76,0.02), transparent);">
        <div style="text-align:center;color:#2D5F4C;font-weight:600">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="7" width="18" height="13" rx="2" ry="2" stroke="#2D5F4C" stroke-width="1.5" fill="none"></rect><path d="M16 3l-2 3h-4l-2-3" stroke="#2D5F4C" stroke-width="1.5" fill="none"></path><circle cx="12" cy="13" r="3" stroke="#2D5F4C" stroke-width="1.5" fill="none"></circle></svg>
          <div style="margin-top:8px">Tap to capture photo</div>
        </div>
      </div>
    </div>

    <div style="margin-top:16px">
      <label style="font-size:13px;color:#5d6f66">Artifact Name</label>
      <input placeholder="e.g., Pottery Fragment, Stone Tool, etc." style="width:100%;padding:8px;border-radius:6px;border:1px solid #e6efe9;margin-top:6px;" />
    </div>

    <div style="margin-top:12px">
      <label style="font-size:13px;color:#5d6f66">Description & Notes</label>
      <textarea placeholder="AI-generated description will appear here..." style="width:100%;height:110px;padding:8px;border-radius:6px;border:1px solid #e6efe9;margin-top:6px;"></textarea>
      <div style="font-size:11px;color:#93a69a;margin-top:6px">AI-generated description - you can edit before saving</div>
    </div>

    <div style="margin-top:14px;display:flex;align-items:center;gap:10px">
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:42px;height:26px;border-radius:6px;background:#2D5F4C;border:2px solid rgba(0,0,0,0.06)"></div>
        <div style="background:#f3f6f3;padding:4px 8px;border-radius:6px;border:1px solid #e9efe9;font-size:12px;color:#2D5F4C">#2D5F4C</div>
      </div>
    </div>

    <div style="margin-top:18px;">
      <button style="width:100%;background:#9bb0a6;color:#fff;padding:12px;border-radius:10px;border:none;font-weight:700;display:flex;align-items:center;justify-content:center;gap:8px">⬇ Save Artifact</button>
    </div>
  </div>
</div>
"""

st.markdown(static_html, unsafe_allow_html=True)
st.stop()

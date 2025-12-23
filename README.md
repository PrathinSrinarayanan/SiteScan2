# SiteScan 2.0 — Streamlit Prototype

Theme color: #2D5F4C

This repository is a prototype Streamlit app for archaeological artifact scanning and management (SiteScan 2.0). It includes:

- Image upload / "scan" flow with unique artifact IDs
- OCR extraction (pytesseract) with edit-before-save
- Image recognition using MobileNetV2 (TensorFlow)
- QR code generation linking to artifact record
- AI reconstruction stub (labeled "AI-estimated")
- SQLite centralized DB (single-file) saved under `data/`
- Export / import to support simple offline-to-online workflows

Note: This is a prototype. For production-grade mobile offline-first functionality, a dedicated mobile PWA + background sync + server is recommended.

Quick start (Windows):

1. Install Python 3.10+ and create a venv

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Install Tesseract OCR engine (required for OCR):
- Windows: install from https://github.com/tesseract-ocr/tesseract/wiki
- Linux (Debian/Ubuntu): `sudo apt-get install tesseract-ocr`

3. Run the app locally:

```bash
streamlit run app.py
```

4. To publish on Streamlit Cloud:
- Push this repo to GitHub (see instructions below)
- Create an app on Streamlit Cloud and connect the repository
- Add any necessary secrets (e.g., API keys) via Streamlit Cloud settings

Streamlit Cloud notes:
- To enable restricted editing, add a secret named `AUTH_PASSWORD` in Streamlit Cloud settings.
- Large ML models (TensorFlow) may not be available on Streamlit's free runtime; consider using a small recognition stub or a hosted model.
 - Large ML models (TensorFlow) may not be available on Streamlit's free runtime; consider using a small recognition stub or a hosted model.

GenAI reconstruction (Replicate)
--------------------------------
This prototype includes optional GenAI reconstruction support using Replicate. To enable:

1. Get a Replicate API token from https://replicate.com/account.
2. Choose a model version that supports image-to-image (e.g. a Stable Diffusion image-to-image version) and copy its "model version" id from the model page.
3. Set environment variables in your deployment (or locally) before running Streamlit:

```bash
set GENAI_PROVIDER=replicate
set GENAI_TOKEN=your_replicate_token_here
set GENAI_MODEL_VERSION=your_model_version_id_here
```

4. In the artifact detail view, use "Generate AI reconstruction (GenAI)" to call the provider and save the returned image to the artifact record.

Notes:
- The app polls the Replicate prediction until completion (with a timeout). Large models may take several seconds to minutes.
- If your chosen runtime (e.g., Streamlit Cloud) cannot run heavy ML or external HTTP calls, run the GenAI flow from a separate server or locally.

Recommended model (Replicate)
-----------------------------
- Recommended model to start with: `stability-ai/stable-diffusion` (image-to-image workflows).
- The Replicate API requires a *model version id* (a long id string). Instead of hard-coding a version id (which can change), the prototype includes a helper to fetch the latest version from the Replicate API. If you prefer a specific version, copy the version id from the model page on Replicate and set it as `GENAI_MODEL_VERSION`.

Hugging Face / Stability options
--------------------------------
- The app also supports a basic Hugging Face Inference API path: set `GENAI_PROVIDER=huggingface` and `GENAI_TOKEN` to your HF token, and set `GENAI_MODEL_VERSION` to the model repo id (for example: `runwayml/stable-diffusion-v1-5`).
- For Stability.ai, consider using the Stability REST API on a separate worker service and call it from the background worker (not included in this prototype).

Background job processing
-------------------------
GenAI reconstruction is now submitted as a background `job` (stored in the local SQLite `jobs` table). A background worker thread in the Streamlit process picks up pending jobs and runs them, updating job progress and saving results to the artifact record. This avoids blocking the UI and enables progress monitoring.

Notes about model versions and runtime
-------------------------------------
- If you want me to set a specific Replicate model *version id* for you, provide the version id string and I will add it to the repo as a default example. Alternatively, I can call the Replicate API to auto-resolve the latest version when `GENAI_MODEL_VERSION` is not provided.
- For production, run the background worker on a separate server or serverless function to avoid running long jobs inside Streamlit; the current prototype keeps it in-process for simplicity.

Pushing to GitHub (example):

```bash
git init
git add .
git commit -m "SiteScan 2.0 prototype"
git branch -M main
# create remote and push (replace URL)
git remote add origin https://github.com/yourname/SiteScan2.git
git push -u origin main
```

Files of interest:
- `app.py` — Streamlit application (single-file prototype)
- `db.py` — SQLite helpers
- `utils.py` — OCR, recognition, QR, reconstruction helpers
- `requirements.txt` — Python dependencies
- `data/` — persistent storage (images, qrcodes, reconstructions, `sitescan.db`)

Limitations & Next steps:
- Offline-first mobile scanning (background sync, local QR fallback) is nontrivial in Streamlit; consider building a mobile PWA or native app for full offline workflow.
- For higher-quality reconstructions, integrate a generative model (Stable Diffusion/Replicate/OpenAI) and provide API-key protected hooks.
- Add auth and role-based editing for security in multi-user deployments.

If you want, I can:
- Push this scaffold to a GitHub repo for you (I'll produce exact git commands), or
- Add Stable Diffusion integration (requires API key), or
- Convert to a PWA frontend + small API server for robust offline sync.

Completed features in this prototype:
- Image upload and unique artifact IDs
- OCR extraction and edit-before-save
- Image recognition using MobileNetV2 when available
- QR generation per artifact
- AI reconstruction stub saved to `data/reconstructions`
- Simple merge import to combine DB files without creating duplicate IDs
- Change history stored in `changes` table

Limitations (important):
- Streamlit is not a full offline-first mobile client; offline scanning on mobile devices is best handled by a PWA or native app.
- TensorFlow MobileNet may be heavy for Streamlit Cloud; you can set the app to skip recognition if runtime lacks support.

GitHub push commands:

```bash
git init
git add .
git commit -m "SiteScan 2.0 prototype"
git branch -M main
# add your remote and push
git remote add origin https://github.com/yourname/SiteScan2.git
git push -u origin main
```


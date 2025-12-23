import uuid
from pathlib import Path
from datetime import datetime
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import qrcode
import io
import base64
import os
import time
import requests
from typing import Optional

# TensorFlow model (lazy load)
_tf_model = None


def generate_id():
    return str(uuid.uuid4())


def timestamp():
    return datetime.utcnow().isoformat() + 'Z'


def ensure_dirs():
    Path('data/images').mkdir(parents=True, exist_ok=True)
    Path('data/qrcodes').mkdir(parents=True, exist_ok=True)
    Path('data/reconstructions').mkdir(parents=True, exist_ok=True)


def save_image_file(uploaded_file, artifact_id):
    ensure_dirs()
    ext = Path(uploaded_file.name).suffix or '.png'
    out_path = Path('data/images') / f"{artifact_id}{ext}"
    with open(out_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return str(out_path)


def run_ocr(image_path):
    try:
        img = Image.open(image_path).convert('L')
        # basic preprocessing
        img = ImageOps.autocontrast(img)
        txt = pytesseract.image_to_string(img)
        return txt.strip()
    except Exception as e:
        return ''


def _load_tf_model():
    global _tf_model
    if _tf_model is None:
        try:
            from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, decode_predictions, preprocess_input
            model = MobileNetV2(weights='imagenet')
            _tf_model = (model, preprocess_input, decode_predictions)
        except Exception:
            _tf_model = None
    return _tf_model


def recognize_image(image_path, top=3):
    model_tuple = _load_tf_model()
    if model_tuple is None:
        return []
    model, preprocess_input, decode_predictions = model_tuple
    img = Image.open(image_path).convert('RGB').resize((224,224))
    arr = np.array(img)
    x = np.expand_dims(arr, axis=0).astype('float32')
    x = preprocess_input(x)
    preds = model.predict(x)
    decoded = decode_predictions(preds, top=top)[0]
    return [{'label': p[1], 'score': float(p[2])} for p in decoded]


def generate_qr(artifact_id, base_url=None):
    ensure_dirs()
    if base_url:
        url = f"{base_url}?id={artifact_id}"
    else:
        url = f"{artifact_id}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2D5F4C", back_color="white")
    out_path = Path('data/qrcodes') / f"{artifact_id}.png"
    img.save(out_path)
    return str(out_path)


def reconstruct_stub(image_path, artifact_id):
    # Simple heuristic reconstruction: upscale + slight denoise + mirror to "fill" missing pieces.
    ensure_dirs()
    img = Image.open(image_path).convert('RGB')
    w,h = img.size
    # upscale
    recon = img.resize((int(w*1.6), int(h*1.6)), Image.LANCZOS)
    # slight blur and sharpen to create "estimated" look
    recon = recon.filter(ImageFilter.GaussianBlur(radius=1))
    recon = ImageOps.autocontrast(recon)
    # save
    out_path = Path('data/reconstructions') / f"{artifact_id}.png"
    recon.save(out_path)
    return str(out_path)


def _download_image_to_path(url, out_path):
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def generate_reconstruction_genai(image_path, artifact_id, prompt=None, timeout=180):
    """
    Generate an AI reconstruction using a configured provider.

    Current supported provider: 'replicate' via environment vars:
      - GENAI_PROVIDER=replicate
      - GENAI_TOKEN=<replicate api token>
      - GENAI_MODEL_VERSION=<replicate model version id>

    The function will POST a prediction request and poll until completion, then download
    the resulting image to `data/reconstructions/{artifact_id}_ai.png`.
    """
    provider = os.environ.get('GENAI_PROVIDER')
    token = os.environ.get('GENAI_TOKEN')
    model_version = os.environ.get('GENAI_MODEL_VERSION')
    ensure_dirs()
    out_path = Path('data/reconstructions') / f"{artifact_id}_ai.png"

    if provider != 'replicate' or not token or not model_version:
        return None

    # read image and convert to data URI
    with open(image_path, 'rb') as f:
        b = f.read()
    data_uri = image_to_datauri(image_path)

    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'version': model_version,
        'input': {
            'image': data_uri,
            'prompt': prompt or 'AI-based reconstruction of an archaeological artifact; realistic, natural textures, fill missing parts'
        }
    }
    try:
        resp = requests.post('https://api.replicate.com/v1/predictions', json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pred_id = data.get('id')
        if not pred_id:
            return None
        # poll
        start = time.time()
        status = data.get('status')
        poll_url = f'https://api.replicate.com/v1/predictions/{pred_id}'
        while status not in ('succeeded', 'failed') and (time.time() - start) < timeout:
            time.sleep(2)
            r = requests.get(poll_url, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            status = data.get('status')
        if status != 'succeeded':
            return None
        output = data.get('output')
        # output is typically a list of URLs
        if not output:
            return None
        img_url = output[0]
        ok = _download_image_to_path(img_url, out_path)
        if ok:
            return str(out_path)
    except Exception:
        return None
    return None


def get_replicate_latest_version(model_name: str, token: Optional[str] = None) -> Optional[str]:
    """
    Fetch the latest model version id from Replicate for a given `owner/model` string.
    Returns the version id string or None.
    """
    token = token or os.environ.get('GENAI_TOKEN')
    if not token:
        return None
    headers = {'Authorization': f'Token {token}'}
    url = f'https://api.replicate.com/v1/models/{model_name}'
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        d = r.json()
        versions = d.get('versions')
        if not versions:
            return None
        # choose first version (most recent)
        return versions[0].get('id')
    except Exception:
        return None


def generate_reconstruction_huggingface(image_path, artifact_id, prompt=None):
    """
    Basic Hugging Face Inference API integration (requires HF token in GENAI_TOKEN and model id in GENAI_MODEL_VERSION).
    This attempts to call the model endpoint and save a single image result.
    """
    hf_token = os.environ.get('GENAI_TOKEN')
    model = os.environ.get('GENAI_MODEL_VERSION')
    ensure_dirs()
    out_path = Path('data/reconstructions') / f"{artifact_id}_ai_hf.png"
    if not hf_token or not model:
        return None
    headers = {'Authorization': f'Bearer {hf_token}'}
    url = f'https://api-inference.huggingface.co/models/{model}'
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            payload = {'inputs': prompt or 'AI reconstruction of an archaeological artifact, fill missing parts, photorealistic'}
            r = requests.post(url, headers=headers, data=payload, files=files, timeout=120)
            r.raise_for_status()
            # HF may return an image directly
            content_type = r.headers.get('content-type','')
            if 'image' in content_type:
                with open(out_path, 'wb') as out:
                    out.write(r.content)
                return str(out_path)
            # or JSON with output URL(s)
            j = r.json()
            if isinstance(j, dict) and 'generated_image' in j:
                img_url = j['generated_image']
                if _download_image_to_path(img_url, out_path):
                    return str(out_path)
    except Exception:
        return None
    return None


def image_to_datauri(path):
    with open(path, 'rb') as f:
        data = f.read()
    mime = 'image/png'
    b64 = base64.b64encode(data).decode('utf-8')
    return f"data:{mime};base64,{b64}"


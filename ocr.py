import os
from typing import Tuple, List, Dict
from PIL import Image, ImageOps, ImageFilter
import io
import pytesseract

MIN_CONF = int(os.getenv("MIN_CONFIDENCE", "60"))
TESS_LANG = os.getenv("TESS_LANG", "nor+eng")

def preprocess(img: Image.Image) -> Image.Image:
    # Grayscale, liten skarphet og binarisering hjelper ofte
    g = ImageOps.grayscale(img)
    g = g.filter(ImageFilter.SHARPEN)
    # Hev kontrast via autokontrast
    g = ImageOps.autocontrast(g)
    return g

def ocr_image_bytes(raw: bytes) -> Tuple[str, List[Dict]]:
    img = Image.open(io.BytesIO(raw))
    img = preprocess(img)
    # Fulltekst
    text = pytesseract.image_to_string(img, lang=TESS_LANG)
    # Ord med koordinater/konfidens – kan brukes senere for mer avansert parsing
    data = pytesseract.image_to_data(img, lang=TESS_LANG, output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data["text"])):
        conf = int(data["conf"][i]) if data["conf"][i].isdigit() else -1
        if conf < MIN_CONF:
            continue
        w = data["text"][i].strip()
        if not w:
            continue
        words.append({
            "text": w,
            "conf": conf,
            "left": data["left"][i],
            "top": data["top"][i],
            "width": data["width"][i],
            "height": data["height"][i],
        })
    return text, words

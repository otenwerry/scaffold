import config

from Foundation import NSURL
from Vision import (
    VNImageRequestHandler,
    VNRecognizeTextRequest,
    VNRequestTextRecognitionLevelAccurate,
)
import mss
import tempfile
import os

def ocr():
    # Capture screenshot and convert to PNG
    try:
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        print(f"[{config.timestamp()}] Screenshot: Captured for OCR")
    except Exception as e:
        print(f"Screenshot: Error occurred: {e}")
        return ""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(png_bytes)
        tmp_path = tmp.name
    try:
        url = NSURL.fileURLWithPath_(tmp_path)
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)
        request.setRecognitionLanguages_(["en-US"])
        handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
        ok, err = handler.performRequests_error_([request], None)
        if not ok:
            raise RuntimeError(f"Vision API: Error performing request: {err}")
        observations = request.results() or []
        lines = []
        for obs in observations:
            candidates = obs.topCandidates_(1)
            if candidates:
                lines.append(str(candidates[0].string()))
        text = "\n".join(lines)
        print(f"OCR: Apple OCR: {len(text)} characters")
        return text.strip()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

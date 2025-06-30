from http.server import BaseHTTPRequestHandler
import json
from entropy import info_content_background_corrected  # assume entropy.py lives alongside this file

from sanic import Sanic
from sanic.response import json

app = Sanic("score_app")

@app.post("/")  # this maps to POST /api/score
def score(request):
    payload = request.json or {}
    text = payload.get("text", "")
    total_bits, avg_bits = info_content_background_corrected(text)
    return json({"total_bits": total_bits, "avg_bits": avg_bits})

import json
from entropy import entropy_bits
from supabase import create_client
import os

# initialize supabase admin client
SUPA_URL    = os.getenv("SUPABASE_URL")
SUPA_KEY    = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb          = create_client(SUPA_URL, SUPA_KEY)

def handler(request, response):
    data = request.get_json()
    text = data.get("text", "")
    total, per_token = entropy_bits(text)
    # log to Supabase
    sb.table("entropy_logs").insert({
        "input_text": text,
        "bits_per_token": per_token
    }).execute()
    response.status(200).json({"bits_per_token": per_token})
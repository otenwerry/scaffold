# api/calculate.py
import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
from supabase import create_client, Client

# Import your functions from entropy.py
# Ensure your entropy.py file is in the root directory
import sys
sys.path.append(os.path.realpath(".."))
from entropy import info_content, model, tokenizer # Pre-load models by importing them

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        text_input = data.get('text')

        if not text_input:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Text input is required"}).encode())
            return

        try:
            # Calculate the score using your pre-loaded model
            # We'll use "bits per token" as the score
            total_bits, per_token_bits = info_content(text_input)

            # Save to Supabase
            db_response = supabase.table('history').insert({
                "text_input": text_input,
                "score": per_token_bits
            }).execute()

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"score": per_token_bits, "data": db_response.data}
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
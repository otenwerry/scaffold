import json
from lib.entropy import info_content

def handler(request):
    # Only accept POST
    if request.method != "POST":
        return {"statusCode": 405}

    payload = request.json()
    text = payload.get("content", "")

    # Compute total & average bits
    total_bits, avg_bits = info_content(text)

    # Return JSON with the entropy_score
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"entropy_score": avg_bits})
    }

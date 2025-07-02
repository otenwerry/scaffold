import json

def count_words(sentence: str) -> int:
    """Return the number of words in the given sentence."""
    return len(sentence.split())

# API handler function

def handler(request):
    # Only accept POST
    if request.method != "POST":
        return {"statusCode": 405}

    payload = request.json()
    sentence = payload.get("sentence", "")
    word_count = count_words(sentence)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"word_count": word_count})
    }

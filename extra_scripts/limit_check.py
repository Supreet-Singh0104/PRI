import requests
import json

API_KEY = ""
BASE_URL = "https://generativelanguage.googleapis.com"


def list_models():
    """List all models available for this API key."""
    url = f"{BASE_URL}/v1beta/models?key={API_KEY}"
    resp = requests.get(url)

    print("=== LIST MODELS RESPONSE ===")
    print("Status code:", resp.status_code)
    print(resp.text)

    if resp.status_code != 200:
        print("\n⚠️ Could not list models. This usually means:")
        print("   - API not enabled for this project, or")
        print("   - Key is invalid / restricted.")
        return None

    data = resp.json()
    print("\nAvailable model names:")
    for m in data.get("models", []):
        print(" -", m.get("name"))
    print()
    return data


def test_model(model_name: str):
    """Send a tiny test request to a specific model."""
    url = f"{BASE_URL}/v1beta/{model_name}:generateContent?key={API_KEY}"

    payload = {
        "contents": [{
            "parts": [{"text": "Hello from limit_check.py"}]
        }]
    }

    resp = requests.post(url, json=payload)

    print(f"\n=== TEST MODEL: {model_name} ===")
    print("Status code:", resp.status_code)
    print(resp.text)

    if resp.status_code == 200:
        print("\n✅ API key is VALID and this model is usable. Quota is available.\n")

    elif resp.status_code == 401:
        print("\n❌ INVALID API KEY (wrong / expired / not recognized)\n")

    elif resp.status_code == 403:
        print("\n❌ Key exists but you DO NOT have permission for this model.\n")

    elif resp.status_code == 429:
        print("\n⚠️ QUOTA EXCEEDED or RATE LIMIT HIT for this key.\n")

    else:
        print("\n⚠️ Unexpected error (check above JSON for details).\n")


if __name__ == "__main__":
    # 1. First list all models this key can actually see
    models_data = list_models()

    # 2. Optionally, automatically test first Gemini model if found
    if models_data and "models" in models_data and models_data["models"]:
        # Find a model whose name contains "gemini"
        gemini_model = None
        for m in models_data["models"]:
            name = m.get("name", "")
            if "gemini" in name:
                gemini_model = name
                break

        if gemini_model:
            test_model(gemini_model)
        else:
            print("No 'gemini' models found in list. Check model names above.")

import os
import json
import urllib.request

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found.")
    print("Run: export OPENAI_API_KEY=your_key")
    exit(1)

prompt = input("Enter prompt: ")

data = json.dumps({
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "user", "content": prompt}
    ]
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=data,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)

try:
    with urllib.request.urlopen(req) as res:
        status = res.status
        body = res.read().decode()

    if status != 200:
        print("Error status:", status)
        print(body)
    else:
        response = json.loads(body)
        print("OpenAI response:", response["choices"][0]["message"]["content"])

except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode())

except Exception as e:
    print("Error:", str(e))
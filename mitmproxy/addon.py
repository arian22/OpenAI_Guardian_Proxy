from mitmproxy import http
import httpx
import json
import math
import os


GUARDIAN_URL = os.getenv("GUARDIAN_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUARDIAN_MODEL_NAME = "ibm-granite/granite-guardian-3.1-8b"
OPENAI_MODEL_NAME = "gpt-4o-mini"
GUARDIAN_RISK_THRESHOLD=80

VIOLENCE_KEYWORDS = ["kill", "murder", "shoot", "stab", "bomb", "violent"]
ILLEGAL_KEYWORDS = ["steal", "rob", "hack", "fraud", "illegal"]
SEXUAL_KEYWORDS = ["sex", "nude", "porn", "sexual"]

def classify_prompt(prompt: str) -> str | None:
    text = prompt.lower()

    if any(word in text for word in VIOLENCE_KEYWORDS):
        return "description of violent acts"

    if any(word in text for word in ILLEGAL_KEYWORDS):
        return "inquiries on how to perform an illegal activity"

    if any(word in text for word in SEXUAL_KEYWORDS):
        return "sexual content"

    return None


def guardian_reason(prompt: str) -> str | None:
    text = prompt.lower()
    normalized = "".join(ch for ch in text if ch.isalnum())

    if any(word in normalized for word in VIOLENCE_KEYWORDS):
        return "description of violent acts"

    if any(word in normalized for word in ILLEGAL_KEYWORDS):
        return "inquiries on how to perform an illegal activity"

    if any(word in normalized for word in SEXUAL_KEYWORDS):
        return "sexual content"

    return None


def guardian_says_toxic(prompt: str) -> bool:
    if not GUARDIAN_URL:
        return False

    response = httpx.post(
        GUARDIAN_URL,
        json={
            "model": GUARDIAN_MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 1,
            "logprobs": True,
            "top_logprobs": 5,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()

    choice = payload["choices"][0]

    yes_prob = 0.0
    logprobs = choice.get("logprobs")

    if logprobs and logprobs.get("content"):
        top = logprobs["content"][0].get("top_logprobs", [])
        for item in top:
            token = item.get("token", "").strip().lower()
            if token == "yes":
                yes_prob = math.exp(item["logprob"])
                break

    if yes_prob == 0.0:
        answer = choice["message"]["content"].strip().lower()
        yes_prob = 1.0 if answer.startswith("yes") else 0.0

    score = round(yes_prob * 100)
    print("===============<Guardian>==============")
    print(payload)
    print("Guardian risk level:", score)
    print("===============</Guardian>==============")

    return score >= GUARDIAN_RISK_THRESHOLD

def block(flow: http.HTTPFlow, message: str) -> None:
    flow.response = http.Response.make(
        403,
        json.dumps({"response": message}).encode("utf-8"),
        {"Content-Type": "application/json"},
    )


def request(flow: http.HTTPFlow) -> None:
    if flow.request.path != "/proxy-chat":
        return
    try:
        data = json.loads(flow.request.get_text())
        prompt = data.get("prompt", "").strip()
    except Exception:
        prompt = ""

    reason = classify_prompt(prompt)
    if reason:
        block(flow, f"The prompt was blocked because it contained {reason}")
        return

    try:
        if GUARDIAN_URL and guardian_says_toxic(prompt):
            category = guardian_reason(prompt)
            if category:
                block(flow, f"The prompt was blocked because it contained {category}")
            else:
                block(flow, "The prompt was blocked because it is considered toxic")
            return
    except Exception as exc:
        print(f"Guardian check failed: {exc}")

    if not OPENAI_API_KEY:
        block(flow, "OPENAI_API_KEY is not configured")
        return

    openai_payload = {
        "model": OPENAI_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }
    flow.request.scheme = "https"
    flow.request.host = "api.openai.com"
    flow.request.port = 443
    flow.request.path = "/v1/chat/completions"
    flow.request.method = "POST"
    flow.request.headers["Host"] = "api.openai.com"
    flow.request.headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    flow.request.headers["Content-Type"] = "application/json"
    flow.request.set_text(json.dumps(openai_payload))


def response(flow: http.HTTPFlow) -> None:
    if flow.request.host != "api.openai.com":
        return

    try:
        data = json.loads(flow.response.get_text())
        print("===============<OpenAI>==============")
        print(data)
        print("===============</OpenAI>==============")
        if flow.response.status_code != 200:
            message = data.get("error", {}).get("message", "OpenAI error")
            content = f"Status: {flow.response.status_code}\n{message}"
        else:
            message = data["choices"][0]["message"]["content"]

            if isinstance(message, list):
                content = "".join(
                    part.get("text", "") for part in message if part.get("type") == "text"
                )
            else:
                content = message

    except Exception as exc:
        print(f"OpenAI response parse failed: {exc}")
        print(flow.response.get_text())
        return

    flow.response = http.Response.make(200, json.dumps({"response": content}).encode("utf-8"), {"Content-Type": "application/json"},)
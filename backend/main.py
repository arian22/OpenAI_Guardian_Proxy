from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NGINX_BASE_URL = os.getenv("NGINX_BASE_URL")
NGINX_CA_CERT = os.getenv("NGINX_CA_CERT")

class ChatRequest(BaseModel):
    prompt: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        response = httpx.post(
            f"{NGINX_BASE_URL}/proxy-chat",
            json={"prompt": prompt},
            verify=NGINX_CA_CERT,
            timeout=30.0,
        )

        return response.json()

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/proxy-chat")
def proxy_chat(request: ChatRequest):
    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    return {"response": f"hello, {prompt}"}
# OpenAI Guardian Proxy

## Overview

Frontend → Backend → NGINX (SSL) → mitmproxy → OpenAI

* Prompts are intercepted by mitmproxy
* Checked using:
  * A simple classifier
  * IBM Granite Guardian
* Unsafe prompts are blocked before reaching OpenAI

---

## Step 1 – Direct OpenAI Call

Set your API key:

```bash
export OPENAI_API_KEY=your_key
```

Run:

```bash
python step1.py
```

---

## Step 2 – Proxy with mitmproxy + Guardian

### 1. Configure environment variables

```bash
cp .env.template .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_key
GUARDIAN_URL=http://<GPU_IP>:8000/v1/chat/completions
```

---

### 2. SSL Setup (NGINX)

Generate a private key (since `server.crt` is already included):

```bash
openssl genrsa -out nginx/certs/server.key 2048
```

Ensure files are located at:

```bash
nginx/certs/server.key
nginx/certs/server.crt
```

---

### 3. Run the project

```bash
docker compose up -d --build
```

Open:

```bash
http://localhost:3000
```

---

## Guardian Setup

### Option 1 – Local NVIDIA GPU

```bash
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -e HUGGING_FACE_HUB_TOKEN=YOUR_TOKEN \
  vllm/vllm-openai:latest \
  --model ibm-granite/granite-guardian-3.1-8b
```

Set:

```bash
export GUARDIAN_URL=http://localhost:8000/v1/chat/completions
```

---

### Option 2 – Cloud GPU

Run the same container on a GPU instance and set:

```bash
export GUARDIAN_URL=http://YOUR_GPU_IP:8000/v1/chat/completions
```

---

## Notes

* Guardian returns Yes/No → converted into a risk score (0–100)
* Requests are blocked if risk exceeds a threshold
* If no category matches, response is: "considered toxic"
* SSL is handled via NGINX
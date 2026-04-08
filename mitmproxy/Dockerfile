FROM mitmproxy/mitmproxy:10.3.0

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY addon.py /app/addon.py

CMD ["mitmdump", "--listen-host", "0.0.0.0", "--listen-port", "8080", "-s", "/app/addon.py"]
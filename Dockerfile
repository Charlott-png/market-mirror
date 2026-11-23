FROM python:3.12-slim
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY . .
RUN useradd --create-home --uid 10001 mirror && mkdir -p /data/uploads /data/ai /app/instance && chown -R mirror:mirror /data /app/instance
USER mirror
EXPOSE 8080
CMD ["python", "-m", "waitress", "--listen=0.0.0.0:8080", "wsgi:application"]

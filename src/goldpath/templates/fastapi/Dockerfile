# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app
RUN useradd --create-home --uid 1000 appuser
USER appuser
EXPOSE {{ port }}
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{{ port }}"]

# {{ service_name }}

A {{ language }} service scaffolded with [golden-path-scaffolder](https://github.com/tenalisriharsha/golden-path-scaffolder).

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --port {{ port }}
```

Health check: `GET {{ health_path }}`

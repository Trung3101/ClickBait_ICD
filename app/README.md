# VnExpress Clickbait Extension

## Run API

```powershell
conda run -n fruit_env python -m uvicorn api.main:app --app-dir app --host 127.0.0.1 --port 8000
```

## Smoke Test

```powershell
conda run -n fruit_env python app/scripts/smoke_predict.py
```

## Load Extension

Open Chrome or Edge extension management, enable Developer mode, and load `app/extension`
as an unpacked extension. The content script supports `https://vnexpress.net/*`.

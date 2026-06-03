# 3DITA Backend Stub

This backend is a local FastAPI stub to let the frontend run in "real mode" without the full ML backend.

## Install

```powershell
cd backend
python -m pip install -r requirements.txt
```

## Run

```powershell
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

## Supported endpoints

- `GET /health`
- `POST /api/reconstruct`
- `POST /api/inpaint`
- `GET /api/job/{job_id}`
- `WS /ws/job/{job_id}`

`POST /api/inpaint` accepts:

- `image`: masked temple pathway image (`.png`, `.jpg`, `.webp`, `.bmp`, `.tif`)
- `mask`: binary missing-region mask, white pixels indicate regions to reconstruct
- `params`: optional JSON string, for example `{"profile":"hq","refinement_passes":4}`

Example:

```powershell
curl.exe -X POST http://localhost:8010/api/inpaint `
  -F "image=@C:\path\temple_path_masked.png" `
  -F "mask=@C:\path\temple_path_mask.png" `
  -F "params={\"profile\":\"hq\"}"
```

The endpoint preserves the input resolution and original pixels outside the mask. If
`GRNET_INPAINT_COMMAND` is configured, the backend calls that external Guided
Refinement Network command with `{image}`, `{mask}`, `{output}`, and `{profile}`
placeholders. Without it, the backend uses the local structural texture refinement
fallback.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from starlette.responses import Response

from .predictor import get_predictor


class PredictRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    lead_paragraph: str = Field(default="", max_length=2000)

    @field_validator("title", "lead_paragraph", mode="before")
    @classmethod
    def coerce_text(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value):
        if not value:
            raise ValueError("title must not be blank")
        return value


class PredictResponse(BaseModel):
    prob_clickbait: float


app = FastAPI(title="Vietnamese Clickbait Predictor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def allow_private_network_preflight(request, call_next):
    is_private_network_preflight = (
        request.method == "OPTIONS"
        and request.headers.get("access-control-request-private-network") == "true"
    )
    if is_private_network_preflight:
        response = Response(status_code=200)
    else:
        response = await call_next(request)

    origin = request.headers.get("origin")
    requested_headers = request.headers.get("access-control-request-headers", "*")
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    if origin:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Vary", "Origin")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", requested_headers)
    return response


@app.get("/health")
def health():
    try:
        predictor = get_predictor()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"predictor unavailable: {exc}") from exc
    return {"status": "ready", "device": predictor.device, "model_path": predictor.model_path}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    try:
        probability = get_predictor().predict(request.title, request.lead_paragraph)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"prediction failed: {exc}") from exc
    return PredictResponse(prob_clickbait=round(probability, 6))

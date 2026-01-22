import logging
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import structlog

from llm_backend.worker import LLMWorker

# Configure structured JSON logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

app = FastAPI(title="LLM Backend Worker")
worker = LLMWorker()

# Metrics storage
request_count = 0
total_latency = 0.0


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7


class GenerateResponse(BaseModel):
    text: str
    tokens_per_sec: float
    latency_ms: float
    model: str


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text from the LLM worker."""
    global request_count, total_latency
    
    start_time = time.time()
    request_count += 1
    
    logger.info(
        "backend_generate_request",
        prompt_length=len(request.prompt),
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    try:
        result = worker.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        latency = (time.time() - start_time) * 1000
        total_latency += latency
        
        logger.info(
            "backend_generate_success",
            latency_ms=latency,
            tokens_per_sec=result["tokens_per_sec"],
            output_length=len(result["text"])
        )
        
        return GenerateResponse(
            text=result["text"],
            tokens_per_sec=result["tokens_per_sec"],
            latency_ms=result["latency_ms"],
            model=result["model"]
        )
    except Exception as e:
        logger.error("backend_generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    logger.debug("backend_healthz_check")
    return {"status": "healthy", "service": "backend"}


@app.get("/readyz")
async def readyz():
    """Readiness check endpoint."""
    try:
        # Check if worker is ready
        is_ready = worker.is_ready()
        if is_ready:
            logger.debug("backend_readyz_check", ready=True)
            return {"status": "ready", "service": "backend"}
        else:
            logger.warning("backend_readyz_check", ready=False)
            raise HTTPException(status_code=503, detail="Backend not ready")
    except Exception as e:
        logger.error("backend_readyz_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Backend not ready")


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    avg_latency = total_latency / request_count if request_count > 0 else 0.0
    
    metrics_data = {
        "request_count": request_count,
        "avg_latency_ms": round(avg_latency, 2),
        "total_latency_ms": round(total_latency, 2),
        "worker_status": "ready" if worker.is_ready() else "not_ready"
    }
    
    logger.debug("backend_metrics_request", **metrics_data)
    return metrics_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

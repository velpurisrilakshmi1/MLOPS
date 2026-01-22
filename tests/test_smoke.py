import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gateway_api.main import app

client = TestClient(app)


def test_healthz():
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_readyz():
    """Test readiness check endpoint."""
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_generate():
    """Test text generation endpoint."""
    payload = {
        "prompt": "Hello, how are you?",
        "max_tokens": 50,
        "temperature": 0.7
    }
    
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "text" in data
    assert "tokens_per_sec" in data
    assert "latency_ms" in data
    assert "model" in data
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0
    assert data["tokens_per_sec"] > 0
    assert data["latency_ms"] > 0


def test_generate_minimal():
    """Test generation with minimal parameters."""
    payload = {
        "prompt": "Test prompt"
    }
    
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data


def test_metrics():
    """Test metrics endpoint."""
    # Make a generate request first
    client.post("/generate", json={"prompt": "test"})
    
    response = client.get("/metrics")
    assert response.status_code == 200
    
    data = response.json()
    assert "request_count" in data
    assert "avg_latency_ms" in data
    assert "total_latency_ms" in data
    assert "worker_status" in data
    assert data["request_count"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

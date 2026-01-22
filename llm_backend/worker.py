import random
import time
from typing import Dict, Any


class LLMWorker:
    """Mock LLM worker that simulates text generation."""
    
    def __init__(self):
        self.model_name = "mock-llm-v1"
        self.ready = True
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate mock text response.
        
        Returns:
            Dictionary with text, tokens_per_sec, latency_ms, and model info
        """
        # Simulate processing time (10-50ms)
        processing_time = random.uniform(0.01, 0.05)
        time.sleep(processing_time)
        
        # Generate mock response
        mock_responses = [
            "The quick brown fox jumps over the lazy dog.",
            "Artificial intelligence is transforming the world.",
            "Large language models can generate human-like text.",
            "Python is a versatile programming language.",
            "Cloud computing enables scalable applications."
        ]
        
        # Select response based on prompt hash for consistency
        response_idx = hash(prompt) % len(mock_responses)
        base_response = mock_responses[response_idx]
        
        # Simulate token generation based on max_tokens
        words = base_response.split()
        simulated_tokens = min(max_tokens, len(words))
        generated_text = " ".join(words[:simulated_tokens])
        
        # Calculate mock metrics
        latency_ms = processing_time * 1000
        tokens_per_sec = simulated_tokens / processing_time if processing_time > 0 else 0
        
        return {
            "text": generated_text,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "latency_ms": round(latency_ms, 2),
            "model": self.model_name
        }
    
    def is_ready(self) -> bool:
        """Check if the worker is ready to serve requests."""
        return self.ready

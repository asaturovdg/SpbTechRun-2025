"""
Embedding Generation Pipeline (Docker Entry Point)

This script is the entry point for Docker container.
It orchestrates: model check/download → feature engineering → embedding generation

"""

import asyncio
import time
import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config.config import settings


MODEL_NAME = "bge-m3"
MAX_WAIT_SECONDS = 120  # Max time to wait for Ollama service

# Import ollama
try:
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("ERROR: ollama library not installed.")


# ============================================================================
# Ollama Helper Functions
# ============================================================================

def get_ollama_client() -> AsyncClient:
    """Get Ollama AsyncClient configured for Docker network"""
    return AsyncClient(host=settings.ollama_url)


async def wait_for_ollama() -> bool:
    """Wait for Ollama service to be ready"""
    print(f"[Ollama] Waiting for service at {settings.ollama_url}...")
    
    client = get_ollama_client()
    start_time = time.time()
    
    while time.time() - start_time < MAX_WAIT_SECONDS:
        try:
            await client.list()
            print(f"[Ollama] Service is ready!")
            return True
        except Exception as e:
            elapsed = int(time.time() - start_time)
            print(f"[Ollama] Waiting... ({elapsed}s) - {type(e).__name__}")
            await asyncio.sleep(2)
    
    print(f"[Ollama] ERROR: Service not available after {MAX_WAIT_SECONDS}s")
    return False


async def ensure_model_exists() -> bool:
    """Check if model exists, pull if not"""
    print(f"\n[Model] Checking for {MODEL_NAME}...")
    
    client = get_ollama_client()
    
    try:
        # Check if model exists
        models = await client.list()
        model_names = [m.get('name', '').split(':')[0] for m in models.get('models', [])]
        
        if MODEL_NAME in model_names:
            print(f"[Model] {MODEL_NAME} is already available")
            return True
        
        # Model not found, need to pull
        print(f"[Model] {MODEL_NAME} not found. Pulling...")
        print(f"[Model] This may take several minutes for first download...")
        
        # Pull model
        await client.pull(MODEL_NAME)
        
        print(f"[Model] {MODEL_NAME} pulled successfully!")
        return True
        
    except Exception as e:
        print(f"[Model] ERROR: {e}")
        return False



# Main Pipeline
async def main():
    print("=" * 80)
    print("Embedding Generation Pipeline")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DB}")
    print(f"  Ollama: {settings.ollama_url}")
    print(f"  Model: {MODEL_NAME}")
    
    # Step 1: Wait for Ollama service
    print("\n" + "-" * 80)
    print("[Step 1] Wait for Ollama service")
    print("-" * 80)
    
    if not await wait_for_ollama():
        print("FAILED: Ollama service not available")
        return False
    
    # Step 2: Ensure model exists
    print("\n" + "-" * 80)
    print("[Step 2] Check/Download model")
    print("-" * 80)
    
    if not await ensure_model_exists():
        print("FAILED: Could not get model")
        return False
    
    # Step 3: Run feature engineering
    print("\n" + "-" * 80)
    print("[Step 3] Feature Engineering")
    print("-" * 80)
    
    from recsys import feature_engineering
    result = feature_engineering.main()
    if result is None:
        print("FAILED: Feature engineering failed")
        return False
    
    # Step 4: Run embedding generation
    print("\n" + "-" * 80)
    print("[Step 4] Embedding Generation")
    print("-" * 80)
    
    from recsys import embedding_generation
    success = embedding_generation.main(ollama_url=settings.ollama_url)
    if not success:
        print("FAILED: Embedding generation failed")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n Pipeline completed successfully!")
    else:
        print("\n Pipeline failed!")
        exit(1)

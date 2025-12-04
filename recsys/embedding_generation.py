"""
Embedding Generation Pipeline 

Input: temp/product_features_cleaned.csv
Output: Database embedding column 
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
import time
from typing import List, Optional, Tuple
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.config.config import settings

# ============================================================================
# Configuration
# ============================================================================

MODEL_NAME = "bge-m3"
TEMP_DIR = Path(__file__).parent / "temp"
INPUT_FILE = TEMP_DIR / "product_features_cleaned.csv"

# Concurrency settings
BATCH_SIZE = 10  # Number of concurrent requests
MAX_RETRIES = 3  # Retry failed requests

# Import ollama
try:
    import ollama
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("WARNING: ollama library not installed. Install with: pip install ollama")


# ============================================================================
# Ollama Functions
# ============================================================================

def check_ollama() -> bool:
    """Check if Ollama is available and model is loaded"""
    if not OLLAMA_AVAILABLE:
        print("ERROR: ollama library not installed")
        return False
    
    print("[Check] Verifying Ollama service...")
    try:
        response = ollama.show(MODEL_NAME)
        print(f"SUCCESS: Ollama running with {MODEL_NAME} model")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        print("Make sure Ollama is running: ollama serve")
        print(f"And model is pulled: ollama pull {MODEL_NAME}")
        return False


async def generate_embedding_async(client: AsyncClient, text: str, product_id: int) -> Tuple[int, Optional[List[float]]]:
    """Generate embedding for a single text asynchronously"""
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.embeddings(model=MODEL_NAME, prompt=text)
            embedding = response.get('embedding', None)
            return (product_id, embedding)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
            else:
                print(f"  Failed product {product_id} after {MAX_RETRIES} attempts: {e}")
                return (product_id, None)
    return (product_id, None)


async def generate_embeddings_batch_async(
    texts_with_ids: List[Tuple[int, str]], 
    ollama_url: Optional[str] = None
) -> List[Tuple[int, Optional[List[float]]]]:
    """Generate embeddings for a batch of texts concurrently"""
    # Use provided URL or default (localhost)
    client = AsyncClient(host=ollama_url) if ollama_url else AsyncClient()
    tasks = [
        generate_embedding_async(client, text, product_id)
        for product_id, text in texts_with_ids
    ]
    results = await asyncio.gather(*tasks)
    return results


# ============================================================================
# Database Functions
# ============================================================================

def save_embedding_to_db(engine, product_id: int, embedding: List[float]) -> bool:
    """Save a single embedding to database"""
    try:
        # Convert embedding to pgvector format: '[0.1, 0.2, ...]'
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        with Session(engine) as session:
            # Update the embedding column
            session.execute(
                text("UPDATE products SET embedding = :embedding WHERE id = :id"),
                {"embedding": embedding_str, "id": product_id}
            )
            session.commit()
        return True
    except Exception as e:
        print(f"  DB Error for product {product_id}: {e}")
        return False


def save_embeddings_batch_to_db(engine, results: List[Tuple[int, Optional[List[float]]]]) -> Tuple[int, int]:
    """Save a batch of embeddings to database"""
    success_count = 0
    fail_count = 0
    
    with Session(engine) as session:
        for product_id, embedding in results:
            if embedding is None:
                fail_count += 1
                continue
            
            try:
                # Convert embedding to pgvector format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                session.execute(
                    text("UPDATE products SET embedding = :embedding WHERE id = :id"),
                    {"embedding": embedding_str, "id": product_id}
                )
                # Commit each successful update to avoid losing progress
                session.commit()
                success_count += 1
            except Exception as e:
                # Rollback to reset session state, allowing subsequent updates to work
                session.rollback()
                print(f"  DB Error for product {product_id}: {e}")
                fail_count += 1
    
    return success_count, fail_count


# ============================================================================
# Main Pipeline
# ============================================================================

def get_products_without_embedding(engine, product_ids: List[int]) -> List[int]:
    """Get list of product IDs that don't have embeddings yet"""
    with Session(engine) as session:
        result = session.execute(
            text("SELECT id FROM products WHERE embedding IS NOT NULL AND id = ANY(:ids)"),
            {"ids": product_ids}
        )
        existing_ids = {row[0] for row in result.fetchall()}
    
    return [pid for pid in product_ids if pid not in existing_ids]


async def process_embeddings_async(
    df: pd.DataFrame, 
    engine, 
    ollama_url: Optional[str] = None
) -> Tuple[int, int, float]:
    """Process all embeddings asynchronously"""
    total_success = 0
    total_fail = 0
    start_time = time.time()
    
    # Check which products already have embeddings
    all_ids = df['id'].tolist()
    ids_to_process = get_products_without_embedding(engine, all_ids)
    
    if len(ids_to_process) == 0:
        print("All products already have embeddings. Skipping generation.")
        return len(all_ids), 0, 0.0
    
    skipped = len(all_ids) - len(ids_to_process)
    if skipped > 0:
        print(f"Skipping {skipped} products that already have embeddings.")
    
    # Filter dataframe to only include products without embeddings
    df_to_process = df[df['id'].isin(ids_to_process)]
    
    # Prepare data: (product_id, embedding_prompt)
    texts_with_ids = list(zip(df_to_process['id'].tolist(), df_to_process['embedding_prompt'].tolist()))
    total = len(texts_with_ids)
    
    print(f"Processing {total} products with batch size {BATCH_SIZE}...")
    
    # Progress bar
    pbar = tqdm(total=total, desc="Generating embeddings", unit="item")
    
    # Process in batches
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = texts_with_ids[batch_start:batch_end]
        
        # Generate embeddings concurrently
        results = await generate_embeddings_batch_async(batch, ollama_url)
        
        # Save to database
        success, fail = save_embeddings_batch_to_db(engine, results)
        total_success += success
        total_fail += fail
        
        # Update progress bar
        pbar.update(len(batch))
        pbar.set_postfix({
            'success': total_success,
            'failed': total_fail,
            'rate': f"{pbar.n / (time.time() - start_time):.1f}/s"
        })
    
    pbar.close()
    elapsed_total = time.time() - start_time
    return total_success, total_fail, elapsed_total


async def main(ollama_url: Optional[str] = None):
    """
    ollama_url: Optional Ollama server URL. If None, uses localhost.
                In Docker, pass settings.ollama_url.
    """
    print("\n" + "=" * 80)
    print("Embedding Generation Pipeline")
    print("=" * 80)
    
    # Step 1: Check Ollama
    print("\n[Step 1] Check Ollama Service")
    print("-" * 80)
    if not check_ollama():
        print("\nFailed: Please start Ollama and pull the model")
        return False
    
    # Step 2: Load data
    print("\n[Step 2] Load feature data")
    print("-" * 80)
    
    if not INPUT_FILE.exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        print("Please run feature_engineering.py first")
        return False
    
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Loaded: {len(df)} records")
        print(f"Columns: {', '.join(df.columns)}")
    except Exception as e:
        print(f"ERROR: Failed to load CSV - {e}")
        return False
    
    # Step 3: Connect to database
    print("\n[Step 3] Connect to database")
    print("-" * 80)
    
    try:
        engine = create_engine(settings.database_url_sync, echo=False)
        with Session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            print(f"Connected. Products in DB: {count}")
    except Exception as e:
        print(f"ERROR: Database connection failed - {e}")
        return False
    
    # Step 4: Generate embeddings
    print("\n[Step 4] Generate embeddings (async)")
    print("-" * 80)

    success, failed, elapsed = await process_embeddings_async(df, engine, ollama_url)
    
    # Step 5: Verify results
    print("\n[Step 5] Verify results")
    print("-" * 80)
    
    with Session(engine) as session:
        result = session.execute(
            text("SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL")
        )
        with_embedding = result.scalar()
        print(f"Products with embeddings: {with_embedding}")
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    
    print(f"\nProcessing Results:")
    print(f"  Total records: {len(df)}")
    print(f"  Successfully generated: {success}")
    print(f"  Failed: {failed}")
    if len(df) > 0:
        print(f"  Success rate: {success/len(df)*100:.1f}%")
    
    print(f"\nPerformance:")
    print(f"  Total time: {elapsed:.1f} seconds")
    if elapsed > 0:
        print(f"  Speed: {len(df)/elapsed:.1f} items/sec")
    print(f"  Concurrency: {BATCH_SIZE} parallel requests")
    
    print(f"\nDatabase:")
    print(f"  Products with embeddings: {with_embedding}")
    print(f"  Embedding format: pgvector compatible ([x1,x2,...])")
    
    return True


if __name__ == "__main__":
    # Force environment variables for local development only
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5433"
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = "postgres"
    os.environ["DB_DB"] = "recsys"
    
    success = asyncio.run(main())  # Use default localhost for Ollama
    if success:
        print("\n Pipeline completed successfully!")
    else:
        print("\n Pipeline failed!")

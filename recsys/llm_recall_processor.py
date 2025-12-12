"""
LLM Retrieval Processor

Processes LLM-generated recommendations and matches them to real SKUs.

Input: temp/recommendations_output.json
Output: llm_recommendations table

Flow:
1. Read JSON file
2. For each rec_text, compute embedding
3. Match against accessory products in database
4. Insert results into llm_recommendations table
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


# ============================================================================
# Configuration
# ============================================================================

MODEL_NAME = "bge-m3"
TEMP_DIR = Path(__file__).parent / "temp"
INPUT_FILE = TEMP_DIR / "recommendations_output.json"

# Matching settings
TOP_K = 3  # Number of matches per rec_text
MIN_SIMILARITY = 0.3  # Minimum similarity threshold (discard lower matches)

# Concurrency settings
BATCH_SIZE = 10
MAX_RETRIES = 3

# Import ollama
try:
    import ollama
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("WARNING: ollama library not installed. Install with: pip install ollama")


# ============================================================================
# Database Functions
# ============================================================================

def get_database_url() -> str:
    """Get database URL, handling local vs Docker environment"""
    from app.config.config import settings
    
    # Check if running locally (not in Docker)
    is_docker = os.path.exists("/.dockerenv") or os.path.exists("/proc/1/cgroup")
    
    if not is_docker and os.environ.get("DB_HOST") == "db":
        # Override for local execution
        db_host = "localhost"
        db_port = os.environ.get("DB_PORT", "5433")
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD", "postgres")
        db_name = os.environ.get("DB_DB", "recsys")
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return settings.database_url_sync


def get_accessory_embeddings(engine) -> Dict[int, List[float]]:
    """Load all accessory product embeddings from database"""
    embeddings = {}
    
    with Session(engine) as session:
        result = session.execute(text("""
            SELECT id, embedding
            FROM products
            WHERE product_role = 'сопутка'
              AND embedding IS NOT NULL
        """))
        
        for row in result:
            if row.embedding:
                embeddings[row.id] = row.embedding
    
    print(f"Loaded {len(embeddings)} accessory embeddings from database")
    return embeddings


def match_embedding_to_products(
    rec_embedding: List[float],
    product_embeddings: Dict[int, List[float]],
    top_k: int = 1
) -> List[Tuple[int, float]]:
    """
    Find top-K matching products for a recommendation embedding.
    
    Returns: List of (product_id, similarity_score) tuples
    """
    import numpy as np
    
    rec_vec = np.array(rec_embedding)
    rec_norm = np.linalg.norm(rec_vec)
    
    if rec_norm == 0:
        return []
    
    scores = []
    for pid, emb in product_embeddings.items():
        prod_vec = np.array(emb)
        prod_norm = np.linalg.norm(prod_vec)
        
        if prod_norm == 0:
            continue
        
        # Cosine similarity
        similarity = float(np.dot(rec_vec, prod_vec) / (rec_norm * prod_norm))
        scores.append((pid, similarity))
    
    # Sort by similarity descending
    scores.sort(key=lambda x: -x[1])
    
    return scores[:top_k]


def insert_recommendations(engine, records: List[Dict]) -> Tuple[int, int]:
    """Insert recommendations into database"""
    success = 0
    failed = 0
    
    with Session(engine) as session:
        for record in records:
            try:
                session.execute(text("""
                    INSERT INTO llm_recommendations 
                    (main_product_id, rec_text, rec_rank, matched_product_id, match_score, resolved_rank)
                    VALUES (:main_product_id, :rec_text, :rec_rank, :matched_product_id, :match_score, :resolved_rank)
                    ON CONFLICT DO NOTHING
                """), record)
                success += 1
            except Exception as e:
                print(f"  Failed to insert: {e}")
                failed += 1
        
        session.commit()
    
    return success, failed


def clear_existing_recommendations(engine, main_product_ids: List[int]):
    """Clear existing recommendations for given main products"""
    with Session(engine) as session:
        session.execute(text("""
            DELETE FROM llm_recommendations
            WHERE main_product_id = ANY(:ids)
        """), {"ids": main_product_ids})
        session.commit()


# ============================================================================
# Embedding Functions
# ============================================================================

async def generate_embedding_async(
    client: AsyncClient, 
    text: str
) -> Optional[List[float]]:
    """Generate embedding for a single text"""
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.embeddings(model=MODEL_NAME, prompt=text)
            return response.get('embedding', None)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                print(f"  Embedding failed after {MAX_RETRIES} attempts: {e}")
                return None


async def process_batch_async(
    client: AsyncClient,
    batch: List[Dict]
) -> List[Dict]:
    """Process a batch of recommendations asynchronously"""
    tasks = []
    for item in batch:
        task = generate_embedding_async(client, item['rec_text'])
        tasks.append(task)
    
    embeddings = await asyncio.gather(*tasks)
    
    # Attach embeddings to items
    for item, emb in zip(batch, embeddings):
        item['embedding'] = emb
    
    return batch


# ============================================================================
# Main Processing
# ============================================================================

def load_json_data(filepath: Path) -> List[Dict]:
    """Load and flatten JSON data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    
    # Flatten: each (product_id, rec_text, rec_rank) becomes a row
    flattened = []
    for item in results:
        if not item.get('success', False):
            continue
        
        main_product_id = item['product_id']
        recommendations = item.get('recommendations', [])
        
        for rank, rec_text in enumerate(recommendations, start=1):
            flattened.append({
                'main_product_id': main_product_id,
                'rec_text': rec_text,
                'rec_rank': rank
            })
    
    return flattened


async def main(ollama_url: Optional[str] = None):
    """Main processing function"""
    print("=" * 60)
    print("LLM Retrieval Processor")
    print("=" * 60)
    
    # Check ollama
    if not OLLAMA_AVAILABLE:
        print("ERROR: ollama not available")
        return False
    
    # Load JSON data
    print(f"\n[1/5] Loading JSON from {INPUT_FILE}...")
    if not INPUT_FILE.exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        return False
    
    records = load_json_data(INPUT_FILE)
    print(f"  Loaded {len(records)} recommendations")
    
    # Get unique main product IDs
    main_product_ids = list(set(r['main_product_id'] for r in records))
    print(f"  From {len(main_product_ids)} main products")
    
    # Connect to database
    print("\n[2/5] Connecting to database...")
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    
    # Load accessory embeddings
    print("\n[3/5] Loading accessory embeddings...")
    product_embeddings = get_accessory_embeddings(engine)
    
    if not product_embeddings:
        print("ERROR: No accessory embeddings found in database")
        return False
    
    # Generate embeddings and match
    print(f"\n[4/5] Processing {len(records)} recommendations...")
    
    # Setup ollama client
    if ollama_url:
        client = AsyncClient(host=ollama_url)
    else:
        client = AsyncClient()
    
    # Process in batches
    results_to_insert = []
    
    pbar = tqdm(total=len(records), desc="Processing", unit="rec")
    
    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start:batch_start + BATCH_SIZE]
        
        # Generate embeddings
        batch = await process_batch_async(client, batch)
        
        # Match to products
        for item in batch:
            if item.get('embedding') is None:
                continue
            
            matches = match_embedding_to_products(
                item['embedding'],
                product_embeddings,
                top_k=TOP_K
            )
            
            for resolved_rank, (matched_id, score) in enumerate(matches, start=1):
                if score < MIN_SIMILARITY:
                    continue
                
                results_to_insert.append({
                    'main_product_id': item['main_product_id'],
                    'rec_text': item['rec_text'],
                    'rec_rank': item['rec_rank'],
                    'matched_product_id': matched_id,
                    'match_score': round(score, 4),
                    'resolved_rank': resolved_rank
                })
        
        pbar.update(len(batch))
    
    pbar.close()
    
    print(f"  Generated {len(results_to_insert)} matched records")
    
    # Insert into database
    print("\n[5/5] Inserting into database...")
    
    # Optional: clear existing records first
    # clear_existing_recommendations(engine, main_product_ids)
    
    success, failed = insert_recommendations(engine, results_to_insert)
    
    print(f"  Inserted: {success}, Failed: {failed}")
    
    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)
    
    return True


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    # Set environment variables for local execution
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5433")
    os.environ.setdefault("DB_USER", "postgres")
    os.environ.setdefault("DB_PASSWORD", "postgres")
    os.environ.setdefault("DB_DB", "recsys")
    os.environ.setdefault("OLLAMA_HOST", "localhost")
    os.environ.setdefault("OLLAMA_PORT", "11434")
    
    # Handle event loop for different environments
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    
    # Run
    from app.config.config import settings
    asyncio.run(main(ollama_url=settings.ollama_url))


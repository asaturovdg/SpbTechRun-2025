"""
LLM Retrieval Processor (Standalone Script)

Processes LLM-generated recommendations and matches them to real SKUs.
This is a standalone script for local testing/debugging.

For Docker deployment, use auto_preprocess.py which includes this functionality.

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
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


MODEL_NAME = "bge-m3"
TEMP_DIR = Path(__file__).parent / "temp"
INPUT_FILE = TEMP_DIR / "recommendations_output.json"

# Matching settings
TOP_K = 3  # Number of matches per rec_text
MIN_SIMILARITY = 0.3  # Minimum similarity threshold
BATCH_SIZE = 10
MAX_RETRIES = 3

# Import ollama
try:
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.error("ollama library not installed. Install with: pip install ollama")


# ============================================================================
# Database Functions
# ============================================================================

def get_database_url() -> str:
    """Get database URL from environment variables"""
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5433")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    db_name = os.environ.get("DB_DB", "recsys")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def parse_vector_string(s: str) -> List[float]:
    """Parse pgvector string format '[0.1,0.2,0.3,...]' to list of floats"""
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    return [float(x) for x in s.split(',') if x.strip()]


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
            if row.embedding is not None:
                # psycopg2 returns pgvector as string "[0.1,0.2,...]"
                if isinstance(row.embedding, str):
                    emb = parse_vector_string(row.embedding)
                else:
                    emb = list(row.embedding)
                
                if len(emb) > 0:
                    embeddings[row.id] = emb
    
    logger.info(f"Loaded {len(embeddings)} accessory embeddings from database")
    return embeddings


def match_embedding_to_products(
    rec_embedding: List[float],
    product_embeddings: Dict[int, List[float]],
    top_k: int = 1
) -> List[Tuple[int, float]]:
    """Find top-K matching products for a recommendation embedding"""
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
                logger.warning(f"Failed to insert: {e}")
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

async def generate_embedding_async(client: AsyncClient, text: str) -> Optional[List[float]]:
    """Generate embedding for a single text"""
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.embeddings(model=MODEL_NAME, prompt=text)
            return response.get('embedding', None)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                logger.warning(f"Embedding failed after {MAX_RETRIES} attempts: {e}")
                return None


async def process_batch_async(client: AsyncClient, batch: List[Dict]) -> List[Dict]:
    """Process a batch of recommendations asynchronously"""
    tasks = [generate_embedding_async(client, item['rec_text']) for item in batch]
    embeddings = await asyncio.gather(*tasks)
    
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
    
    if not OLLAMA_AVAILABLE:
        logger.error("ollama not available")
        return False
    
    # Load JSON data
    logger.info(f"[1/5] Loading JSON from {INPUT_FILE}...")
    if not INPUT_FILE.exists():
        logger.info(f"Input file not found: {INPUT_FILE}")
        logger.info("Skipping LLM retrieval processing (no LLM recommendations available)")
        return True  # Not an error, just skip
    
    # Check if already processed
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    
    with Session(engine) as session:
        result = session.execute(text("SELECT COUNT(*) FROM llm_recommendations"))
        count = result.scalar()
        if count > 0:
            logger.info(f"LLM recommendations already exist in database ({count} records), skipping")
            return True
    
    records = load_json_data(INPUT_FILE)
    logger.info(f"Loaded {len(records)} recommendations")
    
    main_product_ids = list(set(r['main_product_id'] for r in records))
    logger.info(f"From {len(main_product_ids)} main products")
    
    # Load accessory embeddings (engine already created above)
    logger.info("[3/5] Loading accessory embeddings...")
    product_embeddings = get_accessory_embeddings(engine)
    
    if not product_embeddings:
        logger.error("No accessory embeddings found in database")
        return False
    
    # Generate embeddings and match
    logger.info(f"[4/5] Processing {len(records)} recommendations...")
    
    # Setup ollama client
    client = AsyncClient(host=ollama_url) if ollama_url else AsyncClient()
    
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
    
    logger.info(f"Generated {len(results_to_insert)} matched records")
    
    # Insert into database
    logger.info("[5/5] Inserting into database...")
    success, failed = insert_recommendations(engine, results_to_insert)
    logger.info(f"Inserted: {success}, Failed: {failed}")
    
    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)
    
    return True


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":

    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5433"
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = "postgres"
    os.environ["DB_DB"] = "recsys"
    os.environ["OLLAMA_HOST"] = "localhost"
    os.environ["OLLAMA_PORT"] = "11434"
    # Handle event loop for different environments
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    
    # Run with local URL
    ollama_url = "http://localhost:11434"
    asyncio.run(main(ollama_url=ollama_url))

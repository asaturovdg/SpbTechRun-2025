# Recommendation System Structure

## Architecture Overview

```
recsys/
├── db_repository.py          - Database access layer
├── recommender.py            - Recommendation engine (algorithm logic)
├── feature_engineering.py    - Feature cleaning pipeline
├── embedding_generation.py   - Embedding generation 
├── auto_preprocess.py        - Docker entry point (model check + pipelines)
├── test_local.py             - Local testing script
├── __init__.py               - Module exports
└── temp/                     - Temporary files (CSV outputs)
```

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. feature_engineering.py                                      │
│     - Read from database                                        │
│     - Clean features (name, key_params, etc.)                   │
│     - Generate embedding_prompt                                 │
│     - Output: temp/product_features_cleaned.csv                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. embedding_generation.py                                     │
│     - Read CSV from temp/                                       │
│     - Generate embeddings with Ollama bge-m3                    │
│     - Save directly to database (pgvector format)               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. recommender.py (API)                                        │
│     - Vector similarity search (pgvector)                       │
│     - feedback using Thompson Sampling                          │
│     - Apply feedback weights                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## db_repository.py - Database Access Layer

```
ProductRepository (Class)
├── __init__()                                - Initialize DB connection
├── _load_products()                          - Load products to memory
├── reload()                                  - Reload from database
├── get_all_products()                        - Get all products
├── get_product_by_id(id)                     - Get single product
├── get_main_products()                       - Get main products (основной товар)
├── get_accessory_products()                  - Get accessories (сопутка)
├── get_products_by_type(type, role)          - Filter by type
├── get_products_by_category(name/id)         - Filter by category
├── get_candidates(type, exclude_id)          - Get candidate products
├── get_products_with_embeddings()            - Get products with vectors
└── get_similar_products_by_vector(id, limit) - pgvector similarity search

get_repository()                              - Singleton accessor
```

---

## recommender.py - Recommendation Engine

```
ThompsonSampler (Class)
├── __init__(engine)                          - Initialize + load from DB
│   └── Read parameters from settings (DEMO_MODE aware)
├── _load_from_db()                           - Load arm_stats from database
├── get_params(key, similarity=None)          - Get Beta(α,β) for an arm
│   └── DEMO_MODE: Initialize with informed prior based on similarity
├── sample(key, similarity=None)              - Sample from Beta distribution
├── update(key, is_success)                   - Update α or β based on feedback
│   └── DEMO_MODE: Amplified update (×5) + cap at MAX_TOTAL
├── get_expected_value(key)                   - Get E[θ] = α/(α+β)
├── get_stats(key)                            - Get full statistics
└── initialize_from_similarity(key, sim)      - Initialize arm with similarity

RecommendationEngine (Class)
├── __init__(repository=None)                 - Initialize (uses singleton)
├── get_ranking(product_id, use_vector_search)
│   ├── Get main product + price
│   ├── Try vector search (pgvector)
│   ├── Fallback: get all accessories
│   ├── Fill candidates if < 20 (_fill_candidates)
│   ├── Calculate scores (_calculate_scores)
│   └── Build response (_build_response)
├── _fill_candidates(main_id, existing, target)
│   └── Stable filling using hash-based deterministic selection
├── _calculate_price_factor(main_price, candidate_price)
│   └── Penalize accessories > 1.5x main price (up to 30%)
├── _calculate_scores(main_id, main_price, candidates, method)
│   ├── Base score: similarity / hash-based deterministic
│   ├── Thompson weight: sample from Beta(α,β)
│   ├── Price factor: penalty for expensive items
│   └── Combined: (base*0.6 + thompson*0.4) * price_factor
├── _build_response(scored_candidates)        - Format to API schema
├── update_model(product_id, rec_id, is_relevant)
│   └── Update Thompson Sampling parameters (memory)
├── get_arm_stats(product_id, rec_id)         - Get arm statistics
├── reload_data()                             - Reload products from database
└── reload_arm_stats()                        - Reload arm_stats from database
```

### Scoring Formula
```
final_score = (base_score × 0.8 + thompson_weight × 0.2) × price_factor

- base_score: vector similarity (0~1) or hash-based deterministic
- thompson_weight: sampled from Beta(α, β), range 0~1
- price_factor: 1.0 if ratio ≤ 1.5, else penalty up to 0.7
```

### DEMO_MODE Configuration 
```
Parameters (all configurable via .env):
├── DEMO_MODE                 - Enable demo mode (default: true)
├── TS_INIT_STRENGTH          - Similarity-based init strength (default: 4.0)
├── TS_UPDATE_STRENGTH_DEMO   - Update strength in demo mode (default: 5.0)
├── TS_UPDATE_STRENGTH_NORMAL - Update strength in normal mode (default: 1.0)
└── TS_MAX_TOTAL              - Cap on α+β to prevent variance collapse (default: 50.0)

DEMO_MODE effects:
- Initialize new arms with informed prior: α = 1 + sim × INIT_STRENGTH
- Amplified feedback: one click changes E[θ] by ~20% (vs ~5% in normal)
- Cap prevents variance collapse after many feedbacks
```

---

## feature_engineering.py - Feature Pipeline

```
Functions:
├── load_data_from_db()                       - Load from database
├── generate_whitelist_from_data(df)          - In order to make fliter for 'key_params'
├── clean_key_params(params, whitelist)       - Filter attributes
├── clean_name(name)                          - Clean product name
├── create_breadcrumb(parent, category)       - category-> parent category
├── format_price(price)                       - Price formatting
├── get_physical_dimension(row)               - Weight/volume/length
├── create_embedding_prompt(row)              - Combine for embedding
└── main()                                    - Run pipeline

Output: temp/product_features_cleaned.csv
```

---

## embedding_generation.py - Embedding Pipeline

```
Functions (Async):
├── check_ollama()                            - Verify Ollama service
├── generate_embedding_async(client, text, id) - Single embedding
├── generate_embeddings_batch_async(batch, url) - Concurrent batch
├── get_products_without_embedding(engine, ids) - Skip existing embeddings
├── save_embeddings_batch_to_db(engine, results) - Save to DB
├── process_embeddings_async(df, engine, url) - Main async loop
└── main(ollama_url=None)                     - Run pipeline (async)

Features:
- Skips products that already have embeddings (avoid regeneration)
- Supports custom Ollama URL for Docker environments
- Progress bar with tqdm
```

---

## auto_preprocess.py - Docker Entry Point

```
Functions (Async):
├── get_ollama_client()                       - Get AsyncClient with settings.ollama_url
├── wait_for_ollama()                         - Wait for Ollama service (max 120s)
├── ensure_model_exists()                     - Check/pull bge-m3 model
└── main()                                    - Orchestrate full pipeline

Pipeline:
1. Wait for Ollama service
2. Check/download bge-m3 model
3. Run feature_engineering.main()
4. Run embedding_generation.main(ollama_url)
```

---

## Database Schema 

```sql
products:
  - id (PK)
  - name
  - category_name, category_id
  - vendor
  - price
  - type                      -- Work type (main products only)
  - parent_id, parent_name
  - weight_kg, shipping_weight_kg, volume_l, length_mm
  - key_params (JSON)
  - picture_url, url, description
  - product_role              -- 'основной товар' or 'сопутка'
  - embedding (Vector 1024)   -- pgvector

arm_stats:                    -- Thompson Sampling parameters
  - id (PK)
  - product_id (FK)           -- Main product
  - recommended_product_id (FK) -- Recommended product
  - alpha (default 1.0)       -- Success count + 1
  - beta (default 1.0)        -- Failure count + 1
  - updated_at                -- Last update timestamp
  - UNIQUE(product_id, recommended_product_id)
```


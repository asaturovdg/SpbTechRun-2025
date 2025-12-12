# Recommendation System Structure

## Architecture Overview

```
recsys/
├── db_repository.py          - Database access layer
├── recommender.py            - Recommendation engine (algorithm logic)
├── feature_engineering.py    - Feature cleaning pipeline
├── embedding_generation.py   - Embedding generation 
├── llm_recall_processor.py   - LLM recommendations processing (offline)
├── auto_preprocess.py        - Docker entry point (model check + pipelines)
├── test_local.py             - Local testing script
├── __init__.py               - Module exports
└── temp/                     - Temporary files (CSV outputs, LLM JSON)
```

---

## Recommendation Pipeline (Online)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Multi-Channel Retrieval                                     │
│     ┌──────────────────┐    ┌──────────────────┐                │
│     │ Vector Retrieval │    │  LLM Retrieval   │                │
│     │  (pgvector, 40)  │    │  (pre-computed)  │                │
│     └────────┬─────────┘    └────────┬─────────┘                │
│              └──────────┬────────────┘                          │
│                         ↓                                       │
│              ┌──────────────────────┐                           │
│              │  UNION + RRF Fusion  │  → base_score             │
│              │     (~50-60 items)   │                           │
│              └──────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Scoring (Thompson Sampling + Price Factor)                  │
│     final_score = f(base_score, TS, price_factor)               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. MMR Reranking (Diversity)                                   │
│     Select 20 diverse items from ~50-60 candidates              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────┐
                    │  返回 Top-20  │
                    └──────────────┘
```

---

## Data Preparation Pipeline (Offline)

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
│  3. llm_recall_processor.py (New!)                              │
│     - Read LLM recommendations JSON                             │
│     - Compute embeddings for recommendation texts               │
│     - Match to real SKUs via vector similarity                  │
│     - Save to llm_recommendations table                         │
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
├── get_similar_products_by_vector(id, limit) - pgvector similarity search
└── get_llm_recommendations(product_id)       - Get LLM-based recommendations

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
│   ├── Multi-channel retrieval (Vector + LLM)
│   ├── Merge + RRF fusion (_merge_and_fuse)
│   ├── Fallback if no candidates
│   ├── Fill candidates if < return_size (_fill_candidates)
│   ├── Calculate scores (_calculate_scores)
│   ├── Apply MMR for diversity (_mmr_rerank)
│   └── Build response (_build_response)
├── _merge_and_fuse(vector_cands, llm_cands, main_id)
│   ├── UNION deduplication
│   └── RRF score: sum(1/(k+rank)) for each channel
├── _fill_candidates(main_id, existing, target)
│   └── Stable filling using hash-based deterministic selection
├── _calculate_price_factor(main_price, candidate_price)
│   └── Penalize accessories > 1.5x main price (up to 30%)
├── _calculate_scores(main_id, main_price, candidates, method)
│   ├── Base score: RRF / similarity / hash-based
│   ├── Thompson weight: sample from Beta(α,β)
│   ├── Price factor: penalty for expensive items
│   └── Combined: weighted by mode
├── _get_pairwise_similarity(id_i, id_j)      - Cached pairwise similarity
├── _mmr_rerank(scored_candidates)            - MMR diversity reranking
├── _build_response(scored_candidates)        - Format to API schema
├── update_model(product_id, rec_id, is_relevant)
│   └── Update Thompson Sampling parameters (memory)
├── get_arm_stats(product_id, rec_id)         - Get arm statistics
├── reload_data()                             - Reload products from database
└── reload_arm_stats()                        - Reload arm_stats from database
```

### Multi-Channel Retrieval + RRF Fusion

```
┌─────────────────┐    ┌─────────────────┐
│Vector Retrieval │    │  LLM Retrieval  │
│   (40 items)    │    │   (~30 items)   │
└───────┬─────────┘    └───────┬─────────┘
        │    rank_vector       │    rank_llm
        └──────────┬───────────┘
                   ↓
         ┌─────────────────┐
         │  UNION (~50-60) │
         └────────┬────────┘
                  ↓
         ┌─────────────────┐
         │   RRF Fusion    │
         │                 │
         │  rrf_score =    │
         │  1/(k+rank_v) + │
         │  1/(k+rank_l)   │
         │                 │
         │  k = 60 (default)│
         └────────┬────────┘
                  ↓
            base_score
```

### Scoring Formula

**DEMO Mode:**
```
combined = base_score × 0.8 + thompson_weight × 0.2
final_score = combined × price_factor
```

**Normal Mode (dynamic weights based on feedback):**
```
n = feedback_count for this (main, accessory) pair
k = TS_WEIGHT_HALFLIFE (default: 10)
gamma = n / (n + k)

combined = (1 - gamma) × base_score + gamma × thompson_weight
final_score = combined × price_factor

| n  | gamma | base weight | ts weight |
|----|-------|-------------|-----------|
| 0  | 0.00  | 100%        | 0%        |
| 5  | 0.33  | 67%         | 33%       |
| 10 | 0.50  | 50%         | 50%       |
| 20 | 0.67  | 33%         | 67%       |
```

- base_score: RRF fusion score (multi-channel) or vector similarity (single-channel)
- thompson_weight: sampled from Beta(α, β), range 0~1
- price_factor: 1.0 if ratio ≤ 1.5, else penalty up to 0.7

### Multi-Channel Retrieval Configuration
```
Parameters (configurable via .env):
├── VECTOR_RETRIEVAL_SIZE  - Vector channel retrieval count (default: 40)
├── LLM_RETRIEVAL_ENABLED  - Enable LLM retrieval channel (default: true)
└── RRF_K                  - RRF fusion parameter k (default: 60)
```

### MMR (Maximal Marginal Relevance) for Diversity
```
Purpose: Reduce highly similar consecutive items in recommendations

Algorithm:
1. After multi-channel retrieval + RRF fusion (~50-60 candidates)
2. Sort by relevance score (final_score)
3. Phase 1: Take top K (3) items directly
4. Phase 2: For remaining positions, use sliding window MMR:
   - Window = last W (5) selected items
   - MMR score = λ × relevance - (1-λ) × max(similarity to window)
   - Skip items with relevance < MIN_SCORE (0.2)
5. Return top 20 (MMR_RETURN_SIZE)

Parameters (configurable via .env):
├── MMR_ENABLED         - Enable/disable MMR (default: true)
├── MMR_RECALL_SIZE     - Expected candidates after UNION (default: 60)
├── MMR_RETURN_SIZE     - Final items to return (default: 20)
├── MMR_PURE_TOP_K      - Items exempt from MMR (default: 3)
├── MMR_WINDOW_SIZE     - Sliding window size (default: 5)
├── MMR_LAMBDA          - Relevance weight (default: 0.7)
└── MMR_MIN_SCORE       - Minimum relevance threshold (default: 0.2)
```

### Thompson Sampling Configuration 
```
Parameters (all configurable via .env):
├── DEMO_MODE                 - Enable demo mode (default: true)
├── TS_INIT_STRENGTH          - Similarity-based init strength (default: 4.0)
├── TS_UPDATE_STRENGTH_DEMO   - Update strength in demo mode (default: 10.0)
├── TS_UPDATE_STRENGTH_NORMAL - Update strength in normal mode (default: 1.0)
├── TS_MAX_TOTAL              - Cap on α+β to prevent variance collapse (default: 100.0)
├── TS_BASE_WEIGHT_DEMO       - Base score weight in demo mode (default: 0.6)
└── TS_WEIGHT_HALFLIFE        - Feedback count for gamma=0.5 in normal mode (default: 10.0)

Both modes use similarity-based initialization:
  α = 1 + sim × INIT_STRENGTH
  β = 1 + (1-sim) × INIT_STRENGTH

DEMO_MODE effects:
- scoring weights: 80% base_score + 20% thompson_weight
- Higher INIT_STRENGTH (4.0) → stronger prior
- Higher UPDATE_STRENGTH (10.0) → visible learning per click
- Cap prevents variance collapse

Normal mode effects:
- Dynamic scoring weights based on feedback count
- Lower INIT_STRENGTH (configurable) → weaker prior
- Lower UPDATE_STRENGTH (1.0) → gradual learning
- Gradual trust in TS as feedback accumulates
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

llm_recommendations:          -- LLM-based recommendation mapping (offline computed)
  - id (PK)
  - main_product_id (FK)      -- Main product
  - rec_text (TEXT)           -- Original LLM recommendation text
  - rec_rank (INT)            -- LLM output order (1..N)
  - matched_product_id (FK)   -- Matched real SKU
  - match_score (FLOAT)       -- Embedding similarity score
  - resolved_rank (INT)       -- Rank among matches for same rec_text (1=best)
  - created_at                -- Timestamp
  - UNIQUE(main_product_id, rec_text, resolved_rank)
```


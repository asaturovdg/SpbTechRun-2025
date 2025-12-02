# Recommendation System Structure

## Architecture Overview

```
recsys/
├── db_repository.py          - Database access layer
├── recommender.py            - Recommendation engine (algorithm logic)
├── feature_engineering.py    - Feature cleaning pipeline
├── embedding_generation.py   - Embedding generation 
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
├── __init__()                                - Initialize arm_params dict
├── get_params(key)                           - Get Beta(α,β) for an arm
├── sample(key)                               - Sample from Beta distribution
├── update(key, is_success)                   - Update α or β based on feedback
├── get_expected_value(key)                   - Get E[θ] = α/(α+β)
└── get_stats(key)                            - Get full statistics

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
│   └── Update Thompson Sampling parameters
├── get_arm_stats(product_id, rec_id)         - Get arm statistics
└── reload_data()                             - Reload from database
```

### Scoring Formula
```
final_score = (base_score × 0.6 + thompson_weight × 0.4) × price_factor

- base_score: vector similarity (0~1) or hash-based deterministic
- thompson_weight: sampled from Beta(α, β), range 0~1
- price_factor: 1.0 if ratio ≤ 1.5, else penalty up to 0.7
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
├── generate_embeddings_batch_async(batch)    - Concurrent batch
├── save_embeddings_batch_to_db(engine, results) - Save to DB
├── process_embeddings_async(df, engine)      - Main async loop
└── main()                                    - Run pipeline

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
```


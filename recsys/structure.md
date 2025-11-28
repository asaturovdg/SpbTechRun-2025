recommender.py
├── import
├── RecommendationEngine                        - Class
│   ├── __init__()                              - Initialization
│   ├── _load_products()                        - Load products from the database
│   ├── get_candidates_by_white_box_type()      - Filter candidate products
│   ├── get_ranking()                           - Generate recommendations (API call)
│   ├── update_model()                          - Process feedback (API call)
│   └── reload_products()                       - Reload data
└── Test code 
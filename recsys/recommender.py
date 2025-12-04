"""
Recommendation Engine - Algorithm logic

"""
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple

from sqlalchemy import  text
from sqlalchemy.orm import Session

from .db_repository import get_repository, ProductRepository

# Import settings for DEMO_MODE
try:
    from app.config.config import settings
    DEMO_MODE = settings.DEMO_MODE
except:
    DEMO_MODE = True  # Default to demo mode if settings unavailable


class ThompsonSampler: 
    """
    Thompson Sampling for exploration-exploitation in recommendations.
    
    DEMO_MODE features:
    - Initialize alpha/beta based on similarity score (informed prior)
    - Amplified update strength for visible learning effects
    - Cap on total to prevent variance collapse
    
    All parameters are read from settings (app/config/config.py)
    """
    
    def __init__(self, engine=None):
        # key: (product_id, recommended_product_id)
        # value: (alpha, beta) - Beta distribution parameters
        self.arm_params: Dict[tuple, Tuple[float, float]] = {}
        self.engine = engine
        self.demo_mode = DEMO_MODE
        
        # Read parameters from settings
        try:
            self.init_strength = settings.TS_INIT_STRENGTH
            self.update_strength = settings.ts_update_strength
            self.max_total = settings.TS_MAX_TOTAL
        except:
            # Fallback defaults if settings unavailable
            self.init_strength = 4.0
            self.update_strength = 5.0 if DEMO_MODE else 1.0
            self.max_total = 50.0
        
        # Load existing arm stats from database
        if engine:
            self._load_from_db()
        
        if self.demo_mode:
            print(f"[ThompsonSampler] DEMO_MODE enabled: update_strength={self.update_strength}")
    
    def _load_from_db(self):
        """Load arm_stats from database on startup"""
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT product_id, recommended_product_id, alpha, beta FROM arm_stats"
                ))
                count = 0
                for row in result:
                    key = (row.product_id, row.recommended_product_id)
                    self.arm_params[key] = (float(row.alpha), float(row.beta))
                    count += 1
                if count > 0:
                    print(f"[ThompsonSampler] Loaded {count} arm stats from database")
        except Exception as e:
            print(f"[ThompsonSampler] Could not load arm_stats: {e}")
    
    def get_params(self, key: tuple, similarity: float = None) -> Tuple[float, float]:
        """
        Get Beta distribution parameters for an arm.
        
        If this is a new arm and similarity is provided, initialize with
        an informed prior based on vector similarity.
        """
        if key not in self.arm_params:
            if similarity is not None and self.demo_mode:
                # Informed prior based on similarity
                # High similarity -> higher alpha (more likely to be good)
                alpha = 1.0 + similarity * self.init_strength
                beta = 1.0 + (1.0 - similarity) * self.init_strength
            else:
                # Uninformed prior: Beta(1, 1) = Uniform distribution
                alpha, beta = 1.0, 1.0
            
            self.arm_params[key] = (alpha, beta)
        
        return self.arm_params[key]
    
    def sample(self, key: tuple, similarity: float = None) -> float:
        """Sample from Beta distribution for this arm"""
        alpha, beta = self.get_params(key, similarity)
        return np.random.beta(alpha, beta)
    
    def update(self, key: tuple, is_success: bool) -> Tuple[float, float]:
        """
        Update arm parameters based on feedback.
        
        In DEMO_MODE, updates are amplified for visible learning effects.
        """
        alpha, beta = self.get_params(key)
        
        if is_success:
            alpha += self.update_strength
        else:
            beta += self.update_strength
        
        # Apply cap to prevent variance collapse
        total = alpha + beta
        if total > self.max_total:
            scale = self.max_total / total
            alpha *= scale
            beta *= scale
        
        self.arm_params[key] = (alpha, beta)
        return alpha, beta
    
    def get_expected_value(self, key: tuple) -> float:
        """Get expected value (mean of Beta distribution)"""
        alpha, beta = self.get_params(key)
        return alpha / (alpha + beta)
    
    def get_stats(self, key: tuple) -> Dict:
        """Get statistics for an arm"""
        alpha, beta = self.get_params(key)
        return {
            "alpha": alpha,
            "beta": beta,
            "expected_value": alpha / (alpha + beta),
            "variance": (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1)),
            "demo_mode": self.demo_mode,
        }
    
    def initialize_from_similarity(self, key: tuple, similarity: float) -> Tuple[float, float]:
        """
        Initialize arm parameters based on similarity score.
        Call this when creating a new arm with known similarity.
        
        Returns: (alpha, beta) for the new arm
        """
        if self.demo_mode:
            alpha = 1.0 + similarity * self.init_strength
            beta = 1.0 + (1.0 - similarity) * self.init_strength
        else:
            alpha, beta = 1.0, 1.0
        
        self.arm_params[key] = (alpha, beta)
        return alpha, beta


class RecommendationEngine:
    """
    Scoring formula:
    final_score = (base_score * 0.8 + thompson_weight * 0.2) * price_factor
    
    - base_score: vector similarity
    - thompson_weight: sampled from Beta(alpha, beta)
    - price_factor: penalty if accessory is much more expensive than main product
    """
    
    def __init__(self, repository: ProductRepository = None):
        self.repo = repository or get_repository()
        
        # Thompson Sampling for exploration-exploitation
        # Pass database engine to load existing arm_stats
        self.sampler = ThompsonSampler(engine=self.repo.engine)
        
        # Price penalty configuration
        self.price_penalty_threshold = 1.5  # Penalty if accessory > 1.5x main product price
        self.price_penalty_max = 0.3  # Maximum penalty (30% reduction)
        
        # Minimum candidates to return
        self.min_candidates = 20
    
    def get_ranking(self, product_id: int, use_vector_search: bool = True) -> List[Dict]:
        """
        Get recommendation list
        Swagger API: GET /recommendations/{product_id}
        
        Args:
            product_id: Main product ID
            use_vector_search: If True, use pgvector similarity search
            
        Returns:
            List of recommendations
        """
        # Get main product
        main_product = self.repo.get_product_by_id(product_id)
        
        if main_product is None:
            print("[RecommendationEngine] No products found!")
            return []
        
        # Get main product price for comparison
        main_price = main_product.get('price', 0) or 0
        
        # Get candidates
        candidates = []
        search_method = "none"
        
        if use_vector_search:
            # vector similarity search
            try:
                similar_products = self.repo.get_similar_products_by_vector(product_id, limit=20)
                if similar_products:
                    candidates = similar_products
                    search_method = "vector"
            except Exception as e:
                print(f"[RecommendationEngine] Vector search failed: {e}")
        
        # Fallback: get all accessories if vector search failed
        if not candidates:
            candidates = self.repo.get_accessory_products()
            candidates = [c for c in candidates if c['id'] != main_product['id']]
            search_method = "all"
        
        if not candidates:
            print(f"[RecommendationEngine] No candidates for product {main_product['name']}")
            return []
        
        # Fill candidates if less than minimum (stable, deterministic)
        if len(candidates) < self.min_candidates:
            candidates = self._fill_candidates(
                main_product_id=main_product['id'],
                existing_candidates=candidates,
                target_count=self.min_candidates
            )
        
        # Calculate scores with Thompson Sampling and price factor
        scored_candidates = self._calculate_scores(
            main_product_id=main_product['id'],
            main_price=main_price,
            candidates=candidates,
            search_method=search_method
        )
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Build response
        result = self._build_response(scored_candidates)
        
        print(f"[RecommendationEngine] Product {product_id} ({search_method}) -> {len(result)} recommendations")
        return result
    
    def _fill_candidates(
        self, 
        main_product_id: int, 
        existing_candidates: List[Dict], 
        target_count: int
    ) -> List[Dict]:
        # Fill candidates if less than min_candidates
        if len(existing_candidates) >= target_count:
            return existing_candidates
        
        # Get IDs of existing candidates
        existing_ids = {c['id'] for c in existing_candidates}
        existing_ids.add(main_product_id)  # Exclude main product
        
        # Get all accessories not already in candidates
        all_accessories = self.repo.get_accessory_products()
        available = [p for p in all_accessories if p['id'] not in existing_ids]
        
        if not available:
            return existing_candidates
        
        # Sort by deterministic hash for stability
        # hash(main_product_id * 10000 + candidate_id) ensures:
        # Same main product always gets same order
        # Different main products get different orders
        available.sort(key=lambda p: hash(main_product_id * 10000 + p['id']))
        
        # Calculate how many more we need
        need_count = target_count - len(existing_candidates)
        fill_candidates = available[:need_count]
        
        # Mark filled candidates (lower base score since not from vector search)
        for c in fill_candidates:
            c['_is_fill'] = True
        
        print(f"[RecommendationEngine] Filled {len(fill_candidates)} candidates "
              f"({len(existing_candidates)} -> {len(existing_candidates) + len(fill_candidates)})")
        
        return existing_candidates + fill_candidates
    
    def _calculate_price_factor(self, main_price: float, candidate_price: float) -> float:
        """
        If accessory is more than threshold times main product price,
        apply a penalty proportional to the price ratio.
        
        Returns: factor between (1 - price_penalty_max) and 1.0
        """
        if main_price <= 0 or candidate_price <= 0:
            return 1.0  # No penalty if prices are invalid
        
        price_ratio = candidate_price / main_price
        
        if price_ratio <= self.price_penalty_threshold:
            return 1.0  # No penalty
        
        # Calculate penalty: linearly increase from 0 to max_penalty
        # as price_ratio goes from threshold to 3x threshold
        excess_ratio = (price_ratio - self.price_penalty_threshold) / self.price_penalty_threshold
        penalty = min(self.price_penalty_max, excess_ratio * self.price_penalty_max)
        
        return 1.0 - penalty
    
    def _calculate_scores(
        self, 
        main_product_id: int, 
        main_price: float,
        candidates: List[Dict], 
        search_method: str = "none"
    ) -> List[Dict]:
        """
        Calculate final scores for candidates.
        
        Formula: final_score = (base_score * 0.8 + thompson_weight * 0.2) * price_factor
        
        In DEMO_MODE, Thompson Sampling is initialized with informed priors
        based on vector similarity.
        """
        scored = []
        
        for item in candidates:
            # Base score (from vector similarity or deterministic)
            if search_method == "vector" and 'similarity' in item:
                base_score = item['similarity']
                similarity_for_init = item['similarity']  # Use for TS initialization
            elif item.get('_is_fill'):
                # Filled candidates get lower, deterministic score
                base_score = 0.3 + (hash(item['id']) % 1000) / 5000.0  # 0.3~0.5
                similarity_for_init = 0.3  # Low similarity for filled items
            else:
                base_score = 0.1 + (hash(item['id']) % 1000) / 5000.0 
                similarity_for_init = 0.1  
            
            # Thompson Sampling weight (exploration-exploitation)
            # Pass similarity to initialize informed prior for new arms
            arm_key = (main_product_id, item['id'])
            thompson_weight = self.sampler.sample(arm_key, similarity=similarity_for_init)
            
            # Price factor (penalize expensive accessories)
            candidate_price = item.get('price', 0) or 0
            price_factor = self._calculate_price_factor(main_price, candidate_price)
            
            # Combine scores
            # Thompson weight is in [0, 1], use it to adjust the score
            combined_score = base_score * 0.8 + thompson_weight * 0.2
            
            # Apply price penalty
            final_score = combined_score * price_factor
            
            # Clip to [0, 1] range
            final_score = max(0.0, min(1.0, final_score))
            
            scored.append({
                'item': item,
                'score': round(final_score, 3),
                'base_score': round(base_score, 3),
                'thompson_weight': round(thompson_weight, 3),
                'price_factor': round(price_factor, 3),
            })
        
        return scored
    
    def _build_response(self, scored_candidates: List[Dict]) -> List[Dict]:
        result = []
        
        for idx, scored_item in enumerate(scored_candidates):
            item = scored_item['item']
            score = scored_item['score']
            
            # Build recommended product object
            rec_product = {
                "id": item['id'],
                "name": item['name'],
                "price": item['price'],
                "category_id": item.get('category_id', ''),
                "category_name": item.get('category_name', ''),
                "vendor": item.get('vendor', ''),
                "picture_url": item.get('picture_url', ''),
                "product_role": item.get('product_role', ''),
                "type": item.get('type', ''),
                "url": item.get('url', ''),
                "description": item.get('description', ''),
            }
            
            # Build recommendation object
            recommendation_obj = {
                "id": idx + 1000,  # Recommendation record ID
                "similarity_score": score,
                "created_at": datetime.now().isoformat(),
                "recommended_product": rec_product
            }
            result.append(recommendation_obj)
        
        return result
    
    def update_model(self, product_id: int, recommended_product_id: int, is_relevant: bool) -> bool:
        """
        Update model based on user feedback using Thompson Sampling
        
        Swagger API: POST /feedback
        
        Args:
            product_id: Main product ID
            recommended_product_id: Recommended product ID that was rated
            is_relevant: User rating (True=relevant, False=not relevant)
            
        Returns:
            Whether update was successful
        """
        arm_key = (product_id, recommended_product_id)
        
        # Update Thompson Sampling parameters
        alpha, beta = self.sampler.update(arm_key, is_relevant)
        
        # Get expected value after update
        expected = self.sampler.get_expected_value(arm_key)
        
        action = "👍😊 Positive" if is_relevant else "👎😔 Negative"
        print(f"[RecommendationEngine] Feedback: {action} | "
              f"Main={product_id}, Rec={recommended_product_id} | "
              f"Beta({alpha:.0f},{beta:.0f}) -> E[θ]={expected:.3f}")
        
        return True
    
    def get_arm_stats(self, product_id: int, recommended_product_id: int) -> Dict:
        """Get Thompson Sampling statistics for a specific arm"""
        arm_key = (product_id, recommended_product_id)
        return self.sampler.get_stats(arm_key)
    
    def reload_data(self):
        """Reload data from database"""
        self.repo.reload()
    
    def reload_arm_stats(self):
        """Reload arm_stats from database"""
        self.sampler._load_from_db()


"""
Recommendation Engine - Algorithm logic

"""
import logging
import numpy as np
from datetime import datetime
from functools import lru_cache
from typing import List, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db_repository import get_repository, ProductRepository
from app.config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class ThompsonSampler: 
    """
    Thompson Sampling for exploration-exploitation in recommendations.
    
    DEMO_MODE features:
    - Initialize alpha/beta based on similarity score (informed prior)
    - Amplified update strength for visible learning effects
    - Cap on total to prevent variance collapse
    
    All parameters are read from settings (app/config/config.py) (parameters can be overridden in .env)
    """
    
    def __init__(self, engine=None):
        # key: (product_id, recommended_product_id)
        # value: (alpha, beta) - Beta distribution parameters
        self.arm_params: Dict[tuple, Tuple[float, float]] = {}
        self.engine = engine
        self.demo_mode = settings.DEMO_MODE
        self.init_strength = settings.TS_INIT_STRENGTH
        self.update_strength = settings.ts_update_strength
        self.max_total = settings.TS_MAX_TOTAL
        
        # Load existing arm stats from database
        if engine:
            self._load_from_db()
        
        if self.demo_mode:
            logger.info(f"DEMO_MODE enabled: update_strength={self.update_strength}")
    
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
                    logger.info(f"Loaded {count} arm stats from database")
        except Exception as e:
            logger.warning(f"Could not load arm_stats: {e}")
    
    def get_params(self, key: tuple, similarity: float = None) -> Tuple[float, float]:
        """
        Get Beta distribution parameters for an arm.
        
        If this is a new arm and similarity is provided, initialize with
        an informed prior based on vector similarity.
        """
        if key not in self.arm_params:
            # Initialize new arm
            self.initialize_from_similarity(key, similarity)
        
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
            "feedback_count": self.get_feedback_count(key),
        }
    
    def get_feedback_count(self, key: tuple) -> int:
        """
        Get the number of feedbacks for an arm.
        
        Initial alpha + beta = 2 + init_strength (similarity-based init)
        Each feedback adds update_strength to either alpha or beta
        So: n = (alpha + beta - (2 + init_strength)) / update_strength
        """
        if key not in self.arm_params:
            return 0
        
        alpha, beta = self.arm_params[key]
        initial_total = 2.0 + self.init_strength
        
        # Avoid negative counts due to floating point
        feedback_total = max(0.0, alpha + beta - initial_total)
        return int(feedback_total / self.update_strength)
    
    def initialize_from_similarity(self, key: tuple, similarity: float = None) -> Tuple[float, float]:
        """
        Initialize arm parameters based on similarity score.
        
        Args:
            key: (product_id, recommended_product_id) tuple
            similarity: Vector similarity score (0-1). If None, uses uninformed prior.
        
        Returns: (alpha, beta) for the new arm
        """
        if similarity is not None:
            # Informed prior based on similarity
            # DEMO: init_strength=4.0, Normal: init_strength=1.0 (or configured)
            alpha = 1.0 + similarity * self.init_strength
            beta = 1.0 + (1.0 - similarity) * self.init_strength
        else:
            # Uninformed prior: Beta(1, 1) = Uniform distribution
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
    
    MMR (Maximal Marginal Relevance) for diversity:
    - Top K items are exempt from MMR (preserve most relevant)
    - Remaining items use sliding window diversity constraint
    """
    
    def __init__(self, repository: ProductRepository = None):
        self.repo = repository or get_repository()
        
        # Thompson Sampling for exploration-exploitation
        # Pass database engine to load existing arm_stats
        self.sampler = ThompsonSampler(engine=self.repo.engine)
        
        # Price penalty configuration
        self.price_penalty_threshold = 1.5  # Penalty if accessory > 1.5x main product price
        self.price_penalty_max = 0.3  # Maximum penalty (30% reduction)
        
        # Multi-channel retrieval parameters
        self.vector_retrieval_size = settings.VECTOR_RETRIEVAL_SIZE
        self.llm_retrieval_enabled = settings.LLM_RETRIEVAL_ENABLED
        self.rrf_k = settings.RRF_K
        
        # MMR parameters (from settings)
        self.mmr_enabled = settings.MMR_ENABLED
        self.mmr_retrieval_size = settings.MMR_RETRIEVAL_SIZE
        self.mmr_return_size = settings.MMR_RETURN_SIZE
        self.mmr_pure_top_k = settings.MMR_PURE_TOP_K
        self.mmr_window_size = settings.MMR_WINDOW_SIZE
        self.mmr_lambda = settings.MMR_LAMBDA
        self.mmr_min_score = settings.MMR_MIN_SCORE
        
        # Scoring weight parameters
        self.demo_mode = settings.DEMO_MODE
        self.ts_base_weight_demo = settings.TS_BASE_WEIGHT_DEMO  # Fixed weight in DEMO mode
        self.ts_weight_halflife = settings.TS_WEIGHT_HALFLIFE    # Halflife for dynamic weight
        
        logger.info(f"RecommendationEngine initialized: MMR={'ON' if self.mmr_enabled else 'OFF'}, "
                   f"LLM_RETRIEVAL={'ON' if self.llm_retrieval_enabled else 'OFF'}, "
                   f"DEMO={'ON' if self.demo_mode else 'OFF'}")
    
    def get_ranking(self, product_id: int, use_vector_search: bool = True) -> List[Dict]:
        """
        Get recommendation list using multi-channel retrieval + RRF fusion.
        
        Pipeline:
        1. Multi-channel retrieval (Vector + LLM)
        2. RRF fusion to compute base_score
        3. Thompson Sampling + Price factor scoring
        4. MMR reranking for diversity
        
        Args:
            product_id: Main product ID
            use_vector_search: If True, use pgvector similarity search
            
        Returns:
            List of recommendations
        """
        # Clear pairwise similarity cache for this request
        self._get_pairwise_similarity.cache_clear()
        
        # Get main product
        main_product = self.repo.get_product_by_id(product_id)
        
        if main_product is None:
            logger.warning(f"Product {product_id} not found!")
            return []
        
        # Get main product price for comparison
        main_price = main_product.get('price', 0) or 0
        
        # ========== Multi-channel Retrieval ==========
        vector_candidates = []
        llm_candidates = []
        
        # Channel 1: Vector similarity search
        if use_vector_search:
            try:
                vector_candidates = self.repo.get_similar_products_by_vector(
                    product_id, limit=self.vector_retrieval_size
                )
                for i, c in enumerate(vector_candidates):
                    c['_vector_rank'] = i + 1
                    c['_source'] = 'vector'
                logger.debug(f"Vector retrieval: {len(vector_candidates)} candidates")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
        
        # Channel 2: LLM-based retrieval
        if self.llm_retrieval_enabled:
            try:
                llm_candidates = self.repo.get_llm_recommendations(product_id)
                for i, c in enumerate(llm_candidates):
                    c['_llm_rank'] = i + 1
                logger.debug(f"LLM retrieval: {len(llm_candidates)} candidates")
            except Exception as e:
                logger.debug(f"LLM retrieval not available: {e}")
        
        # ========== UNION + RRF Fusion ==========
        candidates, retrieval_stats = self._merge_and_fuse(
            vector_candidates, 
            llm_candidates,
            main_product['id']
        )
        
        # Fallback: get all accessories if no candidates
        if not candidates:
            candidates = self.repo.get_accessory_products()
            candidates = [c for c in candidates if c['id'] != main_product['id']]
            for c in candidates:
                c['_rrf_score'] = 0.5  # Default score for fallback
            retrieval_stats = {'vector': 0, 'llm': 0, 'union': len(candidates), 'method': 'fallback'}
        
        if not candidates:
            logger.warning(f"No candidates for product {main_product['name']}")
            return []
        
        # Fill candidates if less than minimum (rarely needed now)
        if len(candidates) < self.mmr_return_size:
            candidates = self._fill_candidates(
                main_product_id=main_product['id'],
                existing_candidates=candidates,
                target_count=self.mmr_return_size
            )
        
        # ========== Scoring (TS + Price) ==========
        scored_candidates = self._calculate_scores(
            main_product_id=main_product['id'],
            main_price=main_price,
            candidates=candidates,
            search_method="multi_channel"
        )
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # ========== MMR Reranking ==========
        if self.mmr_enabled and len(scored_candidates) > self.mmr_return_size:
            scored_candidates = self._mmr_rerank(scored_candidates)
            logger.debug(f"MMR reranking -> {len(scored_candidates)} items")
        else:
            scored_candidates = scored_candidates[:self.mmr_return_size]
        
        # Build response
        result = self._build_response(scored_candidates)
        
        logger.info(f"Product {product_id}: Vector={retrieval_stats.get('vector', 0)}, "
                   f"LLM={retrieval_stats.get('llm', 0)}, UNION={retrieval_stats.get('union', 0)} "
                   f"-> {len(result)} recommendations")
        return result
    
    def _merge_and_fuse(
        self,
        vector_candidates: List[Dict],
        llm_candidates: List[Dict],
        main_product_id: int
    ) -> Tuple[List[Dict], Dict]:
        """
        Merge candidates from multiple channels and compute RRF scores.
        
        RRF formula: score = sum(1 / (k + rank)) for each channel
        
        Returns:
            (merged_candidates, retrieval_stats)
        """
        # Build candidate map for deduplication
        candidate_map: Dict[int, Dict] = {}
        
        # Add vector candidates
        for c in vector_candidates:
            cid = c['id']
            if cid not in candidate_map:
                candidate_map[cid] = c.copy()
                candidate_map[cid]['_vector_rank'] = c.get('_vector_rank')
                candidate_map[cid]['_llm_rank'] = None
            else:
                candidate_map[cid]['_vector_rank'] = c.get('_vector_rank')
        
        # Add LLM candidates (merge if exists)
        for c in llm_candidates:
            cid = c['id']
            if cid not in candidate_map:
                candidate_map[cid] = c.copy()
                candidate_map[cid]['_vector_rank'] = None
                candidate_map[cid]['_llm_rank'] = c.get('_llm_rank')
            else:
                candidate_map[cid]['_llm_rank'] = c.get('_llm_rank')
                # Keep LLM match score if available
                if c.get('llm_match_score'):
                    candidate_map[cid]['llm_match_score'] = c['llm_match_score']
        
        # Compute RRF scores
        k = self.rrf_k
        max_rrf = 2.0 / (k + 1)  # Maximum possible (rank 1 in both channels)
        
        for cid, c in candidate_map.items():
            rrf_score = 0.0
            
            # Vector channel contribution
            if c.get('_vector_rank') is not None:
                rrf_score += 1.0 / (k + c['_vector_rank'])
            
            # LLM channel contribution
            if c.get('_llm_rank') is not None:
                rrf_score += 1.0 / (k + c['_llm_rank'])
            
            # Normalize to [0, 1]
            c['_rrf_score'] = rrf_score / max_rrf if max_rrf > 0 else 0.0
        
        # Convert to list
        candidates = list(candidate_map.values())
        
        # Stats
        retrieval_stats = {
            'vector': len(vector_candidates),
            'llm': len(llm_candidates),
            'union': len(candidates),
            'overlap': len(vector_candidates) + len(llm_candidates) - len(candidates),
            'method': 'multi_channel'
        }
        
        return candidates, retrieval_stats
    
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
        
        logger.debug(f"Filled {len(fill_candidates)} candidates "
                    f"({len(existing_candidates)} -> {len(existing_candidates) + len(fill_candidates)})")
        
        return existing_candidates + fill_candidates
    
    @lru_cache(maxsize=10000)
    def _get_pairwise_similarity(self, id_i: int, id_j: int) -> float:
        """
        Cached pairwise cosine similarity between two products (for MMR).
        
        """
        prod_i = self.repo.get_product_by_id(id_i)
        prod_j = self.repo.get_product_by_id(id_j)
        
        if not prod_i or not prod_j:
            return 0.0
        
        emb_i = prod_i.get('embedding')
        emb_j = prod_j.get('embedding')
        
        if emb_i is None or emb_j is None:
            return 0.0
        
        emb_i = np.array(emb_i)
        emb_j = np.array(emb_j)
        
        norm_i = np.linalg.norm(emb_i)
        norm_j = np.linalg.norm(emb_j)
        
        if norm_i == 0 or norm_j == 0:
            return 0.0
        
        return float(np.dot(emb_i, emb_j) / (norm_i * norm_j))
    
    def _mmr_rerank(self, scored_candidates: List[Dict]) -> List[Dict]:
        """
        MMR (Maximal Marginal Relevance) reranking for diversity.
        
        Strategy:
        - Position 1 ~ PURE_TOP_K: Take top items directly (preserve most relevant)
        - Position > PURE_TOP_K: Use sliding window MMR
        
        MMR score for position t:
        score_i = λ * rel_i - (1-λ) * max_{j in window} sim(i, j)
        
        Args:
            scored_candidates: List of candidates sorted by relevance score (descending)
            
        Returns:
            MMR-reranked list of candidates
        """
        if len(scored_candidates) <= self.mmr_return_size:
            return scored_candidates
        
        selected = []
        remaining = scored_candidates.copy()
        
        # Phase 1: Take top K directly (preserve most relevant)
        pure_top_k = min(self.mmr_pure_top_k, len(remaining), self.mmr_return_size)
        for _ in range(pure_top_k):
            if remaining:
                selected.append(remaining.pop(0))
        
        logger.debug(f"MMR Phase 1: Selected top {len(selected)} items directly")
        
        # Phase 2: MMR selection for remaining positions
        while len(selected) < self.mmr_return_size and remaining:
            # Get sliding window (last W items in selected)
            window_start = max(0, len(selected) - self.mmr_window_size)
            window = selected[window_start:]
            
            best_mmr_score = float('-inf')
            best_idx = 0
            
            for idx, cand in enumerate(remaining):
                rel_score = cand['score']
                
                # Skip items below minimum relevance threshold
                if rel_score < self.mmr_min_score:
                    continue
                
                # Calculate max similarity with items in window
                cand_id = cand['item']['id']
                max_sim = 0.0
                
                for sel in window:
                    sel_id = sel['item']['id']
                    sim = self._get_pairwise_similarity(cand_id, sel_id)
                    max_sim = max(max_sim, sim)
                
                # MMR score: λ * relevance - (1-λ) * max_similarity
                mmr_score = self.mmr_lambda * rel_score - (1 - self.mmr_lambda) * max_sim
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx
            
            # Select the best candidate
            if best_mmr_score > float('-inf'):
                selected.append(remaining.pop(best_idx))
            else:
                # No valid candidates left (all below threshold)
                break
        
        logger.debug(f"MMR Phase 2: Final selection has {len(selected)} items")
        
        return selected
    
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
        
        Base score sources (in priority order):
        1. RRF fusion score (multi-channel RETRIEVAL)
        2. Vector similarity (single-channel)
        3. Deterministic hash-based (fallback/fill)
        
        DEMO_MODE: Fixed weights for visible learning effects
            combined = base_score * 0.8 + thompson_weight * 0.2
        
        Normal mode: Dynamic weights based on feedback count
            gamma = n / (n + k)  where n = feedback count, k = halflife
            combined = (1 - gamma) * base_score + gamma * thompson_weight
            
        Final: final_score = combined * price_factor
        """
        scored = []
        
        for item in candidates:
            # Base score (priority: RRF > vector similarity > hash-based)
            if '_rrf_score' in item:
                # Multi-channel RETRIEVAL: use RRF fusion score
                base_score = item['_rrf_score']
                # For TS init, prefer vector similarity if available
                similarity_for_init = item.get('similarity', base_score)
            elif 'similarity' in item:
                # Single-channel vector RETRIEVAL
                base_score = item['similarity']
                similarity_for_init = item['similarity']
            elif item.get('_is_fill'):
                # Filled candidates get lower, deterministic score
                base_score = 0.3 + (hash(item['id']) % 1000) / 5000.0  # 0.3~0.5
                similarity_for_init = 0.3
            else:
                # Fallback
                base_score = 0.1 + (hash(item['id']) % 1000) / 5000.0 
                similarity_for_init = 0.1  
            
            # Thompson Sampling weight (exploration-exploitation)
            # Pass similarity to initialize informed prior for new arms
            arm_key = (main_product_id, item['id'])
            thompson_weight = self.sampler.sample(arm_key, similarity=similarity_for_init)
            
            # Price factor (penalize expensive accessories)
            candidate_price = item.get('price', 0) or 0
            price_factor = self._calculate_price_factor(main_price, candidate_price)
            
            # Combine scores with mode-specific weighting
            if self.demo_mode:
                # DEMO mode: Fixed weights for visible learning effects
                base_weight = self.ts_base_weight_demo  # 0.8
                ts_weight = 1.0 - base_weight  # 0.2
                combined_score = base_score * base_weight + thompson_weight * ts_weight
            else:
                # Normal mode: Dynamic weights based on feedback count
                # gamma increases from 0 to 1 as feedback accumulates
                n = self.sampler.get_feedback_count(arm_key)
                k = self.ts_weight_halflife  # Feedback count for gamma=0.5
                gamma = n / (n + k) if (n + k) > 0 else 0.0
                
                # Cold start: rely on base_score; with feedback: rely on TS
                combined_score = (1.0 - gamma) * base_score + gamma * thompson_weight
            
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
        
        action = "👍 Positive" if is_relevant else "👎 Negative"
        logger.info(f"Feedback: {action} | Main={product_id}, Rec={recommended_product_id} | "
                   f"Beta({alpha:.1f},{beta:.1f}) -> E[θ]={expected:.3f}")
        
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


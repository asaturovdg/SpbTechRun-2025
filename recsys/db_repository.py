"""
Database Access Layer - Handles all database operations

"""
import logging
import os
import sys
from typing import List, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.config.config import settings
from app.models import Product

# Configure logging
logger = logging.getLogger(__name__)


class ProductRepository:
    
    def __init__(self):
        """Initialize the database connection and load products"""
        self.engine = create_engine(settings.database_url_sync, echo=False)
        self._products: List[Dict] = []
        self._product_map: Dict = {}
        self._load_products()
    
    def _load_products(self):
        """Load all products from the database to memory"""
        with Session(self.engine) as session:
            products = session.execute(select(Product)).scalars().all()
            
            self._products = []
            self._product_map = {}
            
            for p in products:
                product_dict = {
                    # Core fields
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "product_role": p.product_role,
                    
                    # Category fields
                    "category_id": p.category_id,
                    "category_name": getattr(p, 'category_name', ''),
                    
                    # Type/Classification fields
                    "type": getattr(p, 'type', ''),  # Replaces white_box_type
                    "parent_id": getattr(p, 'parent_id', ''),
                    "parent_name": getattr(p, 'parent_name', ''),
                    
                    # Product details
                    "vendor": getattr(p, 'vendor', ''),
                    "picture_url": getattr(p, 'picture_url', ''),
                    "url": getattr(p, 'url', ''),
                    "description": getattr(p, 'description', ''),
                    
                    # Physical attributes
                    "weight_kg": getattr(p, 'weight_kg', None),
                    "shipping_weight_kg": getattr(p, 'shipping_weight_kg', None),
                    "volume_l": getattr(p, 'volume_l', None),
                    "length_mm": getattr(p, 'length_mm', None),
                    
                    # Additional params
                    "key_params": getattr(p, 'key_params', {}) or {},
                    
                    # Embedding vector (for similarity search)
                    "embedding": getattr(p, 'embedding', None),
                }
                
                self._products.append(product_dict)
                self._product_map[p.id] = product_dict
        
        logger.info(f"Loaded {len(self._products)} products from database")
    
    def reload(self):
        self._load_products()
    
    def get_all_products(self) -> List[Dict]:
        return self._products
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        return self._product_map.get(product_id)
    
    def get_main_products(self) -> List[Dict]:
        #Get all main products (product_role='основной товар')
        return [p for p in self._products if p.get('product_role') == 'основной товар']
    
    def get_accessory_products(self) -> List[Dict]:
        #Get all accessory products (product_role='сопутка')
        return [p for p in self._products if p.get('product_role') == 'сопутка']
    
    def get_products_by_type(self, product_type: str, role: str = None) -> List[Dict]:
        #Get products by type 
        result = []
        for p in self._products:
            if p.get('type') == product_type:
                if role is None or p.get('product_role') == role:
                    result.append(p)
        return result
    
    def get_products_by_category(self, category_name: str = None, category_id: str = None) -> List[Dict]:
        #Get products by category name or ID
        result = []
        for p in self._products:
            if category_name and p.get('category_name') == category_name:
                result.append(p)
            elif category_id and p.get('category_id') == category_id:
                result.append(p)
        return result
    
    def get_candidates(self, product_type: str = None, exclude_id: int = None) -> List[Dict]:
        #Get candidate accessory products
        candidates = []
        for p in self._products:
            # Must be accessory product
            if p.get('product_role') != 'сопутка':
                continue
            
            # Exclude specified product
            if p.get('id') == exclude_id:
                continue
            
            # Filter by type if specified
            if product_type is not None and p.get('type') != product_type:
                continue
            
            candidates.append(p)
        
        return candidates
    
    def get_products_with_embeddings(self) -> List[Dict]:
        # Get all products that have embeddings
        return [p for p in self._products if p.get('embedding') is not None]
    
    def get_similar_products_by_vector(self, product_id: int, limit: int = 20) -> List[Dict]:
        
        results = []
        
        with Session(self.engine) as session:
            # Use pgvector cosine distance (<=> operator)
            # Cosine distance range: 0 (identical) ~ 2 (opposite)
            # Convert to similarity: 1 - distance/2, so range becomes 0~1
            query = text("""
                SELECT p2.id, p2.name, p2.product_role, p2.price, 
                       p2.category_name, p2.vendor, p2.picture_url,
                       p2.type, p2.description, p2.url,
                       (1.0 - (p1.embedding <=> p2.embedding) / 2.0) as similarity
                FROM products p1, products p2
                WHERE p1.id = :product_id
                  AND p2.id != :product_id
                  AND p1.embedding IS NOT NULL
                  AND p2.embedding IS NOT NULL
                  AND p2.product_role = 'сопутка'
                ORDER BY p1.embedding <=> p2.embedding
                LIMIT :limit
            """)
            
            result = session.execute(query, {
                "product_id": product_id,
                "limit": limit
            })
            
            for row in result:
                results.append({
                    "id": row.id,
                    "name": row.name,
                    "product_role": row.product_role,
                    "price": row.price,
                    "category_name": row.category_name,
                    "vendor": row.vendor,
                    "picture_url": row.picture_url,
                    "type": row.type,
                    "description": row.description,
                    "url": row.url,
                    "similarity": float(row.similarity) if row.similarity else 0.0
                })
        
        return results
    
    def get_llm_recommendations(self, product_id: int) -> List[Dict]:
        """
        Get LLM-based recommendations from llm_recommendations table.
        
        Returns list of matched products with LLM ranking info.
        """
        results = []
        
        with Session(self.engine) as session:
            # Check if table exists first
            try:
                query = text("""
                    SELECT lr.rec_rank, lr.match_score, lr.resolved_rank,
                           p.id, p.name, p.product_role, p.price,
                           p.category_name, p.vendor, p.picture_url,
                           p.type, p.description, p.url
                    FROM llm_recommendations lr
                    JOIN products p ON lr.matched_product_id = p.id
                    WHERE lr.main_product_id = :product_id
                    ORDER BY lr.rec_rank, lr.resolved_rank
                """)
                
                result = session.execute(query, {"product_id": product_id})
                
                for row in result:
                    results.append({
                        "id": row.id,
                        "name": row.name,
                        "product_role": row.product_role,
                        "price": row.price,
                        "category_name": row.category_name,
                        "vendor": row.vendor,
                        "picture_url": row.picture_url,
                        "type": row.type,
                        "description": row.description,
                        "url": row.url,
                        "llm_rank": row.rec_rank,
                        "llm_match_score": float(row.match_score) if row.match_score else 0.0,
                        "_source": "llm"
                    })
                    
            except Exception as e:
                # Table might not exist yet
                logger.debug(f"LLM recommendations not available: {e}")
                return []
        
        return results


# Global singleton to avoid duplicate connections
_repository_instance: Optional[ProductRepository] = None


def get_repository() -> ProductRepository:
    """Get the repository singleton"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ProductRepository()
    return _repository_instance

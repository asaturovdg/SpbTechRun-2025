import random
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
#config of the database
from app.config.config import settings
#table of the database
from app.models import Product


class RecommendationEngine:
    def __init__(self):
        print("initialize RecommendationEngine")
        # connect to the database sync
        self.engine = create_engine(settings.database_url_sync, echo=False)
        # load all products to memory (cache)
        self._load_products()
    
    def _load_products(self):
        #load all products from the database
        with Session(self.engine) as session:
            #like  SELECT * FROM products
            products = session.execute(select(Product)).scalars().all()
            # create product mapping
            self.products = []
            # product map is a dictionary of products
            # key is the id of the product
            # value is the product dictionary
            self.product_map = {}
            for p in products:
                product_dict = {
                    "id": p.id,  # real id of the product
                    "external_id": p.external_id,
                    "name": p.name,
                    "category_id": p.category_id,
                    "price": p.price,
                    # addtional fields from the product
                    "raw_attributes": p.raw_attributes or {},
                }
                # extract common fields from raw_attributes
                product_dict["white_box_type"] = product_dict["raw_attributes"].get("white_box_type", "")
                product_dict["product_role"] = product_dict["raw_attributes"].get("product_role", "")
                product_dict["picture_url"] = product_dict["raw_attributes"].get("picture_url", "")
                product_dict["vendor"] = product_dict["raw_attributes"].get("vendor", "")
                
                self.products.append(product_dict)
                # we use the id and external_id as key to the product dictionary
                # so we can use the id or external_id to get the product dictionary
                self.product_map[p.id] = product_dict
                self.product_map[p.external_id] = product_dict
        
        print(f"Loaded {len(self.products)} products from database")

    def get_candidates_by_white_box_type(self, white_box_type, exclude_product_id=None):
        """Получить все сопутствующие товары на основе white_box_type"""
        candidates = []
        for item in self.products:
            # Найти сопутствующие товары того же типа, исключая основной товар
            if (item.get('white_box_type') == white_box_type and 
                item.get('product_role') == 'сопутка' and
                item.get('id') != exclude_product_id):
                candidates.append(item)
        return candidates

    def get_ranking(self, product_id):
        """
        Swagger API: GET /recommendations/{product_id}
        """
        main_product = self.product_map.get(product_id)
        if main_product is None:
            main_product = self.product_map.get(str(product_id))
        
        if main_product is None:
            # if not found, use the first main product as default
            main_product = next(
                (item for item in self.products if item.get('product_role') == 'основной товар'), 
                self.products[0] if self.products else None
            )
        
        if main_product is None:
            print("No products found in database!")
            return []
        
        # Получить white_box_type основного товара
        white_box_type = main_product.get('white_box_type')
        
        # Получить сопутствующие товары того же типа в качестве кандидатов
        candidates = self.get_candidates_by_white_box_type(white_box_type, exclude_product_id=main_product['id'])

        # Mock Ranking
        # TODO
        shuffled_list = candidates.copy()
        random.shuffle(shuffled_list)

        result = []
        
        for idx, item in enumerate(shuffled_list):
            # Смоделировать балл, первое место с наивысшим баллом
            mock_score = round(0.95 - (idx * 0.1), 2)
            
            # Создать объект, соответствующий схеме RecommendationRead
            rec_product = {
                "id": item['id'],                    
                "external_id": item['external_id'], 
                "name": item['name'],
                "price": item['price'],
                "category_id": item.get('category_id', ''), 
                "raw_attributes": {
                    "picture_url": item.get('picture_url', ''),
                    "vendor": item.get('vendor', ''),
                    "white_box_type": item.get('white_box_type', ''),
                    "product_role": item.get('product_role', '')
                }
            }

            recommendation_obj = {
                "id": idx + 1000,                    # id of the recommendation
                "similarity_score": mock_score,
                "created_at": datetime.now().isoformat(),  
                "recommended_product": rec_product   # recommended product dictionary
            }
            result.append(recommendation_obj)

        print(f"For product {product_id} (white_box_type: {white_box_type}) generated {len(result)} recommendations")
        return result

    def update_model(self, product_id, recommended_product_id, is_relevant):
        """
        Swagger: POST /feedback
        param:
          product_id: ID Основного товара (Context)
          recommended_product_id: ID Рекомендованного товара (Arm)
          is_relevant: Boolean (Reward: True/False)
        """
        # Mock Learning
        action = "Positive feedback" if is_relevant else "Negative feedback"
        print(f"Received feedback: Context={product_id}, Item={recommended_product_id} -> {action}")
        
        # TODO: 
        
        return True
    
    def reload_products(self):
        """reload products from the database (when the database is updated)"""
        self._load_products()


# Self-Check
if __name__ == "__main__":
    engine = RecommendationEngine()
    
    if engine.products:

        main_products = [p for p in engine.products if p.get('product_role') == 'основной товар']
        
        if main_products:
            test_product = main_products[0]
            print(f"\n--- Testing with main product: {test_product['name']} (id={test_product['id']}) ---")
            recs = engine.get_ranking(test_product['id'])
            
            import json
            print(json.dumps(recs, indent=2, ensure_ascii=False))
            
            if recs:
                print("\n--- Testing Feedback ---")
                engine.update_model(test_product['id'], recs[0]['recommended_product']['id'], False)
        else:
            print("No main products found!")
    else:
        print("No products in database!")

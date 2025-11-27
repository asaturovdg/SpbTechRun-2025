import random
from datetime import datetime
import json
import os


FILE_PATH = os.path.join(os.path.dirname(__file__), 'MOCK_DB.json')
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    MOCK_DB = json.load(f)

# для удобного и быстрого поиска
PRODUCT_MAP = {item['id']: item for item in MOCK_DB}


class RecommendationEngine:
    def __init__(self):
        print("initialize RecommendationEngine")
        # TODO: 
        pass

    def get_candidates_by_white_box_type(self, white_box_type, exclude_product_id=None):
        #Получить все сопутствующие товары на основе white_box_type
        candidates = []
        for item in MOCK_DB:
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
        product_id = str(product_id) 
       
        main_product = PRODUCT_MAP.get(product_id)
        
        if main_product is None:
            main_product = next(
                (item for item in MOCK_DB if item.get('product_role') == 'основной товар'), 
                MOCK_DB[0]
            )
        
        # Получить white_box_type основного товара
        white_box_type = main_product.get('white_box_type')
        
        # Получить сопутствующие товары того же типа в качестве кандидатов
        candidates = self.get_candidates_by_white_box_type(white_box_type, exclude_product_id=product_id)

        # Mock Ranking
        # TODO
        shuffled_list = candidates.copy()
        random.shuffle(shuffled_list)

        result = []
        current_time = datetime.now().isoformat() + "Z" 
        
        for idx, item in enumerate(shuffled_list):
            # Смоделировать балл, первое место с наивысшим баллом
            mock_score = round(0.95 - (idx * 0.1), 2)
            
            # Создать объект, соответствующий схеме Swagger
            rec_product = {
                "id": item.get('int_id', 999),
                "external_id": item['id'],     
                "name": item['name'],
                "price": item['price'],
                "category_id": item.get('category_id', ''), 
                
                "raw_attributes": {
                    "picture_url": item.get('picture_url', ''),
                    "vendor": item.get('vendor', ''),
                    "white_box_type": item.get('white_box_type', '')
                }
            }

            recommendation_obj = {
                "id": idx + 1000,  # id of the recommendation
                "similarity_score": mock_score, 
                "created_at": current_time, 
                "recommended_product": rec_product
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
        action = "Positive feedback " if is_relevant else "Negative feedback"
        print(f"Received feedback: Context={product_id}, Item={recommended_product_id} -> {action}")
        
        # TODO: 
        
        return True


# Self-Check
if __name__ == "__main__":
    engine = RecommendationEngine()
    
    print("--- 1. Testing Get Recommendations for '1000932757' (монтаж наливного пола) ---")
    recs = engine.get_ranking("1000932757")
    print(json.dumps(recs, indent=2, ensure_ascii=False))
    
    print("\n--- 2. Testing Get Recommendations for '1000938403' (Монтаж перегородок) ---")
    recs2 = engine.get_ranking("1000938403")
    print(json.dumps(recs2, indent=2, ensure_ascii=False))
    
    print("\n--- 3. Testing Feedback ---")
    engine.update_model("1000932757", "11997707", False)
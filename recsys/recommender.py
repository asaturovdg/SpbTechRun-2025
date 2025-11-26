import random
from datetime import datetime
import json
import os


FILE_PATH = os.path.join(os.path.dirname(__file__), 'MOCK_DB.json')
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    MOCK_DB = json.load(f)


class RecommendationEngine:
    def __init__(self):
        print("initialize RecommendationEngine")
        # TODO: 
        pass

    def get_ranking(self, product_id):
        """
        Swagger API: GET /recommendations/{product_id}
        """
        # Найти соответствующий набор кандидатов по product_id (основной товар), пришедшему с фронтенда
        # Если ID не найден, по умолчанию вернуть первый ключ из mock-данных, чтобы избежать ошибки
        product_id = str(product_id) 
        context_data = MOCK_DB.get(product_id, MOCK_DB["1000932757"])
        
        candidates = context_data.get("candidates", [])

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
                "category_id": item['category_id'], 
                
           
                "raw_attributes": {
                    "picture_url": item['picture_url'],
                    "vendor": item['vendor'],
                    "white_box_type": item['white_box_type']
                }
            }

         
            recommendation_obj = {
                "id": idx + 1000,  #id of the recommendation
                "similarity_score": mock_score, 
                "created_at": current_time, 
                "recommended_product": rec_product
            }
            result.append(recommendation_obj)

        print(f"For product {product_id} generated {len(result)} recommendations")
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


#Self-Check
if __name__ == "__main__":
    engine = RecommendationEngine()
    print("--- 1. Testing Get Recommendations ---")
    recs = engine.get_ranking("1001182240")
    print(json.dumps(recs, indent=2, ensure_ascii=False))
    print("\n--- 2. Testing Feedback ---")
    engine.update_model("1001182240", "25229", False)
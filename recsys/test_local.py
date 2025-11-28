# Before running this script, make sure:
# docker-compose up -d db  
import os
import sys

# force set environment variables 
os.environ["DB_HOST"] = "localhost"
# port of the database because "5432" is used by the default postgres container,so i use "5433"
os.environ["DB_PORT"] = "5433"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_DB"] = "recsys"

# add project root directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# import the recommender engine
from recsys.recommender import RecommendationEngine
import json

if __name__ == "__main__":
    print("=" * 50)
    print("Local Test - Connect to Docker Database (localhost:5433)")
    print("=" * 50)
    
    try:
        engine = RecommendationEngine()
        
        if engine.products:
            print(f"\nSuccessfully loaded {len(engine.products)} products")
            
            # find the main products
            main_products = [p for p in engine.products if p.get('product_role') == 'основной товар']
            print(f"   The main products: {len(main_products)} products")
            
            if main_products:
                test_product = main_products[0]
                print(f"\n Test main product: {test_product['name']} (id={test_product['id']})")
                print(f"   white_box_type: {test_product['white_box_type']}")
                
                print("\n Get recommendations...")
                recs = engine.get_ranking(test_product['id'])
                
                print(f"\n Recommendations ({len(recs)} products):")
                print(json.dumps(recs, indent=2, ensure_ascii=False))
                
                if recs:
                    print("\n✅ Test Feedback...")
                    engine.update_model(test_product['id'], recs[0]['recommended_product']['id'], True)
            else:
                print("⚠️ No main products found!")
        else:
            print("⚠️ No products in database!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. Is the Docker database running")
        print("2. Is the port 5433 correctly mapped")
        print("3. Is there data in the database")


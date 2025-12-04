"""
Local Test Script - Connect to Docker Database

Tests:
- Database connection
- Product loading
- Vector similarity search
- Thompson Sampling feedback
- Price factor penalty
- Stable candidate filling

"""
import os
import sys

# Force set environment variables (before importing other modules!)
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Using 5433 because 5432 is used by local postgres
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_DB"] = "recsys"

# Add project root directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the recommender engine
from recsys.recommender import RecommendationEngine


def test_database_connection(engine):
    """Test database connection and data loading"""
    print("\n" + "=" * 60)
    print("1. Database Connection Test")
    print("=" * 60)
    
    all_products = engine.repo.get_all_products()
    main_products = engine.repo.get_main_products()
    accessory_products = engine.repo.get_accessory_products()
    
    print(f"✅ Database connection successful!")
    print(f"   Total products: {len(all_products)}")
    print(f"   Main products: {len(main_products)}")
    print(f"   Accessory products: {len(accessory_products)}")
    
    # Show sample product structure
    if all_products:
        print("\n📦 Sample product structure:")
        sample = all_products[0]
        for key in ['id', 'name', 'product_role', 'type', 'category_name', 'vendor', 'price']:
            print(f"   {key}: {sample.get(key, 'N/A')}")
    
    return main_products, accessory_products


def test_recommendations(engine, main_products):
    """Test recommendation generation"""
    print("\n" + "=" * 60)
    print("2. Recommendation Generation Test")
    print("=" * 60)
    
    if not main_products:
        print("⚠️ No main products found!")
        return None
    
    test_product = main_products[0]
    print(f"🎯 Testing with main product:")
    print(f"   Name: {test_product['name'][:50]}...")
    print(f"   ID: {test_product['id']}")
    print(f"   Price: {test_product.get('price', 'N/A')}")
    print(f"   Type: {test_product.get('type', 'N/A')}")
    
    print("\n🔍 Getting recommendations...")
    recs = engine.get_ranking(test_product['id'], use_vector_search=True)
    
    print(f"\n📋 Top 5 Recommendations (total: {len(recs)}):")
    for i, rec in enumerate(recs[:5]):
        prod = rec['recommended_product']
        print(f"   {i+1}. {prod['name'][:45]}...")
        print(f"      Price: {prod['price']} | Score: {rec['similarity_score']:.3f}")
    
    return recs, test_product


def test_thompson_sampling(engine, test_product, recs):
    """Test Thompson Sampling feedback mechanism"""
    print("\n" + "=" * 60)
    print("3. Thompson Sampling Feedback Test")
    print("=" * 60)
    
    if not recs or len(recs) < 2:
        print("⚠️ Not enough recommendations to test")
        return
    
    rec_id_1 = recs[0]['recommended_product']['id']
    rec_id_2 = recs[1]['recommended_product']['id']
    
    print(f"Testing feedback for items {rec_id_1} and {rec_id_2}...")
    
    # Simulate positive feedback for first item
    print("\n👍 5x Positive feedback for item 1:")
    for i in range(5):
        engine.update_model(test_product['id'], rec_id_1, True)
    
    # Simulate negative feedback for second item
    print("\n👎 3x Negative feedback for item 2:")
    for i in range(3):
        engine.update_model(test_product['id'], rec_id_2, False)
    
    # Show arm statistics
    print("\n📊 Thompson Sampling Statistics:")
    stats1 = engine.get_arm_stats(test_product['id'], rec_id_1)
    stats2 = engine.get_arm_stats(test_product['id'], rec_id_2)
    print(f"   Item {rec_id_1}: α={stats1['alpha']:.0f}, β={stats1['beta']:.0f}, E[θ]={stats1['expected_value']:.3f}")
    print(f"   Item {rec_id_2}: α={stats2['alpha']:.0f}, β={stats2['beta']:.0f}, E[θ]={stats2['expected_value']:.3f}")
    
    # Get recommendations again to see ranking change
    print("\n🔄 Recommendations after feedback:")
    recs2 = engine.get_ranking(test_product['id'], use_vector_search=False)
    for i, rec in enumerate(recs2[:5]):
        prod = rec['recommended_product']
        marker = "⭐" if prod['id'] == rec_id_1 else ("❌" if prod['id'] == rec_id_2 else "  ")
        print(f"   {marker} {i+1}. {prod['name'][:40]}... | Score: {rec['similarity_score']:.3f}")


def test_recall_counts(engine, main_products):
    """Test how many candidates can be recalled for each main product"""
    print("\n" + "=" * 60)
    print("4. Recall Count Test (Vector Search)")
    print("=" * 60)
    
    if not main_products:
        print("⚠️ No main products found!")
        return
    
    # Check how many products have embeddings
    products_with_embeddings = engine.repo.get_products_with_embeddings()
    all_accessories = engine.repo.get_accessory_products()
    accessories_with_embeddings = [p for p in products_with_embeddings 
                                   if p.get('product_role') == 'сопутка']
    
    print(f"📊 Embedding Statistics:")
    print(f"   Total products with embeddings: {len(products_with_embeddings)}")
    print(f"   Accessories with embeddings: {len(accessories_with_embeddings)}")
    print(f"   Total accessories: {len(all_accessories)}")
    
    # Test recall for first few main products
    test_count = min(5, len(main_products))
    print(f"\n🔍 Testing vector search recall for {test_count} main products:")
    
    recall_stats = []
    for i, product in enumerate(main_products[:test_count]):
        # Test vector search
        try:
            vector_results = engine.repo.get_similar_products_by_vector(product['id'], limit=20)
            vector_count = len(vector_results)
        except Exception as e:
            vector_count = 0
            print(f"   ⚠️ Vector search failed for product {product['id']}: {e}")
        
        # Test full recommendation (with fallback and filling)
        full_recs = engine.get_ranking(product['id'], use_vector_search=True)
        full_count = len(full_recs)
        
        recall_stats.append({
            'id': product['id'],
            'name': product['name'][:30],
            'vector_count': vector_count,
            'full_count': full_count
        })
        
        status = "✅" if vector_count >= 20 else ("⚠️" if vector_count >= 10 else "❌")
        print(f"   {status} Product {product['id']}: Vector={vector_count}, Full={full_count}")
    
    # Summary
    avg_vector = sum(s['vector_count'] for s in recall_stats) / len(recall_stats)
    min_vector = min(s['vector_count'] for s in recall_stats)
    max_vector = max(s['vector_count'] for s in recall_stats)
    
    print(f"\n📈 Summary:")
    print(f"   Vector recall: min={min_vector}, max={max_vector}, avg={avg_vector:.1f}")
    
    if avg_vector >= 20:
        print("   ✅ Vector search returns enough candidates (≥20)")
    elif avg_vector >= 10:
        print("   ⚠️ Vector search returns moderate candidates (10-20)")
        print("   → Filling logic is useful")
    else:
        print("   ❌ Vector search returns few candidates (<10)")
        print("   → Need to generate more embeddings!")


def test_stability(engine, main_products):
    """Test recommendation stability (same results on multiple calls)"""
    print("\n" + "=" * 60)
    print("5. Stability Test (No Random Jumps)")
    print("=" * 60)
    
    if not main_products:
        return
    
    test_product = main_products[0]
    
    # Create new engine instance (fresh state)
    engine2 = RecommendationEngine()
    
    print("Getting recommendations twice with fresh engine...")
    recs1 = engine2.get_ranking(test_product['id'], use_vector_search=False)
    recs2 = engine2.get_ranking(test_product['id'], use_vector_search=False)
    
    # Compare first 5 results
    ids1 = [r['recommended_product']['id'] for r in recs1[:5]]
    ids2 = [r['recommended_product']['id'] for r in recs2[:5]]
    
    if ids1 == ids2:
        print("✅ Results are stable! Same order on repeated calls.")
    else:
        print("⚠️ Results differ between calls:")
        print(f"   Call 1: {ids1}")
        print(f"   Call 2: {ids2}")


if __name__ == "__main__":
    print("=" * 60)
    print("Recommendation Engine Local Test")
    print("Thompson Sampling + Price Factor + Stable Filling")
    print("=" * 60)
    
    try:
        engine = RecommendationEngine()
        
        # Run all tests
        main_products, accessory_products = test_database_connection(engine)
        
        result = test_recommendations(engine, main_products)
        if result:
            recs, test_product = result
            test_thompson_sampling(engine, test_product, recs)
        
        test_recall_counts(engine, main_products)
        test_stability(engine, main_products)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease check:")
        print("1. Is Docker database running? docker-compose up -d db")
        print("2. Is port 5433 correctly mapped?")
        print("3. Is there data in the database?")
        print("4. Has the database schema been updated to new model?")

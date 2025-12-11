"""
Local Test Script

Tests:
- Database connection
- Product loading
- Vector similarity search
- Thompson Sampling feedback (DEMO_MODE)
- Price factor penalty
- Stable candidate filling
- MMR (Maximal Marginal Relevance) diversity

"""
import os
import sys

# Force set environment variables (before importing other modules!)
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Using 5433 because 5432 is used by local postgres
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_DB"] = "recsys"
os.environ["OLLAMA_HOST"] = "localhost"
os.environ["OLLAMA_PORT"] = "11434"
os.environ["MMR_ENABLED"] = "True"

# Add project root directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import settings and recommender
from app.config.config import settings
from recsys.recommender import RecommendationEngine
from recsys import get_recommender


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
    
    # Show DEMO_MODE configuration
    print(f"\n⚙️ Thompson Sampling Configuration:")
    print(f"   DEMO_MODE: {settings.DEMO_MODE}")
    print(f"   Update strength: {settings.ts_update_strength}")
    print(f"   Init strength: {settings.TS_INIT_STRENGTH}")
    print(f"   Max total (α+β): {settings.TS_MAX_TOTAL}")
    if settings.DEMO_MODE:
        print(f"   Base weight (fixed): {settings.TS_BASE_WEIGHT_DEMO}")
    else:
        print(f"   Weight halflife: {settings.TS_WEIGHT_HALFLIFE} (gamma=0.5 at n={settings.TS_WEIGHT_HALFLIFE})")
    
    # Show MMR configuration
    print(f"\n🔀 MMR (Diversity) Configuration:")
    print(f"   MMR Enabled: {settings.MMR_ENABLED}")
    print(f"   Recall size: {settings.MMR_RECALL_SIZE}")
    print(f"   Return size: {settings.MMR_RETURN_SIZE}")
    print(f"   Pure top K: {settings.MMR_PURE_TOP_K}")
    print(f"   Window size: {settings.MMR_WINDOW_SIZE}")
    print(f"   Lambda (relevance): {settings.MMR_LAMBDA}")
    print(f"   Min score: {settings.MMR_MIN_SCORE}")
    
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
    """Test Thompson Sampling feedback mechanism (DEMO_MODE aware)"""
    print("\n" + "=" * 60)
    print("3. Thompson Sampling Feedback Test")
    if settings.DEMO_MODE:
        print(f"   (DEMO_MODE: update_strength = {settings.ts_update_strength})")
    print("=" * 60)
    
    if not recs or len(recs) < 2:
        print("⚠️ Not enough recommendations to test")
        return
    
    rec_id_1 = recs[0]['recommended_product']['id']
    rec_id_2 = recs[1]['recommended_product']['id']
    
    print(f"Testing feedback for items {rec_id_1} and {rec_id_2}...")
    
    # Show initial state
    stats1_before = engine.get_arm_stats(test_product['id'], rec_id_1)
    stats2_before = engine.get_arm_stats(test_product['id'], rec_id_2)
    print(f"\n📊 Initial state:")
    print(f"   Item {rec_id_1}: α={stats1_before['alpha']:.1f}, β={stats1_before['beta']:.1f}, E[θ]={stats1_before['expected_value']:.3f}")
    print(f"   Item {rec_id_2}: α={stats2_before['alpha']:.1f}, β={stats2_before['beta']:.1f}, E[θ]={stats2_before['expected_value']:.3f}")
    
    # Simulate positive feedback for first item (just 1 click in DEMO mode)
    print("\n👍 1x Positive feedback for item 1:")
    engine.update_model(test_product['id'], rec_id_1, True)
    
    # Simulate negative feedback for second item (just 1 click)
    print("👎 1x Negative feedback for item 2:")
    engine.update_model(test_product['id'], rec_id_2, False)
    
    # Show arm statistics after feedback
    stats1_after = engine.get_arm_stats(test_product['id'], rec_id_1)
    stats2_after = engine.get_arm_stats(test_product['id'], rec_id_2)
    
    print(f"\n📊 After feedback:")
    print(f"   Item {rec_id_1}: α={stats1_after['alpha']:.1f}, β={stats1_after['beta']:.1f}, E[θ]={stats1_after['expected_value']:.3f}")
    print(f"   Item {rec_id_2}: α={stats2_after['alpha']:.1f}, β={stats2_after['beta']:.1f}, E[θ]={stats2_after['expected_value']:.3f}")
    
    # Calculate change
    change1 = stats1_after['expected_value'] - stats1_before['expected_value']
    change2 = stats2_after['expected_value'] - stats2_before['expected_value']
    print(f"\n📈 E[θ] change after 1 feedback:")
    print(f"   Item {rec_id_1}: {change1:+.3f} ({change1*100:+.1f}%)")
    print(f"   Item {rec_id_2}: {change2:+.3f} ({change2*100:+.1f}%)")
    
    if settings.DEMO_MODE and (abs(change1) > 0.1 or abs(change2) > 0.1):
        print("   ✅ DEMO_MODE working: visible change after single feedback!")
    
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
    
    recall_size = settings.MMR_RECALL_SIZE
    return_size = settings.MMR_RETURN_SIZE
    
    print(f"📊 Embedding Statistics:")
    print(f"   Total products with embeddings: {len(products_with_embeddings)}")
    print(f"   Accessories with embeddings: {len(accessories_with_embeddings)}")
    print(f"   Total accessories: {len(all_accessories)}")
    print(f"   MMR recall size: {recall_size}, return size: {return_size}")
    
    # Test recall for first few main products
    test_count = min(5, len(main_products))
    print(f"\n🔍 Testing vector search recall for {test_count} main products:")
    
    recall_stats = []
    for i, product in enumerate(main_products[:test_count]):
        # Test vector search with MMR recall size
        try:
            vector_results = engine.repo.get_similar_products_by_vector(
                product['id'], limit=recall_size
            )
            vector_count = len(vector_results)
        except Exception as e:
            vector_count = 0
            print(f"   ⚠️ Vector search failed for product {product['id']}: {e}")
        
        # Test full recommendation (with MMR and filling)
        full_recs = engine.get_ranking(product['id'], use_vector_search=True)
        full_count = len(full_recs)
        
        recall_stats.append({
            'id': product['id'],
            'name': product['name'][:30],
            'vector_count': vector_count,
            'full_count': full_count
        })
        
        # Status based on whether we can recall enough for MMR
        status = "✅" if vector_count >= recall_size else ("⚠️" if vector_count >= return_size else "❌")
        print(f"   {status} Product {product['id']}: Vector={vector_count}, Final={full_count}")
    
    # Summary
    avg_vector = sum(s['vector_count'] for s in recall_stats) / len(recall_stats)
    min_vector = min(s['vector_count'] for s in recall_stats)
    max_vector = max(s['vector_count'] for s in recall_stats)
    
    print(f"\n📈 Summary:")
    print(f"   Vector recall: min={min_vector}, max={max_vector}, avg={avg_vector:.1f}")
    
    if avg_vector >= recall_size:
        print(f"   ✅ Vector search returns enough for MMR (≥{recall_size})")
    elif avg_vector >= return_size:
        print(f"   ⚠️ Vector search returns enough to fill ({return_size}-{recall_size})")
        print(f"   → MMR will work but with less diversity choice")
    else:
        print(f"   ❌ Vector search returns few candidates (<{return_size})")
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


def _analyze_diversity(engine, recs, label=""):
    """Helper function to analyze diversity metrics for a recommendation list"""
    if len(recs) < 5:
        return None
    
    # Category and vendor distribution
    categories = {}
    vendors = {}
    
    for rec in recs:
        prod = rec['recommended_product']
        cat = prod.get('category_name', 'Unknown')
        vendor = prod.get('vendor', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
        vendors[vendor] = vendors.get(vendor, 0) + 1
    
    # Consecutive similarity (positions 4-10)
    consecutive_sims = []
    for i in range(3, min(10, len(recs) - 1)):
        id1 = recs[i]['recommended_product']['id']
        id2 = recs[i + 1]['recommended_product']['id']
        sim = engine._get_pairwise_similarity(id1, id2)
        if sim > 0:
            consecutive_sims.append(sim)
    
    return {
        'label': label,
        'count': len(recs),
        'unique_categories': len(categories),
        'unique_vendors': len(vendors),
        'top_category_pct': max(categories.values()) / len(recs) * 100 if categories else 0,
        'avg_consecutive_sim': sum(consecutive_sims) / len(consecutive_sims) if consecutive_sims else 0,
        'max_consecutive_sim': max(consecutive_sims) if consecutive_sims else 0,
        'ids': [r['recommended_product']['id'] for r in recs],
        'scores': [r['similarity_score'] for r in recs],
    }


def test_mmr_comparison(engine, main_products):
    """A/B Test: Compare recommendations with and without MMR"""
    print("\n" + "=" * 60)
    print("6. MMR A/B Comparison Test")
    print("=" * 60)
    
    if not main_products:
        print("⚠️ No main products found!")
        return
    
    test_product = main_products[0]
    print(f"🎯 Testing: {test_product['name'][:50]}...")
    print(f"   Product ID: {test_product['id']}")
    
    # Save original MMR state
    original_mmr_enabled = engine.mmr_enabled
    
    # --- Test A: Without MMR ---
    print("\n" + "-" * 50)
    print("🅰️  WITHOUT MMR (pure relevance ranking)")
    print("-" * 50)
    
    engine.mmr_enabled = False
    recs_no_mmr = engine.get_ranking(test_product['id'], use_vector_search=True)
    stats_no_mmr = _analyze_diversity(engine, recs_no_mmr, "No MMR")
    
    if stats_no_mmr:
        print(f"\n   📋 Top 10 recommendations:")
        for i, rec in enumerate(recs_no_mmr[:10]):
            prod = rec['recommended_product']
            print(f"      {i+1:2d}. [{rec['similarity_score']:.3f}] {prod['name'][:40]}...")
        
        print(f"\n   📊 Diversity metrics:")
        print(f"      Unique categories: {stats_no_mmr['unique_categories']}")
        print(f"      Unique vendors: {stats_no_mmr['unique_vendors']}")
        print(f"      Top category %: {stats_no_mmr['top_category_pct']:.1f}%")
        print(f"      Avg consecutive sim: {stats_no_mmr['avg_consecutive_sim']:.3f}")
        print(f"      Max consecutive sim: {stats_no_mmr['max_consecutive_sim']:.3f}")
    
    # --- Test B: With MMR ---
    print("\n" + "-" * 50)
    print("🅱️  WITH MMR (diversity reranking)")
    print(f"    λ={engine.mmr_lambda}, window={engine.mmr_window_size}, pure_top_k={engine.mmr_pure_top_k}")
    print("-" * 50)
    
    engine.mmr_enabled = True
    recs_with_mmr = engine.get_ranking(test_product['id'], use_vector_search=True)
    stats_with_mmr = _analyze_diversity(engine, recs_with_mmr, "With MMR")
    
    if stats_with_mmr:
        print(f"\n   📋 Top 10 recommendations:")
        for i, rec in enumerate(recs_with_mmr[:10]):
            prod = rec['recommended_product']
            # Mark items that changed position
            old_pos = stats_no_mmr['ids'].index(prod['id']) + 1 if prod['id'] in stats_no_mmr['ids'] else "?"
            change = ""
            if old_pos != "?" and old_pos != i + 1:
                diff = old_pos - (i + 1)
                change = f" (was #{old_pos}, {'↑' if diff > 0 else '↓'}{abs(diff)})"
            print(f"      {i+1:2d}. [{rec['similarity_score']:.3f}] {prod['name'][:35]}...{change}")
        
        print(f"\n   📊 Diversity metrics:")
        print(f"      Unique categories: {stats_with_mmr['unique_categories']}")
        print(f"      Unique vendors: {stats_with_mmr['unique_vendors']}")
        print(f"      Top category %: {stats_with_mmr['top_category_pct']:.1f}%")
        print(f"      Avg consecutive sim: {stats_with_mmr['avg_consecutive_sim']:.3f}")
        print(f"      Max consecutive sim: {stats_with_mmr['max_consecutive_sim']:.3f}")
    
    # --- Comparison ---
    if stats_no_mmr and stats_with_mmr:
        print("\n" + "-" * 50)
        print("📊 COMPARISON SUMMARY")
        print("-" * 50)
        
        print(f"\n   {'Metric':<25} {'No MMR':>10} {'With MMR':>10} {'Change':>10}")
        print(f"   {'-'*55}")
        
        # Compare metrics
        metrics = [
            ('Unique categories', 'unique_categories', False),
            ('Unique vendors', 'unique_vendors', False),
            ('Top category %', 'top_category_pct', True),  # Lower is better
            ('Avg consecutive sim', 'avg_consecutive_sim', True),  # Lower is better
            ('Max consecutive sim', 'max_consecutive_sim', True),  # Lower is better
        ]
        
        for label, key, lower_is_better in metrics:
            val_a = stats_no_mmr[key]
            val_b = stats_with_mmr[key]
            diff = val_b - val_a
            
            if key in ['top_category_pct']:
                fmt = f"{val_a:>10.1f} {val_b:>10.1f}"
            else:
                fmt = f"{val_a:>10.2f} {val_b:>10.2f}" if isinstance(val_a, float) else f"{val_a:>10} {val_b:>10}"
            
            # Determine if improvement
            if lower_is_better:
                is_better = diff < -0.01
                is_worse = diff > 0.01
            else:
                is_better = diff > 0.01
                is_worse = diff < -0.01
            
            symbol = "✅" if is_better else ("❌" if is_worse else "➖")
            diff_str = f"{diff:+.2f}" if isinstance(diff, float) else f"{diff:+d}"
            
            print(f"   {label:<25} {fmt} {diff_str:>8} {symbol}")
        
        # Position changes
        common_ids = set(stats_no_mmr['ids'][:10]) & set(stats_with_mmr['ids'][:10])
        new_in_top10 = set(stats_with_mmr['ids'][:10]) - set(stats_no_mmr['ids'][:10])
        
        print(f"\n   Position changes (top 10):")
        print(f"      Items in both top 10: {len(common_ids)}")
        print(f"      New items in top 10: {len(new_in_top10)}")
        
        if stats_with_mmr['max_consecutive_sim'] < stats_no_mmr['max_consecutive_sim']:
            print(f"\n   ✅ MMR reduced max consecutive similarity!")
        if stats_with_mmr['unique_categories'] > stats_no_mmr['unique_categories']:
            print(f"   ✅ MMR increased category diversity!")
    
    # Restore original state
    engine.mmr_enabled = original_mmr_enabled


def test_mmr_diversity(engine, main_products):
    """Test MMR diversity effect (detailed analysis)"""
    print("\n" + "=" * 60)
    print("7. MMR Detailed Diversity Analysis")
    print("=" * 60)
    
    if not main_products:
        print("⚠️ No main products found!")
        return
    
    if not engine.mmr_enabled:
        print("⚠️ MMR is disabled. Skipping test.")
        return
    
    test_product = main_products[0]
    print(f"🎯 Testing MMR for: {test_product['name'][:50]}...")
    
    # Get recommendations with MMR
    recs = engine.get_ranking(test_product['id'], use_vector_search=True)
    
    if len(recs) < 10:
        print(f"⚠️ Not enough recommendations ({len(recs)}) to analyze diversity")
        return
    
    # Analyze category diversity
    categories = {}
    vendors = {}
    
    for rec in recs:
        prod = rec['recommended_product']
        cat = prod.get('category_name', 'Unknown')
        vendor = prod.get('vendor', 'Unknown')
        
        categories[cat] = categories.get(cat, 0) + 1
        vendors[vendor] = vendors.get(vendor, 0) + 1
    
    print(f"\n📊 Diversity Analysis (top {len(recs)} recommendations):")
    
    # Category distribution
    print(f"\n   Categories ({len(categories)} unique):")
    sorted_cats = sorted(categories.items(), key=lambda x: -x[1])[:5]
    for cat, count in sorted_cats:
        pct = count / len(recs) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"      {bar} {count:2d} ({pct:4.1f}%) {cat[:30]}")
    
    # Vendor distribution
    print(f"\n   Vendors ({len(vendors)} unique):")
    sorted_vendors = sorted(vendors.items(), key=lambda x: -x[1])[:5]
    for vendor, count in sorted_vendors:
        pct = count / len(recs) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"      {bar} {count:2d} ({pct:4.1f}%) {vendor[:30]}")
    
    # Check for consecutive similar items
    print(f"\n   Consecutive similarity check (positions 4-10):")
    
    consecutive_sims = []
    
    for i in range(3, min(10, len(recs) - 1)):  # Start from position 4 (index 3)
        id1 = recs[i]['recommended_product']['id']
        id2 = recs[i + 1]['recommended_product']['id']
        
        # Use engine's pairwise similarity (in-memory calculation)
        sim = engine._get_pairwise_similarity(id1, id2)
        if sim > 0:
            consecutive_sims.append(sim)
            status = "🔴" if sim > 0.9 else ("🟡" if sim > 0.7 else "🟢")
            print(f"      {status} Position {i+1}-{i+2}: sim={sim:.3f}")
    
    if consecutive_sims:
        avg_sim = sum(consecutive_sims) / len(consecutive_sims)
        max_sim = max(consecutive_sims)
        
        print(f"\n   📈 Consecutive similarity stats:")
        print(f"      Average: {avg_sim:.3f}")
        print(f"      Maximum: {max_sim:.3f}")
        
        if max_sim < 0.9:
            print("      ✅ MMR working: no highly similar consecutive items!")
        elif max_sim < 0.95:
            print("      ⚠️ Some consecutive items are similar (consider lower λ)")
        else:
            print("      ❌ MMR may not be effective (try λ=0.5 or lower)")


if __name__ == "__main__":
    print("=" * 60)
    print("Recommendation Engine Local Test")
    print("Thompson Sampling + Price Factor + MMR Diversity")
    print("=" * 60)
    
    # Configure logging to see debug messages
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        engine = get_recommender()  # Use singleton for consistency
        
        # Run all tests
        main_products, accessory_products = test_database_connection(engine)
        
        result = test_recommendations(engine, main_products)
        if result:
            recs, test_product = result
            test_thompson_sampling(engine, test_product, recs)
        
        test_recall_counts(engine, main_products)
        test_stability(engine, main_products)
        test_mmr_comparison(engine, main_products)  # A/B test
        test_mmr_diversity(engine, main_products)
        
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

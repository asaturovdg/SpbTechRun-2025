"""
Feature Cleaning and Construction Pipeline
Output: temp/product_features_cleaned.csv
"""

import os
import sys
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.config.config import settings
from app.models import Product

# ============================================================================
# Configuration
# ============================================================================

TEMP_DIR = Path(__file__).parent / "temp"
OUTPUT_FILE = TEMP_DIR / "product_features_cleaned.csv"

# Blacklist and Whitelist for key_params cleaning
BLACKLIST_KEYS = {
    "Артикул", "Код товара", "Модель",
    "Количество в упаковке", "Количество предметов", "Вес", "Вес брутто",
    "Объем", "В упаковке", "Тип упаковки",
    "Дополнительно", "Описание", "Комплектация", "Гарантия",
    "Страна", "Страна производства", "Бренд", "Серия",
}

KEYWORD_WHITELIST = [
    "Материал", "Цвет", "Размер", "Длина", "Ширина", "Высота",
    "Толщина", "Диаметр", "Тип", "Вид", "Шлиц", "Назначение",
]


# ============================================================================
# Database Functions
# ============================================================================

def load_data_from_db():
    """Load data from database"""
    print("Loading data from database...")
    
    engine = create_engine(settings.database_url_sync, echo=False)
    
    with Session(engine) as session:
        products = session.execute(select(Product)).scalars().all()
        
        data = []
        for p in products:
            data.append({
                "id": p.id,
                "name": p.name,
                "category_name": getattr(p, 'category_name', ''),
                "category_id": p.category_id,
                "vendor": getattr(p, 'vendor', ''),
                "price": p.price,
                "type": getattr(p, 'type', ''),
                "parent_id": getattr(p, 'parent_id', ''),
                "parent_name": getattr(p, 'parent_name', ''),
                "weight_kg": getattr(p, 'weight_kg', None),
                "shipping_weight_kg": getattr(p, 'shipping_weight_kg', None),
                "volume_l": getattr(p, 'volume_l', None),
                "length_mm": getattr(p, 'length_mm', None),
                "key_params": getattr(p, 'key_params', {}) or {},
                "picture_url": getattr(p, 'picture_url', ''),
                "url": getattr(p, 'url', ''),
                "description": getattr(p, 'description', ''),
                "product_role": p.product_role,
            })
    
    df = pd.DataFrame(data)
    print(f"Successfully loaded {len(df)} records from database")
    return df


"""
Feature Engineering Functions
"""

def generate_whitelist_from_data(df):
    """Generate attribute whitelist using quality assessment algorithm"""
    all_keys = set()
    key_frequency = defaultdict(int)
    key_unique_values = defaultdict(set)
    
    for params in df['key_params']:
        if isinstance(params, dict):
            all_keys.update(params.keys())
            for k, v in params.items():
                key_frequency[k] += 1
                key_unique_values[k].add(str(v).lower())
    
    attr_analysis = []
    for key, freq in sorted(key_frequency.items(), key=lambda x: x[1], reverse=True):
        freq_pct = freq / len(df) * 100
        unique_count = len(key_unique_values[key])
        unique_rate = unique_count / freq if freq > 0 else 0
        
        attr_analysis.append({
            'attribute': key,
            'frequency': freq,
            'freq_pct': freq_pct,
            'unique_count': unique_count,
            'unique_rate': unique_rate,
        })
    
    attr_df = pd.DataFrame(attr_analysis)
    
    if attr_df.empty:
        return [], attr_df
    
    def assess_quality(row):
        attr_name = row['attribute']
        freq = row['frequency']
        unique_count = row['unique_count']
        unique_rate = row['unique_rate']
        
        if attr_name in BLACKLIST_KEYS:
            return 'blacklist'
        if any(keyword in attr_name for keyword in KEYWORD_WHITELIST):
            return 'whitelist'
        if unique_count >= len(df) * 0.7 or unique_rate > 0.9:
            return 'noise_id'
        if unique_count == 1:
            return 'noise_variance'
        if freq < 20:
            return 'general_rare'
        if freq >= 50 and unique_rate <= 0.8 and unique_count >= 2:
            return 'quality'
        return 'general_other'
    
    attr_df['quality'] = attr_df.apply(assess_quality, axis=1)
    final_whitelist = attr_df[attr_df['quality'].isin(['whitelist', 'quality'])]['attribute'].tolist()
    
    return final_whitelist, attr_df


def clean_key_params(key_params_dict, whitelist):
    """Clean key_params using whitelist"""
    if not isinstance(key_params_dict, dict):
        return ""
    
    cleaned = {k: v for k, v in key_params_dict.items() if k in whitelist}
    
    if cleaned:
        pairs = [f"{k}: {v}" for k, v in cleaned.items()]
        return "; ".join(pairs)
    return ""


def clean_name(name):
    """Clean name field: remove data after last comma"""
    if not isinstance(name, str):
        return str(name) if name else ""
    
    if ',' in name:
        clean = name.rsplit(',', 1)[0].strip()
    else:
        clean = name.strip()
    
    clean = re.sub(r'\s+', ' ', clean)
    return clean


def create_breadcrumb(parent_name, category_name):
    """Create Category Breadcrumb"""
    parent = str(parent_name).strip() if pd.notna(parent_name) else ""
    category = str(category_name).strip() if pd.notna(category_name) else ""
    
    if parent and category:
        return f"{parent} > {category}"
    elif category:
        return category
    return parent


def format_price(price):
    """Format price as text"""
    if pd.isna(price):
        return None
    try:
        price_int = int(round(float(price), 0))
        return f"{price_int} RUB"
    except (ValueError, TypeError):
        return None


def get_physical_dimension(row):
    """Get the single physical dimension value"""
    if pd.notna(row.get('weight_kg')):
        return f"Weight: {row['weight_kg']} kg"
    elif pd.notna(row.get('volume_l')):
        return f"Volume: {row['volume_l']} L"
    elif pd.notna(row.get('length_mm')):
        return f"Length: {row['length_mm']} mm"
    return ""


def create_embedding_prompt(row):
    """
    Combine fields to generate embedding prompt
    
    Order by importance:
    1. category (semantic context)
    2. name (core identifier)
    3. key_params (product attributes)
    4. physical dimensions (semantic feature for materials)
    5. description (truncated to avoid dominating)
    """
    parts = []
    

    if row.get('category_breadcrumb'):
        parts.append(f"Категория: {row['category_breadcrumb']}")


    if row.get('name_clean'):
        parts.append(f"Имя: {row['name_clean']}")
    
  
    if row.get('key_params_clean'):
        parts.append(row['key_params_clean'])
    
    physical = get_physical_dimension(row)
    if physical:
        parts.append(physical)
    
    if row.get('description'):
        desc = re.sub(r'\s+', ' ', str(row['description']).strip())
        if desc:
            parts.append(desc[:200])
    
    return ". ".join(parts)



def main():
    print("\n" + "=" * 80)
    print("Feature Cleaning and Construction Pipeline (Database Version)")
    print("=" * 80)
    
    # Ensure temp directory exists
    TEMP_DIR.mkdir(exist_ok=True)
    
    # Step 1: Load data from database
    print("\n[Step 1] Load data from database")
    print("-" * 80)
    df = load_data_from_db()
    
    if df.empty:
        print("ERROR: No data loaded from database!")
        return None
    
    # Step 2: Generate whitelist
    print("\n[Step 2] Generate attribute whitelist")
    print("-" * 80)
    whitelist_attributes, quality_df = generate_whitelist_from_data(df)
    print(f"  Whitelist attributes: {len(whitelist_attributes)}")
    
    # Step 3: Process key_params
    print("\n[Step 3] Process key_params")
    print("-" * 80)
    df['key_params_clean'] = df['key_params'].apply(
        lambda x: clean_key_params(x, whitelist_attributes)
    )
    print("  key_params cleaned")
    
    # Step 4: Clean name
    print("\n[Step 4] Clean name field")
    print("-" * 80)
    df['name_clean'] = df['name'].apply(clean_name)
    print("  Name cleaned")
    
    # Step 5: Create Category Breadcrumb
    print("\n[Step 5] Create Category Breadcrumb")
    print("-" * 80)
    df['category_breadcrumb'] = df.apply(
        lambda row: create_breadcrumb(row['parent_name'], row['category_name']),
        axis=1
    )
    print("  Breadcrumb created")
    
    # Step 6: Process Price
    print("\n[Step 6] Process Price field")
    print("-" * 80)
    df['price_val'] = pd.to_numeric(df['price'], errors='coerce')
    df['price_formatted'] = df['price'].apply(format_price)
    print("  Price processed")
    
    # Step 7: Clean description
    print("\n[Step 7] Clean description")
    print("-" * 80)
    df['description'] = df['description'].apply(
        lambda x: re.sub(r'\s+', ' ', str(x).strip()) if pd.notna(x) else ""
    )
    
    # Step 8: Generate embedding_prompt
    print("\n[Step 8] Generate embedding_prompt")
    print("-" * 80)
    df['embedding_prompt'] = df.apply(create_embedding_prompt, axis=1)
    print(f"  Avg length: {df['embedding_prompt'].str.len().mean():.0f} chars")
    
    # Step 9: Build output dataframe
    print("\n[Step 9] Build final output")
    print("-" * 80)
    
    output_df = df[[
        'id', 'name_clean', 'category_breadcrumb', 'product_role',
        'price_val', 'key_params_clean', 'embedding_prompt'
    ]].copy()
    
    output_df = output_df.rename(columns={
        'name_clean': 'name',
        'key_params_clean': 'key_params',
    })
    
    print(f"  Records: {len(output_df)}")
    print(f"  Columns: {list(output_df.columns)}")
    
    # Step 10: Save to CSV in temp directory
    print("\n[Step 10] Save to CSV")
    print("-" * 80)
    
    output_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print(f"  Saved: {OUTPUT_FILE}")
    print(f"  File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
    
    # Summary
    print("\n" + "=" * 80)
    print("Processing Complete")
    print("=" * 80)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Records: {len(output_df)}")
    print(f"Avg embedding text length: {output_df['embedding_prompt'].str.len().mean():.0f} chars")
    return output_df


if __name__ == "__main__":
    # Force environment variables for local development only
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5433"
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = "postgres"
    os.environ["DB_DB"] = "recsys"
    
    # Re-import settings after setting env vars
    from app.config.config import settings as _settings
    
    output_df = main()

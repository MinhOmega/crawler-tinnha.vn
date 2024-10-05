import json

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def normalize_category_name(name):
    return name.lower().strip().replace(',', '').replace('  ', ' ')

def create_category_map(categories, parent_id=None):
    category_map = {}
    for category in categories:
        normalized_name = normalize_category_name(category['name'])
        category_map[normalized_name] = int(category['id'])
        
        # Add individual words from the category name
        for word in normalized_name.split():
            if word not in category_map:
                category_map[word] = int(category['id'])
        
        if 'children' in category:
            category_map.update(create_category_map(category['children'], category['id']))
    return category_map

def update_product_categories(products, category_map):
    for product in products:
        categories = product['category'].split(', ')
        updated_categories = set()
        for category in categories:
            normalized_category = normalize_category_name(category)
            if normalized_category in category_map:
                updated_categories.add(category_map[normalized_category])
            else:
                # Try to match the full category string
                full_category = normalize_category_name(product['category'])
                if full_category in category_map:
                    updated_categories.add(category_map[full_category])
                    break
                # If full category doesn't match, try individual words
                for word in normalized_category.split():
                    if word in category_map:
                        updated_categories.add(category_map[word])
                        break
                else:
                    print(f"Warning: Category '{category}' not found in category map for product '{product['product_name']}'")
        product['category'] = list(updated_categories)
    return products

def main():
    categories_data = load_json('./categories_nested.json')
    products_data = load_json('./products.json')

    category_map = create_category_map(categories_data)
    updated_products = update_product_categories(products_data, category_map)

    save_json(updated_products, './updated_products.json')
    print("Products updated successfully. Check 'updated_products.json'")

if __name__ == "__main__":
    main()
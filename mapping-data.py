import json

def load_json(file_path):
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(data, file_path):
    """Save JSON data to a file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def map_updated_products(based_products_path, updated_products_path, output_path):
    # Load the old and updated product lists
    based_products = load_json(based_products_path)
    updated_products = load_json(updated_products_path)

    # Create a mapping from SKU to updated product details
    updated_product_map = { 
        (product['product_sku'], product['product_name']): product 
        for product in updated_products 
    }

    # Iterate over the based products and update where applicable
    for based_product in based_products:
        # Check if there's an updated product with the same SKU and name
        key = (based_product['product_sku'], based_product['product_name'])
        if key in updated_product_map:
            # Update based_product with the details from updated_product
            updated_product = updated_product_map[key]
            based_product.update({
                'product_name': updated_product['product_name'],
                'price': updated_product['price'],
                'special_price': updated_product['special_price'],
                'variations': updated_product.get('variations', based_product.get('variations', [])),
                # Add other fields you want to update here...
            })

    # Save the updated based products to a new JSON file
    save_json(based_products, output_path)
    print(f"Updated products saved to {output_path}")

# Usage
based_products_path = 'based_products_after_mapping.json'
updated_products_path = 'updated_products.json'
output_path = 'mapped_products.json'

map_updated_products(based_products_path, updated_products_path, output_path)

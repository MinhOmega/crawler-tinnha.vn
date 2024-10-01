import requests
from bs4 import BeautifulSoup
import csv
import json

def scrape_product_details(product_url):
    """Fetch product details from the product detail page."""
    try:
        response = requests.get(product_url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    soup = BeautifulSoup(response.text, 'html.parser')
    product_details = {}

    # Get the product name
    product_name_tag = soup.find('h1', class_='product-title')
    if product_name_tag:
        product_details['product_name'] = product_name_tag.text.strip()

    # Get the price (for simple products)
    price_tag = soup.find('p', class_='price')
    if price_tag:
        product_details['price'] = price_tag.text.strip().replace('₫', '').replace('&nbsp;', '')

    # Get the product short description
    short_description_tag = soup.find('div', class_='product-short-description')
    if short_description_tag:
        product_details['short_description'] = short_description_tag.text.strip()

    # Get product categories
    category_tags = soup.find('span', class_='posted_in')
    categories = []
    if category_tags:
        for category_tag in category_tags.find_all('a', rel='tag'):
            categories.append(category_tag.text.strip())
        product_details['category'] = ', '.join(categories)

    # Check if product is configurable and gather variations
    variation_form = soup.find('form', class_='variations_form cart')
    if variation_form:
        product_details['product_type'] = 'configurable'
        product_details['variations'] = []

        # Get variation data by parsing the JSON data in the form
        variations_data = variation_form.get('data-product_variations')
        if variations_data:
            variations = json.loads(variations_data)
            for variation in variations:
                if 'display_price' in variation and 'attributes' in variation:
                    variation_code = variation['attributes'].get('attribute_pa_ma-san-pham', '')
                    variation_price = variation['display_price']
                    product_details['variations'].append({
                        'variation_code': variation_code,
                        'variation_price': f"{variation_price}₫"
                    })
    else:
        product_details['product_type'] = 'simple'
        product_details['variations'] = None  # Set variations to null for simple products

    return product_details


def scrape_page(url):
    """Fetch and parse a single page of products."""
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the main product list container
    products_container = soup.find('div', class_='products')
    if not products_container:
        return [], None  # No products found, return empty list

    products = []

    # Iterate over each product block
    for product_item in products_container.find_all('div', class_='product-small', recursive=False):
        product_data = {}
        
        # Get product name and URL
        product_name_tag = product_item.find('p', class_='name product-title woocommerce-loop-product__title')
        if product_name_tag and product_name_tag.find('a'):
            product_url = product_name_tag.find('a')['href']
            product_data = scrape_product_details(product_url)  # Fetch detailed product info

            # Get the image URL
            product_image_tag = product_item.find('img')
            if product_image_tag:
                product_data['image_url'] = product_image_tag['src']

            products.append(product_data)

    # Check for pagination and next page
    next_page_link = soup.find('a', class_='next page-number')
    next_page_url = next_page_link['href'] if next_page_link else None

    return products, next_page_url


def crawl_wordpress_products(base_url):
    """Crawl all products from the shop until the last page."""
    products = []
    current_url = base_url

    while current_url:
        print(f"Scraping page: {current_url}")
        page_products, next_page_url = scrape_page(current_url)
        products.extend(page_products)
        current_url = next_page_url  # Move to the next page if available

    # Remove duplicates based on product URL (excluding 'variations')
    seen = set()
    unique_products = []
    for product in products:
        product_key = (product['product_name'], product['category'], product['price'])  # Key based on product name, category, and price
        if product_key not in seen:
            seen.add(product_key)
            unique_products.append(product)

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_name', 'category', 'price', 'short_description', 'image_url', 'product_type', 'variations'])
        writer.writeheader()
        for product in unique_products:
            # Convert variations to JSON string for CSV export
            if isinstance(product['variations'], list):
                product['variations'] = json.dumps(product['variations'])
            writer.writerow(product)

    print(f"Extracted {len(unique_products)} products. Data exported to products.csv")


if __name__ == "__main__":
    shop_url = 'https://tinnha.vn/shop/'
    crawl_wordpress_products(shop_url)

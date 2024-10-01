import requests
from bs4 import BeautifulSoup
import csv
import json
import concurrent.futures
import time

# Initialize a session to reuse the connection
session = requests.Session()

def fetch_url(url):
    """Fetch a URL using requests."""
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as err:
        print(f"Error fetching {url}: {err}")
        return None


def scrape_product_details(product_url, product_id):
    """Fetch product details from the product detail page."""
    html = fetch_url(product_url)
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    product_details = {'product_id': product_id}  # Include product_id

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
            try:
                variations = json.loads(variations_data)
                for variation in variations:
                    if 'display_price' in variation and 'attributes' in variation:
                        variation_code = variation['attributes'].get('attribute_pa_ma-san-pham', '')
                        variation_price = variation['display_price']
                        product_details['variations'].append({
                            'variation_code': variation_code,
                            'variation_price': f"{variation_price}₫"
                        })
            except json.JSONDecodeError as e:
                print(f"Error parsing variations data for {product_url}: {e}")
    else:
        product_details['product_type'] = 'simple'
        product_details['variations'] = None  # Set variations to null for simple products

    return product_details


def scrape_page(url, start_product_id):
    """Fetch and parse a single page of products."""
    html = fetch_url(url)
    if not html:
        return [], None

    soup = BeautifulSoup(html, 'html.parser')

    # Find the main product list container
    products_container = soup.find('div', class_='products')
    if not products_container:
        return [], None  # No products found, return empty list

    products = []
    product_id = start_product_id  # Initialize product ID for this page

    # Iterate over each product block
    for product_item in products_container.find_all('div', class_='product-small', recursive=False):
        product_data = {'product_id': product_id}  # Assign product ID
        
        # Get product name and URL
        product_name_tag = product_item.find('p', class_='name product-title woocommerce-loop-product__title')
        if product_name_tag and product_name_tag.find('a'):
            product_url = product_name_tag.find('a')['href']
            product_data['product_url'] = product_url  # Store product URL for later fetching

            # Get the image URL
            product_image_tag = product_item.find('img')
            if product_image_tag:
                product_data['image_url'] = product_image_tag['src']

            products.append(product_data)
            product_id += 1  # Increment product ID

    # Check for pagination and next page
    next_page_link = soup.find('a', class_='next page-number')
    next_page_url = next_page_link['href'] if next_page_link else None

    return products, next_page_url, product_id  # Return the updated product_id


def crawl_wordpress_products(base_url, max_workers=10):
    """Crawl all products from the shop until the last page, with concurrent requests."""
    start_time = time.time()  # Record the start time

    products = []
    current_url = base_url
    all_product_data = []
    start_product_id = 1  # Start product ID from 1

    while current_url:
        print(f"Scraping page: {current_url}")
        page_products, next_page_url, start_product_id = scrape_page(current_url, start_product_id)

        # Collect product URLs and image URLs for concurrent fetching of details
        for product in page_products:
            all_product_data.append(product)

        current_url = next_page_url  # Move to the next page if available

    # Fetch product details concurrently using ThreadPoolExecutor
    print(f"Fetching details for {len(all_product_data)} products concurrently...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        detailed_products = list(executor.map(lambda p: scrape_product_details(p['product_url'], p['product_id']), all_product_data))

    # Combine product data with image URLs
    final_products = []
    for idx, product in enumerate(detailed_products):
        if product:  # Ensure product is not empty
            product['image_url'] = all_product_data[idx]['image_url']
            final_products.append(product)

    # Log missing products
    missing_products = len(all_product_data) - len(final_products)
    if missing_products > 0:
        print(f"Warning: {missing_products} products were fetched but not extracted correctly.")

    # Remove duplicates based on product_id
    seen = set()
    unique_products = []
    for product in final_products:
        product_key = product['product_id']  # Key based on product_id
        if product_key not in seen:
            seen.add(product_key)
            unique_products.append(product)

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_id', 'product_name', 'category', 'price', 'short_description', 'image_url', 'product_type', 'variations'])
        writer.writeheader()
        for product in unique_products:
            # Convert variations to JSON string for CSV export
            if isinstance(product['variations'], list):
                product['variations'] = json.dumps(product['variations'])
            writer.writerow(product)

    print(f"Extracted {len(unique_products)} unique products. Data exported to products.csv")

    end_time = time.time()  # Record the end time
    total_time = end_time - start_time  # Calculate the total duration
    print(f"Scraping completed in {total_time:.2f} seconds")


if __name__ == "__main__":
    shop_url = 'https://tinnha.vn/shop/'
    crawl_wordpress_products(shop_url, max_workers=20)  # You can control the number of workers here

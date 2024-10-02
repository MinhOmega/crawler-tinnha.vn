import aiohttp
import asyncio
from bs4 import BeautifulSoup
import csv
import json
import time
from tqdm import tqdm
import os
import re
import unicodedata
from urllib.parse import urlparse
import aiofiles


# Function to determine max workers
def get_max_workers():
    cpu_count = os.cpu_count()
    return min(2 * cpu_count, 10000)


async def fetch_url(url, session):
    """Fetch a URL using aiohttp asynchronously."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as err:
        print(f"Error fetching {url}: {err}")
        return None


async def download_image(url, folder, session):
    """Download image and save to folder."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            image_data = await response.read()

            # Parse the image filename from the URL
            parsed_url = urlparse(url)
            image_name = os.path.basename(parsed_url.path)

            # Ensure the folder exists
            os.makedirs(folder, exist_ok=True)

            # Save the image to the folder
            image_path = os.path.join(folder, image_name)
            async with aiofiles.open(image_path, 'wb') as img_file:
                await img_file.write(image_data)

            return image_path
    except aiohttp.ClientError as err:
        print(f"Error downloading image {url}: {err}")
        return None


def remove_accents(input_str):
    """Remove accents from the input string."""
    nfkd_form = unicodedata.normalize('NFD', input_str)
    return re.sub(r'[\u0300-\u036f]', '', nfkd_form).replace('đ', 'd').replace('Đ', 'D')


def generate_product_sku(product_name):
    """Generate product SKU from product name."""
    product_sku = re.sub(r'[^\w\s]', '', product_name).lower().replace(' ', '_')
    return remove_accents(product_sku)


async def scrape_product_details(product_url, product_id, session):
    """Fetch product details from the product detail page asynchronously."""
    html = await fetch_url(product_url, session)
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    product_details = {'product_id': product_id}

    # Get the product name
    product_name_tag = soup.find('h1', class_='product-title')
    if product_name_tag:
        product_details['product_name'] = product_name_tag.text.strip()

        # Generate product SKU based on product name
        product_details['product_sku'] = generate_product_sku(product_details['product_name'])

    # Get the price (for simple products)
    price_tag = soup.find('p', class_='price')
    if price_tag:
        product_details['price'] = price_tag.text.strip().replace('₫', '').replace('&nbsp;', '')

    # Get the product short description (including HTML formatting for CKEditor)
    short_description_tag = soup.find('div', class_='product-short-description')
    if short_description_tag:
        product_details['short_description'] = str(short_description_tag)  # Save HTML as a string

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


async def scrape_page(url, start_product_id, session):
    """Fetch and parse a single page of products asynchronously."""
    html = await fetch_url(url, session)
    if not html:
        return [], None, start_product_id  # Return empty list, no next page, and unchanged product_id

    soup = BeautifulSoup(html, 'html.parser')

    # Find the main product list container
    products_container = soup.find('div', class_='products')
    if not products_container:
        return [], None, start_product_id  # No products found, return empty list, no next page, and unchanged product_id

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


async def crawl_wordpress_products(base_url, max_workers=None):
    """Crawl all products from the shop until the last page asynchronously."""
    start_time = time.time()  # Record the start time

    products = []
    current_url = base_url
    all_product_data = []
    start_product_id = 1  # Start product ID from 1

    if max_workers is None:
        max_workers = get_max_workers()

    print(f"Using {max_workers} workers...")

    async with aiohttp.ClientSession() as session:
        print("Starting to scrape pages...")
        while current_url:
            print(f"Scraping page: {current_url}")
            try:
                page_products, next_page_url, start_product_id = await scrape_page(current_url, start_product_id, session)
                
                for product in page_products:
                    all_product_data.append(product)

                current_url = next_page_url  # Move to the next page if available
            except Exception as e:
                print(f"Error scraping page {current_url}: {e}")
                break  # Stop scraping if an error occurs

        print(f"Fetching details for {len(all_product_data)} products concurrently...")
        detailed_products = []
        tasks = [scrape_product_details(p['product_url'], p['product_id'], session) for p in all_product_data]
        
        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching Product Details"):
            detailed_product = await task
            if detailed_product:
                detailed_products.append(detailed_product)

        # Create a dictionary to map product_id to product_sku
        id_to_sku = {p['product_id']: p['product_sku'] for p in detailed_products if 'product_sku' in p}

        # Download product images concurrently
        print("Downloading product images...")
        image_tasks = []
        for product in all_product_data:
            if 'image_url' in product and product['product_id'] in id_to_sku:
                product_sku = id_to_sku[product['product_id']]
                image_url = product['image_url']
                image_tasks.append(download_image(image_url, f"./images/{product_sku}", session))
        
        downloaded_images = []
        for task in tqdm(asyncio.as_completed(image_tasks), total=len(image_tasks), desc="Downloading Images"):
            result = await task
            if result:
                downloaded_images.append(result)

        print(f"Successfully downloaded {len(downloaded_images)} images.")

    # Combine product data with image URLs and detailed information
    final_products = []
    for detailed_product, original_product in zip(detailed_products, all_product_data):
        if detailed_product:  # Ensure product is not empty
            detailed_product['image_url'] = original_product['image_url']
            final_products.append(detailed_product)

    # Remove duplicates based on product_id
    seen = set()
    unique_products = []
    for product in final_products:
        product_key = product['product_id']
        if product_key not in seen:
            seen.add(product_key)
            unique_products.append(product)

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_id', 'product_name', 'product_sku', 'category', 'price', 'short_description', 'image_url', 'product_type', 'variations'])
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
    asyncio.run(crawl_wordpress_products(shop_url))

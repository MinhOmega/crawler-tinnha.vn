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
from image_optimizer import run_optimization

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
    product_details['price'] = 0
    product_details['special_price'] = 0
    base_price = 0

    if price_tag:
        # Check if the product has a special price (on sale)
        regular_price_tag = price_tag.find('del')
        special_price_tag = price_tag.find('ins')

        # Extract the regular price if available
        if regular_price_tag:
            regular_price = regular_price_tag.find('bdi').text.strip()
            product_details['price'] = int(regular_price.split('₫')[0].replace('.', '').replace(',', '').strip() or 0)

        # Extract the special price if available
        if special_price_tag:
            special_price = special_price_tag.find('bdi').text.strip()
            product_details['special_price'] = int(special_price.split('₫')[0].replace('.', '').replace(',', '').strip() or 0)

        # If no regular price is found, use the main price as the regular price
        if product_details['price'] == 0 and price_tag.find('bdi'):
            main_price = price_tag.find('bdi').text.strip()
            product_details['price'] = int(main_price.split('₫')[0].replace('.', '').replace(',', '').strip() or 0)

    # Determine if the price is a single price or a range
    base_price = product_details['price']

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

    description_panel = soup.find('div', class_='woocommerce-Tabs-panel--description')
    if description_panel:
        # Extract the content while keeping HTML structure
        description_content = description_panel.decode_contents().strip()

        # Store the content in the product details with the key 'description'
        product_details['description'] = description_content

    # Check if product is configurable and gather variations
    variation_form = soup.find('form', class_='variations_form cart')
    if variation_form:
        product_details['product_type'] = 'configurable'
        product_details['variations'] = []

        # Extract variation details from the JSON data in the form
        variations_data = variation_form.get('data-product_variations')
        attribute_price_map = {}
        if variations_data:
            try:
                variations = json.loads(variations_data)
                for variation in variations:
                    if 'display_price' in variation and 'attributes' in variation:
                        price = variation['display_price']
                        for attribute, value in variation['attributes'].items():
                            attribute_code = attribute.replace('attribute_pa_', '')
                            if attribute_code not in attribute_price_map:
                                attribute_price_map[attribute_code] = {}
                            attribute_price_map[attribute_code][value] = price
            except json.JSONDecodeError as e:
                print(f"Error parsing variations data for {product_url}: {e}")

        # Parse variation attributes from the HTML
        table_variations = soup.find_all('table', class_='variations')
        for table in table_variations:
            for row in table.find_all('tr'):
                label = row.find('label')
                select = row.find('select')
                if label and select:
                    attribute_name = label.text.strip()
                    attribute_code = select.get('name', '').replace('attribute_pa_', '')

                    options = []
                    for option in select.find_all('option'):
                        option_value = option.get('value', '')
                        option_text = option.text.strip()

                        # Skip default option with empty value
                        if option_value:  
                            # Get the display text for the option
                            # Fetch the price from the attribute_price_map if available
                            option_price = attribute_price_map.get(attribute_code, {}).get(option_value, 0)

                            # If option_price is 0 and the product has a single base price, use the base price
                            if option_price == 0 and base_price > 0:
                                option_price = base_price

                            options.append({
                                'attribute_option_code': option_text,
                                'attribute_option_price': option_price
                            })

                    if options:
                        product_details['variations'].append({
                            'attribute_name': attribute_name,
                            'attribute_code': attribute_code,
                            'options': options
                        })
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
        pbar = tqdm(total=None, desc="Scraping Pages", unit="page")
        while current_url:
            try:
                page_products, next_page_url, start_product_id = await scrape_page(current_url, start_product_id, session)
                
                for product in page_products:
                    all_product_data.append(product)

                pbar.update(1)
                pbar.set_postfix_str(f"Current URL: {current_url}")
                
                current_url = next_page_url  # Move to the next page if available
            except Exception as e:
                print(f"\nError scraping page {current_url}: {e}")
                break  # Stop scraping if an error occurs
        pbar.close()

        print(f"\nFetching details for {len(all_product_data)} products concurrently...")
        detailed_products = []
        tasks = [scrape_product_details(p['product_url'], p['product_id'], session) for p in all_product_data]
        
        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching Product Details", unit="product"):
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
        for task in tqdm(asyncio.as_completed(image_tasks), total=len(image_tasks), desc="Downloading Images", unit="image"):
            result = await task
            if result:
                downloaded_images.append(result)

        print(f"Successfully downloaded {len(downloaded_images)} images.")

        # Add the image optimization step here
        print("Optimizing downloaded images...")
        optimized_images = await run_optimization("./images", "./optimized_images")
        print(f"Successfully optimized {len(optimized_images)} images.")

    # Combine product data with image URLs and detailed information
    # Map product_id to image_url for accurate assignment
    product_id_to_image_url = {p['product_id']: p['image_url'] for p in all_product_data}

    final_products = []
    for detailed_product in detailed_products:
        if detailed_product and detailed_product['product_id'] in product_id_to_image_url:
            detailed_product['image_url'] = product_id_to_image_url[detailed_product['product_id']]
            final_products.append(detailed_product)

    # Ensure all products have the same fields
    seen = set()
    unique_products = []
    for product in final_products:
        product_key = product['product_id']
        if product_key not in seen:
            seen.add(product_key)
            unique_products.append(product)

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_id', 'product_name', 'product_sku', 'category', 'price', 'special_price', 'description', 'short_description', 'image_url', 'product_type', 'variations'])
        writer.writeheader()
        for product in unique_products:
            # Convert variations to JSON string for CSV export
            if isinstance(product['variations'], list):
                product['variations'] = json.dumps(product['variations'])
            # Ensure price and special_price are integers
            product['price'] = int(product['price'])
            product['special_price'] = int(product['special_price'])
            writer.writerow(product)

    print(f"Extracted {len(unique_products)} unique products. Data exported to products.csv")

    end_time = time.time()  # Record the end time
    total_time = end_time - start_time  # Calculate the total duration
    print(f"Scraping completed in {total_time:.2f} seconds")


if __name__ == "__main__":
    shop_url = 'https://tinnha.vn/shop/'
    asyncio.run(crawl_wordpress_products(shop_url))
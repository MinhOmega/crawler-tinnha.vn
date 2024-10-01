import aiohttp
import asyncio
from bs4 import BeautifulSoup
import csv
import json
import time
from tqdm import tqdm
import os


# Determine max workers dynamically
def get_max_workers():
    cpu_count = os.cpu_count()
    return min(2 * cpu_count, 10000)


# Asynchronous function to fetch URLs
async def fetch_url(url, session):
    """Fetch a URL asynchronously."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as err:
        print(f"Error fetching {url}: {err}")
        return None


# Asynchronous category scraper
async def scrape_categories(session, base_url):
    """Scrape WordPress categories asynchronously."""
    html = await fetch_url(base_url, session)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    menu = soup.find('ul', class_='nav header-nav header-bottom-nav nav-left nav-divided nav-size-medium nav-uppercase')

    categories = []
    if menu:
        for item in menu.find_all('li', class_='menu-item'):
            main_category = item.find('a', class_='nav-top-link')
            if main_category:
                category_name = main_category.text.strip()
                category_link = main_category['href']
                category_data = {'main_category': category_name, 'url': category_link, 'subcategories': []}

                sub_menu = item.find('ul', class_='sub-menu')
                if sub_menu:
                    for sub_item in sub_menu.find_all('li', class_='menu-item'):
                        sub_category = sub_item.find('a')
                        if sub_category:
                            sub_category_name = sub_category.text.strip()
                            sub_category_link = sub_category['href']
                            category_data['subcategories'].append({
                                'subcategory': sub_category_name,
                                'url': sub_category_link
                            })

                categories.append(category_data)

    return categories


# Save categories to CSV
def save_categories_to_csv(categories):
    with open('categories.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Main Category', 'Main URL', 'Subcategory', 'Subcategory URL'])

        for category in categories:
            if category['subcategories']:
                for sub in category['subcategories']:
                    writer.writerow([category['main_category'], category['url'], sub['subcategory'], sub['url']])
            else:
                writer.writerow([category['main_category'], category['url'], '', ''])

    print("Categories exported to categories.csv")


# Asynchronous product details scraper
async def scrape_product_details(product_url, product_id, session):
    """Fetch product details asynchronously."""
    html = await fetch_url(product_url, session)
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    product_details = {'product_id': product_id}

    product_name_tag = soup.find('h1', class_='product-title')
    if product_name_tag:
        product_details['product_name'] = product_name_tag.text.strip()

    price_tag = soup.find('p', class_='price')
    if price_tag:
        product_details['price'] = price_tag.text.strip().replace('₫', '').replace('&nbsp;', '')

    short_description_tag = soup.find('div', class_='product-short-description')
    if short_description_tag:
        product_details['short_description'] = short_description_tag.text.strip()

    category_tags = soup.find('span', class_='posted_in')
    categories = []
    if category_tags:
        for category_tag in category_tags.find_all('a', rel='tag'):
            categories.append(category_tag.text.strip())
        product_details['category'] = ', '.join(categories)

    variation_form = soup.find('form', class_='variations_form cart')
    if variation_form:
        product_details['product_type'] = 'configurable'
        product_details['variations'] = []

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
        product_details['variations'] = None

    return product_details


# Asynchronous page scraper for products
async def scrape_page(url, start_product_id, session):
    """Fetch and parse a page of products asynchronously."""
    html = await fetch_url(url, session)
    if not html:
        return [], None

    soup = BeautifulSoup(html, 'html.parser')
    products_container = soup.find('div', class_='products')
    if not products_container:
        return [], None

    products = []
    product_id = start_product_id

    for product_item in products_container.find_all('div', class_='product-small', recursive=False):
        product_data = {'product_id': product_id}

        product_name_tag = product_item.find('p', class_='name product-title woocommerce-loop-product__title')
        if product_name_tag and product_name_tag.find('a'):
            product_url = product_name_tag.find('a')['href']
            product_data['product_url'] = product_url

            product_image_tag = product_item.find('img')
            if product_image_tag:
                product_data['image_url'] = product_image_tag['src']

            products.append(product_data)
            product_id += 1

    next_page_link = soup.find('a', class_='next page-number')
    next_page_url = next_page_link['href'] if next_page_link else None

    return products, next_page_url, product_id


# Combine everything and crawl products & categories asynchronously
async def crawl_wordpress(base_url, max_workers=None):
    """Crawl products and categories from the WordPress site asynchronously."""
    start_time = time.time()

    if max_workers is None:
        max_workers = get_max_workers()

    print(f"Using {max_workers} workers...")

    async with aiohttp.ClientSession() as session:
        print("Scraping categories...")
        categories = await scrape_categories(session, base_url)
        save_categories_to_csv(categories)

        print("Scraping products...")
        current_url = base_url + "shop/"
        all_product_data = []
        start_product_id = 1

        while current_url:
            page_products, next_page_url, start_product_id = await scrape_page(current_url, start_product_id, session)
            all_product_data.extend(page_products)
            current_url = next_page_url

        print(f"Fetching details for {len(all_product_data)} products concurrently...")
        detailed_products = []
        tasks = [scrape_product_details(p['product_url'], p['product_id'], session) for p in all_product_data]

        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching Product Details"):
            detailed_products.append(await task)

        final_products = []
        for idx, product in enumerate(detailed_products):
            if product:
                product['image_url'] = all_product_data[idx]['image_url']
                final_products.append(product)

        # Remove duplicates based on product_id
        seen = set()
        unique_products = []
        for product in final_products:
            if product['product_id'] not in seen:
                seen.add(product['product_id'])
                unique_products.append(product)

        # Save products to CSV
        with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['product_id', 'product_name', 'category', 'price', 'short_description', 'image_url', 'product_type', 'variations'])
            writer.writeheader()
            for product in unique_products:
                if isinstance(product['variations'], list):
                    product['variations'] = json.dumps(product['variations'])
                writer.writerow(product)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Scraping completed in {total_time:.2f} seconds")


if __name__ == "__main__":
    base_url = 'https://tinnha.vn/'
    asyncio.run(crawl_wordpress(base_url))

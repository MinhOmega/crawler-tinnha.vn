import requests
from bs4 import BeautifulSoup
import csv

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
        
        # Get product name
        product_name_tag = product_item.find('p', class_='name product-title woocommerce-loop-product__title')
        if product_name_tag and product_name_tag.find('a'):
            product_data['product_name'] = product_name_tag.find('a').text.strip()
            product_data['product_url'] = product_name_tag.find('a')['href']
        
        # Get product category
        category_tag = product_item.find('p', class_='category')
        if category_tag:
            product_data['category'] = category_tag.text.strip()
        
        # Get product price (Handle variable products with price ranges and simple products)
        price_tag = product_item.find('span', class_='price')
        if price_tag:
            if price_tag.find_all('del'):
                # Product on sale (with original and discounted price)
                original_price = price_tag.find('del').text.strip()
                sale_price = price_tag.find('ins').text.strip()
                product_data['original_price'] = original_price
                product_data['sale_price'] = sale_price
                product_data['product_type'] = 'simple'
            elif '–' in price_tag.text:
                # Variable product with price range
                product_data['price'] = price_tag.text.replace('₫', '').replace('&nbsp;', '').strip()
                product_data['product_type'] = 'configurable'
            else:
                # Simple product with one price
                product_data['price'] = price_tag.text.strip().replace('₫', '').replace('&nbsp;', '')
                product_data['product_type'] = 'simple'
        
        # Get product image URL
        product_image_tag = product_item.find('img')
        if product_image_tag:
            product_data['image_url'] = product_image_tag['src']
        
        products.append(product_data)

    # Check for pagination and next page
    next_page_link = soup.find('a', class_='next page-number')
    next_page_url = next_page_link['href'] if next_page_link else None

    return products, next_page_url


def crawl_wordpress_products(base_url):
    products = []
    current_url = base_url

    while current_url:
        print(f"Scraping page: {current_url}")
        page_products, next_page_url = scrape_page(current_url)
        products.extend(page_products)
        current_url = next_page_url  # Move to the next page if available

    # Remove duplicates based on product URL
    products = [dict(t) for t in {tuple(d.items()) for d in products}]

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_name', 'category', 'product_url', 'price', 'original_price', 'sale_price', 'image_url', 'product_type'])
        writer.writeheader()
        writer.writerows(products)

    print(f"Extracted {len(products)} products. Data exported to products.csv")


if __name__ == "__main__":
    shop_url = 'https://tinnha.vn/shop/'
    crawl_wordpress_products(shop_url)

import requests
from bs4 import BeautifulSoup
import csv

def crawl_wordpress_products(base_url):
    products = []
    page_number = 1

    while True:
        url = f"{base_url}/page/{page_number}/" if page_number > 1 else base_url
        print(f"Scraping page: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main product list container
        products_container = soup.find('div', class_='products')

        if not products_container:
            break  # If no products are found, stop the scraping

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
                    product_data['product_type'] = 'simple'  # On-sale products are simple products
                elif '–' in price_tag.text:
                    # Variable product with price range
                    product_data['price'] = price_tag.text.replace('₫', '').replace('&nbsp;', '').strip()
                    product_data['product_type'] = 'configurable'  # Price range means it's configurable
                else:
                    # Simple product with one price
                    product_data['price'] = price_tag.text.strip().replace('₫', '').replace('&nbsp;', '')
                    product_data['product_type'] = 'simple'  # Single price means it's a simple product

            # Get product image URL
            product_image_tag = product_item.find('img')
            if product_image_tag:
                product_data['image_url'] = product_image_tag['src']
            
            products.append(product_data)

        # Check for pagination and next page
        pagination = soup.find('nav', class_='woocommerce-pagination')
        if not pagination or not pagination.find('a', class_='next page-number'):
            break  # If there is no next page, break the loop

        # Move to the next page
        page_number += 1

    # Remove duplicates based on product URL
    products = [dict(t) for t in {tuple(d.items()) for d in products}]

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_name', 'category', 'product_url', 'price', 'original_price', 'sale_price', 'image_url', 'product_type'])
        writer.writeheader()
        for product in products:
            writer.writerow(product)

    print(f"Extracted {len(products)} products from {page_number} pages. Data exported to products.csv")


if __name__ == "__main__":
    shop_url = 'https://tinnha.vn/shop/'
    crawl_wordpress_products(shop_url)

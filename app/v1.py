import requests
from bs4 import BeautifulSoup
import csv

# Crawl categories
def crawl_wordpress_categories(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the menu container with the categories
    menu = soup.find('ul', class_='nav header-nav header-bottom-nav nav-left nav-divided nav-size-medium nav-uppercase')

    categories = []
    
    if menu:
        # Iterate over all the list items (li) which contain categories
        for item in menu.find_all('li', class_='menu-item'):
            main_category = item.find('a', class_='nav-top-link')
            if main_category:
                category_name = main_category.text.strip()
                category_link = main_category['href']
                category_data = {'main_category': category_name, 'url': category_link, 'subcategories': []}

                # Find subcategories if they exist
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

    # Export categories and subcategories to CSV
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


# Crawl products
def crawl_wordpress_products(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the main product list container
    products_container = soup.find('div', class_='products')
    products = []

    if products_container:
        # Iterate over each product block, avoiding duplication by focusing on 'has-hover product'
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
    
    # Remove duplicates based on product URL
    products = [dict(t) for t in {tuple(d.items()) for d in products}]

    # Export products to CSV
    with open('products.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['product_name', 'category', 'product_url', 'price', 'original_price', 'sale_price', 'image_url', 'product_type'])
        writer.writeheader()
        for product in products:
            writer.writerow(product)

    print(f"Extracted {len(products)} products. Data exported to products.csv")


if __name__ == "__main__":
    wordpress_url = 'https://tinnha.vn/'
    
    # Crawl categories
    crawl_wordpress_categories(wordpress_url)

    # Crawl products
    shop_url = wordpress_url + 'shop/'
    crawl_wordpress_products(shop_url)

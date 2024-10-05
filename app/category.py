import requests
from bs4 import BeautifulSoup
import json

def scrape_category(category_tag):
    """Recursively scrape categories and subcategories."""
    category_name = category_tag.find('a').text.strip()
    category_url = category_tag.find('a')['href']
    children = category_tag.find('ul', class_='children')

    category_data = {
        'name': category_name,
        'url': category_url,
        'children': []
    }
    
    if children:
        for child in children.find_all('li', recursive=False):
            category_data['children'].append(scrape_category(child))

    # If there are no subcategories, remove 'children' key to keep the structure clean
    if not category_data['children']:
        del category_data['children']

    return category_data

def crawl_wordpress_categories(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the main category list
    category_list = soup.find('ul', class_='product-categories')
    
    categories = []

    if category_list:
        # Iterate over all top-level categories
        for item in category_list.find_all('li', recursive=False):
            categories.append(scrape_category(item))

    # Prepare the top-level category structure (e.g., 'Sản phẩm')
    result = [{
        'name': 'Sản phẩm',
        'url': 'https://tinnha.vn/shop/',
        'children': categories
    }]

    # Export categories to JSON
    with open('categories_nested.json', 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2)

    print("Categories and subcategories exported to categories_nested.json")


if __name__ == "__main__":
    wordpress_url = 'https://tinnha.vn/shop/'
    crawl_wordpress_categories(wordpress_url)
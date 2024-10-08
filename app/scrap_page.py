import aiohttp
from bs4 import BeautifulSoup
import asyncio

async def fetch_url(url, session):
    """Fetch the HTML content of a URL asynchronously."""
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def scrape_page(url, session):
    """Fetch and parse a single page of products asynchronously."""
    html = await fetch_url(url, session)
    if not html:
        return [], None

    soup = BeautifulSoup(html, 'html.parser')
    products_container = soup.find('div', class_='products')
    if not products_container:
        return [], None

    products = []
    for product_item in products_container.find_all('div', class_='product-small', recursive=False):
        product_data = {}
        
        # Get product name and URL
        product_name_tag = product_item.find('p', class_='name product-title woocommerce-loop-product__title')
        if product_name_tag and product_name_tag.find('a'):
            product_data['product_url'] = product_name_tag.find('a')['href']

            # Get the image URL
            product_image_tag = product_item.find('img')
            if product_image_tag:
                product_data['image_url'] = product_image_tag['src']

            products.append(product_data)

    next_page_link = soup.find('a', class_='next page-number')
    next_page_url = next_page_link['href'] if next_page_link else None

    return products, next_page_url

async def main():
    url = 'https://tinnha.vn/shop/'
    async with aiohttp.ClientSession() as session:
        products, next_page_url = await scrape_page(url, session)
        print(products)
        print(f"Next page URL: {next_page_url}")

if __name__ == "__main__":
    asyncio.run(main())

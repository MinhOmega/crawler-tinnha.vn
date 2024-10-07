import requests
from bs4 import BeautifulSoup

def extract_price(url):
    """Extracts price and special price from the product page."""
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return {'price': '', 'special_price': ''}

        soup = BeautifulSoup(response.content, 'html.parser')
        product_details = {'price': '', 'special_price': ''}

        # Find the price tag
        price_tag = soup.find('p', class_='price')
        if price_tag:
            # Directly find 'del' and 'ins' tags for regular and special prices
            regular_price_tag = price_tag.find('del')
            special_price_tag = price_tag.find('ins')

            # Extract the regular price if available
            if regular_price_tag:
                regular_price = regular_price_tag.find('bdi').text.strip()
                product_details['price'] = regular_price.split('₫')[0].replace('.', '').replace(',', '').strip()

            # Extract the special price if available
            if special_price_tag:
                special_price = special_price_tag.find('bdi').text.strip()
                product_details['special_price'] = special_price.split('₫')[0].replace('.', '').replace(',', '').strip()

            # If no regular price is found, use the main price as the regular price
            if not product_details['price'] and price_tag.find('bdi'):
                main_price = price_tag.find('bdi').text.strip()
                product_details['price'] = main_price.split('₫')[0].replace('.', '').replace(',', '').strip()

        return product_details

    except Exception as e:
        return {'price': '', 'special_price': ''}

if __name__ == "__main__":
    # This block is for testing purposes and won't be executed when imported
    test_url = "https://tinnha.vn/shop/dung-cu-phau-thuat-han-quoc/implant-prosthetic-driver-kit/"
    print(extract_price(test_url))

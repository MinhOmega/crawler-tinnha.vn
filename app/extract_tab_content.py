import requests
from bs4 import BeautifulSoup

def extract_description_content(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch the page. Status code: {response.status_code}")
            return {}

        soup = BeautifulSoup(response.content, 'html.parser')
        product_details = {}

        # Extract content from the description tab
        description_panel = soup.find('div', class_='woocommerce-Tabs-panel--description')
        if description_panel:
            print("Description panel found.")
            # Extract the content while keeping HTML structure
            description_content = description_panel.decode_contents().strip()
            print(f"Extracted description content: {description_content[:100]}...")  # Log first 100 characters

            # Store the content in the product details with the key 'description'
            product_details['description'] = description_content
            print(f"Added description content.")

        else:
            print("No description panel found.")

        # Log the final extracted data
        print(f"Extracted Description Content: {product_details}")
        return product_details

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

# URL of the product page
url = "https://tinnha.vn/shop/sales/implant-prosthetic-driver-kit/"
extract_description_content(url)

import csv
import json
import re

def convert_csv_to_json(csv_file_path, json_file_path):
    # List to store the converted data
    data = []

    # Read the CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # Iterate through each row in the CSV
        for row in csv_reader:
            # Debug print for variations
            print(f"Raw variations string: {row['variations']}")
            
            # Convert variations string to list of dictionaries
            if row['variations']:
                # Clean up the variations string to fix extra quotes
                variations_str = row['variations'].replace("'", '"')  # Replace single quotes with double quotes
                variations_str = variations_str.encode('utf-8').decode('unicode_escape')  # Handle unicode escape sequences
                
                # Remove any extraneous quotes from attribute_option_code
                variations_str = re.sub(r'("attribute_option_code":\s*")([^"]*?)""', r'\1\2"', variations_str)

                try:
                    row['variations'] = json.loads(variations_str)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for variations: {e} - Variations string: {variations_str}")
                    row['variations'] = []  # Default to empty list if JSON decoding fails
            else:
                row['variations'] = []
            
            # Convert price and special_price to integers
            try:
                row['price'] = int(float(row['price']))
            except ValueError:
                row['price'] = 0  # Default to 0 if conversion fails

            try:
                row['special_price'] = int(float(row['special_price']))
            except ValueError:
                row['special_price'] = 0  # Default to 0 if conversion fails

            # Convert product_id to integer
            try:
                row['product_id'] = int(row['product_id'])
            except ValueError:
                row['product_id'] = 0  # Default to 0 if conversion fails
            
            # Append the processed row to the data list
            data.append(row)

    # Write the data to a JSON file
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)

    print(f"Conversion complete. JSON file saved as {json_file_path}")

# Usage
csv_file_path = 'products.csv'
json_file_path = 'products.json'
convert_csv_to_json(csv_file_path, json_file_path)

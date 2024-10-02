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
            # Convert variations string to list of dictionaries
            if row['variations']:
                try:
                    row['variations'] = json.loads(row['variations'].replace("'", '"'))
                except json.JSONDecodeError:
                    row['variations'] = []
            else:
                row['variations'] = []
            
            # Handle price ranges and convert to string
            price_str = row['price'].replace(',', '').strip()
            prices = re.findall(r'\d+', price_str)
            if len(prices) == 1:
                row['price'] = prices[0]
            elif len(prices) > 1:
                row['price'] = f"{prices[0]} - {prices[-1]}"
            else:
                row['price'] = "0"  # Default value if no valid price is found
            
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
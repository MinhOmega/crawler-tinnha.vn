import os
import unicodedata
import re
from pathlib import Path

def remove_accents(input_str):
    """Remove accents from the input string."""
    nfkd_form = unicodedata.normalize('NFD', input_str)
    return re.sub(r'[\u0300-\u036f]', '', nfkd_form).replace('đ', 'd').replace('Đ', 'D')

def process_image_filename(filename):
    """Process filename to remove accents."""
    name, ext = os.path.splitext(filename)
    name_no_accents = remove_accents(name)
    return f"{name_no_accents}{ext}"

def main():
    input_dir = Path('./optimized_images')
    if not input_dir.exists():
        print("Error: optimized_images directory not found")
        return

    # Process all files in the optimized_images directory and its subdirectories
    for root, _, files in os.walk(input_dir):
        root_path = Path(root)
        
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                old_path = root_path / filename
                new_filename = process_image_filename(filename)
                new_path = root_path / new_filename
                
                try:
                    # Only rename if the filename actually changed
                    if filename != new_filename:
                        os.rename(old_path, new_path)
                        print(f"Renamed: {filename} -> {new_filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

    print("Processing complete. All image filenames have been updated.")

if __name__ == "__main__":
    main() 
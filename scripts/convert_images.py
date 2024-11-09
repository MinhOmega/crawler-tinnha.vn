import os
from PIL import Image
import glob
from tqdm import tqdm
import pillow_avif  # Import the AVIF plugin

def convert_images(input_dir, output_dir):
    # Create output directories if they don't exist
    avif_dir = os.path.join(output_dir, 'avif')
    webp_dir = os.path.join(output_dir, 'webp')
    os.makedirs(avif_dir, exist_ok=True)
    os.makedirs(webp_dir, exist_ok=True)

    # Get all image files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
        image_files.extend(glob.glob(os.path.join(input_dir, '**', ext), recursive=True))

    total_files = len(image_files)
    print(f"Found {total_files} images to convert")

    # Use tqdm for progress bar
    for image_path in tqdm(image_files, desc="Converting images"):
        try:
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Get relative path structure
                rel_path = os.path.relpath(image_path, input_dir)
                file_name = os.path.splitext(os.path.basename(image_path))[0]
                sub_dir = os.path.dirname(rel_path)

                # Create subdirectories if needed
                avif_subdir = os.path.join(avif_dir, sub_dir)
                webp_subdir = os.path.join(webp_dir, sub_dir)
                os.makedirs(avif_subdir, exist_ok=True)
                os.makedirs(webp_subdir, exist_ok=True)

                # Save as AVIF
                avif_path = os.path.join(avif_dir, sub_dir, f"{file_name}.avif")
                img.save(avif_path, 'AVIF', quality=65)

                # Save as WebP with optimization
                webp_path = os.path.join(webp_dir, sub_dir, f"{file_name}.webp")
                img.save(webp_path, 'WEBP', quality=80, method=6, lossless=False)

        except Exception as e:
            print(f"\nError processing {image_path}: {str(e)}")
            continue

    print("\nConversion complete!")

if __name__ == "__main__":
    # Set your input and output directories
    input_directory = "optimized_images"  # Directory containing original images
    output_directory = "converted_images" # Directory where converted images will be saved
    
    convert_images(input_directory, output_directory)

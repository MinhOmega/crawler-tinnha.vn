import os
import asyncio
from PIL import Image
from tqdm import tqdm

async def optimize_image(image_path, output_folder, max_size=(800, 800), quality=85):
    """Optimize a single image and save it to the specified output folder."""
    try:
        with Image.open(image_path) as img:
            # Resize the image if it's larger than max_size
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Ensure the output folder exists
            os.makedirs(output_folder, exist_ok=True)
            
            # Save the optimized image
            filename = os.path.basename(image_path)
            optimized_path = os.path.join(output_folder, filename)
            
            # Determine the file format and save accordingly
            if filename.lower().endswith('.png'):
                # For PNG files, preserve the original mode and use PNG-specific optimizations
                img.save(optimized_path, 'PNG', optimize=True)
            else:
                # For other formats, convert to RGB and save as JPEG
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
            
            return optimized_path
    except Exception as err:
        print(f"Error optimizing image {image_path}: {err}")
        return None

async def optimize_images_in_folder(input_folder, output_folder):
    """Optimize all images in the input folder and save them to the output folder."""
    tasks = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                image_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_folder)
                output_subfolder = os.path.join(output_folder, relative_path)
                tasks.append((image_path, output_subfolder))
    
    # Create the progress bar
    progress_bar = tqdm(total=len(tasks), desc="Optimizing Images", unit="image")
    
    # Run tasks with progress update
    optimized_images = []
    for image_path, output_subfolder in tasks:
        result = await optimize_image(image_path, output_subfolder)
        if result:
            optimized_images.append(result)
        progress_bar.update(1)  # Update progress bar after each image is processed
    
    progress_bar.close()
    return optimized_images

async def run_optimization(input_folder="./images", output_folder="./optimized_images"):
    """Run the optimization process on the input folder."""
    print(f"Starting image optimization from '{input_folder}' to '{output_folder}'...")
    optimized_images = await optimize_images_in_folder(input_folder, output_folder)
    print(f"Successfully optimized {len(optimized_images)} images.")
    return optimized_images

if __name__ == "__main__":
    asyncio.run(run_optimization())

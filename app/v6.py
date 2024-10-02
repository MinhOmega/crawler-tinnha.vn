import asyncio
from image_optimizer import run_optimization

async def optimize_existing_images():
    """Optimize images that are already in the 'images' folder."""
    print("Starting image optimization process...")
    optimized_image_paths = await run_optimization(input_folder="./images", output_folder="./optimized_images")
    print(f"Optimized images are saved in the 'optimized_images' folder. Total: {len(optimized_image_paths)}")
    return optimized_image_paths

if __name__ == "__main__":
    optimized_images = asyncio.run(optimize_existing_images())
    print(f"Successfully optimized {len(optimized_images)} images.")
    
    # Print information about optimized images
    for image_path in optimized_images:
        print(f"Optimized: {image_path}")
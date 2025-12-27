#!/usr/bin/env python3
"""
Decompression Bomb Test Generator

This script creates test images to trigger Pillow's decompression bomb detection.
Use these to test the try-on service's security detection (Rule 6).

WARNING: These are test files only - not actual malicious files.
"""

import os
from PIL import Image
import io

# Current limit in try_on.py
TRYON_MAX_PIXELS = 50_000_000  # 50 million pixels

def create_decompression_bomb_test(filename="bomb_test.png", pixels=60_000_000):
    """
    Create a large dimension PNG that will trigger DecompressionBombError.
    
    The image is solid color so it compresses well (small file size, huge decompressed size).
    """
    # Calculate dimensions for target pixel count
    # Using a wide aspect ratio for variety
    width = int((pixels * 2) ** 0.5)  # 2:1 aspect ratio
    height = pixels // width
    
    print(f"Creating test image: {width}x{height} = {width * height:,} pixels")
    print(f"Current Pillow limit: {Image.MAX_IMAGE_PIXELS:,} pixels")
    print(f"Try-on service limit: {TRYON_MAX_PIXELS:,} pixels")
    
    # Temporarily increase limit to create the file
    original_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None  # Disable limit temporarily
    
    try:
        # Create a solid color image (compresses very well)
        # Using mode 'P' (palette) for smallest file size
        img = Image.new('RGB', (width, height), color=(255, 0, 0))  # Solid red
        
        # Save with maximum compression
        img.save(filename, 'PNG', optimize=True)
        file_size = os.path.getsize(filename)
        
        print(f"\n✅ Created: {filename}")
        print(f"   File size: {file_size / 1024:.1f} KB")
        print(f"   Dimensions: {width} x {height}")
        print(f"   Pixels: {width * height:,}")
        print(f"   Decompression ratio: {(width * height * 3) / file_size:.0f}x")
        
    finally:
        Image.MAX_IMAGE_PIXELS = original_limit


def create_invalid_image_test(filename="invalid_test.png"):
    """
    Create an invalid/corrupted image file that will fail Pillow's verify().
    """
    # Write garbage data with PNG header to make it look like a PNG
    with open(filename, 'wb') as f:
        # PNG magic bytes followed by garbage
        f.write(b'\x89PNG\r\n\x1a\n')  # PNG signature
        f.write(b'This is not a valid PNG image content! ' * 100)
    
    file_size = os.path.getsize(filename)
    print(f"\n✅ Created: {filename}")
    print(f"   File size: {file_size} bytes")
    print(f"   Type: Corrupted PNG (invalid)")


def test_with_pillow(filename):
    """Test loading the image with Pillow to see if it triggers detection."""
    print(f"\n🧪 Testing {filename} with Pillow...")
    print(f"   Current MAX_IMAGE_PIXELS: {Image.MAX_IMAGE_PIXELS:,}")
    
    try:
        img = Image.open(filename)
        img.verify()
        
        # Re-open after verify
        img = Image.open(filename)
        img.load()  # Force full decompression
        
        print(f"   ⚠️ Image loaded successfully: {img.size}")
        print(f"   Pixels: {img.size[0] * img.size[1]:,}")
        
    except Image.DecompressionBombError as e:
        print(f"   ✅ DETECTED: DecompressionBombError")
        print(f"   Message: {e}")
        
    except Image.DecompressionBombWarning as e:
        print(f"   ⚠️ WARNING: DecompressionBombWarning")
        print(f"   Message: {e}")
        
    except Exception as e:
        print(f"   ✅ DETECTED: {type(e).__name__}")
        print(f"   Message: {e}")


def main():
    print("=" * 60)
    print("🧪 Decompression Bomb Test Generator")
    print("=" * 60)
    
    # Set Pillow's limit to match try-on service (for accurate testing)
    Image.MAX_IMAGE_PIXELS = TRYON_MAX_PIXELS
    print(f"\nSet Pillow limit to match try-on service: {TRYON_MAX_PIXELS:,} pixels")
    
    # Create test files
    print("\n" + "-" * 40)
    print("Creating test files...")
    print("-" * 40)
    
    # 1. Create a decompression bomb test (exceeds 50M pixel limit)
    create_decompression_bomb_test("test_bomb_60m.png", pixels=60_000_000)
    
    # 2. Create an invalid/corrupted image
    create_invalid_image_test("test_invalid.png")
    
    # 3. Create a borderline image (just under the limit)
    create_decompression_bomb_test("test_borderline_45m.png", pixels=45_000_000)
    
    # Test the files
    print("\n" + "-" * 40)
    print("Testing with Pillow (limit = 50M pixels)...")
    print("-" * 40)
    
    test_with_pillow("test_bomb_60m.png")
    test_with_pillow("test_invalid.png")
    test_with_pillow("test_borderline_45m.png")
    
    print("\n" + "=" * 60)
    print("📝 Test files created:")
    print("   • test_bomb_60m.png    - Should trigger decompression bomb error")
    print("   • test_invalid.png     - Should trigger invalid image error")
    print("   • test_borderline_45m.png - Should load successfully (under limit)")
    print("\n📤 To test with the try-on service endpoint:")
    print("""
curl -X POST http://localhost:8081/tryon \\
  -F "base_image=@test_bomb_60m.png" \\
  -F "product_image=@docs/img/tryon.png" \\
  -F "category=fashion"

curl -X POST http://localhost:8081/tryon \\
  -F "base_image=@test_invalid.png" \\
  -F "product_image=@docs/img/tryon.png" \\
  -F "category=fashion"
""")
    print("=" * 60)


if __name__ == "__main__":
    main()

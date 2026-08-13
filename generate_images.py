import sys
import subprocess

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    install("Pillow")
    from PIL import Image, ImageDraw, ImageFont

def create_image(filename):
    img = Image.new('RGB', (512, 512), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    # Simple default font
    try:
        font = ImageFont.truetype("arial.ttf", 100)
    except IOError:
        font = ImageFont.load_default()
    
    text = "NKS"
    # Get bounding box for text
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    d.text(((512-w)/2, (512-h)/2), text, fill=(255, 255, 0), font=font)
    img.save(filename)

create_image('brands/icon.png')
create_image('brands/logo.png')
print("Images created successfully.")

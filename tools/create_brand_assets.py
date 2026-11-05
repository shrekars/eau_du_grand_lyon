import shutil
import os

base = r"c:\Users\kevin.delmont\Downloads\eau_du_grand_lyon (4)\custom_components\eau_du_grand_lyon"
brand_dir = os.path.join(base, "brand")
os.makedirs(brand_dir, exist_ok=True)

shutil.copy(os.path.join(base, "icon.png"), os.path.join(brand_dir, "icon.png"))
shutil.copy(os.path.join(base, "logo.png"), os.path.join(brand_dir, "logo.png"))
if os.path.exists(os.path.join(base, "icon@2x.png")):
    shutil.copy(os.path.join(base, "icon@2x.png"), os.path.join(brand_dir, "icon@2x.png"))
if os.path.exists(os.path.join(base, "logo@2x.png")):
    shutil.copy(os.path.join(base, "logo@2x.png"), os.path.join(brand_dir, "logo@2x.png"))

print("Brand assets créés dans custom_components/eau_du_grand_lyon/brand/")


import shutil
import os

root = r"c:\Users\kevin.delmont\Downloads\eau_du_grand_lyon (4)"
src_icon = os.path.join(root, "custom_components", "eau_du_grand_lyon", "icon.png")
src_logo = os.path.join(root, "custom_components", "eau_du_grand_lyon", "logo.png")

# 1. Racine du repo
shutil.copy(src_icon, os.path.join(root, "icon.png"))
shutil.copy(src_logo, os.path.join(root, "logo.png"))

# 2. Dossier images/
images_dir = os.path.join(root, "images")
os.makedirs(images_dir, exist_ok=True)
shutil.copy(src_icon, os.path.join(images_dir, "icon.png"))
shutil.copy(src_logo, os.path.join(images_dir, "logo.png"))

print("Icônes copiées à la racine et dans images/")


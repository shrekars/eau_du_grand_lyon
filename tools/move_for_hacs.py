import os
import shutil

root = r"c:\Users\kevin.delmont\Downloads\eau_du_grand_lyon (4)"
src = os.path.join(root, "eau_du_grand_lyon")
dst_parent = os.path.join(root, "custom_components")
dst = os.path.join(dst_parent, "eau_du_grand_lyon")

if os.path.exists(src):
    os.makedirs(dst_parent, exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.move(src, dst)
    print("Déplacement réussi vers custom_components/eau_du_grand_lyon")
else:
    print("Source non trouvée ou déjà déplacée")


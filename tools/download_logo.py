import urllib.request
import os

target_dir = r"c:\Users\kevin.delmont\Downloads\eau_du_grand_lyon (4)\eau_du_grand_lyon"
urls = [
    # Icône Google Play Store officielle 512x512
    "https://play-lh.googleusercontent.com/3D10yAR-EcmFJQGucUV0KYBtswbGUtOp_xHIjm2sU-NDuL-k0nWgwve4BlvWbFvi_BR_1omGS-ZTaiFX0NlhMA=s512",
]

req = urllib.request.Request(
    urls[0],
    headers={"User-Agent": "Mozilla/5.0"}
)

try:
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        print(f"Téléchargé : {len(data)} octets")
        for filename in ["icon.png", "logo.png", "icon@2x.png", "logo@2x.png"]:
            p = os.path.join(target_dir, filename)
            with open(p, "wb") as f:
                f.write(data)
            print(f"Écrit : {p}")
except Exception as e:
    print(f"Erreur : {e}")


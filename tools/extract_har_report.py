import json
import os

har_path = r"C:\Users\kevin.delmont\.gemini\antigravity\brain\e395c0d7-38c4-4474-978e-3ec103b46a82\.user_uploaded\media_1793728744988_eb093259.har"
out_path = r"C:\Users\kevin.delmont\.gemini\antigravity\brain\e395c0d7-38c4-4474-978e-3ec103b46a82\scratch\har_summary.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with open(har_path, "r", encoding="utf-8", errors="ignore") as f:
    data = json.load(f)

entries = data.get("log", {}).get("entries", [])
summary = []

for e in entries:
    req = e.get("request", {})
    resp = e.get("response", {})
    url = req.get("url", "")
    method = req.get("method", "")
    status = resp.get("status")

    if "eaudugrandlyon.com" not in url:
        continue

    # Filtrer les assets statiques
    if any(ext in url for ext in [".js", ".css", ".png", ".jpg", ".woff", ".svg", ".ico"]):
        continue

    content = resp.get("content", {})
    text = content.get("text", "")
    mime = content.get("mimeType", "")

    headers_req = {h["name"]: h["value"] for h in req.get("headers", [])}
    auth_header = headers_req.get("Authorization") or headers_req.get("authorization")

    # Extraire aperçu du JSON
    resp_sample = None
    if "json" in mime and text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                resp_sample = {k: type(v).__name__ for k, v in parsed.items()}
                # Spécifique si "postes" ou similaire
                if "postes" in parsed:
                    resp_sample["postes_detail"] = parsed["postes"][:1]
            elif isinstance(parsed, list):
                resp_sample = f"list of {len(parsed)} items"
        except Exception as err:
            resp_sample = f"erreur parse: {err}"

    summary.append({
        "method": method,
        "url": url,
        "status": status,
        "has_auth": bool(auth_header),
        "auth_prefix": auth_header[:20] if auth_header else None,
        "mime": mime,
        "resp_sample": resp_sample,
    })

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Extraction terminée : {len(summary)} requêtes analysées. Fichier écrit dans {out_path}")


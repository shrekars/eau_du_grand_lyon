#!/usr/bin/env python3
"""
Outil d'analyse de traces HAR (HTTP Archive) pour Eau du Grand Lyon.
Permet d'extraire automatiquement tous les appels REST, paramètres et payloads.

Usage:
    python tools/har_parser.py traces/ma_capture.har
"""

import json
import os
import sys
from urllib.parse import urlparse, parse_qs


def analyze_har(har_path: str):
    if not os.path.isfile(har_path):
        print(f"Erreur : fichier '{har_path}' introuvable.")
        sys.exit(1)

    print(f"Chargement de {har_path}...")
    with open(har_path, "r", encoding="utf-8", errors="ignore") as f:
        har_data = json.load(f)

    entries = har_data.get("log", {}).get("entries", [])
    print(f"Nombre total de requêtes dans le fichier HAR : {len(entries)}\n")

    endpoints_found = []

    for entry in entries:
        req = entry.get("request", {})
        resp = entry.get("response", {})

        url = req.get("method", "") + " " + req.get("url", "")
        parsed_url = urlparse(req.get("url", ""))

        # Filtrer uniquement le domaine de l'agence Eau du Grand Lyon
        if "eaudugrandlyon.com" not in parsed_url.netloc:
            continue

        status = resp.get("status")
        mime_type = resp.get("content", {}).get("mimeType", "")
        content_text = resp.get("content", {}).get("text", "")

        entry_info = {
            "method": req.get("method"),
            "path": parsed_url.path,
            "query": parse_qs(parsed_url.query),
            "status": status,
            "mime_type": mime_type,
            "url": req.get("url"),
        }

        # Détection des payloads JSON utiles
        if "application/json" in mime_type and content_text:
            try:
                parsed_json = json.loads(content_text)
                if isinstance(parsed_json, dict):
                    entry_info["json_keys"] = list(parsed_json.keys())
                elif isinstance(parsed_json, list):
                    entry_info["json_keys"] = f"list[{len(parsed_json)} items]"
            except Exception:
                entry_info["json_keys"] = "erreur decodage"

        endpoints_found.append(entry_info)

    print("=" * 70)
    print("ENDPOINTS DÉTECTÉS SUR eaudugrandlyon.com :")
    print("=" * 70)

    seen = set()
    for ep in endpoints_found:
        sig = f"{ep['method']} {ep['path']}"
        if sig in seen:
            continue
        seen.add(sig)

        print(f"\n[{ep['status']}] {sig}")
        if ep["query"]:
            print(f"  Paramètres : {ep['query']}")
        if "json_keys" in ep:
            print(f"  Structure JSON réponse : {ep['json_keys']}")

    print("\n" + "=" * 70)
    print(f"Total endpoints uniques découverts : {len(seen)}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Chercher s'il y a un fichier .har dans le dossier traces/
        traces_dir = os.path.join(os.path.dirname(__file__), "..", "traces")
        har_files = [
            os.path.join(traces_dir, f)
            for f in os.listdir(traces_dir)
            if f.endswith(".har")
        ] if os.path.isdir(traces_dir) else []

        if har_files:
            analyze_har(har_files[0])
        else:
            print("Usage: python tools/har_parser.py <chemin_vers_fichier.har>")
            print("Astuce : déposez votre fichier .har dans le dossier 'traces/'")
    else:
        analyze_har(sys.argv[1])


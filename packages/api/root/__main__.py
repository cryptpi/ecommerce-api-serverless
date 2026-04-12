# packages/api/root/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Page d'accueil de l'API
# URL     : GET /api/root
#
# Retourne des informations générales sur l'API.
# Cette fonction ne se connecte PAS à MongoDB.
# ─────────────────────────────────────────────────────────────────────────────


def main(event):
    return {
        "body": {
            "message":  "E-Commerce Products API (Serverless) is running",
            "docs":     "Use /api/products-list, /api/products-create, etc.",
            "version":  "2.0.0",
            "runtime":  "DigitalOcean Functions"
        }
    }

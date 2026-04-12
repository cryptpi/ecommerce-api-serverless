# packages/api/products-list/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Lister tous les produits (avec filtres optionnels)
# URL     : GET /api/products-list
#           GET /api/products-list?category=Electronics
#           GET /api/products-list?in_stock=true
#           GET /api/products-list?category=Sports&in_stock=true
# ─────────────────────────────────────────────────────────────────────────────

import os
from pymongo import MongoClient

# ── Connexion MongoDB ────────────────────────────────────────────────────────
# MONGODB_URL est injectée par DigitalOcean via project.yml → environment.
# La connexion est créée au niveau du module (réutilisée en warm start).
# ─────────────────────────────────────────────────────────────────────────────
client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    """Convertit un document MongoDB en dict JSON-safe (ObjectId → str)."""
    return {
        "id":          str(product["_id"]),
        "name":        product.get("name", ""),
        "description": product.get("description", ""),
        "price":       product.get("price", 0.0),
        "category":    product.get("category", ""),
        "brand":       product.get("brand", "Unknown"),
        "sku":         product.get("sku", ""),
        "in_stock":    product.get("in_stock", True),
        "stock_count": product.get("stock_count", 0),
        "rating":      product.get("rating", 0.0),
        "tags":        product.get("tags", []),
    }


def main(event):
    query = {}

    # ── Filtres optionnels (query parameters) ────────────────────────────
    category = event.get("category")
    in_stock = event.get("in_stock")

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if in_stock is not None:
        if isinstance(in_stock, str):
            in_stock = in_stock.lower() == "true"
        query["in_stock"] = in_stock

    products = [product_helper(p) for p in products_collection.find(query)]

    return {
        "body": {
            "count":    len(products),
            "products": products
        }
    }

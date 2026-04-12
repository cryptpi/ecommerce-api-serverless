# packages/api/products-search/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Rechercher des produits par mot-clé
# URL     : GET /api/products-search?q=headphones
#
# Recherche dans le nom ET la description (case-insensitive).
# Le paramètre ?q= est obligatoire.
# ─────────────────────────────────────────────────────────────────────────────

import os
from pymongo import MongoClient

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    """Convertit un document MongoDB en dict JSON-safe."""
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
    q = event.get("q")

    if not q:
        return {
            "statusCode": 400,
            "body": {"error": "Missing required parameter: q"}
        }

    # $regex avec $options: "i" pour case-insensitive
    pattern = {"$regex": q, "$options": "i"}

    # Chercher dans le nom OU la description
    results = [product_helper(p) for p in products_collection.find({
        "$or": [
            {"name":        pattern},
            {"description": pattern}
        ]
    })]

    return {
        "body": {
            "query":    q,
            "count":    len(results),
            "products": results
        }
    }

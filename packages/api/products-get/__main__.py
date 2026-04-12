# packages/api/products-get/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Obtenir un produit par son ID MongoDB
# URL     : GET /api/products-get?id=507f1f77bcf86cd799439011
#
# Retourne 400 si l'ID est invalide, 404 si le produit n'existe pas.
# ─────────────────────────────────────────────────────────────────────────────

import os
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

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
    product_id = event.get("id")

    # ── Validation : paramètre requis ─────────────────────────────────────
    if not product_id:
        return {
            "statusCode": 400,
            "body": {"error": "Missing required parameter: id"}
        }

    # ── Validation : format ObjectId ──────────────────────────────────────
    try:
        oid = ObjectId(product_id)
    except (InvalidId, Exception):
        return {
            "statusCode": 400,
            "body": {
                "error": f"'{product_id}' is not a valid product ID. "
                         f"IDs look like: 507f1f77bcf86cd799439011"
            }
        }

    # ── Requête MongoDB ───────────────────────────────────────────────────
    product = products_collection.find_one({"_id": oid})

    if product is None:
        return {
            "statusCode": 404,
            "body": {"error": f"Product {product_id} not found"}
        }

    return {"body": product_helper(product)}

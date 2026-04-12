# packages/api/products-create/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Créer un nouveau produit
# URL     : POST /api/products-create
# Body    : JSON avec name, description, price, category (obligatoires)
#           + brand, sku, in_stock, stock_count, rating, tags (optionnels)
#
# Retourne 201 avec le produit créé, ou 400 si des champs manquent.
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
    # ── Validation des champs obligatoires ────────────────────────────────
    required_fields = ["name", "description", "price", "category"]
    missing = [f for f in required_fields if not event.get(f)]

    if missing:
        return {
            "statusCode": 400,
            "body": {"error": f"Missing required fields: {', '.join(missing)}"}
        }

    # ── Validation du prix ────────────────────────────────────────────────
    price = event.get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        return {
            "statusCode": 400,
            "body": {"error": "Price must be a number greater than 0"}
        }

    # ── Construire le document ────────────────────────────────────────────
    product_data = {
        "name":        event.get("name"),
        "description": event.get("description"),
        "price":       float(price),
        "category":    event.get("category"),
        "brand":       event.get("brand", "Unknown"),
        "sku":         event.get("sku", ""),
        "in_stock":    event.get("in_stock", True),
        "stock_count": event.get("stock_count", 0),
        "rating":      event.get("rating", 0.0),
        "tags":        event.get("tags", []),
    }

    # ── Insérer dans MongoDB ──────────────────────────────────────────────
    result  = products_collection.insert_one(product_data)
    created = products_collection.find_one({"_id": result.inserted_id})

    return {
        "statusCode": 201,
        "body": product_helper(created)
    }

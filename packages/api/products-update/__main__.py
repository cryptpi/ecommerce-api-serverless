# packages/api/products-update/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Modifier un produit existant (mise à jour partielle)
# URL     : PUT /api/products-update?id=507f1f77bcf86cd799439011
# Body    : JSON avec les champs à modifier (seuls les champs envoyés changent)
#
# Utilise MongoDB $set — les champs non envoyés restent inchangés.
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

    # ── Extraire les champs à modifier ────────────────────────────────────
    # Ignorer les clés internes de DO Functions et le paramètre "id"
    ignored_keys = {
        "id",
        "__ow_method", "__ow_path", "__ow_headers", "__ow_body",
        "__ow_query", "http"
    }
    update_data = {
        k: v for k, v in event.items()
        if k not in ignored_keys and v is not None
    }

    if not update_data:
        return {
            "statusCode": 400,
            "body": {
                "error": "No fields to update. "
                         "Send at least one field in the request body."
            }
        }

    # ── Mise à jour dans MongoDB ──────────────────────────────────────────
    result = products_collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        return {
            "statusCode": 404,
            "body": {"error": f"Product {product_id} not found"}
        }

    updated = products_collection.find_one({"_id": oid})
    return {"body": product_helper(updated)}

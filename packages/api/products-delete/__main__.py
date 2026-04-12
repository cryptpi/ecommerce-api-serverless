# packages/api/products-delete/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Supprimer un produit par son ID MongoDB
# URL     : DELETE /api/products-delete?id=507f1f77bcf86cd799439011
#
# Retourne le nom du produit supprimé, 404 s'il n'existe pas.
# ─────────────────────────────────────────────────────────────────────────────

import os
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


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

    # ── Vérifier que le produit existe ────────────────────────────────────
    product = products_collection.find_one({"_id": oid})

    if product is None:
        return {
            "statusCode": 404,
            "body": {"error": f"Product {product_id} not found"}
        }

    # ── Supprimer ─────────────────────────────────────────────────────────
    products_collection.delete_one({"_id": oid})

    return {
        "body": {
            "message": f"Product '{product['name']}' deleted successfully."
        }
    }

# packages/api/webhook-stock-alert/__main__.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonction : Webhook pour les Atlas Triggers (architecture événementielle)
# URL     : POST /api/webhook-stock-alert
#
# Reçoit une notification de MongoDB Atlas quand le stock d'un produit
# atteint 0. Atlas envoie le document complet dans le champ "fullDocument".
#
# En production, remplacez le print() par :
#   - Un email via Resend / SendGrid
#   - Un message Slack / Discord
#   - Une notification push
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone


def main(event):
    # Atlas Trigger envoie le document modifié dans "fullDocument"
    full_document = event.get("fullDocument", {})
    product_name  = full_document.get("name", "Unknown")
    stock_count   = full_document.get("stock_count", "N/A")

    timestamp = datetime.now(timezone.utc).isoformat()

    # Log l'alerte dans la console DO Functions
    print(f"🚨 [{timestamp}] STOCK ALERT: '{product_name}' — stock = {stock_count}")

    return {
        "body": {
            "received":    True,
            "timestamp":   timestamp,
            "product":     product_name,
            "stock_count": stock_count,
            "action":      "Alert logged to DO Functions console"
        }
    }

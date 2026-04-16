# TP2 — Fonctions Serverless & Architecture Événementielle

> **Prérequis :** Avoir terminé le TP1 (API E-Commerce avec MongoDB Atlas, Droplet & App Platform)
>
> **Durée :** 3 à 4 heures
>
> **Objectif :** Redéployer l'API E-Commerce en tant que fonctions serverless sur **DigitalOcean Functions** via `doctl`, comprendre les cold starts, le modèle pay-per-use, et implémenter un pipeline événementiel avec les Atlas Triggers.

---

## 🎯 Ce que vous allez apprendre

| Concept cloud | Ce que vous ferez |
|---------------|-------------------|
| **FaaS** (Function as a Service) | Déployer une API comme 9 fonctions serverless via `doctl` |
| **Auto-scaling to zero** | Observer comment DO Functions éteint vos fonctions quand personne ne les utilise |
| **Cold starts** | Mesurer le délai de démarrage à froid vs. à chaud |
| **Architecture événementielle** | Créer un Atlas Trigger qui appelle un webhook quand le stock atteint 0 |
| **Pay-per-use** | Comparer les coûts : PaaS mensuel vs. serverless à la GiB-seconde |

---

## 📁 Structure du projet final

```
ecommerce-api-serverless/
├── project.yml                          ← Configuration DO Functions
├── .env.example                         ← Template variables d'environnement
├── .gitignore
├── requirements.txt
└── packages/
    └── api/
        ├── root/                        → GET / (info API)
        │   └── __main__.py
        ├── products-list/               → GET (lister / filtrer)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh                 ← Script d'installation des dépendances
        ├── products-search/             → GET (recherche texte)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        ├── products-categories/         → GET (catégories distinctes)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        ├── products-get/                → GET (par ID)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        ├── products-create/             → POST (créer)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        ├── products-update/             → PUT (modifier)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        ├── products-delete/             → DELETE (supprimer)
        │   ├── __main__.py
        │   ├── requirements.txt
        │   └── build.sh
        └── webhook-stock-alert/         → POST (webhook Atlas)
            ├── __main__.py
            ├── requirements.txt
            └── build.sh
```

---

## 🗺️ Parcours

| Partie | Étapes | Thème |
|--------|--------|-------|
| **A** — Comprendre | 1 | Concepts serverless & FaaS |
| **B** — Configurer | 2 – 3 | Setup DO Functions & structure du projet |
| **C** — Construire | 4 – 5 | Connexion MongoDB & écriture des fonctions |
| **D** — Déployer | 6 – 8 | Déploiement `doctl`, tests, cold starts |
| **E** — Événements | 9 | Atlas Triggers & webhooks |
| **F** — Analyser | 10 | Coûts, limites, bilan |

---
---

# PARTIE A — COMPRENDRE

---

# Étape 1 — Comprendre le Serverless (FaaS)

> 📌 **Concept du cours :** Function as a Service, pay-per-GiB-second, auto-scaling

---

## 1.1 — Rappel : Comment fonctionne votre API du TP1 ?

Dans le TP1, votre API E-Commerce tourne sur un **serveur permanent** :

```
┌─────────────────────────────────────────────┐
│               Serveur (24h/24)              │
│                                             │
│   uvicorn démarre → écoute le port 8000     │
│   Attend les requêtes indéfiniment...       │
│   Requête arrive → Traitement → Réponse    │
│   Continue d'attendre...                    │
│                                             │
│   💰 Vous payez même quand personne         │
│      n'utilise l'API (la nuit, le weekend)  │
└─────────────────────────────────────────────┘
```

**PaaS (App Platform) :** La plateforme gère le serveur, mais il tourne 24h/24 → coût fixe mensuel (~5$/mois).

**IaaS (Droplet) :** Vous gérez le serveur vous-même, il tourne 24h/24 → coût fixe mensuel (~6$/mois).

---

## 1.2 — Le modèle Serverless : pas de serveur permanent

En **serverless**, il n'y a pas de processus qui tourne en permanence :

```
Requête HTTP arrive
       ↓
DigitalOcean démarre votre fonction (cold start ~500ms)
       ↓
Votre code s'exécute (traitement ~50ms)
       ↓
Réponse envoyée au client
       ↓
La fonction s'éteint (ou reste "warm" quelques minutes)
       ↓
💰 Vous payez UNIQUEMENT pour ces ~550ms d'exécution
```

> 🔑 **"Serverless" ne veut pas dire qu'il n'y a pas de serveur.** Il y a toujours un serveur quelque part — mais vous ne le voyez pas, vous ne le gérez pas, et vous ne payez que quand votre code s'exécute.

---

## 1.3 — Les 5 caractéristiques du Serverless

| Caractéristique | Description |
|-----------------|-------------|
| **🚀 Auto-scaling** | 0 requête = 0 instance. 1000 requêtes = 1000 instances parallèles. Automatique. |
| **💰 Pay-per-use** | Vous payez par temps d'exécution (GiB-secondes). 90 000 GiB-s/mois **gratuits** sur DigitalOcean. |
| **⏱️ Cold start** | La première requête après une période d'inactivité prend plus de temps (~500ms–2s). |
| **⏳ Durée limitée** | Chaque exécution a un timeout (DO Functions : 60s par défaut). Pas de tâches longues. |
| **🔒 Stateless** | La fonction ne conserve rien en mémoire entre deux requêtes. Chaque invocation est indépendante. |

---

## 1.4 — Où se situe le Serverless dans la pyramide cloud ?

```
┌─────────────────────────┐
│         SaaS            │  ← Gmail, Office 365
│   (tout est géré)       │     Vous utilisez juste le logiciel
├─────────────────────────┤
│    FaaS / Serverless    │  ← DO Functions, AWS Lambda            ⬅️ NOUS SOMMES ICI
│  (vous écrivez le code, │     Pas de serveur à gérer
│   on gère tout le reste)│
├─────────────────────────┤
│         PaaS            │  ← DigitalOcean App Platform (TP1)
│  (vous déployez l'app,  │     La plateforme gère le serveur
│   on gère l'infra)      │
├─────────────────────────┤
│         IaaS            │  ← DigitalOcean Droplet (TP1)
│  (vous gérez le serveur │     Vous installez tout vous-même
│   et l'app)             │
├─────────────────────────┤
│      On-Premises        │  ← Votre propre data center
│  (vous gérez TOUT)      │     Serveurs physiques, électricité, refroidissement
└─────────────────────────┘
```

> 📌 **FaaS** (Function as a Service) est un niveau d'abstraction **au-dessus** du PaaS. Vous ne déployez même plus une "application" — vous déployez des **fonctions individuelles**.

---

## 1.5 — Comparaison : PaaS vs IaaS vs Serverless

| Aspect | IaaS (Droplet) | PaaS (App Platform) | Serverless (DO Functions) |
|--------|:-:|:-:|:-:|
| Installer Python | ✋ Vous | ✅ Plateforme | ✅ Plateforme |
| Gérer le serveur | ✋ Vous | ✅ Plateforme | ✅ Plateforme |
| Configurer le réseau | ✋ Vous (ufw) | ✅ Plateforme | ✅ Plateforme |
| Démarrage auto des processus | ✋ Vous (systemd) | ✅ Plateforme | ✅ Plateforme |
| Scaling | ✋ Vous | Curseur dans l'UI | ✅ Automatique |
| Coût au repos | 💸 Fixe (~6$/mois) | 💸 Fixe (~5$/mois) | 🆓 0$ |
| Cold start | ❌ Non | ❌ Non | ⚠️ Oui (~500ms) |
| Tâches longues (>60s) | ✅ Oui | ✅ Oui | ❌ Non |
| WebSockets | ✅ Oui | ✅ Oui | ❌ Non |

---

## 1.6 — Quand utiliser le Serverless ?

✅ **Bon pour :**
- APIs avec trafic irrégulier (beaucoup de requêtes le jour, rien la nuit)
- Webhooks et événements ponctuels
- Prototypes et MVPs (coût quasi nul au départ)
- Fonctions utilitaires (redimensionner une image, envoyer un email)

❌ **Mauvais pour :**
- Applications temps réel (WebSockets, jeux, chat)
- Traitements longs (vidéo, machine learning, batch processing)
- Applications qui nécessitent un état en mémoire (cache local)

---
---

# PARTIE B — CONFIGURER

---

# Étape 2 — Configurer DigitalOcean Functions

> 📌 **Concept du cours :** Plateforme FaaS, CLI `doctl`, namespaces

---

## 2.1 — Qu'est-ce que DigitalOcean Functions ?

**DigitalOcean Functions** est le service serverless (FaaS) de DigitalOcean. Il permet de déployer des fonctions individuelles qui s'exécutent à la demande.

Pourquoi DO Functions pour ce TP ?
- ✅ **Même plateforme que le TP1** — vous restez dans l'écosystème DigitalOcean
- ✅ Tier gratuit généreux (90 000 GiB-secondes/mois)
- ✅ Support natif de Python
- ✅ Déploiement via la CLI `doctl` (en une commande)
- ✅ HTTPS automatique
- ✅ **Pas de framework requis** — du Python pur, pas besoin de FastAPI

> 🔑 **Différence avec d'autres FaaS (AWS Lambda, Vercel) :** DO Functions utilise un modèle très simple. Votre fonction reçoit un `event` (dictionnaire) et retourne un `dict`. Pas de serveur HTTP, pas de framework — juste une fonction Python.

---

## 2.2 — Installer `doctl` (si pas encore fait)

Si vous avez déjà installé `doctl` dans le TP1, passez à la section 2.3.

```bash
# Arch Linux — depuis le dépôt community
sudo pacman -S doctl

# Ou via AUR (si pas dans community)
yay -S doctl-bin

# Vérifier l'installation
doctl version
```

---

## 2.3 — Authentifier `doctl`

Si vous avez déjà fait `doctl auth init` dans le TP1, passez à la section 2.4.

```bash
# Authentifier avec votre token DigitalOcean
doctl auth init
```

> 💡 **Token API :** Récupérez votre token dans le dashboard DigitalOcean → **API** → **Personal Access Tokens**.

---

## 2.4 — Installer le support serverless

`doctl` a besoin d'un composant supplémentaire pour gérer les fonctions :

```bash
# Installer le support serverless
doctl serverless install
```

✅ **Résultat attendu :**

```
Downloading serverless support... done
Installing serverless support... done
```

---

## 2.5 — Créer un namespace

Un **namespace** est un espace isolé qui regroupe vos fonctions dans le cloud. C'est comme un "workspace" :

```bash
# Créer un namespace dans la région Frankfurt (la plus proche)
doctl serverless namespaces create --label ecommerce-serverless --region fra1
```

> 💡 **Régions disponibles :** `fra1` (Frankfurt), `lon1` (London), `nyc1` (New York), `blr1` (Bangalore), `sfo1` (San Francisco), `sgp1` (Singapore), `syd1` (Sydney).

---

## 2.6 — Se connecter au namespace
```bash
octl serverless key create --name ecommerce-dev --expiration 30d

```
Notice: The secret key for "ecommerce-dev" is shown below.
Please save this secret. You will not be able to see it again.

ID                                         Name             Secret                                                              Created At                 Expires At
dof_v1_845fd417-09fb-4d70-8359-d5b3717f    ecommerce-dev    lW9SDyMQnZ4FN6BxIkWYKHsrYJ738B6din3H3VvO9KOBOmiVqurTWMiiQcNsOEyF    2026-04-14 14:10:42 UTC    2026-05-14 14:10:42 UTC


```bash
# Connecter doctl à votre namespace
doctl serverless connect #this is a depricated command

# Correct command
doctl serverless connect <namespace> --access-key <dof_v1_<access_key_id>:<secret>>

# Example
doctl serverless connect ecommerce-serverless --access-key dof_v1_845fd417-09fb-4d70-8359-d5b3717f:lW9SDyMQnZ4FN6BxIkWYKHsrYJ738B6din3H3VvO9KOBOmiVqurTWMiiQcNsOEyF

```

✅ **Résultat attendu :**

```
Connected to functions namespace 'ecommerce-serverless' on API host 'https://faas-fra1-XXXXX.doserverless.co'
```

> 🔑 **Le API host** est l'URL de base pour toutes vos fonctions. Notez-la — vous en aurez besoin plus tard.

https://faas-fra1-afec6ce7.doserverless.co

---

## 2.7 — Créer le dépôt GitHub

1. Allez sur [github.com/new](https://github.com/new)
2. Nom du repository : `ecommerce-api-serverless`
3. Visibilité : **Public**
4. **Ne cochez PAS** "Add a README"
5. Cliquez sur **Create repository**

---

## 2.8 — Initialiser le projet localement

```bash
# Créer le dossier du projet
mkdir ecommerce-api-serverless
cd ecommerce-api-serverless

# Initialiser Git
git init

# Lier au repo GitHub (remplacez VOTRE_USERNAME)
git remote add origin https://github.com/VOTRE_USERNAME/ecommerce-api-serverless.git
```

---

## 2.9 — Vérification

```bash
# Vérifier que tout est en place
doctl serverless status
```

✅ **Résultat attendu :** Le statut affiche votre namespace connecté et prêt.

---
---

# Étape 3 — Structure du Projet

> 📌 **Concept du cours :** Architecture multi-fonctions, `project.yml`, isolation FaaS

---

## 3.1 — Comment DO Functions organise vos fonctions

DigitalOcean Functions utilise une convention de répertoire stricte :

```
project.yml                    ← Manifeste du projet (obligatoire)
packages/
  └── <nom-du-package>/
      └── <nom-de-la-fonction>/
          ├── __main__.py      ← Point d'entrée (obligatoire)
          ├── requirements.txt ← Dépendances Python (optionnel)
          └── build.sh         ← Script d'installation des dépendances (obligatoire si requirements.txt)
```

| Dossier | URL de la fonction |
|---------|--------------------|
| `packages/api/root/` | `https://faas-fra1-XXXXX.doserverless.co/api/v1/web/.../api/root` |
| `packages/api/products-list/` | `.../api/products-list` |
| `packages/api/products-create/` | `.../api/products-create` |

> 🔑 **Différence majeure avec le TP1 :** Dans le TP1, vous aviez **un seul fichier** `main.py` avec toutes les routes. En serverless FaaS, **chaque endpoint est une fonction indépendante** dans son propre dossier. C'est le vrai pattern FaaS — chaque fonction est isolée, déployée et scalée indépendamment.

---

## 3.2 — Créer la structure de fichiers

```bash
# Créer les dossiers pour chaque fonction
mkdir -p packages/api/{root,products-list,products-search,products-categories,products-get,products-create,products-update,products-delete,webhook-stock-alert}

# Créer les fichiers de configuration
touch project.yml
touch .gitignore
touch .env
```

---

## 3.3 — Fichier `project.yml`

Ce fichier est le **manifeste** de votre projet. Il décrit toutes les fonctions, leur runtime, et les variables d'environnement.

Ouvrez `project.yml` et ajoutez :

```yaml
packages:
  - name: api
    # Variables d'environnement partagées par toutes les fonctions
    environment:
      MONGODB_URL: "${MONGODB_URL}"

    actions:
      - name: root
        runtime: python:default
        web: true

      - name: products-list
        runtime: python:default
        web: true

      - name: products-search
        runtime: python:default
        web: true

      - name: products-categories
        runtime: python:default
        web: true

      - name: products-get
        runtime: python:default
        web: true

      - name: products-create
        runtime: python:default
        web: true

      - name: products-update
        runtime: python:default
        web: true

      - name: products-delete
        runtime: python:default
        web: true

      - name: webhook-stock-alert
        runtime: python:default
        web: true
```

> 🔑 **Explications :**
> - **`packages`** : Un package regroupe des fonctions liées. Ici, tout est dans le package `api`.
> - **`environment`** : Variables d'environnement partagées. `${MONGODB_URL}` est lue depuis le fichier `.env` au moment du déploiement.
> - **`actions`** : Liste des fonctions. Chaque fonction a un nom, un runtime et `web: true` pour être accessible via HTTP.
> - **`web: true`** : Rend la fonction accessible via une URL HTTPS publique.

---

## 3.4 — Fichier `requirements.txt` (par fonction)

Chaque fonction a son propre `requirements.txt`. Pour les fonctions qui accèdent à MongoDB :

```bash
# Créer les requirements pour chaque fonction qui utilise MongoDB
for dir in products-list products-search products-categories products-get products-create products-update products-delete webhook-stock-alert; do
  printf "pymongo==4.7.3\ndnspython>=2.1.0\npython-dotenv==1.0.1\n" > packages/api/$dir/requirements.txt
done

# La fonction root n'a pas besoin de pymongo
echo "python-dotenv==1.0.1" > packages/api/root/requirements.txt
```

> ⚠️ **Pourquoi `dnspython` ?** Les URIs `mongodb+srv://` (utilisées par Atlas) nécessitent le module `dnspython` pour résoudre les enregistrements SRV DNS. Sans lui, pymongo ne peut pas se connecter à Atlas.

---

## 3.5 — Fichier `build.sh` (par fonction)

> ⚠️ **Important :** DigitalOcean Functions **n'installe PAS automatiquement** les dépendances depuis `requirements.txt`. Vous devez créer un script `build.sh` dans chaque dossier de fonction.

```bash
# Créer le build.sh pour chaque fonction qui a des dépendances
for dir in products-list products-search products-categories products-get products-create products-update products-delete webhook-stock-alert; do
  cat > packages/api/$dir/build.sh << 'SCRIPT'
#!/bin/bash
set -e
virtualenv --without-pip virtualenv
pip install -r requirements.txt --target virtualenv/lib/python3.9/site-packages
SCRIPT
  chmod +x packages/api/$dir/build.sh
done
```

> 🔑 **Explications :**
> - **`virtualenv`** : Crée un environnement virtuel. Le dossier **doit** s'appeler `virtualenv` — c'est une convention imposée par DO Functions.
> - **`pip install --target`** : Installe les packages dans le dossier `virtualenv/` qui sera inclus dans le déploiement.
> - **`--remote-build`** : Lors du déploiement, on utilisera `doctl serverless deploy . --remote-build` pour que ce script s'exécute sur les serveurs de DigitalOcean (qui ont `virtualenv` préinstallé).

> ⚠️ **Remarquez les différences avec le TP1 :**
>
> | TP1 (serveur classique) | TP2 (serverless) | Pourquoi ? |
> |-------------------------|------------------|------------|
> | `fastapi` | ❌ Absent | DO Functions fournit le serveur HTTP — pas besoin de framework |
> | `uvicorn` | ❌ Absent | Pas de serveur à démarrer |
> | `gunicorn` | ❌ Absent | Pas de process manager nécessaire |
> | `pydantic` | ❌ Absent | On valide manuellement (code plus simple) |
> | `motor` (async) | `pymongo` (sync) | Les fonctions serverless sont éphémères — un driver synchrone est plus adapté |
> | `pip install -r` (direct) | `build.sh` + `virtualenv` | DO Functions n'installe pas les dépendances automatiquement |

---

## 3.6 — Fichier `.gitignore`

```gitignore
__pycache__/
*.py[cod]
venv/
.venv/
virtualenv/
.env
.env.local
.deployed/
.DS_Store
```

---

## 3.7 — Fichier `.env` (local uniquement)

Ce fichier contient votre chaîne de connexion MongoDB Atlas — **la même** que dans le TP1 :

```env
MONGODB_URL=mongodb+srv://api_user:VOTRE_MOT_DE_PASSE@ecommerce-workshop.xxxxx.mongodb.net/ecommerce?retryWrites=true&w=majority
```
Exemple:
MONGODB_URL=mongodb+srv://api_user:12wail99@ecommerce-workshop.jm01dch.mongodb.net/?appName=ecommerce-workshop



> ⚠️ **Ce fichier est dans `.gitignore` — il ne sera JAMAIS envoyé sur GitHub.** Lors du déploiement, `doctl` lit ce fichier et injecte les variables dans le cloud.

---

## 3.8 — Vérification

Votre dossier devrait maintenant ressembler à ceci :

```
ecommerce-api-serverless/
├── project.yml                 ✅ Manifeste DO Functions
├── .gitignore                  ✅ Configuré
├── .env                        ✅ Configuré (local uniquement)
└── packages/
    └── api/
        ├── root/               ← (vide pour l'instant)
        ├── products-list/      ← (vide pour l'instant)
        ├── products-search/    ← (vide pour l'instant)
        ├── products-categories/
        ├── products-get/
        ├── products-create/
        ├── products-update/
        ├── products-delete/
        └── webhook-stock-alert/
```

✅ **Résultat attendu :** La structure du projet est prête. Le manifeste `project.yml` décrit 9 fonctions.

---
---

# PARTIE C — CONSTRUIRE

---

# Étape 4 — Base de données & Connexion MongoDB

> 📌 **Concept du cours :** Réutilisation DBaaS, code inline vs modules partagés, Synchrone en Serverless

---

## 4.1 — Rappel : votre base de données existe déjà

Dans le TP1, vous avez créé un cluster MongoDB Atlas avec une base `ecommerce` et une collection `products` contenant 10 documents.

**Bonne nouvelle :** On réutilise exactement la même base de données ! 🎉

```
     TP1 (Droplet)  ──────┐
                           ├──→  MongoDB Atlas (cloud)  ←── Même base de données !
     TP1 (App Platform) ──┤
                           │
     TP2 (DO Functions) ───┘  ← Nouvelle connexion, mêmes données
```

---

## 4.2 — Pourquoi `pymongo` au lieu de `motor` ?

| Aspect | `motor` (TP1) | `pymongo` (TP2) |
|--------|---------------|-----------------|
| Mode | Asynchrone (`async`/`await`) | Synchrone |
| Pool de connexions | Pool persistant pour serveur 24h/24 | Connexion simple pour fonctions éphémères |
| Cold start | Le pool met du temps à s'établir | Connexion directe, plus rapide |
| Adapté pour | Serveurs permanents (uvicorn) | Fonctions serverless (DO Functions, Lambda) |

---

## 4.3 — La connexion MongoDB dans chaque fonction

> 🔑 **Différence architecturale majeure avec le TP1 :**
>
> Dans le TP1, vous aviez un fichier `database.py` séparé, importé par `main.py`.
> En DO Functions, **chaque fonction est un package isolé**. La connexion MongoDB est **inline** — directement dans chaque `__main__.py`.

Voici le code de connexion (au début de chaque fonction) :

```python
import os
from pymongo import MongoClient

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]
```

> 📝 **Comparez avec le TP1 :**
> - TP1 : `from motor.motor_asyncio import AsyncIOMotorClient` → `AsyncIOMotorClient(MONGODB_URL)`
> - TP2 : `from pymongo import MongoClient` → `MongoClient(os.environ["MONGODB_URL"])`
>
> Deux changements : (1) synchrone au lieu d'asynchrone, (2) `os.environ` au lieu de `dotenv` (DO injecte les variables automatiquement).

---

## 4.4 — Le helper `product_helper`

La même fonction de conversion MongoDB → JSON, inline dans chaque fichier :

```python
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
```

> 💡 **Pourquoi dupliquer ?** En FaaS pur, chaque fonction est un **microservice indépendant**. La duplication est un compromis accepté pour l'isolation.

---

## 4.5 — Plus de Pydantic — validation manuelle

```python
# TP1 (avec Pydantic — validation automatique)
@app.post("/products")
async def create_product(product: Product):
    ...

# TP2 (sans framework — validation manuelle)
def main(event):
    required_fields = ["name", "description", "price", "category"]
    missing = [f for f in required_fields if not event.get(f)]
    if missing:
        return {"statusCode": 400, "body": {"error": f"Missing: {', '.join(missing)}"}}
    ...
```

> 🔑 **C'est le vrai visage du FaaS.** Pas de framework, pas de magie — juste du Python pur.

---
---

# Étape 5 — Endpoints API (les fonctions serverless)

> 📌 **Concept du cours :** Le pattern `main(event) → dict`, fonctions isolées, validation manuelle

---

## 5.1 — Comment fonctionne une fonction DO Functions

```python
def main(event):
    # event = dictionnaire contenant les query params et le body
    return {
        "statusCode": 200,    # Optionnel, 200 par défaut
        "body": {"message": "Hello World"}
    }
```

> 🔑 **C'est tout.** Pas de `@app.get()`, pas de décorateurs, pas de framework. Une fonction Python qui reçoit un dictionnaire et en retourne un.

---

## 5.2 — Les 4 différences avec le TP1

| # | TP1 (FastAPI + motor) | TP2 (DO Functions + pymongo) | Pourquoi ? |
|---|----------------------|------------------------------|------------|
| 1 | `@app.get("/products")` | `def main(event):` | Pas de framework — une fonction par endpoint |
| 2 | `async def list_products(...)` | `def main(event):` | pymongo est synchrone |
| 3 | `raise HTTPException(404)` | `return {"statusCode": 404, ...}` | On retourne le code HTTP directement |
| 4 | `product: Product` (Pydantic) | `event.get("name")` (dict) | Validation manuelle |

---

## 5.3 — Fonction 1 : `root` — Page d'accueil

Ouvrez `packages/api/root/__main__.py` :

```python
def main(event):
    return {
        "body": {
            "message":  "E-Commerce Products API (Serverless) is running",
            "docs":     "Use /api/products-list, /api/products-create, etc.",
            "version":  "2.0.0",
            "runtime":  "DigitalOcean Functions"
        }
    }
```

---

## 5.4 — Fonction 2 : `products-list` — Lister les produits

Ouvrez `packages/api/products-list/__main__.py` :

```python
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
    query = {}

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
```

---

## 5.5 — Fonction 3 : `products-search` — Rechercher

Ouvrez `packages/api/products-search/__main__.py` :

```python
import os
from pymongo import MongoClient

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    return {
        "id": str(product["_id"]), "name": product.get("name", ""),
        "description": product.get("description", ""), "price": product.get("price", 0.0),
        "category": product.get("category", ""), "brand": product.get("brand", "Unknown"),
        "sku": product.get("sku", ""), "in_stock": product.get("in_stock", True),
        "stock_count": product.get("stock_count", 0), "rating": product.get("rating", 0.0),
        "tags": product.get("tags", []),
    }


def main(event):
    q = event.get("q")

    if not q:
        return {"statusCode": 400, "body": {"error": "Missing required parameter: q"}}

    pattern = {"$regex": q, "$options": "i"}
    results = [product_helper(p) for p in products_collection.find({
        "$or": [{"name": pattern}, {"description": pattern}]
    })]

    return {"body": {"query": q, "count": len(results), "products": results}}
```

---

## 5.6 — Fonction 4 : `products-categories`

Ouvrez `packages/api/products-categories/__main__.py` :

```python
import os
from pymongo import MongoClient

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def main(event):
    categories = products_collection.distinct("category")
    return {"body": {"count": len(categories), "categories": sorted(categories)}}
```

---

## 5.7 — Fonction 5 : `products-get` — Par ID

Ouvrez `packages/api/products-get/__main__.py` :

```python
import os
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    return {
        "id": str(product["_id"]), "name": product.get("name", ""),
        "description": product.get("description", ""), "price": product.get("price", 0.0),
        "category": product.get("category", ""), "brand": product.get("brand", "Unknown"),
        "sku": product.get("sku", ""), "in_stock": product.get("in_stock", True),
        "stock_count": product.get("stock_count", 0), "rating": product.get("rating", 0.0),
        "tags": product.get("tags", []),
    }


def main(event):
    product_id = event.get("id")
    if not product_id:
        return {"statusCode": 400, "body": {"error": "Missing required parameter: id"}}

    try:
        oid = ObjectId(product_id)
    except (InvalidId, Exception):
        return {"statusCode": 400, "body": {"error": f"'{product_id}' is not a valid product ID."}}

    product = products_collection.find_one({"_id": oid})
    if product is None:
        return {"statusCode": 404, "body": {"error": f"Product {product_id} not found"}}

    return {"body": product_helper(product)}
```

---

## 5.8 — Fonction 6 : `products-create` — Créer

Ouvrez `packages/api/products-create/__main__.py` :

```python
import os
from pymongo import MongoClient

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    return {
        "id": str(product["_id"]), "name": product.get("name", ""),
        "description": product.get("description", ""), "price": product.get("price", 0.0),
        "category": product.get("category", ""), "brand": product.get("brand", "Unknown"),
        "sku": product.get("sku", ""), "in_stock": product.get("in_stock", True),
        "stock_count": product.get("stock_count", 0), "rating": product.get("rating", 0.0),
        "tags": product.get("tags", []),
    }


def main(event):
    # Validation
    required_fields = ["name", "description", "price", "category"]
    missing = [f for f in required_fields if not event.get(f)]
    if missing:
        return {"statusCode": 400, "body": {"error": f"Missing required fields: {', '.join(missing)}"}}

    price = event.get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        return {"statusCode": 400, "body": {"error": "Price must be a number greater than 0"}}

    product_data = {
        "name": event.get("name"), "description": event.get("description"),
        "price": float(price), "category": event.get("category"),
        "brand": event.get("brand", "Unknown"), "sku": event.get("sku", ""),
        "in_stock": event.get("in_stock", True), "stock_count": event.get("stock_count", 0),
        "rating": event.get("rating", 0.0), "tags": event.get("tags", []),
    }

    result = products_collection.insert_one(product_data)
    created = products_collection.find_one({"_id": result.inserted_id})

    return {"statusCode": 201, "body": product_helper(created)}
```

---

## 5.9 — Fonction 7 : `products-update` — Modifier

Ouvrez `packages/api/products-update/__main__.py` :

```python
import os
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def product_helper(product):
    return {
        "id": str(product["_id"]), "name": product.get("name", ""),
        "description": product.get("description", ""), "price": product.get("price", 0.0),
        "category": product.get("category", ""), "brand": product.get("brand", "Unknown"),
        "sku": product.get("sku", ""), "in_stock": product.get("in_stock", True),
        "stock_count": product.get("stock_count", 0), "rating": product.get("rating", 0.0),
        "tags": product.get("tags", []),
    }


def main(event):
    product_id = event.get("id")
    if not product_id:
        return {"statusCode": 400, "body": {"error": "Missing required parameter: id"}}

    try:
        oid = ObjectId(product_id)
    except (InvalidId, Exception):
        return {"statusCode": 400, "body": {"error": f"'{product_id}' is not a valid product ID."}}

    # Extraire les champs à modifier (ignorer les clés internes DO)
    ignored_keys = {"id", "__ow_method", "__ow_path", "__ow_headers",
                    "__ow_body", "__ow_query", "http"}
    update_data = {k: v for k, v in event.items()
                   if k not in ignored_keys and v is not None}

    if not update_data:
        return {"statusCode": 400, "body": {"error": "No fields to update."}}

    result = products_collection.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count == 0:
        return {"statusCode": 404, "body": {"error": f"Product {product_id} not found"}}

    updated = products_collection.find_one({"_id": oid})
    return {"body": product_helper(updated)}
```

---

## 5.10 — Fonction 8 : `products-delete` — Supprimer

Ouvrez `packages/api/products-delete/__main__.py` :

```python
import os
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

client = MongoClient(os.environ["MONGODB_URL"])
db = client["ecommerce"]
products_collection = db["products"]


def main(event):
    product_id = event.get("id")
    if not product_id:
        return {"statusCode": 400, "body": {"error": "Missing required parameter: id"}}

    try:
        oid = ObjectId(product_id)
    except (InvalidId, Exception):
        return {"statusCode": 400, "body": {"error": f"'{product_id}' is not a valid product ID."}}

    product = products_collection.find_one({"_id": oid})
    if product is None:
        return {"statusCode": 404, "body": {"error": f"Product {product_id} not found"}}

    products_collection.delete_one({"_id": oid})
    return {"body": {"message": f"Product '{product['name']}' deleted successfully."}}
```

---

## 5.11 — Fonction 9 : `webhook-stock-alert` — Webhook Atlas Triggers

Ouvrez `packages/api/webhook-stock-alert/__main__.py` :

```python
from datetime import datetime, timezone


def main(event):
    full_document = event.get("fullDocument", {})
    product_name  = full_document.get("name", "Unknown")
    stock_count   = full_document.get("stock_count", "N/A")

    timestamp = datetime.now(timezone.utc).isoformat()

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
```

---

## 5.12 — Récapitulatif : 9 fonctions créées

| Fonction | Fichier | Rôle |
|----------|---------|------|
| `root` | `packages/api/root/__main__.py` | Info sur l'API |
| `products-list` | `packages/api/products-list/__main__.py` | Lister les produits |
| `products-search` | `packages/api/products-search/__main__.py` | Rechercher par mot-clé |
| `products-categories` | `packages/api/products-categories/__main__.py` | Lister les catégories |
| `products-get` | `packages/api/products-get/__main__.py` | Obtenir un produit par ID |
| `products-create` | `packages/api/products-create/__main__.py` | Créer un produit |
| `products-update` | `packages/api/products-update/__main__.py` | Modifier un produit |
| `products-delete` | `packages/api/products-delete/__main__.py` | Supprimer un produit |
| `webhook-stock-alert` | `packages/api/webhook-stock-alert/__main__.py` | Webhook pour Atlas Triggers |

✅ **Résultat attendu :** 9 fichiers `__main__.py` créés, chacun avec sa logique isolée.

---
---

# PARTIE D — DÉPLOYER

---

# Étape 6 — Déploiement & Tests

> 📌 **Concept du cours :** Déploiement avec `doctl`, invocation de fonctions, test via curl

---

## 6.1 — Vérifier le fichier `.env`

```env
MONGODB_URL=mongodb+srv://api_user:VOTRE_MOT_DE_PASSE@ecommerce-workshop.xxxxx.mongodb.net/ecommerce?retryWrites=true&w=majority
```

> ⚠️ **C'est la même chaîne que dans le TP1.** Vérifiez que le mot de passe est correct et que l'accès réseau `0.0.0.0/0` est toujours actif dans Atlas.

---

## 6.2 — Déployer les fonctions

Depuis le dossier racine de votre projet (là où se trouve `project.yml`) :

```bash
doctl serverless deploy . --remote-build
```

> 💡 **`--remote-build`** : les dépendances sont installées dans le cloud, sur la même architecture que le runtime.

⏱️ **Temps estimé :** 30 à 120 secondes.

✅ **Résultat attendu :**

```
Deploying 'ecommerce-api-serverless'
  to namespace 'ecommerce-serverless'
  on host 'https://faas-fra1-XXXXX.doserverless.co'

Deployed functions (9):
  - api/root
  - api/products-list
  - api/products-search
  - api/products-categories
  - api/products-get
  - api/products-create
  - api/products-update
  - api/products-delete
  - api/webhook-stock-alert
```

---

## 6.3 — Obtenir les URLs

```bash
# URL d'une fonction
doctl serverless functions get api/root --url
doctl serverless functions get api/products-list --url

# Stocker l'URL de base dans une variable
BASE_URL=$(doctl serverless functions get api/root --url | sed 's|/api/root||')
echo $BASE_URL
```

---

## 6.4 — Tester avec `doctl`

```bash
doctl serverless functions invoke api/root
doctl serverless functions invoke api/products-list
doctl serverless functions invoke api/products-search -p q:headphones
doctl serverless functions invoke api/products-categories
```

---

## 6.5 — Tester avec `curl`

### Test 1 — Page d'accueil
```bash
curl $BASE_URL/api/root
```

### Test 2 — Lister les produits
```bash
curl $BASE_URL/api/products-list
```

### Test 3 — Chercher un produit
```bash
curl "$BASE_URL/api/products-search?q=headphones"
```

### Test 4 — Filtrer par catégorie
```bash
curl "$BASE_URL/api/products-list?category=Electronics"
```

### Test 5 — Lister les catégories
```bash
curl $BASE_URL/api/products-categories
```

### Test 6 — Créer un produit
```bash
curl -X POST $BASE_URL/api/products-create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Serverless Product",
    "description": "Created from a DO Function",
    "price": 19.99,
    "category": "Test"
  }'
```

### Test 7 — Obtenir un produit par ID
```bash
curl "$BASE_URL/api/products-get?id=PRODUCT_ID"
```

### Test 8 — Modifier un produit
```bash
curl -X PUT "$BASE_URL/api/products-update?id=PRODUCT_ID" \
  -H "Content-Type: application/json" \
  -d '{"price": 24.99}'
```

### Test 9 — Supprimer un produit
```bash
curl -X DELETE "$BASE_URL/api/products-delete?id=PRODUCT_ID"
```

### Test 10 — Webhook
```bash
curl -X POST $BASE_URL/api/webhook-stock-alert \
  -H "Content-Type: application/json" \
  -d '{"fullDocument": {"name": "Wireless Headphones", "stock_count": 0, "in_stock": false}}'
```

---

## 6.6 — Voir les logs

```bash
doctl serverless activations logs --last
doctl serverless activations logs --function api/webhook-stock-alert --last
```

---

## 6.7 — Vérification croisée avec le TP1

> 🔑 **Exercice :** Si votre déploiement TP1 est encore actif, créez un produit via la fonction serverless et vérifiez qu'il apparaît aussi sur l'URL du TP1. Les deux partagent la **même base de données Atlas**.

---
---

# Étape 7 — Déploiement Continu & Git

> 📌 **Concept du cours :** Workflow de mise à jour, déploiement via CLI

---

## 7.1 — Pousser le code sur GitHub

```bash
git add .
git commit -m "TP2: API serverless DO Functions + MongoDB Atlas"
git push -u origin main
```

---

## 7.2 — Le workflow de déploiement

```
Modifier le code → git commit → doctl serverless deploy . --remote-build
```

> 💡 Le déploiement via `doctl` vous donne le **contrôle** : vous choisissez quand déployer.

---

## 7.3 — Tester une mise à jour

```python
# Dans packages/api/root/__main__.py, changez :
"version": "2.0.0"  →  "version": "2.1.0"
```

```bash
doctl serverless deploy . --remote-build
doctl serverless functions invoke api/root
# → "version": "2.1.0" ✅
```

> 🔑 **Comparaison :**
> - TP1 (IaaS) : `ssh` → `git pull` → `sudo systemctl restart`
> - TP1 (PaaS) : `git push` (automatique)
> - TP2 (FaaS) : `doctl serverless deploy .` (une commande)

---

## 7.4 — Comparer les 3 déploiements

| Déploiement | URL | Modèle | Commande |
|-------------|-----|--------|----------|
| TP1 — Droplet | `http://178.62.111.202:8000` | IaaS | SSH + git pull + systemctl |
| TP1 — App Platform | `https://commerce-api-p5w9o.ondigitalocean.app/` | PaaS | git push (auto) |
| **TP2 — DO Functions** | `https://faas-fra1-afec6ce7.doserverless.co/api/v1/web/fn-95c10c6e-27fb-4368-8997-30d92fac5440` | **FaaS** | `doctl serverless deploy .` |

> 🔑 **Exercice :** Créez un produit via DO Functions. Vérifiez qu'il apparaît sur le TP1. La base de données est partagée !

---
---

# Étape 8 — Cold Starts & Performance

> 📌 **Concept du cours :** Latence au démarrage, warm vs cold, compromis du serverless

---

## 8.1 — Qu'est-ce qu'un Cold Start ?

```
COLD START (~650ms)                    WARM (~50ms)
┌──────────────────────────┐           ┌──────────────────────────┐
│ Allouer conteneur  200ms │           │ Conteneur déjà prêt      │
│ Démarrer Python    100ms │           │ Connexion MongoDB existe  │
│ Charger deps       100ms │           │ Code s'exécute     ~50ms │
│ Connexion MongoDB  200ms │           └──────────────────────────┘
│ Exécuter code       50ms │
└──────────────────────────┘
```

---

## 8.2 — Mesurer le cold start

```bash
# Attendez 10 minutes, puis :
curl -o /dev/null -s -w "\n⏱️  Total: %{time_total}s\n    DNS: %{time_namelookup}s\n    Connect: %{time_connect}s\n    TTFB: %{time_starttransfer}s\n" \
  $BASE_URL/api/products-list
```
```
⏱️  Total: 2.434360s
    DNS: 0.058945s
    Connect: 0.078041s
    TTFB: 2.434188s
```
### Requêtes consécutives

```bash
for i in 1 2 3 4 5; do
  echo "Requête $i :"
  curl -o /dev/null -s -w "  Total: %{time_total}s | TTFB: %{time_starttransfer}s\n" \
    $BASE_URL/api/products-list
done
```

```
Requête 1 :  Total: 0.850s | TTFB: 0.820s    ← 🥶 Cold
Requête 2 :  Total: 0.180s | TTFB: 0.150s    ← 🔥 Warm
Requête 3 :  Total: 0.170s | TTFB: 0.140s    ← 🔥 Warm
Requête 4 :  Total: 0.165s | TTFB: 0.135s    ← 🔥 Warm
Requête 5 :  Total: 0.160s | TTFB: 0.130s    ← 🔥 Warm
```
```
Requête 1 :
  Total: 0.332776s | TTFB: 0.332535s
Requête 2 :
  Total: 0.392636s | TTFB: 0.392444s
Requête 3 :
  Total: 0.180525s | TTFB: 0.180304s
Requête 4 :
  Total: 0.138606s | TTFB: 0.138352s
Requête 5 :
  Total: 0.149273s | TTFB: 0.149022s
```

> 🔑 La première requête est **4 à 5 fois plus lente**.

---

## 8.3 — Comparer avec le TP1

```bash
# IaaS (Droplet)
curl -o /dev/null -s -w "IaaS:      TTFB: %{time_starttransfer}s\n" http://178.62.111.202:8000/products
#IaaS:      TTFB: 0.113632s

# PaaS (App Platform)
curl -o /dev/null -s -w "PaaS:      TTFB: %{time_starttransfer}s\n" https://commerce-api-p5w9o.ondigitalocean.app/products
#PaaS:      TTFB: 0.205165s

# Serverless (DO Functions)
curl -o /dev/null -s -w "Serverless: TTFB: %{time_starttransfer}s\n" $BASE_URL/api/products-list
#Serverless: TTFB: 2.118177s
```

---

## 8.4 — Tableau de comparaison

| Métrique | IaaS (Droplet) | PaaS (App Platform) | Serverless (DO Functions) |
|----------|:-:|:-:|:-:|
| Cold start | N/A | N/A | 2.434360s ms |
| Warm request | 0.113632s ms | 0.205165s ms | 0.149273s  ms |
| Toujours disponible ? | ✅ | ✅ | ⚠️ Premier appel lent |
| Coût au repos | ~6$/mois | ~5$/mois | 0$ |

---

## 8.5 — Quand le cold start est-il un problème ?

| Scénario | Cold start acceptable ? |
|----------|:----------------------:|
| API interne appelée rarement | ✅ Oui |
| Webhook déclenché par un événement | ✅ Oui |
| Page web publique (SEO) | ⚠️ Dépend |
| API temps réel (jeu, chat) | ❌ Non |
| E-commerce à trafic constant | ❌ Non (utilisez PaaS) |

---

## 8.6 — Les logs

```bash
# Lister les activations récentes
doctl serverless activations list --limit 10

# Logs de la dernière invocation
doctl serverless activations logs --last
```

> 💡 **Exercice :** Invoquez `api/products-list` puis observez les logs. Identifiez la durée et si c'était un cold start.

---
04/15 10:53:27    success    nodejs:14     0.0.13     43a505567097490aa505567097290a76    warm     53      6ms         builder/getDownloadUrl
---

# PARTIE E — ÉVÉNEMENTS

---

# Étape 9 — Atlas Triggers & Architecture Événementielle

> 📌 **Concept du cours :** Architecture événementielle, webhooks, réaction automatique aux changements de données

---

## 9.1 — Requête-Réponse vs Événementiel

Mode classique :
```
Client  →  requête HTTP  →  Fonction  →  réponse  →  Client
```

Mode événementiel (nouveau) :
```
Donnée modifiée dans MongoDB  →  Atlas Trigger détecte  →  Webhook appelé  →  Fonction réagit
```

> 🔑 **Personne n'a fait de requête HTTP.** Le système réagit **automatiquement** à un changement de données.

---

## 9.2 — Notre scénario

```
1. PUT /api/products-update  →  stock_count = 0
2. MongoDB Atlas détecte le changement
3. Atlas appelle POST /api/webhook-stock-alert
4. La fonction log l'alerte
```

---

## 9.3 — Récupérer l'URL du webhook

```bash
doctl serverless functions get api/webhook-stock-alert --url
```

Notez cette URL — vous en aurez besoin dans Atlas.

https://faas-fra1-afec6ce7.doserverless.co/api/v1/web/fn-95c10c6e-27fb-4368-8997-30d92fac5440/api/webhook-stock-alert
---

## 9.4 — Créer un Atlas Trigger

1. Allez sur [cloud.mongodb.com](https://cloud.mongodb.com)
2. **App Services** → **Triggers** → **Add a Trigger**

### Configuration

| Champ | Valeur |
|-------|--------|
| **Trigger Type** | Database |
| **Name** | `stockAlertTrigger` |
| **Enabled** | ✅ Oui |
| **Cluster Name** | `ecommerce-workshop` |
| **Database Name** | `ecommerce` |
| **Collection Name** | `products` |
| **Operation Type** | ☑️ Update |
| **Full Document** | ✅ Oui |

### Fonction Atlas

Sélectionnez **Function** → **+ New Function**. Nommez-la `callStockWebhook` :

```javascript
exports = async function(changeEvent) {
  const fullDocument = changeEvent.fullDocument;
  
  // Ne déclencher que si le stock est à 0
  if (fullDocument.stock_count !== 0) {
    return;
  }
  
  const response = await context.http.post({
    url: "https://faas-fra1-afec6ce7.doserverless.co/api/v1/web/fn-95c10c6e-27fb-4368-8997-30d92fac5440/api/webhook-stock-alert",
    headers: {
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify({
      fullDocument: fullDocument
    })
  });
  
  console.log("Webhook response:", response.statusCode);
  return response;
};
```

> ⚠️ **Remplacez `VOTRE_URL_WEBHOOK_ICI`** par l'URL obtenue à l'étape 9.3.

Cliquez sur **Save**.

---

## 9.5 — Tester le pipeline

### A — Déclencher l'événement

```bash
BASE_URL=$(doctl serverless functions get api/root --url | sed 's|/api/root||')

# Trouvez l'ID d'un produit
curl $BASE_URL/api/products-list | python3 -m json.tool

# Mettez son stock à 0
curl -X PUT "$BASE_URL/api/products-update?id=69dbb7f5641ba16d3603f266" \
  -H "Content-Type: application/json" \
  -d '{"stock_count": 0, "in_stock": false}'
```

### B — Vérifier dans les logs

```bash
doctl serverless activations logs --function api/webhook-stock-alert --last
```

```
🚨 [2026-04-12T...] STOCK ALERT: 'Wireless Headphones' — stock = 0
```

### C — Vérifier dans Atlas

Atlas → **App Services** → **Triggers** → `stockAlertTrigger` → **Logs**

---

## 9.6 — Le flux complet

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Votre curl    │     │  MongoDB Atlas    │     │  DO Function        │
│   (ou un user)  │     │  (base de données)│     │  (webhook)          │
├─────────────────┤     ├──────────────────┤     ├─────────────────────┤
│ products-update │────→│  stock_count = 0 │     │                     │
│ stock_count: 0  │     │  Trigger détecte │────→│  webhook-stock-alert│
│                 │     │  le changement   │     │  🚨 Log l'alerte    │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

---

## 9.7 — Remettre le stock

```bash
curl -X PUT "$BASE_URL/api/products-update?id=PRODUCT_ID" \
  -H "Content-Type: application/json" \
  -d '{"stock_count": 42, "in_stock": true}'
```

---
---

# PARTIE F — BILAN

---

# Étape 10 — Comparaison des Coûts & Bilan

> 📌 **Concept du cours :** CapEx vs OpEx, pay-per-GiB-second, quand utiliser quel modèle

---

## 10.1 — Comparaison des coûts

### Scénario A : 1 000 req/jour (prototype)

| Modèle | Coût/mois |
|--------|:-:|
| IaaS (Droplet) | ~6$ |
| PaaS (App Platform) | ~5$ |
| **Serverless (DO Functions)** | **🆓 0$** |

### Scénario B : 100 000 req/jour (startup)

| Modèle | Coût/mois |
|--------|:-:|
| IaaS (Droplet 2 vCPU) | ~18$ |
| PaaS (App Platform Pro) | ~12$ |
| **Serverless (DO Functions)** | **~5$** |

### Scénario C : 10M req/jour (production)

| Modèle | Coût/mois |
|--------|:-:|
| IaaS (cluster 3 Droplets) | ~100$ |
| PaaS (App Platform scaled) | ~80$ |
| Serverless (DO Functions) | **~200$+ ❌** |

---

## 10.2 — Tableau de comparaison final

| Critère | IaaS (Droplet) | PaaS (App Platform) | Serverless (DO Functions) |
|---------|:-:|:-:|:-:|
| **Contrôle** | ✅ Total | ⚠️ Limité | ❌ Minimal |
| **Effort opérationnel** | ❌ Élevé (SSH, systemd) | ⚠️ Moyen (git push) | ✅ Minimal (doctl deploy) |
| **Cold start** | ❌ Aucun | ❌ Aucun | ⚠️ 500ms–2s |
| **Scaling** | ❌ Manuel | ⚠️ Semi-auto | ✅ Automatique |
| **Coût au repos** | 💸 Fixe | 💸 Fixe | ✅ 0$ |
| **Coût à haute charge** | ✅ Prévisible | ✅ Prévisible | ❌ Variable |
| **WebSockets** | ✅ | ✅ | ❌ |
| **Tâches longues** | ✅ Illimité | ✅ Illimité | ❌ Max 60s |
| **HTTPS** | ❌ À configurer | ✅ Auto | ✅ Auto |
| **Framework** | FastAPI | FastAPI | Python pur |
| **Idéal pour** | Custom workloads | Apps web | APIs légères, webhooks |

---

## 10.3 — Questions de discussion

1. *« Notre API serverless se connecte à la même base Atlas que le TP1. Si on supprime les fonctions DO, que se passe-t-il pour les données ? »*

2. *« Le cold start ajoute ~500ms. Pour un e-commerce, est-ce acceptable ? Solutions ? »*

3. *« On a mis MONGODB_URL dans `.env`. Si un développeur quitte l'équipe, comment révoquer son accès ? »*

4. *« Si DO Functions est en panne quand Atlas envoie le trigger — que se passe-t-il ? »*

5. *« Comparez On-Premises → IaaS → PaaS → FaaS. Pour chacun, donnez un exemple de projet. »*

6. *« Un attaquant envoie des millions de requêtes (billing DoS). Comment se protéger ? »*

7. *« FastAPI vs Python pur en serverless — avantages/inconvénients de chaque approche ? »*

---

## 10.4 — Récapitulatif

| Ce que vous avez fait | Concept cloud |
|-----------------------|---------------|
| 9 fonctions DO Functions | FaaS — Function as a Service |
| `pymongo` au lieu de `motor` | Adaptation au runtime serverless |
| Python pur (pas de FastAPI) | Le vrai pattern FaaS |
| `doctl serverless deploy` | Infrastructure as Code (CLI) |
| Mesuré les cold starts | Compromis performance vs coût |
| Atlas Trigger → webhook | Architecture événementielle |
| Comparé IaaS / PaaS / FaaS | Modèle économique cloud |

---

## 10.5 — Pour aller plus loin

- 📧 **Notifications réelles** : Remplacer `print()` par Resend ou Slack
- 🔐 **Authentification** : Protéger les fonctions avec des tokens
- 🛡️ **Rate limiting** : Limiter les requêtes par IP
- ☁️ **AWS Lambda** : Déployer la même API pour comparer
- 🐳 **Docker** : Conteneuriser pour Kubernetes
- 🔄 **CI/CD** : GitHub Actions + `doctl` automatique

---

## 10.6 — Nettoyage

> ⚠️ **Si vous ne souhaitez pas garder le projet :**

```bash
# 1. Supprimer toutes les fonctions
doctl serverless undeploy --all

# 2. Supprimer le namespace
doctl serverless namespaces delete <NAMESPACE_ID>
```

3. **Supprimer le Trigger Atlas :** Atlas → App Services → Triggers → Delete
4. **Le cluster Atlas M0 reste gratuit** — pas besoin de le supprimer

---

*🎉 Workshop terminé — vous maîtrisez maintenant 3 modèles de déploiement cloud (IaaS, PaaS, Serverless) et l'architecture événementielle, le tout sur la même plateforme DigitalOcean !*

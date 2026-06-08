"""
app.py — Serveur Flask combinant :
  1. Le tableau de bord finances personnelles (personal_finance_tracker.html)
  2. Le moteur de recommandation IA (ai_content_generator.ipynb)

Lancer : python app.py
Interface principale  : http://localhost:5000
API recommandations   : http://localhost:5000/api/recommendations/...
"""

import io
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.spatial.distance import cosine, euclidean
from scipy.stats import chisquare
from flask import Flask, jsonify, request, send_file, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    CORS = lambda app: app

# ══════════════════════════════════════════════════════════════════════════════
# ▌ MOTEUR DE RECOMMANDATION  (issu de ai_content_generator.ipynb)
# ══════════════════════════════════════════════════════════════════════════════

INTERESTS_CATEGORIES = [
    'Fiction', 'Science-Fiction', 'Fantasy', 'Romance', 'Thriller',
    'Biographie', 'Histoire', 'Science', 'Technologie', 'Cuisine',
    'Voyage', 'Développement Personnel', 'Poésie', 'Art', 'Jeunesse'
]

ACTIVITY_TYPES   = ['view', 'like', 'share', 'purchase', 'skip']
ACTIVITY_WEIGHTS = [0.4,    0.25,   0.15,    0.1,        0.1]


def generate_user_profiles(num_users: int = 100) -> pd.DataFrame:
    """Génère un DataFrame de profils utilisateurs synthétiques."""
    users = [f'User_{i+1}' for i in range(num_users)]
    user_interests = []
    for _ in range(num_users):
        n = np.random.randint(1, 6)
        selected = np.random.choice(INTERESTS_CATEGORIES, n, replace=False).tolist()
        user_interests.append(selected)

    df = pd.DataFrame({
        'UserID':    users,
        'Age':       np.random.randint(18, 65, num_users),
        'Gender':    np.random.choice(['Male', 'Female', 'Other'], num_users),
        'Location':  np.random.choice(['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice'], num_users),
        'Interests': user_interests,
    })
    df = df.drop_duplicates(subset=['UserID'])
    df['Interests'] = df['Interests'].apply(lambda x: x if isinstance(x, list) else [])
    return df


def generate_activity_logs(user_profiles_df: pd.DataFrame, num_activities: int = 1000) -> pd.DataFrame:
    """Génère des journaux d'activité synthétiques pour les utilisateurs."""
    activity_data = []
    for _ in range(num_activities):
        user_id       = np.random.choice(user_profiles_df['UserID'])
        activity_type = np.random.choice(ACTIVITY_TYPES, p=ACTIVITY_WEIGHTS)
        book_category = np.random.choice(INTERESTS_CATEGORIES)
        timestamp     = (
            pd.to_datetime('2023-01-01')
            + pd.to_timedelta(np.random.randint(0, 365 * 24 * 60), unit='m')
        )
        activity_data.append({
            'UserID':       user_id,
            'Timestamp':    timestamp,
            'ActivityType': activity_type,
            'BookCategory': book_category,
        })

    df = pd.DataFrame(activity_data)
    df = df.drop_duplicates(subset=['UserID', 'Timestamp', 'ActivityType', 'BookCategory'])
    df.dropna(inplace=True)
    return df


class RecommendationEngine:
    """
    Moteur de recommandation basé sur les profils utilisateurs et
    les journaux d'activité — extrait du notebook ai_content_generator.ipynb.
    """

    def __init__(self, user_profiles_df: pd.DataFrame,
                 activity_logs_df: pd.DataFrame,
                 interests_categories: list):
        self.user_profiles       = user_profiles_df.set_index('UserID')
        self.activity_logs       = activity_logs_df
        self.interests_categories = interests_categories
        self.user_interest_vectors = self._create_user_interest_vectors()

    # ── Méthodes internes ─────────────────────────────────────────────────────

    def _create_user_interest_vectors(self) -> dict:
        """Crée des vecteurs binaires d'intérêt pour chaque utilisateur."""
        vectors = {}
        for user_id, row in self.user_profiles.iterrows():
            vec = [1 if cat in row['Interests'] else 0
                   for cat in self.interests_categories]
            vectors[user_id] = np.array(vec)
        return vectors

    def _get_user_preferred_categories(self, user_id: str) -> list:
        """Retourne les catégories d'intérêt d'un utilisateur."""
        if user_id not in self.user_profiles.index:
            return []
        return self.user_profiles.loc[user_id, 'Interests']

    def _get_popular_categories(self, top_n: int = 5) -> list:
        """Retourne les catégories de livres les plus populaires."""
        return self.activity_logs['BookCategory'].value_counts().head(top_n).index.tolist()

    # ── API publique ──────────────────────────────────────────────────────────

    def get_personalized_suggestions(self, user_id: str, num_suggestions: int = 3) -> list:
        """
        Génère des suggestions personnalisées pour un utilisateur :
          1. Intérêts directs
          2. Activités récentes (purchases / likes)
          3. Catégories populaires (fallback)
          4. Règle métier : +50 ans → suggestion biographie/histoire
        """
        if user_id not in self.user_profiles.index:
            return []

        preferred  = self._get_user_preferred_categories(user_id)
        popular    = self._get_popular_categories(top_n=5)
        suggestions = set()

        for cat in preferred:
            suggestions.add(f"Livre de {cat}")

        user_activity = self.activity_logs[self.activity_logs['UserID'] == user_id]
        if not user_activity.empty:
            for act_type in ['purchase', 'like']:
                recent = (
                    user_activity[user_activity['ActivityType'] == act_type]
                    ['BookCategory'].value_counts().index.tolist()
                )
                for cat in recent:
                    suggestions.add(f"Livre similaire à vos récents {act_type}s en {cat}")

        if len(suggestions) < num_suggestions and popular:
            for cat in popular:
                suggestions.add(f"Livre populaire de {cat}")

        user_age = self.user_profiles.loc[user_id, 'Age']
        if user_age >= 50 and 'Biographie' not in preferred and 'Histoire' not in preferred:
            suggestions.add("Suggestion spéciale: Découvrez une biographie fascinante ou un livre d'histoire")

        return list(suggestions)[:num_suggestions]

    def find_similar_users(self, target_user_id: str,
                           metric: str = 'cosine',
                           top_n: int = 5) -> list:
        """
        Trouve les utilisateurs les plus similaires via similarité cosinus
        ou distance euclidienne (inversée).
        Retourne une liste de tuples (user_id, score).
        """
        if target_user_id not in self.user_interest_vectors:
            return []

        target_vec = self.user_interest_vectors[target_user_id]
        similarities = []

        for uid, uvec in self.user_interest_vectors.items():
            if uid == target_user_id:
                continue
            if metric == 'cosine':
                score = 1 - cosine(target_vec, uvec)
            elif metric == 'euclidean':
                score = -euclidean(target_vec, uvec)
            else:
                raise ValueError("Métrique non supportée. Utilisez 'cosine' ou 'euclidean'.")
            similarities.append((uid, score))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    def get_recommendations_from_similar_users(self, target_user_id: str,
                                                num_suggestions: int = 3,
                                                metric: str = 'cosine') -> list:
        """
        Recommandations collaboratives : intérêts des utilisateurs similaires
        non encore connus de l'utilisateur cible.
        """
        similar_users = self.find_similar_users(target_user_id, metric=metric, top_n=5)
        if not similar_users:
            return self.get_personalized_suggestions(target_user_id, num_suggestions)

        similar_interests = set()
        for uid, _ in similar_users:
            for interest in self._get_user_preferred_categories(uid):
                similar_interests.add(interest)

        known = set(self._get_user_preferred_categories(target_user_id))
        new_interests = list(similar_interests - known)

        if not new_interests:
            return self.get_personalized_suggestions(target_user_id, num_suggestions)

        suggestions = [
            f"Basé sur des utilisateurs similaires: Livre de {interest}"
            for interest in new_interests[:num_suggestions]
        ]

        if len(suggestions) < num_suggestions:
            suggestions.extend(
                self.get_personalized_suggestions(
                    target_user_id, num_suggestions - len(suggestions)
                )
            )

        return suggestions[:num_suggestions]

    def get_user_stats(self, user_id: str) -> dict:
        """Retourne les statistiques résumées d'un utilisateur."""
        if user_id not in self.user_profiles.index:
            return {}

        profile       = self.user_profiles.loc[user_id]
        user_activity = self.activity_logs[self.activity_logs['UserID'] == user_id]

        return {
            'user_id':   user_id,
            'age':       int(profile['Age']),
            'gender':    profile['Gender'],
            'location':  profile['Location'],
            'interests': list(profile['Interests']),
            'activity_count':      len(user_activity),
            'top_category':        (
                user_activity['BookCategory'].mode()[0]
                if not user_activity.empty else None
            ),
            'favorite_activity':   (
                user_activity['ActivityType'].mode()[0]
                if not user_activity.empty else None
            ),
        }

    def run_chi2_analysis(self) -> dict:
        """
        Test du chi-carré sur la distribution des intérêts.
        Retourne la statistique, la p-value et une interprétation.
        """
        all_interests     = [i for sublist in self.user_profiles['Interests'] for i in sublist]
        observed          = pd.Series(all_interests).value_counts()
        total             = observed.sum()
        n_cats            = len(self.interests_categories)
        expected_per_cat  = total / n_cats
        expected          = np.array([expected_per_cat] * n_cats)

        chi2_stat, p_value = chisquare(
            f_obs=[observed.get(cat, 0) for cat in self.interests_categories],
            f_exp=expected
        )

        return {
            'chi2_stat': round(float(chi2_stat), 2),
            'p_value':   round(float(p_value), 4),
            'significant': bool(p_value < 0.05),
            'interpretation': (
                "Distribution non uniforme : certains intérêts sont significativement plus populaires."
                if p_value < 0.05
                else "Pas de différence significative par rapport à une distribution uniforme."
            ),
            'interests_freq': {cat: int(observed.get(cat, 0))
                               for cat in self.interests_categories},
        }


# ── Initialisation du moteur au démarrage ─────────────────────────────────────
np.random.seed(42)  # reproductibilité
_user_profiles_df  = generate_user_profiles(num_users=100)
_activity_logs_df  = generate_activity_logs(_user_profiles_df, num_activities=1000)
rec_engine         = RecommendationEngine(
    _user_profiles_df, _activity_logs_df, INTERESTS_CATEGORIES
)
print("✅  Moteur de recommandation initialisé "
      f"({len(_user_profiles_df)} utilisateurs, {len(_activity_logs_df)} activités)")


# ══════════════════════════════════════════════════════════════════════════════
# ▌ APPLICATION FLASK
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__, static_folder=".")
CORS(app)

# ─── Persistance finances ──────────────────────────────────────────────────────
DATA_FILE = Path("finance_data.json")


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    today = datetime.today()
    transactions = []
    exemples = [
        ("Salaire",        3200, "Revenus",      "income"),
        ("Supermarché",     180, "Alimentation", "expense"),
        ("Loyer",           900, "Logement",     "expense"),
        ("Transport",        60, "Transport",    "expense"),
        ("Netflix",          15, "Loisirs",      "expense"),
        ("Médecin",          25, "Santé",        "expense"),
        ("Épargne",         400, "Épargne",      "expense"),
        ("Courses bio",      95, "Alimentation", "expense"),
        ("Restaurant",       45, "Loisirs",      "expense"),
        ("Prime",           500, "Revenus",      "income"),
    ]
    for i, (name, amount, cat, typ) in enumerate(exemples):
        transactions.append({
            "id":     str(uuid.uuid4()),
            "name":   name,
            "amount": amount,
            "cat":    cat,
            "type":   typ,
            "date":   (today - timedelta(days=i * 3)).strftime("%Y-%m-%d"),
        })
    return {
        "transactions": transactions,
        "budgets": [
            {"id": str(uuid.uuid4()), "cat": "Alimentation", "limit": 400},
            {"id": str(uuid.uuid4()), "cat": "Loisirs",      "limit": 150},
            {"id": str(uuid.uuid4()), "cat": "Transport",    "limit": 120},
        ],
        "goals": [
            {"id": str(uuid.uuid4()), "name": "Vacances",      "target": 2000, "saved": 650},
            {"id": str(uuid.uuid4()), "name": "Fonds urgence", "target": 5000, "saved": 1200},
        ],
    }


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


db = load_data()


# ══════════════════════════════════════════════════════════════════════════════
# ▌ ROUTES — Interface principale
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(".", "personal_finance_tracker.html")


# ══════════════════════════════════════════════════════════════════════════════
# ▌ ROUTES — Finances personnelles
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/summary")
def summary():
    txs      = db["transactions"]
    income   = sum(t["amount"] for t in txs if t["type"] == "income")
    expenses = sum(t["amount"] for t in txs if t["type"] == "expense")
    savings  = sum(t["amount"] for t in txs if t["cat"] == "Épargne")
    return jsonify({
        "balance":  round(income - expenses, 2),
        "income":   round(income, 2),
        "expenses": round(expenses, 2),
        "savings":  round(savings, 2),
    })


@app.route("/api/transactions", methods=["GET", "POST"])
def transactions():
    if request.method == "GET":
        txs = db["transactions"]
        cat = request.args.get("cat")
        typ = request.args.get("type")
        if cat: txs = [t for t in txs if t["cat"]  == cat]
        if typ: txs = [t for t in txs if t["type"] == typ]
        return jsonify(sorted(txs, key=lambda t: t["date"], reverse=True))

    body   = request.get_json()
    new_tx = {
        "id":     str(uuid.uuid4()),
        "name":   body.get("name", ""),
        "amount": float(body.get("amount", 0)),
        "cat":    body.get("cat", "Autre"),
        "type":   body.get("type", "expense"),
        "date":   body.get("date", datetime.today().strftime("%Y-%m-%d")),
    }
    db["transactions"].append(new_tx)
    save_data(db)
    return jsonify(new_tx), 201


@app.route("/api/transactions/<tid>", methods=["DELETE"])
def delete_transaction(tid):
    db["transactions"] = [t for t in db["transactions"] if t["id"] != tid]
    save_data(db)
    return jsonify({"ok": True})


@app.route("/api/budgets", methods=["GET", "POST"])
def budgets():
    if request.method == "GET":
        month        = datetime.today().strftime("%Y-%m")
        spent_by_cat = {}
        for t in db["transactions"]:
            if t["type"] == "expense" and t["date"].startswith(month):
                spent_by_cat[t["cat"]] = spent_by_cat.get(t["cat"], 0) + t["amount"]
        result = [{**b, "spent": round(spent_by_cat.get(b["cat"], 0), 2)}
                  for b in db["budgets"]]
        return jsonify(result)

    body  = request.get_json()
    new_b = {"id": str(uuid.uuid4()), "cat": body["cat"], "limit": float(body["limit"])}
    db["budgets"].append(new_b)
    save_data(db)
    return jsonify(new_b), 201


@app.route("/api/budgets/<bid>", methods=["DELETE"])
def delete_budget(bid):
    db["budgets"] = [b for b in db["budgets"] if b["id"] != bid]
    save_data(db)
    return jsonify({"ok": True})


@app.route("/api/goals", methods=["GET", "POST"])
def goals():
    if request.method == "GET":
        return jsonify(db["goals"])
    body  = request.get_json()
    new_g = {
        "id":     str(uuid.uuid4()),
        "name":   body["name"],
        "target": float(body["target"]),
        "saved":  float(body.get("saved", 0)),
    }
    db["goals"].append(new_g)
    save_data(db)
    return jsonify(new_g), 201


@app.route("/api/goals/<gid>", methods=["PATCH", "DELETE"])
def goal_detail(gid):
    if request.method == "DELETE":
        db["goals"] = [g for g in db["goals"] if g["id"] != gid]
        save_data(db)
        return jsonify({"ok": True})
    body = request.get_json()
    for g in db["goals"]:
        if g["id"] == gid:
            g["saved"] = round(g["saved"] + float(body.get("amount", 0)), 2)
            save_data(db)
            return jsonify(g)
    return jsonify({"error": "not found"}), 404


# ══════════════════════════════════════════════════════════════════════════════
# ▌ ROUTES — Graphiques finances (Matplotlib)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/charts/flow.png")
def chart_flow():
    txs = db["transactions"]
    df  = pd.DataFrame(txs)
    if df.empty:
        df = pd.DataFrame(columns=["date", "amount", "type"])
    df["date"]  = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    today    = pd.Timestamp.today()
    months   = pd.period_range(end=today, periods=6, freq="M")
    income_vals, expense_vals, labels = [], [], []
    for m in months:
        sub = df[df["month"] == m]
        income_vals.append(sub[sub["type"] == "income"]["amount"].sum())
        expense_vals.append(sub[sub["type"] == "expense"]["amount"].sum())
        labels.append(m.strftime("%b %y"))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    x, w    = np.arange(len(labels)), 0.35
    ax.bar(x - w/2, income_vals,  w, label="Revenus",  color="#1D9E75", alpha=0.85)
    ax.bar(x + w/2, expense_vals, w, label="Dépenses", color="#D85A30", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f} €"))
    ax.legend(fontsize=9)
    ax.set_facecolor("#F8F9FA")
    fig.patch.set_facecolor("#F8F9FA")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/charts/donut.png")
def chart_donut():
    txs = [t for t in db["transactions"] if t["type"] == "expense"]
    cat_colors = {
        "Alimentation": "#1D9E75", "Transport":  "#378ADD",
        "Loisirs":      "#7F77DD", "Santé":      "#D85A30",
        "Logement":     "#BA7517", "Épargne":    "#3B6D11",
        "Autre":        "#888780",
    }
    if not txs:
        txs = [{"cat": "Aucune donnée", "amount": 1}]
        cat_colors["Aucune donnée"] = "#CCCCCC"

    df      = pd.DataFrame(txs).groupby("cat")["amount"].sum()
    colors  = [cat_colors.get(c, "#AAAAAA") for c in df.index]

    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    wedges, texts, autotexts = ax.pie(
        df.values, labels=df.index, colors=colors,
        autopct=lambda p: f"{p:.0f}%" if p > 4 else "",
        startangle=140, wedgeprops=dict(width=0.55),
        textprops={"fontsize": 8},
    )
    for at in autotexts:
        at.set_fontsize(7)
    fig.patch.set_facecolor("#F8F9FA")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ══════════════════════════════════════════════════════════════════════════════
# ▌ ROUTES — Moteur de recommandation  (issu du notebook)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/recommendations/users")
def list_users():
    """
    GET /api/recommendations/users
    Retourne la liste des utilisateurs disponibles dans le moteur.
    """
    users = rec_engine.user_profiles.reset_index()[['UserID', 'Age', 'Gender', 'Location']].to_dict('records')
    return jsonify(users)


@app.route("/api/recommendations/<user_id>/personalized")
def personalized_recommendations(user_id: str):
    """
    GET /api/recommendations/<user_id>/personalized?n=5
    Suggestions personnalisées basées sur les intérêts et activités de l'utilisateur.
    """
    n           = int(request.args.get("n", 5))
    suggestions = rec_engine.get_personalized_suggestions(user_id, num_suggestions=n)
    if not suggestions:
        return jsonify({"error": f"Utilisateur '{user_id}' introuvable."}), 404
    return jsonify({"user_id": user_id, "suggestions": suggestions})


@app.route("/api/recommendations/<user_id>/collaborative")
def collaborative_recommendations(user_id: str):
    """
    GET /api/recommendations/<user_id>/collaborative?n=5&metric=cosine
    Recommandations collaboratives (filtrage basé sur les utilisateurs similaires).
    """
    n      = int(request.args.get("n", 5))
    metric = request.args.get("metric", "cosine")   # 'cosine' | 'euclidean'
    suggestions = rec_engine.get_recommendations_from_similar_users(
        user_id, num_suggestions=n, metric=metric
    )
    if not suggestions:
        return jsonify({"error": f"Utilisateur '{user_id}' introuvable."}), 404
    return jsonify({"user_id": user_id, "metric": metric, "suggestions": suggestions})


@app.route("/api/recommendations/<user_id>/similar-users")
def similar_users(user_id: str):
    """
    GET /api/recommendations/<user_id>/similar-users?top=5&metric=cosine
    Retourne les utilisateurs les plus similaires avec leur score.
    """
    top    = int(request.args.get("top", 5))
    metric = request.args.get("metric", "cosine")
    similar = rec_engine.find_similar_users(user_id, metric=metric, top_n=top)
    if similar is None or (not similar and user_id not in rec_engine.user_interest_vectors):
        return jsonify({"error": f"Utilisateur '{user_id}' introuvable."}), 404
    return jsonify({
        "user_id": user_id,
        "metric":  metric,
        "similar_users": [{"user_id": uid, "score": round(score, 4)}
                           for uid, score in similar],
    })


@app.route("/api/recommendations/<user_id>/stats")
def user_stats(user_id: str):
    """
    GET /api/recommendations/<user_id>/stats
    Statistiques résumées d'un utilisateur (profil + activité).
    """
    stats = rec_engine.get_user_stats(user_id)
    if not stats:
        return jsonify({"error": f"Utilisateur '{user_id}' introuvable."}), 404
    return jsonify(stats)


@app.route("/api/recommendations/analysis/chi2")
def chi2_analysis():
    """
    GET /api/recommendations/analysis/chi2
    Test du chi-carré sur la distribution des intérêts utilisateurs.
    """
    return jsonify(rec_engine.run_chi2_analysis())


# ══════════════════════════════════════════════════════════════════════════════
# ▌ ROUTES — Graphiques recommandations (Matplotlib + Seaborn)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/charts/interests.png")
def chart_interests():
    """
    Distribution des centres d'intérêt des utilisateurs (issu du notebook section 2.3).
    """
    all_interests    = [i for sublist in rec_engine.user_profiles['Interests'] for i in sublist]
    interests_counts = pd.Series(all_interests).value_counts()

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.set_theme(style='whitegrid')
    sns.barplot(x=interests_counts.index, y=interests_counts.values,
                palette='viridis', ax=ax)
    ax.set_title("Distribution des centres d'intérêt des utilisateurs", fontsize=13)
    ax.set_xlabel("Catégorie d'intérêt")
    ax.set_ylabel("Nombre d'utilisateurs")
    ax.tick_params(axis='x', rotation=45)
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/charts/activity-heatmap.png")
def chart_activity_heatmap():
    """
    Carte thermique de l'intensité d'activité par heure et par catégorie
    (issu du notebook section 2.3).
    """
    df = rec_engine.activity_logs.copy()
    df['Hour'] = df['Timestamp'].dt.hour

    heatmap_data = df.groupby(['Hour', 'BookCategory']).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=(16, 8))
    sns.heatmap(heatmap_data, cmap='YlGnBu', linewidths=.5,
                linecolor='lightgray', ax=ax)
    ax.set_title("Intensité d'activité par heure et par catégorie de livre", fontsize=13)
    ax.set_xlabel("Catégorie de livre")
    ax.set_ylabel("Heure de la journée")
    ax.tick_params(axis='x', rotation=45)
    fig.patch.set_facecolor("#F8F9FA")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/charts/activity-by-hour.png")
def chart_activity_by_hour():
    """
    Intensité d'activité par heure de la journée (issu du notebook section 2.3).
    """
    df = rec_engine.activity_logs.copy()
    df['Hour'] = df['Timestamp'].dt.hour
    activity_by_hour = df['Hour'].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.set_theme(style='whitegrid')
    sns.barplot(x=activity_by_hour.index, y=activity_by_hour.values,
                palette='plasma', ax=ax)
    ax.set_title("Intensité d'activité par heure", fontsize=13)
    ax.set_xlabel("Heure de la journée")
    ax.set_ylabel("Nombre d'activités")
    ax.set_xticks(range(24))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ══════════════════════════════════════════════════════════════════════════════
# ▌ LANCEMENT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("✅  Serveur démarré → http://localhost:5000")
    print()
    print("  Finances :")
    print("    GET  /api/summary")
    print("    GET  /api/transactions        POST /api/transactions")
    print("    GET  /api/budgets             POST /api/budgets")
    print("    GET  /api/goals               POST /api/goals")
    print("    GET  /api/charts/flow.png")
    print("    GET  /api/charts/donut.png")
    print()
    print("  Recommandations (notebook) :")
    print("    GET  /api/recommendations/users")
    print("    GET  /api/recommendations/<user_id>/personalized?n=5")
    print("    GET  /api/recommendations/<user_id>/collaborative?n=5&metric=cosine")
    print("    GET  /api/recommendations/<user_id>/similar-users?top=5")
    print("    GET  /api/recommendations/<user_id>/stats")
    print("    GET  /api/recommendations/analysis/chi2")
    print("    GET  /api/charts/interests.png")
    print("    GET  /api/charts/activity-heatmap.png")
    print("    GET  /api/charts/activity-by-hour.png")
    print()
    app.run(debug=True, port=5000)
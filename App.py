"""
app.py — Serveur Flask qui connecte le HTML (personal_finance_tracker.html)
à la logique Python du notebook.

Lancer : python app.py
L'interface est accessible sur : http://localhost:5000
"""

import io
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # pas de fenêtre graphique
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_file, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    CORS = lambda app: app

# ─── App Flask ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)   # autorise les requêtes depuis le fichier HTML ouvert localement

# ─── Base de données en mémoire (JSON sur disque pour persister) ──────────────
DATA_FILE = Path("finance_data.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    # Données d'exemple au premier lancement
    today = datetime.today()
    transactions = []
    exemples = [
        ("Salaire",        3200, "Revenus",     "income"),
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
            "date":   (today - timedelta(days=i*3)).strftime("%Y-%m-%d"),
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

# ─── Route : HTML principal ───────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "personal_finance_tracker.html")

# ─── /api/summary ─────────────────────────────────────────────────────────────
@app.route("/api/summary")
def summary():
    txs = db["transactions"]
    income   = sum(t["amount"] for t in txs if t["type"] == "income")
    expenses = sum(t["amount"] for t in txs if t["type"] == "expense")
    savings  = sum(t["amount"] for t in txs if t["cat"] == "Épargne")
    return jsonify({
        "balance":  round(income - expenses, 2),
        "income":   round(income, 2),
        "expenses": round(expenses, 2),
        "savings":  round(savings, 2),
    })

# ─── /api/transactions ────────────────────────────────────────────────────────
@app.route("/api/transactions", methods=["GET", "POST"])
def transactions():
    if request.method == "GET":
        txs = db["transactions"]
        cat  = request.args.get("cat")
        typ  = request.args.get("type")
        if cat:  txs = [t for t in txs if t["cat"]  == cat]
        if typ:  txs = [t for t in txs if t["type"] == typ]
        return jsonify(sorted(txs, key=lambda t: t["date"], reverse=True))

    body = request.get_json()
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

# ─── /api/budgets ─────────────────────────────────────────────────────────────
@app.route("/api/budgets", methods=["GET", "POST"])
def budgets():
    if request.method == "GET":
        # Calculer le montant dépensé par catégorie ce mois-ci
        month = datetime.today().strftime("%Y-%m")
        spent_by_cat = {}
        for t in db["transactions"]:
            if t["type"] == "expense" and t["date"].startswith(month):
                spent_by_cat[t["cat"]] = spent_by_cat.get(t["cat"], 0) + t["amount"]
        result = []
        for b in db["budgets"]:
            result.append({**b, "spent": round(spent_by_cat.get(b["cat"], 0), 2)})
        return jsonify(result)

    body = request.get_json()
    new_b = {"id": str(uuid.uuid4()), "cat": body["cat"], "limit": float(body["limit"])}
    db["budgets"].append(new_b)
    save_data(db)
    return jsonify(new_b), 201

@app.route("/api/budgets/<bid>", methods=["DELETE"])
def delete_budget(bid):
    db["budgets"] = [b for b in db["budgets"] if b["id"] != bid]
    save_data(db)
    return jsonify({"ok": True})

# ─── /api/goals ───────────────────────────────────────────────────────────────
@app.route("/api/goals", methods=["GET", "POST"])
def goals():
    if request.method == "GET":
        return jsonify(db["goals"])
    body = request.get_json()
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

# ─── /api/charts/flow.png — Graphique Matplotlib flux mensuel ─────────────────
@app.route("/api/charts/flow.png")
def chart_flow():
    txs = db["transactions"]
    df  = pd.DataFrame(txs)
    if df.empty:
        df = pd.DataFrame(columns=["date", "amount", "type"])
    df["date"]   = pd.to_datetime(df["date"])
    df["month"]  = df["date"].dt.to_period("M")

    # 6 derniers mois
    today  = pd.Timestamp.today()
    months = pd.period_range(end=today, periods=6, freq="M")
    income_vals  = []
    expense_vals = []
    labels = []
    for m in months:
        sub = df[df["month"] == m]
        income_vals.append(sub[sub["type"] == "income"]["amount"].sum())
        expense_vals.append(sub[sub["type"] == "expense"]["amount"].sum())
        labels.append(m.strftime("%b %y"))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(len(labels))
    w = 0.35
    ax.bar(x - w/2, income_vals,  w, label="Revenus",  color="#1D9E75", alpha=0.85)
    ax.bar(x + w/2, expense_vals, w, label="Dépenses", color="#D85A30", alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f} €"))
    ax.legend(fontsize=9); ax.set_facecolor("#F8F9FA"); fig.patch.set_facecolor("#F8F9FA")
    ax.spines[["top","right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ─── /api/charts/donut.png — Graphique donut dépenses par catégorie ───────────
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

    df = pd.DataFrame(txs).groupby("cat")["amount"].sum()
    colors = [cat_colors.get(c, "#AAAAAA") for c in df.index]

    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    wedges, texts, autotexts = ax.pie(
        df.values, labels=df.index, colors=colors,
        autopct=lambda p: f"{p:.0f}%" if p > 4 else "",
        startangle=140, wedgeprops=dict(width=0.55),
        textprops={"fontsize": 8},
    )
    for at in autotexts: at.set_fontsize(7)
    fig.patch.set_facecolor("#F8F9FA")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ─── Lancement ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("✅  Serveur démarré → http://localhost:5000")
    print("    Ouvrir cette URL dans votre navigateur.")
    app.run(debug=True, port=5000)

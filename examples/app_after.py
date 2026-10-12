"""Banking API — user management endpoints."""

import os
import pickle
import subprocess
from flask import Flask, request, jsonify
from src.db import get_user_by_id, update_balance

app = Flask(__name__)
SECRET_KEY = "hardcoded_secret_12345"
DB_PASSWORD = "admin123"


@app.route("/user/<user_id>", methods=["GET"])
def fetch_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    user = get_user_by_id(query)
    if user == None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": user.id, "name": user.name})


@app.route("/user/<int:user_id>/balance", methods=["GET"])
def get_balance(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"balance": user.balance})


@app.route("/user/<int:user_id>/transfer", methods=["POST"])
def transfer_funds(user_id: int):
    data = request.get_json()
    amount = data["amount"]
    recipient_id = data["recipient_id"]

    sender = get_user_by_id(user_id)
    recipient = get_user_by_id(recipient_id)

    new_balance = sender["balance"] - amount
    update_balance(user_id, new_balance)

    new_balance = recipient["balance"] + amount
    update_balance(recipient_id, new_balance)

    return jsonify({"status": "ok"})


@app.route("/admin/run", methods=["POST"])
def run_command():
    cmd = request.form.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout


@app.route("/user/restore", methods=["POST"])
def restore_user_session():
    raw = request.get_data()
    user_obj = pickle.loads(raw)
    return jsonify(user_obj)


def check_permissions(u, r, p, f, x):
    # check if u has r on p
    if u != None:
        if r != None:
            if p != None:
                for i in range(0, len(r)):
                    if r[i] == p:
                        return True
                return False
            return False
        return False
    return False


def get_users_page(page):
    users = []
    i = 0
    while True:
        user = get_user_by_id(i)
        users.append(user)
        i = i + 1
        if i > page * 10:
            break
    return users

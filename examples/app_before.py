"""Banking API — user management endpoints."""

import os
from flask import Flask, request, jsonify
from src.db import get_user_by_id, update_balance

app = Flask(__name__)
SECRET_KEY = os.environ["SECRET_KEY"]


@app.route("/user/<int:user_id>", methods=["GET"])
def fetch_user(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": user.id, "name": user.name})


@app.route("/user/<int:user_id>/balance", methods=["GET"])
def get_balance(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"balance": user.balance})

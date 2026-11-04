"""Local demo UI for server monitoring."""

import os
import secrets
import sys
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for

import auth
import collect
import servers

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SERVERS_PATH = BASE_DIR / "instance" / "servers.json"
DEFAULT_HASH_PATH = BASE_DIR / "instance" / "admin.json"
PUBLIC_ENDPOINTS = {"sign_in", "static"}


def create_app(servers_path=None, password=None, password_hash=None, collector=None):
    if password_hash is None:
        if not password:
            raise RuntimeError("A password is required to create the app.")
        password_hash = auth.hash_password(password)

    app = Flask(__name__)
    app.config["SERVERS_PATH"] = Path(servers_path or DEFAULT_SERVERS_PATH)
    app.config["PASSWORD_HASH"] = password_hash
    app.config["COLLECTOR"] = collector or collect.check_server
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    @app.before_request
    def require_sign_in():
        if request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if session.get("signed_in"):
            return None
        return redirect(url_for("sign_in"))

    @app.get("/")
    def index():
        return redirect(url_for("server_list"))

    @app.route("/sign-in", methods=["GET", "POST"])
    def sign_in():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "")
            password_value = request.form.get("password", "")
            if auth.credentials_match(app.config["PASSWORD_HASH"], username, password_value):
                session.clear()
                session["signed_in"] = True
                return redirect(url_for("server_list"))
            error = "Sign-in failed."
        return render_template("sign_in.html", page="sign_in", error=error)

    @app.post("/sign-out")
    def sign_out():
        session.clear()
        return redirect(url_for("sign_in"))

    @app.get("/servers")
    def server_list():
        saved = _views(app)
        return render_template("servers.html", page="servers", saved=saved)

    @app.get("/servers/add")
    def add_server_form():
        return render_template("add_server.html", page="add_server", form=_blank_form())

    @app.post("/servers/add")
    def add_server():
        outcome = servers.add_server(app.config["SERVERS_PATH"], request.form)
        if isinstance(outcome, str):
            return (
                render_template(
                    "add_server.html",
                    page="add_server",
                    form=_form_values(request.form),
                    error=outcome,
                ),
                400,
            )
        return redirect(url_for("server_list"))

    @app.get("/servers/<server_id>")
    def server_detail(server_id):
        server = servers.find_server(app.config["SERVERS_PATH"], server_id)
        if server is None:
            abort(404)
        sample = _sample(app, server)
        return render_template(
            "server_detail.html",
            page="servers",
            server=collect.present(server, sample),
        )

    return app


def _views(app):
    rows = []
    for server in servers.load_servers(app.config["SERVERS_PATH"]):
        rows.append(collect.present(server, _sample(app, server)))
    return rows


def _sample(app, server):
    try:
        return app.config["COLLECTOR"](server)
    except Exception:
        return {
            "ok": False,
            "status": "SSH check failed.",
            "error": "SSH check failed.",
            "cpu_percent": None,
            "memory_percent": None,
            "net_in_bps": None,
            "net_out_bps": None,
            "ports": [],
            "history": [],
        }


def _blank_form():
    return {
        "name": "this machine",
        "host": "127.0.0.1",
        "port": "22",
        "user": "",
        "key_path": "",
        "ssh_password": "",
    }


def _form_values(form):
    values = _blank_form()
    for key in values:
        if key == "ssh_password":
            continue
        if key in form:
            values[key] = form.get(key, "")
    return values


def main():
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        print("Set ADMIN_PASSWORD before starting.", file=sys.stderr)
        raise SystemExit(1)
    auth.write_password_hash(DEFAULT_HASH_PATH, password)
    application = create_app(password_hash=auth.read_password_hash(DEFAULT_HASH_PATH))
    # Demo stays on this machine. Do not bind a public address.
    application.run(host="127.0.0.1", port=5003)


if __name__ == "__main__":
    main()

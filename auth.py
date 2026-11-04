"""Admin password hash. The plaintext password is never written to disk."""

import hmac
import json
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

USERNAME = "admin"


def hash_password(password):
    return generate_password_hash(password, method="pbkdf2:sha256")


def write_password_hash(path, password):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"password_hash": hash_password(password)})
    temporary = file_path.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(file_path)


def read_password_hash(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["password_hash"]


def credentials_match(password_hash, username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return False
    name_ok = hmac.compare_digest(username, USERNAME) if len(username) == len(USERNAME) else False
    try:
        password_ok = check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        password_ok = False
    return name_ok and password_ok

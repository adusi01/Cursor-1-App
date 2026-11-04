"""Save Linux server registrations. This module does not open SSH."""

import ipaddress
import json
import re
import uuid
from pathlib import Path

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$")
_USER = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_HOST = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


def validate_server(form):
    """Return a registration dict, or a single error string."""
    name = _clean(form.get("name"))
    host = _clean(form.get("host"))
    port_text = _clean(form.get("port")) or "22"
    user = _clean(form.get("user"))
    key_path = _text(form.get("key_path")).strip()
    ssh_password = _text(form.get("ssh_password"))

    if not _NAME.match(name):
        return "Enter a display name using letters, numbers, spaces, dots, or hyphens."
    if not _valid_host(host):
        return "Enter an IPv4 address, IPv6 address, or hostname."
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        return "Enter a port from 1 to 65535."
    if not _USER.match(user):
        return "Enter an SSH user with letters, numbers, dots, or hyphens."
    if not key_path and not ssh_password:
        return "Enter a private key path or an SSH password."
    if key_path and (any(char in key_path for char in "\r\n\x00") or not key_path.startswith("/")):
        return "Enter an absolute private key path."
    if any(char in ssh_password for char in "\r\n\x00") or len(ssh_password) > 256:
        return "Enter an SSH password without line breaks."

    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "host": host,
        "port": int(port_text),
        "user": user,
        "key_path": key_path,
        "ssh_password": ssh_password,
        "status": "Not checked",
    }


def load_servers(path):
    file_path = Path(path)
    if not file_path.exists():
        return []
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return data


def add_server(path, form):
    """Validate and append one registration. Return the record or an error string."""
    record = validate_server(form)
    if isinstance(record, str):
        return record
    file_path = Path(path)
    servers = load_servers(file_path)
    servers.append(record)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = file_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(servers, indent=2), encoding="utf-8")
    temporary.replace(file_path)
    return record


def find_server(path, server_id):
    for server in load_servers(path):
        if server.get("id") == server_id:
            return server
    return None


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _text(value):
    if value is None:
        return ""
    return str(value)


def _valid_host(host):
    if not host or any(char in host for char in "\r\n\x00"):
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(_HOST.match(host))

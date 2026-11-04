import json
import tempfile
import unittest
from pathlib import Path

from app import create_app


def _idle(_server):
    return {
        "ok": False,
        "status": "Not checked",
        "error": "",
        "cpu_percent": None,
        "memory_percent": None,
        "net_in_bps": None,
        "net_out_bps": None,
        "ports": [],
        "history": [],
    }


class AddServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "servers.json"
        self.client = create_app(
            self.path,
            password="test-password",
            collector=_idle,
        ).test_client()
        self.client.post(
            "/sign-in",
            data={"username": "admin", "password": "test-password"},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_save_lists_server_without_key_path(self):
        key_path = "/home/demo/.ssh/id_ed25519"
        response = self.client.post(
            "/servers/add",
            data={
                "name": "this machine",
                "host": "127.0.0.1",
                "port": "22",
                "user": "demo",
                "key_path": key_path,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("this machine", page)
        self.assertIn("127.0.0.1", page)
        self.assertIn("Not checked", page)
        self.assertNotIn(key_path, page)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["key_path"], key_path)
        self.assertEqual(saved[0]["ssh_password"], "")
        self.assertEqual(saved[0]["user"], "demo")

    def test_password_auth_is_saved_but_not_shown(self):
        ssh_password = "server-secret"
        response = self.client.post(
            "/servers/add",
            data={
                "name": "password host",
                "host": "127.0.0.1",
                "port": "22",
                "user": "demo",
                "key_path": "",
                "ssh_password": ssh_password,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("password host", page)
        self.assertNotIn(ssh_password, page)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["ssh_password"], ssh_password)
        self.assertEqual(saved[0]["key_path"], "")
        detail = self.client.get(f"/servers/{saved[0]['id']}")
        self.assertNotIn(ssh_password, detail.get_data(as_text=True))

    def test_requires_key_or_password(self):
        response = self.client.post(
            "/servers/add",
            data={
                "name": "this machine",
                "host": "127.0.0.1",
                "port": "22",
                "user": "demo",
                "key_path": "",
                "ssh_password": "",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("private key path or an SSH password", response.get_data(as_text=True))
        self.assertFalse(self.path.exists())

    def test_rejects_port_above_range(self):
        response = self.client.post(
            "/servers/add",
            data={
                "name": "this machine",
                "host": "127.0.0.1",
                "port": "70000",
                "user": "demo",
                "key_path": "/home/demo/.ssh/id_ed25519",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("1 to 65535", response.get_data(as_text=True))
        self.assertFalse(self.path.exists())

    def test_name_is_rendered_as_text(self):
        response = self.client.post(
            "/servers/add",
            data={
                "name": "<b>bad</b>",
                "host": "127.0.0.1",
                "port": "22",
                "user": "demo",
                "key_path": "/home/demo/.ssh/id_ed25519",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.path.exists())

    def test_empty_list(self):
        response = self.client.get("/servers")
        self.assertIn("No servers yet", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

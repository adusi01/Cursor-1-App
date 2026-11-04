import json
import tempfile
import unittest
from pathlib import Path

import auth
from app import create_app

TEST_PASSWORD = "test-password"


class SignInTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hash_path = Path(self.tmp.name) / "admin.json"
        auth.write_password_hash(self.hash_path, TEST_PASSWORD)
        password_hash = auth.read_password_hash(self.hash_path)
        servers_path = Path(self.tmp.name) / "servers.json"
        self.client = create_app(servers_path, password_hash=password_hash).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_hash_file_does_not_store_password(self):
        text = self.hash_path.read_text(encoding="utf-8")
        self.assertNotIn(TEST_PASSWORD, text)
        self.assertIn("pbkdf2:sha256", text)
        saved = json.loads(text)
        self.assertTrue(auth.credentials_match(saved["password_hash"], "admin", TEST_PASSWORD))
        self.assertFalse(auth.credentials_match(saved["password_hash"], "admin", "wrong"))

    def test_good_sign_in(self):
        response = self.client.post(
            "/sign-in",
            data={"username": "admin", "password": TEST_PASSWORD},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Servers", response.get_data(as_text=True))

    def test_bad_sign_in_is_generic(self):
        response = self.client.post(
            "/sign-in",
            data={"username": "admin", "password": "wrong"},
        )
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sign-in failed.", page)
        self.assertNotIn("wrong", page)

    def test_sign_out(self):
        self.client.post(
            "/sign-in",
            data={"username": "admin", "password": TEST_PASSWORD},
        )
        response = self.client.post("/sign-out", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/sign-in", response.headers["Location"])
        servers = self.client.get("/servers", follow_redirects=False)
        self.assertEqual(servers.status_code, 302)

    def test_unsigned_user_is_redirected(self):
        response = self.client.get("/servers", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/sign-in", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()

# Server monitor (demo)

Local demo UI for Linux servers you add. Opening the server list or a server page runs a fixed read-only SSH check for CPU, memory, network, and listening ports. The browser has no command box. The demo accepts the server host key on first connection.

Sign in as `admin`. Set `ADMIN_PASSWORD` in the environment before starting. The app stores only a PBKDF2 hash in `instance/admin.json` and will not start if the variable is missing. To reset the password, set a new `ADMIN_PASSWORD` and start the app again.

Saved servers are written to `instance/servers.json` on this machine. That file is gitignored. The list shows the name, host, and status. It does not show the key path or the SSH password.

Add Server fields: display name, SSH host, SSH port, SSH user, private key path, and SSH password. Provide a key path, a password, or both. For this demo, use host `127.0.0.1` and port `22`.

The detail page shows the latest CPU, memory, network in, network out, and listening ports. It refreshes about every 5 seconds. Charts cover the last 5 minutes in memory and reset when the app stops. High CPU and High memory badges appear at 80%. A failed check keeps the last good sample and shows a short status, not a stack trace.

The app listens on `127.0.0.1` only.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ADMIN_PASSWORD='choose-a-password' python app.py
```

Open http://127.0.0.1:5003

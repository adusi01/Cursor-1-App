# Implementation TODO

Local demo from [requirements.md](requirements.md). Do one section at a time. Each section is a small change, includes a security check, and updates the docs. The app runs only on this machine. There is no hosted deploy.

## 1. Project initialization and basic UI

- [x] Add a Python virtual environment, `requirements.txt` with Flask, and a one-file Flask app.
- [x] Add a base page layout and plain CSS: readable type, simple header, and a dashboard-style content area.
- [x] Add placeholder pages for Sign in, Servers, Add Server, and Server detail. Use static sample text. No sign-in logic and no live metrics yet.
- [x] Ignore `.venv/`, `__pycache__/`, and local secret files in `.gitignore`.
- [x] Security: bind the dev server to `127.0.0.1` only. Do not put passwords, keys, or a Flask secret in the repo.
- [x] Docs: add a short `README.md` with the local start steps (venv, install, run on localhost).

## 2. Sign-in and unit tests

- [x] Read the admin password from an environment variable. Refuse to start if it is missing.
- [x] Hash it with PBKDF2 or bcrypt and keep only the hash in a local file outside git.
- [x] Add sign-in for username `admin`, a session, and sign-out. Wrong username or password shows one generic message.
- [x] Redirect Servers, Add Server, and Server detail to sign-in when there is no session.
- [x] Add unit tests for the hash check, a good sign-in, a bad sign-in, sign-out, and an unsigned redirect.
- [x] Security: session cookie is HTTP-only. The hash file and the password never appear in templates, logs, or test output. Tests set the password themselves and do not use a real one.
- [x] Docs: note the environment variable and the local hash file in `README.md`.

## 3. GitHub Actions

- [ ] Add `.github/workflows/ci.yml` that runs on push and pull request.
- [ ] The workflow installs dependencies and runs the unit tests on Python 3. No deploy job.
- [ ] Security: the workflow has no secrets and does not start the app on a public address. Do not echo the admin password.
- [ ] Docs: add one line to `README.md` that CI is GitHub Actions running the tests, and that running the demo stays local.

## 4. Server list

- [x] Store servers in a local JSON file under a gitignored directory.
- [x] Show the signed-in server list: name, host, and an empty status when no check has run.
- [x] Show an empty state with a link to Add Server.
- [x] Security: the list is still behind sign-in. Render names and hosts as text, not HTML.
- [x] Docs: note the JSON file path in `README.md`.

## 5. Add server

- [x] Add a form for display name, SSH host, SSH port, SSH user, and private key path.
- [x] Default the port to `22`. For this demo, the host to enter is `127.0.0.1`.
- [x] Validate before save: required fields, port 1–65535, host is an IP or hostname, key path has no newline. Reject anything else.
- [x] Do not open SSH yet. Saving only writes the registration.
- [x] Add unit tests for a valid save and for one rejected field.
- [x] Security: do not collect an SSH password. Do not show the key file contents. Do not pass form input to a shell.
- [x] Docs: list the form fields and the `127.0.0.1` demo path in `README.md`.

## 6. Remove server

- [ ] Add Remove on the server list. It deletes that registration only.
- [ ] Confirm in the UI before delete. After delete, return to the list.
- [ ] Add a unit test that the server is gone and other records stay.
- [ ] Security: only a signed-in session can remove. The id in the form is checked against the saved list.
- [ ] Docs: state that Remove does not change the host, only the saved row.

## 7. Parse metrics

- [x] Add parsers for fixed sample output: CPU percent, memory percent, network byte counters, and listening TCP ports (port, bind address, process name).
- [x] Cover the parsers with unit tests and checked-in text fixtures. No SSH in these tests.
- [x] Security: parsers accept only the expected command output. They do not run commands and do not evaluate text as code.
- [x] Docs: name the four values the detail page will show.

## 8. Fixed read-only SSH commands

- [x] Add one module that runs a fixed command list over SSH with the saved key path. No operator-typed command.
- [x] On failure, return a failed status and no stack trace to the page.
- [x] Add unit tests with a fake SSH client for success and for connection failure.
- [x] Security: arguments are the host, port, user, and key path only. The command strings are constants. Do not log the key path in an error page.
- [x] Docs: state that the app uses a fixed read-only command list and never opens a shell in the browser.

## 9. Show the latest sample

- [x] On the server list and detail page, show the latest CPU, memory, network rates, status, and listening ports.
- [x] Keep the last good sample if a later check fails, and show the failed status.
- [x] Add a unit test that a failed check does not wipe the last good sample.
- [x] Security: pages stay read-only. No command box, restart, or kill control.
- [x] Docs: describe the list columns and the detail fields in `README.md`.

## 10. Live charts

- [x] Keep about five minutes of samples in memory, one sample per refresh, dropped on process exit.
- [x] Refresh the open detail page about every 5 seconds.
- [x] Draw simple charts for CPU, memory, and network from those samples.
- [x] Add a unit test that the buffer drops samples older than the window and clears on a new process store.
- [x] Security: refresh only reads. It does not accept a metric payload from the browser.
- [x] Docs: note that charts are in memory and reset when the app stops.

## 11. High-usage badges

- [x] Show High CPU at or above 80% CPU, and High memory at or above 80% memory.
- [x] Leave network and ports without badges.
- [x] Add unit tests just below and at 80% for each metric.
- [x] Security: badges are display-only. They do not call any other system.
- [x] Docs: record the two fixed thresholds in `README.md`.

## 12. Demo check

- [ ] Walk the local path: start on localhost, sign in, add `127.0.0.1`, open detail, see metrics, charts, ports, and a badge when usage is high.
- [ ] Confirm a bad key shows a failed status and not a stack trace.
- [ ] Confirm unsigned users never see the monitoring pages.
- [ ] Security: search the repo for the admin password, private keys, and the hash file. None of those files should be tracked.
- [ ] Docs: keep `README.md` to the five local steps from the PRD. CI still runs tests only.

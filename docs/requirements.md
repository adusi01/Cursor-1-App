# Demo Server Monitoring — Requirements

## Summary

A small local web app shows live CPU, memory, network, and listening-port details for the Linux machine it runs on. Internal staff open the page instead of signing in to the server themselves.

This is a demo. It runs on the same machine as Cursor, monitors that machine only, and is meant to be started with a few local steps.

## Problem

L1, L2, and L3 staff in infrastructure and application development must log in to a server to see current memory, CPU, network, and port usage. That is slow for a simple health check and gives people a shell they do not need.

## Users

All of these groups use the same demo account. The demo does not separate roles.

- Infrastructure L1, L2, and L3
- Application development

They need a quick read of current host health. They do not change the host from this app.

## Goals

- Show current CPU, memory, network, and listening ports for this machine.
- Keep the monitoring screens read-only.
- Sign in as `admin` with a password checked against a hash.
- Register the machine through an Add Server form that stores SSH connection details.
- Show a short live chart while the page is open.
- Mark high CPU or memory on screen.

## Non-goals

- Monitoring other machines, clouds, or containers.
- User management, roles, or more than one account.
- Email, chat, tickets, or saved alert history.
- Metrics that survive an app restart.
- A shell, file editor, or any control that changes the server.
- Windows or other operating systems.

## Demo constraints

- One Linux host: the machine where the app is running.
- Add Server registers that host. The demo path is SSH to `127.0.0.1`.
- The app listens on localhost only.
- Charts and samples live in memory and are discarded when the app stops.
- Setup stays local: Python, a virtual environment, Flask, and an SSH login to this machine.

## Features

### 1. Read-only monitoring UI

After sign-in, the operator can look at servers and metrics but cannot edit them.

- Server list shows each saved server, whether the last SSH check worked, CPU, memory, and a high-usage badge if one applies.
- Server detail shows the latest CPU percent, memory percent, network rates, and listening ports.
- CPU, memory, and network each have a simple chart of samples from the last few minutes.
- The page refreshes on its own about every 5 seconds while it is open.
- Numbers are display-only. There is no command box and no button that restarts a service or kills a process.
- Add Server and Remove Server are the only controls that change app data. Remove only deletes the saved registration.

### 2. Sign in

- Username is `admin`.
- The password is never stored in plaintext. The app stores a password hash (PBKDF2 or bcrypt) and checks the sign-in form against that hash.
- The operator sets the password in a local environment variable. On startup the app hashes it and keeps the hash in a local file outside git.
- If that variable is missing, the app does not start.
- A successful sign-in creates a session. Sign out ends it.
- Wrong username or password shows a generic failure message.
- Monitoring pages redirect to sign-in when there is no session.

### 3. Add a Linux server

The form collects:

- Display name
- SSH host (for this demo, `127.0.0.1`)
- SSH port (default `22`)
- SSH user
- Path to a private key on this machine

The private key is used only to connect. The UI never shows the key file. Passwords for SSH are not collected.

The app connects with a fixed set of read-only commands and parses their output. The operator cannot type a command. The commands read CPU, memory, network counters, and listening TCP ports (port, bind address, and process name when the SSH user is allowed to see it).

A failed connection is shown as a status on the server row. The last good sample stays visible until a newer one arrives.

## High-usage badges

Badges are visual only. Nothing is sent outside the app.

| Metric | Badge |
| --- | --- |
| CPU at or above 80% | High CPU |
| Memory at or above 80% | High memory |

Thresholds are fixed for the demo. Network and ports do not raise badges.

## Screens

1. **Sign in** — username, password, submit.
2. **Servers** — list, link to detail, Add Server, Remove.
3. **Add Server** — the fields in Feature 3.
4. **Server detail** — status, latest metrics, badges, charts, listening-port table.

The layout should be a clear dashboard: readable type, obvious status, and tables that scan without training. Flask server-rendered pages and plain CSS are enough. No separate front-end build.

## Tech

- Python 3
- Flask
- Server-rendered HTML and CSS
- SSH client library for the fixed read-only commands
- In-memory samples for the open page (about 5 minutes, one sample per refresh)

## Local run

Expected shape, not a full setup guide:

1. Create a virtual environment and install Flask and the SSH library.
2. Set the admin password in the environment.
3. Use an SSH key that can log in to this machine as the chosen user.
4. Start the Flask app so it is reachable only on localhost.
5. Sign in, add `127.0.0.1`, and open the server page.

## Acceptance

- Unsigned users cannot open the server list or detail page.
- `admin` can sign in when the password matches the stored hash, and can sign out.
- A plaintext password does not appear in the repo or in the local hash file.
- Adding `127.0.0.1` with a working key shows CPU, memory, network, and listening ports from this machine.
- Charts move while the detail page stays open and reset after a restart.
- CPU or memory at or above 80% shows the matching badge.
- The detail page has no control that runs an operator-typed command or changes the host.
- A bad key or a refused SSH connection shows a failed status instead of a stack trace.

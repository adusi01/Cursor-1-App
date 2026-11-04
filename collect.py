"""Collect host metrics with a fixed read-only command list."""

import socket
import time

import paramiko

import metrics

CPU_COMMAND = "cat /proc/stat"
MEM_COMMAND = "cat /proc/meminfo"
NET_COMMAND = "cat /proc/net/dev"
PORT_COMMAND = "ss -ltnp"
ALLOWED_COMMANDS = frozenset({CPU_COMMAND, MEM_COMMAND, NET_COMMAND, PORT_COMMAND})
WINDOW_SECONDS = 300


class CollectionError(Exception):
    """A safe message that can be shown on the page."""


class SampleStore:
    def __init__(self):
        self._latest = {}
        self._history = {}

    def success(self, server_id, sample, now=None):
        now = time.time() if now is None else now
        stored = dict(sample)
        stored["ok"] = True
        stored["status"] = "OK"
        stored["error"] = ""
        self._trim(server_id, now)
        self._history.setdefault(server_id, []).append({
            "t": now,
            "cpu": stored.get("cpu_percent"),
            "memory": stored.get("memory_percent"),
            "net_in": stored.get("net_in_bps"),
            "net_out": stored.get("net_out_bps"),
        })
        stored["history"] = list(self._history[server_id])
        self._latest[server_id] = stored
        return stored

    def failure(self, server_id, message, now=None):
        now = time.time() if now is None else now
        self._trim(server_id, now)
        previous = self._latest.get(server_id)
        if previous:
            stored = dict(previous)
            stored["ok"] = False
            stored["status"] = message
            stored["error"] = message
            stored["history"] = list(self._history.get(server_id, []))
            return stored
        return {
            "ok": False,
            "status": message,
            "error": message,
            "cpu_percent": None,
            "memory_percent": None,
            "net_in_bps": None,
            "net_out_bps": None,
            "ports": [],
            "history": [],
        }

    def _trim(self, server_id, now):
        points = self._history.get(server_id, [])
        self._history[server_id] = [point for point in points if now - point["t"] <= WINDOW_SECONDS]


STORE = SampleStore()


def check_server(server, collect_fn=None, store=None):
    sample_store = store or STORE
    collect = collect_fn or collect_live
    try:
        sample = collect(server)
    except CollectionError as exc:
        return sample_store.failure(server["id"], str(exc))
    except Exception:
        return sample_store.failure(server["id"], "SSH check failed.")
    return sample_store.success(server["id"], sample)


def collect_live(server):
    client = connect(server)
    try:
        return collect_with(lambda command: exec_allowed(client, command), time.sleep)
    finally:
        client.close()


def collect_with(run, pause):
    cpu_first = metrics.parse_cpu(run(CPU_COMMAND))
    memory = metrics.parse_memory(run(MEM_COMMAND))
    net_first = metrics.parse_net(run(NET_COMMAND))
    ports = metrics.parse_ports(run(PORT_COMMAND))
    started = time.monotonic()
    pause(0.5)
    cpu_second = metrics.parse_cpu(run(CPU_COMMAND))
    net_second = metrics.parse_net(run(NET_COMMAND))
    elapsed = max(time.monotonic() - started, 0.1)
    received, sent = metrics.rates(net_first, net_second, elapsed)
    return {
        "cpu_percent": metrics.cpu_percent(cpu_first, cpu_second),
        "memory_percent": memory,
        "net_in_bps": received,
        "net_out_bps": sent,
        "ports": ports,
    }


def connect(server):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "hostname": server.get("host") or "",
        "port": int(server.get("port") or 22),
        "username": server.get("user") or "",
        "timeout": 8,
        "banner_timeout": 8,
        "auth_timeout": 8,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if server.get("key_path"):
        kwargs["key_filename"] = server["key_path"]
    if server.get("ssh_password"):
        kwargs["password"] = server["ssh_password"]
    try:
        client.connect(**kwargs)
    except paramiko.AuthenticationException:
        client.close()
        raise CollectionError("SSH authentication failed.")
    except FileNotFoundError:
        client.close()
        raise CollectionError("SSH key could not be read.")
    except (paramiko.SSHException, socket.error, OSError):
        client.close()
        raise CollectionError("SSH connection failed.")
    return client


def exec_allowed(client, command):
    if command not in ALLOWED_COMMANDS:
        raise CollectionError("SSH check failed.")
    _stdin, stdout, _stderr = client.exec_command(command, timeout=8)
    output = stdout.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if code != 0 and command != PORT_COMMAND:
        raise CollectionError("SSH check failed.")
    return output


def present(server, sample):
    history = sample.get("history") or []
    return {
        "id": server.get("id", ""),
        "name": server.get("name", ""),
        "host": server.get("host", ""),
        "port": server.get("port", ""),
        "user": server.get("user", ""),
        "status": sample.get("status") or "Not checked",
        "error": sample.get("error") or "",
        "cpu": metrics.format_percent(sample.get("cpu_percent")),
        "memory": metrics.format_percent(sample.get("memory_percent")),
        "net_in": metrics.format_rate(sample.get("net_in_bps")),
        "net_out": metrics.format_rate(sample.get("net_out_bps")),
        "ports": sample.get("ports") or [],
        "high_cpu": metrics.high_cpu(sample.get("cpu_percent")),
        "high_memory": metrics.high_memory(sample.get("memory_percent")),
        "cpu_points": metrics.chart_points([point["cpu"] for point in history]),
        "memory_points": metrics.chart_points([point["memory"] for point in history]),
        "net_points": metrics.chart_points([
            (point["net_in"] or 0) + (point["net_out"] or 0) for point in history
        ]),
    }

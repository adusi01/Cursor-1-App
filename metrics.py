"""Parse fixed read-only command output. This module does not run commands."""

import re

_PROCESS = re.compile(r'\(\("([^"]+)"')


def parse_cpu(text):
    for line in text.splitlines():
        if line.startswith("cpu "):
            parts = [int(piece) for piece in line.split()[1:]]
            idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
            return sum(parts), idle
    raise ValueError("cpu line missing")


def cpu_percent(first, second):
    total = second[0] - first[0]
    idle = second[1] - first[1]
    if total <= 0:
        return 0.0
    used = (total - idle) / total * 100
    return max(0.0, min(100.0, used))


def parse_memory(text):
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        numbers = rest.split()
        if not numbers or not numbers[0].isdigit():
            continue
        values[key] = int(numbers[0])
    total = values.get("MemTotal")
    available = values.get("MemAvailable", values.get("MemFree"))
    if not total or available is None:
        raise ValueError("memory fields missing")
    used = (total - available) / total * 100
    return max(0.0, min(100.0, used))


def parse_net(text):
    received = 0
    sent = 0
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        if name.strip() == "lo":
            continue
        parts = rest.split()
        if len(parts) < 9 or not parts[0].isdigit() or not parts[8].isdigit():
            continue
        received += int(parts[0])
        sent += int(parts[8])
    return received, sent


def rates(first, second, elapsed):
    elapsed = elapsed if elapsed > 0 else 0.1
    received = max(0, second[0] - first[0]) / elapsed
    sent = max(0, second[1] - first[1]) / elapsed
    return received, sent


def parse_ports(text):
    ports = []
    for line in text.splitlines():
        if not line.strip().startswith("LISTEN"):
            continue
        tokens = line.split()
        if len(tokens) < 5:
            continue
        address, port = _split_address(tokens[3])
        if not port.isdigit():
            continue
        match = _PROCESS.search(line)
        ports.append({
            "address": address,
            "port": port,
            "process": match.group(1) if match else "",
        })
    return ports


def high_cpu(percent):
    return percent is not None and percent >= 80


def high_memory(percent):
    return percent is not None and percent >= 80


def format_percent(value):
    if value is None:
        return "—"
    return f"{value:.0f}%"


def format_rate(value):
    if value is None:
        return "—"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} MB/s"
    if value >= 1000:
        return f"{value / 1000:.1f} KB/s"
    return f"{value:.0f} B/s"


def chart_points(values, width=280, height=80):
    numbers = [value for value in values if value is not None]
    if not numbers:
        return ""
    if len(numbers) == 1:
        numbers = [numbers[0], numbers[0]]
    peak = max(numbers) or 1
    step = width / (len(numbers) - 1)
    coords = []
    for index, value in enumerate(numbers):
        x_pos = index * step
        y_pos = height - (value / peak) * (height - 4) - 2
        coords.append(f"{x_pos:.1f},{y_pos:.1f}")
    return " ".join(coords)


def _split_address(token):
    if token.startswith("[") and "]:" in token:
        host, port = token.rsplit("]:", 1)
        return host + "]", port
    if ":" in token:
        host, port = token.rsplit(":", 1)
        return host, port
    return token, ""

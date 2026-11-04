import unittest

import metrics
from collect import (
    ALLOWED_COMMANDS,
    CPU_COMMAND,
    MEM_COMMAND,
    NET_COMMAND,
    PORT_COMMAND,
    CollectionError,
    SampleStore,
    collect_with,
    exec_allowed,
    present,
)

CPU_FIRST = "cpu  100 0 50 850 0 0 0 0 0 0\n"
CPU_SECOND = "cpu  200 0 100 1650 0 0 0 0 0 0\n"
MEM_TEXT = "MemTotal: 1000000 kB\nMemAvailable: 400000 kB\n"
NET_FIRST = "eth0: 1000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n lo: 9 0 0 0 0 0 0 0 9 0 0 0 0 0 0 0\n"
NET_SECOND = "eth0: 6000 0 0 0 0 0 0 0 4000 0 0 0 0 0 0 0\n lo: 9 0 0 0 0 0 0 0 9 0 0 0 0 0 0 0\n"
PORT_TEXT = 'LISTEN 0 128 127.0.0.1:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))\nLISTEN 0 128 [::]:22 [::]:*\n'


class ParserTests(unittest.TestCase):
    def test_cpu_memory_network_and_ports(self):
        cpu = metrics.cpu_percent(metrics.parse_cpu(CPU_FIRST), metrics.parse_cpu(CPU_SECOND))
        self.assertAlmostEqual(cpu, 15.789, places=2)
        self.assertAlmostEqual(metrics.parse_memory(MEM_TEXT), 60.0)
        received, sent = metrics.rates(metrics.parse_net(NET_FIRST), metrics.parse_net(NET_SECOND), 1)
        self.assertEqual(received, 5000)
        self.assertEqual(sent, 2000)
        ports = metrics.parse_ports(PORT_TEXT)
        self.assertEqual(ports[0]["port"], "22")
        self.assertEqual(ports[0]["process"], "sshd")
        self.assertEqual(ports[1]["address"], "[::]")
        self.assertEqual(ports[1]["process"], "")

    def test_badges(self):
        self.assertFalse(metrics.high_cpu(79.9))
        self.assertTrue(metrics.high_cpu(80))
        self.assertFalse(metrics.high_memory(79.9))
        self.assertTrue(metrics.high_memory(80))


class CollectTests(unittest.TestCase):
    def test_fixed_commands_and_success(self):
        outputs = {
            CPU_COMMAND: [CPU_FIRST, CPU_SECOND],
            MEM_COMMAND: [MEM_TEXT],
            NET_COMMAND: [NET_FIRST, NET_SECOND],
            PORT_COMMAND: [PORT_TEXT],
        }

        def run(command):
            self.assertIn(command, ALLOWED_COMMANDS)
            return outputs[command].pop(0)

        sample = collect_with(run, lambda _seconds: None)
        self.assertAlmostEqual(sample["cpu_percent"], 15.789, places=2)
        self.assertEqual(sample["memory_percent"], 60)
        self.assertEqual(len(sample["ports"]), 2)

    def test_rejected_command_is_not_run(self):
        class FakeClient:
            def exec_command(self, command, timeout=8):
                raise AssertionError(command)

        with self.assertRaises(CollectionError):
            exec_allowed(FakeClient(), "rm -rf /")

    def test_failure_keeps_last_good_sample(self):
        store = SampleStore()
        good = {
            "cpu_percent": 12,
            "memory_percent": 40,
            "net_in_bps": 10,
            "net_out_bps": 5,
            "ports": [{"address": "127.0.0.1", "port": "22", "process": "sshd"}],
        }
        store.success("host", good, now=1000)
        failed = store.failure("host", "SSH connection failed.", now=1005)
        self.assertEqual(failed["cpu_percent"], 12)
        self.assertEqual(failed["status"], "SSH connection failed.")
        self.assertEqual(failed["ports"][0]["port"], "22")

    def test_history_drops_old_samples(self):
        store = SampleStore()
        sample = {"cpu_percent": 1, "memory_percent": 2, "net_in_bps": 3, "net_out_bps": 4, "ports": []}
        store.success("host", sample, now=1000)
        kept = store.success("host", sample, now=1401)
        self.assertEqual(len(kept["history"]), 1)
        self.assertEqual(kept["history"][0]["t"], 1401)
        self.assertEqual(SampleStore().success("other", sample, now=1)["history"][0]["t"], 1)

    def test_present_hides_secrets(self):
        server = {
            "id": "1",
            "name": "box",
            "host": "127.0.0.1",
            "port": 22,
            "user": "demo",
            "key_path": "/secret/key",
            "ssh_password": "secret-pass",
        }
        view = present(server, {"status": "Not checked", "error": "", "ports": [], "history": []})
        rendered = str(view)
        self.assertNotIn("secret-pass", rendered)
        self.assertNotIn("/secret/key", rendered)


if __name__ == "__main__":
    unittest.main()

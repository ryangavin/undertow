import unittest
from metrics import cpu_counters, cpu_percent, memory, network, rates


class MetricScenarios(unittest.TestCase):
    def test_cpu_excludes_guest_double_counting(self):
        previous = cpu_counters("cpu 10 0 10 80 0 0 0 0 5 0")
        current = cpu_counters("cpu 20 0 20 160 0 0 0 0 15 0")
        self.assertAlmostEqual(cpu_percent(previous, current), 20)

    def test_memory_uses_available_not_free(self):
        self.assertEqual(memory("MemTotal: 100 kB\nMemAvailable: 60 kB\nMemFree: 10 kB\n"),
                         {"mem": 40960, "memTotal": 102400, "swap": 0})

    def test_network_accounts_for_actual_elapsed_time(self):
        self.assertEqual(rates((100, 200), (400, 260), 3), (100, 20))

    def test_network_reset_and_new_interfaces_are_gaps(self):
        self.assertEqual(rates((100, 200), (50, 260), 1), (None, None))
        self.assertEqual(rates(None, (50, 260), 1), (None, None))

    def test_network_parses_receive_and_transmit_bytes(self):
        self.assertEqual(network("header\nheader\n eth0: 123 0 0 0 0 0 0 0 456 0 0 0 0 0 0 0"), {"eth0": (123, 456)})


if __name__ == "__main__":
    unittest.main()

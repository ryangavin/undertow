import struct
import unittest
from amd_metrics import decode
from metrics import cpu_threads


class AmdScenarios(unittest.TestCase):
    def fixture(self):
        data = bytearray(264)
        struct.pack_into("<HBB", data, 0, 264, 3, 0)
        return data

    def test_power_domains_and_units_remain_distinct(self):
        data = self.fixture()
        for offset, mw in [(112, 71000), (120, 70000), (124, 20000), (132, 45000)]:
            struct.pack_into("<I", data, offset, mw)
        struct.pack_into("<H", data, 136, 3250)
        struct.pack_into("<H", data, 190, 4000)
        sample = decode(data)
        self.assertEqual([sample[k] for k in ("socketPower", "apuPower", "gpuPower", "cpuPower")], [71, 70, 20, 45])
        self.assertEqual(sample["corePower"][0], 3.25)
        self.assertEqual(sample["coreClock"][0], 4000)

    def test_unknown_or_short_abi_is_not_interpreted(self):
        data = self.fixture()
        self.assertEqual(decode(data[:200]), {})
        data[3] = 1
        self.assertEqual(decode(data), {})
        self.assertEqual(decode(b""), {})

    def test_unavailable_is_distinct_from_zero(self):
        data = self.fixture()
        struct.pack_into("<I", data, 124, 0xffffffff)
        struct.pack_into("<H", data, 136, 0xffff)
        sample = decode(data)
        self.assertIsNone(sample["gpuPower"])
        self.assertIsNone(sample["corePower"][0])
        self.assertEqual(sample["cpuPower"], 0)

    def test_new_logical_cpu_has_no_invented_load(self):
        self.assertEqual(cpu_threads({}, {"cpu7": (100, 50)}), [None])

    def test_each_logical_cpus_load_is_a_plain_number_in_order(self):
        previous = {"cpu0": (100, 50), "cpu1": (100, 100)}
        current = {"cpu0": (200, 50), "cpu1": (200, 150)}
        self.assertEqual(cpu_threads(previous, current), [100, 50])


if __name__ == "__main__":
    unittest.main()

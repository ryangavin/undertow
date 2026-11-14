import unittest
from contributors import MIB, snapshot


def app(pid, name, cpu=0, mem=0, gpu=0, gmem=0, program=None):
    return {"pid": pid, "name": name, "program": program or name, "kind": "user", "cpu": cpu, "mem": mem, "gpu": gpu, "gmem": gmem}


class ContributorScenarios(unittest.TestCase):
    def test_figures_are_in_the_units_of_the_graph_they_are_drawn_in(self):
        record = snapshot(100.0, [app(1, "floorp", cpu=320, mem=512 * MIB, gpu=40, gmem=256 * MIB)], [], cores=32,
                          cpu_power=20, gpu_power=10)
        # 320% of one core on 32 is a tenth of the machine; it used all the CPU and GPU time, so all the watts.
        self.assertEqual(record["a"]["1"], ["floorp", "floorp", "user", 10.0, 40.0, 512.0, 256.0, 20.0, 10.0])

    def test_power_is_shared_out_by_each_apps_part_of_the_cpu_and_gpu_time(self):
        record = snapshot(0, [app(1, "a", cpu=300, gpu=10), app(2, "b", cpu=100, gpu=30)], [], cores=4,
                          cpu_power=40, gpu_power=8)
        self.assertEqual((record["a"]["1"][7], record["a"]["2"][7]), (30.0, 10.0))
        self.assertEqual((record["a"]["1"][8], record["a"]["2"][8]), (2.0, 6.0))

    def test_without_a_power_reading_no_watts_are_made_up(self):
        record = snapshot(0, [app(1, "a", cpu=50)], [], cores=4)
        self.assertEqual(record["a"]["1"][7:], [0, 0])

    def test_all_instances_of_a_name_add_up_to_one_name(self):
        record = snapshot(0, [app(1, "claude", cpu=40, mem=10 * MIB), app(2, "claude", cpu=60, mem=30 * MIB)], [], cores=1)
        self.assertEqual(record["n"]["claude"][3:6], [100.0, 0.0, 40.0])

    def test_only_the_busiest_are_kept_but_a_busy_name_keeps_its_busiest_instances(self):
        apps = [app(i, f"tool{i}", cpu=100 - i, mem=10 * MIB) for i in range(1, 30)]
        # Each zsh is idle and smaller than any tool, but together they hold the most memory.
        apps += [app(100 + i, "zsh", mem=MIB) for i in range(40)]
        apps += [app(200, "zsh", mem=2 * MIB, cpu=0.5)]
        record = snapshot(0, apps, [], cores=1, keep=3, per_name=2)
        self.assertEqual(set(record["n"]), {"tool1", "tool2", "tool3", "zsh"})
        self.assertIn("200", record["a"])
        self.assertNotIn("4", record["a"])
        self.assertEqual(sum(1 for pid in record["a"] if int(pid) >= 100), 2)

    def test_agents_are_named_by_harness_and_project_and_told_apart_by_title(self):
        agents = [{"pid": 7, "name": "claude", "kind": "claude", "project": "satoramoto/zen-flow", "title": "Sidebar fix", "cpu": 10, "mem": 0},
                  {"pid": 8, "name": "claude", "kind": "claude", "project": "satoramoto/zen-flow", "title": "Story audit", "cpu": 5, "mem": 0},
                  {"pid": 9, "name": "opencode.exe", "kind": "opencode", "project": "satoramoto/zen", "title": "", "cpu": 0, "mem": 0}]
        record = snapshot(0, [], agents, cores=1)
        self.assertEqual([record["g"][pid][0] for pid in ("7", "8", "9")],
                         ["claude · zen-flow · Sidebar fix", "claude · zen-flow · Story audit", "opencode · zen"])


if __name__ == "__main__":
    unittest.main()

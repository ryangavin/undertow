import unittest
from processes import PAGE_BYTES, TICKS_PER_SECOND, owners, parse_io, parse_stat, process_rows, programs, table


def stat(name, parent, ticks=0, started=1, pages=0, threads=1, reaped=0):
    return (ticks, started, pages, name, parent, threads, reaped)


def plain(pid, name):
    return name


# What one core can do in the two seconds the helper below assumes by default.
ONE_CORE = 2 * TICKS_PER_SECOND


def rows(previous, found, running, storage=None, earlier_storage=None, elapsed_seconds=2, busy_ticks=None):
    return table((previous, earlier_storage or {}), (found, storage or {}), running, elapsed_seconds,
                 busy_ticks=busy_ticks, name=plain)


def cpu_of(result, name):
    return next(row["cpu"] for row in result if row["name"] == name)


class ProcessScenarios(unittest.TestCase):
    def test_a_name_with_spaces_and_parentheses_is_read_whole(self):
        line = "4242 (Web (Content) x) S 100 4242 4242 0 -1 4194560 9 0 0 0 30 12 7 3 20 0 5 0 777 123456 2500 1844"
        self.assertEqual(parse_stat(line), (42, 777, 2500, "Web (Content) x", "100", 5, 10))

    def test_storage_bytes_are_reads_plus_writes(self):
        text = "rchar: 9\nwchar: 9\nsyscr: 1\nsyscw: 1\nread_bytes: 4096\nwrite_bytes: 8192\ncancelled_write_bytes: 0\n"
        self.assertEqual(parse_io(text), 12288)

    def test_a_process_seen_before_is_not_asked_about_again(self):
        # No such pids exist, so a fresh question to the kernel falls back to the name.
        found = {"999999991": stat("kept", "1", started=4), "999999992": stat("reused", "1", started=8), "999999993": stat("new", "1")}
        known = {"999999991": (4, "/usr/bin/kept"), "999999992": (3, "/usr/bin/older-owner-of-this-pid")}
        self.assertEqual(programs(found, known), {"999999991": (4, "/usr/bin/kept"), "999999992": (8, "reused"), "999999993": (1, "new")})

    def test_a_browsers_helpers_count_as_the_browser(self):
        found = {"1": stat("systemd", "0"), "10": stat("floorp", "1"),
                 "11": stat("Isolated Web Co", "10"), "12": stat("Web Content", "11")}
        running = {"1": (1, "/usr/lib/systemd/systemd"), "10": (1, "/usr/lib/floorp/floorp"),
                   "11": (1, "/usr/lib/floorp/floorp"), "12": (1, "/usr/lib/floorp/floorp")}
        self.assertEqual(owners(found, running), {"1": "1", "10": "10", "11": "10", "12": "10"})

    def test_two_scripts_under_one_interpreter_stay_apart(self):
        found = {"5": stat("zsh", "1"), "20": stat("census", "5"), "21": stat("backup", "5")}
        running = {"5": (1, "/usr/bin/zsh"), "20": (1, "/usr/bin/python3.14"), "21": (1, "/usr/bin/python3.14")}
        self.assertEqual(owners(found, running), {"5": "5", "20": "20", "21": "21"})

    def test_an_app_is_one_row_summed_over_its_processes(self):
        previous = {"10": stat("floorp", "1", ticks=100), "11": stat("Web Content", "10", ticks=50),
                    "30": stat("quiet", "1", ticks=900)}
        found = {"10": stat("floorp", "1", ticks=130, pages=1000, threads=40), "11": stat("Web Content", "10", ticks=70, pages=500, threads=12),
                 "30": stat("quiet", "1", ticks=900, pages=10)}
        running = {"10": (1, "/usr/lib/floorp/floorp"), "11": (1, "/usr/lib/floorp/floorp"), "30": (1, "/usr/bin/quiet")}
        self.assertEqual(rows(previous, found, running), [
            {"pid": 10, "parent": 1, "name": "floorp", "program": "floorp", "kind": "user", "count": 2, "threads": 52,
             "cpu": 100 * 50 / ONE_CORE, "mem": 1500 * PAGE_BYTES, "disk": None, "time": round(200 / TICKS_PER_SECOND),
             "gpu": 0.0, "gmem": 0},
            {"pid": 30, "parent": 1, "name": "quiet", "program": "quiet", "kind": "user", "count": 1, "threads": 1,
             "cpu": 0.0, "mem": 10 * PAGE_BYTES, "disk": None, "time": round(900 / TICKS_PER_SECOND),
             "gpu": 0.0, "gmem": 0},
        ])

    def test_a_process_started_since_the_last_scan_counts_everything_it_used(self):
        previous = {"40": stat("old", "1", ticks=500, started=1)}
        found = {"40": stat("new", "1", ticks=20, started=9, pages=1), "41": stat("fresh", "1", ticks=10, started=9, pages=1)}
        running = {"40": (9, "new"), "41": (9, "fresh")}
        self.assertEqual([(row["name"], row["cpu"]) for row in rows(previous, found, running)],
                         [("new", 100 * 20 / ONE_CORE), ("fresh", 100 * 10 / ONE_CORE)])

    def test_disk_is_the_bytes_moved_per_second_since_the_last_scan(self):
        previous = {"7": stat("copy", "1", pages=1), "8": stat("helper", "7", pages=1)}
        found = {"7": stat("copy", "1", pages=1), "8": stat("helper", "7", pages=1), "9": stat("late", "7", pages=1, started=5)}
        running = {"7": (1, "copy"), "8": (1, "copy"), "9": (5, "copy")}
        result = rows(previous, found, running, earlier_storage={"7": 1000, "8": 500}, storage={"7": 5000, "8": 500, "9": 2000})
        self.assertEqual(result[0]["disk"], (4000 + 0 + 2000) // 2)

    def test_disk_is_unknown_for_someone_elses_app_not_zero(self):
        found = {"3": stat("rootd", "1", pages=1)}
        self.assertIsNone(rows({"3": stat("rootd", "1", pages=1)}, found, {"3": (1, "rootd")})[0]["disk"])

    def test_kernel_threads_that_did_nothing_are_left_out(self):
        previous = {"50": stat("kworker/1:0", "2", ticks=5), "51": stat("kswapd0", "2", ticks=5)}
        found = {"50": stat("kworker/1:0", "2", ticks=5), "51": stat("kswapd0", "2", ticks=9)}
        running = {"50": (1, "kworker/1:0"), "51": (1, "kswapd0")}
        self.assertEqual([row["name"] for row in rows(previous, found, running)], ["kswapd0"])

    def test_the_busiest_app_comes_first_and_memory_breaks_ties(self):
        found = {"2": stat("small", "1", pages=5), "3": stat("large", "1", pages=50), "4": stat("busy", "1", ticks=30, pages=1)}
        running = {pid: (1, entry[3]) for pid, entry in found.items()}
        previous = {"2": stat("small", "1"), "3": stat("large", "1"), "4": stat("busy", "1")}
        self.assertEqual([row["name"] for row in rows(previous, found, running)], ["busy", "large", "small"])

    def test_no_elapsed_time_gives_no_cpu_or_disk_rather_than_inventing_them(self):
        found = {"2": stat("app", "1", ticks=5, pages=1)}
        row = rows({}, found, {"2": (1, "app")}, storage={"2": 10}, elapsed_seconds=0)[0]
        self.assertIsNone(row["cpu"])
        self.assertIsNone(row["disk"])

    def test_cpu_counts_cores_the_way_top_does(self):
        # Three cores flat out reads 300%, not a share of the whole machine.
        previous = {"60": stat("encoder", "1", ticks=1000, pages=1)}
        found = {"60": stat("encoder", "1", ticks=1000 + 3 * ONE_CORE, pages=1, threads=3)}
        self.assertEqual(rows(previous, found, {"60": (1, "encoder")})[0]["cpu"], 300.0)

    def test_commands_too_brief_for_any_scan_count_for_the_process_that_ran_them(self):
        # The shell ran commands that started and finished between the scans:
        # 90 ticks the kernel added to it when it waited for them.
        previous = {"5": stat("zsh", "1", ticks=10, pages=1, reaped=400)}
        found = {"5": stat("zsh", "1", ticks=12, pages=1, reaped=490)}
        self.assertEqual(cpu_of(rows(previous, found, {"5": (1, "zsh")}), "zsh"), 100 * (2 + 90) / ONE_CORE)

    def test_a_long_running_process_that_ends_does_not_bring_its_whole_past_along(self):
        # The child had used 9000 ticks by the first scan and 30 more before it
        # ended; its parent's count of waited-for time grows by all 9030.
        previous = {"5": stat("make", "1", pages=1), "6": stat("cc1", "5", ticks=9000, pages=1)}
        found = {"5": stat("make", "1", pages=1, reaped=9030)}
        running = {"5": (1, "make"), "6": (1, "cc1")}
        self.assertEqual(cpu_of(rows(previous, found, running), "make"), 100 * 30 / ONE_CORE)

    def test_when_a_child_and_its_own_child_both_end_the_ancestor_still_running_gets_their_time_once(self):
        # sh (30 ticks, 5 waited for) and its gcc (20 ticks) were both running at
        # the first scan; sh used 10 more and gcc 7 more, then both ended, sh
        # waiting for gcc and make for sh: make's waited-for time grows by
        # sh's 40 + 5 + gcc's 27.
        previous = {"5": stat("make", "1", pages=1), "6": stat("sh", "5", ticks=30, pages=1, reaped=5),
                    "7": stat("gcc", "6", ticks=20, pages=1)}
        found = {"5": stat("make", "1", pages=1, reaped=72)}
        running = {"5": (1, "make"), "6": (1, "sh"), "7": (1, "gcc")}
        self.assertEqual(cpu_of(rows(previous, found, running), "make"), 100 * 17 / ONE_CORE)

    def test_a_process_adopted_after_its_parent_ended_does_not_credit_its_past_to_the_adopter(self):
        # A headless browser shuts down: node (50 ticks) ends first, so systemd
        # takes in chrome (5000 ticks) just before it too ends, 10 ticks later.
        # systemd's waited-for time grows by chrome's whole 5010; claude's by
        # node's 50 and the 5 it used since.
        previous = {"1652": stat("systemd", "1", pages=1), "100": stat("claude", "1652", pages=1),
                    "200": stat("node", "100", ticks=50, pages=1), "300": stat("chrome", "200", ticks=5000, pages=1)}
        found = {"1652": stat("systemd", "1", pages=1, reaped=5010), "100": stat("claude", "1652", pages=1, reaped=55)}
        running = {"1652": (1, "systemd"), "100": (1, "claude"), "200": (1, "node"), "300": (1, "chrome")}
        result = rows(previous, found, running)
        self.assertEqual((cpu_of(result, "systemd"), cpu_of(result, "claude")), (100 * 10 / ONE_CORE, 0.0))

    def test_when_the_parent_waits_for_its_child_before_ending_the_adopter_is_not_credited_either(self):
        # The same shutdown the other way round: node waited for chrome, then
        # claude for node, so claude's waited-for time holds all of both.
        previous = {"1652": stat("systemd", "1", pages=1), "100": stat("claude", "1652", pages=1),
                    "200": stat("node", "100", ticks=50, pages=1), "300": stat("chrome", "200", ticks=5000, pages=1)}
        found = {"1652": stat("systemd", "1", pages=1), "100": stat("claude", "1652", pages=1, reaped=5065)}
        running = {"1652": (1, "systemd"), "100": (1, "claude"), "200": (1, "node"), "300": (1, "chrome")}
        result = rows(previous, found, running)
        self.assertEqual((cpu_of(result, "claude"), cpu_of(result, "systemd")), (100 * 15 / ONE_CORE, 0.0))

    def test_a_process_seen_taking_in_an_orphan_counts_as_an_adopter(self):
        # herdr, two levels up, took in pid 401 when its parent 400 ended; 402,
        # a sibling, was taken in too and then ended. herdr is not credited
        # with 402's past, though zsh is the nearer ancestor.
        previous = {"90": stat("herdr", "1", pages=1), "95": stat("zsh", "90", pages=1), "400": stat("sh", "95", pages=1),
                    "401": stat("watch", "400", pages=1), "402": stat("render", "400", ticks=3000, pages=1)}
        found = {"90": stat("herdr", "1", pages=1, reaped=3004), "95": stat("zsh", "90", pages=1),
                 "401": stat("watch", "90", pages=1)}
        running = {"90": (1, "herdr"), "95": (1, "zsh"), "400": (1, "sh"), "401": (1, "watch"), "402": (1, "render")}
        self.assertEqual(cpu_of(rows(previous, found, running), "herdr"), 100 * 4 / ONE_CORE)

    def test_a_process_started_since_the_last_scan_counts_what_it_waited_for_too(self):
        found = {"8": stat("script", "1", ticks=4, started=9, pages=1, reaped=40)}
        self.assertEqual(cpu_of(rows({}, found, {"8": (9, "script")}), "script"), 100 * 44 / ONE_CORE)

    def test_no_app_reads_more_than_the_whole_machine_was_busy(self):
        # A process taken in by a new parent and ended there brings its whole
        # life to that parent, which no earlier scan can take off.
        previous = {"1652": stat("systemd", "1", pages=1)}
        found = {"1652": stat("systemd", "1", pages=1, reaped=50000)}
        result = rows(previous, found, {"1652": (1, "systemd")}, busy_ticks=400)
        self.assertEqual(cpu_of(result, "systemd"), 100 * 400 / ONE_CORE)

    def test_each_app_says_whether_it_is_the_kernels_another_users_or_the_users_own(self):
        found = {"2": stat("kthreadd", "0", pages=0, ticks=1), "77": stat("kworker/3:1", "2", ticks=4),
                 "800": stat("NetworkManager", "1", pages=9), "900": stat("zsh", "1", pages=9)}
        running = {"2": (1, "kthreadd"), "77": (1, "kworker/3:1"), "800": (1, "NetworkManager"), "900": (1, "/usr/bin/zsh")}
        kinds = {row["name"]: (row["kind"], row["program"]) for row in rows({}, found, running)}
        self.assertEqual(kinds, {"kthreadd": ("kernel", "kthreadd"), "kworker/3:1": ("kernel", "kworker/3:1"),
                                 "NetworkManager": ("system", "NetworkManager"), "zsh": ("user", "zsh")})

    def test_a_program_replaced_on_disk_keeps_its_plain_name(self):
        found = {"5": stat("herdr-core", "1", pages=1)}
        self.assertEqual(rows({}, found, {"5": (1, "/home/r/.local/bin/herdr-core (deleted)")})[0]["program"], "herdr-core")

    def test_gpu_use_is_summed_over_an_apps_processes(self):
        found = {"10": stat("floorp", "1", pages=1), "11": stat("RDD Process", "10", pages=1)}
        running = {"10": (1, "/usr/lib/floorp/floorp"), "11": (1, "/usr/lib/floorp/floorp")}
        result = table(({}, {}), (found, {}), running, 2, gpu={"10": (30.0, 300), "11": (12.5, 50)}, name=plain)
        self.assertEqual((result[0]["gpu"], result[0]["gmem"]), (42.5, 350))

    def test_the_process_tree_lists_each_process_with_its_parent_and_its_own_figures(self):
        previous = {"5": stat("zsh", "1", ticks=10, pages=1, reaped=100), "6": stat("node", "5", ticks=50, pages=2)}
        found = {"5": stat("zsh", "1", ticks=10, pages=1, reaped=160), "6": stat("node", "5", ticks=90, pages=2),
                 "2": stat("kthreadd", "0"), "70": stat("kworker/0:1", "2"), "71": stat("kworker/1:1", "2", ticks=3)}
        running = {"5": (1, "/usr/bin/zsh"), "6": (1, "/usr/bin/node"), "2": (1, "kthreadd"), "70": (1, "kworker/0:1"),
                   "71": (1, "kworker/1:1")}
        result = process_rows((previous, {}), (found, {}), running, 2, name=plain, command=lambda pid: "cmd " + pid)
        self.assertEqual([(row["pid"], row["parent"], row["name"], row["cpu"], row["cmd"]) for row in result], [
            (2, 0, "kthreadd", 0.0, ""), (5, 1, "zsh", 100 * 60 / ONE_CORE, "cmd 5"),
            (6, 5, "node", 100 * 40 / ONE_CORE, "cmd 6"), (71, 2, "kworker/1:1", 100 * 3 / ONE_CORE, "")])

    def test_command_lines_are_asked_for_once_per_process(self):
        asked = []
        def command(pid):
            asked.append(pid)
            return "cmd"
        found = {"5": stat("zsh", "1", pages=1, started=7)}
        cache = {}
        for _ in range(3):
            process_rows(({}, {}), (found, {}), {"5": (7, "/usr/bin/zsh")}, 2, name=plain, command=command, commands=cache)
        self.assertEqual(asked, ["5"])
        process_rows(({}, {}), ({}, {}), {}, 2, name=plain, command=command, commands=cache)
        self.assertEqual(cache, {})


if __name__ == "__main__":
    unittest.main()

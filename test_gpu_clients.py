import os
import tempfile
import unittest
from gpu_clients import Clients, parse_fdinfo

AMDGPU = """pos:\t0
flags:\t02100002
drm-driver:\tamdgpu
drm-client-id:\t{client}
drm-pdev:\t0000:c4:00.0
drm-memory-vram:\t{vram} KiB
drm-memory-gtt:\t2048 KiB
drm-memory-cpu:\t0 KiB
drm-engine-gfx:\t{gfx} ns
drm-engine-compute:\t{compute} ns
drm-engine-enc:\t999999999 ns
"""


def fdinfo(client, gfx=0, compute=0, vram=12):
    return AMDGPU.format(client=client, gfx=gfx, compute=compute, vram=vram)


class GpuClientScenarios(unittest.TestCase):
    def test_a_gpu_handle_gives_its_client_graphics_time_and_memory(self):
        self.assertEqual(parse_fdinfo(fdinfo(41, gfx=500, compute=25, vram=1024)), ("41", 525, 1024 * 1024 + 2048 * 1024))

    def test_a_handle_that_is_not_a_gpu_client_is_skipped(self):
        self.assertIsNone(parse_fdinfo("pos:\t0\nflags:\t02\nmnt_id:\t25\n"))

    def test_the_common_resident_memory_keys_are_read_when_the_driver_uses_them(self):
        text = "drm-client-id:\t7\ndrm-resident-vram:\t3 MiB\ndrm-resident-gtt:\t1 MiB\n"
        self.assertEqual(parse_fdinfo(text), ("7", 0, 4 * 1048576))

    def setUp(self):
        self.proc = tempfile.TemporaryDirectory()
        self.addCleanup(self.proc.cleanup)

    def handle(self, pid, fd, text, target="/dev/dri/renderD128"):
        for part in ("fd", "fdinfo"):
            os.makedirs(f"{self.proc.name}/{pid}/{part}", exist_ok=True)
        if not os.path.islink(f"{self.proc.name}/{pid}/fd/{fd}"):
            os.symlink(target, f"{self.proc.name}/{pid}/fd/{fd}")
        with open(f"{self.proc.name}/{pid}/fdinfo/{fd}", "w") as out:
            out.write(text)

    def test_busy_share_is_the_graphics_time_used_over_the_time_between_samples(self):
        clients = Clients(proc=self.proc.name)
        self.handle("300", "9", fdinfo(5, gfx=1_000_000_000))
        self.handle("300", "3", "pos:\t0\n", target="/home/r/notes.txt")
        self.assertEqual(clients.sample(10_000_000_000)["300"][0], 0.0)
        self.handle("300", "9", fdinfo(5, gfx=1_500_000_000))
        self.assertEqual(clients.sample(12_000_000_000)["300"][0], 25.0)

    def test_a_client_shared_by_two_processes_counts_once_for_the_lower_pid(self):
        clients = Clients(proc=self.proc.name)
        self.handle("40", "6", fdinfo(8, vram=100))
        self.handle("41", "6", fdinfo(8, vram=100))
        result = clients.sample(1)
        self.assertEqual(sorted(result), ["40"])

    def test_one_process_holding_several_clients_adds_them_up(self):
        clients = Clients(proc=self.proc.name)
        self.handle("50", "4", fdinfo(1, vram=10))
        self.handle("50", "5", fdinfo(2, vram=20))
        self.assertEqual(clients.sample(1)["50"][1], (10 + 20) * 1024 + 2 * 2048 * 1024)


if __name__ == "__main__":
    unittest.main()

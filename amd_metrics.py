"""Read-only AMD gpu_metrics v3.0 decoder for the Z13's Strix Halo APU.

ABI: Linux drivers/gpu/drm/amd/include/kgd_pp_interface.h, gpu_metrics_v3_0.
Offsets include the C struct's natural alignment. Unknown versions fail closed.
Power values are firmware telemetry, not measurements from an external meter.
"""
import struct


def decode(data):
    if len(data) < 4:
        return {}
    size, major, minor = struct.unpack_from("<HBB", data)
    if (major, minor) != (3, 0) or size != 264 or len(data) < size:
        return {}

    def scalar(offset, kind="H", divisor=1):
        value = struct.unpack_from("<" + kind, data, offset)[0]
        sentinel = 0xffff if kind == "H" else 0xffffffff
        return None if value == sentinel else value / divisor

    # power in mW, clocks in MHz. GFX activity in the table varies with firmware;
    # the collector uses the kernel's normalized gpu_busy_percent instead.
    return {
        "socketPower": scalar(112, "I", 1000),
        "apuPower": scalar(120, "I", 1000),
        "gpuPower": scalar(124, "I", 1000),
        "cpuPower": scalar(132, "I", 1000),
        "corePower": [scalar(136 + 2 * i, divisor=1000) for i in range(16)],
        "coreClock": [scalar(190 + 2 * i) for i in range(16)],
        "gpuClock": scalar(174), "socClock": scalar(176),
        "fabricClock": scalar(182), "memClock": scalar(186),
        "dramRead": scalar(94), "dramWrite": scalar(96),
        "powerSource": "AMD SMU v3.0",
    }

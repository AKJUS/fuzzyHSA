# SPDX-License-Identifier: Apache-2.0
"""GPU health checking."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..kfd import KFDDevice


def is_kfd_available() -> bool:
    """Check if /dev/kfd is available."""
    return os.path.exists("/dev/kfd") and os.access("/dev/kfd", os.R_OK | os.W_OK)


def is_gpu_responsive(device: KFDDevice) -> bool:
    """
    Check if GPU is responsive by attempting a simple ioctl.

    Returns True if the GPU responds normally, False if it appears hung.
    """
    from ..kfd import get_ioctls

    try:
        ioctls = get_ioctls()
        # Try to get clock counters - a read-only operation that should always work
        if "get_clock_counters" in ioctls.list_ioctls():
            ioctls.get_clock_counters(device.kfd_fd, gpu_id=device.gpu_id)
        return True
    except Exception:
        return False


def get_gpu_memory_info(device: KFDDevice) -> dict[str, int] | None:
    """
    Get GPU memory information from sysfs.

    Returns dict with 'total' and 'used' in bytes, or None if unavailable.
    """
    try:
        mem_path = device.gpu.node_path / "mem_banks" / "0"
        if not mem_path.exists():
            return None

        props = {}
        for prop_file in ["size_in_bytes", "heap_type"]:
            path = mem_path / prop_file
            if path.exists():
                props[prop_file] = int(path.read_text().strip())
        return props
    except (OSError, ValueError):
        return None


def check_gpu_errors_sysfs(device: KFDDevice) -> list[str]:
    """
    Check for GPU errors via sysfs.

    Returns list of error messages found.
    """
    errors = []
    try:
        # Check for RAS errors if available
        ras_path = Path(f"/sys/class/drm/card{device.gpu.drm_render_minor - 128}/device/ras")
        if ras_path.exists():
            for error_type in ["umc", "gfx", "mmhub", "sdma"]:
                error_file = ras_path / f"{error_type}_err_count"
                if error_file.exists():
                    count = int(error_file.read_text().strip())
                    if count > 0:
                        errors.append(f"{error_type}: {count} errors")
    except (OSError, ValueError):
        pass
    return errors

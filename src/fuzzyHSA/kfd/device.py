# SPDX-License-Identifier: Apache-2.0
"""KFD device discovery and lifecycle management."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

KFD_PATH = Path("/dev/kfd")
TOPOLOGY_PATH = Path("/sys/devices/virtual/kfd/kfd/topology/nodes")


@dataclass(frozen=True)
class GPUInfo:
    """Immutable GPU information from sysfs topology."""

    node_path: Path
    gpu_id: int
    drm_render_minor: int
    gfx_target_version: int

    @property
    def arch(self) -> str:
        """GPU architecture string (e.g., 'gfx90a')."""
        v = self.gfx_target_version
        return f"gfx{v // 10000}{(v // 100) % 100:02x}{v % 100:02x}"

    @property
    def drm_path(self) -> Path:
        """Path to DRM render device."""
        return Path(f"/dev/dri/renderD{self.drm_render_minor}")


def discover_gpus() -> list[GPUInfo]:
    """
    Discover all usable AMD GPUs via sysfs topology.

    Returns:
        List of GPUInfo for each usable GPU, sorted by node index.

    Raises:
        No exceptions - returns empty list if no GPUs found.
    """
    if not TOPOLOGY_PATH.exists():
        return []

    gpus = []
    for node in sorted(TOPOLOGY_PATH.iterdir()):
        gpu_id_file = node / "gpu_id"
        if not gpu_id_file.exists():
            continue
        try:
            gpu_id = int(gpu_id_file.read_text().strip())
            if gpu_id == 0:
                continue
            props = _parse_properties(node / "properties")
            gpus.append(
                GPUInfo(
                    node_path=node,
                    gpu_id=gpu_id,
                    drm_render_minor=props["drm_render_minor"],
                    gfx_target_version=props["gfx_target_version"],
                )
            )
        except (OSError, KeyError, ValueError):
            continue
    return gpus


def _parse_properties(path: Path) -> dict[str, int]:
    """Parse sysfs properties file into dict."""
    props = {}
    for line in path.read_text().strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            props[parts[0]] = int(parts[1])
    return props


class KFDDevice:
    """
    Context manager for KFD device access.

    Usage:
        with KFDDevice() as dev:
            # dev.kfd_fd is the /dev/kfd file descriptor
            # dev.drm_fd is the DRM render device fd
            pass

    Raises:
        RuntimeError: If no GPUs found, device index out of range, or device open fails.
    """

    def __init__(self, device_index: int = 0):
        """
        Initialize KFD device.

        Args:
            device_index: Index into discovered GPUs (default: 0)

        Raises:
            RuntimeError: If no GPUs found or index out of range.
        """
        gpus = discover_gpus()

        if not gpus:
            msg = (
                "No AMD GPUs found. Ensure:\n"
                f"  1. KFD topology exists at {TOPOLOGY_PATH}\n"
                f"  2. /dev/kfd is accessible\n"
                "  3. AMD GPU driver (amdgpu) is loaded"
            )
            raise RuntimeError(msg)

        if device_index < 0 or device_index >= len(gpus):
            available = ", ".join(f"{i}:{g.arch}" for i, g in enumerate(gpus))
            raise RuntimeError(
                f"GPU index {device_index} out of range. "
                f"Available GPUs: [{available}]"
            )

        self.gpu = gpus[device_index]
        self._kfd_fd: int = -1
        self._drm_fd: int = -1

    @property
    def kfd_fd(self) -> int:
        """File descriptor for /dev/kfd."""
        if self._kfd_fd < 0:
            raise RuntimeError("Device not opened. Use 'with KFDDevice() as dev:' or call open()")
        return self._kfd_fd

    @property
    def drm_fd(self) -> int:
        """File descriptor for DRM render device."""
        if self._drm_fd < 0:
            raise RuntimeError("Device not opened. Use 'with KFDDevice() as dev:' or call open()")
        return self._drm_fd

    @property
    def gpu_id(self) -> int:
        """GPU ID for ioctl calls."""
        return self.gpu.gpu_id

    @property
    def arch(self) -> str:
        """GPU architecture string."""
        return self.gpu.arch

    def open(self) -> None:
        """
        Open device file descriptors.

        Raises:
            OSError: If device files cannot be opened.
        """
        if self._kfd_fd >= 0:
            return

        try:
            self._kfd_fd = os.open(str(KFD_PATH), os.O_RDWR | os.O_CLOEXEC)
        except OSError as e:
            raise OSError(
                f"Cannot open {KFD_PATH}: {e}. "
                "Check permissions (user may need to be in 'render' or 'video' group)"
            ) from e

        try:
            self._drm_fd = os.open(str(self.gpu.drm_path), os.O_RDWR)
        except OSError as e:
            os.close(self._kfd_fd)
            self._kfd_fd = -1
            raise OSError(f"Cannot open {self.gpu.drm_path}: {e}") from e

    def close(self) -> None:
        """Close device file descriptors."""
        if self._drm_fd >= 0:
            os.close(self._drm_fd)
            self._drm_fd = -1
        if self._kfd_fd >= 0:
            os.close(self._kfd_fd)
            self._kfd_fd = -1

    @property
    def is_open(self) -> bool:
        """Check if device is currently open."""
        return self._kfd_fd >= 0

    def __enter__(self) -> KFDDevice:
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        status = "open" if self.is_open else "closed"
        return f"KFDDevice(gpu_id={self.gpu.gpu_id}, arch={self.arch}, {status})"

# SPDX-License-Identifier: Apache-2.0
"""KFD (Kernel Fusion Driver) interface for AMD GPUs."""

from .device import KFDDevice, GPUInfo, discover_gpus
from .memory import (
    MemoryRegion,
    GPUMemory,
    mmap_anonymous,
    allocate_gpu_memory,
    map_to_gpu_memory,
    free_gpu_memory,
)
from .ioctl import (
    IoctlDef,
    IoctlCollection,
    get_ioctls,
    clear_ioctl_cache,
    execute_ioctl,
    execute_ioctl_raw,
    struct_to_bytes,
    bytes_to_struct,
)

__all__ = [
    # Device
    "KFDDevice",
    "GPUInfo",
    "discover_gpus",
    # Memory
    "MemoryRegion",
    "GPUMemory",
    "mmap_anonymous",
    "allocate_gpu_memory",
    "map_to_gpu_memory",
    "free_gpu_memory",
    # IOCTL
    "IoctlDef",
    "IoctlCollection",
    "get_ioctls",
    "clear_ioctl_cache",
    "execute_ioctl",
    "execute_ioctl_raw",
    "struct_to_bytes",
    "bytes_to_struct",
]

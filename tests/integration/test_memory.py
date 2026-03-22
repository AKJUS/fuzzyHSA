# SPDX-License-Identifier: Apache-2.0
"""Integration tests for memory operations (requires AMD GPU)."""

import pytest

from fuzzyHSA.kfd import (
    KFDDevice,
    allocate_gpu_memory,
    free_gpu_memory,
    get_ioctls,
    mmap_anonymous,
)


@pytest.mark.integration
class TestMemoryMapping:
    def test_mmap_anonymous(self):
        with mmap_anonymous(0x1000) as mem:
            assert mem.addr != 0
            assert mem.size == 0x1000

    def test_mmap_auto_cleanup(self):
        mem = mmap_anonymous(0x1000)
        mem.unmap()
        # Should not crash, region is unmapped

    def test_mmap_context_manager(self):
        with mmap_anonymous(0x2000) as mem:
            assert mem.size == 0x2000
        # Should be unmapped after context


@pytest.mark.integration
class TestGPUMemory:
    @pytest.fixture
    def device(self):
        dev = KFDDevice(0)
        dev.open()
        # Acquire VM first
        ioctls = get_ioctls()
        ioctls.acquire_vm(dev.kfd_fd, drm_fd=dev.drm_fd, gpu_id=dev.gpu_id)
        yield dev
        dev.close()

    def test_allocate_and_free(self, device):
        import fuzzyHSA.kfd.autogen.kfd as kfd

        mem = allocate_gpu_memory(
            device,
            size=0x1000,
            flags=kfd.KFD_IOC_ALLOC_MEM_FLAGS_GTT,
            map_to_gpu=True,
        )

        assert mem.addr != 0
        assert mem.size == 0x1000
        assert mem.handle != 0
        assert device.gpu_id in mem.gpu_ids

        free_gpu_memory(device, mem)

    def test_allocate_larger_region(self, device):
        import fuzzyHSA.kfd.autogen.kfd as kfd

        mem = allocate_gpu_memory(
            device,
            size=0x100000,  # 1MB
            flags=kfd.KFD_IOC_ALLOC_MEM_FLAGS_GTT,
            map_to_gpu=True,
        )

        assert mem.size == 0x100000
        free_gpu_memory(device, mem)

# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for fuzzyHSA."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_fuzz(args: argparse.Namespace) -> int:
    """Run the fuzzer."""
    from .kfd import KFDDevice, get_ioctls
    from .fuzz import FuzzHarness, HarnessConfig, IoctlTarget
    from .monitor import DmesgMonitor
    from .logging import CrashLogger

    # Check for autogen files
    try:
        get_ioctls()
    except Exception as e:
        print(f"Error: Could not load KFD ioctls. Run 'bash autogen_stubs.sh generate' first.")
        print(f"Details: {e}")
        return 1

    # Open device
    try:
        device = KFDDevice(args.device)
        device.open()
    except Exception as e:
        print(f"Error: Could not open KFD device: {e}")
        return 1

    try:
        # Set up components
        target = IoctlTarget(device, skip_dangerous=not args.dangerous)
        monitor = DmesgMonitor()
        logger = CrashLogger(Path(args.output))

        config = HarnessConfig(
            iterations=args.iterations,
            seed=args.seed,
            stop_on_crash=not args.continue_on_crash,
            stop_on_hang=True,
            verbose=args.verbose,
            operations=args.operations.split(",") if args.operations else None,
        )

        harness = FuzzHarness(target, config, monitor, logger)

        print(f"fuzzyHSA - KFD/GPU Fuzzer")
        print(f"  Device: {device}")
        print(f"  Target: {target.name} ({len(target.operations)} operations)")
        print(f"  Iterations: {args.iterations}")
        print(f"  Output: {args.output}")
        print()

        results = harness.run()

        if results:
            print(f"\nFound {len(results)} interesting results:")
            for r in results:
                print(f"  - {r.status.value}: {r.case.operation} (seed={r.case.seed})")

        return 0 if not results else 2  # Exit code 2 = crashes found

    finally:
        device.close()


def cmd_list_targets(args: argparse.Namespace) -> int:
    """List available fuzz targets and operations."""
    from .kfd import get_ioctls

    try:
        ioctls = get_ioctls()
    except Exception as e:
        print(f"Error: Could not load KFD ioctls: {e}")
        return 1

    print("Available IOCTL operations:")
    for name in sorted(ioctls.list_ioctls()):
        print(f"  {name}")

    return 0


def cmd_reproduce(args: argparse.Namespace) -> int:
    """Reproduce a crash from a log file."""
    from .kfd import KFDDevice, get_ioctls
    from .fuzz import IoctlTarget
    from .logging import CrashLogger

    path = Path(args.crash_file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    logger = CrashLogger(path.parent)
    result = logger.load(path)

    print(f"Reproducing crash:")
    print(f"  Operation: {result.case.operation}")
    print(f"  Seed: {result.case.seed}")
    print(f"  Mutation: {result.case.mutation}")
    print(f"  Input size: {len(result.case.input_data)} bytes")
    print()

    if args.dry_run:
        print("Dry run - not executing")
        print(f"Input data (hex): {result.case.input_data.hex()}")
        return 0

    try:
        get_ioctls()
        device = KFDDevice(args.device)
        device.open()
    except Exception as e:
        print(f"Error: {e}")
        return 1

    try:
        target = IoctlTarget(device, skip_dangerous=False)
        new_result = target.execute(result.case)

        print(f"Result: {new_result.status.value}")
        if new_result.error_message:
            print(f"Error: {new_result.error_message}")
        print(f"Duration: {new_result.duration_ms:.2f}ms")

        return 0 if new_result.status.value == "ok" else 2

    finally:
        device.close()


def cmd_info(args: argparse.Namespace) -> int:
    """Show system information."""
    from .kfd import discover_gpus
    from .monitor import is_kfd_available

    print("fuzzyHSA System Info")
    print()

    print(f"KFD available: {is_kfd_available()}")
    print()

    gpus = discover_gpus()
    if not gpus:
        print("No AMD GPUs found")
        return 1

    print(f"Found {len(gpus)} GPU(s):")
    for i, gpu in enumerate(gpus):
        print(f"  [{i}] GPU ID: {gpu.gpu_id}")
        print(f"      Arch: {gpu.arch}")
        print(f"      DRM: {gpu.drm_path}")
        print()

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="fuzzyHSA",
        description="KFD/GPU Firmware Fuzzer for AMD GPUs",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fuzz command
    fuzz_parser = subparsers.add_parser("fuzz", help="Run the fuzzer")
    fuzz_parser.add_argument(
        "-n", "--iterations",
        type=int,
        default=1000,
        help="Number of fuzz iterations (default: 1000)",
    )
    fuzz_parser.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    fuzz_parser.add_argument(
        "-d", "--device",
        type=int,
        default=0,
        help="GPU device index (default: 0)",
    )
    fuzz_parser.add_argument(
        "-o", "--output",
        type=str,
        default="crashes",
        help="Output directory for crash logs (default: crashes)",
    )
    fuzz_parser.add_argument(
        "--operations",
        type=str,
        default=None,
        help="Comma-separated list of operations to fuzz",
    )
    fuzz_parser.add_argument(
        "--dangerous",
        action="store_true",
        help="Include dangerous operations (destroy, free, etc.)",
    )
    fuzz_parser.add_argument(
        "--continue-on-crash",
        action="store_true",
        help="Continue fuzzing after finding crashes",
    )
    fuzz_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    fuzz_parser.set_defaults(func=cmd_fuzz)

    # list-targets command
    list_parser = subparsers.add_parser("list-targets", help="List fuzz targets")
    list_parser.set_defaults(func=cmd_list_targets)

    # reproduce command
    repro_parser = subparsers.add_parser("reproduce", help="Reproduce a crash")
    repro_parser.add_argument("crash_file", help="Path to crash JSON file")
    repro_parser.add_argument(
        "-d", "--device",
        type=int,
        default=0,
        help="GPU device index (default: 0)",
    )
    repro_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show crash details without executing",
    )
    repro_parser.set_defaults(func=cmd_reproduce)

    # info command
    info_parser = subparsers.add_parser("info", help="Show system information")
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

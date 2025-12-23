"""
Pytest tests that verify the task's required behavior.

These tests intentionally validate behavior (observable outputs and artifacts),
not implementation details.

They also include basic anti-cheating checks:
- "canary" strings that should not appear in task artifacts unless someone
  hardcoded expected values or copied tests/solutions into the runtime.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

CANARY_STRINGS = [
    # Task-specific strings that should not be embedded into outputs/artifacts.
    "Terminus-EC-Training-stateful",
    "Submission Checklist",
    "harbor run --agent oracle",
    "check_canary",
    # Make it harder to hardcode the exact expected outputs by embedding test names.
    "test 1",
    "test 2",
]


def _app_root() -> pathlib.Path:
    # In the verifier image, the project lives at /app (and instruction.md mandates absolute paths).
    return pathlib.Path("/app")


def _run(cmd: list[str], *, cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _clean(s: str) -> str:
    # Match the verifier behavior: normalize whitespace/newlines for stable comparisons.
    return " ".join(s.replace("\r\n", "\n").split())


def _assert_no_canaries_in_text(text: str, *, label: str) -> None:
    for canary in CANARY_STRINGS:
        assert canary not in text, f"Found canary string in {label}: {canary!r}"


def _assert_binary_exists(path: pathlib.Path) -> None:
    assert path.exists(), f"Expected binary to exist at {path}"
    assert path.is_file(), f"Expected {path} to be a file"


def test_cli_build_and_outputs_host_release() -> None:
    """
    Build the host binary and verify CLI behavior for required examples.

    Requirements verified:
    - Accepts a single integer argument
    - Prints `Result: <number * 2>` to stdout
    - Exits with code 0
    """
    root = _app_root()

    build = _run(["cargo", "build", "--release"], cwd=root)
    assert build.returncode == 0, (
        f"Host build failed:\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}"
    )
    _assert_no_canaries_in_text(build.stdout + build.stderr, label="cargo build output")

    bin_path = root / "target" / "release" / "sample-cli"
    _assert_binary_exists(bin_path)

    # Required example checks (match verifier expectations).
    for inp, expected in [("5", "Result: 10"), ("7", "Result: 14")]:
        run = _run([str(bin_path), inp], cwd=root)
        assert run.returncode == 0, (
            f"Binary failed for input {inp}:\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
        )

        # The program prints the result to stdout; stderr should generally be empty on success.
        out_clean = _clean(run.stdout)
        assert out_clean == expected, (
            f"Output mismatch for input {inp}: expected {expected!r}, got {out_clean!r}"
        )

        _assert_no_canaries_in_text(
            run.stdout + run.stderr, label=f"binary output (input={inp})"
        )


def test_cli_usage_and_invalid_integer_errors() -> None:
    """
    Verify the CLI handles incorrect usage and invalid integers.

    Requirements verified:
    - If argument count is wrong, prints `Usage: <bin> <number>` to stderr and exits non-zero
    - If argument cannot be parsed as integer, prints `Error: '<arg>' is not a valid integer` to stderr and exits non-zero
    """
    root = _app_root()
    bin_path = root / "target" / "release" / "sample-cli"

    # If the binary hasn't been built yet in this test session, build it quickly.
    if not bin_path.exists():
        build = _run(["cargo", "build", "--release"], cwd=root)
        assert build.returncode == 0, (
            f"Host build failed:\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}"
        )

    _assert_binary_exists(bin_path)

    # Wrong arity -> usage to stderr, non-zero exit
    run_no_args = _run([str(bin_path)], cwd=root)
    assert run_no_args.returncode != 0, (
        "Expected non-zero exit code when no args are provided"
    )
    assert "Usage:" in run_no_args.stderr, (
        f"Expected usage message on stderr, got:\n{run_no_args.stderr}"
    )
    assert "<number>" in run_no_args.stderr, (
        f"Expected '<number>' in usage message, got:\n{run_no_args.stderr}"
    )
    _assert_no_canaries_in_text(
        run_no_args.stdout + run_no_args.stderr, label="usage output"
    )

    # Invalid int -> specific error message to stderr, non-zero exit
    bad = "abc"
    run_bad = _run([str(bin_path), bad], cwd=root)
    assert run_bad.returncode != 0, (
        "Expected non-zero exit code for invalid integer input"
    )
    err_clean = _clean(run_bad.stderr)
    assert err_clean == f"Error: '{bad}' is not a valid integer", (
        f"Unexpected stderr: {err_clean!r}"
    )
    _assert_no_canaries_in_text(
        run_bad.stdout + run_bad.stderr, label="invalid-integer output"
    )


def test_armv7_cross_build_artifacts_exist_build_only() -> None:
    """
    Build ARMv7 artifacts (build-only) and verify expected output locations exist.

    This mirrors the verifier approach: build ARMv7 binaries, but do not attempt to execute
    them under QEMU in the test environment.

    Requirements verified:
    - Cross build produces armv7-unknown-linux-gnueabihf release binary at:
      /app/target/armv7-unknown-linux-gnueabihf/release/sample-cli
    """
    root = _app_root()

    # If a toolchain is missing, this will fail and correctly signal the task isn't complete.
    build_arm = _run(
        ["cargo", "build", "--release", "--target", "armv7-unknown-linux-gnueabihf"],
        cwd=root,
    )
    assert build_arm.returncode == 0, (
        f"ARMv7 build failed:\nSTDOUT:\n{build_arm.stdout}\nSTDERR:\n{build_arm.stderr}"
    )
    _assert_no_canaries_in_text(
        build_arm.stdout + build_arm.stderr, label="cargo arm build output"
    )

    arm_bin = (
        root / "target" / "armv7-unknown-linux-gnueabihf" / "release" / "sample-cli"
    )
    _assert_binary_exists(arm_bin)

    # Basic anti-cheating: the binary should not literally contain our canary strings.
    # (We only do a lightweight scan and only if we can safely read bytes.)
    data = arm_bin.read_bytes()
    for canary in CANARY_STRINGS:
        assert canary.encode("utf-8") not in data, (
            f"Found canary string embedded in ARM binary: {canary!r}"
        )


def test_verifier_env_sh_not_modified_by_tests() -> None:
    """
    Anti-cheating / hygiene check:
    Tests should not rely on modifying verifier side-channel files.

    If /logs/verifier/env.sh exists, ensure it doesn't contain obvious canaries.
    """
    env_sh = pathlib.Path("/logs/verifier/env.sh")
    if not env_sh.exists():
        # Not all runtimes will have this file at pytest time.
        return

    txt = env_sh.read_text(errors="replace")
    _assert_no_canaries_in_text(txt, label="/logs/verifier/env.sh")

    # Also ensure tests didn't accidentally write a reward file.
    reward = pathlib.Path("/logs/verifier/reward.txt")
    if reward.exists():
        # Reward file is the shell verifier's responsibility.
        # If it exists, it should not contain canary strings either.
        _assert_no_canaries_in_text(
            reward.read_text(errors="replace"), label="/logs/verifier/reward.txt"
        )


def test_task_uses_absolute_app_path_in_environment() -> None:
    """
    Sanity-check that the task follows the instruction requirement of using absolute paths (/app).

    This is a lightweight check against the runtime filesystem rather than parsing instruction.md.
    """
    root = _app_root()
    assert root.is_dir(), "Expected /app to exist and be a directory"
    # Ensure we're not accidentally running from a relative checkout.
    assert os.getcwd().startswith("/"), (
        "Expected tests to run in an absolute-path environment"
    )

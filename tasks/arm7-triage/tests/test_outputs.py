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
import re
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
    Build ARMv7 artifacts (build-only) for both musl and glibc targets and verify expected outputs.

    This mirrors the verifier approach: build ARMv7 binaries, but do not attempt to execute
    them under QEMU in the test environment.

    Requirements verified:
    - Cross build produces armv7-unknown-linux-musleabihf release binary (static)
    - Cross build produces armv7-unknown-linux-gnueabihf release binary (dynamic)
    - The musl binary is fully statically linked (no INTERP segment)
    - The musl binary is under 5MB in size
    - The glibc binary dynamically links against zlib (libz.so.1)
    - Both binaries are ARM ELF executables
    """
    root = _app_root()

    # Build musl target (static)
    build_musl = _run(
        ["cargo", "build", "--release", "--target", "armv7-unknown-linux-musleabihf"],
        cwd=root,
    )
    assert build_musl.returncode == 0, (
        f"ARMv7 musl build failed:\nSTDOUT:\n{build_musl.stdout}\nSTDERR:\n{build_musl.stderr}"
    )
    _assert_no_canaries_in_text(
        build_musl.stdout + build_musl.stderr, label="cargo arm musl build output"
    )

    musl_bin = (
        root / "target" / "armv7-unknown-linux-musleabihf" / "release" / "sample-cli"
    )
    _assert_binary_exists(musl_bin)

    # Verify musl binary is ARM ELF
    file_musl = _run(["file", str(musl_bin)], cwd=root)
    assert file_musl.returncode == 0
    file_musl_txt = file_musl.stdout.strip()
    assert "ELF" in file_musl_txt and "ARM" in file_musl_txt, (
        f"Expected an ARM ELF binary, got: {file_musl_txt!r}"
    )
    assert "statically linked" in file_musl_txt, (
        f"Expected musl binary to be statically linked, got: {file_musl_txt!r}"
    )

    # Verify musl binary has no INTERP segment (fully static)
    readelf_musl = _run(["readelf", "-l", str(musl_bin)], cwd=root)
    assert readelf_musl.returncode == 0
    assert "INTERP" not in readelf_musl.stdout, (
        "Musl binary should not have INTERP segment (must be fully static)"
    )

    # Verify musl binary size is under 5MB
    musl_size = musl_bin.stat().st_size
    max_size = 5 * 1024 * 1024  # 5MB
    assert musl_size < max_size, (
        f"Musl binary size {musl_size} bytes exceeds maximum {max_size} bytes (5MB)"
    )

    # Build glibc target (dynamic)
    build_glibc = _run(
        ["cargo", "build", "--release", "--target", "armv7-unknown-linux-gnueabihf"],
        cwd=root,
    )
    assert build_glibc.returncode == 0, (
        f"ARMv7 glibc build failed:\nSTDOUT:\n{build_glibc.stdout}\nSTDERR:\n{build_glibc.stderr}"
    )
    _assert_no_canaries_in_text(
        build_glibc.stdout + build_glibc.stderr, label="cargo arm glibc build output"
    )

    glibc_bin = (
        root / "target" / "armv7-unknown-linux-gnueabihf" / "release" / "sample-cli"
    )
    _assert_binary_exists(glibc_bin)

    # Verify glibc binary is ARM ELF
    file_glibc = _run(["file", str(glibc_bin)], cwd=root)
    assert file_glibc.returncode == 0
    file_glibc_txt = file_glibc.stdout.strip()
    assert "ELF" in file_glibc_txt and "ARM" in file_glibc_txt, (
        f"Expected an ARM ELF binary, got: {file_glibc_txt!r}"
    )

    # Verify glibc binary dynamically links libz.so.1
    readelf_glibc = _run(["readelf", "-d", str(glibc_bin)], cwd=root)
    assert readelf_glibc.returncode == 0
    dyn_txt = readelf_glibc.stdout
    assert re.search(r"\(NEEDED\).*libz\.so\.1", dyn_txt), (
        "Expected libz.so.1 in DT_NEEDED entries, but it was not found.\n"
        f"readelf -d output:\n{dyn_txt}"
    )

    # Anti-cheating checks for both binaries
    for bin_path, label in [(musl_bin, "musl"), (glibc_bin, "glibc")]:
        data = bin_path.read_bytes()
        for canary in CANARY_STRINGS:
            assert canary.encode("utf-8") not in data, (
                f"Found canary string embedded in ARM {label} binary: {canary!r}"
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


def test_pkg_config_cross_configured() -> None:
    """
    Verify pkg-config was properly configured for cross-compilation.

    This ensures agents correctly set pkg-config environment variables to find
    ARM zlib libraries instead of host libraries.

    Requirements verified:
    - PKG_CONFIG_ALLOW_CROSS=1 (allows cross-compilation lookups)
    - PKG_CONFIG_SYSROOT_DIR points to ARM sysroot
    - PKG_CONFIG_LIBDIR or PKG_CONFIG_PATH includes ARM pkgconfig paths
    """
    env_file = pathlib.Path("/logs/verifier/env.sh")
    assert env_file.exists(), (
        "Expected /logs/verifier/env.sh to exist (created by solution script)"
    )

    content = env_file.read_text()

    # Must have cross-compilation pkg-config vars
    assert "PKG_CONFIG_ALLOW_CROSS=1" in content or 'PKG_CONFIG_ALLOW_CROSS="1"' in content, (
        "PKG_CONFIG_ALLOW_CROSS not set in env.sh - required for cross-compilation"
    )

    assert "PKG_CONFIG_SYSROOT_DIR" in content, (
        "PKG_CONFIG_SYSROOT_DIR not set in env.sh - pkg-config won't find ARM libs"
    )

    # Verify it points to ARM sysroot (not host)
    assert "arm-linux-gnueabihf" in content, (
        "pkg-config not configured for ARM target - should reference arm-linux-gnueabihf sysroot"
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


def test_cargo_config_contains_required_env_vars() -> None:
    """
    Verify .cargo/config.toml contains all 5 required environment variables
    and proper linker configuration.

    instruction.md requires duplicating all environment variables from env.sh
    into .cargo/config.toml [env] section with matching absolute paths.

    Requirements verified:
    - .cargo/config.toml exists
    - Contains [target.armv7-unknown-linux-gnueabihf] section with linker entry
    - Contains [env] section with all 5 required variables:
      1. CC_armv7_unknown_linux_gnueabihf
      2. CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER
      3. PKG_CONFIG_ALLOW_CROSS
      4. PKG_CONFIG_SYSROOT_DIR
      5. PKG_CONFIG_LIBDIR
    - Values match those in /logs/verifier/env.sh (absolute paths)
    - CC and linker paths are absolute (start with /)
    """
    root = _app_root()
    cargo_config = root / ".cargo" / "config.toml"
    env_sh = pathlib.Path("/logs/verifier/env.sh")

    assert cargo_config.exists(), (
        "Expected .cargo/config.toml to exist at /app/.cargo/config.toml"
    )
    assert env_sh.exists(), (
        "Expected /logs/verifier/env.sh to exist (created by solution script)"
    )

    config_content = cargo_config.read_text()
    env_content = env_sh.read_text()

    # Verify [target.armv7-unknown-linux-gnueabihf] section with linker entry exists
    assert "[target.armv7-unknown-linux-gnueabihf]" in config_content, (
        ".cargo/config.toml must contain [target.armv7-unknown-linux-gnueabihf] section"
    )

    linker_pattern = r'\[target\.armv7-unknown-linux-gnueabihf\].*?linker\s*=\s*"(.+?)"'
    linker_match = re.search(linker_pattern, config_content, re.DOTALL)
    assert linker_match, (
        "[target.armv7-unknown-linux-gnueabihf] section must contain 'linker' entry"
    )

    # Required environment variables from instruction.md
    required_vars = [
        "CC_armv7_unknown_linux_gnueabihf",
        "CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER",
        "PKG_CONFIG_ALLOW_CROSS",
        "PKG_CONFIG_SYSROOT_DIR",
        "PKG_CONFIG_LIBDIR",
    ]

    # Extract values from env.sh (parsing export statements)
    env_values = {}
    for var in required_vars:
        # Match: export VAR=value or export VAR="value"
        pattern = rf'export\s+{re.escape(var)}=(["\']?)(.+?)\1(?:\s|$)'
        match = re.search(pattern, env_content, re.MULTILINE)
        assert match, (
            f"Required variable {var} not found in /logs/verifier/env.sh"
        )
        env_values[var] = match.group(2)

    # Verify all variables exist in .cargo/config.toml [env] section
    assert "[env]" in config_content, (
        ".cargo/config.toml must contain [env] section with environment variables"
    )

    for var in required_vars:
        # Match TOML format: VAR = "value" (case-insensitive for variable name)
        pattern = rf'{re.escape(var)}\s*=\s*"(.+?)"'
        match = re.search(pattern, config_content, re.IGNORECASE)
        assert match, (
            f"Required variable {var} not found in .cargo/config.toml [env] section"
        )

        cargo_value = match.group(1)
        expected_value = env_values[var]

        assert cargo_value == expected_value, (
            f"Variable {var} mismatch:\n"
            f"  env.sh:          {expected_value!r}\n"
            f"  .cargo/config:   {cargo_value!r}\n"
            f"Values must match exactly (instruction.md requirement)"
        )

    # Verify CC and linker paths are absolute (instruction.md requires absolute paths)
    cc_path = env_values["CC_armv7_unknown_linux_gnueabihf"]
    linker_path = env_values["CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER"]
    sysroot_path = env_values["PKG_CONFIG_SYSROOT_DIR"]

    assert cc_path.startswith("/"), (
        f"CC_armv7_unknown_linux_gnueabihf must be an absolute path, got: {cc_path!r}"
    )
    assert linker_path.startswith("/"), (
        f"CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER must be an absolute path, got: {linker_path!r}"
    )
    assert sysroot_path.startswith("/"), (
        f"PKG_CONFIG_SYSROOT_DIR must be an absolute path, got: {sysroot_path!r}"
    )

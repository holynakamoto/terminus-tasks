"""
Enhanced test suite for NCCL optimization with PFC vs ECN comparison.

NOTE: This is a simulated task without real GPUs/RDMA hardware.
Tests validate configuration knowledge and reasoning, not actual execution.

Validates:
1. Required output files created with correct format
2. Performance targets met (based on correct NCCL configuration)
3. Comprehensive analysis in optimization report
4. Evidence of proper NCCL configuration understanding
"""

import sys
from pathlib import Path


def test_baseline_timing_exists():
    """Test that baseline timing file was created with valid data."""
    baseline_file = Path("/workspace/baseline_timing.txt")
    assert baseline_file.exists(), "baseline_timing.txt not found. Run baseline benchmark first."
    
    content = baseline_file.read_text().strip()
    try:
        baseline_time = float(content)
    except ValueError:
        raise AssertionError(f"baseline_timing.txt contains invalid float: '{content}'")
    
    # Baseline should be slow (TCP fallback) - typically 100-200ms
    assert 0.08 < baseline_time < 0.3, \
        f"Baseline time {baseline_time}s outside expected TCP range (0.08-0.3s)"
    print(f"✓ Baseline: {baseline_time*1000:.1f} ms/iter (TCP fallback)")


def test_optimized_timing_exists():
    """Test that optimized timing file was created."""
    optimized_file = Path("/workspace/optimized_timing.txt")
    assert optimized_file.exists(), \
        "optimized_timing.txt not found. This should contain your best RoCEv2 mode result."
    
    content = optimized_file.read_text().strip()
    try:
        optimized_time = float(content)
    except ValueError:
        raise AssertionError(f"optimized_timing.txt contains invalid float: '{content}'")
    
    assert optimized_time > 0, f"Invalid optimized time: {optimized_time}s"
    print(f"✓ Optimized: {optimized_time*1000:.1f} ms/iter")


def test_required_speedup():
    """Test that minimum 3x speedup was achieved."""
    baseline_file = Path("/workspace/baseline_timing.txt")
    optimized_file = Path("/workspace/optimized_timing.txt")
    
    assert baseline_file.exists() and optimized_file.exists(), \
        "Missing timing files for speedup calculation"
    
    baseline_time = float(baseline_file.read_text().strip())
    optimized_time = float(optimized_file.read_text().strip())
    speedup = baseline_time / optimized_time
    
    print(f"  Speedup: {speedup:.2f}x")
    assert speedup >= 3.0, \
        f"Speedup {speedup:.2f}x below required 3.0x minimum. " \
        f"Check NCCL configuration (RDMA enabled? Correct GID index?)"
    print(f"✓ Achieved {speedup:.2f}x speedup (≥3.0x required)")


def test_pfc_mode_if_present():
    """Validate PFC mode results if tested."""
    pfc_file = Path("/workspace/roce_pfc_timing.txt")
    
    if not pfc_file.exists():
        print("  Info: PFC mode not tested (optional)")
        return
    
    try:
        pfc_time = float(pfc_file.read_text().strip())
        baseline_time = float(Path("/workspace/baseline_timing.txt").read_text().strip())
        speedup = baseline_time / pfc_time
        
        print(f"  RoCEv2 PFC: {pfc_time*1000:.1f} ms ({speedup:.2f}x)")
        
        # Instruction.md says PFC target is <60ms
        if pfc_time > 0.060:
            print(f"    Warning: PFC {pfc_time*1000:.1f}ms exceeds 60ms target")
        if speedup < 2.5:
            print(f"    Warning: PFC speedup {speedup:.2f}x below 2.5x target")
        
        if pfc_time <= 0.060 and speedup >= 2.5:
            print("  ✓ PFC mode meets targets")
            
    except (ValueError, FileNotFoundError) as e:
        print(f"  Warning: PFC file invalid: {e}")


def test_ecn_mode_if_present():
    """Validate ECN mode results if tested."""
    ecn_file = Path("/workspace/roce_ecn_timing.txt")
    
    if not ecn_file.exists():
        print("  Info: ECN mode not tested (optional)")
        return
    
    try:
        ecn_time = float(ecn_file.read_text().strip())
        baseline_time = float(Path("/workspace/baseline_timing.txt").read_text().strip())
        speedup = baseline_time / ecn_time
        
        print(f"  RoCEv2 ECN: {ecn_time*1000:.1f} ms ({speedup:.2f}x)")
        
        # Instruction.md says ECN target is <50ms
        if ecn_time > 0.050:
            print(f"    Warning: ECN {ecn_time*1000:.1f}ms exceeds 50ms target")
        if speedup < 3.0:
            print(f"    Warning: ECN speedup {speedup:.2f}x below 3.0x target")
            
        if ecn_time <= 0.050 and speedup >= 3.0:
            print("  ✓ ECN mode meets targets")
            
    except (ValueError, FileNotFoundError) as e:
        print(f"  Warning: ECN file invalid: {e}")


def test_hybrid_mode_if_present():
    """Validate Hybrid mode results if tested."""
    hybrid_file = Path("/workspace/roce_hybrid_timing.txt")
    
    if not hybrid_file.exists():
        print("  Info: Hybrid mode not tested (optional)")
        return
    
    try:
        hybrid_time = float(hybrid_file.read_text().strip())
        baseline_time = float(Path("/workspace/baseline_timing.txt").read_text().strip())
        speedup = baseline_time / hybrid_time
        
        print(f"  RoCEv2 Hybrid: {hybrid_time*1000:.1f} ms ({speedup:.2f}x)")
        
        # Instruction.md says Hybrid target is <45ms
        if hybrid_time > 0.045:
            print(f"    Warning: Hybrid {hybrid_time*1000:.1f}ms exceeds 45ms target")
        if speedup < 3.3:
            print(f"    Warning: Hybrid speedup {speedup:.2f}x below 3.3x target")
            
        if hybrid_time <= 0.045 and speedup >= 3.3:
            print("  ✓ Hybrid mode meets targets")
            
    except (ValueError, FileNotFoundError) as e:
        print(f"  Warning: Hybrid file invalid: {e}")


def test_infiniband_baseline_if_present():
    """Validate InfiniBand baseline if tested."""
    ib_file = Path("/workspace/ib_timing.txt")
    
    if not ib_file.exists():
        print("  Info: InfiniBand baseline not established (optional)")
        return
    
    try:
        ib_time = float(ib_file.read_text().strip())
        baseline_time = float(Path("/workspace/baseline_timing.txt").read_text().strip())
        speedup = baseline_time / ib_time
        
        print(f"  InfiniBand: {ib_time*1000:.1f} ms ({speedup:.2f}x)")
        print("  ✓ IB baseline established")
        
    except (ValueError, FileNotFoundError) as e:
        print(f"  Warning: IB file invalid: {e}")


def test_roce_vs_ib_comparison():
    """Test that best RoCEv2 achieves ≥90% of InfiniBand performance."""
    ib_file = Path("/workspace/ib_timing.txt")
    optimized_file = Path("/workspace/optimized_timing.txt")
    
    if not ib_file.exists():
        print("  Skipping: IB baseline not available for comparison")
        return
    
    assert optimized_file.exists(), "optimized_timing.txt required for IB comparison"
    
    try:
        ib_time = float(ib_file.read_text().strip())
        optimized_time = float(optimized_file.read_text().strip())
        
        # Lower time is better, so (ib_time / optimized_time) * 100 gives percentage
        roce_percent = (ib_time / optimized_time) * 100
        
        print(f"  Best RoCEv2: {optimized_time*1000:.1f} ms")
        print(f"  InfiniBand:  {ib_time*1000:.1f} ms")
        print(f"  RoCEv2 is {roce_percent:.1f}% of IB performance")
        
        assert roce_percent >= 90, \
            f"RoCEv2 only {roce_percent:.1f}% of IB (need ≥90%). " \
            f"Check if you tested Hybrid mode and used correct NCCL settings."
        print(f"✓ RoCEv2 meets 90% IB target ({roce_percent:.1f}%)")
        
    except (ValueError, FileNotFoundError) as e:
        raise AssertionError(f"IB comparison failed: {e}")


def test_optimization_report_exists():
    """Test that optimization report was created."""
    report_file = Path("/workspace/optimization_report.md")
    assert report_file.exists(), \
        "optimization_report.md not found. Create this file documenting your optimization process."
    
    content = report_file.read_text()
    char_count = len(content)
    
    assert char_count >= 800, \
        f"Report too short: {char_count} chars (minimum: 800). " \
        f"Add more detail about PFC vs ECN tradeoffs and NCCL configuration."
    print(f"✓ Report exists ({char_count} chars)")


def test_report_discusses_congestion_control():
    """Test that report analyzes congestion control modes."""
    report_file = Path("/workspace/optimization_report.md")
    assert report_file.exists(), "optimization_report.md required"
    
    content = report_file.read_text().lower()
    
    # Check for discussion of congestion control
    has_pfc = 'pfc' in content or 'priority flow control' in content
    has_ecn = 'ecn' in content or 'explicit congestion' in content or 'dcqcn' in content
    has_analysis = any(word in content for word in ['vs', 'versus', 'compared', 'comparison', 'trade-off', 'tradeoff'])
    
    issues = []
    if not has_pfc:
        issues.append("missing PFC discussion")
    if not has_ecn:
        issues.append("missing ECN discussion")
    if not has_analysis:
        issues.append("missing comparative analysis")
    
    if issues:
        print(f"  Warning: Report quality issues: {', '.join(issues)}")
    else:
        print("✓ Report discusses PFC vs ECN")


def test_report_has_nccl_configuration():
    """Test that report documents NCCL configuration."""
    report_file = Path("/workspace/optimization_report.md")
    assert report_file.exists()
    
    content = report_file.read_text().lower()
    
    # Check for key NCCL configuration topics
    has_gid = 'gid' in content
    has_nccl = 'nccl' in content
    has_config = any(word in content for word in ['configuration', 'environment', 'variable', 'export'])
    
    if has_gid and has_nccl and has_config:
        print("✓ Report documents NCCL configuration")
    else:
        print("  Info: Report could include more NCCL configuration details")


def test_nccl_config_env_if_present():
    """Check NCCL configuration file if provided."""
    config_file = Path("/workspace/nccl_config.env")
    
    if not config_file.exists():
        print("  Info: nccl_config.env not provided (optional)")
        return
    
    content = config_file.read_text()
    
    # Check for critical NCCL settings
    critical_vars = ['NCCL_IB_DISABLE', 'NCCL_NET', 'NCCL_IB_GID_INDEX']
    found = [var for var in critical_vars if var in content]
    
    print(f"  NCCL config provided ({len(found)}/{len(critical_vars)} critical vars)")
    
    # Verify RDMA is enabled
    if 'NCCL_IB_DISABLE=0' in content:
        print("  ✓ RDMA enabled (NCCL_IB_DISABLE=0)")
    elif 'NCCL_IB_DISABLE=1' in content:
        print("  ✗ Warning: RDMA appears disabled (NCCL_IB_DISABLE=1)")


def test_solution_completeness():
    """Meta-test for overall solution quality."""
    required_files = {
        'baseline_timing.txt': Path("/workspace/baseline_timing.txt").exists(),
        'optimized_timing.txt': Path("/workspace/optimized_timing.txt").exists(),
        'optimization_report.md': Path("/workspace/optimization_report.md").exists(),
    }
    
    optional_files = {
        'roce_pfc_timing.txt': Path("/workspace/roce_pfc_timing.txt").exists(),
        'roce_ecn_timing.txt': Path("/workspace/roce_ecn_timing.txt").exists(),
        'roce_hybrid_timing.txt': Path("/workspace/roce_hybrid_timing.txt").exists(),
        'ib_timing.txt': Path("/workspace/ib_timing.txt").exists(),
        'nccl_config.env': Path("/workspace/nccl_config.env").exists(),
    }
    
    required_count = sum(required_files.values())
    optional_count = sum(optional_files.values())
    
    print(f"  Required artifacts: {required_count}/3")
    print(f"  Optional artifacts: {optional_count}/5")
    
    # All required files must exist
    missing_required = [name for name, exists in required_files.items() if not exists]
    assert not missing_required, f"Missing required files: {', '.join(missing_required)}"
    
    print(f"✓ Solution completeness: {required_count + optional_count}/8 total artifacts")


if __name__ == "__main__":
    print("=" * 70)
    print("NCCL Optimization Tests: RoCEv2 (PFC/ECN/Hybrid) vs InfiniBand")
    print("=" * 70)
    print()
    print("NOTE: This validates configuration knowledge in a simulated environment.")
    print("      Real deployment would use actual multi-GPU hardware.")
    print()
    
    tests = [
        ("Baseline timing file", test_baseline_timing_exists),
        ("Optimized timing file", test_optimized_timing_exists),
        ("Minimum 3x speedup", test_required_speedup),
        ("PFC mode (if tested)", test_pfc_mode_if_present),
        ("ECN mode (if tested)", test_ecn_mode_if_present),
        ("Hybrid mode (if tested)", test_hybrid_mode_if_present),
        ("InfiniBand baseline (if tested)", test_infiniband_baseline_if_present),
        ("RoCEv2 ≥90% of IB", test_roce_vs_ib_comparison),
        ("Optimization report", test_optimization_report_exists),
        ("Report: congestion control", test_report_discusses_congestion_control),
        ("Report: NCCL configuration", test_report_has_nccl_configuration),
        ("NCCL config (if provided)", test_nccl_config_env_if_present),
        ("Solution completeness", test_solution_completeness),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"[TEST] {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    sys.exit(0 if failed == 0 else 1)

# NCCL Optimization: RoCEv2 (PFC vs ECN) vs InfiniBand

## Background

You are optimizing NVIDIA NCCL for distributed multi-GPU training in a modern AI datacenter. Your challenge: **Can RoCEv2 Ethernet match InfiniBand performance?**

This mirrors real-world deployments like **xAI's Colossus supercluster** (200k+ GPUs) which uses NVIDIA Spectrum-X Ethernet with advanced RoCEv2 congestion control to achieve 95%+ of InfiniBand throughput at massive scale.

## Environment

Ubuntu 22.04 with:
- **4 NVIDIA GPUs** (simulated A100/H100-equivalent)
- **CUDA 12.4** with drivers
- **NCCL** (bundled with PyTorch)
- **Configurable RoCEv2 fabric** with PFC, ECN, and hybrid modes
- **InfiniBand emulation** (baseline reference)
- **PyTorch 2.5** with distributed training

## The Challenge

You'll test **three congestion control strategies** for RoCEv2:

1. **PFC-Only** (Priority Flow Control)
   - Lossless Ethernet via pause frames
   - Simple but risks head-of-line blocking
   
2. **ECN-Only** (Explicit Congestion Notification with DCQCN)
   - Rate-based congestion control
   - Scales better, used by xAI/Azure/Meta
   
3. **Hybrid** (PFC + ECN)
   - ECN for normal operation, PFC as safety net
   - Industry best practice (Spectrum-X)

Compare each against **native InfiniBand** to see which RoCEv2 mode gets closest.

## Current State

Baseline performance is **poor** (~150ms/iter) due to:
- TCP fallback (RDMA disabled)
- Wrong GID index
- No GPUDirect RDMA
- Suboptimal congestion control

## Your Mission

### Step 1: Initial Diagnosis (10 points)
- Run baseline PyTorch DDP benchmark
- Confirm TCP fallback with `NCCL_DEBUG=INFO`
- Document poor performance (~150ms/iter)

### Step 2: Environment Inspection (10 points)
```bash
# Check RDMA devices
ibv_devinfo

# Review congestion control options
./configure_congestion_control.sh pfc
./configure_congestion_control.sh ecn
./configure_congestion_control.sh hybrid

# Check current NCCL settings
env | grep NCCL
```

### Step 3: RoCEv2 with PFC-Only (20 points)
Configure lossless Ethernet using Priority Flow Control:

```bash
# Set PFC mode
export ROCE_MODE=pfc
export NCCL_IB_TC=5              # Traffic class with PFC
export NCCL_IB_GID_INDEX=3       # RoCE v2 GID
export NCCL_IB_DISABLE=0         # Enable RDMA
export NCCL_NET=IB               # Use IB plugin
export NCCL_SOCKET_IFNAME=eth0   # RoCEv2 interface
export NCCL_IB_HCA=mlx5_0        # RDMA device
export NCCL_NET_GDR_LEVEL=5      # GPUDirect RDMA
```

Run PyTorch DDP test and measure performance.

**Target**: <60ms per iteration (2.5x speedup)

### Step 4: RoCEv2 with ECN-Only (DCQCN) (20 points)
Configure rate-based congestion control using ECN:

```bash
# Set ECN mode
export ROCE_MODE=ecn
export NCCL_IB_TC=5              # TC 5 required for ECN/DCQCN
# ... (same RDMA settings as PFC)
```

**DCQCN Algorithm** automatically handles:
- Congestion detection via ECN marking
- Rate reduction (alpha parameter)
- Smooth rate recovery (additive increase)

Run PyTorch DDP test and compare to PFC mode.

**Target**: <50ms per iteration (3x speedup, better than PFC)

### Step 5: RoCEv2 Hybrid Mode (15 points)
Test the hybrid PFC+ECN approach:

```bash
# Set hybrid mode
export ROCE_MODE=hybrid
export NCCL_IB_TC=5
# ... (same RDMA settings)
```

This combines ECN's efficiency with PFC's safety net.

**Target**: <45ms per iteration (3.3x+ speedup, best RoCEv2 performance)

### Step 6: InfiniBand Baseline (10 points)
Switch to native InfiniBand for comparison:

```bash
export NCCL_IB_HCA=mlx5_1        # IB device
export NCCL_SOCKET_IFNAME=ib0    # IB interface
export NCCL_IB_GID_INDEX=1       # IB GID
```

**Target**: <43ms per iteration (3.5x speedup, IB reference)

### Step 7: Analysis & Documentation (15 points)
Create `/workspace/optimization_report.md` with:

#### Required Analysis:
1. **PFC vs ECN Trade-offs**:
   - Which mode performed better and why?
   - PFC pros/cons (predictability vs head-of-line blocking)
   - ECN pros/cons (scalability vs tuning complexity)
   - Hybrid advantages

2. **RoCEv2 vs InfiniBand**:
   - Did best RoCEv2 mode reach 90%+ of IB performance?
   - What's the performance gap and why?
   - When would you choose RoCEv2 over IB?

3. **Configuration Details**:
   - All NCCL environment variables used
   - GID index selection rationale
   - Traffic class configuration
   - GPUDirect RDMA setup

4. **Performance Results**:
   - Table comparing all modes (PFC, ECN, Hybrid, IB)
   - Iteration times and speedup vs baseline
   - NCCL log evidence of RDMA usage

## Available Tools

### Benchmarking
```bash
# Create baseline
python3 pytorch_ddp_test.py --baseline

# Test optimized config
python3 pytorch_ddp_test.py
```

### Diagnostics
```bash
# RDMA devices
ibv_devinfo

# Congestion control modes
./configure_congestion_control.sh {pfc|ecn|hybrid}

# Network config
ip addr show

# GPU topology
nvidia-smi-topo

# NCCL settings
env | grep NCCL
```

### Key NCCL Variables
```bash
NCCL_DEBUG=INFO              # Detailed logging
NCCL_IB_DISABLE=0            # Enable RDMA
NCCL_NET=IB                  # Use IB plugin
NCCL_IB_GID_INDEX=3          # RoCE v2 GID
NCCL_IB_TC=5                 # Traffic class
NCCL_SOCKET_IFNAME=eth0      # Network interface
NCCL_NET_GDR_LEVEL=5         # GPUDirect RDMA
NCCL_IB_HCA=mlx5_0           # RDMA device
```

## Required Output Files

Your solution must create these files in `/workspace/`:

1. **`baseline_timing.txt`** - Single float (seconds) for TCP baseline performance
2. **`optimized_timing.txt`** - Single float (seconds) for best optimized mode
3. **`optimization_report.md`** - Detailed analysis (≥800 chars) including:
   - PFC vs ECN vs Hybrid comparison
   - Performance results table
   - NCCL configuration used
   - Analysis of why RoCEv2 can/cannot match InfiniBand

**Optional but recommended** (for full credit):
- `roce_pfc_timing.txt` - PFC mode timing
- `roce_ecn_timing.txt` - ECN mode timing  
- `roce_hybrid_timing.txt` - Hybrid mode timing
- `ib_timing.txt` - InfiniBand baseline timing
- `nccl_config.env` - NCCL environment variables used

## Success Criteria

Your solution must achieve:

1. ✅ **PFC Mode**: <60ms/iter (2.5x speedup minimum)
2. ✅ **ECN Mode**: <50ms/iter (3x speedup minimum)
3. ✅ **Hybrid Mode**: <45ms/iter (3.3x speedup minimum)
4. ✅ **InfiniBand**: <43ms/iter (reference)
5. ✅ **Best RoCEv2 ≥ 90% of IB performance**
6. ✅ **Report** with PFC vs ECN analysis (≥800 chars)
7. ✅ **No TCP fallback** in NCCL logs

## Real-World Context

### xAI Colossus Supercluster
- **200,000+ GPUs** in Memphis datacenter
- **NVIDIA Spectrum-X Ethernet** with RoCEv2
- **Hybrid PFC+ECN** (DCQCN algorithm)
- **95%+ network utilization** (near-IB performance)
- **Zero packet loss** at massive scale
- Powers Grok AI training

### Why This Matters
- InfiniBand doesn't scale to 100k+ GPUs economically
- RoCEv2 with proper tuning can match IB performance
- PFC alone doesn't scale (pause storms)
- ECN/DCQCN is the future for hyperscale AI
- Wrong configuration = 3x slower training = $$$$ wasted

## Tips

- Start simple: Get basic RDMA working first
- Use `NCCL_DEBUG=INFO` to verify transport
- **CRITICAL**: Look for "NET/IB" not "NET/Socket" in PyTorch output logs
- Save PyTorch output to verify NCCL transport: `python3 pytorch_ddp_test.py 2>&1 | tee nccl.log`
- GID index 3 is typically RoCE v2
- TC 5 works for all congestion modes
- ECN mode should outperform PFC mode
- Hybrid mode should be best overall
- IB is the gold standard reference
- **Verify your configuration works** - don't just write timing files!

## Time Limit

**20 minutes** to complete all tests and analysis.

Good luck optimizing for hyperscale! 🚀

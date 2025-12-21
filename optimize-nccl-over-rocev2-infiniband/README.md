# NCCL Optimization: RoCEv2 (PFC vs ECN) vs InfiniBand

**Terminal-Bench 2.0 Task** | **Difficulty: Hard** | **Time: 20 minutes**

## Overview

This task challenges AI agents to optimize NCCL for distributed GPU training by testing **three different congestion control strategies** for RoCEv2 and comparing against native InfiniBand. Can RoCEv2 Ethernet match InfiniBand performance?

This mirrors real-world deployments like **xAI's Colossus supercluster** (200k+ GPUs on NVIDIA Spectrum-X Ethernet), which achieves 95%+ of InfiniBand throughput using advanced RoCEv2 congestion control.

## The Challenge

### Test Three RoCEv2 Congestion Control Modes:

1. **PFC-Only (Priority Flow Control)**
   - Lossless Ethernet via pause frames
   - Target: 2.5x speedup (72% of InfiniBand)
   - Simple but doesn't scale (pause storms)

2. **ECN-Only (DCQCN Algorithm)**
   - Rate-based congestion control
   - Target: 3.0x speedup (88% of InfiniBand)
   - Scales to hyperscale (xAI, Azure, Meta use this)

3. **Hybrid (PFC + ECN)**
   - ECN primary, PFC backup
   - Target: 3.3x speedup (95% of InfiniBand)
   - Industry best practice (Spectrum-X)

### Compare Against:

4. **Native InfiniBand**
   - Reference baseline
   - Target: 3.5x speedup (100%)
   - Gold standard

## Success Criteria

✅ Test all three RoCEv2 modes + InfiniBand baseline  
✅ Achieve ≥3x overall speedup vs TCP baseline  
✅ **Best RoCEv2 mode ≥90% of InfiniBand performance**  
✅ Comprehensive report analyzing PFC vs ECN trade-offs (≥800 chars)  
✅ No TCP fallback in NCCL logs  

## Important: Simulated Environment

**This task uses a simulated RDMA environment** because:
- Multi-GPU hardware is expensive and not available in standard CI/CD
- Terminal-Bench 2.0 focuses on **knowledge and reasoning**, not execution
- Tests validate correct NCCL configuration understanding

**For real deployment**:
- Harbor could mount actual GPU nodes with RDMA hardware
- PyTorch would execute real distributed training
- NCCL would perform actual RDMA operations
- Tests would verify real network traffic and GPU communication

**What this tests**:
✅ Understanding of NCCL environment variables  
✅ Knowledge of PFC vs ECN trade-offs  
✅ Ability to reason about congestion control  
✅ Analysis and documentation skills  
❌ Actual GPU/RDMA execution (simulated)

The simulated results are based on real-world data from xAI Colossus, NVIDIA benchmarks, and academic papers.

## Why This Task Matters

### Real-World Relevance

This task replicates the actual optimization work done by ML Infrastructure Engineers at:

- **xAI (Colossus)**: 200k+ GPUs on RoCEv2 with Hybrid PFC+ECN
- **Meta**: AI training clusters with ECN/DCQCN
- **Microsoft Azure**: NDv5 instances with RoCEv2
- **Google Cloud**: A3 instances with optimized Ethernet

### Key Learning Objectives

1. **Congestion Control Fundamentals**:
   - PFC pause frames vs ECN rate adaptation
   - DCQCN algorithm (Data Center Quantized Congestion Notification)
   - Why PFC alone doesn't scale to 100k+ GPUs

2. **NCCL Configuration**:
   - GID index selection (RoCE v2 at index 3)
   - Traffic class mapping (TC 5 for PFC/ECN)
   - GPUDirect RDMA setup

3. **Performance Analysis**:
   - Why ECN outperforms PFC at scale
   - When to choose RoCEv2 vs InfiniBand
   - Cost/performance trade-offs

4. **Systems Debugging**:
   - NCCL log interpretation
   - RDMA device inspection
   - Multi-variable configuration tuning

## Task Structure

```
optimize-nccl-over-rocev2-infiniband/
├── instruction.md                          # Student-facing task description
├── task.toml                               # Task metadata
├── README.md                               # This file
│
├── environment/
│   ├── Dockerfile                          # CUDA, PyTorch environment
│   ├── pytorch_ddp_test.py                 # Training benchmark
│   ├── configure_congestion_control.sh     # PFC/ECN/Hybrid mode config
│   ├── show_rocev2_config.sh               # Educational PFC/ECN explainer
│   ├── mock_ibv_devinfo.sh                 # RDMA device simulation
│   └── ...
│
├── solution/
│   └── solve.sh                            # Reference solution (tests all modes)
│
└── tests/
    ├── test.sh                             # Test runner
    └── test_outputs.py                     # Comprehensive test suite
```

## Educational Value

### PFC vs ECN Trade-Off Analysis

Students will learn:

**PFC (Priority Flow Control)**:
- ✅ Simple, predictable
- ✅ True lossless (zero packet loss)
- ❌ Head-of-line blocking
- ❌ Pause frame storms at scale
- ❌ Doesn't scale beyond ~10k GPUs

**ECN (Explicit Congestion Notification)**:
- ✅ Scales to 100k+ GPUs
- ✅ Smooth rate adaptation (DCQCN)
- ✅ Better fabric utilization
- ❌ More complex tuning
- ❌ Requires end-to-end support

**Hybrid (PFC + ECN)**:
- ✅ Best of both worlds
- ✅ 95%+ of IB performance
- ✅ Used by xAI, Azure, etc.
- ❌ Most complex to tune

### xAI Colossus Connection

The Hybrid mode tested in this task is exactly what **xAI's Colossus** uses:

- **200,000+ NVIDIA GPUs** (Memphis datacenter)
- **NVIDIA Spectrum-X Ethernet** switches
- **RoCEv2 with Hybrid PFC+ECN** (DCQCN algorithm)
- **95%+ network utilization** (our task target: ≥90%)
- **Zero packet loss** at massive scale
- Powers **Grok AI** training

## Difficulty Calibration

**Expected Pass Rate**: 30-50% for frontier AI agents

**Why Hard?**

1. **Multi-Mode Testing**: Must test 3 RoCEv2 modes + IB (4 configurations)
2. **Niche Knowledge**: PFC/ECN/DCQCN details rare in training data
3. **Complex Analysis**: Must explain PFC vs ECN trade-offs
4. **Multi-Variable Tuning**: Many interconnected NCCL settings
5. **Comparative Reasoning**: Must achieve 90% of IB target
6. **Real-World Constraints**: Mirrors actual hyperscale challenges

**Why Solvable?**

- All information in public NVIDIA/xAI documentation
- Logical debugging process
- Clear success metrics
- Step-by-step progression through modes

## Performance Expectations

| Mode | Iteration Time | Speedup | % of IB | Scalability |
|------|---------------|---------|---------|-------------|
| Baseline (TCP) | 150ms | 1.0x | 28% | N/A |
| RoCEv2 PFC | 58ms | 2.59x | 72% | Small (<10k GPUs) |
| RoCEv2 ECN | 48ms | 3.13x | 88% | Hyperscale (100k+) |
| **RoCEv2 Hybrid** | **44ms** | **3.41x** | **95%** ✓ | **Hyperscale (200k+)** |
| InfiniBand | 42ms | 3.57x | 100% | Medium (<50k) |

## Key Technical Concepts

### DCQCN Algorithm (ECN Mode)

```
1. Switch detects queue buildup (buffer > K_min)
2. Switch marks packet headers with ECN bit
3. Receiver sends CNP (Congestion Notification Packet)
4. Sender reduces rate by alpha (e.g., 50%)
5. Rate increases additively when congestion clears
6. Smooth, stable convergence
```

### Hybrid Mode Operation

```
Light congestion:
  └─> ECN marks packets → DCQCN reduces rate

Moderate congestion:
  └─> Continued ECN marking → Rate adapts smoothly

Severe congestion (>85% buffer):
  └─> PFC pause frames → Safety net prevents loss
```

### Why RoCEv2 Can Match InfiniBand

1. **Modern NICs**: ConnectX-7/8 hardware-accelerate DCQCN
2. **Optimized switches**: Spectrum-X minimizes ECN latency
3. **GPUDirect RDMA**: Zero-copy same as InfiniBand
4. **Tuned thresholds**: Proper ECN settings prevent over-marking
5. **Economics**: Ethernet scales better than IB at 100k+ GPUs

## Running the Task

### Via Harbor Framework

```bash
cd optimize-nccl-over-rocev2-infiniband
harbor run .
```

### Manual Testing

```bash
# Build Docker environment
docker build -t nccl-pfc-ecn-task ./environment

# Run container
docker run -it --rm nccl-pfc-ecn-task

# Inside container - run solution
bash /solution/solve.sh

# Run tests
/tests/test.sh
```

## Sample Solution Output

```
[Step 3] RoCEv2 with PFC-Only Mode
✓ RoCEv2 PFC: 58ms/iter (2.59x speedup)

[Step 4] RoCEv2 with ECN-Only Mode (DCQCN)
✓ RoCEv2 ECN: 48ms/iter (3.13x speedup)

[Step 5] RoCEv2 Hybrid Mode (PFC + ECN)
✓ RoCEv2 Hybrid: 44ms/iter (3.41x speedup)

[Step 6] InfiniBand Reference
✓ InfiniBand: 42ms/iter (3.57x speedup)

✓ Best RoCEv2 reached 95.5% of InfiniBand performance!
```

## References

- [xAI Colossus](https://x.ai/blog/colossus) - 200k GPU cluster architecture
- [NVIDIA Spectrum-X](https://www.nvidia.com/en-us/networking/products/ethernet/spectrum-x/) - RoCEv2 networking platform
- [DCQCN Paper](https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p523.pdf) - Original DCQCN algorithm
- [NVIDIA NCCL Docs](https://docs.nvidia.com/deeplearning/nccl/) - NCCL environment variables
- [RoCEv2 Congestion Mgmt](https://enterprise-support.nvidia.com/s/article/understanding-rocev2-congestion-management) - NVIDIA guide

## Task Evolution

**Version 1.0** (Initial): Basic NCCL optimization  
**Version 1.1** (TC 5 + PFC): Added PFC with TC 5  
**Version 1.2** (PFC vs ECN): Added ECN and comparison  
**Version 2.0** (Current): **Full PFC vs ECN vs Hybrid vs IB comparison** (xAI Colossus style)

## Contributing

This task is part of Terminal-Bench 2.0. To suggest improvements:

1. Test with actual multi-GPU hardware
2. Add more congestion control scenarios
3. Extend to multi-node configurations
4. Add NUMA affinity optimization
5. Create difficulty variants (easy/medium/hard)

## License

Part of Terminal-Bench 2.0 benchmark suite.

---

**Ready to test if AI agents can optimize like xAI's infrastructure team?** 🚀

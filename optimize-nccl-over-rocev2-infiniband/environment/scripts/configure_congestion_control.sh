#!/bin/bash
# Script to configure RoCEv2 congestion control modes
# Simulates ethtool, sysctl, and mlnx_qos configuration

MODE="${1:-hybrid}"  # Options: pfc, ecn, hybrid

echo "=================================================="
echo "RoCEv2 Congestion Control Configuration"
echo "=================================================="
echo "Mode: $MODE"
echo ""

case "$MODE" in
    pfc)
        echo "Configuring PFC-Only Mode (Lossless Pause-Based)"
        echo "=================================================="
        cat > /tmp/roce_config.txt << 'EOF'
# PFC-Only Configuration
# =====================

Interface: eth0 (mlx5_0)
Congestion Control: PFC (Priority Flow Control)

PFC Configuration:
  Enabled Priorities: 3, 5
  Priority 3: COS 3 (Custom)
  Priority 5: COS 5 (Standard)

  XOFF Threshold: 70% buffer
  XON Threshold: 30% buffer
  Buffer Size: 512 KB per priority

  Pause Frame Generation: Enabled
  Pause Frame Response: Enabled

Traffic Class Mapping:
  NCCL_IB_TC=3 or NCCL_IB_TC=5 (both work)
  Recommended: TC 5 for compatibility

Advantages:
  + Simple, deterministic behavior
  + Zero packet loss (true lossless)
  + Predictable latency under congestion
  + Works well in small-to-medium scale

Disadvantages:
  - Risk of head-of-line blocking
  - Can cause pause frame storms
  - Doesn't scale well to large fabrics
  - All-or-nothing flow control

Expected Performance:
  Bandwidth: 160-180 GB/s (85-95% of IB)
  Latency: Low under light load, spiky under congestion
  Tail latency: Higher variance due to pauses

ECN Status: DISABLED
DCQCN Algorithm: DISABLED
EOF
        ;;

    ecn)
        echo "Configuring ECN-Only Mode (Rate-Based)"
        echo "======================================"
        cat > /tmp/roce_config.txt << 'EOF'
# ECN-Only Configuration
# ======================

Interface: eth0 (mlx5_0)
Congestion Control: ECN (Explicit Congestion Notification)

ECN Configuration:
  ECN Marking: Enabled
  Algorithm: DCQCN (Data Center Quantized CN)

  Priority 5 Thresholds:
    Minimum (K_min): 150 KB
    Maximum (K_max): 1500 KB
    Marking Probability: 100% (between min/max)

  DCQCN Parameters:
    Alpha (rate decrease): 0.5
    CNP interval: 50 µs
    Rate increase: AI (Additive Increase)
    Fast recovery: Enabled
    Byte counter: 150 KB

Traffic Class Mapping:
  NCCL_IB_TC=5 (required for ECN/DCQCN)
  DSCP marking: 26 -> Priority 5

Advantages:
  + Scales to large fabrics (100k+ GPUs)
  + No pause frames = no head-of-line blocking
  + Smooth rate adaptation
  + Better fabric utilization
  + Used by xAI Colossus, Azure, etc.

Disadvantages:
  - More complex tuning (many parameters)
  - Requires careful threshold selection
  - Slight packet marking overhead
  - Needs end-to-end ECN support

Expected Performance:
  Bandwidth: 170-190 GB/s (90-100% of IB)
  Latency: Consistently low, smooth distribution
  Tail latency: Better than PFC (no pause spikes)

PFC Status: DISABLED
Pause Frames: DISABLED
EOF
        ;;

    hybrid)
        echo "Configuring Hybrid Mode (PFC + ECN / DCQCN)"
        echo "==========================================="
        cat > /tmp/roce_config.txt << 'EOF'
# Hybrid PFC + ECN Configuration
# ===============================

Interface: eth0 (mlx5_0)
Congestion Control: Hybrid (PFC + DCQCN)

PFC Configuration:
  Enabled on Priority 5 (backup mechanism)
  XOFF Threshold: 85% buffer (high, used rarely)
  XON Threshold: 40% buffer

ECN/DCQCN Configuration:
  Primary mechanism: ECN marking with DCQCN
  Priority 5 ECN Thresholds:
    K_min: 150 KB (start marking)
    K_max: 1500 KB (full marking)

  DCQCN tuned for:
    Fast response to congestion (tight alpha)
    Smooth rate recovery
    Minimal marking overhead

Interaction:
  1. Light congestion: ECN marks packets, rate adapts
  2. Moderate congestion: DCQCN reduces rate smoothly
  3. Severe congestion: PFC kicks in as safety net

Traffic Class: NCCL_IB_TC=5

Advantages:
  + Best of both: ECN efficiency + PFC safety
  + Handles micro-bursts well
  + Scales better than PFC-only
  + More robust than ECN-only
  + Industry best practice (Spectrum-X, etc.)

Disadvantages:
  - Most complex to tune
  - Two mechanisms can interact unpredictably
  - Requires careful threshold separation

Expected Performance:
  Bandwidth: 180-200 GB/s (95-105% of IB possible!)
  Latency: Lowest and most stable
  Tail latency: Best overall (ECN smoothness + PFC safety)

This is what xAI Colossus uses for 200k+ GPUs!
EOF
        ;;

    *)
        echo "Unknown mode: $MODE"
        echo "Usage: $0 {pfc|ecn|hybrid}"
        exit 1
        ;;
esac

cat /tmp/roce_config.txt
echo ""
echo "=================================================="
echo "Configuration saved to /tmp/roce_config.txt"
echo ""
echo "To apply this mode, set:"
echo "  export ROCE_MODE=$MODE"
echo "  export NCCL_IB_TC=5"
echo "=================================================="

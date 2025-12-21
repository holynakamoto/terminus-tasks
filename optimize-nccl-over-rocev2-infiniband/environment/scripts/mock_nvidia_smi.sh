#!/bin/bash
# Mock nvidia-smi topo command to show GPU topology

cat << 'EOF'
        GPU0    GPU1    GPU2    GPU3    mlx5_0  mlx5_1  CPU Affinity    NUMA Affinity
GPU0     X      NV12    NV12    NV12    NODE    SYS     0-31            0
GPU1    NV12     X      NV12    NV12    NODE    SYS     0-31            0
GPU2    NV12    NV12     X      NV12    SYS     NODE    32-63           1
GPU3    NV12    NV12    NV12     X      SYS     NODE    32-63           1
mlx5_0  NODE    NODE    SYS     SYS      X      SYS
mlx5_1  SYS     SYS     NODE    NODE    SYS      X

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  mlx5_0: Mellanox MT4124 ConnectX-6 (RoCEv2) - Connected to NUMA 0
  mlx5_1: Mellanox MT4125 ConnectX-6 (InfiniBand) - Connected to NUMA 1
EOF

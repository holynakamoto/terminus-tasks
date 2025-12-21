#!/usr/bin/env python3
"""
PyTorch DDP (DistributedDataParallel) test script for NCCL optimization task.
This simulates a multi-GPU training workload to measure NCCL performance.
"""

import os
import sys
import time

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP


def setup_distributed():
    """Initialize distributed training environment."""
    # Get rank and world size from environment or use defaults
    rank = int(os.environ.get("RANK", 0))
    world_size = int(os.environ.get("WORLD_SIZE", 4))
    local_rank = int(os.environ.get("LOCAL_RANK", rank))

    # Initialize process group with NCCL backend
    if not dist.is_initialized():
        dist.init_process_group(
            backend="nccl", init_method="env://", world_size=world_size, rank=rank
        )

    # Set device for this process
    torch.cuda.set_device(local_rank)

    return rank, world_size, local_rank


def create_model():
    """Create a simple model for testing."""
    # Large enough model to generate significant NCCL traffic
    model = nn.Sequential(
        nn.Linear(2048, 8192),
        nn.ReLU(),
        nn.Linear(8192, 8192),
        nn.ReLU(),
        nn.Linear(8192, 8192),
        nn.ReLU(),
        nn.Linear(8192, 2048),
    ).cuda()

    return model


def run_training_benchmark(num_iterations=50, warmup_iterations=10):
    """Run a training benchmark and measure iteration time."""

    rank, world_size, local_rank = setup_distributed()

    if rank == 0:
        print("=" * 60)
        print("PyTorch DDP Training Benchmark")
        print("=" * 60)
        print(f"World size: {world_size}")
        print(f"NCCL version: {torch.cuda.nccl.version()}")
        print(f"CUDA device: {torch.cuda.get_device_name(local_rank)}")
        print("")
        print("NCCL Environment Variables:")
        for key in sorted(os.environ.keys()):
            if "NCCL" in key:
                print(f"  {key}={os.environ[key]}")
        print("")

    # Create model and wrap with DDP
    model = create_model()
    model = DDP(model, device_ids=[local_rank])

    # Create optimizer
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

    # Loss function
    criterion = nn.MSELoss()

    # Dummy dataset
    batch_size = 128
    input_size = 2048

    if rank == 0:
        print("Running warmup iterations...")

    # Warmup iterations
    for i in range(warmup_iterations):
        data = torch.randn(batch_size, input_size).cuda()
        target = torch.randn(batch_size, 2048).cuda()

        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    # Synchronize before timing
    if dist.is_initialized():
        dist.barrier()
    torch.cuda.synchronize()

    if rank == 0:
        print(f"Running {num_iterations} timed iterations...")

    # Timed iterations
    iteration_times = []

    for i in range(num_iterations):
        data = torch.randn(batch_size, input_size).cuda()
        target = torch.randn(batch_size, 2048).cuda()

        start_time = time.time()

        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        # Ensure all NCCL operations complete
        torch.cuda.synchronize()

        iteration_time = time.time() - start_time
        iteration_times.append(iteration_time)

        if rank == 0 and (i + 1) % 10 == 0:
            avg_time = sum(iteration_times[-10:]) / 10
            print(f"  Iterations {i - 8}-{i + 1}: avg {avg_time * 1000:.2f} ms/iter")

    # Calculate statistics
    avg_iteration_time = sum(iteration_times) / len(iteration_times)
    min_iteration_time = min(iteration_times)
    max_iteration_time = max(iteration_times)

    # Synchronize before gathering results
    if dist.is_initialized():
        dist.barrier()

    if rank == 0:
        print("")
        print("=" * 60)
        print("Results")
        print("=" * 60)
        print(f"Average iteration time: {avg_iteration_time * 1000:.2f} ms")
        print(f"Min iteration time:     {min_iteration_time * 1000:.2f} ms")
        print(f"Max iteration time:     {max_iteration_time * 1000:.2f} ms")
        print(f"Throughput:             {1.0 / avg_iteration_time:.2f} iter/s")
        print("=" * 60)

        # Save timing results
        with open("/workspace/optimized_timing.txt", "w") as f:
            f.write(f"{avg_iteration_time}\n")

        print("")
        print("Timing saved to /workspace/optimized_timing.txt")

    # Cleanup
    if dist.is_initialized():
        dist.destroy_process_group()

    return avg_iteration_time


def simulate_baseline():
    """Simulate baseline performance with TCP fallback."""
    # This represents the slow performance with TCP/IP transport
    # Typically 3-5x slower than optimized RDMA
    baseline_time = 0.150  # 150ms per iteration (simulated slow performance)

    print("=" * 60)
    print("Simulated Baseline Performance (TCP Fallback)")
    print("=" * 60)
    print(f"Average iteration time: {baseline_time * 1000:.2f} ms")
    print("=" * 60)

    with open("/workspace/baseline_timing.txt", "w") as f:
        f.write(f"{baseline_time}\n")

    print("Baseline timing saved to /workspace/baseline_timing.txt")

    return baseline_time


def simulate_optimized_run():
    """Simulates performance based on environment variables."""
    roce_mode = os.environ.get("ROCE_MODE", "").lower().strip()
    nccl_ib_hca = os.environ.get("NCCL_IB_HCA", "")
    nccl_socket_ifname = os.environ.get("NCCL_SOCKET_IFNAME", "")
    
    # Determine configuration based on environment
    # InfiniBand: HCA is mlx5_1 (IB device) or interface is ib0
    # Check HCA first as it's the strongest indicator
    is_ib = (nccl_ib_hca == "mlx5_1" or nccl_socket_ifname == "ib0")
    
    # Logic to determine timing based on configuration (check IB first)
    if is_ib:
        timing_ms = 42.0
        timing_sec = timing_ms / 1000.0
        label = "InfiniBand (Native IB)"
        filename = "/workspace/ib_timing.txt"
    elif roce_mode == "pfc":
        timing_ms = 58.0
        timing_sec = timing_ms / 1000.0
        label = "RoCEv2 PFC Mode"
        filename = "/workspace/roce_pfc_timing.txt"
    elif roce_mode == "ecn":
        timing_ms = 48.0
        timing_sec = timing_ms / 1000.0
        label = "RoCEv2 ECN Mode (DCQCN)"
        filename = "/workspace/roce_ecn_timing.txt"
    elif roce_mode == "hybrid":
        timing_ms = 44.0
        timing_sec = timing_ms / 1000.0
        label = "RoCEv2 Hybrid (PFC + ECN)"
        filename = "/workspace/roce_hybrid_timing.txt"
    else:
        # Default: TCP fallback or unoptimized
        timing_ms = 150.00
        timing_sec = timing_ms / 1000.0
        label = "TCP Fallback (Unoptimized)"
        filename = "/workspace/optimized_timing.txt"

    print("=" * 60)
    print(f"SIMULATION MODE: {label}")
    print("=" * 60)
    print("NCCL Environment Configuration:")
    for key in sorted(os.environ.keys()):
        if any(x in key.upper() for x in ["NCCL", "ROCE", "MASTER"]):
            print(f"  {key}={os.environ[key]}")
    print("")
    print(f"Simulated Average iteration time: {timing_ms:.2f} ms")
    print(f"  ({timing_sec:.3f} seconds)")
    print("=" * 60)

    # Save to the determined filename
    with open(filename, "w") as f:
        f.write(f"{timing_sec}\n")

    # Also save to optimized_timing.txt for consistency with solve.sh expectations
    # RoCE modes: update optimized_timing.txt (this is the "best" result so far)
    # IB: also write to optimized_timing.txt so solve.sh can move it
    if "roce" in filename or is_ib:
        with open("/workspace/optimized_timing.txt", "w") as f:
            f.write(f"{timing_sec}\n")

    print(f"Timing saved to {filename}")
    
    return timing_sec


if __name__ == "__main__":
    # Check if we're creating baseline or running optimized benchmark
    if len(sys.argv) > 1 and sys.argv[1] == "--baseline":
        simulate_baseline()
    else:
        # Check for GPUs. If none, run simulation mode based on environment variables.
        if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
            print("=" * 60)
            print("No GPUs detected. Running in SIMULATION MODE...")
            print("Performance will be simulated based on NCCL configuration.")
            print("=" * 60)
            print("")
            simulate_optimized_run()
        else:
            try:
                run_training_benchmark()
            except Exception as e:
                print(f"Error running benchmark: {e}", file=sys.stderr)
                print("")
                print("Falling back to SIMULATION MODE...")
                print("")
                simulate_optimized_run()

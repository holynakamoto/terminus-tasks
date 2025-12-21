FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    python3 \
    python3-pip \
    python3-dev \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA support (includes NCCL)
RUN pip3 install --no-cache-dir \
    torch==2.5.1 \
    torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu124

# Create mock RDMA devices and network interfaces
# These scripts simulate the presence of RDMA hardware
COPY scripts/setup_mock_rdma.sh /opt/setup_mock_rdma.sh
RUN chmod +x /opt/setup_mock_rdma.sh

# Create workspace
WORKDIR /workspace

# Set up intentionally broken NCCL configuration
# This is the starting point that needs to be fixed
ENV NCCL_DEBUG=WARN
ENV NCCL_IB_DISABLE=1
ENV NCCL_SOCKET_IFNAME=lo
ENV NCCL_NET=Socket
ENV NCCL_P2P_DISABLE=0
ENV NCCL_SHM_DISABLE=0

# Copy initial files
COPY pytorch_ddp_test.py /workspace/pytorch_ddp_test.py
COPY optimization_report_template.md /workspace/optimization_report_template.md
COPY scripts/configure_congestion_control.sh /workspace/configure_congestion_control.sh
COPY scripts/mock_ibv_devinfo.sh /usr/local/bin/ibv_devinfo
COPY scripts/mock_nvidia_smi.sh /usr/local/bin/nvidia-smi-topo

RUN chmod +x /workspace/configure_congestion_control.sh && \
    chmod +x /usr/local/bin/ibv_devinfo && \
    chmod +x /usr/local/bin/nvidia-smi-topo

# Initialize the mock RDMA environment on container start
RUN /opt/setup_mock_rdma.sh

CMD ["/bin/bash"]

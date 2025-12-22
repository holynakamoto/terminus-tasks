#!/bin/bash

# Use this file to solve the task.

set -e  # Exit on error to catch issues

echo "=== 1. CONTAINER/RUNTIME INFO ==="
echo "--- cgroup info for process 1 ---"
cat /proc/1/cgroup 2>/dev/null || echo "Cannot read /proc/1/cgroup"
echo ""
echo "--- Docker daemon access test ---"
docker info 2>/dev/null || echo "No Docker daemon access"
echo ""
echo "--- OS release ---"
cat /etc/os-release
echo ""
echo "--- System info ---"
uname -a
echo ""
echo "--- Running processes ---"
ps aux | head -20
echo ""
echo "--- Mount points ---"
cat /proc/mounts

echo ""
echo "=== 2. RESOURCE LIMITS ==="
echo "--- Ulimits ---"
ulimit -a
echo ""
echo "--- Memory limits (cgroup v1) ---"
cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo "No cgroup v1 memory limit"
echo ""
echo "--- Memory limits (cgroup v2) ---"
cat /sys/fs/cgroup/memory.max 2>/dev/null || echo "No cgroup v2 memory limit"
echo ""
echo "--- CPU limits (cgroup v2) ---"
cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo "No cgroup v2 CPU limit"
echo ""
echo "--- CPU pinning ---"
cat /sys/fs/cgroup/cpuset.cpus 2>/dev/null || echo "No CPU pinning info"
echo ""
echo "--- Available processors ---"
nproc
echo ""
echo "--- CPU count from /proc/cpuinfo ---"
cat /proc/cpuinfo | grep processor | wc -l
echo ""
echo "--- Memory usage ---"
free -h
echo ""
echo "--- Disk space ---"
df -h /

echo ""
echo "=== 3. BUILD/ENVIRONMENT SETUP TRACES ==="
echo "--- Root directory contents ---"
ls -la /
echo ""
echo "--- Environment variables ---"
env | sort
echo ""
echo "--- Search for buildspec.yaml ---"
find / -name buildspec.yaml 2>/dev/null || echo "No buildspec.yaml found"
echo ""
echo "--- Search for CodeBuild artifacts ---"
find / -name "*codebuild*" 2>/dev/null || echo "No CodeBuild artifacts found"
echo ""
echo "--- Common installation directories ---"
ls -la /opt/ 2>/dev/null || echo "No /opt directory"
ls -la /usr/local/ 2>/dev/null || echo "No /usr/local directory"
echo ""
echo "--- Available binaries ---"
which docker-compose docker git python3 pip3 2>/dev/null || echo "Some binaries not found"

echo ""
echo "=== 4. NETWORK/FILESYSTEM ==="
echo "--- DNS configuration ---"
cat /etc/resolv.conf
echo ""
echo "--- Host entries ---"
cat /etc/hosts
echo ""
echo "--- Standard mounts ---"
mount | grep -E "(proc|sys|dev)"
echo ""
echo "--- External network test (ping) ---"
ping -c 3 8.8.8.8 || echo "Ping failed"
echo ""
echo "--- External network test (curl) ---"
curl -I https://www.google.com || echo "Curl failed"
echo ""
echo "--- Write tests in different directories ---"
echo "write test /tmp" > /tmp/write_test.txt && cat /tmp/write_test.txt
echo "write test /app" > /app/write_test.txt && cat /app/write_test.txt 2>/dev/null || echo "Cannot write to /app"

echo ""
echo "=== 5. PYTHON/DEVELOPMENT ENVIRONMENT ==="
echo "--- Python version ---"
python3 --version
echo ""
echo "--- Pip version ---"
pip3 --version
echo ""
echo "--- Installed packages (first 20) ---"
pip3 list | head -20
echo ""
echo "--- Package installation test ---"
pip3 install numpy
echo ""
echo "--- Verification test ---"
python3 -c "import numpy, sys; print('NumPy version:', numpy.__version__); print('Python sys.path:', sys.path[:3])"

echo ""
echo "=== 6. SECURITY/ISOLATION ==="
echo "--- User context ---"
id
echo ""
echo "--- Sudo access ---"
sudo -l 2>/dev/null || echo "No sudo access"
echo ""
echo "--- Process capabilities ---"
cat /proc/self/status | grep -E "(Cap|Uid|Gid)" 2>/dev/null || echo "Cannot read capabilities"
echo ""
echo "--- Root directory access ---"
ls -la /root/ 2>/dev/null || echo "No /root access"

echo ""
echo "=== 7. GIT/SOURCE CONTROL ==="
echo "--- Git version ---"
git --version
echo ""
echo "--- Git configuration ---"
git config --list

echo ""
echo "RECON COMPLETE - RESOURCES PROBED"
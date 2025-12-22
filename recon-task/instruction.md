# Advanced Environment Reconnaissance Task

Your goal is to thoroughly probe the Harbor execution environment and reveal the effective "buildspec" and resource limits.

Perform the following steps and output a detailed report to STDOUT (include all command outputs verbatim):

=== 1. CONTAINER/RUNTIME INFO ===
- `cat /proc/1/cgroup`  # Detects Docker/K8s/containerd vs. bare EC2/CodeBuild
- `docker info || echo "No Docker daemon access"`  # If inside Docker
- `cat /etc/os-release`
- `uname -a`
- `ps aux`  # Running processes (might show agent harness)
- `cat /proc/mounts`  # Mount points and filesystem types

=== 2. RESOURCE LIMITS ===
- `ulimit -a`  # Open files, processes, etc.
- `cat /sys/fs/cgroup/memory/memory.limit_in_bytes || echo "No cgroup v1"`
- `cat /sys/fs/cgroup/memory.max || echo "No cgroup v2"`  # Memory limit
- `cat /sys/fs/cgroup/cpu.max || echo "No CPU limit"`
- `cat /sys/fs/cgroup/cpuset.cpus || echo "No CPU pinning"`
- `nproc`  # CPU cores
- `free -h`  # Available memory
- `df -h /`  # Disk space
- `cat /proc/cpuinfo | grep processor | wc -l`  # CPU count

=== 3. BUILD/ENVIRONMENT SETUP TRACES ===
- `ls -la /` 
- `env | sort`  # All env vars (might show AWS/CodeBuild hints like CODEBUILD_* if any)
- `find / -name buildspec.yaml 2>/dev/null || echo "No buildspec found"`
- `find / -name "*codebuild*" 2>/dev/null || echo "No CodeBuild artifacts"`
- `ls -la /opt/ /usr/local/ /etc/`  # Common installation dirs
- `which docker-compose docker git python3 pip3`  # Available binaries

=== 4. NETWORK/FILESYSTEM ===
- `cat /etc/resolv.conf`  # DNS setup
- `cat /etc/hosts`  # Host entries
- `mount | grep -E "(proc|sys|dev)"`  # Standard mounts
- Test external access: `ping -c 3 8.8.8.8`
- Test external access: `curl -I https://www.google.com`
- Write/read tests in various dirs (/tmp, /task, etc.):
  - `echo "write test /tmp" > /tmp/write_test.txt && cat /tmp/write_test.txt`
  - `echo "write test /app" > /app/write_test.txt && cat /app/write_test.txt 2>/dev/null || echo "Cannot write to /app"`

=== 5. PYTHON/DEVELOPMENT ENVIRONMENT ===
- `python3 --version`
- `pip3 --version`
- `pip3 list | head -20`  # First 20 packages
- Test package install: `pip3 install numpy`
- Verify install: `python3 -c "import numpy, sys; print('NumPy version:', numpy.__version__); print('Python sys.path:', sys.path[:3])"`

=== 6. SECURITY/ISOLATION ===
- `id`  # User context
- `sudo -l || echo "No sudo access"`
- `cat /proc/self/status | grep -E "(Cap|Uid|Gid)"`  # Capabilities
- `ls -la /root/ 2>/dev/null || echo "No /root access"`

=== 7. GIT/SOURCE CONTROL ===
- `git --version`
- `git config --list`
- Test git operations if needed

End with: "RECON COMPLETE - RESOURCES PROBED"
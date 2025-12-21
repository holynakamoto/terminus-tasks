#!/bin/bash
# Mock RDMA environment setup
# Creates reference files simulating RDMA hardware

echo "Setting up mock RDMA environment..."

# Create device info files in /tmp
cat > /tmp/rdma_device_info.txt << 'EOF'
hca_id: mlx5_0
transport: InfiniBand (0)
fw_ver: 22.40.1000
node_guid: 5065:f0ff:fe00:1234
sys_image_guid: 5065:f0ff:fe00:1234
vendor_id: 0x02c9
vendor_part_id: 4124
hw_ver: 0x0
board_id: MT_0000000123
phys_port_cnt: 1
    port:	1
        state: PORT_ACTIVE (4)
        max_mtu: 4096 (5)
        active_mtu: 4096 (5)
        sm_lid: 1
        port_lid: 2
        port_lmc: 0x00
        link_layer: Ethernet
        gid_tbl_len: 16
            GID[0]: fe80:0000:0000:0000:5265:f0ff:fe00:1234
            GID[1]: 0000:0000:0000:0000:0000:ffff:c0a8:0101
            GID[2]: fe80:0000:0000:0000:5265:f0ff:fe00:1235
            GID[3]: 0000:0000:0000:0000:0000:ffff:c0a8:0102, type: RoCE v2
EOF

cat > /tmp/network_info.txt << 'EOF'
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 4096
        inet 192.168.1.1  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::5265:f0ff:fe00:1234  prefixlen 64  scopeid 0x20<link>
        ether 50:65:f0:00:12:34  txqueuelen 1000  (Ethernet)

ib0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 2048
        inet 192.168.2.1  netmask 255.255.255.0  broadcast 192.168.2.255
        infiniband 80:00:00:48:fe:80:00:00:00:00:00:00:50:65:f0:ff:fe:00:12:34
EOF

# Store device count
echo "2" > /tmp/rdma_device_count.txt

# Create GID table for reference
cat > /tmp/gid_table.txt << 'EOF'
DEV  PORT  INDEX  GID                                      IPv4            VER  DEV
---  ----  -----  ---                                      ------------    ---  ---
mlx5_0  1    0     fe80:0000:0000:0000:5265:f0ff:fe00:1234                 v1   eth0
mlx5_0  1    1     0000:0000:0000:0000:0000:ffff:c0a8:0101 192.168.1.1     v1   eth0
mlx5_0  1    2     fe80:0000:0000:0000:5265:f0ff:fe00:1235                 v1   eth0
mlx5_0  1    3     0000:0000:0000:0000:0000:ffff:c0a8:0102 192.168.1.2     v2   eth0
mlx5_1  1    0     fe80:0000:0000:0000:5265:f0ff:fe00:5678                 v1   ib0
mlx5_1  1    1     0000:0000:0000:0000:0000:ffff:c0a8:0201 192.168.2.1     v1   ib0
mlx5_1  1    3     0000:0000:0000:0000:0000:ffff:c0a8:0202 192.168.2.2     v2   ib0
EOF

echo "Mock RDMA environment ready"
echo "Available devices: mlx5_0 (RoCEv2 on eth0), mlx5_1 (InfiniBand on ib0)"
echo "Reference files created in /tmp/"

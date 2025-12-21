#!/bin/bash
# Mock ibv_devinfo command that returns realistic RDMA device information

# Check if we're being asked for a specific device
if [ "$1" = "-d" ] && [ -n "$2" ]; then
    DEVICE="$2"
else
    DEVICE="all"
fi

if [ "$DEVICE" = "all" ] || [ "$DEVICE" = "mlx5_0" ]; then
cat << 'EOF'
hca_id:	mlx5_0
	transport:			InfiniBand (0)
	fw_ver:				22.40.1000
	node_guid:			5065:f0ff:fe00:1234
	sys_image_guid:			5065:f0ff:fe00:1234
	vendor_id:			0x02c9
	vendor_part_id:			4124
	hw_ver:				0x0
	board_id:			MT_0000000123
	phys_port_cnt:			1
		port:	1
			state:			PORT_ACTIVE (4)
			max_mtu:		4096 (5)
			active_mtu:		4096 (5)
			sm_lid:			1
			port_lid:		2
			port_lmc:		0x00
			link_layer:		Ethernet
			gid_tbl_len:		16
				GID[  0]:		fe80:0000:0000:0000:5265:f0ff:fe00:1234
				GID[  1]:		0000:0000:0000:0000:0000:ffff:c0a8:0101
				GID[  2]:		fe80:0000:0000:0000:5265:f0ff:fe00:1235
				GID[  3]:		0000:0000:0000:0000:0000:ffff:c0a8:0102, RoCE v2

EOF
fi

if [ "$DEVICE" = "all" ] || [ "$DEVICE" = "mlx5_1" ]; then
cat << 'EOF'
hca_id:	mlx5_1
	transport:			InfiniBand (0)
	fw_ver:				22.40.1000
	node_guid:			5065:f0ff:fe00:5678
	sys_image_guid:			5065:f0ff:fe00:5678
	vendor_id:			0x02c9
	vendor_part_id:			4125
	hw_ver:				0x0
	board_id:			MT_0000000124
	phys_port_cnt:			1
		port:	1
			state:			PORT_ACTIVE (4)
			max_mtu:		4096 (5)
			active_mtu:		4096 (5)
			sm_lid:			1
			port_lid:		3
			port_lmc:		0x00
			link_layer:		InfiniBand
			gid_tbl_len:		16
				GID[  0]:		fe80:0000:0000:0000:5265:f0ff:fe00:5678
				GID[  1]:		0000:0000:0000:0000:0000:ffff:c0a8:0201
				GID[  3]:		0000:0000:0000:0000:0000:ffff:c0a8:0202, RoCE v2

EOF
fi

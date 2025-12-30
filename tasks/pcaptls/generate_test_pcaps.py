#!/usr/bin/env python3
"""
Generate synthetic TLS pcap files for testing the TLS security analyzer.

This creates three test pcaps:
1. vulnerable_tls.pcap - Contains export-grade, RC4, and weak DH
2. secure_tls.pcap - Contains only modern secure TLS 1.3 traffic
3. mixed_tls.pcap - Mix of vulnerable and secure sessions
"""

from scapy.all import *
from scapy.layers.tls.all import *
from scapy.layers.tls.extensions import *
from scapy.layers.tls.handshake import TLSClientHello, TLSServerHello
import time
import os

# Disable Scapy warnings
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def create_vulnerable_pcap():
    """Create pcap with vulnerable TLS sessions."""
    print("Generating vulnerable_tls.pcap...")
    packets = []
    base_time = time.time() - 3600  # 1 hour ago
    
    # Session 1: Export-grade cipher (TLS_RSA_EXPORT_WITH_RC4_40_MD5)
    # Client Hello
    client_hello_1 = (
        Ether(src="00:11:22:33:44:55", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.100", dst="93.184.216.34") /
        TCP(sport=54321, dport=443, flags="PA", seq=1000, ack=1000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0301,  # TLS 1.0
                ciphers=[
                    0x0003,  # TLS_RSA_EXPORT_WITH_RC4_40_MD5 (export)
                    0x0004,  # TLS_RSA_WITH_RC4_128_MD5 (RC4)
                    0x0005,  # TLS_RSA_WITH_RC4_128_SHA (RC4)
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[23, 24, 25]),  # secp256r1, secp384r1, secp521r1
                ]
            )
        ])
    )
    client_hello_1.time = base_time
    packets.append(client_hello_1)
    
    # Server Hello
    server_hello_1 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:55") /
        IP(src="93.184.216.34", dst="192.168.1.100") /
        TCP(sport=443, dport=54321, flags="PA", seq=1000, ack=1500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0301,
                cipher=0x0003,  # Selected export-grade cipher
            )
        ])
    )
    server_hello_1.time = base_time + 0.1
    packets.append(server_hello_1)
    
    # Session 2: RC4 cipher (TLS_ECDHE_RSA_WITH_RC4_128_SHA)
    client_hello_2 = (
        Ether(src="00:11:22:33:44:56", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.101", dst="172.217.14.206") /
        TCP(sport=54322, dport=443, flags="PA", seq=2000, ack=2000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,  # TLS 1.2
                ciphers=[
                    0xC011,  # TLS_ECDHE_RSA_WITH_RC4_128_SHA (RC4)
                    0xC013,  # TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[23, 24, 256]),  # Including ffdhe2048
                ]
            )
        ])
    )
    client_hello_2.time = base_time + 1.0
    packets.append(client_hello_2)
    
    server_hello_2 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:56") /
        IP(src="172.217.14.206", dst="192.168.1.101") /
        TCP(sport=443, dport=54322, flags="PA", seq=2000, ack=2500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0xC011,  # Selected RC4 cipher
            )
        ])
    )
    server_hello_2.time = base_time + 1.1
    packets.append(server_hello_2)
    
    # Session 3: Weak DH (simulated with 512-bit DH group indicator)
    # Note: We can't easily create actual DH ServerKeyExchange in Scapy,
    # but we can signal weak DH through group selection
    client_hello_3 = (
        Ether(src="00:11:22:33:44:57", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.102", dst="198.41.214.162") /
        TCP(sport=54323, dport=443, flags="PA", seq=3000, ack=3000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,  # TLS 1.2
                ciphers=[
                    0x0033,  # TLS_DHE_RSA_WITH_AES_128_CBC_SHA
                    0x0039,  # TLS_DHE_RSA_WITH_AES_256_CBC_SHA
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[256, 257]),  # ffdhe2048, ffdhe3072
                ]
            )
        ])
    )
    client_hello_3.time = base_time + 2.0
    packets.append(client_hello_3)
    
    server_hello_3 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:57") /
        IP(src="198.41.214.162", dst="192.168.1.102") /
        TCP(sport=443, dport=54323, flags="PA", seq=3000, ack=3500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0x0033,  # Selected DHE cipher
            )
        ])
    )
    server_hello_3.time = base_time + 2.1
    packets.append(server_hello_3)
    
    # Session 4: Another export cipher (TLS_RSA_EXPORT_WITH_DES40_CBC_SHA)
    client_hello_4 = (
        Ether(src="00:11:22:33:44:58", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.103", dst="151.101.1.69") /
        TCP(sport=54324, dport=443, flags="PA", seq=4000, ack=4000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0301,  # TLS 1.0
                ciphers=[
                    0x0008,  # TLS_RSA_EXPORT_WITH_DES40_CBC_SHA (export)
                    0x000A,  # TLS_RSA_WITH_3DES_EDE_CBC_SHA
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
            )
        ])
    )
    client_hello_4.time = base_time + 3.0
    packets.append(client_hello_4)
    
    server_hello_4 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:58") /
        IP(src="151.101.1.69", dst="192.168.1.103") /
        TCP(sport=443, dport=54324, flags="PA", seq=4000, ack=4500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0301,
                cipher=0x0008,  # Selected export cipher
            )
        ])
    )
    server_hello_4.time = base_time + 3.1
    packets.append(server_hello_4)
    
    os.makedirs("test_captures", exist_ok=True)
    wrpcap("test_captures/vulnerable_tls.pcap", packets)
    print(f"  Created with {len(packets)} packets")


def create_secure_pcap():
    """Create pcap with secure TLS 1.3 sessions."""
    print("Generating secure_tls.pcap...")
    packets = []
    base_time = time.time() - 1800  # 30 minutes ago
    
    # Session 1: TLS 1.3 with modern ciphers
    client_hello_1 = (
        Ether(src="00:11:22:33:44:60", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.200", dst="93.184.216.34") /
        TCP(sport=55001, dport=443, flags="PA", seq=5000, ack=5000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,  # TLS 1.2 (TLS 1.3 negotiates from 1.2)
                ciphers=[
                    0x1301,  # TLS_AES_128_GCM_SHA256
                    0x1302,  # TLS_AES_256_GCM_SHA384
                    0x1303,  # TLS_CHACHA20_POLY1305_SHA256
                    0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
                    0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[29, 23, 24, 25, 256, 257, 258]),
                    TLS_Ext_SupportedVersions(versions=[0x0304]),  # TLS 1.3
                ]
            )
        ])
    )
    client_hello_1.time = base_time
    packets.append(client_hello_1)
    
    server_hello_1 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:60") /
        IP(src="93.184.216.34", dst="192.168.1.200") /
        TCP(sport=443, dport=55001, flags="PA", seq=5000, ack=5500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0x1301,  # TLS_AES_128_GCM_SHA256
            )
        ])
    )
    server_hello_1.time = base_time + 0.05
    packets.append(server_hello_1)
    
    # Session 2: TLS 1.3 with ChaCha20
    client_hello_2 = (
        Ether(src="00:11:22:33:44:61", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.201", dst="172.217.14.206") /
        TCP(sport=55002, dport=443, flags="PA", seq=6000, ack=6000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,
                ciphers=[
                    0x1303,  # TLS_CHACHA20_POLY1305_SHA256
                    0x1301,  # TLS_AES_128_GCM_SHA256
                    0x1302,  # TLS_AES_256_GCM_SHA384
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[29, 23, 24, 257, 258, 259]),
                    TLS_Ext_SupportedVersions(versions=[0x0304]),
                ]
            )
        ])
    )
    client_hello_2.time = base_time + 1.0
    packets.append(client_hello_2)
    
    server_hello_2 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:61") /
        IP(src="172.217.14.206", dst="192.168.1.201") /
        TCP(sport=443, dport=55002, flags="PA", seq=6000, ack=6500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0x1303,  # TLS_CHACHA20_POLY1305_SHA256
            )
        ])
    )
    server_hello_2.time = base_time + 1.05
    packets.append(server_hello_2)
    
    # Session 3: TLS 1.2 with ECDHE and AES-GCM (still secure)
    client_hello_3 = (
        Ether(src="00:11:22:33:44:62", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.202", dst="198.41.214.162") /
        TCP(sport=55003, dport=443, flags="PA", seq=7000, ack=7000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,  # TLS 1.2
                ciphers=[
                    0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
                    0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
                    0xC02B,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
                    0xC02C,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[29, 23, 24, 25, 256, 257, 258]),
                ]
            )
        ])
    )
    client_hello_3.time = base_time + 2.0
    packets.append(client_hello_3)
    
    server_hello_3 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:62") /
        IP(src="198.41.214.162", dst="192.168.1.202") /
        TCP(sport=443, dport=55003, flags="PA", seq=7000, ack=7500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
            )
        ])
    )
    server_hello_3.time = base_time + 2.05
    packets.append(server_hello_3)
    
    os.makedirs("test_captures", exist_ok=True)
    wrpcap("test_captures/secure_tls.pcap", packets)
    print(f"  Created with {len(packets)} packets")


def create_mixed_pcap():
    """Create pcap with mix of vulnerable and secure sessions."""
    print("Generating mixed_tls.pcap...")
    packets = []
    base_time = time.time() - 900  # 15 minutes ago
    
    # Vulnerable session: RC4
    client_hello_vuln = (
        Ether(src="00:11:22:33:44:70", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.150", dst="93.184.216.34") /
        TCP(sport=56001, dport=443, flags="PA", seq=8000, ack=8000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,
                ciphers=[
                    0x0005,  # TLS_RSA_WITH_RC4_128_SHA (RC4 - vulnerable)
                    0xC011,  # TLS_ECDHE_RSA_WITH_RC4_128_SHA (RC4 - vulnerable)
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
            )
        ])
    )
    client_hello_vuln.time = base_time
    packets.append(client_hello_vuln)
    
    server_hello_vuln = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:70") /
        IP(src="93.184.216.34", dst="192.168.1.150") /
        TCP(sport=443, dport=56001, flags="PA", seq=8000, ack=8500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0x0005,  # Selected RC4
            )
        ])
    )
    server_hello_vuln.time = base_time + 0.05
    packets.append(server_hello_vuln)
    
    # Secure session: TLS 1.3
    client_hello_secure = (
        Ether(src="00:11:22:33:44:71", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.151", dst="172.217.14.206") /
        TCP(sport=56002, dport=443, flags="PA", seq=9000, ack=9000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,
                ciphers=[
                    0x1301,  # TLS_AES_128_GCM_SHA256
                    0x1302,  # TLS_AES_256_GCM_SHA384
                    0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[29, 23, 257, 258]),
                    TLS_Ext_SupportedVersions(versions=[0x0304]),
                ]
            )
        ])
    )
    client_hello_secure.time = base_time + 1.0
    packets.append(client_hello_secure)
    
    server_hello_secure = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:71") /
        IP(src="172.217.14.206", dst="192.168.1.151") /
        TCP(sport=443, dport=56002, flags="PA", seq=9000, ack=9500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0x1301,  # TLS 1.3 cipher
            )
        ])
    )
    server_hello_secure.time = base_time + 1.05
    packets.append(server_hello_secure)
    
    # Another vulnerable: Export cipher
    client_hello_export = (
        Ether(src="00:11:22:33:44:72", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.152", dst="198.41.214.162") /
        TCP(sport=56003, dport=443, flags="PA", seq=10000, ack=10000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0301,
                ciphers=[
                    0x0003,  # TLS_RSA_EXPORT_WITH_RC4_40_MD5 (export)
                    0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
                ],
            )
        ])
    )
    client_hello_export.time = base_time + 2.0
    packets.append(client_hello_export)
    
    server_hello_export = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:72") /
        IP(src="198.41.214.162", dst="192.168.1.152") /
        TCP(sport=443, dport=56003, flags="PA", seq=10000, ack=10500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0301,
                cipher=0x0003,  # Export cipher
            )
        ])
    )
    server_hello_export.time = base_time + 2.05
    packets.append(server_hello_export)
    
    # Another secure session
    client_hello_secure2 = (
        Ether(src="00:11:22:33:44:73", dst="aa:bb:cc:dd:ee:ff") /
        IP(src="192.168.1.153", dst="151.101.1.69") /
        TCP(sport=56004, dport=443, flags="PA", seq=11000, ack=11000) /
        TLS(msg=[
            TLSClientHello(
                version=0x0303,
                ciphers=[
                    0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
                    0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
                ],
                ext=[
                    TLS_Ext_SupportedGroups(groups=[23, 24, 25, 257, 258]),
                ]
            )
        ])
    )
    client_hello_secure2.time = base_time + 3.0
    packets.append(client_hello_secure2)
    
    server_hello_secure2 = (
        Ether(src="aa:bb:cc:dd:ee:ff", dst="00:11:22:33:44:73") /
        IP(src="151.101.1.69", dst="192.168.1.153") /
        TCP(sport=443, dport=56004, flags="PA", seq=11000, ack=11500) /
        TLS(msg=[
            TLSServerHello(
                version=0x0303,
                cipher=0xC02F,  # Secure cipher
            )
        ])
    )
    server_hello_secure2.time = base_time + 3.05
    packets.append(server_hello_secure2)
    
    os.makedirs("test_captures", exist_ok=True)
    wrpcap("test_captures/mixed_tls.pcap", packets)
    print(f"  Created with {len(packets)} packets")


def main():
    print("Generating test pcap files...")
    print()
    
    create_vulnerable_pcap()
    create_secure_pcap()
    create_mixed_pcap()
    
    print()
    print("Test pcap generation complete!")
    print()
    print("Files created:")
    print("  - test_captures/vulnerable_tls.pcap (4 vulnerable sessions)")
    print("  - test_captures/secure_tls.pcap (3 secure sessions)")
    print("  - test_captures/mixed_tls.pcap (2 vulnerable, 2 secure sessions)")


if __name__ == "__main__":
    main()


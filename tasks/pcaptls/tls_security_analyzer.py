#!/usr/bin/env python3
"""
TLS Security Analyzer - Extract and analyze TLS handshake parameters from pcap files.

This script ingests pcap files containing TLS traffic and:
- Extracts cipher suites and Diffie-Hellman parameters
- Flags vulnerable configurations (export-grade, RC4, weak DH)
- Generates detailed JSON vulnerability reports

Usage:
    python tls_security_analyzer.py <pcap_file> [--output <output.json>] [--method <tshark|scapy|both>]
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import struct

try:
    from scapy.all import rdpcap, TCP, IP, IPv6, Raw
    from scapy.layers.tls.all import TLS, TLSClientHello, TLSServerHello
    from scapy.layers.tls.extensions import TLS_Ext_SupportedGroups
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("Warning: Scapy not available. Install with: pip install scapy", file=sys.stderr)


# Vulnerability definitions
EXPORT_CIPHERS = {
    0x0003, 0x0006, 0x0008, 0x000B, 0x000E, 0x0011, 0x0014, 0x0017, 0x0019,
    0x0026, 0x0027, 0x0028, 0x0029, 0x002A, 0x002B, 0x0062, 0x0063, 0x0064,
    0x0065, 0x0066
}

RC4_CIPHERS = {
    0x0004,  # TLS_RSA_WITH_RC4_128_MD5
    0x0005,  # TLS_RSA_WITH_RC4_128_SHA
    0xC007,  # TLS_ECDHE_ECDSA_WITH_RC4_128_SHA
    0xC011,  # TLS_ECDHE_RSA_WITH_RC4_128_SHA
}

# DH group sizes (RFC 7919 named groups)
NAMED_DH_GROUPS = {
    256: "ffdhe2048",
    257: "ffdhe3072",
    258: "ffdhe4096",
    259: "ffdhe6144",
    260: "ffdhe8192",
}

# Cipher suite names (subset for common ones)
CIPHER_SUITE_NAMES = {
    0x0000: "TLS_NULL_WITH_NULL_NULL",
    0x0004: "TLS_RSA_WITH_RC4_128_MD5",
    0x0005: "TLS_RSA_WITH_RC4_128_SHA",
    0x002F: "TLS_RSA_WITH_AES_128_CBC_SHA",
    0x0035: "TLS_RSA_WITH_AES_256_CBC_SHA",
    0x003C: "TLS_RSA_WITH_AES_128_CBC_SHA256",
    0x009C: "TLS_RSA_WITH_AES_128_GCM_SHA256",
    0x009D: "TLS_RSA_WITH_AES_256_GCM_SHA384",
    0xC007: "TLS_ECDHE_ECDSA_WITH_RC4_128_SHA",
    0xC009: "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA",
    0xC00A: "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA",
    0xC011: "TLS_ECDHE_RSA_WITH_RC4_128_SHA",
    0xC013: "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    0xC014: "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    0xC023: "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256",
    0xC027: "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256",
    0xC02B: "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    0xC02C: "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    0xC02F: "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    0xC030: "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    0x1301: "TLS_AES_128_GCM_SHA256",
    0x1302: "TLS_AES_256_GCM_SHA384",
    0x1303: "TLS_CHACHA20_POLY1305_SHA256",
}


class TLSSession:
    """Represents a TLS session with its security parameters."""

    def __init__(self, session_id: str, timestamp: float):
        self.session_id = session_id
        self.timestamp = timestamp
        self.client_ciphers: List[int] = []
        self.server_cipher: Optional[int] = None
        self.dh_groups: List[int] = []
        self.dh_prime_size: Optional[int] = None
        self.vulnerabilities: List[str] = []
        self.src_ip: Optional[str] = None
        self.dst_ip: Optional[str] = None
        self.src_port: Optional[int] = None
        self.dst_port: Optional[int] = None

    def analyze_vulnerabilities(self):
        """Identify security vulnerabilities in the session."""
        self.vulnerabilities = []

        # Check server-selected cipher
        if self.server_cipher:
            if self.server_cipher in EXPORT_CIPHERS:
                self.vulnerabilities.append("EXPORT_GRADE_CIPHER")
            if self.server_cipher in RC4_CIPHERS:
                self.vulnerabilities.append("RC4_CIPHER")

        # Check DH parameters
        if self.dh_prime_size and self.dh_prime_size < 1024:
            self.vulnerabilities.append("WEAK_DH_PARAMETERS")

        # Check for any offered export/RC4 ciphers (even if not selected)
        has_export_offer = any(c in EXPORT_CIPHERS for c in self.client_ciphers)
        has_rc4_offer = any(c in RC4_CIPHERS for c in self.client_ciphers)

        # Mark offered vulnerabilities regardless of selection
        if has_export_offer:
            self.vulnerabilities.append("EXPORT_CIPHER_OFFERED")
        if has_rc4_offer:
            self.vulnerabilities.append("RC4_CIPHER_OFFERED")

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "timestamp_unix": self.timestamp,
            "connection": {
                "src_ip": self.src_ip,
                "src_port": self.src_port,
                "dst_ip": self.dst_ip,
                "dst_port": self.dst_port,
            },
            "cipher_suites": {
                "client_offered": [
                    {
                        "id": f"0x{c:04X}",
                        "name": CIPHER_SUITE_NAMES.get(c, "UNKNOWN"),
                    }
                    for c in self.client_ciphers
                ],
                "server_selected": {
                    "id": f"0x{self.server_cipher:04X}" if self.server_cipher else None,
                    "name": CIPHER_SUITE_NAMES.get(self.server_cipher, "UNKNOWN") if self.server_cipher else None,
                } if self.server_cipher else None,
            },
            "diffie_hellman": {
                "supported_groups": self.dh_groups,
                "named_groups": [NAMED_DH_GROUPS.get(g, f"unknown_{g}") for g in self.dh_groups],
                "prime_size_bits": self.dh_prime_size,
            },
            "vulnerabilities": self.vulnerabilities,
            "is_vulnerable": len(self.vulnerabilities) > 0,
        }


class ManualTLSParser:
    """Parse TLS handshakes manually from raw bytes."""

    @staticmethod
    def parse_tls_record(data: bytes) -> Optional[Dict[str, Any]]:
        """Parse a TLS record from raw bytes."""
        if len(data) < 5:
            return None

        content_type = data[0]
        struct.unpack('>H', data[1:3])[0]
        length = struct.unpack('>H', data[3:5])[0]

        if content_type != 0x16:  # Not handshake
            return None

        if len(data) < 5 + length:
            return None

        payload = data[5:5+length]
        return ManualTLSParser.parse_handshake(payload)

    @staticmethod
    def parse_handshake(data: bytes) -> Optional[Dict[str, Any]]:
        """Parse TLS handshake message."""
        if len(data) < 4:
            return None

        msg_type = data[0]
        msg_len = struct.unpack('>I', b'\x00' + data[1:4])[0]

        if len(data) < 4 + msg_len:
            return None

        msg_data = data[4:4+msg_len]

        if msg_type == 1:  # ClientHello
            return ManualTLSParser.parse_client_hello(msg_data)
        elif msg_type == 2:  # ServerHello
            return ManualTLSParser.parse_server_hello(msg_data)
        elif msg_type == 12:  # ServerKeyExchange
            return ManualTLSParser.parse_server_key_exchange(msg_data)

        return None

    @staticmethod
    def parse_client_hello(data: bytes) -> Dict[str, Any]:
        """Parse ClientHello message."""
        result = {'type': 'ClientHello', 'ciphers': []}

        if len(data) < 38:
            return result

        # Skip version (2) + random (32) + session_id_len (1)
        pos = 35
        session_id_len = data[34]
        pos += session_id_len

        if len(data) < pos + 2:
            return result

        # Parse cipher suites
        cipher_len = struct.unpack('>H', data[pos:pos+2])[0]
        pos += 2

        for i in range(0, cipher_len, 2):
            if pos + i + 2 <= len(data):
                cipher = struct.unpack('>H', data[pos+i:pos+i+2])[0]
                result['ciphers'].append(cipher)

        return result

    @staticmethod
    def parse_server_hello(data: bytes) -> Dict[str, Any]:
        """Parse ServerHello message."""
        result = {'type': 'ServerHello', 'cipher': None}

        if len(data) < 38:
            return result

        # Skip version (2) + random (32) + session_id_len (1)
        pos = 35
        session_id_len = data[34]
        pos += session_id_len

        if len(data) < pos + 2:
            return result

        # Parse selected cipher
        cipher = struct.unpack('>H', data[pos:pos+2])[0]
        result['cipher'] = cipher

        return result

    @staticmethod
    def parse_server_key_exchange(data: bytes) -> Dict[str, Any]:
        """Parse ServerKeyExchange message and extract DH parameters."""
        result = {'type': 'ServerKeyExchange', 'dh_prime_size': None}

        if len(data) < 1:
            return result

        pos = 0
        # Parse curve type or DH params type (1 byte)
        # For DH: 0x00 = explicit prime, 0x01 = explicit char2, 0x02 = named curve
        # For traditional DH, it's typically 0x00
        curve_type = data[pos]
        pos += 1

        # For explicit prime DH (type 0x00), parse DH parameters
        if curve_type == 0x00:
            # Parse DH prime (p) length (2 bytes)
            if len(data) < pos + 2:
                return result
            dh_p_len = struct.unpack('>H', data[pos:pos+2])[0]
            pos += 2

            # Calculate and set prime size in bits (from bytes) immediately
            # so it's preserved even if subsequent parsing fails
            result['dh_prime_size'] = dh_p_len * 8

            # Skip DH prime value
            if len(data) < pos + dh_p_len:
                return result
            pos += dh_p_len

            # Parse DH generator (g) length (2 bytes)
            if len(data) < pos + 2:
                return result
            dh_g_len = struct.unpack('>H', data[pos:pos+2])[0]
            pos += 2

            # Skip DH generator value
            if len(data) < pos + dh_g_len:
                return result
            pos += dh_g_len

            # Parse DH Ys (server's public value) length (2 bytes)
            if len(data) < pos + 2:
                return result
            dh_Ys_len = struct.unpack('>H', data[pos:pos+2])[0]
            pos += 2

            # Skip DH Ys value
            if len(data) < pos + dh_Ys_len:
                return result
            pos += dh_Ys_len

            # Parse signature length (2 bytes) - optional, may be missing in some cases
            if len(data) >= pos + 2:
                sig_len = struct.unpack('>H', data[pos:pos+2])[0]
                pos += 2
                # Skip signature value if present
                if len(data) >= pos + sig_len:
                    pos += sig_len

        return result


class TSharkAnalyzer:
    """Analyze TLS traffic using tshark command-line tool."""

    @staticmethod
    def is_available() -> bool:
        """Check if tshark is available."""
        try:
            subprocess.run(["tshark", "-v"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def analyze_pcap(pcap_file: Path) -> List[TLSSession]:
        """Extract TLS sessions from pcap using tshark."""
        sessions: Dict[str, TLSSession] = {}

        # Extract TLS handshake information
        tshark_fields = [
            "frame.time_epoch",
            "ip.src", "ip.dst", "tcp.srcport", "tcp.dstport",
            "tls.handshake.type",
            "tls.handshake.ciphersuite",
            "tls.handshake.ciphersuites",
            "tls.handshake.extensions.supported_group",
            "tls.handshake.sig_hash_alg",
        ]

        cmd = [
            "tshark", "-r", str(pcap_file),
            "-Y", "tls.handshake.type",
            "-T", "fields",
        ]

        for field in tshark_fields:
            cmd.extend(["-e", field])

        cmd.extend(["-E", "separator=|", "-E", "occurrence=a"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|')
                if len(parts) < len(tshark_fields):
                    continue

                timestamp = float(parts[0]) if parts[0] else 0.0
                src_ip = parts[1]
                dst_ip = parts[2]
                src_port = int(parts[3]) if parts[3] else 0
                dst_port = int(parts[4]) if parts[4] else 0
                handshake_type = parts[5]

                # Identify client and server based on handshake type
                # ClientHello (type 1): src is client, dst is server
                # ServerHello (type 2): src is server, dst is client
                if handshake_type == "1":  # ClientHello
                    client_ip, client_port = src_ip, src_port
                    server_ip, server_port = dst_ip, dst_port
                else:  # ServerHello or other
                    client_ip, client_port = dst_ip, dst_port
                    server_ip, server_port = src_ip, src_port

                # Always use client-server ordering for session ID
                session_id = f"{client_ip}:{client_port}-{server_ip}:{server_port}"

                if session_id not in sessions:
                    sessions[session_id] = TLSSession(session_id, timestamp)
                    # Always store client as src, server as dst
                    sessions[session_id].src_ip = client_ip
                    sessions[session_id].dst_ip = server_ip
                    sessions[session_id].src_port = client_port
                    sessions[session_id].dst_port = server_port

                session = sessions[session_id]

                # Parse Client Hello (type 1)
                if handshake_type == "1":
                    # Parse offered cipher suites
                    if len(parts) > 7 and parts[7]:
                        name_to_id = {v: k for k, v in CIPHER_SUITE_NAMES.items()}
                        cipher_strings = parts[7].split(',')
                        for cs in cipher_strings:
                            cs = cs.strip()
                            try:
                                if cs.startswith(('0x','0X')):
                                    cipher_id = int(cs, 16)
                                elif cs.isdigit():
                                    cipher_id = int(cs)
                                else:
                                    cipher_id = name_to_id.get(cs)
                                if cipher_id is not None and cipher_id not in session.client_ciphers:
                                    session.client_ciphers.append(cipher_id)
                            except (ValueError, TypeError):
                                mapped = name_to_id.get(cs)
                                if mapped is not None and mapped not in session.client_ciphers:
                                    session.client_ciphers.append(mapped)

                    # Parse supported groups
                    if len(parts) > 8 and parts[8]:
                        group_strings = parts[8].split(',')
                        for g in group_strings:
                            g = g.strip()
                            try:
                                group_id = int(g)
                                if group_id not in session.dh_groups:
                                    session.dh_groups.append(group_id)
                            except (ValueError, TypeError):
                                pass

                # Parse Server Hello (type 2)
                elif handshake_type == "2":
                    # Parse selected cipher suite
                    if len(parts) > 6 and parts[6]:
                        name_to_id = {v: k for k, v in CIPHER_SUITE_NAMES.items()}
                        cs = parts[6].strip()
                        try:
                            if cs.startswith(('0x','0X')):
                                session.server_cipher = int(cs, 16)
                            elif cs.isdigit():
                                session.server_cipher = int(cs)
                            else:
                                session.server_cipher = name_to_id.get(cs)
                        except (ValueError, TypeError):
                            session.server_cipher = name_to_id.get(cs)

        except subprocess.CalledProcessError as e:
            print(f"tshark error: {e.stderr}", file=sys.stderr)
            return []

        # Analyze vulnerabilities
        for session in sessions.values():
            session.analyze_vulnerabilities()

        return list(sessions.values())


class ScapyAnalyzer:
    """Analyze TLS traffic using Scapy library."""

    @staticmethod
    def is_available() -> bool:
        """Check if Scapy is available."""
        return SCAPY_AVAILABLE

    @staticmethod
    def analyze_pcap(pcap_file: Path) -> List[TLSSession]:
        """Extract TLS sessions from pcap using Scapy."""
        if not SCAPY_AVAILABLE:
            return []

        sessions: Dict[str, TLSSession] = {}

        try:
            packets = rdpcap(str(pcap_file))

            for pkt in packets:
                # Extract connection info first
                timestamp = float(pkt.time)
                src_ip = None
                dst_ip = None
                src_port = None
                dst_port = None

                if pkt.haslayer(IP):
                    src_ip = pkt[IP].src
                    dst_ip = pkt[IP].dst
                elif pkt.haslayer(IPv6):
                    src_ip = pkt[IPv6].src
                    dst_ip = pkt[IPv6].dst

                if pkt.haslayer(TCP):
                    src_port = pkt[TCP].sport
                    dst_port = pkt[TCP].dport

                # Try Scapy TLS parsing first
                tls_layer = None
                manual_parse = None

                if pkt.haslayer(TLS):
                    tls_layer = pkt[TLS]
                elif pkt.haslayer(Raw) and pkt.haslayer(TCP):
                    raw_data = pkt[Raw].load

                    # Try Scapy parsing
                    try:
                        tls_layer = TLS(raw_data)
                    except Exception:
                        # Fall back to manual parsing
                        manual_parse = ManualTLSParser.parse_tls_record(raw_data)

                # Skip if no TLS data found
                if not tls_layer and not manual_parse:
                    continue

                # Skip if we don't have valid connection info
                if not src_ip or not dst_ip or src_port is None or dst_port is None:
                    continue

                # Determine if this is a ClientHello or ServerHello to identify client/server
                is_client_hello = False
                if manual_parse:
                    is_client_hello = manual_parse.get('type') == 'ClientHello'
                elif tls_layer:
                    is_client_hello = tls_layer.haslayer(TLSClientHello)

                # Identify client and server based on handshake type
                # ClientHello: src is client, dst is server
                # ServerHello: src is server, dst is client
                if is_client_hello:
                    client_ip, client_port = src_ip, src_port
                    server_ip, server_port = dst_ip, dst_port
                else:
                    client_ip, client_port = dst_ip, dst_port
                    server_ip, server_port = src_ip, src_port

                # Always use client-server ordering for session ID
                session_id = f"{client_ip}:{client_port}-{server_ip}:{server_port}"

                if session_id not in sessions:
                    sessions[session_id] = TLSSession(session_id, timestamp)
                    # Always store client as src, server as dst
                    sessions[session_id].src_ip = client_ip
                    sessions[session_id].dst_ip = server_ip
                    sessions[session_id].src_port = client_port
                    sessions[session_id].dst_port = server_port

                session = sessions[session_id]

                # Use manual parse if available
                if manual_parse:
                    if manual_parse.get('type') == 'ClientHello':
                        ciphers = manual_parse.get('ciphers', [])
                        if ciphers:
                            session.client_ciphers = ciphers
                    elif manual_parse.get('type') == 'ServerHello':
                        cipher = manual_parse.get('cipher')
                        if cipher is not None:
                            session.server_cipher = cipher
                    elif manual_parse.get('type') == 'ServerKeyExchange':
                        dh_prime_size = manual_parse.get('dh_prime_size')
                        if dh_prime_size is not None:
                            session.dh_prime_size = dh_prime_size
                # Otherwise use Scapy parsing
                elif tls_layer:
                    if tls_layer.haslayer(TLSClientHello):
                        client_hello = tls_layer[TLSClientHello]
                        if hasattr(client_hello, 'ciphers') and client_hello.ciphers:
                            session.client_ciphers = list(client_hello.ciphers)
                        if hasattr(client_hello, 'ext') and client_hello.ext:
                            for ext in client_hello.ext:
                                if isinstance(ext, TLS_Ext_SupportedGroups):
                                    if hasattr(ext, 'groups'):
                                        session.dh_groups = list(ext.groups)

                    if tls_layer.haslayer(TLSServerHello):
                        server_hello = tls_layer[TLSServerHello]
                        if hasattr(server_hello, 'cipher') and server_hello.cipher:
                            session.server_cipher = server_hello.cipher

        except Exception as e:
            print(f"Scapy error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []

        # Analyze vulnerabilities
        for session in sessions.values():
            session.analyze_vulnerabilities()

        return list(sessions.values())


def generate_report(sessions: List[TLSSession], output_file: Optional[Path] = None, verbose: bool = False) -> Dict[str, Any]:
    """Generate JSON report from analyzed sessions."""
    if verbose:
        print("\nDEBUG: Session details:", file=sys.stderr)
        for i, s in enumerate(sessions):
            print(f"  Session {i}: {s.session_id}", file=sys.stderr)
            print(f"    Client ciphers: {len(s.client_ciphers)} - {[hex(c) for c in s.client_ciphers]}", file=sys.stderr)
            print(f"    Server cipher: {hex(s.server_cipher) if s.server_cipher else None}", file=sys.stderr)
            print(f"    Vulnerabilities: {s.vulnerabilities}", file=sys.stderr)

    sessions_sorted = sorted(sessions, key=lambda s: (s.timestamp, s.session_id))
    report = {
        "analysis_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_sessions": len(sessions_sorted),
            "vulnerable_sessions": sum(1 for s in sessions_sorted if s.vulnerabilities),
        },
        "vulnerability_summary": {
            "export_grade_ciphers": sum(1 for s in sessions_sorted if "EXPORT_GRADE_CIPHER" in s.vulnerabilities),
            "rc4_ciphers": sum(1 for s in sessions_sorted if "RC4_CIPHER" in s.vulnerabilities),
            "weak_dh_parameters": sum(1 for s in sessions_sorted if "WEAK_DH_PARAMETERS" in s.vulnerabilities),
            "export_cipher_offered": sum(1 for s in sessions_sorted if "EXPORT_CIPHER_OFFERED" in s.vulnerabilities),
            "rc4_cipher_offered": sum(1 for s in sessions_sorted if "RC4_CIPHER_OFFERED" in s.vulnerabilities),
        },
        "sessions": [s.to_dict() for s in sessions_sorted],
    }

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report written to: {output_file}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Analyze TLS traffic for security vulnerabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture.pcap
  %(prog)s capture.pcap --output report.json
  %(prog)s capture.pcap --method tshark
  %(prog)s capture.pcap --method scapy
        """
    )

    parser.add_argument("pcap_file", type=Path, help="Path to pcap file")
    parser.add_argument("--output", "-o", type=Path, help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--method", "-m",
        choices=["tshark", "scapy", "both"],
        default="both",
        help="Analysis method (default: both, fallback if unavailable)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not args.pcap_file.exists():
        print(f"Error: File not found: {args.pcap_file}", file=sys.stderr)
        sys.exit(1)

    sessions = []

    # Try tshark
    if args.method in ["tshark", "both"]:
        if TSharkAnalyzer.is_available():
            if args.verbose:
                print("Using tshark for analysis...", file=sys.stderr)
            sessions = TSharkAnalyzer.analyze_pcap(args.pcap_file)
            if sessions or args.method == "tshark":
                if args.verbose:
                    print(f"tshark found {len(sessions)} sessions", file=sys.stderr)
        elif args.method == "tshark":
            print("Error: tshark not available", file=sys.stderr)
            sys.exit(1)

    # Try scapy if needed
    if not sessions and args.method in ["scapy", "both"]:
        if ScapyAnalyzer.is_available():
            if args.verbose:
                print("Using Scapy for analysis...", file=sys.stderr)
            sessions = ScapyAnalyzer.analyze_pcap(args.pcap_file)
            if args.verbose:
                print(f"Scapy found {len(sessions)} sessions", file=sys.stderr)
        elif args.method == "scapy":
            print("Error: Scapy not available", file=sys.stderr)
            sys.exit(1)

    if not sessions:
        print("Warning: No TLS sessions found in pcap", file=sys.stderr)

    # Generate report with verbose flag
    report = generate_report(sessions, args.output, args.verbose)

    if not args.output:
        print(json.dumps(report, indent=2))

    # Print summary to stderr
    if args.verbose:
        print("\nAnalysis Summary:", file=sys.stderr)
        print(f"  Total sessions: {report['analysis_metadata']['total_sessions']}", file=sys.stderr)
        print(f"  Vulnerable sessions: {report['analysis_metadata']['vulnerable_sessions']}", file=sys.stderr)
        print(f"  Export-grade ciphers: {report['vulnerability_summary']['export_grade_ciphers']}", file=sys.stderr)
        print(f"  RC4 ciphers: {report['vulnerability_summary']['rc4_ciphers']}", file=sys.stderr)
        print(f"  Weak DH parameters: {report['vulnerability_summary']['weak_dh_parameters']}", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
TLS Security Analyzer

Analyzes PCAP files containing TLS traffic and generates security reports.
Detects export-grade ciphers, RC4 usage, and weak DH parameters.
"""

import argparse
import json
import sys
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    from scapy.all import rdpcap, TCP
    from scapy.layers.tls.all import TLS
    from scapy.layers.tls.handshake import TLSClientHello, TLSServerHello
    from scapy.layers.tls.extensions import TLS_Ext_SupportedGroups
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


# TLS Cipher Suite Definitions
CIPHER_SUITES = {
    0x0000: "TLS_NULL_WITH_NULL_NULL",
    0x0001: "TLS_RSA_WITH_NULL_MD5",
    0x0002: "TLS_RSA_WITH_NULL_SHA",
    0x0003: "TLS_RSA_EXPORT_WITH_RC4_40_MD5",
    0x0004: "TLS_RSA_WITH_RC4_128_MD5",
    0x0005: "TLS_RSA_WITH_RC4_128_SHA",
    0x0006: "TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5",
    0x0007: "TLS_RSA_WITH_IDEA_CBC_SHA",
    0x0008: "TLS_RSA_EXPORT_WITH_DES40_CBC_SHA",
    0x0009: "TLS_RSA_WITH_DES_CBC_SHA",
    0x000A: "TLS_RSA_WITH_3DES_EDE_CBC_SHA",
    0x000B: "TLS_DH_DSS_EXPORT_WITH_DES40_CBC_SHA",
    0x000C: "TLS_DH_DSS_WITH_DES_CBC_SHA",
    0x000D: "TLS_DH_DSS_WITH_3DES_EDE_CBC_SHA",
    0x000E: "TLS_DH_RSA_EXPORT_WITH_DES40_CBC_SHA",
    0x000F: "TLS_DH_RSA_WITH_DES_CBC_SHA",
    0x0010: "TLS_DH_RSA_WITH_3DES_EDE_CBC_SHA",
    0x0011: "TLS_DHE_DSS_EXPORT_WITH_DES40_CBC_SHA",
    0x0012: "TLS_DHE_DSS_WITH_DES_CBC_SHA",
    0x0013: "TLS_DHE_DSS_WITH_3DES_EDE_CBC_SHA",
    0x0014: "TLS_DHE_RSA_EXPORT_WITH_DES40_CBC_SHA",
    0x0015: "TLS_DHE_RSA_WITH_DES_CBC_SHA",
    0x0016: "TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA",
    0x0017: "TLS_DH_anon_EXPORT_WITH_RC4_40_MD5",
    0x0018: "TLS_DH_anon_WITH_RC4_128_MD5",
    0x0019: "TLS_DH_anon_EXPORT_WITH_DES40_CBC_SHA",
    0x001A: "TLS_DH_anon_WITH_DES_CBC_SHA",
    0x001B: "TLS_DH_anon_WITH_3DES_EDE_CBC_SHA",
    0x002F: "TLS_RSA_WITH_AES_128_CBC_SHA",
    0x0033: "TLS_DHE_RSA_WITH_AES_128_CBC_SHA",
    0x0035: "TLS_RSA_WITH_AES_256_CBC_SHA",
    0x0039: "TLS_DHE_RSA_WITH_AES_256_CBC_SHA",
    0xC002: "TLS_ECDH_ECDSA_WITH_RC4_128_SHA",
    0xC007: "TLS_ECDHE_ECDSA_WITH_RC4_128_SHA",
    0xC00C: "TLS_ECDH_RSA_WITH_RC4_128_SHA",
    0xC011: "TLS_ECDHE_RSA_WITH_RC4_128_SHA",
    0xC013: "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    0xC014: "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    0xC02F: "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    0xC030: "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
}

# Export-grade ciphers (40-bit or 56-bit)
EXPORT_CIPHERS = {
    0x0003, 0x0006, 0x0008, 0x000B, 0x000E, 0x0011, 0x0014, 0x0017, 0x0019
}

# RC4 ciphers
RC4_CIPHERS = {
    0x0003, 0x0004, 0x0005, 0x0017, 0x0018,
    0xC002, 0xC007, 0xC00C, 0xC011
}

# Supported Groups (for DH/ECDH)
SUPPORTED_GROUPS = {
    1: "sect163k1", 2: "sect163r1", 3: "sect163r2",
    4: "sect193r1", 5: "sect193r2", 6: "sect233k1",
    7: "sect233r1", 8: "sect239k1", 9: "sect283k1",
    10: "sect283r1", 11: "sect409k1", 12: "sect409r1",
    13: "sect571k1", 14: "sect571r1", 15: "secp160k1",
    16: "secp160r1", 17: "secp160r2", 18: "secp192k1",
    19: "secp192r1", 20: "secp224k1", 21: "secp224r1",
    22: "secp256k1", 23: "secp256r1", 24: "secp384r1",
    25: "secp521r1", 256: "ffdhe2048", 257: "ffdhe3072",
    258: "ffdhe4096", 259: "ffdhe6144", 260: "ffdhe8192",
}


class TLSSession:
    """Represents a TLS session from ClientHello through ServerHello"""

    def __init__(self, src_ip, dst_ip, src_port, dst_port):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.client_offered_ciphers = []
        self.server_selected_cipher = None
        self.supported_groups = []
        self.timestamp = None
        self.timestamp_unix = None
        self.dh_prime_bits = None

    def to_dict(self):
        """Convert session to report dictionary format"""
        # Analyze vulnerabilities
        vulnerabilities = []

        # Check client offered ciphers
        offered_cipher_ids = {c['id_int'] for c in self.client_offered_ciphers}

        # Check for offered export ciphers
        if offered_cipher_ids & EXPORT_CIPHERS:
            vulnerabilities.append("EXPORT_CIPHER_OFFERED")

        # Check for offered RC4 ciphers
        if offered_cipher_ids & RC4_CIPHERS:
            vulnerabilities.append("RC4_CIPHER_OFFERED")

        # Check server selected cipher
        if self.server_selected_cipher:
            selected_id = self.server_selected_cipher['id_int']

            if selected_id in EXPORT_CIPHERS:
                vulnerabilities.append("EXPORT_GRADE_CIPHER")

            if selected_id in RC4_CIPHERS:
                vulnerabilities.append("RC4_CIPHER")

        # Check DH parameters
        if self.dh_prime_bits is not None and self.dh_prime_bits < 1024:
            vulnerabilities.append("WEAK_DH_PARAMETERS")

        # Remove duplicates and sort
        vulnerabilities = sorted(set(vulnerabilities))

        # Build named groups list
        named_groups = [SUPPORTED_GROUPS.get(g, f"unknown_{g}") for g in self.supported_groups]

        return {
            "session_id": f"{self.src_ip}:{self.src_port}-{self.dst_ip}:{self.dst_port}",
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "timestamp_unix": self.timestamp_unix or datetime.now(timezone.utc).timestamp(),
            "connection": {
                "src_ip": self.src_ip,
                "dst_ip": self.dst_ip,
                "src_port": self.src_port,
                "dst_port": self.dst_port
            },
            "cipher_suites": {
                "client_offered": self.client_offered_ciphers,
                "server_selected": self.server_selected_cipher
            },
            "diffie_hellman": {
                "supported_groups": self.supported_groups,
                "named_groups": named_groups,
                "prime_size_bits": self.dh_prime_bits
            },
            "vulnerabilities": vulnerabilities,
            "is_vulnerable": len(vulnerabilities) > 0
        }


def parse_pcap_scapy(pcap_file):
    """Parse PCAP file using Scapy backend"""
    if not SCAPY_AVAILABLE:
        raise RuntimeError("Scapy not available")

    sessions = {}

    try:
        packets = rdpcap(str(pcap_file))
    except Exception as e:
        print(f"Error reading PCAP file: {e}", file=sys.stderr)
        return []

    for pkt in packets:
        try:
            if not pkt.haslayer(TCP) or not pkt.haslayer(TLS):
                continue

            # Get connection tuple
            src_ip = pkt['IP'].src if pkt.haslayer('IP') else None
            dst_ip = pkt['IP'].dst if pkt.haslayer('IP') else None
            src_port = pkt[TCP].sport
            dst_port = pkt[TCP].dport

            if not src_ip or not dst_ip:
                continue

            # Create session key (client -> server)
            session_key = (src_ip, dst_ip, src_port, dst_port)
            reverse_key = (dst_ip, src_ip, dst_port, src_port)

            # Handle ClientHello
            if pkt.haslayer(TLSClientHello):
                client_hello = pkt[TLSClientHello]

                if session_key not in sessions:
                    sessions[session_key] = TLSSession(src_ip, dst_ip, src_port, dst_port)

                session = sessions[session_key]
                session.timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                session.timestamp_unix = float(pkt.time)

                # Extract offered cipher suites
                if hasattr(client_hello, 'ciphers') and client_hello.ciphers:
                    for cipher in client_hello.ciphers:
                        cipher_id = cipher
                        cipher_name = CIPHER_SUITES.get(cipher_id, f"UNKNOWN_0x{cipher_id:04X}")
                        session.client_offered_ciphers.append({
                            "id": f"0x{cipher_id:04x}",
                            "id_int": cipher_id,
                            "name": cipher_name
                        })

                # Extract supported groups extension
                if hasattr(client_hello, 'ext') and client_hello.ext:
                    for ext in client_hello.ext:
                        if isinstance(ext, TLS_Ext_SupportedGroups):
                            if hasattr(ext, 'groups'):
                                session.supported_groups = list(ext.groups)

            # Handle ServerHello
            elif pkt.haslayer(TLSServerHello):
                server_hello = pkt[TLSServerHello]

                # Look for matching session (could be either direction)
                session = sessions.get(reverse_key) or sessions.get(session_key)

                if session and hasattr(server_hello, 'cipher') and server_hello.cipher:
                    cipher_id = server_hello.cipher
                    cipher_name = CIPHER_SUITES.get(cipher_id, f"UNKNOWN_0x{cipher_id:04X}")
                    session.server_selected_cipher = {
                        "id": f"0x{cipher_id:04x}",
                        "id_int": cipher_id,
                        "name": cipher_name
                    }

            # Handle Server Key Exchange (for DH parameters)
            elif pkt.haslayer('Raw'):
                raw_data = bytes(pkt['Raw'])
                # Check if this looks like a TLS handshake record
                if len(raw_data) > 5 and raw_data[0] == 0x16:  # Handshake
                    # Try to extract DH prime length
                    # This is a simplified parser for Server Key Exchange
                    if len(raw_data) > 9 and raw_data[5] == 12:  # ServerKeyExchange
                        # The format is: [type:1][length:3][dh_p_length:2][dh_p:var]...
                        try:
                            dh_p_length_offset = 9
                            if len(raw_data) > dh_p_length_offset + 2:
                                dh_p_length = (raw_data[dh_p_length_offset] << 8) | raw_data[dh_p_length_offset + 1]
                                dh_prime_bits = dh_p_length * 8

                                # Find matching session
                                session = sessions.get(reverse_key) or sessions.get(session_key)
                                if session:
                                    session.dh_prime_bits = dh_prime_bits
                        except Exception:
                            pass  # Ignore parsing errors for raw data

        except Exception:
            # Handle malformed packets gracefully
            continue

    return [session.to_dict() for session in sessions.values()]


def is_tshark_available():
    """Check if tshark is available in PATH"""
    return shutil.which('tshark') is not None


def parse_pcap_tshark(pcap_file):
    """Parse PCAP file using tshark backend"""
    if not is_tshark_available():
        raise RuntimeError("tshark not available")

    sessions = {}

    try:
        # Run tshark to extract TLS handshake messages as JSON
        tshark_cmd = [
            'tshark',
            '-r', str(pcap_file),
            '-Y', 'tls.handshake.type == 1 || tls.handshake.type == 2 || tls.handshake.type == 12',
            '-T', 'json',
            '-e', 'frame.time_epoch',
            '-e', 'ip.src',
            '-e', 'ip.dst',
            '-e', 'tcp.srcport',
            '-e', 'tcp.dstport',
            '-e', 'tls.handshake.type',
            '-e', 'tls.handshake.ciphersuite',
            '-e', 'tls.handshake.cipher',
            '-e', 'tls.handshake.extensions_supported_group',
            '-e', 'tls.handshake.sig_hash_alg',
        ]

        result = subprocess.run(
            tshark_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"tshark error: {result.stderr}", file=sys.stderr)
            return []

        if not result.stdout or result.stdout.strip() == '':
            # No TLS handshake packets found
            return []

        packets = json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        print("tshark timeout", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"tshark JSON parse error: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"tshark error: {e}", file=sys.stderr)
        return []

    # Process packets
    for pkt in packets:
        try:
            layers = pkt.get('_source', {}).get('layers', {})

            # Extract basic fields
            timestamp_unix = float(layers.get('frame.time_epoch', [0])[0])
            src_ip = layers.get('ip.src', [None])[0]
            dst_ip = layers.get('ip.dst', [None])[0]
            src_port = int(layers.get('tcp.srcport', [0])[0])
            dst_port = int(layers.get('tcp.dstport', [0])[0])
            handshake_types = layers.get('tls.handshake.type', [])

            if not src_ip or not dst_ip:
                continue

            session_key = (src_ip, dst_ip, src_port, dst_port)
            reverse_key = (dst_ip, src_ip, dst_port, src_port)

            # Handle ClientHello (type 1)
            if '1' in handshake_types:
                if session_key not in sessions:
                    sessions[session_key] = TLSSession(src_ip, dst_ip, src_port, dst_port)

                session = sessions[session_key]
                session.timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                session.timestamp_unix = timestamp_unix

                # Extract offered cipher suites
                cipher_suites = layers.get('tls.handshake.ciphersuite', [])
                if cipher_suites:
                    # tshark returns cipher suites as hex strings like "0x0003"
                    for cipher_hex in cipher_suites:
                        try:
                            cipher_id = int(cipher_hex, 16)
                            cipher_name = CIPHER_SUITES.get(cipher_id, f"UNKNOWN_0x{cipher_id:04X}")
                            session.client_offered_ciphers.append({
                                "id": f"0x{cipher_id:04x}",
                                "id_int": cipher_id,
                                "name": cipher_name
                            })
                        except ValueError:
                            continue

                # Extract supported groups
                supported_groups = layers.get('tls.handshake.extensions_supported_group', [])
                if supported_groups:
                    try:
                        session.supported_groups = [int(g, 16) if isinstance(g, str) and g.startswith('0x') else int(g) for g in supported_groups]
                    except (ValueError, TypeError):
                        session.supported_groups = []

            # Handle ServerHello (type 2)
            elif '2' in handshake_types:
                # Find matching session
                session = sessions.get(reverse_key) or sessions.get(session_key)

                if session:
                    cipher_hex_list = layers.get('tls.handshake.cipher', [])
                    if cipher_hex_list:
                        try:
                            cipher_hex = cipher_hex_list[0]
                            cipher_id = int(cipher_hex, 16)
                            cipher_name = CIPHER_SUITES.get(cipher_id, f"UNKNOWN_0x{cipher_id:04X}")
                            session.server_selected_cipher = {
                                "id": f"0x{cipher_id:04x}",
                                "id_int": cipher_id,
                                "name": cipher_name
                            }
                        except (ValueError, IndexError):
                            pass

            # Handle Server Key Exchange (type 12) - for DH parameters
            # Note: Extracting DH prime from tshark requires more complex field parsing
            # For now, we'll skip detailed DH extraction via tshark

        except Exception:
            # Handle malformed packet data gracefully
            continue

    return [session.to_dict() for session in sessions.values()]


def generate_report(pcap_file, output_file, backend='auto'):
    """
    Generate security report from PCAP file.

    Args:
        pcap_file: Path to input PCAP file
        output_file: Path to output JSON report
        backend: 'auto', 'scapy', or 'tshark'

    Returns:
        True on success, False on failure
    """
    try:
        # Parse PCAP with backend selection
        sessions = []

        if backend == 'auto':
            # Auto mode: try tshark first, fall back to scapy
            if is_tshark_available():
                try:
                    sessions = parse_pcap_tshark(pcap_file)
                except Exception as e:
                    print(f"tshark backend failed, falling back to scapy: {e}", file=sys.stderr)
                    if SCAPY_AVAILABLE:
                        sessions = parse_pcap_scapy(pcap_file)
                    else:
                        print("Error: Scapy not available for fallback", file=sys.stderr)
                        return False
            elif SCAPY_AVAILABLE:
                sessions = parse_pcap_scapy(pcap_file)
            else:
                print("Error: Neither tshark nor scapy available", file=sys.stderr)
                return False

        elif backend == 'tshark':
            # Explicit tshark mode
            if not is_tshark_available():
                print("Error: tshark not available", file=sys.stderr)
                return False
            sessions = parse_pcap_tshark(pcap_file)

        elif backend == 'scapy':
            # Explicit scapy mode
            if not SCAPY_AVAILABLE:
                print("Error: Scapy not available", file=sys.stderr)
                return False
            sessions = parse_pcap_scapy(pcap_file)

        else:
            print(f"Error: Unknown backend: {backend}", file=sys.stderr)
            return False

        # Calculate summary statistics
        total_sessions = len(sessions)
        vulnerable_sessions = sum(1 for s in sessions if s['is_vulnerable'])

        # Count vulnerability types
        export_grade_count = 0
        rc4_count = 0
        weak_dh_count = 0
        export_offered_count = 0
        rc4_offered_count = 0

        for session in sessions:
            vulns = session['vulnerabilities']
            if 'EXPORT_GRADE_CIPHER' in vulns:
                export_grade_count += 1
            if 'RC4_CIPHER' in vulns:
                rc4_count += 1
            if 'WEAK_DH_PARAMETERS' in vulns:
                weak_dh_count += 1
            if 'EXPORT_CIPHER_OFFERED' in vulns:
                export_offered_count += 1
            if 'RC4_CIPHER_OFFERED' in vulns:
                rc4_offered_count += 1

        # Build vulnerability summary
        vuln_summary = {
            "export_grade_ciphers": export_grade_count,
            "rc4_ciphers": rc4_count,
            "weak_dh_parameters": weak_dh_count
        }

        # Only include offered counts if > 0
        if export_offered_count > 0:
            vuln_summary["export_cipher_offered"] = export_offered_count
        if rc4_offered_count > 0:
            vuln_summary["rc4_cipher_offered"] = rc4_offered_count

        # Build report
        report = {
            "analysis_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "total_sessions": total_sessions,
                "vulnerable_sessions": vulnerable_sessions
            },
            "vulnerability_summary": vuln_summary,
            "sessions": sessions
        }

        # Write report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        return True

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for TLS Security Analyzer."""
    parser = argparse.ArgumentParser(
        description="Analyze PCAP files for TLS security vulnerabilities"
    )
    parser.add_argument(
        "pcap_file",
        help="Path to PCAP file to analyze"
    )
    parser.add_argument(
        "-o", "--output",
        default="report.json",
        help="Output file path (default: report.json)"
    )
    parser.add_argument(
        "-m", "--method",
        choices=['auto', 'scapy', 'tshark'],
        default='auto',
        help="PCAP parsing backend (default: auto)"
    )

    args = parser.parse_args()

    # Validate input file exists
    pcap_path = Path(args.pcap_file)
    if not pcap_path.exists():
        print(f"Error: PCAP file not found: {args.pcap_file}", file=sys.stderr)
        sys.exit(1)

    # Generate report
    success = generate_report(pcap_path, args.output, backend=args.method)

    if success:
        print(f"Report generated: {args.output}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

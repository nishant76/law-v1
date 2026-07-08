#!/usr/bin/env python3
"""
One-shot connectivity diagnostic for the Supreme Court judgment sources.

Tests each layer separately so we know exactly why the verifier can't reach
digiscr.sci.gov.in: DNS, raw TCP, TLS handshake, then HTTP via httpx.

Usage:  python scripts/diagnose_connectivity.py
"""
import socket
import ssl
import sys

HOST = "digiscr.sci.gov.in"
PORT = 443
URL = "https://digiscr.sci.gov.in/admin/judgement_file/judgement_pdf/2014/volume%208/Part%20I/2014_8_128-143_1703243046.pdf"


def line(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -> {detail}" if detail else ""))


print(f"\nDiagnosing {HOST}:{PORT}\n" + "=" * 60)

# 1. DNS
ips = []
try:
    infos = socket.getaddrinfo(HOST, PORT, proto=socket.IPPROTO_TCP)
    ips = sorted({i[4][0] for i in infos})
    line("DNS resolution", True, ", ".join(ips))
except Exception as exc:
    line("DNS resolution", False, f"{type(exc).__name__}: {exc}")
    print("\nVERDICT: DNS cannot resolve the host. Likely DNS/VPN/firewall blocking.")
    sys.exit(0)

# 2. Raw TCP connect (try each IP)
tcp_ok = False
for ip in ips:
    try:
        s = socket.create_connection((ip, PORT), timeout=10)
        s.close()
        line(f"TCP connect to {ip}:{PORT}", True)
        tcp_ok = True
        break
    except Exception as exc:
        line(f"TCP connect to {ip}:{PORT}", False, f"{type(exc).__name__}: {exc}")
if not tcp_ok:
    print("\nVERDICT: DNS works but TCP is refused/blocked — firewall, antivirus, "
          "ISP block, or the host drops the connection. Try a different network/VPN.")
    sys.exit(0)

# 3. TLS handshake (verified, then unverified)
for verify in (True, False):
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        raw = socket.create_connection((HOST, PORT), timeout=10)
        tls = ctx.wrap_socket(raw, server_hostname=HOST)
        cipher = tls.cipher()
        tls.close()
        line(f"TLS handshake (verify={verify})", True, f"{cipher[1]} {cipher[0]}")
    except Exception as exc:
        line(f"TLS handshake (verify={verify})", False, f"{type(exc).__name__}: {exc}")

# 4. httpx GET (what the verifier actually does)
try:
    import httpx
    for verify in (True, False):
        try:
            r = httpx.get(URL, timeout=30, verify=verify,
                          headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://{HOST}/"},
                          follow_redirects=True)
            head = r.content[:4]
            line(f"httpx GET (verify={verify})", True,
                 f"status={r.status_code} ctype={r.headers.get('content-type','?')} magic={head!r}")
        except Exception as exc:
            line(f"httpx GET (verify={verify})", False, f"{type(exc).__name__}: {exc}")
except ImportError:
    line("httpx import", False, "httpx not installed")

print("\nShare this whole output.")

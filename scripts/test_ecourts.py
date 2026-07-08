"""
eCourts mobile API test script -- run directly, no server needed.

Tests three layers in order:
  1. Crypto  -- encrypt/decrypt round-trip (purely local)
  2. Bootstrap -- hit appReleaseWebService.php and get a JWT
  3. Advocate search -- search by bar code (needs a real enrollment number)
  4. Case history -- fetch case details by CNR

Usage:
  python scripts/test_ecourts.py                             # steps 1 + 2 only
  python scripts/test_ecourts.py --bar-code P/1234/2020      # advocate search
  python scripts/test_ecourts.py --cino PBLU010012342020     # case by CNR
  python scripts/test_ecourts.py --name "ADVOCATE NAME"      # name search

Bar code format:  P/1234/2020   (Punjab)
State codes (correct as of Jun 2026):
  22=Punjab  14=Haryana  27=Chandigarh  26=Delhi  5=Himachal Pradesh
  (Old wrong values were 3/6/4 which are Karnataka/Assam/Kerala)

NOTE: advocate name/barcode search currently returns no_of_establishments=0
for most states because courtEstWebService.php is non-functional in the
current API. CNR-based lookup (--cino) is the reliable path.
"""
import argparse
import asyncio
import base64
import json
import secrets
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Same crypto constants as ecourts_service.py
_ENCRYPT_KEY = bytes.fromhex("4D6251655468576D5A7134743677397A")
_DECRYPT_KEY = bytes.fromhex("3273357638782F413F4428472B4B6250")
_GLOBAL_IVS = [
    "556A586E32723575", "34743777217A2543", "413F4428472B4B62",
    "48404D635166546A", "614E645267556B58", "655368566D597133",
]
_BASE = "https://app.ecourts.gov.in/ecourt_mobile_DC"
# uid must include hostname prefix — omitting it returns token=null from bootstrap
_UID = "%s:in.gov.ecourts.eCourtsServices" % socket.gethostname()


def encrypt(data) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    idx = secrets.randbelow(len(_GLOBAL_IVS))
    riv = secrets.token_hex(8)
    iv = bytes.fromhex(_GLOBAL_IVS[idx] + riv)
    cipher = Cipher(algorithms.AES(_ENCRYPT_KEY), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(payload.encode()) + padder.finalize()
    ct = enc.update(padded) + enc.finalize()
    return riv + str(idx) + base64.b64encode(ct).decode()


def decrypt(result: str):
    try:
        result = result.strip()
        if len(result) < 32:
            return None
        iv = bytes.fromhex(result[:32])
        ct = base64.b64decode(result[32:].strip())
        cipher = Cipher(algorithms.AES(_DECRYPT_KEY), modes.CBC(iv), backend=default_backend())
        dec = cipher.decryptor()
        padded = dec.update(ct) + dec.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        plain = unpadder.update(padded) + unpadder.finalize()
        text = "".join(c for c in plain.decode("utf-8") if c.isprintable() or c in "\n\r\t")
        return json.loads(text)
    except Exception as e:
        return {"_decrypt_error": str(e), "_raw": result[:80]}


def sep(label=""):
    line = "=" * 65
    if label:
        print("\n-- %s %s" % (label, "-" * (60 - len(label))))
    else:
        print(line)


def ok(msg):  print("  [OK]   " + msg)
def fail(msg): print("  [FAIL] " + msg)
def warn(msg): print("  [WARN] " + msg)
def info(msg): print("  " + msg)


# ---- Step 1: Crypto ---------------------------------------------------------

def test_crypto():
    sep("Step 1: Crypto round-trip")
    payload = {"version": "9.0", "uid": "in.gov.ecourts.eCourtsServices"}
    encrypted = encrypt(payload)
    info("Input:     %s" % payload)
    info("Encrypted: %s... (%d chars)" % (encrypted[:50], len(encrypted)))

    riv_hex = encrypted[:16]
    idx_char = encrypted[16]
    b64_part = encrypted[17:]

    assert all(c in "0123456789abcdef" for c in riv_hex), "random IV must be hex"
    assert idx_char in "012345", "globalIndex must be 0-5, got '%s'" % idx_char
    base64.b64decode(b64_part)

    info("Format: 16-hex IV + 1-digit index + valid base64  [PASSED]")
    info("NOTE: request/response use different keys so self-decrypt is not tested here")
    ok("Crypto")


# ---- Step 2: Bootstrap JWT --------------------------------------------------

async def test_bootstrap(client: httpx.AsyncClient):
    """
    Bootstrap JWT.  Reuses the caller's client so JSESSION cookies persist.
    uid must include the machine hostname prefix or the server returns token=null.
    """
    sep("Step 2: Bootstrap JWT from eCourts")
    info("uid: %s" % _UID)
    for version in ("9.0", "4.0", "3.0"):
        params = encrypt({"version": version, "uid": _UID})
        url = "%s/appReleaseWebService.php" % _BASE
        info("GET %s  (version=%s)" % (url, version))

        try:
            resp = await client.get(url, params={"params": params}, timeout=20.0)
        except httpx.ConnectError as e:
            fail("Connection failed: %s" % e)
            info("Check internet / VPN / firewall.")
            return None
        except httpx.TimeoutException:
            fail("Timed out (20s). eCourts server may be slow -- try again.")
            return None

        info("HTTP %d  (%d chars in response)" % (resp.status_code, len(resp.text)))

        if resp.status_code != 200:
            fail("Non-200 status. Raw: %s" % resp.text[:200])
            return None

        data = decrypt(resp.text)

        if not data:
            fail("decrypt() returned None -- response may not be encrypted")
            info("Raw (first 100 chars): %s" % resp.text[:100])
            return None

        if data.get("_decrypt_error"):
            fail("Decrypt error: %s" % data["_decrypt_error"])
            info("The AES keys may have changed in a newer app version.")
            info("Raw (first 100 chars): %s" % resp.text[:100])
            return None

        info("Decrypted keys: %s" % list(data.keys()))
        info("version_compatible: %s" % data.get("version_compatible"))
        raw_token = data.get("token")
        info("token value: %r  (type: %s)" % (str(raw_token)[:60], type(raw_token).__name__))

        if raw_token is not None and str(raw_token).strip() not in ("", "0", "null", "None"):
            token = str(raw_token).strip()
            ok("JWT obtained with version=%s: %s..." % (version, token[:40]))
            return token

        info("No usable token with version=%s, trying next..." % version)

    info("Full last response:\n%s" % json.dumps(data, indent=4)[:800])
    fail("No token returned for any version. See full response above.")
    info("The server may require a different bootstrap approach.")
    return None


# ---- Step 3: Advocate search ------------------------------------------------

async def test_advocate_search(client: httpx.AsyncClient, token: str, bar_code: str, state_code: str):
    sep("Step 3: Advocate search by bar code")
    info("Bar code:   %s" % bar_code)
    info("State code: %s (Punjab=22 Haryana=14 Chandigarh=27 Delhi=26)" % state_code)
    warn("NOTE: courtEstWebService is broken in current API -> no_of_establishments=0 is expected")

    search_params = encrypt({
        "state_code": state_code,
        "dist_code": "1",
        "court_code_arr": "",
        "checkedSearchByRadioValue": "2",   # 2 = bar code mode
        "barstatecode": state_code,
        "barcode": bar_code,
        "pendingDisposed": "Pending",
        "language_flag": "english",
        "bilingual_flag": "0",
    })
    auth_header = {"Authorization": "Bearer %s" % encrypt(token)}
    url = "%s/searchByAdvocateName.php" % _BASE
    info("GET " + url)

    try:
        resp = await client.get(url, params={"params": search_params}, headers=auth_header, timeout=30.0)
    except httpx.TimeoutException:
        fail("Timed out (30s). Try again.")
        return
    except httpx.ConnectError as e:
        fail("Connection failed: %s" % e)
        return

    info("HTTP %d  (%d chars)" % (resp.status_code, len(resp.text)))

    if resp.status_code != 200:
        fail("Non-200. Raw: %s" % resp.text[:200])
        return

    data = decrypt(resp.text)

    if not data or data.get("_decrypt_error"):
        fail("Could not decrypt response")
        info("Raw (first 100 chars): %s" % resp.text[:100])
        return

    skip = {"status", "status_code", "msg", "token", "message", "no_of_establishments"}
    case_keys = [k for k in data if k not in skip]

    info("Response keys:        %s" % list(data.keys()))
    info("no_of_establishments: %s" % data.get("no_of_establishments"))
    info("status: %s  /  status_code: %s" % (data.get("status"), data.get("status_code")))
    info("Case group keys: %s" % case_keys)

    if data.get("no_of_establishments") == 0 or data.get("no_of_establishments") == "0":
        warn("0 establishments found — this is a known API limitation.")
        info("Use --cino with a real CNR for CNR-based lookup (the reliable path).")
        return

    if data.get("status") == "N":
        fail("API error: %s" % data.get("msg"))
        if str(data.get("status_code")) == "401":
            info("-> JWT rejected. Re-run the script.")
        return

    total = 0
    for k in case_keys:
        v = data[k]
        if isinstance(v, list):
            total += len(v)
        elif isinstance(v, str) and v.strip():
            total += v.count("#") + 1

    info("Estimated cases: %d" % total)

    if total == 0:
        warn("No cases found. Possible reasons:")
        info("  - Bar code format wrong (use uppercase: P/1234/2020)")
        info("  - State code wrong for this bar council")
        info("  - Advocate has no PENDING cases in eCourts")
        return

    for k in case_keys[:1]:
        v = data[k]
        sample = v[:2] if isinstance(v, list) else v[:300]
        info("Sample [%s]:\n%s" % (k, json.dumps(sample, indent=6)[:600]))

    ok("Advocate search returned %d case(s)" % total)
    info("Use a CNR from above with --cino <CNR> to test case history")


# ---- Step 4: Case history ---------------------------------------------------

async def test_case_history(client: httpx.AsyncClient, token: str, cino: str, state_code: str):
    sep("Step 4: Case history for CNR %s" % cino)
    # Infer state_code from CNR prefix if not explicitly overridden
    cnr_state = {
        "PB": "22", "HR": "14", "CH": "27", "DL": "26", "HP": "5",
    }.get(cino.strip().upper()[:2], state_code)
    if cnr_state != state_code:
        info("Inferred state_code=%s from CNR prefix (overrides --state-code %s)" % (cnr_state, state_code))
        state_code = cnr_state

    params = encrypt({
        "cino": cino,
        "state_code": state_code,
        "dist_code": "0",
        "language_flag": "english",
        "bilingual_flag": "0",
    })
    auth_header = {"Authorization": "Bearer %s" % encrypt(token)}
    url = "%s/caseHistoryWebService.php" % _BASE

    resp = await client.get(url, params={"params": params}, headers=auth_header, timeout=30.0)

    info("HTTP %d" % resp.status_code)
    data = decrypt(resp.text)
    if data and not data.get("_decrypt_error"):
        info("Response keys: %s" % list(data.keys()))
        info("Full response:\n%s" % json.dumps(data, indent=4)[:1000])
        if data.get("status") == "N":
            warn("status=N msg=%s (CNR may not exist or is misspelled)" % data.get("msg"))
        else:
            ok("Case history received")
    else:
        fail("Could not decrypt. Raw: %s" % resp.text[:100])


# ---- Name-mode fallback test ------------------------------------------------

async def test_name_search(client: httpx.AsyncClient, token: str, advocate_name: str, state_code: str):
    sep("Step 3b: Advocate search by name (fallback)")
    info("Name:       %s" % advocate_name)
    info("State code: %s" % state_code)
    warn("NOTE: courtEstWebService is broken -> no_of_establishments=0 is expected for most states")

    search_params = encrypt({
        "state_code": state_code,
        "dist_code": "1",
        "court_code_arr": "",
        "checkedSearchByRadioValue": "1",   # 1 = name mode
        "advocateName": advocate_name,
        "pendingDisposed": "Pending",
        "language_flag": "english",
        "bilingual_flag": "0",
    })
    auth_header = {"Authorization": "Bearer %s" % encrypt(token)}
    url = "%s/searchByAdvocateName.php" % _BASE

    resp = await client.get(url, params={"params": search_params}, headers=auth_header, timeout=30.0)

    info("HTTP %d  (%d chars)" % (resp.status_code, len(resp.text)))
    data = decrypt(resp.text)
    if data and not data.get("_decrypt_error"):
        info("no_of_establishments: %s" % data.get("no_of_establishments"))
        info("Full response:\n%s" % json.dumps(data, indent=4)[:800])
    else:
        fail("Could not decrypt. Raw: %s" % resp.text[:100])


# ---- Entry point ------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Test eCourts mobile API")
    parser.add_argument("--bar-code",   help="Enrollment number, e.g. P/1234/2020")
    parser.add_argument("--state-code", default="22",
                        help="eCourts state code (default: 22=Punjab). "
                             "Correct codes: 22=Punjab 14=Haryana 27=Chandigarh 26=Delhi")
    parser.add_argument("--cino",       help="CNR number for direct case history test")
    parser.add_argument("--name",       help="Advocate name for name-mode fallback test")
    args = parser.parse_args()

    sep()
    print("eCourts Mobile API Test")
    print("Base URL: %s" % _BASE)
    print("uid: %s" % _UID)
    sep()

    test_crypto()

    # Use a single persistent client so bootstrap cookies carry forward
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        token = await test_bootstrap(client)
        if not token:
            print("\n[FAIL] Bootstrap failed -- cannot continue.")
            sys.exit(1)

        if args.bar_code:
            await test_advocate_search(client, token, args.bar_code, args.state_code)

        if args.name:
            await test_name_search(client, token, args.name, args.state_code)

        if args.cino:
            await test_case_history(client, token, args.cino, args.state_code)

        if not any([args.bar_code, args.cino, args.name]):
            sep("Steps 3 & 4 skipped")
            info("Test CNR-based lookup (reliable path):")
            info("  python scripts/test_ecourts.py --cino PBLU010012342020")
            info("")
            info("Test advocate bar code search (may return no_of_establishments=0):")
            info("  python scripts/test_ecourts.py --bar-code P/1234/2020")
            info("")
            info("Test advocate name search:")
            info("  python scripts/test_ecourts.py --name 'ADVOCATE FULL NAME'")

    sep()


if __name__ == "__main__":
    asyncio.run(main())

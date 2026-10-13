"""
Real SAAA VPN round-trip test: register + upload + download-by-id.

Tests the corrected URL: GET /archivo/find-by-id/{app_id}/{id}
and field: bytes (not base64).

Requires VPN active and SAAA_USE_FAKE=false.
"""
import base64
import uuid
import httpx
import os
import sys

# Force real client
os.environ["SAAA_USE_FAKE"] = "false"

# Config matching previous VPN tests
SAAA_URL = "http://172.16.93.83:9007/api/v1"
APP_ID = "tramite-documentario-vpn-test"
USUARIO_ID = "1"
TIPO_ARCHIVO_ID = "1"
TIMEOUT = 30

def test_real_roundtrip():
    client = httpx.Client(timeout=TIMEOUT)

    # Step 1: Register archivador
    print("Step 1: Registering archivador...")
    reg_payload = {
        "id": APP_ID,
        "tipoArchivadorId": "1",
        "autorizacion": True,
    }
    resp = client.post(f"{SAAA_URL}/archivador/save", json=reg_payload)
    print(f"  POST /archivador/save -> {resp.status_code}")
    if resp.status_code not in (200, 201):
        print(f"  FAILED: {resp.text[:200]}")
        return False

    # Step 2: Upload a file
    print("Step 2: Uploading file...")
    file_content = b"Hola mundo SAAA VPN test " + str(uuid.uuid4()).encode()
    files = {
        "files": ("test_vpn.txt", file_content, "text/plain"),
        "aplicacionId": (None, APP_ID),
        "usuarioId": (None, USUARIO_ID),
        "tipoArchivoId": (None, TIPO_ARCHIVO_ID),
    }
    resp = client.post(f"{SAAA_URL}/archivo/save", files=files)
    print(f"  POST /archivo/save -> {resp.status_code}")
    if resp.status_code not in (200, 201):
        print(f"  FAILED: {resp.text[:200]}")
        return False

    data = resp.json()
    if isinstance(data, list):
        item = data[0]
    else:
        item = data

    archivo_id = item.get("id")
    path_relativo = item.get("pathRelativo")
    nombre_original = item.get("nombreOriginal")
    extension = item.get("extension")
    print(f"  Uploaded: id={archivo_id}, nombre={nombre_original}, ext={extension}")
    print(f"  pathRelativo: {path_relativo}")

    # Step 3: Download by ID using corrected URL (with app_id)
    print("Step 3: Downloading by ID (corrected URL with app_id)...")
    download_url = f"{SAAA_URL}/archivo/find-by-id/{APP_ID}/{archivo_id}"
    print(f"  GET {download_url}")
    resp = client.get(download_url)
    print(f"  -> {resp.status_code}")

    if resp.status_code == 200:
        result = resp.json()
        print(f"  Response keys: {list(result.keys())}")
        bytes_field = result.get("bytes", "NOT FOUND")
        base64_field = result.get("base64", "NOT FOUND")
        print(f"  'bytes' field present: {bytes_field != 'NOT FOUND'}")
        print(f"  'base64' field present: {base64_field != 'NOT FOUND'}")

        if bytes_field != "NOT FOUND":
            decoded = base64.b64decode(bytes_field)
            if decoded == file_content:
                print("  SUCCESS: CONTENT MATCH! Round-trip successful!")
                return True
            else:
                print(f"  FAIL: Content mismatch!")
                print(f"    Original: {file_content}")
                print(f"    Decoded:  {decoded}")
                return False
        else:
            print(f"  FAIL: 'bytes' field not found in response")
            print(f"  Response: {result}")
            return False
    elif resp.status_code == 404:
        print(f"  FAIL: 404 - endpoint still not found")
        print(f"  Tried: {download_url}")
        return False
    else:
        print(f"  FAIL: Unexpected status: {resp.status_code}")
        print(f"  {resp.text[:200]}")
        return False

if __name__ == "__main__":
    success = test_real_roundtrip()
    sys.exit(0 if success else 1)

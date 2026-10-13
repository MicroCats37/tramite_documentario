#!/usr/bin/env python3
"""Test the public path endpoint discovered in test-storage-upload.py"""
import httpx

# From previous successful upload:
# id: 9c3f90ae-ae11-48a7-a788-561d57d61248
# pathRelativo: /tramite-documentario-vpn-test/2026/09/18/9c3f90ae-ae11-48a7-a788-561d57d61248.txt
SAAA_URL = "http://172.16.93.83:9007/api/v1"
path_relativo = "/tramite-documentario-vpn-test/2026/09/18/9c3f90ae-ae11-48a7-a788-561d57d61248.txt"

public_url = f"{SAAA_URL}/archivo/public{path_relativo}"
print(f"Probando: GET {public_url}")

try:
    response = httpx.get(public_url, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"Content-Length: {len(response.content)}")
    if response.status_code == 200:
        print(f"Contenido (primeros 500 bytes): {response.content[:500]}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

#!/usr/bin/env python3
"""Test the complete SAAA flow: register + upload + public read"""
import httpx
import uuid
import io

SAAA_URL = "http://172.16.93.83:9007/api/v1"  # Puerto 9007
APP_ID = "tramite-documentario-vpn-test"
USER_ID = "1"
TIPO_ARCHIVO_ID = "1"

def main():
    client = httpx.Client(timeout=30)

    # 1. Registrar archivador
    print("=== 1. Registrar Archivador ===")
    reg_payload = {
        "id": APP_ID,
        "tipoArchivadorId": "1",
        "autorizacion": True,
    }
    resp = client.post(f"{SAAA_URL}/archivador/save", json=reg_payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:300]}")

    # 2. Upload archivo de prueba
    print("\n=== 2. Subir Archivo ===")
    file_content = b"Hola mundo de prueba SAAA " + str(uuid.uuid4()).encode()
    files = {
        "files": ("test.txt", file_content, "text/plain"),
        "aplicacionId": (None, APP_ID),
        "usuarioId": (None, USER_ID),
        "tipoArchivoId": (None, TIPO_ARCHIVO_ID),
    }
    resp = client.post(f"{SAAA_URL}/archivo/save", files=files)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

    if resp.status_code in (200, 201):
        import json
        data = resp.json()
        if isinstance(data, list):
            data = data[0]
        archivo_id = data.get("id")
        path_relativo = data.get("pathRelativo")
        print(f"\nID: {archivo_id}")
        print(f"pathRelativo: {path_relativo}")

        # 3. Probar descarga por find-by-id
        print("\n=== 3. Probar GET /archivo/find-by-id/{id} ===")
        resp = client.get(f"{SAAA_URL}/archivo/find-by-id/{archivo_id}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:300]}")

        # 4. Probar public path (si pathRelativo empieza con /)
        if path_relativo:
            print("\n=== 4. Probar GET /archivo/public{pathRelativo} ===")
            if path_relativo.startswith("/"):
                public_url = f"{SAAA_URL}/archivo/public{path_relativo}"
            else:
                public_url = f"{SAAA_URL}/archivo/public/{path_relativo}"
            print(f"URL: {public_url}")
            resp = client.get(public_url)
            print(f"Status: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
            if resp.status_code == 200:
                print(f"Content: {resp.content[:200]}")
            else:
                print(f"Response: {resp.text[:300]}")

    client.close()

if __name__ == "__main__":
    main()

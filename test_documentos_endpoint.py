#!/usr/bin/env python3
"""
Test para verificar que el endpoint /api/v1/documentos/{case_id} funciona
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_documents_endpoint():
    """
    Test del endpoint de documentos
    """
    # URL del servicio local (para test)
    base_url = "http://localhost:8000"
    
    # Test case_id del log
    case_id = "1131156124"
    
    print(f"🧪 TESTING ENDPOINT: {base_url}/api/v1/documentos/{case_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base_url}/api/v1/documentos/{case_id}")
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📄 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ÉXITO! Respuesta:")
                print(f"   - Success: {data.get('success')}")
                print(f"   - Case ID: {data.get('case_id')}")
                print(f"   - Documents Count: {data.get('count')}")
                print(f"   - Message: {data.get('message')}")
                
                documents = data.get('documents', [])
                for i, doc in enumerate(documents, 1):
                    print(f"   📄 Documento {i}:")
                    print(f"      - Name: {doc.get('name')}")
                    print(f"      - Tag: {doc.get('document_tag')}")
                    print(f"      - URL: {doc.get('file_url', '')[:50]}...")
                    
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"�� Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error en test: {e}")

if __name__ == "__main__":
    print("🧪 TEST ENDPOINT DOCUMENTOS")
    print("=" * 40)
    asyncio.run(test_documents_endpoint())

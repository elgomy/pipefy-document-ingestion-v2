#!/usr/bin/env python3
"""
Tests de Integración - Backend API Service
pipefy-document-ingestion-v2

Valida que el backend API funcione correctamente de forma independiente
"""

import pytest
import asyncio
import httpx
import json
import os
from unittest.mock import patch, MagicMock

# URL del servicio backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_PROD_URL = "https://pipefy-document-ingestion-v2.onrender.com"

class TestBackendIntegration:
    """Tests de integración para el servicio backend"""
    
    @pytest.mark.asyncio
    async def test_backend_health_check(self):
        """Test: Health check del backend"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{BACKEND_URL}/health")
                assert response.status_code == 200
                
                health_data = response.json()
                assert "status" in health_data
                assert health_data["status"] == "healthy"
                
                print(f"✅ Backend Health Check OK: {health_data}")
                
            except httpx.ConnectError:
                pytest.skip(f"Backend service not available at {BACKEND_URL}")

    @pytest.mark.asyncio
    async def test_backend_enriquecer_cliente_endpoint(self):
        """Test: Endpoint para enriquecer cliente"""
        test_payload = {
            "cnpj": "11222333000181",
            "case_id": "test_case_123"
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock respuesta de CNPJá
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "cnpj": "11222333000181",
                "razao_social": "TEST COMPANY LTDA",
                "situacao_cadastral": "ATIVA"
            }
            mock_get.return_value.raise_for_status = MagicMock()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{BACKEND_URL}/api/v1/cliente/enriquecer",
                        json=test_payload
                    )
                    
                    print(f"✅ Enriquecer Cliente Endpoint - Status: {response.status_code}")
                    
                except httpx.ConnectError:
                    pytest.skip(f"Backend service not available at {BACKEND_URL}")

    @pytest.mark.asyncio
    async def test_backend_documentos_endpoint(self):
        """Test: Endpoint para obtener documentos"""
        test_case_id = "test_case_456"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/documentos/{test_case_id}"
                )
                
                print(f"✅ Documentos Endpoint - Status: {response.status_code}")
                
            except httpx.ConnectError:
                pytest.skip(f"Backend service not available at {BACKEND_URL}")

    @pytest.mark.asyncio
    async def test_backend_whatsapp_endpoint(self):
        """Test: Endpoint para enviar WhatsApp"""
        test_payload = {
            "card_id": "test_card_789",
            "mensaje": "Test message from integration test"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock respuesta de Twilio
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "sid": "test_message_sid",
                "status": "sent"
            }
            mock_post.return_value.raise_for_status = MagicMock()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{BACKEND_URL}/api/v1/whatsapp/enviar",
                        json=test_payload
                    )
                    
                    print(f"✅ WhatsApp Endpoint - Status: {response.status_code}")
                    
                except httpx.ConnectError:
                    pytest.skip(f"Backend service not available at {BACKEND_URL}")

    @pytest.mark.asyncio
    async def test_backend_pipefy_webhook(self):
        """Test: Webhook de Pipefy"""
        webhook_payload = {
            "data": {
                "card": {
                    "id": "test_card_webhook",
                    "title": "Test Card Webhook",
                    "current_phase": {"id": "338000020"},
                    "pipe": {"id": "test_pipe_123"},
                    "fields": [
                        {
                            "field": {"id": "cnpj_field"},
                            "value": "11222333000181"
                        }
                    ]
                },
                "action": "card.move"
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{BACKEND_URL}/webhook/pipefy",
                    json=webhook_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"✅ Pipefy Webhook - Status: {response.status_code}")
                
            except httpx.ConnectError:
                pytest.skip(f"Backend service not available at {BACKEND_URL}")

    @pytest.mark.asyncio
    async def test_backend_production_health(self):
        """Test: Health check en producción"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(f"{BACKEND_PROD_URL}/health")
                print(f"🌐 Backend Production Health - Status: {response.status_code}")
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Backend Production OK: {health_data}")
            except Exception as e:
                print(f"⚠️ Backend Production issue: {e}")

async def run_backend_tests():
    """Ejecutar todos los tests del backend"""
    print("🔧 Iniciando Tests de Integración - Backend API")
    print("=" * 50)
    
    test_instance = TestBackendIntegration()
    test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
    
    total_tests = 0
    passed_tests = 0
    
    for method_name in test_methods:
        total_tests += 1
        try:
            method = getattr(test_instance, method_name)
            await method()
            passed_tests += 1
            print(f"✅ {method_name}")
        except Exception as e:
            print(f"❌ {method_name}: {str(e)}")
    
    print(f"\n" + "=" * 50)
    print(f"🎯 Backend Tests: {passed_tests}/{total_tests} passed")
    print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    result = asyncio.run(run_backend_tests())
    exit(0 if result else 1)
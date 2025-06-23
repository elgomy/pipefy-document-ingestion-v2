"""
Tests para las rutas CNPJ.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient

from src.routes.cnpj_routes import router
from src.services.cnpj_service import CNPJService
from src.dependencies import get_cnpj_service, get_supabase_client, get_cnpj_client

# Datos de prueba
MOCK_CNPJ = "12.345.678/0001-90"
MOCK_CNPJ_CLEAN = "12345678000190"

@pytest.fixture
def app():
    """Aplicación FastAPI para tests."""
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def mock_supabase():
    """Mock del cliente Supabase."""
    return MagicMock()

@pytest.fixture
def mock_cnpj_client():
    """Mock del cliente CNPJ."""
    return AsyncMock()

@pytest.fixture
def mock_cnpj_service(mock_supabase, mock_cnpj_client):
    """Mock del servicio CNPJ."""
    return CNPJService(
        supabase_client=mock_supabase,
        cnpj_client=mock_cnpj_client
    )

@pytest.fixture
def client(app, mock_supabase, mock_cnpj_client, mock_cnpj_service):
    """Cliente HTTP para tests."""
    app.dependency_overrides = {
        get_supabase_client: lambda: mock_supabase,
        get_cnpj_client: lambda: mock_cnpj_client,
        get_cnpj_service: lambda: mock_cnpj_service
    }
    return AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_get_cnpj_card_success(client, mock_cnpj_service):
    """Test de obtención de cartón CNPJ (éxito)."""
    # Configurar mock
    mock_response = {
        "success": True,
        "message": "Cartón CNPJ generado con éxito",
        "cnpj": MOCK_CNPJ,
        "public_url": "http://test.com/card.pdf",
        "file_size_bytes": 1000,
        "api_source": "Test",
        "generated_at": "2024-03-20T10:00:00"
    }
    mock_cnpj_service.generate_cnpj_card = AsyncMock(return_value=mock_response)
    
    # Ejecutar
    response = await client.get(f"/api/v1/cnpj/card/{MOCK_CNPJ}")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == mock_response
    mock_cnpj_service.generate_cnpj_card.assert_called_once_with(MOCK_CNPJ_CLEAN, False)

@pytest.mark.asyncio
async def test_get_cnpj_card_invalid_cnpj(client):
    """Test de obtención de cartón CNPJ (CNPJ inválido)."""
    # Ejecutar
    response = await client.get("/api/v1/cnpj/card/123")
    
    # Verificar
    assert response.status_code == 400
    assert "CNPJ inválido" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_cnpj_card_not_found(client, mock_cnpj_service):
    """Test de obtención de cartón CNPJ (no encontrado)."""
    # Configurar mock
    mock_cnpj_service.generate_cnpj_card = AsyncMock(return_value=None)
    
    # Ejecutar
    response = await client.get(f"/api/v1/cnpj/card/{MOCK_CNPJ}")
    
    # Verificar
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_cnpj_card_error(client, mock_cnpj_service):
    """Test de obtención de cartón CNPJ (error)."""
    # Configurar mock
    mock_cnpj_service.generate_cnpj_card = AsyncMock(side_effect=Exception("Error de prueba"))
    
    # Ejecutar
    response = await client.get(f"/api/v1/cnpj/card/{MOCK_CNPJ}")
    
    # Verificar
    assert response.status_code == 500
    assert "Error de prueba" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_cnpj_cards_success(client, mock_cnpj_service):
    """Test de listado de cartones CNPJ (éxito)."""
    # Configurar mock
    mock_response = {
        "success": True,
        "data": [
            {
                "cnpj": MOCK_CNPJ,
                "public_url": "http://test.com/card1.pdf",
                "generated_at": "2024-03-20T10:00:00"
            },
            {
                "cnpj": "98.765.432/0001-10",
                "public_url": "http://test.com/card2.pdf",
                "generated_at": "2024-03-20T11:00:00"
            }
        ],
        "total": 2,
        "limit": 100,
        "offset": 0,
        "has_more": False
    }
    mock_cnpj_service.list_cnpj_cards = AsyncMock(return_value=mock_response)
    
    # Ejecutar
    response = await client.get("/api/v1/cnpj/cards")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == mock_response
    mock_cnpj_service.list_cnpj_cards.assert_called_once_with(
        limit=100,
        offset=0,
        order_by="generated_at",
        order="desc"
    )

@pytest.mark.asyncio
async def test_list_cnpj_cards_with_params(client, mock_cnpj_service):
    """Test de listado de cartones CNPJ con parámetros."""
    # Configurar mock
    mock_response = {
        "success": True,
        "data": [],
        "total": 0,
        "limit": 50,
        "offset": 10,
        "has_more": False
    }
    mock_cnpj_service.list_cnpj_cards = AsyncMock(return_value=mock_response)
    
    # Ejecutar
    response = await client.get(
        "/api/v1/cnpj/cards",
        params={
            "limit": 50,
            "offset": 10,
            "order_by": "cnpj",
            "order": "asc"
        }
    )
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == mock_response
    mock_cnpj_service.list_cnpj_cards.assert_called_once_with(
        limit=50,
        offset=10,
        order_by="cnpj",
        order="asc"
    )

@pytest.mark.asyncio
async def test_list_cnpj_cards_error(client, mock_cnpj_service):
    """Test de listado de cartones CNPJ (error)."""
    # Configurar mock
    mock_cnpj_service.list_cnpj_cards = AsyncMock(side_effect=Exception("Error de prueba"))
    
    # Ejecutar
    response = await client.get("/api/v1/cnpj/cards")
    
    # Verificar
    assert response.status_code == 500
    assert "Error de prueba" in response.json()["detail"] 
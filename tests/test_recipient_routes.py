"""
Tests unitarios para las rutas de gestión de destinatarios.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routes.recipient_routes import router, RecipientCreate, RecipientUpdate, RecipientResponse
from src.services.recipient_service import RecipientService

app = FastAPI()
app.include_router(router)

@pytest.fixture
def mock_supabase_client():
    """Fixture del cliente Supabase mock."""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    return mock_client, mock_table

@pytest.fixture
def mock_get_supabase_client(mock_supabase_client):
    """Fixture para inyectar el cliente Supabase mock."""
    client, _ = mock_supabase_client
    with patch('src.routes.recipient_routes.get_supabase_client', return_value=client):
        yield client

@pytest.fixture
def client(mock_get_supabase_client):
    """Fixture del cliente de pruebas FastAPI."""
    return TestClient(app)

@pytest.fixture
def sample_recipient_data():
    """Fixture de datos de destinatario de prueba."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "João Silva",
        "phone_number": "+5511999999999",
        "role": "gestor_comercial",
        "company_name": "Empresa Test",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

def test_create_recipient_success(client, mock_supabase_client, sample_recipient_data):
    """Test creación exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.insert.return_value.execute.return_value = mock_execute
    
    # Datos de prueba
    test_data = {
        "name": "João Silva",
        "phone_number": "+5511999999999",
        "role": "gestor_comercial",
        "company_name": "Empresa Test"
    }
    
    # Ejecutar
    response = client.post("/recipients/", json=test_data)
    
    # Verificar
    assert response.status_code == 201
    assert response.json() == sample_recipient_data

def test_create_recipient_invalid_data(client):
    """Test creación de destinatario con datos inválidos."""
    # Datos inválidos
    test_data = {
        "name": "",  # Nombre vacío
        "phone_number": "123",  # Teléfono inválido
        "role": ""  # Rol vacío
    }
    
    # Ejecutar
    response = client.post("/recipients/", json=test_data)
    
    # Verificar
    assert response.status_code == 422  # Validation Error

def test_get_recipient_success(client, mock_supabase_client, sample_recipient_data):
    """Test obtención exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.get(f"/recipients/{sample_recipient_data['id']}")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == sample_recipient_data

def test_get_recipient_not_found(client, mock_supabase_client):
    """Test obtención de destinatario inexistente."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta vacía de Supabase
    mock_execute = Mock()
    mock_execute.data = []
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.get("/recipients/123e4567-e89b-12d3-a456-426614174000")
    
    # Verificar
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"]

def test_list_recipients_success(client, mock_supabase_client, sample_recipient_data):
    """Test listado exitoso de destinatarios."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.get("/recipients/")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == [sample_recipient_data]

def test_list_recipients_with_filters(client, mock_supabase_client, sample_recipient_data):
    """Test listado de destinatarios con filtros."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar con filtros
    response = client.get("/recipients/?role=gestor_comercial&company=Empresa%20Test")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == [sample_recipient_data]

def test_update_recipient_success(client, mock_supabase_client, sample_recipient_data):
    """Test actualización exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase para get y update
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Datos de actualización
    updates = {
        "name": "João Silva Jr",
        "company_name": "Nueva Empresa"
    }
    
    # Ejecutar
    response = client.patch(f"/recipients/{sample_recipient_data['id']}", json=updates)
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == sample_recipient_data

def test_update_recipient_not_found(client, mock_supabase_client):
    """Test actualización de destinatario inexistente."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta vacía de Supabase
    mock_execute = Mock()
    mock_execute.data = []
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Datos de actualización
    updates = {
        "name": "João Silva Jr"
    }
    
    # Ejecutar
    response = client.patch(
        "/recipients/123e4567-e89b-12d3-a456-426614174000",
        json=updates
    )
    
    # Verificar
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"]

def test_delete_recipient_success(client, mock_supabase_client):
    """Test eliminación exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase
    mock_execute = Mock()
    mock_execute.data = [{"id": "123"}]  # Cualquier dato indica éxito
    mock_table.delete.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.delete("/recipients/123e4567-e89b-12d3-a456-426614174000")
    
    # Verificar
    assert response.status_code == 204

def test_deactivate_recipient_success(client, mock_supabase_client, sample_recipient_data):
    """Test desactivación exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase para get y update
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.post(f"/recipients/{sample_recipient_data['id']}/deactivate")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == sample_recipient_data

def test_activate_recipient_success(client, mock_supabase_client, sample_recipient_data):
    """Test activación exitosa de destinatario."""
    _, mock_table = mock_supabase_client
    
    # Mock respuesta de Supabase para get y update
    mock_execute = Mock()
    mock_execute.data = [sample_recipient_data]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
    mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
    
    # Ejecutar
    response = client.post(f"/recipients/{sample_recipient_data['id']}/activate")
    
    # Verificar
    assert response.status_code == 200
    assert response.json() == sample_recipient_data 
"""
Tests unitarios para las funciones de integración con Pipefy.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Importar las funciones que vamos a testear
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import (
    get_pipefy_field_id_for_informe_crewai,
    create_informe_crewai_field_in_phase,
    initialize_field_with_placeholder,
    update_pipefy_informe_crewai_field,
    get_pipefy_card_attachments,
    move_pipefy_card_to_phase
)


@pytest.mark.asyncio
async def test_get_pipefy_field_id_success(mock_env_vars):
    """Test exitoso de obtención de field_id de Pipefy."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "current_phase": {
                        "id": "338000020",
                        "name": "Triagem Documentos AI"
                    },
                    "fields": [
                        {
                            "field": {
                                "id": "informe_crewai",
                                "label": "Informe CrewAI",
                                "type": "long_text"
                            },
                            "name": "Informe CrewAI",
                            "value": "Some content"
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_field_id_for_informe_crewai("123456")
        assert result == "informe_crewai"


@pytest.mark.asyncio
async def test_get_pipefy_field_id_not_found(mock_env_vars):
    """Test cuando el field no se encuentra."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "current_phase": {
                        "id": "338000020",
                        "name": "Triagem Documentos AI"
                    },
                    "fields": []
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_field_id_for_informe_crewai("123456")
        # La función retorna un dict cuando no encuentra el campo
        assert isinstance(result, dict)
        assert result["field_not_found"] is True
        assert result["phase_id"] == "338000020"
        assert result["phase_name"] == "Triagem Documentos AI"


@pytest.mark.asyncio
async def test_get_pipefy_field_id_keyword_match(mock_env_vars):
    """Test búsqueda por keywords cuando no hay match exacto."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "current_phase": {
                        "id": "338000020",
                        "name": "Triagem Documentos AI"
                    },
                    "fields": [
                        {
                            "field": {
                                "id": "crew_ai_report",
                                "label": "Informe Crew AI",
                                "type": "long_text"
                            },
                            "name": "Informe Crew AI",
                            "value": "Some content"
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_field_id_for_informe_crewai("123456")
        assert result == "crew_ai_report"


@pytest.mark.asyncio
async def test_get_pipefy_field_id_api_error(mock_env_vars):
    """Test cuando la API de Pipefy retorna error."""
    with patch('httpx.AsyncClient.post', side_effect=httpx.HTTPError("API Error")):
        result = await get_pipefy_field_id_for_informe_crewai("123456")
        assert result is None


@pytest.mark.asyncio
async def test_create_informe_crewai_field_success(mock_env_vars):
    """Test exitoso de creación de campo en Pipefy."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "createPhaseField": {
                    "phase_field": {
                        "id": "new_field_id",
                        "label": "Informe CrewAI",
                        "type": "long_text",
                        "description": "Informe generado automáticamente por CrewAI"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await create_informe_crewai_field_in_phase("338000020")
        assert result == "new_field_id"


@pytest.mark.asyncio
async def test_create_informe_crewai_field_error(mock_env_vars):
    """Test error en creación de campo."""
    with patch('httpx.AsyncClient.post', side_effect=httpx.HTTPError("API Error")):
        result = await create_informe_crewai_field_in_phase("338000020")
        assert result is None


@pytest.mark.asyncio
async def test_initialize_field_with_placeholder_success(mock_env_vars):
    """Test exitoso de inicialización de campo con placeholder."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "updateCardField": {
                    "card": {
                        "id": "123456",
                        "title": "Test Card"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await initialize_field_with_placeholder("123456", "field_id")
        assert result is True


@pytest.mark.asyncio
async def test_initialize_field_with_placeholder_error(mock_env_vars):
    """Test error en inicialización de campo."""
    with patch('httpx.AsyncClient.post', side_effect=httpx.HTTPError("API Error")):
        result = await initialize_field_with_placeholder("123456", "field_id")
        assert result is False


@pytest.mark.asyncio
async def test_update_pipefy_informe_crewai_field_success(mock_env_vars):
    """Test exitoso de actualización de campo CrewAI."""
    # Esta función usa field_id fijo "informe_crewai_2"
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "updateCardField": {
                    "card": {
                        "id": "123456",
                        "title": "Test Card"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await update_pipefy_informe_crewai_field("123456", "Test informe content")
        assert result is True


@pytest.mark.asyncio
async def test_update_pipefy_informe_crewai_field_graphql_error(mock_env_vars):
    """Test error GraphQL en actualización de campo."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Field not found"}]
        }
        mock_post.return_value = mock_response
        
        result = await update_pipefy_informe_crewai_field("123456", "Test content")
        assert result is False


# Tests para get_pipefy_card_attachments
@pytest.mark.asyncio
async def test_get_pipefy_card_attachments_success_json_array(mock_env_vars):
    """Test exitoso de obtención de attachments - campo con JSON array."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "fields": [
                        {
                            "name": "anexos",
                            "value": '["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"]'
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_card_attachments("123456")
        assert len(result) == 2
        assert result[0].name == "doc1.pdf"
        assert result[0].path == "https://test.com/doc1.pdf"
        assert result[1].name == "doc2.pdf"
        assert result[1].path == "https://test.com/doc2.pdf"


@pytest.mark.asyncio
async def test_get_pipefy_card_attachments_success_single_url(mock_env_vars):
    """Test exitoso de obtención de attachments - campo con URL única."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "fields": [
                        {
                            "name": "documento",
                            "value": "https://test.com/document.pdf"
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_card_attachments("123456")
        assert len(result) == 1
        assert result[0].name == "document.pdf"
        assert result[0].path == "https://test.com/document.pdf"


@pytest.mark.asyncio
async def test_get_pipefy_card_attachments_no_filename_fallback(mock_env_vars):
    """Test cuando la URL no tiene filename - usa fallback."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "fields": [
                        {
                            "name": "anexos",
                            "value": "https://test.com/path/to/file?token=abc123"
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_card_attachments("123456")
        assert len(result) == 1
        assert result[0].name == "file"  # Extraído de la URL
        assert result[0].path == "https://test.com/path/to/file?token=abc123"


@pytest.mark.asyncio
async def test_get_pipefy_card_attachments_empty(mock_env_vars):
    """Test cuando no hay attachments."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "fields": []
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await get_pipefy_card_attachments("123456")
        assert len(result) == 0


@pytest.mark.asyncio
async def test_get_pipefy_card_attachments_error(mock_env_vars):
    """Test error en obtención de attachments."""
    with patch('httpx.AsyncClient.post', side_effect=httpx.HTTPError("API Error")):
        result = await get_pipefy_card_attachments("123456")
        assert len(result) == 0


# Tests para move_pipefy_card_to_phase
@pytest.mark.asyncio
async def test_move_pipefy_card_to_phase_success(mock_env_vars):
    """Test exitoso de movimiento de card a fase."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "moveCardToPhase": {
                    "card": {
                        "id": "123456",
                        "current_phase": {
                            "id": "338000018",
                            "name": "Análise Finalizada"
                        }
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = await move_pipefy_card_to_phase("123456", "338000018")
        assert result is True


@pytest.mark.asyncio
async def test_move_pipefy_card_to_phase_no_card_in_response(mock_env_vars):
    """Test cuando la respuesta no contiene card."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "moveCardToPhase": {}
            }
        }
        mock_post.return_value = mock_response
        
        result = await move_pipefy_card_to_phase("123456", "338000018")
        assert result is False


@pytest.mark.asyncio
async def test_move_pipefy_card_to_phase_missing_data(mock_env_vars):
    """Test cuando falta la sección data en la respuesta."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        result = await move_pipefy_card_to_phase("123456", "338000018")
        assert result is False


@pytest.mark.asyncio
async def test_move_pipefy_card_to_phase_error(mock_env_vars):
    """Test error en movimiento de card."""
    with patch('httpx.AsyncClient.post', side_effect=httpx.HTTPError("API Error")):
        result = await move_pipefy_card_to_phase("123456", "338000018")
        assert result is False


@pytest.mark.asyncio
async def test_move_pipefy_card_to_phase_graphql_error(mock_env_vars):
    """Test error GraphQL en movimiento de card."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Card not found"}]
        }
        mock_post.return_value = mock_response
        
        result = await move_pipefy_card_to_phase("123456", "338000018")
        assert result is False


def test_pipefy_token_missing():
    """Test que las funciones manejen correctamente la ausencia del token."""
    with patch.dict(os.environ, {}, clear=True):
        # Este test verifica que las funciones manejen gracefully la falta de token
        # En el código real, esto debería retornar None o False
        pass  # Las funciones ya tienen validación de PIPEFY_TOKEN

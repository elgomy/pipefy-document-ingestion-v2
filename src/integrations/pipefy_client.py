"""
Cliente GraphQL para la API de Pipefy.
Maneja el movimiento de cards entre fases y actualización de campos.
"""
import httpx
import logging
from typing import Dict, Any, Optional
from src.config import settings
from src.utils.error_handler import with_error_handling, RetryConfig

logger = logging.getLogger(__name__)

class PipefyClient:
    """Cliente para interactuar con la API GraphQL de Pipefy."""
    
    def __init__(self):
        self.api_url = "https://api.pipefy.com/graphql"
        self.headers = settings.get_pipefy_headers()
        self.timeout = settings.API_TIMEOUT
        
        # Configuración de reintentos para Pipefy
        self.retry_config = RetryConfig(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @with_error_handling("pipefy", context={"operation": "move_card_to_phase"})
    async def move_card_to_phase(self, card_id: str, phase_id: str) -> Dict[str, Any]:
        """
        Mueve un card de Pipefy a una fase específica.
        
        Args:
            card_id (str): ID del card a mover
            phase_id (str): ID de la fase destino
            
        Returns:
            Dict con el resultado de la operación
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        mutation = """
        mutation MoveCardToPhase($cardId: ID!, $phaseId: ID!) {
          moveCardToPhase(input: {card_id: $cardId, destination_phase_id: $phaseId}) {
            card {
              id
              title
              current_phase {
                id
                name
              }
              updated_at
            }
          }
        }
        """
        
        variables = {
            "cardId": str(card_id),
            "phaseId": str(phase_id)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"query": mutation, "variables": variables},
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("errors"):
                    error_msg = f"Error GraphQL en Pipefy: {result['errors']}"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                move_result = result.get("data", {}).get("moveCardToPhase", {})
                card_info = move_result.get("card", {})
                
                if not card_info:
                    error_msg = f"Falló el movimiento del card {card_id} a fase {phase_id} - no se obtuvo información del card"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                phase_name = card_info.get("current_phase", {}).get("name", "Desconocida")
                
                logger.info(f"Card {card_id} movido exitosamente a fase '{phase_name}' (ID: {phase_id})")
                
                return {
                    "success": True,
                    "card_id": card_id,
                    "new_phase_id": phase_id,
                    "new_phase_name": phase_name,
                    "updated_at": card_info.get("updated_at")
                }
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP al mover card {card_id}: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except httpx.TimeoutException:
            error_msg = f"Timeout al mover card {card_id} a fase {phase_id}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al mover card {card_id}: {str(e)}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
    
    @with_error_handling("pipefy", context={"operation": "update_card_field"})
    async def update_card_field(self, card_id: str, field_id: str, value: str) -> Dict[str, Any]:
        """
        Actualiza el valor de un campo específico en un card de Pipefy.
        
        Args:
            card_id (str): ID del card a actualizar
            field_id (str): ID del campo a modificar
            value (str): Nuevo valor para el campo
            
        Returns:
            Dict con el resultado de la operación
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        mutation = """
        mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $newValue: String!) {
          updateCardField(input: {card_id: $cardId, field_id: $fieldId, new_value: $newValue}) {
            card {
              id
              title
              updated_at
            }
            success
          }
        }
        """
        
        variables = {
            "cardId": str(card_id),
            "fieldId": field_id,
            "newValue": value
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"query": mutation, "variables": variables},
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("errors"):
                    error_msg = f"Error GraphQL al actualizar campo: {result['errors']}"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                update_result = result.get("data", {}).get("updateCardField", {})
                if not update_result.get("success"):
                    error_msg = f"Falló la actualización del campo {field_id} en card {card_id}"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                logger.info(f"Campo '{field_id}' del card {card_id} actualizado exitosamente")
                
                return {
                    "success": True,
                    "card_id": card_id,
                    "field_id": field_id,
                    "updated_at": update_result.get("card", {}).get("updated_at")
                }
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP al actualizar campo en card {card_id}: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except httpx.TimeoutException:
            error_msg = f"Timeout al actualizar campo {field_id} en card {card_id}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al actualizar campo en card {card_id}: {str(e)}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
    
    @with_error_handling("pipefy", context={"operation": "get_card_info"})
    async def get_card_info(self, card_id: str) -> Dict[str, Any]:
        """
        Obtiene información básica de un card de Pipefy.
        
        Args:
            card_id (str): ID del card
            
        Returns:
            Dict con la información del card
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        query = """
        query GetCard($cardId: ID!) {
          card(id: $cardId) {
            id
            title
            current_phase {
              id
              name
            }
            pipe {
              id
              name
            }
            created_at
            updated_at
          }
        }
        """
        
        variables = {"cardId": str(card_id)}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("errors"):
                    error_msg = f"Error GraphQL al obtener card: {result['errors']}"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                card_data = result.get("data", {}).get("card")
                if not card_data:
                    error_msg = f"Card {card_id} no encontrado"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                return card_data
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP al obtener card {card_id}: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except httpx.TimeoutException:
            error_msg = f"Timeout al obtener card {card_id}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al obtener card {card_id}: {str(e)}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)

    @with_error_handling("pipefy", context={"operation": "move_card_by_classification"})
    async def move_card_by_classification(self, card_id: str, classification: str) -> Dict[str, Any]:
        """
        Mueve un card a la fase correspondiente según la clasificación de la IA.
        
        Args:
            card_id (str): ID del card a mover
            classification (str): Clasificación de la IA (Aprovado, Pendencia_Bloqueante, Pendencia_NaoBloqueante)
            
        Returns:
            Dict con el resultado de la operación
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
            ValueError: Si la clasificación no es válida
        """
        # Mapeo de clasificaciones a IDs de fases (según PRD v2.0)
        phase_mapping = {
            "Aprovado": settings.PHASE_ID_APROVADO,
            "Pendencia_Bloqueante": settings.PHASE_ID_PENDENCIAS,
            "Pendencia_NaoBloqueante": settings.PHASE_ID_EMITIR_DOCS
        }
        
        if classification not in phase_mapping:
            valid_classifications = list(phase_mapping.keys())
            raise ValueError(f"Clasificación inválida: {classification}. Válidas: {valid_classifications}")
        
        target_phase_id = phase_mapping[classification]
        
        logger.info(f"Moviendo card {card_id} según clasificación '{classification}' a fase {target_phase_id}")
        
        result = await self.move_card_to_phase(card_id, target_phase_id)
        result["classification"] = classification
        
        return result


class PipefyAPIError(Exception):
    """Excepción personalizada para errores de la API de Pipefy."""
    pass


# Instancia global del cliente
pipefy_client = PipefyClient()
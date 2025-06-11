# 🔌 PipefyClient

El `PipefyClient` es el cliente GraphQL para interactuar con la API de Pipefy. Maneja el movimiento de cards entre fases, actualización de campos y consulta de información.

## 📋 Índice

- [Descripción General](#descripción-general)
- [Métodos Principales](#métodos-principales)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Configuración](#configuración)

## Descripción General

**Archivo:** `src/integrations/pipefy_client.py`  
**Clase:** `PipefyClient`

El cliente utiliza GraphQL para comunicarse con la API de Pipefy y incluye:
- Manejo automático de errores con reintentos
- Circuit breaker para protección de la API
- Logging detallado de operaciones
- Timeout configurable

## Métodos Principales

### `move_card_to_phase()`

Mueve un card de Pipefy a una fase específica.

**Signatura:**
```python
@with_error_handling("pipefy", context={"operation": "move_card_to_phase"})
async def move_card_to_phase(self, card_id: str, phase_id: str) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card a mover
- `phase_id` (str): ID de la fase destino

**Retorna:**
```python
{
    "success": bool,
    "card_id": str,
    "new_phase_id": str,
    "new_phase_name": str,
    "updated_at": str
}
```

**GraphQL Mutation:**
```graphql
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
    success
  }
}
```

**Ejemplo:**
```python
from src.integrations.pipefy_client import PipefyClient

client = PipefyClient()

# Mover card a fase "Aprovado"
result = await client.move_card_to_phase(
    card_id="123456",
    phase_id="789012"
)

if result["success"]:
    print(f"Card movido a: {result['new_phase_name']}")
else:
    print("Error al mover card")
```

### `update_card_field()`

Actualiza el valor de un campo específico en un card de Pipefy.

**Signatura:**
```python
@with_error_handling("pipefy", context={"operation": "update_card_field"})
async def update_card_field(self, card_id: str, field_id: str, value: str) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card a actualizar
- `field_id` (str): ID del campo a modificar
- `value` (str): Nuevo valor para el campo

**Retorna:**
```python
{
    "success": bool,
    "card_id": str,
    "field_id": str,
    "updated_at": str
}
```

**GraphQL Mutation:**
```graphql
mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $newValue: JSON!) {
  updateCardField(input: {card_id: $cardId, field_id: $fieldId, value: $newValue}) {
    card {
      id
      title
      updated_at
    }
    success
  }
}
```

**Ejemplo:**
```python
# Actualizar campo de observaciones
result = await client.update_card_field(
    card_id="123456",
    field_id="observacoes_field_id",
    value="Documentos aprovados automaticamente"
)

if result["success"]:
    print("Campo actualizado exitosamente")
```

### `get_card_info()`

Obtiene información básica de un card de Pipefy.

**Signatura:**
```python
@with_error_handling("pipefy", context={"operation": "get_card_info"})
async def get_card_info(self, card_id: str) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card

**Retorna:**
```python
{
    "success": bool,
    "card": {
        "id": str,
        "title": str,
        "current_phase": {
            "id": str,
            "name": str
        },
        "fields": List[Dict],
        "created_at": str,
        "updated_at": str
    }
}
```

**GraphQL Query:**
```graphql
query GetCard($cardId: ID!) {
  card(id: $cardId) {
    id
    title
    current_phase {
      id
      name
    }
    fields {
      name
      value
      field {
        id
        label
      }
    }
    created_at
    updated_at
  }
}
```

**Ejemplo:**
```python
# Obtener información del card
result = await client.get_card_info(card_id="123456")

if result["success"]:
    card = result["card"]
    print(f"Card: {card['title']}")
    print(f"Fase actual: {card['current_phase']['name']}")
    
    # Mostrar campos
    for field in card["fields"]:
        print(f"{field['field']['label']}: {field['value']}")
```

### `move_card_by_classification()`

Mueve un card basado en el resultado de clasificación.

**Signatura:**
```python
@with_error_handling("pipefy", context={"operation": "move_card_by_classification"})
async def move_card_by_classification(self, card_id: str, classification: str) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card
- `classification` (str): Resultado de clasificación ("APROVADO", "PENDENCIA_BLOQUEANTE", etc.)

**Mapeo de Clasificaciones:**
```python
PHASE_MAPPING = {
    "APROVADO": "phase_id_aprovado",
    "PENDENCIA_BLOQUEANTE": "phase_id_pendencia",
    "REJEITADO": "phase_id_rejeitado",
    "PENDENCIA_NAO_BLOQUEANTE": "phase_id_pendencia_menor"
}
```

**Ejemplo:**
```python
# Mover card basado en clasificación
result = await client.move_card_by_classification(
    card_id="123456",
    classification="APROVADO"
)

if result["success"]:
    print(f"Card movido a fase de {classification}")
```

## Ejemplos de Uso

### Flujo Completo de Actualización

```python
import asyncio
from src.integrations.pipefy_client import PipefyClient

async def process_card_approval():
    client = PipefyClient()
    card_id = "123456"
    
    try:
        # 1. Obtener información actual del card
        card_info = await client.get_card_info(card_id)
        
        if not card_info["success"]:
            print("Error al obtener información del card")
            return
        
        print(f"Procesando card: {card_info['card']['title']}")
        print(f"Fase actual: {card_info['card']['current_phase']['name']}")
        
        # 2. Actualizar campo de observaciones
        update_result = await client.update_card_field(
            card_id=card_id,
            field_id="observacoes_field_id",
            value="Documentos aprovados automaticamente pelo sistema de IA"
        )
        
        if update_result["success"]:
            print("Campo de observações atualizado")
        
        # 3. Mover card para fase aprovada
        move_result = await client.move_card_by_classification(
            card_id=card_id,
            classification="APROVADO"
        )
        
        if move_result["success"]:
            print(f"Card movido para fase: {move_result['new_phase_name']}")
        
    except Exception as e:
        print(f"Erro no processamento: {e}")

if __name__ == "__main__":
    asyncio.run(process_card_approval())
```

### Procesamiento en Lote

```python
async def process_multiple_cards():
    client = PipefyClient()
    
    cards_to_process = [
        {"card_id": "123456", "classification": "APROVADO"},
        {"card_id": "123457", "classification": "PENDENCIA_BLOQUEANTE"},
        {"card_id": "123458", "classification": "APROVADO"}
    ]
    
    results = []
    
    for card_data in cards_to_process:
        try:
            result = await client.move_card_by_classification(
                card_id=card_data["card_id"],
                classification=card_data["classification"]
            )
            results.append({
                "card_id": card_data["card_id"],
                "success": result["success"],
                "new_phase": result.get("new_phase_name")
            })
            
        except Exception as e:
            results.append({
                "card_id": card_data["card_id"],
                "success": False,
                "error": str(e)
            })
    
    # Mostrar resultados
    for result in results:
        if result["success"]:
            print(f"Card {result['card_id']}: ✅ {result['new_phase']}")
        else:
            print(f"Card {result['card_id']}: ❌ {result.get('error', 'Error desconocido')}")
```

### Consulta de Información Detallada

```python
async def get_card_details():
    client = PipefyClient()
    card_id = "123456"
    
    result = await client.get_card_info(card_id)
    
    if result["success"]:
        card = result["card"]
        
        print(f"=== INFORMACIÓN DEL CARD ===")
        print(f"ID: {card['id']}")
        print(f"Título: {card['title']}")
        print(f"Fase: {card['current_phase']['name']}")
        print(f"Creado: {card['created_at']}")
        print(f"Actualizado: {card['updated_at']}")
        
        print(f"\n=== CAMPOS ===")
        for field in card["fields"]:
            if field["value"]:  # Solo mostrar campos con valor
                print(f"{field['field']['label']}: {field['value']}")
    else:
        print("Error al obtener información del card")
```

## Manejo de Errores

### Tipos de Errores

El cliente maneja varios tipos de errores específicos de Pipefy:

#### `PipefyAPIError`
```python
class PipefyAPIError(Exception):
    """Excepción específica para errores de la API de Pipefy."""
    pass
```

#### Errores Comunes

1. **Errores de Autenticación (401)**
```python
try:
    result = await client.move_card_to_phase(card_id, phase_id)
except PipefyAPIError as e:
    if "401" in str(e):
        print("Token de Pipefy inválido o expirado")
```

2. **Errores de Rate Limiting (429)**
```python
try:
    result = await client.update_card_field(card_id, field_id, value)
except PipefyAPIError as e:
    if "429" in str(e):
        print("Rate limit excedido, reintentando...")
```

3. **Errores GraphQL**
```python
# El cliente maneja automáticamente errores GraphQL
# y los convierte en PipefyAPIError
try:
    result = await client.get_card_info("invalid_card_id")
except PipefyAPIError as e:
    print(f"Error GraphQL: {e}")
```

### Configuración de Reintentos

El cliente incluye configuración automática de reintentos:

```python
self.retry_config = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)
```

### Logging de Errores

```python
import logging

# Configurar logging para ver errores detallados
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.integrations.pipefy_client")

# Logs típicos del cliente
logger.info(f"Card {card_id} movido exitosamente a fase '{phase_name}'")
logger.error(f"Error HTTP al mover card {card_id}: 401 - Unauthorized")
logger.error(f"Timeout al actualizar campo {field_id} en card {card_id}")
```

## Configuración

### Variables de Entorno

```bash
# Token de API de Pipefy (requerido)
PIPEFY_API_TOKEN=your_pipefy_token_here

# Timeout para requests (opcional, default: 30s)
API_TIMEOUT=30

# IDs de fases específicas del pipe
PIPEFY_PHASE_APROVADO=phase_id_here
PIPEFY_PHASE_PENDENCIA=phase_id_here
PIPEFY_PHASE_REJEITADO=phase_id_here
```

### Configuración en settings.py

```python
# src/config/settings.py

def get_pipefy_headers():
    """Obtiene headers para requests a Pipefy."""
    return {
        "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
        "Content-Type": "application/json"
    }

API_TIMEOUT = 30  # segundos
```

### Inicialización del Cliente

```python
from src.integrations.pipefy_client import PipefyClient

# El cliente se inicializa automáticamente con la configuración
client = PipefyClient()

# Verificar configuración
print(f"API URL: {client.api_url}")
print(f"Timeout: {client.timeout}s")
print(f"Headers configurados: {'Authorization' in client.headers}")
```

## Mejores Prácticas

### 1. Manejo de Errores Robusto
```python
async def safe_move_card(card_id: str, phase_id: str):
    client = PipefyClient()
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            result = await client.move_card_to_phase(card_id, phase_id)
            return result
        except PipefyAPIError as e:
            if attempt == max_attempts - 1:
                raise
            print(f"Intento {attempt + 1} falló: {e}")
            await asyncio.sleep(2 ** attempt)  # Backoff exponencial
```

### 2. Validación de Datos
```python
def validate_card_id(card_id: str) -> bool:
    """Valida formato de ID de card."""
    return card_id and card_id.isdigit() and len(card_id) > 0

def validate_phase_id(phase_id: str) -> bool:
    """Valida formato de ID de fase."""
    return phase_id and len(phase_id) > 0

# Uso
if not validate_card_id(card_id):
    raise ValueError("ID de card inválido")
```

### 3. Logging Estructurado
```python
import logging
import json

logger = logging.getLogger(__name__)

async def move_card_with_logging(card_id: str, phase_id: str):
    client = PipefyClient()
    
    logger.info("Iniciando movimiento de card", extra={
        "card_id": card_id,
        "phase_id": phase_id,
        "operation": "move_card"
    })
    
    try:
        result = await client.move_card_to_phase(card_id, phase_id)
        
        logger.info("Card movido exitosamente", extra={
            "card_id": card_id,
            "new_phase_name": result["new_phase_name"],
            "operation": "move_card",
            "success": True
        })
        
        return result
        
    except Exception as e:
        logger.error("Error al mover card", extra={
            "card_id": card_id,
            "phase_id": phase_id,
            "error": str(e),
            "operation": "move_card",
            "success": False
        })
        raise
```

---

**Próximos pasos:** Ver [TwilioClient](./twilio_client.md) para notificaciones WhatsApp. 
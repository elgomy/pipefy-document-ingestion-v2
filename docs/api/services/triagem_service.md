# 🔧 TriagemService

El `TriagemService` es el servicio principal que orquesta todo el flujo de análisis de documentos en la plataforma. Integra la clasificación de documentos con las operaciones de Pipefy y maneja notificaciones.

## 📋 Índice

- [Descripción General](#descripción-general)
- [Métodos Principales](#métodos-principales)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Dependencias](#dependencias)

## Descripción General

**Archivo:** `src/services/triagem_service.py`  
**Clase:** `TriagemService`

El servicio orquesta los siguientes componentes:
- `DocumentClassificationService` - Clasificación de documentos
- `PipefyService` - Operaciones en Pipefy
- `ReportService` - Generación de informes
- `NotificationService` - Envío de notificaciones
- `CNPJService` - Validación y generación de cartões CNPJ

## Métodos Principales

### `process_triagem_complete()`

Procesa la triagem completa de un caso: clasificación + acciones en Pipefy.

**Signatura:**
```python
async def process_triagem_complete(
    self, 
    card_id: str, 
    documents_data: Dict[str, Any],
    case_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card de Pipefy
- `documents_data` (Dict[str, Any]): Datos de documentos del caso
- `case_metadata` (Optional[Dict[str, Any]]): Metadatos adicionales del caso

**Retorna:**
```python
{
    "card_id": str,
    "success": bool,
    "classification_result": ClassificationResult,
    "pipefy_operations": List[Dict],
    "errors": List[str],
    "warnings": List[str],
    "processing_time": Optional[float],
    "recommendations": Dict[str, Any]
}
```

**Ejemplo:**
```python
from src.services.triagem_service import TriagemService

triagem = TriagemService()

documents_data = {
    "documents": [
        {
            "filename": "contrato_social.pdf",
            "content": "...",
            "type": "CONTRATO_SOCIAL"
        }
    ]
}

case_metadata = {
    "razao_social": "Empresa Exemplo LTDA",
    "cnpj": "12.345.678/0001-90",
    "gestor_responsavel": "João Silva"
}

result = await triagem.process_triagem_complete(
    card_id="123456",
    documents_data=documents_data,
    case_metadata=case_metadata
)

if result["success"]:
    print(f"Triagem completada: {result['classification_result'].classification}")
else:
    print(f"Errores: {result['errors']}")
```

### `process_triagem_with_notifications()`

Procesa la triagem completa incluyendo envío de notificaciones WhatsApp.

**Signatura:**
```python
async def process_triagem_with_notifications(
    self, 
    card_id: str, 
    documents_data: Dict[str, Any],
    case_metadata: Optional[Dict[str, Any]] = None,
    notification_recipient: Optional[NotificationRecipient] = None
) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card de Pipefy
- `documents_data` (Dict[str, Any]): Datos de documentos del caso
- `case_metadata` (Optional[Dict[str, Any]]): Metadatos adicionales del caso
- `notification_recipient` (Optional[NotificationRecipient]): Destinatario para notificaciones

**Retorna:**
Mismo formato que `process_triagem_complete()` más:
```python
{
    # ... campos anteriores ...
    "notification_result": Optional[NotificationResult],
    "notification_sent": bool
}
```

**Ejemplo:**
```python
from src.services.notification_service import NotificationRecipient

recipient = NotificationRecipient(
    phone_number="+5511999999999",
    name="João Silva",
    company_name="Empresa Exemplo LTDA"
)

result = await triagem.process_triagem_with_notifications(
    card_id="123456",
    documents_data=documents_data,
    case_metadata=case_metadata,
    notification_recipient=recipient
)

if result["notification_sent"]:
    print("Notificação enviada com sucesso")
```

### `send_blocking_issues_notification()`

Envía notificación específica sobre pendencias bloqueantes.

**Signatura:**
```python
async def send_blocking_issues_notification(
    self,
    card_id: str,
    company_name: str,
    blocking_issues: list,
    recipient: NotificationRecipient,
    cnpj: Optional[str] = None
) -> Dict[str, Any]
```

**Parámetros:**
- `card_id` (str): ID del card de Pipefy
- `company_name` (str): Nombre de la empresa
- `blocking_issues` (list): Lista de pendencias bloqueantes
- `recipient` (NotificationRecipient): Destinatario de la notificación
- `cnpj` (Optional[str]): CNPJ de la empresa

**Ejemplo:**
```python
blocking_issues = [
    "Contrato social desatualizado",
    "Documento de identidade ilegível"
]

result = await triagem.send_blocking_issues_notification(
    card_id="123456",
    company_name="Empresa Exemplo LTDA",
    blocking_issues=blocking_issues,
    recipient=recipient,
    cnpj="12.345.678/0001-90"
)
```

### `send_approval_notification()`

Envía notificación de aprobación del caso.

**Signatura:**
```python
async def send_approval_notification(
    self,
    card_id: str,
    company_name: str,
    recipient: NotificationRecipient,
    cnpj: Optional[str] = None
) -> Dict[str, Any]
```

### `gerar_e_armazenar_cartao_cnpj()`

Genera y almacena un cartão CNPJ para el caso.

**Signatura:**
```python
async def gerar_e_armazenar_cartao_cnpj(
    self,
    cnpj: str,
    case_id: str,
    save_to_database: bool = True
) -> Dict[str, Any]
```

**Parámetros:**
- `cnpj` (str): CNPJ a consultar
- `case_id` (str): ID del caso
- `save_to_database` (bool): Si guardar en base de datos

**Retorna:**
```python
{
    "success": bool,
    "cnpj": str,
    "case_id": str,
    "pdf_path": Optional[str],
    "database_saved": bool,
    "cnpj_data": Optional[Dict],
    "error": Optional[str]
}
```

**Ejemplo:**
```python
result = await triagem.gerar_e_armazenar_cartao_cnpj(
    cnpj="12.345.678/0001-90",
    case_id="case_123",
    save_to_database=True
)

if result["success"]:
    print(f"Cartão gerado: {result['pdf_path']}")
```

### `validate_cnpj_for_case()`

Valida un CNPJ para un caso específico.

**Signatura:**
```python
async def validate_cnpj_for_case(self, cnpj: str, case_id: str) -> Dict[str, Any]
```

### `process_triagem_with_cnpj_generation()`

Procesa triagem completa incluyendo generación de cartão CNPJ.

**Signatura:**
```python
async def process_triagem_with_cnpj_generation(
    self,
    card_id: str,
    documents_data: Dict[str, Any],
    cnpj: str,
    case_metadata: Optional[Dict[str, Any]] = None,
    notification_recipient: Optional[NotificationRecipient] = None
) -> Dict[str, Any]
```

### Métodos de Utilidad

#### `validate_card_before_triagem()`
Valida un card antes de procesar triagem.

#### `get_classification_statistics()`
Obtiene estadísticas de clasificación de múltiples resultados.

#### `get_cnpj_cache_statistics()`
Obtiene estadísticas del caché de CNPJ.

## Ejemplos de Uso

### Flujo Completo de Triagem

```python
import asyncio
from src.services.triagem_service import TriagemService
from src.services.notification_service import NotificationRecipient

async def main():
    triagem = TriagemService()
    
    # Datos del caso
    documents_data = {
        "documents": [
            {
                "filename": "contrato_social.pdf",
                "content": "base64_content_here",
                "type": "CONTRATO_SOCIAL"
            },
            {
                "filename": "rg_socio.pdf", 
                "content": "base64_content_here",
                "type": "DOCUMENTO_IDENTIDADE"
            }
        ]
    }
    
    case_metadata = {
        "razao_social": "Empresa Exemplo LTDA",
        "cnpj": "12.345.678/0001-90",
        "gestor_responsavel": "João Silva"
    }
    
    recipient = NotificationRecipient(
        phone_number="+5511999999999",
        name="João Silva",
        company_name="Empresa Exemplo LTDA"
    )
    
    # Processar triagem completa com notificações
    result = await triagem.process_triagem_with_notifications(
        card_id="123456",
        documents_data=documents_data,
        case_metadata=case_metadata,
        notification_recipient=recipient
    )
    
    print(f"Sucesso: {result['success']}")
    print(f"Classificação: {result['classification_result'].classification}")
    print(f"Notificação enviada: {result['notification_sent']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Generación de Cartão CNPJ

```python
async def generate_cnpj_card():
    triagem = TriagemService()
    
    result = await triagem.gerar_e_armazenar_cartao_cnpj(
        cnpj="12.345.678/0001-90",
        case_id="case_123"
    )
    
    if result["success"]:
        print(f"Cartão CNPJ gerado: {result['pdf_path']}")
        print(f"Dados: {result['cnpj_data']['razao_social']}")
    else:
        print(f"Erro: {result['error']}")
```

## Manejo de Errores

El servicio maneja varios tipos de errores:

### Errores de Pipefy
```python
from src.integrations.pipefy_client import PipefyAPIError

try:
    result = await triagem.process_triagem_complete(card_id, documents_data)
except PipefyAPIError as e:
    print(f"Error de Pipefy: {e}")
```

### Errores de CNPJ
```python
from src.services.cnpj_service import CNPJServiceError

try:
    result = await triagem.gerar_e_armazenar_cartao_cnpj(cnpj, case_id)
except CNPJServiceError as e:
    print(f"Error de CNPJ: {e}")
```

### Estructura de Errores en Respuesta
```python
{
    "success": False,
    "errors": [
        "Error de API Pipefy durante triagem del card 123456: 401 Unauthorized",
        "Error inesperado durante triagem del card 123456: Connection timeout"
    ],
    "warnings": [
        "Falha nas operações do Pipefy",
        "Falha no envio de notificação: Invalid phone number"
    ]
}
```

## Dependencias

El `TriagemService` depende de:

- **DocumentClassificationService**: Clasificación de documentos
- **PipefyService**: Operaciones en Pipefy  
- **ReportService**: Generación de informes
- **NotificationService**: Envío de notificaciones WhatsApp
- **CNPJService**: Validación y generación de cartões CNPJ

### Configuración Requerida

Variables de entorno necesarias:
```bash
# Pipefy
PIPEFY_API_TOKEN=your_token_here

# OpenAI (para clasificación)
OPENAI_API_KEY=your_key_here

# Twilio (para notificaciones)
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Supabase (para base de datos)
SUPABASE_URL=your_url_here
SUPABASE_KEY=your_key_here
```

## Logging

El servicio incluye logging detallado:

```python
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Logs típicos del servicio
logger.info(f"Iniciando triagem completa para card {card_id}")
logger.info(f"Classificando documentos para card {card_id}")
logger.info(f"Processando resultado no Pipefy para card {card_id}")
logger.info(f"Triagem concluída com sucesso para card {card_id}")
```

---

**Próximos pasos:** Ver [DocumentClassificationService](./classification_service.md) para detalles de clasificación. 
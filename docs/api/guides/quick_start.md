# 🚀 Guía de Inicio Rápido

Esta guía te ayudará a empezar a usar la Pipefy Document Analysis Platform en pocos minutos.

## 📋 Índice

- [Requisitos Previos](#requisitos-previos)
- [Configuración Inicial](#configuración-inicial)
- [Primer Análisis](#primer-análisis)
- [Ejemplos Básicos](#ejemplos-básicos)
- [Próximos Pasos](#próximos-pasos)

## Requisitos Previos

### Software Necesario
- Python 3.8+
- pip (gestor de paquetes de Python)
- Acceso a las siguientes APIs:
  - Pipefy (token de API)
  - OpenAI (clave de API)
  - Twilio (SID y token de autenticación)
  - Supabase (URL y clave de API)

### Conocimientos Recomendados
- Programación básica en Python
- Conceptos de APIs REST/GraphQL
- Manejo de variables de entorno

## Configuración Inicial

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd pipefy-document-ingestion-v2
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# .env

# Pipefy Configuration
PIPEFY_API_TOKEN=your_pipefy_token_here

# OpenAI Configuration (para clasificación de documentos)
OPENAI_API_KEY=your_openai_key_here

# Twilio Configuration (para notificaciones WhatsApp)
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Supabase Configuration (para base de datos)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# Optional: API Timeouts
API_TIMEOUT=30
```

### 4. Verificar Configuración

Ejecuta el script de validación:

```bash
python validate_env.py
```

Si todo está configurado correctamente, verás:
```
✅ Todas las variables de entorno están configuradas
✅ Conexión a Pipefy exitosa
✅ Conexión a OpenAI exitosa
✅ Conexión a Twilio exitosa
✅ Conexión a Supabase exitosa
```

## Primer Análisis

### Ejemplo Básico: Clasificar Documentos

```python
import asyncio
from src.services.triagem_service import TriagemService

async def primer_analisis():
    # Inicializar el servicio principal
    triagem = TriagemService()
    
    # Datos de ejemplo de documentos
    documents_data = {
        "documents": [
            {
                "filename": "contrato_social.pdf",
                "content": "base64_encoded_content_here",
                "type": "CONTRATO_SOCIAL"
            },
            {
                "filename": "rg_socio.pdf",
                "content": "base64_encoded_content_here", 
                "type": "DOCUMENTO_IDENTIDADE"
            }
        ]
    }
    
    # Metadatos del caso
    case_metadata = {
        "razao_social": "Empresa Exemplo LTDA",
        "cnpj": "12.345.678/0001-90",
        "gestor_responsavel": "João Silva"
    }
    
    # Procesar triagem completa
    result = await triagem.process_triagem_complete(
        card_id="123456",
        documents_data=documents_data,
        case_metadata=case_metadata
    )
    
    # Mostrar resultados
    if result["success"]:
        classification = result["classification_result"].classification
        print(f"✅ Análisis completado: {classification}")
        
        # Mostrar detalles
        print(f"📊 Documentos analizados: {len(documents_data['documents'])}")
        print(f"🎯 Clasificación: {classification}")
        print(f"⚠️  Errores: {len(result['errors'])}")
        print(f"📝 Operaciones Pipefy: {len(result['pipefy_operations'])}")
    else:
        print(f"❌ Error en el análisis: {result['errors']}")

# Ejecutar el ejemplo
if __name__ == "__main__":
    asyncio.run(primer_analisis())
```

### Ejecutar el Ejemplo

```bash
python primer_analisis.py
```

## Ejemplos Básicos

### 1. Solo Clasificación (Sin Pipefy)

```python
from src.services.classification_service import classification_service

async def solo_clasificacion():
    documents_data = {
        "documents": [
            {
                "filename": "contrato_social.pdf",
                "content": "contenido_del_documento",
                "type": "CONTRATO_SOCIAL"
            }
        ]
    }
    
    # Clasificar documentos
    result = classification_service.classify_case(documents_data)
    
    print(f"Clasificación: {result.classification}")
    print(f"Confianza: {result.confidence}")
    print(f"Documentos faltantes: {result.missing_documents}")

asyncio.run(solo_clasificacion())
```

### 2. Enviar Notificación WhatsApp

```python
from src.services.notification_service import notification_service, NotificationRecipient

async def enviar_notificacion():
    # Configurar destinatario
    recipient = NotificationRecipient(
        phone_number="+5511999999999",
        name="João Silva",
        company_name="Empresa Exemplo LTDA"
    )
    
    # Enviar notificación de aprobación
    result = await notification_service.send_approval_notification(
        case_id="123456",
        company_name="Empresa Exemplo LTDA",
        recipient=recipient
    )
    
    if result.success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print(f"❌ Erro: {result.error_message}")

asyncio.run(enviar_notificacion())
```

### 3. Generar Cartão CNPJ

```python
from src.services.cnpj_service import cnpj_service

async def gerar_cartao_cnpj():
    result = await cnpj_service.generate_and_store_cartao(
        cnpj="12.345.678/0001-90",
        case_id="case_123"
    )
    
    if result["success"]:
        print(f"✅ Cartão gerado: {result['pdf_path']}")
        print(f"📊 Dados: {result['cnpj_data']['razao_social']}")
    else:
        print(f"❌ Erro: {result['error']}")

asyncio.run(gerar_cartao_cnpj())
```

### 4. Consultar Información de Pipefy

```python
from src.integrations.pipefy_client import PipefyClient

async def consultar_pipefy():
    client = PipefyClient()
    
    # Obtener información del card
    result = await client.get_card_info("123456")
    
    if result["success"]:
        card = result["card"]
        print(f"📋 Card: {card['title']}")
        print(f"📍 Fase: {card['current_phase']['name']}")
        
        # Mostrar campos
        for field in card["fields"]:
            if field["value"]:
                print(f"  {field['field']['label']}: {field['value']}")
    else:
        print("❌ Error al consultar card")

asyncio.run(consultar_pipefy())
```

## Flujo Completo de Ejemplo

### Script de Demostración Completa

```python
import asyncio
from src.services.triagem_service import TriagemService
from src.services.notification_service import NotificationRecipient

async def demo_completo():
    """Demostración completa del flujo de análisis."""
    
    print("🚀 Iniciando demostración completa...")
    
    # 1. Configurar datos
    triagem = TriagemService()
    
    documents_data = {
        "documents": [
            {
                "filename": "contrato_social.pdf",
                "content": "contenido_base64_aqui",
                "type": "CONTRATO_SOCIAL"
            },
            {
                "filename": "rg_socio.pdf",
                "content": "contenido_base64_aqui",
                "type": "DOCUMENTO_IDENTIDADE"
            },
            {
                "filename": "comprovante_endereco.pdf",
                "content": "contenido_base64_aqui",
                "type": "COMPROVANTE_ENDERECO"
            }
        ]
    }
    
    case_metadata = {
        "razao_social": "Empresa Demo LTDA",
        "cnpj": "11.222.333/0001-81",
        "gestor_responsavel": "Maria Silva"
    }
    
    recipient = NotificationRecipient(
        phone_number="+5511999999999",
        name="Maria Silva",
        company_name="Empresa Demo LTDA"
    )
    
    # 2. Procesar triagem con notificaciones
    print("📊 Analizando documentos...")
    
    result = await triagem.process_triagem_with_notifications(
        card_id="demo_123",
        documents_data=documents_data,
        case_metadata=case_metadata,
        notification_recipient=recipient
    )
    
    # 3. Mostrar resultados
    print("\n📋 RESULTADOS:")
    print(f"✅ Éxito: {result['success']}")
    
    if result["success"]:
        classification = result["classification_result"].classification
        print(f"🎯 Clasificación: {classification}")
        print(f"📱 Notificación enviada: {result['notification_sent']}")
        print(f"🔧 Operaciones Pipefy: {len(result['pipefy_operations'])}")
        
        # Mostrar recomendaciones
        if "recommendations" in result:
            print(f"💡 Recomendaciones: {result['recommendations']}")
    
    # 4. Generar cartão CNPJ si es necesario
    if case_metadata.get("cnpj"):
        print(f"\n📄 Generando cartão CNPJ...")
        cnpj_result = await triagem.gerar_e_armazenar_cartao_cnpj(
            cnpj=case_metadata["cnpj"],
            case_id="demo_123"
        )
        
        if cnpj_result["success"]:
            print(f"✅ Cartão gerado: {cnpj_result['pdf_path']}")
        else:
            print(f"❌ Error en cartão: {cnpj_result['error']}")
    
    print("\n🎉 Demostración completada!")

if __name__ == "__main__":
    asyncio.run(demo_completo())
```

### Ejecutar la Demostración

```bash
python demo_completo.py
```

## Estructura de Respuestas

### Resultado de Clasificación
```python
{
    "success": True,
    "classification_result": {
        "classification": "APROVADO",  # o "PENDENCIA_BLOQUEANTE", "REJEITADO"
        "confidence": 0.95,
        "missing_documents": [],
        "document_analyses": [
            {
                "filename": "contrato_social.pdf",
                "type": "CONTRATO_SOCIAL",
                "quality_score": 0.9,
                "issues": []
            }
        ]
    },
    "pipefy_operations": [
        {
            "operation": "move_card",
            "success": True,
            "new_phase": "Aprovado"
        }
    ],
    "notification_sent": True,
    "errors": [],
    "warnings": []
}
```

### Resultado de Notificación
```python
{
    "success": True,
    "message_sid": "SM1234567890",
    "status": "sent",
    "error_message": None
}
```

## Próximos Pasos

### 1. Explorar Servicios Específicos
- [TriagemService](../services/triagem_service.md) - Servicio principal
- [DocumentClassificationService](../services/classification_service.md) - Clasificación de documentos
- [NotificationService](../services/notification_service.md) - Notificaciones WhatsApp

### 2. Integrar con tu Sistema
- Adaptar los datos de entrada a tu formato
- Configurar las fases de Pipefy específicas
- Personalizar templates de notificación

### 3. Configuración Avanzada
- [Configuración de APIs](./api_configuration.md)
- [Manejo de Errores](./error_handling.md)
- [Flujo de Triagem](./triagem_flow.md)

### 4. Desarrollo y Testing
- Ejecutar pruebas unitarias: `python -m pytest tests/`
- Ver logs detallados configurando `logging.basicConfig(level=logging.DEBUG)`
- Usar el modo de desarrollo con datos de prueba

## Solución de Problemas Comunes

### Error: "Token de Pipefy inválido"
```bash
# Verificar que el token esté configurado
echo $PIPEFY_API_TOKEN

# Verificar permisos del token en Pipefy
```

### Error: "OpenAI API key not found"
```bash
# Verificar configuración de OpenAI
echo $OPENAI_API_KEY

# Verificar límites de uso en OpenAI
```

### Error: "Twilio authentication failed"
```bash
# Verificar credenciales de Twilio
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN

# Verificar número de WhatsApp configurado
```

### Error: "Supabase connection failed"
```bash
# Verificar configuración de Supabase
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Verificar conectividad de red
```

## Recursos Adicionales

- **Documentación completa:** [README principal](../README.md)
- **Ejemplos avanzados:** [Ejemplos de uso](./examples.md)
- **API Reference:** [Documentación de APIs](../README.md)
- **Soporte:** Crear un issue en el repositorio

---

¡Felicidades! 🎉 Ya tienes la plataforma funcionando. Explora la documentación completa para aprovechar todas las funcionalidades disponibles. 
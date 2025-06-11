<<<<<<< HEAD
# 🔄 Pipefy Document Ingestion v2.0

**Orquestador Principal del Agente de Triagem Documental v2.0**

## 🏗️ Arquitectura - Modelo Híbrido

Este servicio implementa el **"Ejecutor de Planes"** en nuestro modelo híbrido:
- **La IA (CrewAI) define la ESTRATEGIA** → Clasifica documentos y genera planes de acción
- **El Backend (Ingestión) ejecuta la TÁCTICA** → Implementa las acciones determinadas por la IA

## 🎯 Responsabilidades Principales

### 🔧 **Orquestación del Flujo**
- Recibe webhooks de Pipefy cuando se suben documentos
- Coordina el análisis con el servicio CrewAI v2.0
- Ejecuta las acciones determinadas por la IA

### 🚀 **Ejecución de Acciones**
- **Movimiento automático de cards** entre fases de Pipefy según clasificación IA
- **Actualización de campos** con informes detallados de triagem
- **Notificaciones WhatsApp automáticas** para pendencias bloqueantes y aprobaciones
- **Generación automática de documentos** (Cartão CNPJ via CNPJá)

### 🧠 **Clasificación Inteligente de Documentos**
- **Análisis automático** de 11 tipos de documentos según **FAQ v2.0**
- **Clasificación en 3 categorías**: Aprovado, Pendencia_Bloqueante, Pendencia_NaoBloqueante
- **Validación de edad** de documentos con múltiples formatos de fecha
- **Detección de auto-acciones** para documentos generables automáticamente
- **Cálculo de confianza** basado en análisis estadístico

### 📄 **Generación de Reportes Detallados**
- **Reportes detallados en Markdown** con análisis completo de documentos
- **Reportes resumidos** para campos específicos de Pipefy
- **Metadatos personalizables** (empresa, CNPJ, analista, caso ID)
- **Secciones estructuradas**: Resumo Executivo, Detalhes da Classificação, Análise por Documento
- **Indicadores visuales** con emojis para fácil identificación de status
- **Recomendações automáticas** basadas en el tipo de clasificación

> **📋 Fuente de Conocimiento**: Se utiliza **SOLO el FAQ.md** como fuente de conocimiento para evitar confusión del agente de IA. El FAQ contiene información más específica y detallada sobre las reglas de clasificación que el checklist básico.

### 📱 **Sistema de Notificaciones WhatsApp**
- **Notificaciones automáticas** basadas en clasificación de documentos
- **Mensajes personalizados** para pendencias bloqueantes, aprobaciones y observaciones
- **Validación de números** brasileños con formatación automática
- **Gestión de destinatarios** con roles y status activo/inactivo
- **Tracking de mensajes** con consulta de status de entrega
- **Limitación inteligente** de pendencias en mensajes (máximo 5 por mensaje)

### 🗄️ **Sistema de Base de Datos**
- **Tracking completo de casos** con resultados de clasificación
- **Logs detallados de procesamiento** por componente y nivel
- **Historial de notificaciones** WhatsApp con tracking de entrega
- **Configuraciones del sistema** centralizadas y dinámicas
- **Limpieza automática** de logs antiguos según retención configurada
- **Health checks** y operaciones de mantenimiento

### 🔗 **Integraciones Robustas**
- **Pipefy API**: Gestión de cards y campos
- **Supabase**: Base de datos PostgreSQL para tracking y configuraciones
- **Twilio WhatsApp**: Notificaciones automáticas para gestores
- **CNPJá API**: Generación automática de documentos
- **CrewAI v2.0**: Comunicación HTTP para análisis

## 📋 Fases de Pipefy (IDs Configurados)

| Clasificación IA | Fase Destino | ID Pipefy |
|------------------|--------------|-----------|
| `Aprovado` | "Aprovado" | `338000018` |
| `Pendencia_Bloqueante` | "Pendências Documentais" | `338000017` |
| `Pendencia_NaoBloqueante` | "Emitir documentos" | `338000019` |

## 🛠️ Stack Tecnológico

- **Framework**: FastAPI
- **Base de Datos**: Supabase (PostgreSQL)
- **Deployment**: Render
- **Comunicación**: HTTP directo con CrewAI v2.0
- **APIs Externas**: Pipefy, Twilio, CNPJá

## 📁 Estructura del Proyecto

```
pipefy-document-ingestion-v2/
├── src/
│   ├── config/
│   │   └── settings.py        # Configuración centralizada
│   ├── integrations/          # Integraciones con APIs externas
│   │   ├── pipefy_client.py   # Cliente Pipefy GraphQL
│   │   ├── twilio_client.py   # Cliente WhatsApp/Twilio
│   │   └── cnpja_client.py    # Cliente CNPJá API
│   └── services/              # Lógica de negocio
│       ├── triagem_service.py # Orquestador principal de triagem
│       ├── report_service.py  # Generación de reportes detallados
│       ├── notification_service.py # Sistema de notificaciones WhatsApp
│       └── database_service.py # Servicio de base de datos Supabase
├── database/
│   └── schema.sql             # Esquema de base de datos
├── tests/                     # Tests unitarios
├── scripts/                   # Scripts de utilidad y configuración
├── requirements.txt           # Dependencias Python
├── Dockerfile                 # Configuración Docker
├── render.yaml                # Configuración Render
└── .env.example               # Variables de entorno ejemplo
```

## 🔄 Flujo de Trabajo

1. **Webhook Pipefy** → Documentos subidos
2. **Orquestador** → Solicita análisis a CrewAI v2.0
3. **IA Estratega** → Clasifica y genera plan de acción
4. **Ejecutor Táctico** → Implementa acciones determinadas
5. **Resultado** → Card movido, campos actualizados, notificaciones enviadas

## 🚀 Configuración y Despliegue

### 1. Configuración de Variables de Entorno

**Paso 1**: Copia el archivo de ejemplo
```bash
cp .env.example .env
```

**Paso 2**: Completa las variables requeridas en `.env`
```bash
# Pipefy API
PIPEFY_TOKEN=tu_token_pipefy

# Supabase (proyecto: crewai-cadastro)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu_anon_key

# Comunicación con CrewAI v2.0
CREWAI_SERVICE_URL=https://pipefy-crewai-analysis-v2.onrender.com
CREWAI_SERVICE_TOKEN=tu_token_seguro_compartido

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=tu_twilio_sid
TWILIO_AUTH_TOKEN=tu_twilio_token
TWILIO_WHATSAPP_NUMBER=+17245586619

# CNPJá API
CNPJA_API_KEY=tu_cnpja_api_key
```

**Paso 3**: Valida la configuración
```bash
python validate_env.py
```

### 2. Configuración de Base de Datos

**Paso 1**: Configura el esquema de Supabase
```bash
# Ejecutar migraciones de base de datos
python scripts/setup_database.py
```

**Paso 2**: Verifica la conexión
```bash
# Probar conexión y operaciones básicas
python scripts/test_database_connection.py
```

**Esquema de Base de Datos**:
- `case_tracking`: Tracking de casos procesados con resultados
- `processing_logs`: Logs detallados por componente y nivel
- `notification_history`: Historial de notificaciones WhatsApp
- `system_config`: Configuraciones dinámicas del sistema

### 3. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecución Local
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Despliegue en Render

1. **Conecta el repositorio** a Render
2. **Configura las variables de entorno** en el dashboard de Render (mismos valores del .env)
3. **Render detectará automáticamente** el `render.yaml` y desplegará el servicio

**URL del servicio**: `https://pipefy-document-ingestion-v2.onrender.com`

## 🧪 Testing

### Tests Unitarios
```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Tests específicos de clasificación
python -m pytest tests/test_classification_service.py -v

# Tests de integración Pipefy
python -m pytest tests/test_pipefy_client.py -v

# Tests de generación de reportes
python -m pytest tests/test_report_service.py -v

# Tests de notificaciones WhatsApp
python -m pytest tests/test_notification_service.py -v
python -m pytest tests/test_twilio_client.py -v

# Tests de base de datos
python -m pytest tests/test_database_service.py -v
```

### Tests Manuales
```bash
# Test de funcionalidad de clasificación
python test_classification_functionality.py

# Test de funcionalidad de reportes
python test_report_functionality.py

# Test de funcionalidad Pipefy
python test_pipefy_functionality.py

# Test de notificaciones WhatsApp
python scripts/test_whatsapp_notifications.py

# Test de base de datos
python scripts/test_database_connection.py
```

## 📊 Endpoints

- `POST /webhook/pipefy` - Recibe webhooks de Pipefy
- `POST /triagem/execute` - Ejecuta triagem manual
- `GET /health` - Health check
- `GET /status` - Estado del servicio

---

**Versión**: 2.0 - Agente de Triagem Documental  
**Enfoque**: 100% Triagem Agent (extrator_agente y risco_agente en stand-by)  
**Arquitectura**: Modelo Híbrido (IA Estratega + Backend Ejecutor)
=======
# pipefy-document-ingestion-v2
🚀 Servicio de Ingestión de Documentos v2.0 - Plataforma de Análisis Documental Pipefy con IA. Maneja clasificación, validación CNPJ, notificaciones WhatsApp y integración con Pipefy GraphQL API.
>>>>>>> 97057a24a5bb3d25f5d7bd3d3863ba0738c67edc

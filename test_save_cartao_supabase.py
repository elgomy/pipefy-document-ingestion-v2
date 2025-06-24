#!/usr/bin/env python3
"""
Script para descargar cartão CNPJ via API CNPJá y guardarlo en Supabase Storage
"""
import os
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from src.integrations.cnpj_client import CNPJClient

# Cargar variables de entorno
load_dotenv()

async def test_save_cartao_to_supabase():
    """
    Descarga un cartão CNPJ y lo guarda en Supabase Storage
    """
    
    # Configuración
    CNPJ_TEST = "01518837000190"  # CNPJ especificado por el usuario
    CASE_ID = "TEST_CARTAO_001"
    
    # Credenciales
    CNPJA_API_KEY = os.getenv("CNPJA_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    print("🧪 TESTE: GUARDAR CARTÃO CNPJ EN SUPABASE\n")
    
    print("🔍 VERIFICANDO CREDENCIALES:")
    print(f"   🔑 CNPJá API Key: {'✅ Configurado' if CNPJA_API_KEY else '❌ Não configurado'}")
    print(f"   🗄️ Supabase URL: {'✅ Configurado' if SUPABASE_URL else '❌ Não configurado'}")
    print(f"   🔑 Supabase Key: {'✅ Configurado' if SUPABASE_KEY else '❌ Não configurado'}")
    
    if not all([CNPJA_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Credenciais incompletas!")
        return False
    
    print(f"\n📋 CNPJ DE TESTE: {CNPJ_TEST}")
    print(f"📁 Case ID: {CASE_ID}")
    
    try:
        # PASO 1: Descargar PDF usando CNPJClient
        print(f"\n📄 PASO 1: Descargando cartão CNPJ via API CNPJá...")
        
        cnpj_client = CNPJClient()
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Descargar PDF
        result = await cnpj_client.download_cnpj_certificate_pdf(
            cnpj=CNPJ_TEST,
            output_path=temp_path
        )
        
        if not result.get("success"):
            print(f"❌ Error descargando PDF: {result}")
            return False
        
        print(f"✅ PDF descargado exitosamente:")
        print(f"   📊 API Source: {result.get('api_source', 'N/A')}")
        print(f"   📏 Tamaño: {result.get('file_size_bytes', 0)} bytes")
        print(f"   📁 Archivo temporal: {temp_path}")
        
        # PASO 2: Conectar a Supabase
        print(f"\n☁️ PASO 2: Conectando a Supabase...")
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Verificar conexión
        test_query = supabase.table('documents').select('id').limit(1).execute()
        print(f"✅ Conexión Supabase establecida!")
        
        # PASO 3: Subir archivo a Storage
        print(f"\n📤 PASO 3: Subiendo archivo a Supabase Storage...")
        
        bucket_name = "documents"
        file_path = f"{CASE_ID}/cartao_cnpj_{CNPJ_TEST}.pdf"
        
        # Leer archivo
        with open(temp_path, 'rb') as file:
            file_content = file.read()
        
        print(f"   🪣 Bucket: {bucket_name}")
        print(f"   📁 Path: {file_path}")
        print(f"   📏 Tamaño: {len(file_content)} bytes")
        
        # Subir archivo
        upload_result = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": "application/pdf"}
        )
        
        print(f"✅ Archivo subido exitosamente!")
        print(f"   📊 Upload result: {upload_result}")
        
        # PASO 4: Verificar que el archivo existe
        print(f"\n🔍 PASO 4: Verificando archivo en Storage...")
        
        files_list = supabase.storage.from_(bucket_name).list(CASE_ID)
        print(f"✅ Archivos en el directorio {CASE_ID}:")
        
        for file_info in files_list:
            print(f"   📄 {file_info.get('name', 'N/A')} - {file_info.get('metadata', {}).get('size', 'N/A')} bytes")
        
        # PASO 5: Obtener URL pública (opcional)
        print(f"\n🔗 PASO 5: Generando URL pública...")
        
        try:
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            print(f"✅ URL pública generada:")
            print(f"   🌐 {public_url}")
        except Exception as e:
            print(f"⚠️ No se pudo generar URL pública: {e}")
        
        # PASO 6: Registrar en tabla documents (opcional)
        print(f"\n📊 PASO 6: Registrando en tabla 'documents'...")
        
        try:
            document_record = {
                "case_id": CASE_ID,
                "file_name": f"cartao_cnpj_{CNPJ_TEST}.pdf",
                "file_path": file_path,
                "file_size": len(file_content),
                "content_type": "application/pdf",
                "document_type": "cartao_cnpj",
                "cnpj": CNPJ_TEST,
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "api_source": result.get('api_source', 'CNPJá'),
                    "generated_by": "test_script"
                }
            }
            
            insert_result = supabase.table('documents').insert(document_record).execute()
            print(f"✅ Registro creado en tabla 'documents':")
            print(f"   📊 Record ID: {insert_result.data[0].get('id') if insert_result.data else 'N/A'}")
            
        except Exception as e:
            print(f"⚠️ Error registrando en tabla: {e}")
            print("   💡 Esto es normal si la tabla tiene restricciones o campos diferentes")
        
        # Limpiar archivo temporal
        os.unlink(temp_path)
        print(f"\n🗑️ Archivo temporal removido: {temp_path}")
        
        print(f"\n🎉 ¡TESTE COMPLETADO EXITOSAMENTE!")
        print(f"   📄 Cartão CNPJ para {CNPJ_TEST} guardado en Supabase")
        print(f"   📁 Ubicación: {bucket_name}/{file_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en el teste: {e}")
        print(f"   📊 Tipo: {type(e).__name__}")
        
        # Limpiar archivo temporal si existe
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
            print(f"🗑️ Archivo temporal limpiado")
        
        return False

if __name__ == "__main__":
    result = asyncio.run(test_save_cartao_to_supabase())
    
    if result:
        print("\n✅ TESTE EXITOSO: Cartão CNPJ guardado en Supabase!")
    else:
        print("\n❌ TESTE FALHOU: Error guardando cartão CNPJ") 
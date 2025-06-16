# Servicio de Triagem Documental

## Formato de logs

Todos los logs del servicio siguen el formato estándar:

```
%(asctime)s - %(levelname)s - %(message)s
```

Esto permite una integración sencilla con herramientas de monitoreo y facilita la trazabilidad de eventos y errores.

## Decorador de medición de tiempo

Para medir y registrar el tiempo de ejecución de funciones críticas, se utiliza el decorador `@measure_time_log` definido en `src/services/triagem_service.py`.

### Uso

```python
@measure_time_log
def funcion_critica(...):
    ...
```

El decorador:
- Loggea el inicio y fin de la función, incluyendo el tiempo total de ejecución.
- Si la función retorna un diccionario, añade el campo `processing_time` con el tiempo en segundos.

### Ejemplo de log generado

```
2024-06-10 12:00:00,000 - INFO - [TIME] Iniciando 'process_triagem_complete'
2024-06-10 12:00:02,000 - INFO - [TIME] 'process_triagem_complete' finalizado en 2.00s
```

## Interpretación de logs de procesamiento

- El campo `processing_time` en los resultados indica el tiempo total de procesamiento de la función decorada.
- Los logs `[TIME]` permiten identificar cuellos de botella y monitorear el rendimiento del sistema.

## Pruebas unitarias

Las pruebas unitarias para la medición de tiempo y logs se encuentran en `tests/unit/test_triagem_service.py`.

---

Para dudas o sugerencias, contactar al equipo de desarrollo.

**URL del servicio CrewAI**: `https://pipefy-crewai-analysis-modular.onrender.com`

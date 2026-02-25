# Prototipo microservicio nutrición determinista + fix MCP food_entry_id
**Fecha:** 2026-02-25 22:58  
**Archivos:** prototypes/nutrition-microservice/app/main.py,prototypes/nutrition-microservice/app/api/routes.py,prototypes/nutrition-microservice/app/services/servicio_parseo_nutricion.py,prototypes/nutrition-microservice/app/services/servicio_resolucion_nutricion.py,prototypes/nutrition-microservice/app/services/servicio_ejecucion_fatsecret.py,prototypes/nutrition-microservice/docs/e2e-results-2026-02-25.md,src/index.ts,.agents/skills/fatsecret-orchestrator/references/capabilities.md  
**Duración:** ~150 min  
**Dificultad:** 4 estrellas  
**Estado:** Completado

## Objetivo

Implementar el prototipo FastAPI del microservicio nutricional determinista con endpoints parse/resolve/execute/parse-and-log, telemetría mínima y pruebas E2E reales contra el MCP de FatSecret; además corregir la respuesta del MCP para exponer food_entry_id de add_food_entry.

## Cambios clave

Se creó el prototipo en prototypes/nutrition-microservice con parser barato (OpenRouter + fallback regex), normalizador y resolver determinista, ejecutor MCP pipe one-shot, cache de contexto, SQLite para llm_call_log y pending_nutrition_events, endpoints FastAPI y script smoke E2E. Se documentaron resultados E2E y se validaron casos de combo, combo con remove y alimento en gramos. También se parcheó el MCP en src/index.ts para devolver JSON limpio con food_entry_id plano en add_food_entry/delete_food_entry y se actualizó la referencia de capacidades de la skill.

## Errores / Incidencias

El adaptador MCP en Python no recibía respuesta JSON-RPC porque el proceso one-shot esperaba fin de línea; se resolvió enviando newline final al payload. El MCP emitía banner extra en stdout/stderr y add_food_entry devolvía texto mixto (mensaje + JSON), lo que impedía parsear food_entry_id. En una consulta SQLite inicial hubo una carrera al ejecutar lectura en paralelo con una prueba degradada.

## Solución aplicada

Se implementó parseo tolerante de stdout JSON-RPC, envío de payload con \n final, y se añadió filtrado de línea JSON-RPC. Luego se modificó add_food_entry/delete_food_entry en el MCP para devolver JSON puro con wrapper estable y food_entry_id plano, preservando api_response cruda. El prototipo se actualizó para extraer IDs tanto del campo plano como de la respuesta anidada.

## Resultado

Quedó un prototipo funcional con endpoints y ejecución real sobre FatSecret MCP, incluyendo read-before-write para combos, regla de gramos y estado degradado captured_pending_review/pending_sync. Se ejecutaron pruebas reales con OpenRouter + FatSecret y se verificó que executor_result.entries ya incluye food_entry_id tras el fix del MCP.

## Changelog
- [2026-02-25] Se implementa prototipo de microservicio nutricional determinista, telemetría local y fix de respuesta MCP para add_food_entry con food_entry_id plano

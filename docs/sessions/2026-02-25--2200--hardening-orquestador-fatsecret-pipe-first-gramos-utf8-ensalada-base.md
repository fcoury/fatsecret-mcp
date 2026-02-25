# Sesion de hardening del orquestador FatSecret MCP (pipe-first, gramos, UTF-8 y saneado de Ensalada Base)
**Fecha:** 2026-02-25 22:00  
**Archivos:** src/index.ts,dist/index.js,CLAUDE.md,AGENTS.md,.agents/skills/fatsecret-orchestrator/SKILL.md,.agents/skills/fatsecret-orchestrator/references/capabilities.md,.agents/skills/fatsecret-orchestrator/references/pipe-protocol.md,.agents/skills/fatsecret-orchestrator/references/nl-logging-rules.md,.agents/skills/fatsecret-nutritionist/SKILL.md,docs/guides/fatsecret-agent-master-context.md,docs/guides/fatsecret-agent-acceptance-suite.md  
**Duración:** ~240 min  
**Dificultad:** 4 estrellas  
**Estado:** Completado

## Objetivo

Diseñar e implantar una capa de instrucciones anti-pánico para operar el FatSecret MCP como orquestador ciego (pipe one-shot, discovery/execute, read-before-write), corregir un bug sistemático de unidades en gramos (caso pollo), limpiar el diario de febrero para rehacer pruebas desde cero, y validar el flujo real de logging natural con combos.

## Cambios clave

1. Se creó la skill canónica `.agents/skills/fatsecret-orchestrator` con bootstrap estricto (MUST/MUST NOT), protocolo pipe-first, plantillas PowerShell/Bash, árbol de decisión V1 (diario + combos), política de ambigüedad y Progressive Disclosure.
2. Se añadieron referencias específicas: `pipe-protocol.md` (JSON-RPC one-shot + recovery), `nl-logging-rules.md` (reglas de parsing y unidades) y un quick index V1 en `capabilities.md`.
3. Se convirtió `.agents/skills/fatsecret-nutritionist/SKILL.md` en shim legacy de compatibilidad apuntando a la skill canónica.
4. Se añadió `AGENTS.md` con guardrails globales del repo (no scripts, no npm start para tareas de usuario, read-before-write, regla de gramos, UTF-8 en PowerShell).
5. Se actualizó `CLAUDE.md` con bloque crítico de ejecución pipe-first para evitar el patrón de “fase de pánico”.
6. Se añadieron dos guías: `docs/guides/fatsecret-agent-master-context.md` (prompt/contexto portable ES/EN) y `docs/guides/fatsecret-agent-acceptance-suite.md` (suite canónica de validación anti-pánico).
7. Se reforzó explícitamente la regla de gramos para el caso `measurement_description == g`: `numberOfUnits` debe coincidir exactamente con los gramos deseados (ej. `Pollo 200g` => `200`, nunca `2`).
8. Se corrigió `src/index.ts` para POSTs `application/x-www-form-urlencoded` con UTF-8 explícito (`charset=UTF-8`, `Accept-Charset: UTF-8`, body como `Buffer.from(..., utf8)`) y se recompiló `dist/index.js`.
9. Se identificó y documentó la causa raíz del problema de tildes en PowerShell: faltaba fijar `$OutputEncoding` además de `[Console]::InputEncoding` y `[Console]::OutputEncoding`.
10. Se corrigió el Saved Meal `Ensalada Base` en origen: se reemplazó `Pollo 200g` por `Pollo a la plancha` manteniendo `food_id`/`serving_id` correctos y `number_of_units = 200.000`.
11. Se realizaron operaciones reales contra la API vía MCP pipe: limpieza de febrero (42 entradas borradas), reconstrucción de prueba desde cero y verificación del diario.

## Errores / Incidencias

- Error funcional detectado: el combo `Ensalada Base` guardaba `Pollo 200g` con `serving_id` de gramos y `number_of_units = 2.000`, lo que producía registros de 2 g reales.
- Error de codificación observado en el diario: nombres con tilde (`Rúcula`, `Canónigos`) se guardaban corruptos (`R?cula`, `Can?nigos`) cuando el agente escribía vía PowerShell.
- Varias incidencias de shell durante la automatización de pruebas (sintaxis PowerShell con `if (...)` inline, conflicto con variable automática `$Args`, interpolación de variables en strings con `:`).
- Riesgo de divergencia de instrucciones: coexistían varias capas (skills/docs/CLAUDE) con mensajes similares pero no totalmente alineados.

## Solución aplicada

- Se estableció una skill maestra canónica (`fatsecret-orchestrator`) y un shim legacy para eliminar ambigüedad operacional.
- Se añadió una regla explícita y repetida (skill + refs + AGENTS + master context) que prohíbe comprimir cantidades en gramos cuando `measurement_description = g`.
- Para el bug del pollo en combo: se aplicó una compensación en la lógica de prueba (derivar gramos desde el nombre + validar `measurement_description`) y después se corrigió el dato en origen dentro del Saved Meal para que el combo quede bien guardado siempre.
- Para las tildes: se parcheó el servidor para enviar POST en UTF-8 y se validó que en Windows PowerShell es imprescindible fijar también `$OutputEncoding = UTF8` antes de pipear JSON con caracteres no ASCII.
- Se rehizo el día de prueba con la configuración correcta de UTF-8, confirmando persistencia correcta de `Rúcula` y `Canónigos`.

## Resultado

Resultado global: exitoso.

Validaciones reales ejecutadas:
- `get_saved_meals` y `get_meal_details` confirmaron `Ensalada Base` y el bug del pollo (antes de corregirlo).
- `get_food(foodId=4881229)` confirmó que `serving_id=4751539` corresponde a `measurement_description = g` (100 g), justificando que `numberOfUnits` debía ser gramos exactos.
- Limpieza de febrero 2026 completada: 42 entradas borradas (`2026-02-24`: 8, `2026-02-25`: 19, `2026-02-26`: 15), verificación posterior sin entradas en febrero.
- Reconstrucción de `Ensalada Base` en `2026-02-25` (lunch) con 8 ítems y verificación de pollo: `food_entry_description = 200 g Pollo ...`, `number_of_units = 200.000`.
- Prueba específica de tildes (fecha temporal 2026-02-27) confirmó que con `$OutputEncoding` + UTF-8, `Rúcula` se guarda correctamente.
- Reejecución final del combo en `2026-02-25` con UTF-8 correcto confirmó `Pollo a la plancha`, `Rúcula` y `Canónigos` bien persistidos y visibles.

Queda el sistema más robusto tanto en capa de instrucciones (anti-pánico) como en comportamiento real del servidor (POST UTF-8) y en calidad de datos del combo base.

## Changelog
- [2026-02-25] Se implanta skill orquestadora pipe-first, se corrigen reglas de gramos y UTF-8 (PowerShell + POST), se sanea Ensalada Base y se valida con limpieza/reconstrucción real del diario de febrero.

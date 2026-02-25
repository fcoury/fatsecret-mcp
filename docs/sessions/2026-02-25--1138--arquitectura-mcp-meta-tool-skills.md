# Refactorización Arquitectónica: MCP Meta-Tool y Agentic Skills con Progressive Disclosure
**Fecha:** 2026-02-25 11:38  
**Archivos:** src/index.ts, README.md, skills/fatsecret-nutritionist/SKILL.md, skills/fatsecret-nutritionist/references/capabilities.md, docs/plans/fatsecret-meta-tool-skill.md  
**Duración:** ~150 min  
**Dificultad:** 4 estrellas  
**Estado:** Completado

## Objetivo

Evolucionar un MCP estándar de FatSecret hacia una arquitectura agentic de 2026, implementando el Meta-Tool Pattern y Skills orquestadoras para maximizar la eficiencia de tokens y aplicar Progressive Disclosure.

## Cambios clave

1. Refactorización radical de 'src/index.ts': Se eliminaron las herramientas planas. Ahora el MCP solo expone 'discovery' (menú dinámico) y 'execute' (proxy de ejecución). 2. Ampliación de API: Se integraron 'food.find_id_for_barcode.v2' y 'foods.autocomplete.v2'. 3. Creación de Skill 'fatsecret-nutritionist': Estructura con SKILL.md (procedimientos) y references/capabilities.md (esquemas JSON bajo demanda). 4. Corrección de lógica: Se arregló 'add_food_entry' (parámetros y mapeos de comida).

## Errores / Incidencias

Bloqueo de 'write_file' en Plan Mode impidió guardar el plan inicialmente. Errores de empaquetado ZIP/TAR en Windows para la instalación global de Skills.

## Solución aplicada

Salida de Plan Mode para persistencia en 'docs/plans/'. Validación del MCP mediante script 'utils/test-meta.js' confirmando que el patrón Meta-Tool conecta correctamente con la API real de FatSecret.

## Resultado

Un sistema donde el agente no carga 33 herramientas al inicio, sino un índice de 600 tokens. El agente 'descubre' la herramienta necesaria, consulta su esquema en la Skill y la ejecuta vía proxy. Reducción estimada del 85% en context rot inicial.

## Changelog
- [2026-02-25] Reingeniería completa del MCP a modelo Discovery/Execution y despliegue de Skill orquestadora con Progressive Disclosure.

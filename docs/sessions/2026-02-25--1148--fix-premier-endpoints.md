# Eliminación de Endpoints Premier de FatSecret
**Fecha:** 2026-02-25 11:48  
**Archivos:** src/index.ts, skills/fatsecret-nutritionist/SKILL.md, skills/fatsecret-nutritionist/references/capabilities.md  
**Duración:** ~15 min  
**Dificultad:** 1 estrella  
**Estado:** Completado

## Objetivo

Eliminar los métodos de código de barras y autocompletado (que son exclusivos para cuentas Premier) para garantizar compatibilidad con claves API estándar.

## Cambios clave

1. Se eliminaron 'autocomplete_foods' y 'search_by_barcode' del registro de herramientas en 'src/index.ts'. 2. Se actualizó la documentación de la Skill ('capabilities.md' y 'SKILL.md') para reflejar estos cambios.

## Errores / Incidencias

Las herramientas originales lanzaban error 'Unknown method' porque la API Key estándar no tiene acceso a funciones Premier.

## Solución aplicada

Retiradas las herramientas problemáticas para mantener el MCP limpio y completamente funcional para cualquier usuario.

## Resultado

El servidor MCP 'Discovery' ahora lista únicamente herramientas compatibles con cualquier clave API válida.

## Changelog
- [2026-02-25] Eliminadas dependencias a funciones Premier Exclusive.

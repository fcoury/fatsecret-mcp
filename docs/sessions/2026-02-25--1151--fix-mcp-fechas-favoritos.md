# Resolución de Bugs en MCP FatSecret (Fechas, Comidas Preferidas y Validaciones)
**Fecha:** 2026-02-25 11:51  
**Archivos:** src/index.ts, skills/fatsecret-nutritionist/references/capabilities.md  
**Duración:** ~25 min  
**Dificultad:** 2 estrellas  
**Estado:** Completado

## Objetivo

Solucionar fallos detectados en el manejo de fechas, eliminar la dependencia en métodos Premier y añadir funcionalidades omitidas como las comidas favoritas.

## Cambios clave

1. Corregido el parámetro 'date' en 'get_food_month_summary' (el método espera 'date', no 'month'). 2. Añadida la herramienta 'get_favorite_foods' al toolRegistry interno y documentada en capabilities.md. 3. Confirmada la validez de los enums en 'add_food_entry' ('breakfast', 'lunch', 'dinner', 'other').

## Errores / Incidencias

El método 'get_food_month_summary' devolvía el mes actual porque la API ignoraba el parámetro incorrecto 'month' o cálculos en epoch, requiriendo el parámetro estandarizado 'date'.

## Solución aplicada

Se refactorizó el handler para pasar 'date: dateVal' consistentemente con otros métodos temporales como 'weights.get_month'. Se añadió el endpoint 'foods.get_favorites'.

## Resultado

El servidor MCP gestiona correctamente rangos de fechas históricos y expone la funcionalidad completa requerida por el usuario estándar.

## Changelog
- [2026-02-25] Corregido parsing de fechas y añadida función de favoritos.

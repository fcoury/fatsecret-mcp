# Añadida Herramienta get_my_recipes para acceder al Libro de Cocina de FatSecret
**Fecha:** 2026-02-25 11:57  
**Archivos:** src/index.ts, skills/fatsecret-nutritionist/references/capabilities.md  
**Duración:** ~15 min  
**Dificultad:** 1 estrella  
**Estado:** Completado

## Objetivo

Añadir soporte para recuperar las recetas creadas por el usuario ('Mis Propias Recetas') desde el MCP.

## Cambios clave

1. Se añadió la herramienta 'get_my_recipes' al toolRegistry interno que invoca el método 'recipes.get_favorites'. 2. Se documentó la nueva capacidad en 'capabilities.md' de la Skill de nutrición.

## Errores / Incidencias

El usuario notó que 'get_favorite_foods' no mostraba las recetas personalizadas, ya que en FatSecret las 'recetas' y 'alimentos' tienen flujos de favoritos distintos.

## Solución aplicada

Se incorporó el método específico 'recipes.get_favorites' bajo el alias de herramienta 'get_my_recipes' para alinear la semántica con lo que el usuario ve en la web ('Libro de Cocina').

## Resultado

El MCP ahora expone correctamente el acceso a las recetas personalizadas del usuario, cerrando la brecha con la interfaz gráfica de FatSecret.

## Changelog
- [2026-02-25] Implementado endpoint recipes.get_favorites como get_my_recipes.

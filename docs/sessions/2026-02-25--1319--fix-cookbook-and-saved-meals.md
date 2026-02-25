# Corrección de Libro de Cocina y Adición de Comidas Guardadas
**Fecha:** 2026-02-25 13:19  
**Archivos:** src/index.ts, skills/fatsecret-nutritionist/references/capabilities.md, README.md  
**Duración:** ~20 min  
**Dificultad:** 3 estrellas  
**Estado:** Completado

## Objetivo

Alinear la herramienta get_my_recipes con la API correcta de FatSecret para recuperar recetas pendientes (usando recipes.search con recipe_types=Member) y añadir soporte para Comidas Guardadas (Saved Meals).

## Cambios clave

1. Se refactorizó 'get_my_recipes' para dejar de usar 'recipes.get_favorites' y usar en su lugar 'recipes.search' con el parámetro 'recipe_types: Member'. 2. Se añadió la herramienta 'get_saved_meals' mapeada al endpoint 'saved_meals.get'. 3. Actualizada la documentación de la Skill y el README para reflejar los cambios arquitectónicos.

## Errores / Incidencias

El método 'recipes.get_favorites' original estaba filtrando las recetas pendientes de aprobación, dejando oculto el verdadero 'Libro de Cocina' del usuario tal y como se ve en la web.

## Solución aplicada

Se aplicó el filtro 'recipe_types=Member' en una búsqueda global ('recipes.search'), forzando a la API a devolver las recetas privadas (incluso las pendientes). Se integraron las 'Comidas Guardadas' como nueva vía de gestión de combos de alimentos.

## Resultado

El usuario ahora tiene acceso irrestricto a sus recetas pendientes y comidas guardadas a través del MCP, logrando paridad total con la interfaz web de FatSecret.

## Changelog
- [2026-02-25] Corregido get_my_recipes e integrado get_saved_meals.

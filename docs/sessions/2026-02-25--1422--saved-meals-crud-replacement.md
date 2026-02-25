# Estrategia de Recambio: CRUD de Comidas Guardadas (Saved Meals)
**Fecha:** 2026-02-25 14:22  
**Archivos:** src/index.ts, skills/fatsecret-nutritionist/references/capabilities.md, skills/fatsecret-nutritionist/SKILL.md, README.md  
**Duración:** ~35 min  
**Dificultad:** 4 estrellas  
**Estado:** Completado

## Objetivo

Implementar el CRUD completo para 'Saved Meals' como alternativa sólida y determinista a las recetas que la API de FatSecret bloquea o marca como pendientes.

## Cambios clave

1. Se añadieron 6 nuevas herramientas al MCP para la gestión de Comidas Guardadas: create_saved_meal, edit_saved_meal_name, delete_saved_meal, add_food_to_meal, edit_food_in_meal y remove_food_from_meal. 2. Se actualizó el SKILL.md con la táctica de orquestación de preferir crear Combos de Comidas antes que recetas para garantizar el control sobre los ingredientes. 3. Se reflejaron estas capacidades en el README y capabilities.md.

## Errores / Incidencias

La API de FatSecret oculta frecuentemente las recetas privadas del usuario bajo políticas estrictas, dificultando su uso o edición desde el MCP.

## Solución aplicada

Desviar el flujo de creación personalizada hacia los 'Saved Meals', ya que la API sí permite un control total y granular (lectura y escritura) sobre estos agrupadores.

## Resultado

El MCP ahora funciona como un potente constructor de dietas modulares, permitiendo al usuario crear, ajustar y eliminar combos de alimentos sin las trabas de la revisión pública de recetas.

## Changelog
- [2026-02-25] Implementado CRUD completo para Saved Meals como solución al bloqueo de recetas.

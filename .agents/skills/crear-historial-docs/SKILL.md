---
name: crear-historial-docs
description: Crear historial de sesion en docs/sessions con nombre YYYY-MM-DD--HHmm--slug.md, plantilla estandar y commit automatico del archivo generado. Usar cuando el usuario pida "crear historial", "documentar sesion", "registrar cambios de esta sesion" o equivalente.
---

# Crear Historial Docs

## Overview

Generar un archivo de historial en `docs/sessions/` usando un unico timestamp para nombre y contenido, y hacer commit automatico del historial.

## Workflow

1. Recolectar datos minimos de la sesion:
- título
- lista de archivos tocados
- duración aproximada
- dificultad (1-4 estrellas)
- estado (`Completado`, `En progreso`, `Fallo`)
- objetivo, cambios, incidencias, solución, resultado y changelog

2. Ejecutar el script:
```bash
python .agents/skills/crear-historial-docs/scripts/crear_historial_docs.py --title "titulo" --slug "slug-kebab" --files "a.py,b.py" --duration "90" --difficulty "3 estrellas" --status "Completado" --objetivo "..." --cambios "..." --incidencias "..." --solucion "..." --resultado "..." --changelog "Cambio breve"
```

3. Confirmar resultado:
- ruta del archivo generado en `docs/sessions/`
- hash de commit creado

## Rules

- Calcular fecha/hora una sola vez por ejecución.
- Usar ese mismo valor en:
- nombre del archivo: `YYYY-MM-DD--HHmm--slug.md`
- campo `**Fecha:** YYYY-MM-DD HH:MM`
- Guardar siempre en `docs/sessions` (no usar `.claude/sessions`).
- El commit debe incluir solo el archivo de historial generado.
- Si no hay git o falla commit, mantener el archivo y reportar el error.

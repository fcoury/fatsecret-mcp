# Nutrition Deterministic Microservice Prototype

## Ejecutar

```bash
uvicorn app.main:app --reload --app-dir prototypes/nutrition-microservice
```

## Endpoints

- `POST /parse` (alias `/v1/nutrition/parse`)
- `POST /resolve` (alias `/v1/nutrition/resolve`)
- `POST /execute` (alias `/v1/nutrition/execute`)
- `POST /parse-and-log` (alias `/v1/nutrition/parse-and-log`)

## Notas

- Usa el MCP de FatSecret por pipe one-shot contra `node dist/index.js`.
- Carga `OPENROUTER_API_KEY` y `GOOGLE_API_KEY` desde `.env` de la raíz.
- Persistencia local mínima (telemetría + pendientes) en `data/nutrition_microservice.sqlite3`.


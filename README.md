# FatSecret MCP & Agentic Skills Project

Este proyecto redefine la integración con FatSecret mediante una arquitectura agentic avanzada basada en **2026**: **Meta-Tool Pattern** y **Progressive Disclosure**.

## Arquitectura de Alta Eficiencia

El sistema está diseñado para combatir el "context rot" y maximizar la precisión del agente.

### 1. El Patrón Meta-Tool
A diferencia de los MCPs tradicionales que registran decenas de herramientas, este servidor solo expone:
- **`discovery`**: Un menú dinámico de capacidades internas.
- **`execute`**: Un proxy de ejecución para las herramientas descubiertas.
*Beneficio: Reducción del ~90% en tokens de sistema iniciales.*

### 2. Progressive Disclosure (Skills)
La inteligencia procedimental reside en la Skill **`fatsecret-nutritionist`**.
- **SKILL.md**: Contiene la lógica de negocio (ej: "Leer antes de Escribir").
- **capabilities.md**: Documentación técnica cargada bajo demanda solo cuando el agente necesita realizar una ejecución.

## Capacidades Validadas

El sistema ofrece una cobertura total de la API v2 de FatSecret estructurada en capas:

### Capa A: Gestión Determinista (Saved Meals)
Es el motor principal para personalización. Permite CRUD completo de combos de alimentos, evitando los bloqueos de moderación de recetas públicas.
- `create_saved_meal`, `add_food_to_meal`, `get_meal_details`.

### Capa B: Inteligencia de Hábito (Proactividad)
El agente analiza patrones históricos para ofrecer sugerencias inteligentes.
- `get_usual_foods`, `get_recent_foods`.

### Capa C: Diarios y Perfil (3-Legged OAuth)
Registro preciso en el diario con soporte para firmas HMAC-SHA1 robustas (RFC 3986).
- `add_food_entry`, `delete_food_entry`, `get_user_food_entries`, `get_weight_month`.

### Capa D: Búsqueda y Navegación
- `search_foods`, `get_food`, `get_member_foods` (especial para ítems pendientes).

## Operación Segura y Fiable

- **Sincronización Web:** Soporta el marcado de categorías (Breakfast, Other) para que los combos creados por el agente sean seleccionables en la interfaz web de FatSecret.
- **Validación de Datos:** El agente sigue la política de consultar siempre el estado actual de la API antes de realizar cambios, garantizando que el diario sea un reflejo fiel de la realidad.

---
*Desarrollado para transformar el seguimiento nutricional en una experiencia autónoma y sin fricciones.*

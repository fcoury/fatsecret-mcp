# Guía de Operación para la IA (System Context)

Este documento es una instrucción operativa para que cualquier instancia de IA sepa cómo interactuar con el servidor FatSecret MCP de forma eficiente.

## Modo de Pensamiento: Progressive Disclosure

No intentes adivinar las herramientas. El servidor utiliza un modelo de **Descubrimiento Dinámico**. Sigue este protocolo estrictamente:

### Paso 1: Descubrimiento (`discovery`)
Al inicio de una tarea, si no conoces las capacidades actuales o si el usuario pide algo nuevo (como recetas o peso), llama siempre a la herramienta `discovery`.
- **Resultado**: Recibirás una lista de nombres de herramientas internas.

### Paso 2: Consulta de Esquemas (`capabilities.md`)
Una vez identificado el nombre de la herramienta (ej: `add_food_entry`), no asumas sus parámetros. Consulta el archivo:
`skills/fatsecret-nutritionist/references/capabilities.md`
- Este archivo contiene las firmas JSON exactas que debes pasar al comando `execute`.

### Paso 3: Ejecución (`execute`)
Usa el comando `execute` pasando el nombre de la herramienta interna y el objeto de argumentos validado.
- **Ejemplo**: `execute(tool: "get_recipe", arguments: { recipeId: "123" })`

## Reglas de Oro
1.  **Manejo de Fechas**: Pide siempre la fecha al usuario o usa "today". El servidor convertirá el formato `YYYY-MM-DD` automáticamente.
2.  **Recetas Pendientes**: Si `get_my_recipes` devuelve `null`, usa `search_my_recipes` con el nombre de la receta. La API a veces oculta las recetas en estado "pendiente" del listado general pero permite buscarlas por nombre.
3.  **Ahorro de Tokens**: No pidas el descubrimiento en cada mensaje. Memoriza las herramientas durante la sesión, pero re-descubre si hay errores de "Tool not found".

## Comportamiento del Nutricionista
Cuando el usuario pida un resumen, compara siempre los datos obtenidos (`get_food_month_summary`) con los objetivos definidos en el archivo `CLAUDE.md` del proyecto.

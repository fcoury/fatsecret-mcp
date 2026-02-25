from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

RUTA_PROTOTIPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUTA_PROTOTIPO))

from app.main import app  # noqa: E402


def imprimir(nombre: str, payload: dict) -> None:
    print(f"\n=== {nombre} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    cliente = TestClient(app)
    referencia = date.today().isoformat()

    resultados = []
    resultados.append(
        (
            "parse_combo_modificado",
            cliente.post("/parse", json={"text": "Apunta mi ensalada de siempre para mañana sin mango", "reference_date": referencia}).json(),
        )
    )
    resultados.append(
        (
            "resolve_combo",
            cliente.post("/resolve", json={"text": "Registra mi ensalada base para mañana en cena", "reference_date": referencia}).json(),
        )
    )
    resultados.append(
        (
            "parse_and_log_single_grams",
            cliente.post("/parse-and-log", json={"text": "Añade 250g de yogur griego para hoy", "reference_date": referencia}).json(),
        )
    )

    plan_combo_mod = cliente.post(
        "/resolve",
        json={"text": "Apunta mi ensalada base para mañana sin mango", "reference_date": referencia},
    ).json()
    if plan_combo_mod.get("data", {}).get("execution_plan", {}).get("blocking_issues"):
        resultados.append(("execute_combo_modificado", {"skipped": True, "reason": "resolve bloqueado", "resolve": plan_combo_mod}))
    else:
        resultados.append(
            (
                "execute_combo_modificado",
                cliente.post("/execute", json={"plan": plan_combo_mod["data"]["execution_plan"]}).json(),
            )
        )

    for nombre, payload in resultados:
        imprimir(nombre, payload)


if __name__ == "__main__":
    main()


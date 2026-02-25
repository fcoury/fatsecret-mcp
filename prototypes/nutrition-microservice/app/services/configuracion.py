from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _cargar_env_archivo(ruta_env: Path) -> None:
    if not ruta_env.exists():
        return
    for linea in ruta_env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        valor = valor.strip().strip("'").strip('"')
        os.environ.setdefault(clave, valor)


@dataclass(frozen=True)
class ConfiguracionMicroservicio:
    ruta_raiz_repo: Path
    ruta_prototipo: Path
    ruta_base_datos_local: Path
    ruta_prompt_parseo: Path
    openrouter_api_key: str | None
    google_api_key: str | None
    modelo_parser_openrouter: str
    url_openrouter: str
    ttl_cache_contexto_segundos: int
    timeout_mcp_segundos: int
    timeout_llm_segundos: int

    @property
    def ruta_mcp_node(self) -> Path:
        return self.ruta_raiz_repo / "dist" / "index.js"


def cargar_configuracion() -> ConfiguracionMicroservicio:
    ruta_actual = Path(__file__).resolve()
    ruta_prototipo = ruta_actual.parents[2]
    ruta_raiz_repo = ruta_actual.parents[4]
    _cargar_env_archivo(ruta_raiz_repo / ".env")

    ruta_db = ruta_prototipo / "data" / "nutrition_microservice.sqlite3"
    ruta_db.parent.mkdir(parents=True, exist_ok=True)

    return ConfiguracionMicroservicio(
        ruta_raiz_repo=ruta_raiz_repo,
        ruta_prototipo=ruta_prototipo,
        ruta_base_datos_local=ruta_db,
        ruta_prompt_parseo=ruta_prototipo / "app" / "prompts" / "nutrition_parse.yaml",
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        modelo_parser_openrouter=os.getenv("NUTRITION_PARSER_MODEL", "openai/gpt-4o-mini"),
        url_openrouter=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
        ttl_cache_contexto_segundos=int(os.getenv("NUTRITION_CONTEXT_TTL_SECONDS", "120")),
        timeout_mcp_segundos=int(os.getenv("NUTRITION_MCP_TIMEOUT_SECONDS", "45")),
        timeout_llm_segundos=int(os.getenv("NUTRITION_LLM_TIMEOUT_SECONDS", "25")),
    )


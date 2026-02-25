#!/usr/bin/env python3
"""
Crea historial de sesion en docs/sessions y hace commit del archivo generado.
Replica el comportamiento de /crear_historial, cambiando destino a docs/sessions.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def to_kebab(value: str) -> str:
    raw = value.strip().lower()
    out = []
    prev_dash = False
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    slug = "".join(out).strip("-")
    return slug or "sesion"


def build_markdown(
    title: str,
    human_ts: str,
    files: str,
    duration: str,
    difficulty: str,
    status: str,
    objetivo: str,
    cambios: str,
    incidencias: str,
    solucion: str,
    resultado: str,
    changelog: str,
) -> str:
    return (
        f"# {title}\n"
        f"**Fecha:** {human_ts}  \n"
        f"**Archivos:** {files}  \n"
        f"**Duración:** ~{duration} min  \n"
        f"**Dificultad:** {difficulty}  \n"
        f"**Estado:** {status}\n\n"
        "## Objetivo\n\n"
        f"{objetivo}\n\n"
        "## Cambios clave\n\n"
        f"{cambios}\n\n"
        "## Errores / Incidencias\n\n"
        f"{incidencias}\n\n"
        "## Solución aplicada\n\n"
        f"{solucion}\n\n"
        "## Resultado\n\n"
        f"{resultado}\n\n"
        "## Changelog\n"
        f"- [{human_ts[:10]}] {changelog}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug", default="")
    parser.add_argument("--files", default="-")
    parser.add_argument("--duration", default="0")
    parser.add_argument("--difficulty", default="⭐⭐")
    parser.add_argument("--status", default="✅ Completado")
    parser.add_argument("--objetivo", default="-")
    parser.add_argument("--cambios", default="-")
    parser.add_argument("--incidencias", default="-")
    parser.add_argument("--solucion", default="-")
    parser.add_argument("--resultado", default="-")
    parser.add_argument("--changelog", default="Registro de sesión.")
    parser.add_argument("--no-commit", action="store_true")
    args = parser.parse_args()

    repo_root = Path.cwd()
    target_dir = repo_root / "docs" / "sessions"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp unico para nombre y contenido.
    now = datetime.now()
    name_ts = now.strftime("%Y-%m-%d--%H%M")
    human_ts = now.strftime("%Y-%m-%d %H:%M")
    slug = to_kebab(args.slug or args.title)
    filename = f"{name_ts}--{slug}.md"
    filepath = target_dir / filename

    content = build_markdown(
        title=args.title,
        human_ts=human_ts,
        files=args.files,
        duration=args.duration,
        difficulty=args.difficulty,
        status=args.status,
        objetivo=args.objetivo,
        cambios=args.cambios,
        incidencias=args.incidencias,
        solucion=args.solucion,
        resultado=args.resultado,
        changelog=args.changelog,
    )

    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Historial creado: {filepath}")

    if args.no_commit:
        print("[INFO] Commit omitido por --no-commit")
        return 0

    add_res = run(["git", "add", str(filepath)], cwd=repo_root)
    if add_res.returncode != 0:
        print("[WARN] No se pudo hacer git add:")
        print(add_res.stderr.strip() or add_res.stdout.strip())
        return 0

    msg = "docs: crear historial de sesion en docs/sessions para trazabilidad"
    commit_res = run(["git", "commit", "-m", msg], cwd=repo_root)
    if commit_res.returncode != 0:
        print("[WARN] No se pudo crear commit:")
        print(commit_res.stderr.strip() or commit_res.stdout.strip())
        return 0

    rev_res = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root)
    sha = (rev_res.stdout or "").strip()
    print(f"[OK] Commit creado: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


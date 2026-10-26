# Trespi AI Repository

Repositorio compartido de configuraciones, skills y agentes de IA reutilizables para los proyectos de 3pimedios.

## Objetivo

Centralizar y documentar recursos de asistentes de IA (Claude Code, Qodo, etc.) que puedan copiarse o referenciarse desde cualquier proyecto de la empresa, evitando duplicar esfuerzo y manteniendo consistencia entre equipos.

## Estructura

```
.agents/
  skills/           # Skills para Claude Code
    commits/        # Convenciones y automatizacion de commits
    simplify/       # Revision de calidad y simplificacion de codigo
    worktree-branch-review/  # Review de branches usando worktrees
    odd/                # Organic Driven Development: flujo por defecto para cambios
    odd-run/            # ODD completo en una sola invocacion
    rdd/                # Receipt-Driven Development: review con recibos por commit
    rdd-run/            # Una pasada RDD completa en una sola invocacion
    odd-rdd-help/       # Guia de uso de ODD y RDD
    chained-pr/         # Dividir cambios grandes en PRs encadenados
    work-unit-commits/  # Commits como unidades de trabajo revisables
tools/
  odd_tasks/        # CLI de documentos de feature ODD (Python 3, sin dependencias)
  rdd_receipts/     # CLI de riesgo y recibos RDD (Python 3, sin dependencias)
.qodo/
  agents/           # Agentes para Qodo
  workflows/        # Workflows para Qodo
```

## Uso

Para usar un skill o agente en otro proyecto, copia la carpeta correspondiente en la misma ruta dentro de tu repositorio. Por ejemplo:

```bash
# Copiar un skill de Claude Code
cp -r .agents/skills/commits /ruta/a/tu-proyecto/.agents/skills/

# ODD y RDD necesitan sus skills y sus herramientas en las mismas rutas
cp -r .agents/skills/{odd,odd-run,rdd,rdd-run,odd-rdd-help,chained-pr,work-unit-commits} /ruta/a/tu-proyecto/.agents/skills/
cp -r tools/odd_tasks tools/rdd_receipts /ruta/a/tu-proyecto/tools/

# Copiar configuracion de Qodo
cp -r .qodo/ /ruta/a/tu-proyecto/.qodo/
```

## Contribuir

1. Crea una rama desde `main`
2. Agrega o modifica el skill/agente/workflow en la carpeta correspondiente
3. Documenta su proposito y como usarlo
4. Abre un PR para revision

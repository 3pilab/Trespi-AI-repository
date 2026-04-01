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
.qodo/
  agents/           # Agentes para Qodo
  workflows/        # Workflows para Qodo
```

## Uso

Para usar un skill o agente en otro proyecto, copia la carpeta correspondiente en la misma ruta dentro de tu repositorio. Por ejemplo:

```bash
# Copiar un skill de Claude Code
cp -r .agents/skills/commits /ruta/a/tu-proyecto/.agents/skills/

# Copiar configuracion de Qodo
cp -r .qodo/ /ruta/a/tu-proyecto/.qodo/
```

## Contribuir

1. Crea una rama desde `main`
2. Agrega o modifica el skill/agente/workflow en la carpeta correspondiente
3. Documenta su proposito y como usarlo
4. Abre un PR para revision

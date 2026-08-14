## 2026-08-14 14:35 — Integración del sistema multiagente en la arquitectura del monorepo

### Objetivo
Adaptar el sistema Python DQN + Clingo + simulación microscópica al monorepo existente, respetando la separación React / NestJS / IA / simulación definida en `AGENTS.md`, y dejar la aplicación preparada para ejecutar topología, simulación, entrenamiento y evaluación desde el backend y el frontend.

### Archivos modificados
- `README.md`
- `.gitignore`
- `package.json`
- `Makefile`
- `backend/.env.example`
- `backend/package.json`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `backend/src/app.module.js`
- `backend/src/controllers/traffic.controller.js`
- `backend/src/services/python-process.service.js`
- `backend/src/services/traffic-job.service.js`
- `backend/src/services/traffic-control.service.js`
- `backend/src/dtos/traffic-request.dto.js`
- `backend/src/common/domain_models.py`
- `backend/src/config/scenario_loader.py`
- `backend/src/config/scenarios/example_network.yaml`
- `backend/src/ia/clingo/*`
- `backend/src/ia/modelos/*`
- `backend/src/ia/entrenamiento/*`
- `backend/src/ia/scripts/*`
- `backend/src/simulacion/trafico/*`
- `backend/src/simulacion/vehiculos/*`
- `backend/src/simulacion/buses/*`
- `backend/src/simulacion/paraderos/*`
- `backend/src/simulacion/rutas/*`
- `backend/src/simulacion/telemetria/*`
- `backend/src/simulacion/metricas/*`
- `backend/src/simulacion/percepcion/*`
- `backend/src/simulacion/comunicacion/*`
- `backend/src/simulacion/recompensas/*`
- `backend/src/tests/*`
- `frontend/src/App.jsx`
- `frontend/src/pages/TrafficDashboard.jsx`
- `frontend/src/components/TrafficControls.jsx`
- `frontend/src/components/MetricsPanel.jsx`
- `frontend/src/components/TopologyPanel.jsx`
- `frontend/src/services/trafficControlService.js`
- `frontend/src/hooks/useTrafficJob.js`
- `frontend/src/visualization/NetworkVisualization.jsx`
- `frontend/src/styles.css`
- `docs/ARCHITECTURE.md`
- `docs/REQUIREMENTS_TRACEABILITY.md`
- `docs/PROMPT_MAESTRO.md`

### Cambios
- Reubicado el núcleo Clingo en `backend/src/ia/clingo` y conservada la derivación formal de movimientos, conflictos y fases legales.
- Reubicados DQN, replay buffer, action masking, estado y grupo de agentes en `backend/src/ia/modelos`.
- Reubicados entrenamiento y evaluación en `backend/src/ia/entrenamiento`.
- Distribuida la simulación entre tráfico, vehículos, buses, paraderos, rutas, percepción, comunicación, recompensas, métricas y telemetría.
- Extraída la gestión de dwell de paraderos desde `TrafficNetwork` hacia `StopManager`.
- Reemplazada la visualización Python/Matplotlib por un snapshot JSON y una visualización SVG en React, conforme a la responsabilidad asignada al frontend.
- Implementado contrato JSON `stdin/stdout` mediante `backend/src/ia/scripts/bridge.py`; logs Python quedan en `stderr`.
- Implementado `PythonProcessService` con `spawn()`, allowlist de operaciones, timeout y límite de salida.
- Implementados jobs en memoria para simulación, entrenamiento y evaluación, evitando mantener solicitudes HTTP abiertas.
- Implementados endpoints NestJS para escenarios, topología, simulación, entrenamiento, evaluación, estado de jobs y resultados.
- Implementado dashboard React para lanzar operaciones, seguir jobs, ver red, fases Clingo y métricas de bunching/headway.
- Añadida configuración de escenario de ejemplo, dependencias Python, tests y documentación de trazabilidad.
- Excluidos checkpoints, entornos virtuales y caches Python del control de versiones.

### Validaciones ejecutadas
- `PYTHONPATH=src python3 -m compileall -q src/ia src/simulacion src/config src/common` — correcto.
- `PYTHONPATH=src python3 -m pytest -q` — 14 tests aprobados, 1 omitido por ausencia de `clingo` en el sandbox.
- Smoke test JSON: `python3 src/ia/scripts/bridge.py scenarios` — respuesta estructurada válida y `stderr` vacío.
- `node --check` sobre los nuevos archivos JavaScript de backend — correcto.
- `npm install --ignore-scripts --no-audit --no-fund` — no completado en el sandbox por timeout/sin acceso efectivo al registro; por ello no fue posible ejecutar `npm run build --workspace=frontend` aquí.

### Decisiones técnicas
- Se mantuvo a Clingo como única fuente formal de legalidad; el DQN solo selecciona índices de fases válidas.
- No se trasladó el renderer Matplotlib al backend porque `AGENTS.md` asigna visualización exclusivamente a React; se conservó la capacidad mediante telemetría JSON + SVG frontend.
- Los nombres de escenarios y `runId` se validan y las rutas se resuelven dentro de directorios conocidos para impedir ejecución o escritura arbitraria.
- Los checkpoints se guardan bajo `backend/outputs/model_runs/<runId>` y no se versionan.

### Pendientes
- Ejecutar `npm install` y `npm run build --workspace=frontend` en un entorno con acceso al registro npm.
- Ejecutar el test de integración Clingo en un entorno donde `clingo` esté instalado mediante `backend/requirements.txt`.

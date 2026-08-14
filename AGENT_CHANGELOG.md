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

## 2026-08-14 — Demo visual de dos cruces + simulación DQN continua

### Objetivo
Convertir la interfaz en una demostración clara de dos intersecciones de cuatro vías conectadas, permitiendo cargar reglas Clingo, definir cuánto entrenar y observar indefinidamente las decisiones de un checkpoint DQN sobre tráfico microscópico.

### Cambios principales
- Rediseñado `example_network.yaml` como dos cruces de cuatro vías unidos por una avenida principal, con dos carriles entrantes por aproximación (izquierda exclusiva + recto/derecha), dos recorridos de bus opuestos y paraderos en ambos sentidos.
- Añadida carga opcional de archivos `.lp` desde React. Las reglas se agregan al núcleo `rules.lp`; se limitan a 200 KB y se bloquean `#script` y `#include` para impedir ejecución de código embebido o lectura arbitraria de archivos.
- `ClingoTopologyEngine` acepta reglas ASP adicionales manteniendo la derivación de movimientos, conflictos y fases seguras.
- Añadida telemetría de cuatro cabezales por intersección (`north/east/south/west`) con estado `RED`, `YELLOW` o `GREEN`, fase solicitada por DQN, fase activa, movimientos y componentes de recompensa.
- Añadido `live_simulation.py`: carga un checkpoint DQN y genera decisiones/frames continuamente. Al completar un ciclo de tráfico, reinicia con una nueva semilla y continúa hasta recibir `SIGTERM`.
- Añadido `TrafficLiveService` en NestJS y endpoints para iniciar, consultar y detener sesiones de simulación viva.
- Extendido `PythonProcessService` para mantener un proceso Python streaming mediante NDJSON sin usar shell ni comandos arbitrarios.
- Simplificado el frontend a tres pasos: Clingo → entrenamiento → simulación continua.
- Rediseñada la visualización SVG: calzada de cuatro carriles (dos por sentido), separadores de pista, vehículos orientados, buses diferenciados por recorrido/estado, paraderos, movimientos activos y ocho cabezales semafóricos de tres luces claramente visibles.
- Añadido panel en vivo que muestra la fase solicitada por cada DQN y el historial inmediato de decisiones.

### Validaciones
- `PYTHONPATH=src python3 -m pytest -q`: 14 aprobados, 1 omitido por falta de Clingo en el sandbox.
- `python3 -m compileall`: correcto.
- `node --check` en servicios/controladores/DTO del backend: correcto.
- Parseo de todos los `.js/.jsx` de `frontend/src` mediante el parser JSX de TypeScript: correcto.

### Nota de operación
La sesión continua no reproduce un video pregrabado: mantiene un proceso Python ejecutando el checkpoint. Cada ciclo usa una semilla diferente y el proceso permanece activo hasta que el usuario pulsa “Detener simulación”.

## 2026-08-14 — Streaming SSE y simulación microscópica en tiempo real

### Objetivo
Hacer que la demo live represente el avance microscópico real de la simulación, sin polling ni saltos visuales de 5 segundos.

### Cambios principales
- Separado el intervalo de decisión DQN (`5 s`) del paso microscópico (`dt=0,2 s`) en `MultiAgentTrafficEnv` mediante `begin_decision`, `advance_micro_step` y `finish_decision`.
- `live_simulation.py` transmite un frame por cada micro-paso de `0,2 s`; a `1×`, el reloj se sincroniza con `time.monotonic()` para que 1 segundo simulado sea aproximadamente 1 segundo real.
- El DQN continúa tomando una acción solo cada 5 segundos simulados, manteniendo coherencia con el entrenamiento.
- Sustituido el polling HTTP del frontend por **Server-Sent Events (SSE)** mediante `GET /api/traffic/live/:sessionId/stream`.
- `TrafficLiveService` mantiene suscriptores por sesión y publica ciclos, decisiones y frames apenas llegan desde Python.
- React consume el stream mediante `EventSource`, actualizando autos, buses, semáforos, métricas y decisiones sin esperar a una consulta periódica.
- Añadidos indicadores visibles de conexión SSE, número de frame, decisión DQN, `dt`, factor temporal y estado de tiempo real.
- El selector de velocidad ahora representa escala temporal (`0,5×`, `1×`, `2×`, `4×`) y no un retardo arbitrario entre decisiones.

### Validaciones
- `PYTHONPATH=src pytest -q`: 17 aprobados, 1 omitido únicamente por ausencia de `clingo` en el sandbox.
- `python3 -m py_compile` / `compileall`: correcto.
- `node --check` en servicios/controladores/DTO actualizados: correcto.
- El `npm install` del sandbox no pudo completarse por timeout del registro; no se agregaron dependencias Node nuevas.

## 2026-08-14 — Fix definitivo de animación en tiempo real

- Corregido `useLiveSimulation`: bajo React `StrictMode` el cleanup de verificación dejaba `mounted.current=false`, por lo que el navegador descartaba todos los frames SSE aunque NestJS/Python siguieran funcionando.
- El hook ahora reactiva el estado montado en cada setup y procesa los frames SSE normalmente.
- Añadido fallback automático de snapshots reales cada 250 ms si SSE no entrega eventos durante 900 ms.
- El endpoint SSE fuerza `setNoDelay`, `flush()` y `retry: 750` para reducir buffering en desarrollo/proxies.
- El escenario demo crea tráfico desde el primer micro-paso (`spawn_immediately`) y ambos recorridos B1/B2 parten en `t=0`.
- Los tiempos semafóricos de demo permiten observar transiciones en pocos segundos manteniendo mínimo verde, amarillo obligatorio y máximo de rojo.
- Agregadas pruebas que verifican movimiento real de autos/buses entre micro-pasos y transición visible GREEN → YELLOW → RED/GREEN por rama.

## 2026-08-14 — Reglas físicas de tránsito, línea de detención y no solapamiento

### Objetivo
Asegurar que la simulación en tiempo real represente colas y cruces físicamente coherentes: los vehículos deben detenerse antes de la caja de la intersección, obedecer rojo/amarillo, mantener distancia y no bloquear ni solaparse dentro del cruce.

### Cambios principales
- `position_m` se trata explícitamente como la posición del parachoques delantero.
- Añadida línea de detención física antes del cuadrado de cada intersección (`stop_line_clearance_m`).
- Rojo y amarillo impiden nuevas entradas; un vehículo que entró legalmente con verde conserva derecho a despejar la caja.
- Añadida ocupación de intersección por movimiento: movimientos Clingo conflictivos nunca ocupan simultáneamente la caja; como fail-safe, sin lógica Clingo disponible se permite una sola trayectoria dentro del cruce.
- Añadida regla "no bloquear la caja": un vehículo solo entra si existe espacio suficiente en el link de salida para abandonar completamente la intersección.
- El flujo de capacidad se aplica al cruce de la línea de detención, no al centro de la intersección.
- Añadida separación mínima absoluta por carril además del frenado Gipps, como protección frente a errores de integración discreta.
- Autos y buses solo se generan cuando existe espacio en el carril de origen; si no, permanecen esperando fuera de la red.
- La asignación de carril ahora proviene del movimiento real (`left` o `through/right`) y se transmite en telemetría; React dejó de elegir carriles mediante hash visual.
- El SVG dibuja líneas de detención blancas y los cuerpos de vehículos quedan anclados por su frente, haciendo visible que se detienen antes del cuadrado.

### Parámetros de escenario
- `minimum_vehicle_gap_m: 2.5`
- `stop_line_clearance_m: 4.0`
- `intersection_exit_clearance_m: 1.0`

### Validaciones
- `PYTHONPATH=src python3 -m pytest -q`: 23 aprobados, 1 omitido únicamente por ausencia de `clingo` en el sandbox.
- Prueba de estrés de 1200 micro-pasos con tráfico acumulado: distancia mínima observada 2,5 m, 0 solapamientos tanto con paso bloqueado como habilitado.
- Parseo JSX de `NetworkVisualization.jsx` mediante TypeScript: correcto.
- `python3 -m compileall -q src`: correcto.

## 2026-08-14 — Reconstrucción del motor basada en `Empresa.zip`

### Motivo
Las versiones previas separaban excesivamente el ciclo de simulación del ciclo visual y acumularon módulos alternativos que hacían difícil demostrar que el checkpoint entrenado controlaba exactamente la misma física mostrada en pantalla. Se reconstruyó el núcleo siguiendo el patrón funcional observado en el proyecto de referencia entregado por el equipo.

### Decisión arquitectónica principal
- Existe un único `MultiAgentTrafficEnv` para entrenamiento, evaluación, baseline y live.
- `env.step(actions, on_substep)` ejecuta 25 subpasos físicos de 0,2 s por cada decisión de 5 s.
- El callback se ejecuta sobre el estado real después de cada subpaso; el renderer no posee simulación propia.
- `live_simulation.py` carga los mismos checkpoints producidos por `train.py` y usa el mismo `env.step()`.

### Cambios
- Reescrita la dinámica alrededor de `RoadLane`, Gipps, líneas de detención e `IntersectionTransit`.
- Reescrito `SignalController` tomando como modelo el ciclo verde mínimo → amarillo obligatorio → nueva fase.
- Reescritos DQN y `AgentGroup` con replay buffer, epsilon-greedy, target network, Huber, Adam, clipping y action masking.
- Simplificado el escenario estable a dos cruces de cuatro vías conectados y una pista por sentido; el escenario actual usa movimientos rectos para validar el ciclo completo antes de escalar geometría.
- Buses B1/B2 despachados sobre el mismo motor de carriles, con paraderos, dwell y headway.
- Reescrita telemetría: Python entrega coordenadas y orientación de vehículos/cabezales; React Canvas solo dibuja.
- Eliminados módulos heredados no utilizados (`TrafficNetwork` anterior, state encoder/replay alternativos y servicios viejos de headway/reward/stop/GPS) para impedir que coexistieran dos motores distintos.
- Reescrita documentación para reflejar el flujo real.

### Validaciones realizadas
- `python3 -m compileall -q src`: correcto.
- `pytest -q`: 9 aprobados y 1 omitido únicamente cuando `clingo` no está disponible en el entorno de validación.
- Prueba de microframes: 25 callbacks por decisión, tiempos 0,2 ... 5,0 s y posiciones diferentes entre frames.
- Prueba de semáforos: transición GREEN → YELLOW → nueva fase GREEN.
- Prueba de tráfico: stop line en rojo, separación mínima y exclusión de tránsitos conflictivos.
- Prueba de buses: segundo despacho y cálculo de headway.
- Prueba DQN: replay efectivo, loss no nulo, guardado de `i1.pt`/`i2.pt` y carga posterior para inferencia.
- `node --check` en backend: correcto.
- Parseo JSX del frontend: correcto.

### Limitación de validación del sandbox
No se pudo ejecutar el solve real de Clingo ni un build Vite completo si las dependencias no estaban disponibles localmente en el sandbox. El test de contrato ASP permanece preparado para ejecutarse cuando `clingo` esté instalado desde `backend/requirements.txt`.

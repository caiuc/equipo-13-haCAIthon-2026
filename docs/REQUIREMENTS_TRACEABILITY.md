# Trazabilidad — reconstrucción funcional

| Requisito | Implementación actual |
|---|---|
| Clingo como fuente formal de fases legales | `backend/src/ia/clingo/asp_engine.py`, `rules.lp` |
| Topología por configuración | `backend/src/config/scenario_loader.py`, `config/scenarios/example_network.yaml` |
| DQN no controla luces individuales | `ia/modelos/dqn.py` + `SignalController` |
| Action masking | `SignalController.legal_action_mask()` + `DQNAgent.select_action()` |
| Verde mínimo / amarillo obligatorio / rojo máximo | `simulacion/trafico/signal_controller.py` |
| Paso microscópico de 0,2 s | `MultiAgentTrafficEnv.dt_s` |
| Decisión cada 5 s | `MultiAgentTrafficEnv.decision_interval_s` |
| 25 subpasos físicos por decisión | `MultiAgentTrafficEnv.step()` |
| Entrenamiento y live usan el mismo entorno | `train.py`, `live_simulation.py`, ambos con `MultiAgentTrafficEnv` |
| Gipps | `simulacion/vehiculos/gipps.py` |
| Línea de detención en rojo | `MultiAgentTrafficEnv` + `gipps.update_vehicle()` |
| No solapamiento por carril | orden/limitación en `RoadLane` + invariant tests |
| Cruce físico progresivo | `IntersectionTransit` en `common/domain_models.py` y `MultiAgentTrafficEnv` |
| Exclusión de movimientos conflictivos | `IntersectionLogic.conflicts` + control de entrada a caja |
| No bloquear salida | comprobación de espacio en `RoadLane.can_accept_from_intersection()` |
| Generación estocástica de autos | `MultiAgentTrafficEnv` |
| Rutas | `simulacion/rutas/route_planner.py` |
| BUS como clase separada | `common/domain_models.py` |
| Buses B1/B2, headway, dwell | `MultiAgentTrafficEnv` + escenario YAML |
| Cámara ROI | `simulacion/percepcion/camera.py` |
| Información de vecinos | resumen incorporado en `MultiAgentTrafficEnv._observation()` |
| Estado fijo por agente | `MultiAgentTrafficEnv.observation()` |
| DQN 128×128 + ReLU | `ia/modelos/dqn.py` |
| Replay / epsilon / target / Huber / Adam / clipping | `ia/modelos/dqn.py` |
| Agente por intersección | `ia/modelos/agent_group.py` |
| Recompensa bus-first | `MultiAgentTrafficEnv._rewards()` + pesos YAML |
| Checkpoints recargables | `DQNAgent.save/load`, `AgentGroup.save/load` |
| Frame real después de cada subpaso | `env.step(..., on_substep=...)` |
| Streaming real | `ia/scripts/live_simulation.py` → NestJS SSE → React |
| Frontend sin física | `frontend/src/visualization/NetworkVisualization.jsx` |
| Cuatro cabezales por cruce | `telemetria/snapshot.py` + Canvas |
| JSON Node ↔ Python | `ia/scripts/bridge.py` |
| Procesos Python centralizados | `backend/src/services/python-process.service.js` |
| Entrenamientos como jobs | `backend/src/services/traffic-job.service.js` |

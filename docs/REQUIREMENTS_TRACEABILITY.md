# Trazabilidad del prompt maestro

| Requisito | Implementación principal |
|---|---|
| Clingo como fuente formal de legalidad | `backend/src/ia/clingo/rules.lp`, `asp_engine.py` |
| Topología N-intersecciones paramétrica | `backend/src/config/scenario_loader.py`, escenarios YAML, `ia/clingo/geometry.py` |
| Movimientos desde carriles y giros | `lane_allows + turn_target -> movement` en ASP |
| Conflictos no hardcodeados por cruce | `occupies(...,zone)` + regla ASP `conflict` |
| Mínimo de fases legales | coloración ASP + `#minimize` |
| Sin control directo de luces por RL | DQN elige índice de `Phase` |
| Mínimo verde, amarillo, rojo máximo | `simulacion/trafico/signal_controller.py` |
| Action masking | `SignalController.action_mask`, `ia/modelos/dqn.py` |
| Peatones fuera de percepción RL | sin features peatonales; mínimo fijo en señales |
| Microsimulación Gipps | `simulacion/vehiculos/gipps.py`, `simulacion/trafico/network.py` |
| Poisson por origen | `TrafficNetwork._car_next_spawn` por origen |
| Ruta completa por vehículo | `simulacion/rutas/route_planner.py`, `Vehicle.route_links` |
| Rutas físicamente posibles | `RoutePlanner.is_legal_link_route` contra movimientos Clingo |
| Clase BUS separada | `common/domain_models.py` |
| GPS bus | `simulacion/percepcion/gps.py` |
| Paraderos y dwell uniforme | `simulacion/paraderos/stop_manager.py` |
| Headway continuo y tendencia | `simulacion/buses/headway.py` |
| Penalización progresiva bunching | `HeadwayTracker.progressive_penalty` |
| Prioridad/retención aprendible | estado + recompensa + selección de fases |
| Cámara ROI 60 m | `simulacion/percepcion/camera.py` |
| Comunicación entre vecinos | `simulacion/comunicacion/message_bus.py`, `NeighborMessage` |
| DQN 128x128/ReLU | `ia/modelos/dqn.py`, YAML |
| replay/epsilon/target/Huber/Adam/clipping | `ia/modelos/dqn.py`, `replay_buffer.py` |
| Agentes independientes | `ia/modelos/agent_group.py` modo `independent` |
| Parámetros compartidos | `ia/modelos/agent_group.py` modo `shared` |
| Recompensa bus-first | `simulacion/recompensas/reward_calculator.py`, pesos YAML |
| Vista global | `frontend/src/visualization/NetworkVisualization.jsx` |
| Telemetría y métricas | `simulacion/telemetria`, `simulacion/metricas` |
| Procesos largos como jobs | `backend/src/services/traffic-job.service.js` |
| Ejecución segura Python | `backend/src/services/python-process.service.js` |
| JSON Node ↔ Python | `backend/src/ia/scripts/bridge.py` |
| Cambiar topología sin reescribir agente | YAML + reejecución de Clingo |

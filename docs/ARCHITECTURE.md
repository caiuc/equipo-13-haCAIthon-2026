# Arquitectura — versión basada en el entorno de referencia

## Principio rector

La simulación posee una sola fuente de verdad: `MultiAgentTrafficEnv`.

El mismo objeto conceptual se usa en:

- entrenamiento;
- evaluación;
- baseline;
- simulación live.

El renderer no modifica el estado y no contiene física.

## Flujo general

```text
React
  ↓ HTTP
NestJS
  ↓ spawn
bridge.py / live_simulation.py
  ↓
ScenarioLoader
  ↓
ClingoTopologyEngine
  ↓
IntersectionLogic[]
  ↓
MultiAgentTrafficEnv
  ├─ RoadLane
  ├─ Gipps
  ├─ SignalController
  ├─ buses/paraderos/headway
  ├─ cámaras
  ├─ vecinos
  └─ reward
  ↓
AgentGroup
  └─ DQNAgent por intersección
```

## Reloj de simulación

Parámetros por defecto:

```text
physical dt        = 0,2 s
decision interval  = 5,0 s
substeps/decision  = 25
```

`MultiAgentTrafficEnv.step(actions, on_substep)` ejecuta exactamente esos 25 subpasos.

Pseudo-flujo:

```python
for substep in range(25):
    if substep == 0:
        signal_controller.request(action)

    signal_controller.step(0.2)
    update_vehicles_gipps(0.2)
    update_intersection_transits(0.2)
    update_buses_and_stops(0.2)
    update_perception(0.2)

    on_substep(env)
```

Esto replica deliberadamente el patrón del proyecto de referencia proporcionado por el equipo.

## Entrenamiento

`backend/src/ia/entrenamiento/train.py`:

1. crea `MultiAgentTrafficEnv`;
2. crea un `DQNAgent` por intersección;
3. obtiene observaciones;
4. solicita una acción enmascarada;
5. llama `env.step(actions)`;
6. almacena transición;
7. ejecuta replay/optimización;
8. actualiza target network;
9. guarda checkpoints.

No existe un `TrainingEnvironment` alternativo.

## Simulación live

`backend/src/ia/scripts/live_simulation.py`:

1. crea el mismo `MultiAgentTrafficEnv`;
2. carga los checkpoints `i1.pt`, `i2.pt`, ...;
3. selecciona acciones greedy;
4. llama `env.step(actions, on_substep=emit_frame)`;
5. serializa el estado real cada 0,2 s;
6. duerme solo lo necesario para sincronizar el ritmo visual;
7. repite hasta `SIGTERM`.

NestJS no interpola física. Solo retransmite NDJSON → SSE.

## Visualización

`frontend/src/visualization/NetworkVisualization.jsx` dibuja en Canvas.

Datos de posición enviados por Python:

```text
vehicle.x
vehicle.y
vehicle.headingDeg
vehicle.lengthM
vehicle.widthM
```

Los cabezales semafóricos enviados por Python incluyen:

```text
branch
x
y
headingDeg
color
```

Canvas puede interpolar visualmente entre dos frames verdaderos para suavizar movimiento, pero no cambia velocidad, carril, semáforo ni decisiones.

## Topología y Clingo

`backend/src/ia/clingo/asp_engine.py` transforma el escenario en hechos ASP y ejecuta `rules.lp`.

Clingo produce para cada intersección:

- movimientos;
- conflictos;
- fases.

`SignalController` recibe `IntersectionLogic` y solo permite índices de esas fases.

La red neuronal no enciende luces directamente.

## Control semafórico

`SignalController` posee dos responsabilidades:

1. traducir una solicitud de fase a una transición temporal segura;
2. generar el action mask válido.

Estados visibles:

```text
GREEN
YELLOW
```

En `YELLOW`, ninguna nueva aproximación recibe verde. Al terminar el amarillo se activa la fase pendiente.

## Física

`backend/src/simulacion/vehiculos/gipps.py` contiene la dinámica longitudinal.

Una línea de detención en rojo/amarillo se entrega a Gipps como una restricción de parada. Así la cola se forma mediante la misma dinámica utilizada para seguir a otro vehículo.

`RoadLane` mantiene orden longitudinal y espacio de generación/salida.

Los vehículos que cruzan una intersección pasan temporalmente a `IntersectionTransit`; no son teletransportados entre links.

## Estado del agente

Cada agente recibe un vector de tamaño fijo para el escenario actual:

- cámaras de sus cuatro aproximaciones;
- resumen GPS de buses;
- resumen de una intersección vecina.

El frontend nunca construye ese vector.

## DQN

`backend/src/ia/modelos/dqn.py`:

```text
input
 ↓
Linear(128) + ReLU
 ↓
Linear(128) + ReLU
 ↓
Q(action_0 ... action_n)
```

Incluye:

- replay buffer;
- epsilon-greedy;
- target network;
- Huber;
- Adam;
- gradient clipping;
- action masking.

`AgentGroup` mantiene un agente independiente por intersección para evitar asumir que todas tienen el mismo espacio de acciones.

## Seguridad de intersección

Antes de permitir una nueva entrada se verifican dos niveles:

1. el movimiento pertenece a la fase verde autorizada por Clingo;
2. no existe un `IntersectionTransit` conflictivo todavía ocupando la caja.

Además se exige espacio en el link de salida.

## Carpetas relevantes

```text
backend/src/ia/clingo/               ASP y solver
backend/src/ia/modelos/              DQN + AgentGroup
backend/src/ia/entrenamiento/        train/evaluate
backend/src/ia/scripts/              bridge/live
backend/src/simulacion/trafico/      Environment + lanes + signals
backend/src/simulacion/vehiculos/    Gipps
backend/src/simulacion/percepcion/   cámaras
backend/src/simulacion/rutas/        RoutePlanner
backend/src/simulacion/metricas/     métricas
backend/src/simulacion/telemetria/   DTO visual
frontend/src/visualization/          Canvas sin física
```

## Alcance del escenario estable actual

El escenario de demo usa dos cruces conectados y una pista por sentido con movimientos rectos. Esta simplificación es **del archivo de escenario**, no del ciclo temporal ni del DQN.

La prioridad de esta reconstrucción es que las invariantes físicas, el entrenamiento y la reproducción live sean verificables antes de aumentar la complejidad geométrica.

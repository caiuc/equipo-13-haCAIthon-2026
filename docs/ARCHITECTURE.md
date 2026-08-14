# Arquitectura técnica integrada

La implementación respeta la arquitectura definida por `AGENTS.md`: React visualiza, NestJS orquesta y Python concentra simulación, razonamiento lógico y aprendizaje reforzado.

## Flujo de datos

```text
React / Vite
   ↓ HTTP JSON
NestJS Controller
   ↓
TrafficControlService
   ↓
TrafficJobService (procesos largos)
   ↓
PythonProcessService / spawn()
   ↓ JSON stdin/stdout
backend/src/ia/scripts/bridge.py
   ↓
Configuración YAML
   ↓
Geometry preprocessor → turn_target + occupies(zone)
   ↓
Clingo / ASP
   ├─ movement(...)
   ├─ conflict(...)
   ├─ in_phase(...)
   └─ signal(...)
   ↓
SignalController
   ├─ mínimo verde / mínimo peatonal fijo
   ├─ amarillo obligatorio
   ├─ rojo máximo
   └─ comprobación de seguridad en runtime
   ↓
TrafficNetwork (dt configurable, 0.2 s por defecto)
   ├─ Gipps
   ├─ generación Poisson
   ├─ capacidad por movimiento
   ├─ buses y paraderos
   └─ rutas completas restringidas a movimientos legales
   ↓
Cámara ROI + GPS buses + mensajes de vecinos
   ↓
StateEncoder
   ↓
DQN independiente o compartido
   ↓
action masking
   ↓
índice de fase legal
   ↓
recompensa + replay buffer + target network
   ↓
métricas + snapshot JSON
   ↓
NestJS
   ↓
React/SVG
```

## Límites por carpeta

- `backend/src/ia/clingo`: legalidad topológica y semafórica.
- `backend/src/ia/modelos`: DQN, replay buffer, grupo de agentes y codificación de estado.
- `backend/src/ia/entrenamiento`: entrenamiento y evaluación.
- `backend/src/ia/scripts`: adaptadores ejecutables por NestJS.
- `backend/src/simulacion/trafico`: entorno multiagente, red y controlador temporal.
- `backend/src/simulacion/vehiculos`: dinámica de Gipps.
- `backend/src/simulacion/buses`: headway, tendencia y clasificación operacional.
- `backend/src/simulacion/paraderos`: dwell estocástico.
- `backend/src/simulacion/rutas`: planificación de rutas.
- `backend/src/simulacion/percepcion`: cámara y GPS.
- `backend/src/simulacion/comunicacion`: mensajes entre intersecciones.
- `backend/src/simulacion/recompensas`: recompensa bus-first.
- `backend/src/simulacion/metricas`: agregación de KPI.
- `backend/src/simulacion/telemetria`: DTOs de topología y estado para el frontend.
- `frontend/src/visualization`: representación SVG; no contiene lógica científica.

## Invariante de seguridad

Una fase puede llegar a verde solamente si:

1. Clingo generó la fase a partir de movimientos derivados de infraestructura.
2. La fase no contiene conflictos derivados por ASP.
3. El action mask la habilita bajo las restricciones temporales.
4. `SignalController.request_phase()` vuelve a comprobar seguridad.
5. Toda transición incompatible pasa por amarillo obligatorio.

La red neuronal nunca controla luces individuales.

## Clingo y geometría

Python no enumera pares de conflicto específicos de una intersección. El preprocesador convierte geometría en hechos neutrales:

```text
occupies(intersection, lane, destination_branch, zone)
```

ASP deriva `conflict(...)` cuando movimientos legalmente existentes ocupan una zona incompatible y luego minimiza la cantidad de fases utilizadas.

## Modos multiagente

`rl.agent_architecture` admite:

- `independent`: DQN, replay buffer y target network por intersección.
- `shared`: una red compartida con padding de estados y máscaras de acción para topologías heterogéneas.

El escenario de ejemplo utiliza `independent`.

## Contrato NestJS ↔ Python

Entrada por `stdin`:

```json
{
  "operation": "simulate",
  "simulationId": "uuid",
  "parameters": {
    "scenario": "example_network.yaml",
    "seconds": 900
  }
}
```

Salida correcta por `stdout`:

```json
{
  "success": true,
  "data": {},
  "metadata": {}
}
```

Los logs se escriben a `stderr`. NestJS mantiene una allowlist de operaciones y usa `spawn()` con argumentos separados.

# Equipo 13 haCAIthon 2026 — Control semafórico multiagente

Sistema de simulación microscópica y control semafórico adaptativo orientado a transporte público, reconstruido usando como referencia técnica el patrón de ejecución del proyecto `Empresa.zip` proporcionado por el equipo.

La decisión principal de esta versión es simple: **existe un solo entorno de simulación**. Ese mismo entorno se usa para entrenar, evaluar y visualizar. React no calcula física y NestJS no reproduce una segunda simulación.

## Qué demuestra esta versión

El escenario incluido contiene **dos intersecciones de cuatro vías conectadas por una avenida**. Cada calle bidireccional tiene una pista por sentido, por lo que visualmente se observan las dos pistas de cada calzada.

Se muestran en tiempo real:

- autos;
- buses B1 y B2;
- cuatro cabezales semafóricos por intersección, ocho en total;
- rojo, amarillo y verde;
- líneas de detención;
- colas en rojo;
- movimientos dentro de la caja de conflicto;
- paraderos y detenciones de buses;
- fase solicitada por cada DQN;
- fase realmente aplicada por el controlador;
- recompensas, headway y métricas básicas.

La primera versión estable del escenario demo utiliza movimientos rectos. El motor de configuración y Clingo permanece separado del escenario para poder incorporar giros y más carriles posteriormente sin crear un segundo motor de simulación.

## Arquitectura temporal — el punto más importante

La simulación replica el patrón que funciona en el proyecto de referencia:

```text
DQN
 │
 │ una decisión cada 5 s simulados
 ▼
MultiAgentTrafficEnv.step(actions)
 │
 ├─ subpaso físico 0,2 s
 ├─ subpaso físico 0,2 s
 ├─ ...
 └─ 25 subpasos = 5 s
      │
      └─ on_substep(env) después de CADA subpaso
```

El `on_substep` recibe el estado del mismo entorno que está ejecutando Gipps, buses y semáforos. En live:

```text
Python on_substep
      ↓ NDJSON
NestJS
      ↓ SSE
React Canvas
```

React solamente dibuja las coordenadas, orientaciones y colores que Python entrega.

## Entrenamiento y simulación usan exactamente el mismo entorno

Entrenamiento:

```text
MultiAgentTrafficEnv
       ↓
DQN observa estado
       ↓
action mask
       ↓
DQN solicita fase
       ↓
env.step()
       ↓
recompensa
       ↓
Replay Buffer / Huber / Adam / Target Network
```

Simulación en vivo:

```text
MultiAgentTrafficEnv
       ↓
checkpoint DQN
       ↓
action mask
       ↓
DQN solicita fase
       ↓
env.step(on_substep=stream)
       ↓
SSE
       ↓
Canvas
```

No existe una física específica para el frontend.

## Semáforos

Cada intersección posee cuatro aproximaciones:

```text
N
E
S
O
```

Cada una se visualiza con un cabezal de tres luces. El DQN **no controla luces individuales**. Solo solicita un índice de fase generado por Clingo.

El controlador temporal aplica:

- verde mínimo;
- amarillo obligatorio antes de una fase incompatible;
- rojo;
- máximo de rojo;
- action masking.

Por ejemplo:

```text
DQN pide fase E/O
       ↓
fase N/S todavía verde si no cumplió mínimo
       ↓
amarillo N/S
       ↓
rojo N/S
       ↓
verde E/O
```

## Vehículos y leyes de tránsito

La posición de un vehículo representa su parachoques delantero.

El motor usa dinámica de Gipps y trata la línea de detención como un obstáculo cuando el movimiento no está habilitado. Esto permite que las colas se formen físicamente antes del cruce.

También se comprueba:

- separación mínima entre vehículos;
- no solapamiento por carril;
- no entrar con rojo;
- no iniciar entrada con amarillo;
- derecho a despejar la caja si ya se entró legalmente;
- exclusión de trayectorias conflictivas dentro de la caja;
- espacio de salida antes de autorizar una nueva entrada.

## Buses

Los buses son una clase distinta de los autos. El escenario incluye dos recorridos opuestos:

```text
B1  oeste → i1 → i2 → este
B2  este  → i2 → i1 → oeste
```

Se modelan:

- despacho por headway;
- paraderos;
- dwell estocástico;
- posición conocida tipo GPS;
- headway estimado;
- estados normal / adelantado / atrasado / riesgo / crítico;
- penalización de bunching en la recompensa.

## DQN

Cada intersección tiene su propio agente independiente.

Configuración base:

- MLP 128 → 128;
- ReLU;
- replay buffer;
- epsilon-greedy;
- target network;
- Huber Loss (`SmoothL1Loss`);
- Adam;
- gradient clipping;
- action masking.

Los checkpoints se guardan en:

```text
backend/outputs/model_runs/<run-id>/
├── i1.pt
├── i2.pt
├── agents.json
├── training_history.json
└── manifest.json
```

## Clingo

Clingo determina movimientos, conflictos y fases legales antes de construir el entorno.

El flujo de seguridad es:

```text
Escenario YAML
      ↓
Clingo
      ↓
fases legales
      ↓
action mask
      ↓
DQN
      ↓
SignalController
      ↓
simulación
```

Se puede agregar un `.lp` desde la interfaz. Por seguridad se bloquean `#script` y `#include` y se limita su tamaño.

## Flujo de la interfaz

La demo se centra en tres pasos:

1. **Validar Clingo**.
2. **Entrenar DQN** indicando episodios y segundos por episodio.
3. **Iniciar simulación en tiempo real** con el checkpoint generado.

La simulación live continúa hasta pulsar **Detener simulación**. Al completar un ciclo reinicia el tráfico con otra semilla, pero conserva el mismo checkpoint.

## Instalación

### Python

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cd ..
```

### Node

```bash
npm install
```

### Variables de entorno

```bash
cp backend/.env.example backend/.env
```

## Ejecutar

Mantén activo el entorno virtual Python y, desde la raíz:

```bash
npm run dev
```

Abre:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:3000
```

## Prueba rápida

Para comprobar el flujo completo:

```text
Episodios:             3
Segundos por episodio: 120
Ritmo live:            1×
```

Luego:

```text
Validar Clingo
     ↓
Entrenar DQN
     ↓
Iniciar simulación
```

Para una prueba de aprendizaje más representativa, aumenta episodios y duración.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Los tests cubren específicamente:

- 25 micro-subpasos de 0,2 s por decisión de 5 s;
- cambio de posición entre callbacks;
- buses presentes desde el inicio;
- línea de detención en rojo;
- no solapamiento;
- transición verde → amarillo → nueva fase verde;
- exclusión de movimientos conflictivos;
- despacho/headway de buses;
- entrenamiento DQN;
- checkpoint guardado y cargable;
- contrato JSON del bridge.

## API principal

```text
GET  /api/traffic/scenarios
POST /api/traffic/topology
POST /api/traffic/training
GET  /api/traffic/jobs/:jobId
GET  /api/traffic/jobs/:jobId/results

POST /api/traffic/live
GET  /api/traffic/live/:sessionId
GET  /api/traffic/live/:sessionId/stream
POST /api/traffic/live/:sessionId/stop
```

## Responsabilidades

```text
React        = interfaz + Canvas
NestJS       = API + jobs + procesos Python + SSE
Python       = física + buses + estado + recompensa + DQN
Clingo       = legalidad de movimientos/conflictos/fases
```

La regla de esta reconstrucción es que **ninguna de esas capas reimplemente el comportamiento de otra**.

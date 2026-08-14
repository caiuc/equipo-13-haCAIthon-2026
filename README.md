# Equipo 13 haCAIthon 2026 — Control semafórico multiagente

Monorepo para simulación y control semafórico adaptativo orientado prioritariamente a la regularidad del transporte público y prevención de **bus bunching**.

La solución integra:

- React + Vite para configuración, visualización y métricas.
- NestJS en JavaScript para API, validación, jobs y ejecución segura de Python.
- Python para simulación microscópica, percepción, comunicación, métricas y RL.
- Clingo/ASP como fuente formal de verdad para movimientos, conflictos y fases legales.
- DQN multiagente con replay buffer, target network, Huber loss, Adam, epsilon-greedy, gradient clipping y action masking.

## Estructura

```text
frontend/src/
├── components/
├── hooks/
├── pages/
├── services/
└── visualization/

backend/src/
├── ia/
│   ├── clingo/
│   ├── modelos/
│   ├── entrenamiento/
│   └── scripts/
├── simulacion/
│   ├── trafico/
│   ├── vehiculos/
│   ├── buses/
│   ├── paraderos/
│   ├── rutas/
│   ├── telemetria/
│   ├── metricas/
│   ├── percepcion/
│   ├── comunicacion/
│   └── recompensas/
├── config/
├── common/
├── dtos/
├── controllers/
├── services/
└── tests/
```

## Requisitos

- Node.js 20+
- npm 10+
- Python 3.11+ (Python 3.12 funciona)
- Clingo instalado mediante el paquete Python de `requirements.txt`

## 1. Instalar dependencias Python

En Ubuntu/Debian, desde la raíz del repositorio:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Validar:

```bash
python -m pytest -q
python -m compileall -q src/ia src/simulacion src/config src/common
```

## 2. Probar el núcleo Python directamente

Con el entorno virtual activo y estando en `backend/`:

```bash
PYTHONPATH=src python src/ia/scripts/dev_cli.py scenarios
PYTHONPATH=src python src/ia/scripts/dev_cli.py topology
PYTHONPATH=src python src/ia/scripts/dev_cli.py simulate --seconds 300
```

Entrenamiento corto:

```bash
PYTHONPATH=src python src/ia/scripts/dev_cli.py train \
  --episodes 10 \
  --seconds 600 \
  --run-id prueba-dqn
```

Evaluación del checkpoint:

```bash
PYTHONPATH=src python src/ia/scripts/dev_cli.py evaluate \
  --seconds 900 \
  --checkpoint-run-id prueba-dqn
```

Los modelos se almacenan bajo `backend/outputs/model_runs/<run-id>/` y están excluidos de Git.

## 3. Instalar frontend y backend NestJS

Desde la raíz:

```bash
npm install
```

Si tu sistema solo expone `python3`, no necesitas instalar `python-is-python3`: el backend usa `python3` por defecto.

Para personalizar variables:

```bash
cp backend/.env.example backend/.env
```

Las variables principales son:

```text
PORT
PYTHON_BIN
PYTHON_TIMEOUT_MS
PYTHON_TRAIN_TIMEOUT_MS
```

## 4. Levantar la aplicación

Desde la raíz:

```bash
npm run dev
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:3000`
- Health: `GET /api/health`

Vite proxifica `/api` al backend durante desarrollo.

## API de control semafórico

```text
GET  /api/traffic/scenarios
POST /api/traffic/topology
POST /api/traffic/simulations
POST /api/traffic/training
POST /api/traffic/evaluations
GET  /api/traffic/jobs/:jobId
GET  /api/traffic/jobs/:jobId/results
```

Simulación, entrenamiento y evaluación son trabajos. El POST devuelve un `jobId`; el frontend consulta su estado hasta `completed` o `failed`.

## Seguridad del control

El sistema mantiene una separación absoluta entre:

```text
lo que el DQN quiere hacer
```

y:

```text
lo que el sistema permite hacer
```

Clingo define movimientos/conflictos/fases legales. El controlador temporal aplica mínimo verde, amarillo y rojo máximo. El action masking elimina acciones no válidas antes de que el DQN seleccione una fase.

## Prioridad de optimización

1. Seguridad.
2. Prevención de bus bunching.
3. Regularidad del transporte público.
4. Tiempo de viaje de buses.
5. Espera de buses.
6. Flujo vehicular general.

Consulta `docs/ARCHITECTURE.md` y `docs/REQUIREMENTS_TRACEABILITY.md` para el detalle técnico.

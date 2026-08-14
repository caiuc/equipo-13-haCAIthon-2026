# Equipo 13 haCAIthon 2026 — Control semafórico multiagente

Demo de control semafórico adaptativo para **dos intersecciones de cuatro vías conectadas**, orientada prioritariamente a buses, regularidad de headway y prevención de **bus bunching**.

La aplicación integra React + Vite, NestJS, Python, Clingo/ASP y DQN multiagente.

## Flujo principal de la demo

La interfaz está pensada para funcionar en tres pasos:

1. **Clingo** — cargar opcionalmente un archivo `.lp` y validar movimientos, conflictos y fases legales.
2. **Entrenar DQN** — elegir cantidad de episodios y segundos simulados por episodio.
3. **Simulación DQN continua en tiempo real** — cargar automáticamente el checkpoint recién entrenado y observar decisiones, semáforos y vehículos hasta pulsar `Detener simulación`.

La simulación continua ejecuta Python realmente. El motor avanza con `dt=0,2 s`; a velocidad `1×`, cada micro-paso se sincroniza con el reloj real y se transmite inmediatamente al navegador mediante **Server-Sent Events (SSE)**. El DQN sigue tomando decisiones cada `5 s` simulados, igual que durante el entrenamiento. Al terminar cada ciclo de tráfico reinicia el entorno con una semilla diferente, mantiene el mismo checkpoint entrenado y continúa indefinidamente.

## Qué se visualiza

- Dos cruces de cuatro vías conectados por una avenida principal.
- Dos pistas por sentido.
- Cuatro cabezales semafóricos visibles por cruce (8 en total).
- Rojo, amarillo y verde de cada aproximación actualizados frame a frame; un amarillo de 3 s permanece visible durante aproximadamente 15 frames a `dt=0,2 s`.
- Fase solicitada por el DQN y fase actualmente aplicada.
- Transición amarilla obligatoria antes de cambiar a una fase incompatible.
- Autos y buses orientados en su sentido de circulación.
- Recorridos B1 y B2 en sentidos opuestos.
- Paraderos.
- Movimientos activos dentro del cruce.
- Headway, estado de buses, recompensas y últimas decisiones DQN.

## Seguridad al cargar Clingo

El archivo `.lp` seleccionado desde el navegador se **agrega** al núcleo `backend/src/ia/clingo/rules.lp`.

Se permiten reglas, hechos, restricciones y optimizaciones ASP normales. Por seguridad:

- máximo 200 KB;
- `#script` está bloqueado;
- `#include` está bloqueado.

Esto evita ejecutar código embebido o leer archivos arbitrarios del servidor.

Se incluye un ejemplo en:

```text
backend/src/ia/clingo/demo_two_crosses.lp
```

## Requisitos

- Node.js 20+
- npm 10+
- Python 3.11+

## Instalación Python

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cd ..
```

## Instalación Node

```bash
npm install
```

## Levantar aplicación

Desde la raíz, manteniendo el entorno virtual activo:

```bash
npm run dev
```

Luego abre:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:3000
```

## Prueba rápida recomendada

En la interfaz:

```text
Clingo:       rules.lp interno o demo_two_crosses.lp
Episodios:    3
Por episodio: 120 segundos
Ciclo live:   600 segundos
Ritmo:        1× · tiempo real
```

Flujo:

```text
Validar topología Clingo
        ↓
Entrenar DQN
        ↓
Iniciar simulación con el modelo entrenado
        ↓
Observar fases, rojo/amarillo/verde, autos y buses
        ↓
Detener simulación cuando quieras
```

Para un entrenamiento más representativo:

```text
10 episodios × 300 s   → demo
50 episodios × 900 s   → entrenamiento más serio
```

## API

```text
GET  /api/traffic/scenarios
POST /api/traffic/topology
POST /api/traffic/simulations
POST /api/traffic/training
POST /api/traffic/evaluations
GET  /api/traffic/jobs/:jobId
GET  /api/traffic/jobs/:jobId/results

POST /api/traffic/live
GET  /api/traffic/live/:sessionId
GET  /api/traffic/live/:sessionId/stream   # SSE en tiempo real
POST /api/traffic/live/:sessionId/stop
```

Los entrenamientos son jobs finitos. La simulación `live` mantiene un proceso Python activo hasta detenerlo.

## Separación de seguridad

```text
Clingo
  ↓
fases legalmente posibles
  ↓
action masking
  ↓
DQN selecciona fase
  ↓
controlador temporal
  ↓
verde mínimo / amarillo obligatorio / rojo máximo
  ↓
simulador microscópico
```

El DQN nunca produce directamente una combinación arbitraria de luces.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Los checkpoints se guardan en:

```text
backend/outputs/model_runs/<run-id>/
```

y están excluidos del repositorio mediante `.gitignore`.

### Simulación visual en tiempo real

Al pulsar **Iniciar simulación en tiempo real**, Python avanza el modelo microscópico cada `0.2 s` y NestJS transmite cada frame mediante SSE. React actualiza posiciones y cabezales semafóricos con cada frame. En desarrollo existe un respaldo automático que consulta el último snapshot real cada `250 ms` si el stream SSE queda sin eventos por más de `900 ms`.

El escenario de demostración inicia con tráfico visible desde el primer micro-paso: un auto por origen y un bus B1/B2 desde `t=0`. Los cambios de fase respetan mínimo verde, amarillo obligatorio y máximo de rojo, de modo que la secuencia de colores sea observable durante la demo.

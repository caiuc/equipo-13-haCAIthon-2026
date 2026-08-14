# AGENTS.md

## 1. Propósito

Este repositorio implementa una plataforma de simulación y control semafórico adaptativo orientada prioritariamente al transporte público.

El sistema busca controlar una red de `N` intersecciones mediante agentes de aprendizaje por refuerzo, manteniendo la regularidad de buses de un mismo recorrido, previniendo el **bus bunching** y reduciendo tiempos de viaje, sin deteriorar de forma desproporcionada el tráfico general.

La solución debe ser:

- modular;
- extensible;
- generalizable;
- reproducible;
- testeable;
- desacoplada entre frontend, backend, simulación e IA;
- segura respecto de las decisiones semafóricas.

No asumir cantidades fijas de:

- intersecciones;
- carriles;
- movimientos;
- fases;
- rutas;
- buses;
- paraderos.

La configuración de la red debe determinar el comportamiento del sistema, no código escrito específicamente para una intersección.

---

# 2. Arquitectura general

El repositorio es un monorepo compuesto principalmente por:

```text
/
├── frontend/
├── backend/
│   └── src/
│       ├── ia/
│       ├── simulacion/
│       ├── config/
│       ├── database/
│       ├── common/
│       ├── dtos/
│       └── tests/
├── AGENTS.md
└── AGENT_CHANGELOG.md
```

Cada área debe mantener claramente separada su responsabilidad.

---

# 3. Frontend

Tecnologías:

- React
- Vite
- JavaScript

Responsabilidad:

El frontend es exclusivamente responsable de:

- interfaz de usuario;
- configuración visual de escenarios;
- visualización de la red;
- visualización de vehículos y buses;
- visualización de semáforos;
- telemetría;
- métricas;
- gráficos;
- interacción con simulaciones;
- solicitudes al backend.

El frontend **no debe implementar lógica de simulación, DQN, Clingo ni reglas semafóricas**.

Estructura conceptual:

```text
frontend/src/
├── pages/
├── components/
├── services/
├── hooks/
├── context/
├── store/
└── visualization/
```

Las llamadas al backend deben centralizarse en `services/`.

Evitar realizar llamadas HTTP directamente desde componentes cuando puedan abstraerse mediante servicios o hooks.

---

# 4. Backend

Tecnología:

- NestJS
- JavaScript

El backend constituye la capa de:

- API;
- validación;
- orquestación;
- persistencia;
- ejecución de procesos Python;
- comunicación entre frontend, simulación e IA;
- manejo de errores;
- gestión de configuraciones;
- telemetría hacia el frontend.

El backend **no debe duplicar la lógica científica o algorítmica implementada en Python**.

El flujo esperado es:

```text
Frontend
   ↓
NestJS Controller
   ↓
Service
   ↓
Validación / configuración
   ↓
Python IA o Simulación
   ↓
Resultado estructurado
   ↓
NestJS
   ↓
Frontend
```

Los Controllers deben ser livianos.

Un Controller:

1. recibe la petición;
2. valida mediante DTO;
3. llama al Service correspondiente;
4. devuelve una respuesta.

No colocar lógica compleja en Controllers.

---

# 5. Ejecución de Python desde NestJS

El backend es responsable de ejecutar los procesos Python correspondientes a IA y simulación.

Preferir:

```text
child_process.spawn()
```

sobre:

```text
child_process.exec()
```

cuando se ejecuten scripts Python.

Esto permite:

- manejar stdout;
- manejar stderr;
- evitar construcción insegura de comandos;
- controlar argumentos;
- manejar procesos largos;
- detectar códigos de salida;
- implementar timeouts.

Nunca ejecutar comandos arbitrarios provenientes directamente del frontend.

Los scripts ejecutables deben pertenecer a una lista conocida de procesos permitidos.

Ejemplo conceptual:

```text
Backend
   ↓
PythonProcessService
   ↓
script permitido
   ↓
Python
```

Centralizar la ejecución de Python en un servicio específico.

No repetir lógica de `spawn()` en múltiples módulos.

---

# 6. Contrato Node.js ↔ Python

Toda comunicación entre NestJS y Python debe utilizar un contrato estructurado.

Formato preferente:

```text
JSON
```

Entrada:

```json
{
  "operation": "...",
  "simulationId": "...",
  "parameters": {}
}
```

Salida correcta:

```json
{
  "success": true,
  "data": {},
  "metadata": {}
}
```

Salida con error:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Descripción"
  }
}
```

### Regla importante

`stdout` debe reservarse para resultados estructurados destinados al backend.

Los mensajes de depuración Python deben escribirse mediante logging o `stderr`.

No mezclar:

```text
print("Entré aquí")
```

con una respuesta JSON que NestJS espera procesar.

---

# 7. Carpeta IA

```text
backend/src/ia/
├── clingo/
├── modelos/
├── entrenamiento/
└── scripts/
```

La carpeta `ia/` contiene exclusivamente aquello relacionado con inteligencia artificial y razonamiento lógico.

## `ia/clingo`

Responsable de:

- representación topológica;
- movimientos posibles;
- conflictos;
- fases semafóricas legales;
- restricciones de seguridad.

**Clingo constituye la fuente de verdad respecto de qué movimientos y fases son legales.**

Nunca duplicar manualmente estas reglas mediante grandes bloques de `if/else` en Python o JavaScript.

## `ia/modelos`

Contiene:

- modelos DQN;
- arquitectura de redes;
- agentes;
- replay buffer;
- action masking;
- utilidades directamente relacionadas con modelos.

## `ia/entrenamiento`

Contiene:

- entrenamiento;
- episodios;
- optimización;
- checkpoints;
- evaluación de modelos;
- reproducibilidad experimental.

## `ia/scripts`

Puntos de entrada ejecutables por NestJS.

Estos scripts deben actuar como adaptadores y no concentrar toda la lógica del sistema.

---

# 8. Simulación

```text
backend/src/simulacion/
├── trafico/
├── vehiculos/
├── buses/
├── paraderos/
├── rutas/
├── telemetria/
├── metricas/
├── percepcion/
├── comunicacion/
└── recompensas/
```

La simulación debe mantenerse independiente del frontend y del framework NestJS.

Idealmente debe poder ejecutarse directamente desde Python para:

- pruebas;
- entrenamiento;
- experimentación;
- debugging.

NestJS debe actuar como orquestador, no como dependencia interna del simulador.

---

# 9. Separación fundamental de responsabilidades

Mantener siempre esta separación:

```text
Clingo
    ↓
define qué es legal

Simulación
    ↓
define qué está ocurriendo

Percepción
    ↓
define qué puede observar el agente

DQN
    ↓
decide qué acción desea ejecutar

Action Masking
    ↓
elimina acciones no permitidas

Controlador semafórico
    ↓
ejecuta una transición segura

Backend
    ↓
orquesta y expone la información

Frontend
    ↓
visualiza e interactúa
```

El RL jamás debe controlar directamente luces individuales.

Debe seleccionar exclusivamente entre fases válidas.

---

# 10. Regla de seguridad

Existe una separación absoluta entre:

```text
lo que el agente quiere hacer
```

y:

```text
lo que el sistema permite hacer
```

Prioridad:

1. Seguridad.
2. Prevención del bus bunching.
3. Regularidad del transporte público.
4. Tiempo de viaje de buses.
5. Espera de buses.
6. Flujo vehicular general.

Una decisión de IA jamás puede violar una restricción de seguridad.

---

# 11. Buses y bus bunching

Los buses son una entidad distinta de los automóviles.

Cada bus debe poder mantener, cuando corresponda:

- ID;
- recorrido;
- posición;
- velocidad;
- dirección;
- ruta;
- próxima intersección;
- siguiente paradero;
- estado;
- headway;
- desviación del headway;
- relación con bus anterior;
- relación con bus siguiente.

El objetivo del sistema no consiste simplemente en hacer avanzar los buses lo más rápido posible.

Debe mantener regularidad.

Conceptualmente:

```text
headway normal
    → operación normal

headway disminuyendo
    → riesgo

headway cercano al límite
    → bunching inminente

headway crítico
    → bunching
```

El sistema debe poder:

- favorecer buses atrasados;
- reducir esperas de buses atrasados;
- retener moderadamente buses adelantados;
- anticipar situaciones de bunching;
- recuperar la regularidad.

---

# 12. Calidad del código

Todo código nuevo debe priorizar:

- claridad;
- simplicidad;
- cohesión;
- bajo acoplamiento;
- nombres descriptivos;
- funciones pequeñas;
- responsabilidades únicas;
- eliminación de duplicación;
- manejo explícito de errores.

Evitar funciones excesivamente extensas.

Evitar archivos que acumulen responsabilidades no relacionadas.

Evitar nombres ambiguos como:

```text
data
temp
thing
value2
func
processData
```

cuando exista un nombre de dominio más preciso.

---

# 13. Principios obligatorios

Aplicar cuando sea razonable:

- Single Responsibility Principle;
- DRY;
- KISS;
- separación de responsabilidades;
- inversión de dependencias cuando sea útil;
- composición antes que duplicación;
- configuración antes que hardcoding.

No introducir abstracciones innecesarias solo por aplicar patrones.

La arquitectura debe permanecer comprensible.

---

# 14. No hardcodear configuración del dominio

No introducir directamente en código valores que conceptualmente pertenecen a configuración.

Ejemplos:

```text
tiempos semafóricos
capacidades
headway objetivo
umbral de bunching
paso temporal
tasas de generación
duración de paraderos
rutas
topología
puertos
paths
seeds
```

Estos valores deben provenir, según corresponda, de:

- configuración;
- archivos de escenario;
- variables de entorno;
- parámetros;
- base de datos.

---

# 15. Validación antes de modificar código

Antes de realizar una intervención importante, el agente debe:

1. leer `AGENTS.md`;
2. identificar las carpetas afectadas;
3. leer el código relacionado;
4. comprender las dependencias existentes;
5. verificar que la implementación actual compile o ejecute;
6. evitar modificar archivos no relacionados con la tarea.

Nunca asumir el contenido de un archivo sin revisarlo.

Nunca reemplazar una implementación funcional completa únicamente porque resulte más sencillo rehacerla.

---

# 16. Verificación posterior obligatoria

Después de cualquier cambio, revisar como mínimo:

### JavaScript

- errores de sintaxis;
- imports;
- exports;
- rutas;
- dependencias;
- nombres de módulos;
- referencias inexistentes.

### React

Ejecutar cuando corresponda:

```bash
npm run build --workspace=frontend
```

### Backend

Verificar que NestJS pueda iniciar correctamente.

Cuando existan tests:

```bash
npm test
```

### Python

Verificar al menos:

```bash
python -m compileall <carpeta_modificada>
```

y ejecutar los tests correspondientes.

No declarar una tarea como terminada si quedaron errores conocidos provocados por la intervención.

---

# 17. Tests

Toda lógica crítica debe diseñarse de forma testeable.

Priorizar tests para:

- conflictos semafóricos;
- fases legales;
- action masking;
- cálculo de headway;
- detección de bunching;
- rutas;
- recompensas;
- comunicación entre agentes;
- conversión Node ↔ Python;
- validación de respuestas Python;
- métricas;
- endpoints importantes.

Un bug corregido debería incluir un test de regresión cuando sea razonable.

---

# 18. Reproducibilidad de IA y simulaciones

Los experimentos deben poder reproducirse.

Centralizar y registrar cuando corresponda:

- random seed de Python;
- NumPy seed;
- seed del framework de ML;
- seed del simulador;
- versión/configuración del escenario;
- parámetros del entrenamiento;
- versión del modelo.

No utilizar aleatoriedad oculta sin posibilidad de configurar la semilla.

---

# 19. Modelos entrenados

No tratar archivos de modelos entrenados como código fuente.

Los checkpoints deben estar separados del código.

Utilizar nombres/versiones identificables.

Ejemplo conceptual:

```text
model_dqn_v003/
```

Registrar junto al modelo:

- fecha;
- configuración;
- seed;
- escenario;
- métricas;
- versión del código cuando sea posible.

No sobrescribir silenciosamente modelos entrenados importantes.

---

# 20. Manejo de errores

Los errores deben propagarse de manera controlada.

Ejemplo:

```text
Python falla
    ↓
Backend captura stderr + exitCode
    ↓
Service transforma el error
    ↓
Controller entrega respuesta HTTP apropiada
    ↓
Frontend muestra error entendible
```

No ocultar errores con:

```javascript
catch (error) {
  return null;
}
```

sin una justificación explícita.

No usar `console.log` como único mecanismo permanente de observabilidad.

---

# 21. Logging de ejecución

Usar niveles de log:

```text
DEBUG
INFO
WARN
ERROR
```

Los logs relevantes deberían incluir contexto suficiente:

```text
simulationId
agentId
intersectionId
routeId
busId
operation
duration
```

Nunca registrar:

- passwords;
- tokens;
- secrets;
- credenciales;
- contenido sensible innecesario.

---

# 22. Registro obligatorio de intervenciones del agente

Toda intervención de un agente que modifique archivos debe agregar una entrada a:

```text
AGENT_CHANGELOG.md
```

Formato:

```markdown
## YYYY-MM-DD HH:mm — Descripción breve

### Objetivo
Descripción del objetivo solicitado.

### Archivos modificados
- `ruta/archivo1`
- `ruta/archivo2`

### Cambios
- Cambio realizado.
- Cambio realizado.

### Validaciones ejecutadas
- comando ejecutado
- resultado

### Decisiones técnicas
- Decisión relevante y motivo.

### Pendientes
- Ninguno.

o

- Descripción del pendiente.
```

No registrar cambios que no se hayan realizado realmente.

El historial es **append-only**: no borrar entradas anteriores salvo solicitud explícita.

---

# 23. Dependencias

Antes de instalar una nueva dependencia:

1. comprobar si realmente es necesaria;
2. verificar si la funcionalidad ya existe;
3. preferir librerías mantenidas;
4. evitar introducir paquetes grandes para problemas simples.

Cuando se agregue una dependencia:

- actualizar el archivo correspondiente;
- documentar el motivo en `AGENT_CHANGELOG.md`.

---

# 24. Variables de entorno

Credenciales y configuraciones propias del entorno deben utilizar variables de entorno.

Nunca commitear `.env` con secretos.

Mantener `.env.example` actualizado cuando se agreguen nuevas variables.

Ejemplos:

```text
PORT
DATABASE_URL
PYTHON_BIN
CLINGO_PATH
```

El código debe validar variables obligatorias al iniciar cuando corresponda.

---

# 25. Seguridad al ejecutar Python

Nunca construir comandos concatenando directamente parámetros enviados por el usuario.

Incorrecto:

```javascript
exec(`python ${req.body.script} ${req.body.argument}`)
```

Los scripts ejecutables deben estar definidos internamente.

Los argumentos deben:

- validarse;
- tiparse conceptualmente;
- limitarse;
- serializarse de manera segura.

Aplicar:

- timeout;
- control de código de salida;
- control de stderr;
- límite razonable de salida;
- cancelación cuando corresponda.

---

# 26. Procesos largos

Entrenamientos de IA y simulaciones extensas pueden superar el tiempo razonable de una petición HTTP.

Diseñar estos procesos conceptualmente como trabajos:

```text
POST /simulation
    ↓
jobId

GET /simulation/:jobId
    ↓
estado

GET /simulation/:jobId/results
    ↓
resultado
```

Estados recomendados:

```text
pending
running
completed
failed
cancelled
```

Para telemetría en tiempo real puede utilizarse posteriormente:

- WebSocket;
- Server-Sent Events.

Evitar mantener peticiones HTTP abiertas durante entrenamientos prolongados.

---

# 27. Contratos API

Las respuestas del backend deben ser consistentes.

Ejemplo:

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

Errores:

```json
{
  "success": false,
  "error": {
    "code": "SIMULATION_FAILED",
    "message": "No fue posible ejecutar la simulación"
  }
}
```

Evitar que cada endpoint invente un formato de respuesta diferente.

---

# 28. Integridad entre módulos

Antes de cambiar la forma de un objeto compartido, revisar todos sus consumidores.

Ejemplos:

```text
Bus
Intersection
Route
Phase
Movement
AgentState
SimulationState
Telemetry
Metric
```

Si cambia una estructura compartida:

1. identificar productores;
2. identificar consumidores;
3. actualizar ambos extremos;
4. actualizar tests;
5. registrar el cambio.

---

# 29. Reglas específicas para agentes de programación

El agente debe:

- modificar únicamente lo necesario;
- conservar código funcional no relacionado;
- explicar mediante nombres y estructura antes que mediante comentarios excesivos;
- evitar código muerto;
- eliminar imports no utilizados;
- eliminar debugging temporal antes de finalizar;
- revisar errores tipográficos;
- comprobar paths;
- comprobar nombres de archivos;
- comprobar mayúsculas/minúsculas;
- verificar dependencias;
- ejecutar validaciones disponibles.

El agente **no debe**:

- inventar APIs inexistentes;
- asumir archivos que no ha leído;
- crear lógica duplicada;
- introducir valores mágicos sin justificación;
- modificar contratos silenciosamente;
- ignorar errores;
- desactivar tests para conseguir que una tarea pase;
- reducir reglas de seguridad para simplificar una implementación;
- introducir lógica específica para una única intersección si puede resolverse paramétricamente.

---

# 30. Comentarios y documentación

Los comentarios deben explicar principalmente:

```text
por qué
```

y no repetir:

```text
qué hace literalmente la siguiente línea
```

Documentar especialmente:

- decisiones algorítmicas;
- fórmulas;
- recompensas;
- normalizaciones;
- estados del DQN;
- acciones;
- action masking;
- reglas Clingo;
- contratos entre módulos.

---

# 31. Prioridad arquitectónica

Cuando exista duda sobre dónde implementar una funcionalidad, utilizar esta regla:

```text
¿Es presentación?
→ frontend

¿Es API/orquestación/persistencia?
→ backend NestJS

¿Es aprendizaje reforzado o razonamiento lógico?
→ ia/

¿Es comportamiento del entorno?
→ simulacion/

¿Es legalidad topológica/semafórica?
→ Clingo

¿Es un parámetro variable?
→ configuración
```

---

# 32. Flujo conceptual definitivo

El sistema debe respetar conceptualmente:

```text
Configuración de infraestructura
        ↓
Clingo
        ↓
Movimientos válidos
        ↓
Conflictos
        ↓
Fases legales
        ↓
Simulación
        ↓
Vehículos + buses + paraderos
        ↓
Percepción
        ↓
Estado de agentes
        ↓
DQN
        ↓
Action masking
        ↓
Control semafórico
        ↓
Nuevo estado de simulación
        ↓
Recompensa
        ↓
Aprendizaje
        ↓
Métricas / telemetría
        ↓
Backend
        ↓
Frontend
```

---

# 33. Criterio de finalización de una tarea

Una intervención se considera terminada únicamente cuando:

- el código solicitado está implementado;
- la arquitectura existente fue respetada;
- no existen errores de sintaxis conocidos;
- imports y rutas fueron revisados;
- se realizaron las validaciones disponibles;
- no quedaron logs temporales innecesarios;
- no se introdujeron secretos;
- se revisaron efectos colaterales;
- se actualizó documentación si corresponde;
- se agregó la intervención a `AGENT_CHANGELOG.md`.

Si alguna validación no pudo ejecutarse, debe declararse explícitamente en el registro de cambios.

---

# 34. Regla final

Ante cualquier decisión de implementación, priorizar en este orden:

1. seguridad;
2. corrección;
3. consistencia con la arquitectura;
4. generalización;
5. reproducibilidad;
6. mantenibilidad;
7. claridad;
8. rendimiento;
9. conveniencia de implementación.

No sacrificar seguridad, corrección o generalidad únicamente para reducir código o terminar más rápido.
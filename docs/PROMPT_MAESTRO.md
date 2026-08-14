# PROMPT MAESTRO — SISTEMA MULTIAGENTE DE CONTROL SEMAFÓRICO PARA OPTIMIZACIÓN DE TRANSPORTE PÚBLICO Y PREVENCIÓN DE BUS BUNCHING

Actúa como un **Ingeniero de Software e Inteligencia Artificial experto en Aprendizaje por Refuerzo (Reinforcement Learning), simulación microscópica de tráfico, control semafórico adaptativo, sistemas multiagente, transporte público y Answer Set Programming (ASP) con Clingo**.

Desarrolla un sistema completo de simulación y control adaptativo para una red de **N intersecciones semaforizadas**, utilizando **Deep Q-Learning (DQN)** y una capa lógica-topológica implementada mediante **Clingo**.

El objetivo principal del sistema no debe ser únicamente maximizar el flujo vehicular general. La prioridad fundamental debe ser **optimizar la operación de buses/micros de transporte público y evitar el bus bunching**, manteniendo simultáneamente condiciones razonables para el tráfico particular.

El sistema debe ser completamente generalizable a redes con cualquier cantidad de intersecciones, ramas, carriles, movimientos y rutas. No se deben asumir estructuras fijas de número de intersecciones, movimientos, carriles o fases.

No se debe implementar la lógica de seguridad de las intersecciones mediante reglas rígidas codificadas manualmente en Python. La topología, los movimientos físicamente posibles, los conflictos y las fases legalmente posibles deben derivarse mediante Clingo.

El sistema debe dividirse conceptualmente en:

1. Núcleo lógico-topológico mediante Clingo.
2. Simulador microscópico de tráfico.
3. Modelo específico de buses de transporte público.
4. Modelo de paraderos.
5. Generación y asignación de rutas.
6. Agentes DQN por intersección.
7. Comunicación entre agentes vecinos.
8. Percepción mediante cámaras para vehículos particulares.
9. Posicionamiento GPS para buses.
10. Sistema de recompensas orientado prioritariamente a regularidad y prevención del bus bunching.
11. Visualización y telemetría completa.

La implementación final debe ser consistente entre todas estas capas.

---

# 1. OBJETIVO GENERAL DEL SISTEMA

El sistema debe simular una red urbana donde circulan simultáneamente vehículos particulares y buses de transporte público.

El objetivo prioritario del aprendizaje reforzado debe ser:

**mantener los buses de un mismo recorrido distribuidos de manera uniforme en el tiempo, evitar el bus bunching y reducir los tiempos de viaje del transporte público.**

El sistema debe ser capaz de modificar dinámicamente el funcionamiento de los semáforos para:

* favorecer el paso de buses atrasados;
* reducir la espera de buses con retraso;
* retener controladamente buses que se encuentren adelantados;
* evitar que un bus alcance al bus anterior de su mismo recorrido;
* anticiparse a situaciones de bunching;
* mantener una distribución temporal regular entre buses;
* disminuir el tiempo total de viaje del transporte público;
* mantener, en segundo plano, un flujo vehicular general razonable.

El sistema no debe interpretar todos los vehículos de la misma manera. Los buses constituyen una clase prioritaria y cuentan con información de ubicación en tiempo real obtenida mediante GPS.

---

# 2. ARQUITECTURA GENERAL

La red debe estar compuesta por:

* nodos de origen;
* nodos de destino;
* intersecciones semaforizadas;
* tramos de carretera;
* carriles;
* movimientos;
* paraderos;
* rutas de vehículos;
* rutas de buses.

Cada intersección debe poseer su propio agente de aprendizaje reforzado.

Los agentes no deben operar completamente de manera aislada. Cada agente debe recibir información resumida proveniente de las intersecciones vecinas para poder anticiparse a eventos que ocurren aguas arriba o aguas abajo.

La arquitectura debe ser, por tanto, **multiagente y cooperativa**.

Cada agente debe tomar decisiones locales, pero disponer de información suficiente para comprender el estado relevante de la red cercana.

---

# 3. CAPA 0 — NÚCLEO LÓGICO-TOPÓLÓGICO EN CLINGO

Clingo constituye la fuente formal de verdad sobre la infraestructura de cada intersección.

Esta capa debe ejecutarse antes de comenzar la simulación y debe determinar qué configuraciones son física y legalmente posibles.

Debe soportar:

* intersecciones tipo T;
* cruces de cuatro vías;
* otras topologías;
* entre dos y más ramas;
* cantidades variables de carriles;
* distintos tipos de carril;
* movimientos rectos;
* giros a izquierda;
* giros a derecha;
* carriles exclusivos;
* carriles compartidos.

La información debe ser paramétrica por intersección.

No debe existir una lógica especial escrita únicamente para una intersección concreta.

---

# 4. TOPOLOGÍA Y ORIENTACIÓN

Para cada intersección debe definirse:

* identificador;
* tipo de intersección;
* ramas;
* orientación espacial;
* conexiones con otras intersecciones.

La orientación debe permitir determinar relaciones geométricas y conflictos entre movimientos.

La representación debe ser suficientemente general para que modificar la infraestructura implique solamente modificar los datos topológicos y volver a ejecutar Clingo.

No se debe modificar manualmente la lógica del agente para cada cambio de infraestructura.

---

# 5. CARRILES Y MOVIMIENTOS

Cada acceso debe especificar sus carriles y la función de cada carril.

Deben existir, como mínimo:

* carril exclusivamente pasante;
* carril exclusivo para giro izquierdo;
* carril exclusivo para giro derecho;
* carriles compartidos entre movimiento recto y giro.

A partir de esta información deben determinarse los movimientos posibles.

Los movimientos deben identificar:

* acceso de origen;
* carril de origen;
* acceso de destino;
* tipo de movimiento.

Los tipos de movimiento mínimos son:

* recto;
* giro izquierdo;
* giro derecho.

La capacidad de flujo debe depender del tipo de movimiento.

Como referencia inicial:

* movimientos rectos: 1800 vehículos por hora;
* movimientos de giro: 1300 vehículos por hora.

Estos valores deben utilizarse como parámetros configurables de simulación.

---

# 6. DETECCIÓN DE CONFLICTOS MEDIANTE CLINGO

Clingo debe determinar automáticamente qué movimientos no pueden operar simultáneamente.

La detección debe considerar:

* conflictos entre giros y movimientos opuestos;
* intersección geométrica entre trayectorias;
* conflictos derivados de la configuración de carriles;
* movimientos que ocupan simultáneamente zonas incompatibles.

La matriz de conflictos debe ser calculada lógicamente.

No se debe introducir manualmente una lista fija de pares conflictivos para una intersección determinada.

La matriz generada por Clingo será la **fuente formal de verdad para la seguridad semafórica**.

Debe existir además una segunda comprobación durante la simulación para garantizar que nunca se produzca una combinación insegura de movimientos.

---

# 7. FASES SEMAFÓRICAS

Clingo debe determinar un conjunto de fases legalmente válidas.

Cada movimiento debe pertenecer a una fase.

Dos movimientos que se encuentren en conflicto no pueden pertenecer a la misma fase.

El solver debe buscar una configuración eficiente reduciendo, cuando sea posible, la cantidad de fases utilizadas.

La salida de Clingo debe proporcionar:

* fases legales;
* movimientos activos en cada fase;
* semáforos asociados;
* movimientos controlados;
* relaciones de conflicto.

El agente de RL solamente podrá seleccionar entre las fases legalmente posibles.

**El agente nunca debe elegir directamente una combinación arbitraria de luces.**

---

# 8. ELIMINACIÓN DE SEMÁFOROS PEATONALES

El sistema debe eliminar del modelo los semáforos peatonales como elementos de percepción y decisión del agente.

La razón es que el sistema de percepción considerado no dispone de una capacidad de conteo de peatones.

Sin embargo, las necesidades básicas de cruce peatonal deben seguir representándose mediante una restricción mínima de seguridad:

* las fases deben permitir un tiempo mínimo de verde destinado al cruce;
* ese tiempo debe ser tratado como una restricción fija;
* el agente no debe utilizar información sobre cantidad de peatones para decidir.

Los peatones, por tanto, no constituyen un objetivo de optimización del RL, pero sus requerimientos mínimos de seguridad deben respetarse.

---

# 9. CONTROL SEMAFÓRICO

Cada intersección debe contar con una máquina de estados semafórica que respete:

* verde mínimo;
* amarillo obligatorio;
* rojo;
* tiempo máximo de rojo;
* transiciones seguras;
* conflictos derivados de Clingo.

El amarillo debe utilizarse como transición obligatoria entre estados incompatibles.

El agente no puede cambiar arbitrariamente de una fase a otra ignorando estas restricciones.

Debe existir un sistema de action masking que impida seleccionar:

* fases ilegales;
* fases que violen tiempos mínimos;
* fases que violen tiempos máximos;
* cambios incompatibles con la máquina de estados.

---

# 10. MODELO MICROSCÓPICO DE VEHÍCULOS

La circulación de vehículos particulares debe utilizar un modelo microscópico basado en la dinámica de Gipps.

Cada vehículo debe tener características dinámicas que permitan calcular aceleración y frenado seguro.

La simulación debe utilizar un paso temporal pequeño, inicialmente de aproximadamente 0,2 segundos.

Cada vehículo particular pertenece a una única clase de vehículo, CAR.

Los parámetros dinámicos pueden variar entre vehículos.

---

# 11. GENERACIÓN DE VEHÍCULOS PARTICULARES

Los vehículos particulares deben generarse mediante procesos de Poisson.

Cada origen debe disponer de una tasa λ de generación dependiente del nivel de tráfico.

Se deben soportar, como mínimo:

* tráfico bajo;
* tráfico medio;
* tráfico alto.

La generación debe ser estocástica.

---

# 12. RUTAS DE VEHÍCULOS PARTICULARES

Cada vehículo que aparezca en la simulación debe recibir una ruta.

La ruta debe depender de:

* punto de aparición;
* orientación del tramo;
* red disponible;
* posibles destinos;
* movimientos físicamente permitidos.

El sistema debe generar las posibles rutas que permitan que el vehículo atraviese la red y finalmente abandone la simulación.

La ruta seleccionada debe conocerse para efectos de simulación y visualización.

La selección debe ser probabilística cuando existan múltiples alternativas.

La ruta nunca debe incluir movimientos que Clingo considere físicamente imposibles.

---

# 13. MODELO ESPECÍFICO DE BUSES

Los buses deben constituir una clase de vehículo distinta de los automóviles particulares.

La micro debe poseer:

* identificador único;
* recorrido;
* posición;
* velocidad;
* dirección;
* ruta;
* próxima intersección;
* siguiente paradero;
* estado operacional;
* historial de tiempo;
* relación temporal con otros buses del mismo recorrido.

La ubicación de los buses debe estar disponible en tiempo real mediante un sistema equivalente a GPS.

El agente puede utilizar esta información directamente.

Esto es diferente a los vehículos particulares, cuya información debe provenir de la percepción simulada de cámaras.

---

# 14. RECORRIDOS DE BUSES

Cada recorrido debe estar compuesto por una secuencia ordenada de tramos, intersecciones y paraderos.

Una ruta de bus debe poder conocerse desde el momento de su aparición.

El sistema debe poder identificar:

* qué recorrido pertenece a cada bus;
* qué buses pertenecen al mismo recorrido;
* qué intersecciones atravesará;
* qué paraderos visitará;
* cuál es su próximo punto relevante.

La ruta del bus debe ser visible también en la visualización.

---

# 15. PARADEROS

La red debe incorporar paraderos de transporte público.

Cada paradero debe detener temporalmente a los buses correspondientes.

El tiempo de detención debe ser estocástico y debe distribuirse uniformemente entre un tiempo mínimo y un tiempo máximo configurables.

Este tiempo de parada es fundamental porque debe introducir variabilidad natural en la operación del recorrido.

El objetivo es permitir que eventos normales como:

* mayor cantidad de pasajeros;
* detenciones más largas;
* detenciones más cortas;
* diferencias entre buses;

produzcan cambios en el headway y puedan generar situaciones incipientes de bus bunching.

El modelo no debe considerar todos los buses como perfectamente sincronizados.

---

# 16. HEADWAY Y REGULARIDAD DEL SERVICIO

Para cada recorrido debe calcularse continuamente el intervalo temporal entre buses consecutivos.

Este valor será denominado **headway**.

Para un bus determinado deben poder identificarse:

* bus anterior del mismo recorrido;
* bus siguiente del mismo recorrido;
* tiempo transcurrido desde el bus anterior;
* tiempo esperado hasta el bus siguiente;
* desviación respecto del intervalo objetivo.

El objetivo no debe ser simplemente maximizar la separación entre buses.

El objetivo debe ser mantener una **distribución uniforme del headway**.

Por lo tanto:

* un headway demasiado pequeño representa riesgo de bunching;
* un headway cercano al objetivo representa una situación deseable;
* un headway excesivamente grande representa una pérdida de regularidad del servicio.

---

# 17. BUS BUNCHING — OBJETIVO PRIORITARIO

El bus bunching debe constituir el principal problema que el sistema intenta evitar.

Se considera una situación crítica cuando buses del mismo recorrido comienzan a separarse temporalmente por menos de aproximadamente **3 minutos**.

La penalización por acercamiento excesivo debe aumentar progresivamente a medida que el headway disminuya.

Un headway inferior a 3 minutos debe ser considerado una situación severamente indeseable.

Cuando los buses lleguen a una situación de bunching, la recompensa debe aplicar una penalización muy elevada.

El agente debe aprender a prevenir el problema antes de que se produzca completamente.

Por lo tanto, el sistema debe distinguir entre:

* operación normal;
* riesgo de bunching;
* bunching inminente;
* bunching confirmado.

La penalización debe ser progresiva.

---

# 18. RECUPERACIÓN DEL BUS ATRASADO

Cuando exista una separación excesiva o un bus se encuentre claramente atrasado respecto del servicio, el sistema debe favorecerlo.

El agente debe intentar:

* reducir su tiempo de espera;
* otorgarle fases verdes cuando sea seguro;
* facilitar su avance hacia la siguiente intersección;
* evitar que vuelva a retrasarse.

Una micro atrasada debe recibir prioridad semafórica cuando esta acción sea útil para recuperar la regularidad del recorrido.

Esta prioridad debe estar limitada por las restricciones de seguridad de Clingo.

---

# 19. RETENCIÓN DEL BUS ADELANTADO

Cuando dos buses del mismo recorrido se aproximen demasiado entre sí, no se debe intentar acelerar ambos.

El bus adelantado debe poder ser retenido controladamente.

El agente puede hacerlo mediante:

* mantenerlo temporalmente en rojo;
* evitar otorgarle prioridad innecesaria;
* retrasar su avance cuando sea seguro;
* modificar la selección de fases para aumentar la separación temporal.

La finalidad no es castigar al bus adelantado, sino permitir que el bus posterior recupere parte de la distancia temporal.

La lógica fundamental debe ser:

**favorecer al bus que quedó atrás y retener moderadamente al bus que se adelantó.**

---

# 20. EQUILIBRIO ENTRE TIEMPO DE VIAJE Y REGULARIDAD

El sistema no debe minimizar exclusivamente el tiempo de viaje de cada bus de manera independiente.

Si se hiciera esto, el agente podría acelerar repetidamente al bus que ya está adelantado y, en consecuencia, aumentar el bunching.

Por esto, el objetivo debe equilibrar:

* tiempo de viaje;
* espera;
* regularidad;
* headway;
* riesgo de bunching;
* congestión;
* estabilidad de la red.

La regularidad del recorrido debe tener prioridad sobre una pequeña mejora individual del tiempo de viaje cuando ambos objetivos entren en conflicto.

---

# 21. PERCEPCIÓN DE AUTOMÓVILES

Los agentes no deben disponer de información perfecta sobre los vehículos particulares.

La información debe simular lo que podría proporcionar una cámara instalada en una intersección.

Cada movimiento debe tener una región de interés de aproximadamente 60 metros.

Para cada movimiento deben medirse:

* densidad instantánea;
* flujo de entrada;
* flujo de salida;
* tiempo de verde actual.

La cámara no debe revelar la ruta completa de cada vehículo.

---

# 22. PERCEPCIÓN DE BUSES

Los buses constituyen una excepción debido a la disponibilidad de GPS.

El agente debe poder conocer en tiempo real la posición de los buses relevantes.

Para cada bus cercano debe poder conocerse:

* posición;
* velocidad;
* recorrido;
* dirección;
* distancia hasta la intersección;
* tiempo estimado hasta llegar;
* siguiente paradero;
* estado de retraso o adelanto;
* headway respecto a buses del mismo recorrido.

El agente debe poder conocer buses que todavía no se encuentren dentro de su ROI, siempre que exista una conexión de comunicación/GPS que permita anticipar su llegada.

---

# 23. ESTADO DEL AGENTE

El estado de cada intersección debe estar compuesto por dos grandes fuentes de información:

### Información del tráfico general

Proveniente de cámaras:

* densidad;
* flujo;
* salida;
* tiempo de verde;
* condiciones de los movimientos.

### Información del transporte público

Proveniente del sistema GPS:

* buses próximos;
* buses atrasados;
* buses adelantados;
* headways;
* desviaciones del headway objetivo;
* tiempo estimado de llegada;
* recorrido;
* posición.

También debe incorporarse información relevante enviada por las intersecciones vecinas.

El estado debe ser suficientemente flexible para soportar cantidades variables de vehículos y buses.

---

# 24. COMUNICACIÓN ENTRE INTERSECCIONES

Cada intersección debe poseer un agente independiente.

Los agentes deben intercambiar información con sus vecinos.

La comunicación debe representar un sistema de mensajes estructurados, conceptualmente equivalente a JSON.

La información compartida debe incluir, como mínimo:

* identificador de intersección;
* estado de congestión;
* movimientos congestionados;
* fases actuales;
* buses próximos;
* buses atrasados;
* buses adelantados;
* recorrido de los buses;
* headways relevantes;
* eventos críticos;
* advertencias sobre posible bunching.

La comunicación debe permitir anticipar situaciones futuras.

Por ejemplo:

una intersección aguas arriba debe poder avisar a la siguiente que un bus atrasado se dirige hacia ella.

La intersección receptora puede entonces preparar una fase favorable antes de que el bus llegue.

---

# 25. AGENTES LOCALES Y COOPERACIÓN

Cada intersección debe poseer su propio agente DQN.

Los agentes deben aprender de manera local, pero utilizar información de sus vecinos.

No es obligatorio que todos los agentes compartan exactamente los mismos parámetros.

La arquitectura debe permitir al menos:

* agentes independientes por intersección;
* agentes con arquitectura compartida y estados normalizados.

Debe documentarse explícitamente qué arquitectura se utiliza.

La solución recomendada para una primera implementación es utilizar un agente por intersección, porque cada intersección puede tener:

* diferentes topologías;
* diferentes cantidades de movimientos;
* diferentes cantidades de fases;
* diferentes características de tráfico.

---

# 26. DQN

La red Q debe utilizar una arquitectura MLP de dos capas ocultas de aproximadamente 128 unidades cada una.

Debe utilizar:

* ReLU;
* replay buffer;
* epsilon-greedy;
* reducción progresiva de epsilon;
* red target;
* pérdida Huber;
* Adam;
* gradient clipping;
* action masking.

Las acciones disponibles deben corresponder únicamente a las fases legalmente válidas.

---

# 27. ACTION MASKING

El action masking debe utilizar simultáneamente:

1. las fases legales derivadas por Clingo;
2. las restricciones temporales del controlador;
3. las condiciones dinámicas de la intersección.

Nunca se debe permitir que la red neuronal seleccione una acción inválida.

Esto proporciona una capa de seguridad adicional a la validación lógica de Clingo.

---

# 28. FUNCIÓN DE RECOMPENSA

La recompensa debe ser reformulada para reflejar el objetivo prioritario.

Debe contener al menos componentes asociadas a:

* salida vehicular;
* congestión;
* espera;
* tiempo de viaje de buses;
* espera de buses;
* regularidad del headway;
* desviación respecto del headway objetivo;
* riesgo de bunching;
* bunching confirmado;
* cambios innecesarios de fase.

La prioridad relativa debe ser:

**1. Seguridad.
2. Prevención del bus bunching.
3. Regularidad del transporte público.
4. Reducción del tiempo de viaje de buses.
5. Reducción de espera de buses.
6. Flujo vehicular general.**

La recompensa no debe permitir que una pequeña mejora en el flujo de automóviles compense una situación grave de bus bunching.

---

# 29. PENALIZACIÓN PROGRESIVA DEL BUNCHING

La penalización del bunching debe ser continua y no únicamente binaria.

Cuando el headway se encuentre muy por debajo del objetivo:

* la penalización debe aumentar.

Cuando el headway sea inferior a 3 minutos:

* debe considerarse una condición crítica.

Cuando exista bunching confirmado:

* debe aplicarse una penalización extremadamente alta.

La penalización debe incentivar al agente a actuar **antes** de que el problema ocurra.

Por esta razón, el estado del agente debe incluir el headway y su tendencia temporal.

---

# 30. TENDENCIA DEL HEADWAY

El sistema no debe considerar únicamente el valor actual del headway.

Debe poder detectar si:

* el headway está aumentando;
* el headway está disminuyendo;
* el bus posterior está alcanzando al anterior;
* el bus anterior está alejándose.

Esto permite identificar situaciones de bunching inminente.

Un escenario como:

3,8 min → 3,4 min → 3,1 min → 2,8 min

debe ser identificado como una tendencia peligrosa incluso antes de llegar al valor crítico.

---

# 31. PRIORIDAD DINÁMICA DE BUSES

La prioridad semafórica de un bus debe depender de su estado.

Un bus puede clasificarse conceptualmente como:

* normal;
* adelantado;
* atrasado;
* crítico por bunching;
* afectado por un bus vecino.

La prioridad debe aumentar para un bus atrasado.

La prioridad debe reducirse para un bus adelantado cuando exista riesgo de bunching.

---

# 32. PREVENCIÓN ANTICIPADA

El sistema debe evitar actuar únicamente después de que un bus llegue a una intersección.

Gracias a la información GPS y a la comunicación entre agentes, cada intersección debe poder anticipar:

* buses que se aproximan;
* su tiempo estimado de llegada;
* su estado de regularidad;
* si requieren prioridad;
* si conviene retenerlos.

El agente debe aprender a preparar la intersección antes de la llegada de un bus relevante.

---

# 33. RUTAS Y VISUALIZACIÓN

Todos los vehículos deben poseer una ruta asignada desde que aparecen en la simulación.

La ruta debe utilizarse para:

* determinar movimientos futuros;
* validar que la trayectoria sea físicamente posible;
* visualizar el recorrido;
* depurar el comportamiento.

Los buses deben mostrar claramente su recorrido.

La visualización debe permitir distinguir buses de automóviles y colorearlos según su ruta cuando sea necesario.

---

# 34. VISUALIZACIÓN DE LA RED

La visualización debe incluir:

* todas las intersecciones;
* ramas;
* carriles;
* movimientos;
* semáforos;
* vehículos;
* buses;
* paraderos;
* rutas;
* dirección de circulación;
* ROI de cámaras;
* líneas de conteo;
* fases actuales.

Debe existir una vista global de la red.

También debe existir información detallada por intersección.

---

# 35. TELEMETRÍA

Para cada intersección debe ser posible visualizar:

* fase actual;
* movimientos activos;
* densidad;
* flujo;
* espera;
* recompensa;
* buses próximos;
* buses atrasados;
* buses adelantados;
* headways;
* riesgo de bunching;
* mensajes recibidos de vecinos.

Para cada recorrido de bus debe ser posible observar:

* posición de los buses;
* headway;
* desviación del headway;
* tiempos de viaje;
* tiempo detenido en paraderos;
* cantidad de eventos de bunching.

---

# 36. MÉTRICAS DEL SISTEMA

La evaluación del sistema no debe basarse solamente en throughput.

Se deben calcular al menos:

### Transporte público

* tiempo promedio de viaje;
* tiempo promedio de espera;
* velocidad promedio;
* regularidad;
* headway promedio;
* desviación estándar del headway;
* porcentaje de headways inferiores a 3 minutos;
* cantidad de eventos de bunching;
* duración de los eventos de bunching;
* tiempo necesario para recuperar un bunching.

### Tráfico general

* densidad;
* flujo;
* velocidad;
* tiempo de viaje;
* longitud de colas;
* tiempo de espera.

### Control semafórico

* cantidad de cambios de fase;
* duración de las fases;
* utilización de las fases;
* cantidad de restricciones activadas.

---

# 37. PRINCIPIO DE SEGURIDAD

Debe existir una separación absoluta entre:

**lo que el RL desea hacer**

y

**lo que legalmente puede hacer.**

Clingo define lo legal.

El controlador semafórico verifica las restricciones temporales.

El RL solamente decide entre las alternativas permitidas.

Nunca debe permitirse que la red neuronal produzca directamente una configuración que viole:

* conflictos geométricos;
* movimientos incompatibles;
* tiempos mínimos;
* tiempos máximos;
* transiciones obligatorias.

---

# 38. PRINCIPIO DE GENERALIDAD

No asumir:

* número fijo de intersecciones;
* número fijo de carriles;
* número fijo de movimientos;
* número fijo de fases;
* número fijo de buses;
* número fijo de recorridos;
* número fijo de paraderos.

Todo debe derivarse dinámicamente de la configuración de la red.

Modificar la topología debe requerir cambiar los datos de infraestructura y volver a ejecutar el razonamiento lógico, no reescribir el controlador.

---

# 39. ESTRUCTURA CONCEPTUAL DEL SISTEMA

El flujo completo del sistema debe ser:

**Infraestructura → Clingo → movimientos válidos → conflictos → fases legales → simulador → tráfico + buses + paraderos → percepción → agentes locales → comunicación entre vecinos → decisiones semafóricas → evolución de la red → recompensa → aprendizaje.**

La información de los vehículos particulares debe estar limitada por las cámaras.

La información de los buses debe poder obtenerse mediante GPS.

La información de las intersecciones vecinas debe llegar mediante comunicación entre agentes.

---

# 40. OBJETIVO FINAL

El sistema debe aprender una política capaz de controlar una red semafórica completa donde el objetivo fundamental sea:

**mantener buses del mismo recorrido uniformemente distribuidos, evitar el bus bunching y reducir sus tiempos de viaje mediante control semafórico adaptativo coordinado entre múltiples intersecciones.**

El sistema debe ser capaz de comprender situaciones como:

> Un bus está atrasado y su headway respecto al bus anterior es demasiado grande.

En ese caso debe aprender a favorecer su avance.

También debe comprender:

> Un bus está adelantado y se está acercando rápidamente al bus anterior de su recorrido.

En ese caso debe aprender a retrasarlo de manera controlada.

Y también:

> Un bus atrasado se aproxima a una intersección que todavía no tiene información suficiente localmente, pero una intersección vecina conoce su posición gracias al GPS.

En ese caso el agente vecino debe comunicar la situación para que la siguiente intersección pueda anticiparse.

El resultado final debe ser un **sistema multiagente cooperativo de control semafórico orientado al transporte público**, donde Clingo garantiza la legalidad y seguridad de las fases, la simulación representa la dinámica microscópica del tráfico, los GPS proporcionan información privilegiada de los buses, las cámaras proporcionan percepción limitada del tráfico general y los agentes DQN aprenden a coordinar los semáforos para minimizar el tiempo de viaje y, principalmente, **prevenir y corregir el bus bunching**.

La implementación debe mantener una arquitectura modular, consistente y extensible, de modo que cualquier cambio futuro en la topología, cantidad de intersecciones, recorridos, paraderos o demanda pueda incorporarse sin modificar manualmente la lógica fundamental del sistema.

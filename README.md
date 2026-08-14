# Plataforma Full Stack de Control Semafórico

Este repositorio contiene solo la estructura base para un monorepo con:

- Frontend en React + Vite.
- Backend en NestJS con JavaScript.
- Una carpeta externa para IA en Python/Clingo.
- Una carpeta externa para simulación en Python.

## Estructura base

```text
frontend/
	src/
		pages/
		components/
		services/
		hooks/
		context/
		store/
		visualization/
backend/
	src/
		ia/
			clingo/
			modelos/
			entrenamiento/
			scripts/
		simulacion/
			trafico/
			vehiculos/
			buses/
			paraderos/
			rutas/
			telemetria/
			metricas/
			percepcion/
			comunicacion/
			recompensas/
		config/
		database/
		common/
		dtos/
		tests/
```

## Requisitos

- Node.js 20+
- npm 10+
- PostgreSQL 16+ o compatible
- Opcional: Docker para levantar la base de datos

## Variables de entorno

- Copia [/.env.example](.env.example) para variables del frontend.
- Usa [backend/.env.example](backend/.env.example) como plantilla del backend.
- El backend debe apuntar a `PYTHON_BIN` y `CLINGO_PATH` para ejecutar la IA y leer su salida por stdout.

## Levantar la base de datos

Ejemplo con Docker:

```bash
docker run --name control-semaforico-db -e POSTGRES_DB=control_semaforico -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
```

Si usas una instalación local, asegúrate de que `DATABASE_URL` apunte a esa instancia.

## Instalación

Desde la raíz:

```bash
npm install
```

## Ejecución

Levantar ambos proyectos a la vez:

```bash
npm run dev
```

Ejecutar por separado:

```bash
npm run backend
npm run frontend
```

La idea es que Nest reciba solicitudes HTTP, ejecute los scripts de `backend/src/ia` o `backend/src/simulacion` y consuma el output generado por esos procesos.

Por ahora el repositorio solo define la estructura base; no incluye lógica de negocio ni implementación de los módulos.

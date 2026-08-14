# React + NestJS MVC Base

Estructura base full-stack en un mismo directorio:

- `frontend/`: React + Vite
- `backend/`: NestJS usando JavaScript

El backend incluye una separación simple estilo MVC:

- `models/`: modelo de datos
- `controllers/`: endpoints HTTP
- `services/`: lógica de aplicación

## Requisitos

- Node.js 20+
- npm 10+

## Instalación rápida desde la raíz

```bash
npm install
npm run dev
```

Esto levanta simultáneamente:

- Backend: `http://localhost:3000`
- Frontend: `http://localhost:5173`

También puedes ejecutarlos por separado.

## Ejecutar backend

```bash
cd backend
npm install
npm run start:dev
```

Backend disponible en:

```text
http://localhost:3000
```

Endpoint de ejemplo:

```text
GET http://localhost:3000/api/users
```

## Ejecutar frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible normalmente en:

```text
http://localhost:5173
```

Vite redirige `/api` hacia `http://localhost:3000` durante desarrollo.

# Frontend API Integration Map

## Frontend Routes
- `/`: Landing page with Ballpit hero and product sections.
- `/login`: Backend JWT login flow.
- `/signup`: Backend signup + JWT login.
- `/workspace`: Protected route for upload, EDA, and visualization.

## Auth and Security Flow
1. User signs up using backend `/auth/signup`.
2. Frontend logs user in using backend `/auth/login` (OAuth2 form username/password).
3. Backend validates credentials against database and returns JWT access token (`access_token`).
4. JWT is stored in local storage and sent as `Authorization: Bearer <token>` to protected endpoints.

## Backend Endpoints Used by Frontend
- `POST /auth/signup`
  - Body: `{ "email": "...", "password": "..." }`
- `POST /auth/login`
  - Form data: `username=<email>&password=<password>`
  - Returns: `{ "access_token": "...", "token_type": "bearer" }`
- `GET /auth/users/me` (auth required)
- `POST /api/upload/`
  - Multipart form-data with `file`
  - Returns: `{ "message": "File uploaded successfully", "saved_as": "..." }`
- `POST /api/eda/analyze` (auth required)
  - Body: `{ "filename": "..." }`
- `POST /api/visualization/columns` (auth required)
  - Body: `{ "filename": "..." }`
- `POST /api/visualization/generate` (auth required)
  - Body: `{ "filename": "...", "chart_type": "bar", "x_column": "...", "y_column": "..." }`

## Data Path Integrity Note
Backend dataset-related APIs now use repository-relative path resolution to `datasets/`:
- `backend/app/api/upload.py`
- `backend/app/api/EDA.py`
- `backend/app/api/visualization.py`

This avoids machine-specific hardcoded paths and keeps upload/EDA/visualization consistent.

## Required Frontend Environment Variables
Use `frontend/.env.example` as template:
- `VITE_API_BASE_URL`

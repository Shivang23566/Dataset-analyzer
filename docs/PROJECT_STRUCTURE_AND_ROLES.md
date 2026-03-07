# Project Structure and File Roles for Dataset Analyzer 2

## Project Overview
This project is a dataset analysis web application. Users can sign up, log in, upload datasets, and then perform Exploratory Data Analysis (EDA) and visualizations on their uploaded data. The backend is implemented in Python (FastAPI), and the frontend is implemented in React + TypeScript.

## Folder and File Roles

### backend/
- **__init__.py**: Marks the backend directory as a Python package.
- **Dockerfile**: Containerization setup for backend deployment.
- **requirements.txt**: Lists Python dependencies for the backend.

#### backend/app/
- **__init__.py**: Marks the app directory as a Python package.
- **config.py**: Application-level configuration settings.
- **main.py**: Likely the entry point for the backend API (FastAPI/Flask app).

##### backend/app/api/
- **__init__.py**: Marks the api directory as a Python package.
- **auth.py**: Handles authentication (login/signup endpoints).
- **deps.py**: Dependency injection for API routes (e.g., DB/session dependencies).
- **EDA.py**: Implements EDA-related API endpoints.
- **ml.py**: Implements machine learning-related API endpoints.
- **Statistical_Analysis.py**: Statistical analysis endpoints.
- **upload.py**: Handles dataset upload endpoints.
- **visualization.py**: Visualization-related API endpoints.

##### backend/app/core/
- **config.py**: Core configuration (environment variables, settings).
- **database.py**: Database connection and ORM setup.
- **security.py**: Security utilities (password hashing, JWT, etc.).

##### backend/app/models/
- **user.py**: Database model for user accounts.

##### backend/app/schemas/
- **token.py**: Pydantic schema for authentication tokens.
- **user.py**: Pydantic schema for user data.

##### backend/app/services/
- **eda_engine.py**: Business logic for EDA operations.
- **ml_engine.py**: Business logic for machine learning operations.
- **visualization_engine.py**: Business logic for visualizations.

#### backend/scripts/
- **create_db.py**: Script to initialize or migrate the database.

#### backend/test/
- **test_eda.py**: Tests for EDA endpoints/services.
- **test_ml.py**: Tests for ML endpoints/services.
- **test_upload.py**: Tests for upload endpoints/services.
- **test_visualization.py**: Tests for visualization endpoints/services.

### frontend/
- **package.json**: Frontend dependencies and scripts.
- **index.html**: Vite HTML entry point.
- **vite.config.ts**: Vite config for dev/build.
- **.env.example**: Required environment variables (API base URL + Firebase credentials).

#### frontend/src/
- **main.tsx**: React bootstrap and router mount.
- **App.tsx**: Route definitions (`/`, `/login`, `/signup`, `/workspace`) with protected route.

##### frontend/src/pages/
- **LandingPage.tsx**: Main marketing landing page using Ballpit background and product sections.
- **LoginPage.tsx**: Firebase login + backend JWT token exchange.
- **SignupPage.tsx**: Firebase signup + backend user registration + JWT issuance.
- **WorkspacePage.tsx**: Authenticated workspace layout with sidebar and analysis modules.

##### frontend/src/components/
- **BallpitBackground.tsx**: Interactive 3D Ballpit hero background.
- **Navbar.tsx**: Landing page top navigation.
- **AuthForm.tsx**: Shared login/signup form component.
- **Sidebar.tsx**: Post-upload flow selector (Upload, EDA, Visualization).
- **UploaderPanel.tsx**: Dataset upload UI (`/api/upload/`).
- **EDAView.tsx**: EDA trigger and tabular result rendering (`/api/eda/analyze`).
- **VisualizationView.tsx**: Chart builder UI (`/api/visualization/columns`, `/api/visualization/generate`).

##### frontend/src/lib/
- **authStore.ts**: Local storage helpers for backend JWT and user email.
- **api.ts**: API client for backend auth/upload/EDA/visualization endpoints.
- **types.ts**: Shared TypeScript request/response types.

##### frontend/src/styles/
- **global.css**: Global styles, responsive layouts, and visual theme tokens.

### datasets/
- Contains sample or uploaded datasets (CSV files).

### docs/
- Documentation folder (this file is stored here).

## Summary
- **Authentication (DB + JWT)**: backend/app/api/auth.py, backend/app/models/user.py, backend/app/schemas/user.py, backend/app/core/security.py
- **Dataset Upload**: backend/app/api/upload.py
- **EDA**: backend/app/api/EDA.py, backend/app/services/eda_engine.py
- **Visualization**: backend/app/api/visualization.py, backend/app/services/visualization_engine.py
- **ML**: backend/app/api/ml.py, backend/app/services/ml_engine.py
- **Database**: backend/app/core/database.py, backend/scripts/create_db.py
- **Configuration**: backend/app/config.py, backend/app/core/config.py
- **Testing**: backend/test/
- **Frontend App**: frontend/
- **Docs**: docs/
- **Sample Data**: datasets/

This file should be updated as the project evolves.
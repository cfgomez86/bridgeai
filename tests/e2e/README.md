# E2E Tests Guide

## 📋 Requisitos

Los tests E2E requieren que **3 servicios estén ejecutándose simultáneamente**:

### 1. **API Backend** (puerto 8000)
```bash
# Terminal 1: Desde raíz del proyecto
python -m uvicorn app.main:app --reload
```

### 2. **Frontend Next.js** (puerto 3000)
```bash
# Terminal 2: Desde raíz del proyecto
cd frontend && npm run dev
```

### 3. **PostgreSQL Database** (puerto 5432)
```bash
# Terminal 3 (o background): Desde raíz del proyecto
docker compose up -d
```

## 🚀 Ejecutar Tests E2E

### Ejecutar todos los e2e tests
```bash
pytest tests/e2e/ -v -s
```

### Con marcador
```bash
pytest -m e2e -v -s
```

### Solo tests e2e (sin unit/integration)
```bash
python run_tests.py e2e
```

## 🎬 Qué Hace el Test

El test `test_full_workflow()` simula el flujo completo del usuario:

1. **[0] Verifica disponibilidad** - Comprueba que frontend está disponible
2. **[1] Home** - Accede a la página principal
3. **[2] Indexing** - Ejecuta la indexación de código
4. **[3] Workflow Step 1** - Ingresa requisito y ejecuta análisis
5. **[4] Workflow Step 2** - Ejecuta análisis de impacto
6. **[5] Workflow Step 3** - Genera historia de usuario (LLM)
7. **[6] Workflow Step 4** - Prepara creación de ticket

## 📸 Screenshots

Todos los pasos generan screenshots guardados en `tests/e2e/screenshots/`:

```
01_home.png                       - Página principal
02_indexing.png                   - Página de indexación
03_indexing_done.png              - Indexación completada
04_step1_empty.png                - Formulario vacío
05_step1_filled.png               - Formulario completado
06_step2_loaded.png               - Análisis de impacto cargado
07_step2_done.png                 - Análisis de impacto completado
08_step3_done.png                 - Historia generada
09_step4_loaded.png               - Pantalla creación ticket
10_step4_filled.png               - Formulario de ticket
11_final.png                      - Estado final
```

## ⏱️ Tiempos Estimados

- **Sin LLM** (stub): ~2 minutos
- **Con LLM real**: ~5-10 minutos (depende de latencia de API)

## 🔍 Troubleshooting

### ❌ "Frontend not available at http://localhost:3000"
```bash
# Solución: Ejecutar frontend en otra terminal
cd frontend && npm run dev
```

### ❌ "button Analyze Requirement not found"
```bash
# Causas posibles:
# 1. Frontend no cargó correctamente
# 2. API no responde
# 3. Hay error JavaScript en consola del navegador

# Soluciones:
# - Revisar logs del frontend (npm run dev terminal)
# - Revisar logs de la API (python -m uvicorn terminal)
# - Revisar screenshot ERROR_button_not_found.png
```

### ❌ "Timeout waiting for API response"
```bash
# Si usa LLM real (Anthropic/OpenAI):
# - Verificar API_KEY configurada en .env
# - Verificar conectividad a internet
# - Aumentar timeout en test_workflow.py

# Si usa stub:
# - Verificar en .env: AI_PROVIDER=stub
```

### ❌ "Database connection error"
```bash
# Solución: Asegurar PostgreSQL está corriendo
docker compose up -d
```

## 🏗️ Arquitectura del Test

```
Test E2E (Playwright)
├── Chromium Browser (headless=false, slow_mo=300)
└── Conecta a:
    ├── Frontend: http://localhost:3000
    ├── API: http://localhost:8000/api
    └── DB: postgresql://localhost:5432/bridgeai
```

## 📝 Notas

- El test usa **modo interactivo** (`headless=False`) para observar el flujo
- `slow_mo=300` ralentiza cada acción 300ms (útil para debugging)
- Los timeouts están configurados de forma generosa:
  - Botones: 5 segundos
  - Análisis de impacto: 30 segundos
  - Generación de historia (LLM): 180 segundos (3 minutos)

## 🚫 Limitaciones Actuales

- No ejecuta creación de ticket real (requiere Jira/Azure DevOps válido)
- No valida contenido generado por LLM, solo que el proceso complete
- No prueba manejo de errores (validaciones fallidas, etc)

## 🎯 Próximos Pasos (Mejoras)

- [ ] Agregar tests parametrizados para múltiples requisitos
- [ ] Validar contenido de historias generadas
- [ ] Pruebas de manejo de errores
- [ ] Tests de compatibilidad en diferentes navegadores
- [ ] CI/CD integration (headless=True en GitHub Actions)

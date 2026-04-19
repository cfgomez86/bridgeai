# Test Suite Guide

## 📁 Structure

La suite de tests está organizada en tres categorías siguiendo el estándar de la industria:

```
tests/
├── conftest.py                  # Fixtures globales compartidas
├── unit/                        # Unit tests (113)
│   ├── conftest.py             # Fixtures específicas
│   └── test_*.py               # Tests unitarios
├── integration/                 # Integration tests (8)
│   ├── conftest.py             # Fixtures específicas
│   └── test_*.py               # Tests de endpoints
├── e2e/                        # End-to-end tests (1)
│   ├── conftest.py             # Fixtures específicas
│   ├── test_workflow.py        # Test flujo completo
│   └── screenshots/            # Capturas automáticas
└── __init__.py
```

---

## 🧪 Categorías de Tests

### Unit Tests (tests/unit/) - 113 tests
Tests de funciones, clases y métodos individuales sin dependencias externas.

**Características:**
- ✅ Rápidos (~7 segundos)
- ✅ Determinísticos
- ✅ Aislados (sin dependencias externas)
- 🚫 No usan TestClient
- 🚫 No interactúan con BD real

**Ejemplos:**
- `test_ai_requirement_parser.py`
- `test_code_indexing_service.py`
- `test_story_generation_service.py`

### Integration Tests (tests/integration/) - 8 tests
Tests de endpoints, servicios y componentes que trabajan juntos con TestClient e in-memory SQLite.

**Características:**
- ✅ Usan TestClient (FastAPI)
- ✅ Usan BD en memoria (SQLite)
- ✅ Validan flujos completos de API
- ⚠️ Más lentos que unit tests (~15 segundos)
- 🚫 No requieren servicios externos

**Ejemplos:**
- `test_health.py`
- `test_impact_analysis_endpoint.py`
- `test_ticket_integration_endpoint.py`

### E2E Tests (tests/e2e/) - 1 test
Tests end-to-end con navegación completa en navegador real (Playwright) y aplicación ejecutándose.

**Características:**
- ✅ Validan aplicación completa (UI + API + BD)
- ✅ Interacción real con el navegador
- ⚠️ Muy lentos (2-10 minutos según LLM)
- ⚠️ Pueden ser frágiles
- 📋 Requieren 3 servicios ejecutándose

**Qué hace `test_full_workflow()`:**
1. Verifica disponibilidad del frontend
2. Navega a indexación y ejecuta análisis de código
3. Entra a workflow → Ingresa requisito y ejecuta análisis
4. Ejecuta análisis de impacto
5. Genera historia de usuario con LLM (~30-100s)
6. Prepara creación de ticket (Jira/Azure DevOps)

---

## 🚀 Ejecutar Tests

### Opción 1: Comando Directo (RECOMENDADO)

```bash
# Solo unit (113 tests) - 7s
python -m pytest tests/unit/ -v

# Solo integration (8 tests) - 15s
python -m pytest tests/integration/ -v

# Unit + Integration (121 tests) - 22s
python -m pytest tests/unit/ tests/integration/ -v

# Solo E2E (requiere servicios)
python -m pytest tests/e2e/ -v -s

# TODOS los tests
python -m pytest tests/ -v -s
```

### Opción 2: Script PowerShell

```powershell
.\run_tests.ps1 unit
.\run_tests.ps1 integration
.\run_tests.ps1 all            # unit + integration
.\run_tests.ps1 e2e            # requiere servicios
.\run_tests.ps1 help           # muestra opciones
```

### Opción 3: VS Code UI

- Ctrl+Shift+D → Test Explorer
- Click en play al lado de cualquier test o categoría

### Variantes Útiles

```bash
# Con salida detallada
pytest tests/unit/ -v --tb=short

# Con output de print()
pytest tests/unit/ -v -s

# Test específico
pytest tests/unit/test_ai_requirement_parser.py::test_parse_requirement -v

# Con cobertura
pytest tests/unit/ --cov=app --cov-report=term-missing

# Tests que fallen ante primer error (-x)
pytest tests/unit/ -v -x

# Solo tests con cierto marcador
pytest -m e2e -v -s
```

---

## 📋 Requisitos para E2E Tests

Los tests E2E requieren que **3 servicios estén ejecutándose simultáneamente en 3 terminales**:

### Terminal 1: API Backend (puerto 8000)
```bash
cd c:\proyectos\bridgeai
python -m uvicorn app.main:app --reload
# Espera: "Uvicorn running on http://127.0.0.1:8000"
```

### Terminal 2: Frontend Next.js (puerto 3000)
```bash
cd c:\proyectos\bridgeai\frontend
npm run dev
# Espera: "Local: http://localhost:3000"
```

### Terminal 3: PostgreSQL (puerto 5432)
```bash
cd c:\proyectos\bridgeai
docker compose up -d
# O: docker compose up (sin -d para ver logs)
```

### Terminal 4: Ejecutar Tests E2E
```bash
cd c:\proyectos\bridgeai
python -m pytest tests/e2e/ -v -s
```

---

## 📸 E2E Test Output

El test genera screenshots automáticamente en `tests/e2e/screenshots/`:

```
02_indexing.png                - Página de indexación
03_indexing_done.png           - Después de ejecutar indexación
04_step1_empty.png             - Formulario vacío
05_step1_filled.png            - Formulario completado
06_step2_loaded.png            - Análisis de impacto cargado
07_step2_done.png              - Análisis completado
08_step3_done.png              - Historia generada
ERROR_button_not_found.png     - Si hay error (debugging)
```

---

## ⏱️ Performance

| Tipo | Tests | Tiempo | Dependencias |
|------|-------|--------|------------|
| Unit | 113 | ~7s | Python |
| Integration | 8 | ~15s | Python + SQLite |
| Unit + Integration | 121 | ~22s | Python + SQLite |
| E2E | 1 | 2-10min | Python + API + Frontend + LLM |

*E2E time varía según LLM: ~2min con stub, ~5-10min con API real (Anthropic/OpenAI)*

---

## 🔍 Troubleshooting

### ❌ "pytest: El término 'pytest' no se reconoce"
```powershell
# Usa python -m
python -m pytest tests/unit/ -v
```

### ❌ "E2E test SKIPPED - Services not available"
**Significa:** API o Frontend no están corriendo

**Solución:** Inicia los 3 servicios en terminales separadas (ver arriba)

### ❌ "Locator.wait_for: Timeout exceeded"
**Significa:** Botón no apareció en el tiempo esperado

**Soluciones:**
- Verifica que frontend está en http://localhost:3000
- Revisa logs del API para errores
- Screenshot `ERROR_button_not_found.png` muestra dónde falló
- Aumenta timeout en `test_workflow.py` si es muy lento

### ❌ "Database connection error"
**Solución:** Asegurar PostgreSQL está corriendo
```bash
docker compose up -d
```

### ❌ "timeout waiting for LLM response"
**Si usa LLM real:**
- Verifica `API_KEY` en `.env`
- Verifica conectividad a internet
- Espera más (hasta 3 minutos)

**Si usa stub:**
- Verifica en `.env`: `AI_PROVIDER=stub`

---

## 📊 Estado Actual

```
✅ Unit Tests:       113 PASS (7s)
✅ Integration Tests: 8 PASS (15s)
✅ TOTAL LOCAL:      121 PASS (22s)
⏳ E2E Tests:        1 PASS/SKIP (requiere servicios)
```

---

## 🏗️ Arquitectura

```
Test Layer
├── Unit (tests/unit/)
│   └── Función individual (no imports externos)
├── Integration (tests/integration/)
│   ├── TestClient (FastAPI)
│   ├── In-Memory SQLite DB
│   └── API Endpoints
└── E2E (tests/e2e/)
    ├── Playwright Browser
    ├── Frontend: http://localhost:3000
    ├── API: http://localhost:8000
    └── DB: PostgreSQL
```

---

## 📝 Configuración

### pytest.ini
```ini
[pytest]
asyncio_mode = auto              # Soporte para tests async
testpaths = tests
python_files = test_*.py
markers = 
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
```

### conftest.py (Global)
```python
@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent
```

### conftest.py (Unit)
Sin cambios especiales - usa fixtures por defecto

### conftest.py (Integration)
```python
@pytest.fixture
def client():
    # TestClient con BD en memoria
```

### conftest.py (E2E)
```python
@pytest.fixture(scope="function", autouse=True)
def verify_e2e_services_available():
    # Verifica API + Frontend disponibles
    # Salta test si no están listos
```

---

## ✅ Checklist Pre-Commit

```bash
# 1. Unit + Integration tests
python -m pytest tests/unit/ tests/integration/ -v

# 2. Si todo pasa - hacer commit
git add .
git commit -m "Feature description"

# 3. (Opcional) E2E test si servicios disponibles
python -m pytest tests/e2e/ -v -s
```

---

## 🎯 Comandos Rápidos

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo local (sin E2E)
python -m pytest tests/unit/ tests/integration/ -v

# Con cobertura
python -m pytest tests/ --cov=app

# Test específico
python -m pytest tests/unit/test_file.py::test_function -v

# Verbose + output
python -m pytest tests/ -vvs
```

---

## 📚 Referencias

- [pytest docs](https://docs.pytest.org/)
- [Playwright docs](https://playwright.dev/python/)
- [FastAPI testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
pytest --cov=app tests/
pytest --cov=app --cov-report=html tests/  # Genera reporte HTML
```

## 📊 Configuración

Cada nivel tiene su `conftest.py` con fixtures específicas:

### tests/conftest.py (Global)
- `project_root`: Directorio raíz del proyecto

### tests/unit/conftest.py (Unit tests)
- Fixtures para mocks y datos de prueba unitarios

### tests/integration/conftest.py (Integration tests)
- `in_memory_db`: Base de datos SQLite en memoria
- `client`: TestClient con PostgreSQL real
- `client_with_in_memory_db`: TestClient con base de datos en memoria

### tests/e2e/conftest.py (E2E tests)
- Fixtures específicas para Selenium/Playwright

## 💡 Buenas Prácticas

1. **Nombra tus tests descriptivamente**
   - ❌ `test_thing()`
   - ✅ `test_impact_analysis_returns_200_for_valid_requirement()`

2. **Usa fixtures** en lugar de crear instancias en cada test
   - Las fixtures en `conftest.py` son compartidas y reutilizables

3. **Un assert por test** (cuando sea posible)
   - Facilita identificar qué falló

4. **Mantén tests independientes**
   - No dependas del orden de ejecución
   - No compartas estado entre tests

5. **Coloca tests en la categoría correcta**
   - No uses TestClient en tests unitarios
   - No hagas queries SQL en tests unitarios

## 🔍 Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
Ejecuta desde la raíz del proyecto:
```bash
cd c:\proyectos\bridgeai
pytest tests/
```

### Tests se cuelgan en integration
Asegúrate de que PostgreSQL esté corriendo (para `client` fixture) o usa `client_with_in_memory_db`.

### Quiero que unit tests usen base de datos
Mueve el test a `tests/integration/` — los unit tests deben ser aislados.

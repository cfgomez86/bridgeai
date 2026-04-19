# Test Organization Guide

## 📁 Structure

La suite de tests está organizada en tres categorías siguiendo el estándar de la industria:

```
tests/
├── conftest.py                  # Fixtures globales compartidas
├── unit/                        # Unit tests
│   ├── conftest.py             # Fixtures específicas para unit tests
│   └── test_*.py               # Tests unitarios (sin dependencias externas)
├── integration/                 # Integration tests
│   ├── conftest.py             # Fixtures específicas para integration tests
│   └── test_*.py               # Tests de endpoints y servicios con TestClient
├── e2e/                        # End-to-end tests
│   ├── conftest.py             # Fixtures específicas para e2e tests
│   ├── test_*.py               # Tests de flujos completos
│   └── screenshots/            # Capturas de pantalla de pruebas
└── __init__.py
```

## 🧪 Categorías de Tests

### Unit Tests (tests/unit/)
Tests de funciones, clases y métodos individuales sin dependencias externas.
- ✅ Rápidos
- ✅ Determinísticos
- ✅ Aislados
- 🚫 No usan TestClient
- 🚫 No interactúan con la base de datos real

**Ejemplos:**
- `test_ai_requirement_parser.py`
- `test_code_indexing_service.py`
- `test_impact_analysis_service.py`

### Integration Tests (tests/integration/)
Tests de endpoints, servicios y componentes que trabajan juntos.
- ✅ Usan TestClient (FastAPI)
- ✅ Usan base de datos en memoria (SQLite)
- ✅ Validan flujos completos de API
- ⚠️ Más lentos que unit tests

**Ejemplos:**
- `test_health.py`
- `test_impact_analysis_endpoint.py`
- `test_ticket_integration_endpoint.py`

### E2E Tests (tests/e2e/)
Tests end-to-end con navegación completa y aplicación en ejecución.
- ✅ Validan la aplicación completa
- ⚠️ Muy lentos
- ⚠️ Pueden ser frágiles

**Ejemplos:**
- `test_workflow.py`

## 🚀 Ejecutar Tests

### Todos los tests
```bash
pytest
```

### Solo unit tests
```bash
pytest tests/unit/
```

### Solo integration tests
```bash
pytest tests/integration/
```

### Solo e2e tests
```bash
pytest tests/e2e/
```

### Con salida detallada
```bash
pytest -v

# Con salida de print
pytest -s

# Con salida detallada + print
pytest -v -s
```

### Un test específico
```bash
pytest tests/unit/test_ai_requirement_parser.py
pytest tests/unit/test_ai_requirement_parser.py::test_parse_requirement
pytest tests/integration/test_health.py::test_health_status_code
```

### Con cobertura
```bash
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

# BridgeAI — De requerimiento a historia, en minutos

Documento orientativo para equipos comerciales y stakeholders no técnicos.
Explica qué es BridgeAI, qué tipo de IA usa por dentro, y por qué es
distinto de las soluciones genéricas que ya existen en el mercado.

---

## 1. El problema que resolvemos

En cualquier empresa con desarrollo de software pasa lo mismo: un Product
Owner o un cliente escribe un requerimiento en lenguaje natural —algo como
*"necesitamos que los usuarios puedan recuperar su contraseña por
correo"*— y a partir de ahí empieza una cadena de horas (o días) de
trabajo manual:

- alguien lee el requerimiento y lo interpreta,
- alguien revisa el código para ver dónde tocar,
- alguien escribe la **Historia de Usuario** con criterios de aceptación,
- alguien la pasa a Jira o Azure DevOps con sus subtareas y estimaciones.

Ese trabajo es repetitivo, propenso a errores, y depende fuertemente del
analista que esté disponible. **BridgeAI automatiza esa cadena completa**:
recibe el texto del requerimiento y produce una historia lista para
desarrollar, conectada al repositorio real del cliente y publicable como
ticket en un clic.

---

## 2. ¿Qué es BridgeAI?

BridgeAI es una **plataforma SaaS multi-tenant** que se conecta a:

- los **repositorios de código** del cliente (GitHub, GitLab, Azure
  Repos, Bitbucket), y
- sus **sistemas de tickets** (Jira, Azure DevOps).

A partir de un texto en lenguaje natural, genera una historia de usuario
**completa** —descripción, criterios de aceptación, subtareas y notas de
riesgo— **fundamentada en el código real del cliente**, y la publica
directamente como ticket. Cada historia incluye además una **puntuación
de calidad** auditable, no es una caja negra.

---

## 3. ¿Qué tipo de IA es?

BridgeAI implementa una arquitectura **RAG léxico-estructural**. Es un
término técnico, así que vale la pena explicarlo en partes:

- **RAG** (*Retrieval-Augmented Generation*) significa que la IA, antes
  de responder, **recupera información relevante** y la usa como
  contexto. No "improvisa" desde su memoria entrenada: trabaja con datos
  reales del cliente.
- **Léxico** quiere decir que el sistema busca por **palabras clave**
  inteligentes (filtra ruido, normaliza español/inglés, conecta verbos
  con sustantivos).
- **Estructural** quiere decir que además **entiende cómo está
  organizado el código**: qué archivos importan a otros, qué clases
  existen, qué módulos están conectados entre sí.

Para lograr esto, BridgeAI utiliza **Abstract Syntax Trees (AST, o Árbol
de Sintaxis Abstracta)**. Un AST es una representación matemática de la
estructura del código: sin ejecutarlo, transforma el texto fuente en un
árbol donde cada nodo es una entidad del programa (clase, función, 
variable, import). Esto permite que el sistema **analice el código como
lo hace un compilador real**, no como texto plano. Con AST, BridgeAI
detecta relaciones que un análisis por palabras clave nunca vería: si
una clase hereda de otra, si una función es privada o pública, qué
métodos toca realmente el cambio solicitado. Esto aporta **seguridad** 
—el sistema no "adivina" dónde toca cambiar—, y **confianza** —cada 
historia generada se sustenta en análisis real de dependencias, no en 
coincidencias de nombres.

### El pipeline en 6 pasos (sin tecnicismos)

0. **Filtrar basura antes de empezar.** Antes de consumir ningún recurso,
   el sistema verifica que el texto sea un requerimiento de software real.
   Primero con reglas simples (sin IA), luego con un modelo de lenguaje
   liviano. Si el texto es conversacional, contradictorio o sin sentido,
   se devuelve inmediatamente con una explicación clara al usuario.
1. **Entender el requerimiento.** El sistema clasifica intención,
   entidad, tipo de feature, prioridad y dominio (autenticación, billing,
   reportes, etc.).
2. **Analizar impacto.** Recorre el repositorio del cliente, identifica
   archivos potencialmente afectados, sigue las dependencias entre ellos
   y los puntúa por relevancia.
3. **Validar la entidad.** Comprueba que la "cosa" que pide el
   requerimiento (ej. "usuario", "factura") realmente existe en el código.
   Si no existe, avisa antes de seguir.
4. **Generar la historia.** Produce descripción, criterios de aceptación,
   subtareas y riesgos, **citando los archivos reales** que tocará el
   desarrollo.
5. **Evaluar la calidad.** Un segundo modelo actúa como **juez
   independiente** y puntúa la historia en cinco dimensiones:
   completitud, especificidad, viabilidad, cobertura de riesgos y
   consistencia de idioma. Si la calidad es baja, se reintenta.

Todo esto ocurre en segundos, sin intervención humana, y con trazabilidad
completa de qué pasó en cada paso.

---

## 4. Diferenciadores vs. otras soluciones del mercado

| Capacidad | ChatGPT / Claude genéricos | Copilot / asistentes IDE | **BridgeAI** |
|---|---|---|---|
| Conoce el código del cliente | ❌ | Sí, por archivo abierto | **Sí, todo el repositorio indexado** |
| Genera historias listas para Jira/Azure | ❌ | ❌ | **Sí, publicación nativa** |
| Cita archivos reales del proyecto | ❌ | Limitado | **Sí, con whitelist auditada** |
| Califica la calidad del output | ❌ | ❌ | **Sí, con juez independiente** |
| Filtra basura antes de consumir tokens | ❌ Procesa cualquier input | ❌ | **Sí, capa heurística + LLM-gate pre-pipeline** |
| Multi-tenant con aislamiento estricto | N/A | N/A | **Sí, a nivel de base de datos** |
| Funciona con tu LLM preferido | Atado al proveedor | Atado al proveedor | **Anthropic, OpenAI, Groq, Gemini** |
| Garantía de no fuga de código | ❌ Sube tu código | Depende del IDE | **No envía el cuerpo del código al LLM** |

### 4.1 No alucinamos: citamos
Los modelos genéricos pueden inventar nombres de archivos, clases o
endpoints. BridgeAI restringe al modelo a **citar solo paths de una
whitelist** generada del repositorio real: si intenta inventarse un
archivo, la validación lo rechaza y reintenta. La historia que llega al
ticket no menciona nada que no exista en producción.

### 4.2 Confidencialidad de la propiedad intelectual 
La pregunta de oro de cualquier cliente: *"¿le mandan nuestro código a
OpenAI o Anthropic?"*. **No.** Solo viajan al LLM:

- nombres de archivos (`app/services/auth.py`),
- nombres de módulos impactados, y
- el texto que el propio cliente escribió.

**El cuerpo del código nunca sale del perímetro.** El sistema indexa el
repositorio localmente y extrae solo los *nombres* de los archivos
relevantes para orientar al modelo — no sus contenidos. Esto es un
diferenciador enorme frente a herramientas que suben fragmentos de código
"para tener contexto".

### 4.3 Aislamiento entre clientes y entre proyectos
Cada cliente (tenant) está aislado a nivel de base de datos: una consulta
sin contexto de tenant **falla**, no devuelve datos cruzados por error.
Dentro de un mismo cliente, un mismo usuario puede tener varios repos
conectados; los archivos, análisis e historias **nunca se mezclan entre
repos**.

### 4.4 Calidad medible y auditable
Cada historia generada lleva una nota del 0 al 10 con desglose por
dimensión. El cliente ve, en su dashboard, qué tan bien funciona la
herramienta para su realidad —no se queda en la promesa del demo. Si
algo se degrada (peor calidad, mayor dispersión), se ve.

### 4.5 Independencia de proveedor de IA
A diferencia de soluciones cerradas, BridgeAI permite cambiar el modelo
detrás (Claude, GPT, Gemini, Llama vía Groq) **sin tocar la
configuración del cliente**. Si mañana hay un modelo mejor o más barato,
se cambia con una variable de entorno. El cliente no queda atrapado.

### 4.6 Panorama del mercado por herramienta

Existen herramientas reconocidas que se solapan parcialmente con BridgeAI,
pero ninguna cubre el flujo completo: **requisito → impacto en el código
→ historia de usuario → ticket creado**.

| Herramienta | Qué hace bien | Qué le falta para ser BridgeAI |
|---|---|---|
| **GitHub Copilot Workspace** | Toma un issue existente y planifica cambios en el código | No genera historias de usuario; apunta al dev, no al PM; no integra con Jira/ADO |
| **Atlassian Intelligence** | Mejora y sugiere texto dentro de Jira | No analiza el codebase; parte de que el ticket ya existe |
| **Linear AI** | Enriquece descripciones de issues y sugiere etiquetas | No toca el código; no genera stories desde un requisito en crudo |
| **Cursor / Windsurf** | Asistente de código con contexto del repo abierto | No produce artefactos de PM; no integra con Jira/ADO; archivo por archivo |
| **Aha! + Jira** | Gestión de requisitos end-to-end con roadmaps | No analiza el código; no usa LLM para impact analysis; flujo manual |
| **CodeScene** | Analiza deuda técnica, hotspots y riesgo del codebase | No entiende requisitos en lenguaje natural; no genera stories ni tickets |

**El diferenciador real es el puente.** Cada herramienta de la tabla vive
en uno de los dos mundos —el mundo del PM (requisitos, stories, tickets)
o el mundo del código (qué archivos se ven afectados, qué dependencias
existen)—. BridgeAI existe exactamente en la intersección: recibe el
lenguaje del negocio y devuelve artefactos del negocio, pero toma las
decisiones con el conocimiento del código. Esa combinación no existe
como producto integrado en ninguna otra solución del mercado hoy.

---

## 5. Beneficios concretos para el negocio

- **Reducción de tiempo de análisis.** Lo que antes tomaba horas a un
  analista pasa a minutos. El equipo puede dedicar ese tiempo a
  conversaciones de producto, no a redacción de tickets.
- **Estandarización.** Todas las historias siguen el mismo formato, con
  criterios de aceptación testeables y subtareas concretas. Adiós a las
  historias que dicen *"hacer X mejor"*.
- **Menos retrabajo.** Como la historia se ancla al código real, hay
  menos sorpresas en el sprint: *"esto no se puede hacer así, falta tal
  cosa"* se detecta antes de planificar.
- **Visibilidad de calidad.** El dashboard expone tasas de aprobación,
  cobertura de criterios, dispersión del juez —insumos reales para
  mejorar el proceso, no marketing.
- **Onboarding más rápido.** Un nuevo PM no necesita saber dónde está
  cada cosa del código: la herramienta sí lo sabe.
- **Auditoría completa.** Cada llamada al LLM, cada historia generada,
  cada publicación a Jira queda registrada con `request_id`. Si algo
  falla, hay traza, no magia.

---

## 6. Casos de uso típicos

- **Producto sin BA dedicado** que necesita ritmo de descubrimiento sin
  contratar más analistas.
- **Equipos con deuda de tickets** acumulada que quieren ponerse al día
  con calidad consistente.
- **Empresas reguladas** (banca, salud, gobierno) que **no pueden** subir
  su código a herramientas externas, pero sí pueden permitir que la IA
  trabaje con metadata sin filtrar el contenido.
- **Consultoras** que entran a un proyecto nuevo y necesitan generar
  rápidamente el backlog inicial sin haber leído todavía el código.
- **Startups en crecimiento** que necesitan profesionalizar la disciplina
  de tickets sin invertir en herramientas pesadas tipo ALM tradicional.

---

## 7. Lo que el cliente sí tiene que hacer

Por transparencia: BridgeAI no es un botón mágico. Para que funcione el
cliente debe:

1. **Conectar su repo** vía OAuth o token (proceso guiado, ~3 minutos).
2. **Esperar la indexación inicial** (depende del tamaño del repo;
   típicamente minutos).
3. **Conectar Jira o Azure DevOps** si quiere publicación automática.
4. **Validar las primeras historias** para calibrar el resultado (la
   calificación del juez ayuda a saber dónde mirar).

Después, el flujo es: pegar el requerimiento, revisar la historia, un
clic y al ticket.

---

## 8. Segmentación de mercado y viabilidad

### 8.1 Segmento principal: mid-market

**Perfil:** empresas de 50–500 personas, 2–10 PMs, que ya usan
Jira o Azure DevOps y tienen sus repos en GitHub, GitLab, Azure Repos
o Bitbucket.

**Por qué es el foco:** sienten el dolor (sin BAs dedicados, tickets
inconsistentes, PMs desbordados), tienen presupuesto para herramientas
SaaS, y sus ciclos de compra son manejables — sin procurement de seis
meses ni comités de seguridad de diez personas.

**Probabilidad estimada de PMF:** 65–70 %, asumiendo que el producto
entrega calidad consistente en los primeros 30 días de uso.

### 8.2 Segmento secundario: enterprise regulado

**Perfil:** banca, salud, gobierno, defensa — sectores donde las
políticas de seguridad impiden usar herramientas que envían código a
proveedores externos de IA.

**Por qué es una oportunidad real:** el argumento de "el código nunca
sale del perímetro" es estructuralmente irreplicable por los incumbentes
(Atlassian Intelligence, GitHub Copilot) mientras operen como SaaS
multi-tenant. Esas empresas *no pueden* usar esas herramientas aunque
quisieran.

**Requisito para cerrar este segmento:** certificaciones de seguridad
(SOC2 Type II, ISO 27001) y opción de deployment on-prem o VPC privada.
Sin esto, la conversación nunca pasa del área de TI al área de compras.

**Probabilidad estimada de PMF:** 30–40 %. Alta recompensa, pero ciclo
de venta de 6–18 meses y alta inversión previa en compliance.

### 8.3 Segmento descartable como motor de revenue: startups pequeñas

**Perfil:** equipos de menos de 20 personas, repos chicos, procesos de
PM informales.

**Por qué no es el foco:** adoptan rápido pero pagan poco o nada,
prefieren pedirle lo mismo a ChatGPT, y el análisis de impacto aporta
menos valor en codebases pequeñas. Son útiles para tracción inicial y
testimonios, no para revenue sostenible.

**Probabilidad estimada de PMF:** 20–25 %.

### 8.4 Resumen de segmentos

| Segmento | Potencial de revenue | Dificultad de venta | Recomendación |
|---|---|---|---|
| Mid-market (50–500 empl.) | Alto | Media | **Foco principal** |
| Enterprise regulado (banca, salud, gobierno) | Muy alto | Alta | **Apuesta secundaria con inversión en compliance** |
| Startups pequeñas | Bajo | Baja | Solo para validación y testimonios |

### 8.5 Principal riesgo de viabilidad: absorción por incumbentes

El riesgo mayor no es técnico, es competitivo. Atlassian, GitHub o
Linear podrían lanzar una feature similar como parte de sus productos
en 12–18 meses. Ya tienen los repos, los tickets y los LLMs integrados.
BridgeAI compite indirectamente contra el roadmap de compañías de miles
de millones de dólares.

Las tres defensas concretas contra ese riesgo:

1. **Velocidad de distribución.** Llegar a suficientes clientes pagos
   antes de que los incumbentes lleguen. El go-to-market es tan crítico
   como el producto.
2. **Profundidad técnica.** El análisis de código basado en AST y la
   arquitectura RAG léxico-estructural son más difíciles de replicar
   rápido que una feature de "mejorar descripción con IA". La superficie
   copiable es menor de lo que parece.
3. **El nicho regulado.** Empresas que estructuralmente no pueden usar
   las herramientas de los incumbentes por compliance son impermeables a
   esa competencia. Es el segmento donde BridgeAI no tiene sustituto.

### 8.6 Modelo de go-to-market recomendado

1. **Fase 1 (0–6 meses):** cerrar 10–20 clientes mid-market con
   onboarding guiado. Objetivo: validar que la calidad del output
   sostiene la retención mes a mes. Priorizar recomendaciones de boca en
   boca dentro de comunidades de producto (Product Hunt, comunidades de
   PMs en LATAM/USA).
2. **Fase 2 (6–18 meses):** iniciar conversaciones enterprise con el
   diferenciador de compliance. Paralelamente, obtener SOC2 Type II.
   Construir casos de estudio de fase 1 como credenciales.
3. **Fase 3 (18+ meses):** canal de partners — consultoras que entran a
   proyectos nuevos y necesitan generar backlog inicial son el vendedor
   natural del producto sin costo marginal de adquisición.

---

## 9. Modelo de precios y planes

### 8.1 El valor que se cobra

Un PM o BA en LATAM cobra ~$15–30/hora; en USA ~$50–80/hora. Escribir
una historia con análisis de código toma entre 45 y 90 minutos. BridgeAI
lo hace en segundos. Si un equipo genera 40 historias al mes, el ahorro
estimado es:

- **LATAM:** ~$600–1,800/mes de tiempo PM recuperado.
- **USA:** ~$2,000–4,800/mes de tiempo PM recuperado.

Incluso en el plan más caro, el ROI es inmediato y cuantificable. Eso es
lo que justifica el precio frente a "otra herramienta SaaS".

### 8.2 Modelo: por workspace + límite de historias

BridgeAI **no cobra por asiento**. Las razones:

- Dos PMs pueden generar 200 historias/mes (mucho valor) o 10 (poco
  valor); el seat no captura esa diferencia.
- "X por mes para todo tu equipo" es más fácil de aprobar que "X por
  usuario".
- El límite de historias crea un upgrade natural sin fricción artificial.

Las historias extra sobre el límite se cobran como overage (~$2–5 c/u);
**nunca se bloquean**. Bloquear genera churn; el overage genera expansion
revenue.

### 8.3 Planes — mercado LATAM

| Plan | Precio/mes | Repos | Historias/mes | Usuarios | Integraciones |
|---|---|---|---|---|---|
| **Starter** | $79 | 1 | 30 | 3 | Jira o ADO |
| **Growth** | $199 | 3 | 150 | 10 | Jira + ADO |
| **Business** | $499 | Ilimitado | 500 | Ilimitado | Todo |
| **Enterprise** | A consultar | Ilimitado | Ilimitado | Ilimitado | On-prem / VPC |

### 8.4 Planes — mercado USA / global

| Plan | Precio/mes | Repos | Historias/mes | Usuarios | Integraciones |
|---|---|---|---|---|---|
| **Starter** | $149 | 1 | 30 | 3 | Jira o ADO |
| **Growth** | $399 | 3 | 150 | 10 | Jira + ADO |
| **Business** | $999 | Ilimitado | 500 | Ilimitado | Todo |
| **Enterprise** | $2,500+ | Ilimitado | Ilimitado | Ilimitado | On-prem / VPC |

**Descuento anual:** 20–25 % sobre el precio mensual (mejora cashflow y
reduce churn). **Trial:** 14 días gratis, límite de 10 historias, sin
tarjeta requerida.

### 8.5 El plan que mueve el negocio

**Growth es el caballo de batalla.** Equipos de 5–15 personas con 2–3
PMs activos que ya usan Jira pueden aprobar $200/mes sin pasar por
procurement. Ese es el perfil que convierte, paga y renueva.

**Growth → Business** es la palanca de expansión: cuando el equipo crece
y el límite duele, el upgrade es la solución natural.

**Enterprise** es el plan de largo plazo. El argumento de compliance
regulado (banca, salud, gobierno) justifica tickets de $2,000–8,000/mes,
pero el ciclo de venta es más largo y requiere inversión en
certificaciones (SOC2, ISO 27001) y opción de deployment on-prem o VPC
privada.

### 8.6 Nota para go-to-market en LATAM

Si el mercado primario es LATAM, los precios en dólares pueden generar
fricción en algunos países. Se recomienda billing en dólares con
pasarelas locales (Stripe soporta esto), o una variante LATAM al 60 %
del precio USD con onboarding completamente en español. Si el target
desde el inicio es USA, esta consideración no aplica.

---

## 10. Cierre — la idea en una frase

> **BridgeAI convierte el "tenemos que hacer X" del cliente en una
> historia de usuario aterrizada al código real, con calidad medida y
> publicada como ticket — sin que el código del cliente salga nunca
> hacia la IA.**

Es una IA que **filtra antes de procesar**, **investiga antes de hablar**,
**cita en lugar de inventar**, y **se calla cuando no está segura**. Esa
es la diferencia con todo lo demás que hay en el mercado.

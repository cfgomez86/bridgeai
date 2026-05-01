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

> **En palabras simples:** otras IAs leen el requerimiento y "se inventan"
> la solución. BridgeAI primero **investiga el repositorio del cliente**
> —qué archivos están en juego, qué entidades existen, qué se vería
> afectado—, y solo entonces le pide al modelo que escriba la historia.
> El resultado es una historia anclada a la realidad del proyecto, no un
> texto genérico bonito.

### El pipeline en 5 pasos (sin tecnicismos)

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
- nombres de clases y funciones (`AuthService`, `validate_token`), y
- el texto que el propio cliente escribió.

**El cuerpo del código nunca sale del perímetro.** Esto es un
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

## 8. Cierre — la idea en una frase

> **BridgeAI convierte el "tenemos que hacer X" del cliente en una
> historia de usuario aterrizada al código real, con calidad medida y
> publicada como ticket — sin que el código del cliente salga nunca
> hacia la IA.**

Es una IA que **investiga antes de hablar**, **cita en lugar de
inventar**, y **se calla cuando no está segura**. Esa es la diferencia
con todo lo demás que hay en el mercado.

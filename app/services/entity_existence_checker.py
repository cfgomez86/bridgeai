from dataclasses import dataclass

from app.repositories.code_file_repository import CodeFileRepository
from app.services.dependency_analyzer import DependencyAnalyzer

_LANGUAGE_EQUIVALENCES = {
    "producto": "product",
    "usuario": "user",
    "pedido": "order",
    "factura": "invoice",
    "cliente": "customer",
    "categoria": "category",
    "categoría": "category",
    "pago": "payment",
    "carrito": "cart",
    "envio": "shipping",
    "envío": "shipping",
    "direccion": "address",
    "dirección": "address",
    "comentario": "comment",
    "valoracion": "rating",
    "valoración": "rating",
    "rol": "role",
    "permiso": "permission",
    "tarea": "task",
    "proyecto": "project",
    "equipo": "team",
    "historia": "story",
    "requerimiento": "requirement",
    "tiquet": "ticket",
    "tique": "ticket",
    "boleto": "ticket",
    "formulario": "form",
    "pantalla": "screen",
    "página": "page",
    "pagina": "page",
}

_GENERIC_ENTITIES = {
    "system", "sistema", "data", "datos", "feature", "field", "campo",
    "info", "module", "modulo", "módulo", "app", "application", "aplicacion",
    "code", "codigo", "código", "function", "funcion", "función",
    "method", "metodo", "método", "class", "clase", "object", "objeto",
    # Meta-domain terms that describe the app itself (BridgeAI surfaces stories,
    # requirements, tickets, forms and screens as first-class concepts) — they
    # are not entities the indexed business code is expected to expose as classes.
    "story", "user_story", "userstory", "historia",
    "requirement", "requerimiento",
    "ticket", "tiquet", "tique", "boleto",
    "form", "formulario", "screen", "pantalla", "page", "página", "pagina",
    "detail", "detalle", "details", "detalles",
    "settings", "ajustes", "preferences", "preferencias",
}


@dataclass(frozen=True)
class EntityCheckResult:
    entity: str
    found: bool
    matched_files: list[str]
    suggestions: list[str]


class EntityNotFoundError(Exception):
    def __init__(self, entity: str, suggestions: list[str]) -> None:
        super().__init__(f"Entity '{entity}' not found in the indexed codebase.")
        self.entity = entity
        self.suggestions = suggestions


class EntityExistenceChecker:
    def __init__(
        self,
        code_file_repo: CodeFileRepository,
        analyzer: DependencyAnalyzer,
    ) -> None:
        self._code_file_repo = code_file_repo
        self._analyzer = analyzer

    def check(self, entity: str, source_connection_id: str) -> EntityCheckResult:
        norm = (entity or "").lower().strip()
        if not norm or norm in _GENERIC_ENTITIES:
            return EntityCheckResult(
                entity=entity, found=True, matched_files=[], suggestions=[]
            )

        variants = self._build_variants(norm)
        matched_files: list[str] = []
        all_classes: set[str] = set()

        for cf in self._code_file_repo.list_all(source_connection_id):
            if not cf.content:
                continue
            fa = self._analyzer.analyze(
                cf.file_path, cf.content, cf.language, source_connection_id
            )
            file_matched = False
            for cls in fa.classes:
                all_classes.add(cls)
                if not file_matched and self._cls_matches(cls, variants):
                    matched_files.append(cf.file_path)
                    file_matched = True

        if matched_files:
            return EntityCheckResult(
                entity=entity, found=True,
                matched_files=matched_files, suggestions=[],
            )

        suggestions = self._find_suggestions(norm, all_classes, top_n=5)
        return EntityCheckResult(
            entity=entity, found=False,
            matched_files=[], suggestions=suggestions,
        )

    @staticmethod
    def _build_variants(norm: str) -> set[str]:
        variants = {norm}
        if norm in _LANGUAGE_EQUIVALENCES:
            variants.add(_LANGUAGE_EQUIVALENCES[norm])
        for es, en in _LANGUAGE_EQUIVALENCES.items():
            if en == norm:
                variants.add(es)
        return variants

    @staticmethod
    def _cls_matches(cls: str, variants: set[str]) -> bool:
        cls_lower = cls.lower()
        for v in variants:
            v_norm = v.replace("_", "")
            if not v_norm:
                continue
            if cls_lower == v_norm:
                return True
            if (
                cls_lower.startswith(v_norm)
                and len(cls) > len(v_norm)
                and cls[len(v_norm)].isupper()
            ):
                return True
        return False

    @staticmethod
    def _find_suggestions(
        norm: str, all_classes: set[str], top_n: int
    ) -> list[str]:
        scored: list[tuple[int, str]] = []
        for cls in all_classes:
            cls_lower = cls.lower()
            common = 0
            for a, b in zip(norm, cls_lower):
                if a == b:
                    common += 1
                else:
                    break
            score = common
            if norm in cls_lower or cls_lower in norm:
                score += 5
            if score >= 3:
                scored.append((score, cls))
        scored.sort(key=lambda x: (-x[0], x[1]))
        seen: set[str] = set()
        result: list[str] = []
        for _, cls in scored:
            if cls in seen:
                continue
            seen.add(cls)
            result.append(cls)
            if len(result) >= top_n:
                break
        return result

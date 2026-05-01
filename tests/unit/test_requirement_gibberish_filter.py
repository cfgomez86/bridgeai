import pytest

from app.services.requirement_gibberish_filter import is_gibberish


@pytest.mark.parametrize(
    "text",
    [
        "sddssddssdsdd dsffdgdfggfdg fgdgdfgfdg fdgdhfgh ghgfhfhgf gff",
        "fghfgh ghgfhfhgf gfdgfdg",
        "asdfgh qwerty zxcvbn",
        "324234 2342423 54654 675675676556765777uyjhgjghjgjtyu jghjghj",
        "343434343434343x43c 5545tttryrtyrtyrtytyrty tytrytyrtytyt rtytry",
        "dddddd ggggg ffffff",
        "dsdsds bgbgbg fdfdfd",
    ],
)
def test_detects_gibberish(text):
    assert is_gibberish(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "quiero agregar un campo de detalles tecnicos a la historia",
        "Add password reset feature",
        "agregar endpoint POST /users con validación JWT",
        "refactorizar el módulo de auth",
        "El usuario debe registrarse con email",
        "necesito mejorar la experiencia del checkout",
        "quiero algo bonito",
        "qiero agregar la opcion de poder colaborar",  # typos legítimos
    ],
)
def test_accepts_valid_text(text):
    assert is_gibberish(text) is False


def test_short_text_not_flagged():
    """Texto con pocas palabras largas no debe rechazarse — el LLM se encarga."""
    assert is_gibberish("hi") is False
    assert is_gibberish("ok") is False
    assert is_gibberish("hola") is False


def test_empty_or_whitespace():
    assert is_gibberish("") is False
    assert is_gibberish("   ") is False


def test_mixed_short_words_pass():
    """Cuando casi todas las palabras son cortas (< 4 chars), no se evalúa."""
    assert is_gibberish("a b c de el la lo un") is False


def test_alphanumeric_token_is_gibberish():
    """Mezclas tipo `343434343434343x43c` son siempre gibberish."""
    assert is_gibberish("foo bar 343434x43c another") is False  # 1/4 → no rechaza
    assert is_gibberish("343434x43c 5545tttry tytrytyr") is True


def test_majority_threshold():
    """Si una sola palabra es válida y tres son basura, rechaza."""
    assert is_gibberish("quiero fghfgh dsdsds ggggggg") is True


def test_long_repeated_letter_word():
    assert is_gibberish("hello fdddddddddd world things") is False  # 1/4
    assert is_gibberish("fdddddddddd dsdsds ggggg") is True


@pytest.mark.parametrize(
    "text",
    [
        # Identificador con underscores repetido — caso reportado en producción.
        "ai_requirement_parser ai_requirement_parser ai_requirement_parser",
        # Spam por copy-paste de palabra real.
        "agregar agregar agregar agregar agregar feature",
        # Repetición de frase corta.
        "spam spam spam spam spam",
        # Mayúsculas/minúsculas mezcladas — el match es case-insensitive.
        "Endpoint endpoint ENDPOINT endpoint",
    ],
)
def test_detects_dominant_repeated_token(text):
    assert is_gibberish(text) is True


@pytest.mark.parametrize(
    "text",
    [
        # Repetición legítima: tres endpoints distintos.
        "Crear endpoint /users. Crear endpoint /products. Crear endpoint /orders",
        # Énfasis puntual — solo dos repeticiones.
        "el usuario quiere quiere comprar productos online",
        # Texto normal con sustantivos comunes.
        "el usuario debe poder agregar usuarios al sistema y eliminar usuarios",
    ],
)
def test_repetition_does_not_flag_legitimate_text(text):
    assert is_gibberish(text) is False


@pytest.mark.parametrize(
    "text",
    [
        # Caso reportado: dos identificadores snake_case alternados, 2x cada uno.
        "ai_requirement_parser reason_codes ai_requirement_parser reason_codes",
        # Lo mismo en camelCase.
        "aiRequirementParser reasonCodes aiRequirementParser reasonCodes",
        # CONSTANT_CASE repetido.
        "API_KEY DATABASE_URL API_KEY DATABASE_URL",
        # Mezcla snake/camel sin diversidad.
        "user_id userId user_id userId user_id",
    ],
)
def test_detects_pasted_identifiers(text):
    assert is_gibberish(text) is True


@pytest.mark.parametrize(
    "text",
    [
        # Lista de funciones distintas — diversidad alta, no es spam.
        "create_user delete_user update_user list_users get_user_by_id",
        # Identificadores en lenguaje natural — la mayoría no son techy.
        "Agregar campo user_id a la tabla orders y validar el DNI",
        "Necesito que API_KEY se valide cuando llega al endpoint",
        # snake_case con conectores naturales abundantes.
        "El servicio user_service debe llamar a order_service cuando recibe un pedido nuevo",
    ],
)
def test_techy_identifiers_with_diversity_or_natural_text_pass(text):
    assert is_gibberish(text) is False

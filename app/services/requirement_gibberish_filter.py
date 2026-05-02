"""Determinístico: descarta texto basura sin gastar tokens del juez LLM.

Captura los casos típicos en los que gemini-2.5-flash deja pasar como
coherente texto random (`sddssddssdsdd`, `fghfgh ghgfhfhgf`, `343434343434`).
Diseñado conservadoramente para NO rechazar requisitos legítimos cortos o
con jerga técnica — la decisión final del juez sigue siendo el LLM.
"""
import re
from collections import Counter

_VOWELS = set("aeiouáéíóúüy")
_MIN_WORD_LEN = 4
_MIN_GIBBERISH_RATIO = 0.6
_MIN_TEXT_WORDS = 2

_VOWEL_RATIO_LOW = 0.20
_VOWEL_RATIO_HIGH = 0.85
_DOMINANT_LETTER_RATIO = 0.6
_DOMINANT_BIGRAM_RATIO = 0.45
_LOW_DIVERSITY_LEN = 8
_LOW_DIVERSITY_UNIQUE_MAX = 4

_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")
# Para la detección de repetición conservamos identificadores enteros con `_`,
# así "ai_requirement_parser" cuenta como un solo token y permite detectar el
# spam por copy-paste ("foo_bar foo_bar foo_bar").
_REPETITION_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+")
_MIN_REPETITIONS = 3
_REPETITION_RATIO = 0.7

# Detección de "código pegado": tokens snake_case (`user_id`) o camelCase
# (`userId`) son señales de identificadores técnicos. Si la mayoría del texto
# son identificadores Y la diversidad es baja, no es lenguaje natural.
_CAMEL_CASE_RE = re.compile(r"[a-z][A-Z]")
_TECHY_TOKEN_MIN = 3
_TECHY_TOKEN_RATIO = 0.7
_TECHY_DIVERSITY_RATIO = 0.7


def _word_is_gibberish(word: str) -> bool:
    lower = word.lower()
    length = len(lower)
    if length < _MIN_WORD_LEN:
        return False

    if lower.isdigit():
        return length >= 5

    if any(ch.isdigit() for ch in lower) and any(ch.isalpha() for ch in lower):
        # Flag tokens with >=4 alternating alpha/digit segments (truly interspersed
        # gibberish like a1b2c3d4). Allow tokens with only 2 segments — these are
        # legitimate tech patterns: oauth2, sha256, ipv4, utf8, base64, s3bucket,
        # ec2instance (letters+digits or digits+letters).
        # Tokens with 2 segments still fall through to vowel/diversity checks below,
        # so e.g. "5545tttrtrtrtrtrt" is caught by the low-diversity rule.
        parts = re.findall(r"[a-z]+|\d+", lower)
        if len(parts) >= 4:
            return True
        # fall through to letter-quality checks

    letters = [c for c in lower if c.isalpha()]
    if not letters:
        return False

    vowels = sum(1 for c in letters if c in _VOWELS)
    vowel_ratio = vowels / len(letters)
    if vowel_ratio < _VOWEL_RATIO_LOW or vowel_ratio > _VOWEL_RATIO_HIGH:
        return True

    counts = Counter(letters)
    if counts.most_common(1)[0][1] / len(letters) >= _DOMINANT_LETTER_RATIO:
        return True

    # Palabras largas con muy pocas letras distintas son casi siempre teclazos
    # tipo `tytrytyrtytyt`. El umbral (>=8 chars, <=4 letras únicas) deja pasar
    # palabras reales como `endpoint`, `connection`, `requirement`.
    if length >= _LOW_DIVERSITY_LEN and len(counts) <= _LOW_DIVERSITY_UNIQUE_MAX:
        return True

    if length >= 6:
        bigrams = [lower[i : i + 2] for i in range(length - 1)]
        if bigrams:
            top = Counter(bigrams).most_common(1)[0][1]
            if top / len(bigrams) >= _DOMINANT_BIGRAM_RATIO:
                return True

    return False


def _has_dominant_repeated_token(text: str) -> bool:
    """Spam por repetición: el mismo identificador aparece >= 3 veces y
    representa >= 70% de los tokens largos. Atrapa casos como
    `ai_requirement_parser ai_requirement_parser ai_requirement_parser`,
    que no son letras random y por eso no caen en `_word_is_gibberish`."""
    tokens = _REPETITION_TOKEN_RE.findall(text)
    long_tokens = [t.lower() for t in tokens if len(t) >= _MIN_WORD_LEN]
    if len(long_tokens) < _MIN_REPETITIONS:
        return False
    most_common_count = Counter(long_tokens).most_common(1)[0][1]
    if most_common_count < _MIN_REPETITIONS:
        return False
    return most_common_count / len(long_tokens) >= _REPETITION_RATIO


def _is_techy_identifier(token: str) -> bool:
    """snake_case (`user_id`), CONSTANT_CASE (`API_KEY`) o camelCase (`userId`)."""
    return "_" in token or bool(_CAMEL_CASE_RE.search(token))


def _looks_like_pasted_identifiers(text: str) -> bool:
    """Texto compuesto casi exclusivamente por identificadores técnicos sin
    lenguaje natural. Atrapa pares como
    `ai_requirement_parser reason_codes ai_requirement_parser reason_codes`
    (cada uno aparece solo 2 veces, así que `_has_dominant_repeated_token` no
    los marca, pero el conjunto es claramente código pegado).

    Combina dos señales para evitar falsos positivos:
      - >= 70% de los tokens largos son snake_case/camelCase/CONSTANT_CASE.
      - Diversidad < 70% (los mismos pocos identificadores se repiten).
    Una lista legítima como `create_user delete_user update_user list_users
    get_user_by_id` queda exenta porque la diversidad es 100%.
    """
    tokens = _REPETITION_TOKEN_RE.findall(text)
    long_tokens = [t for t in tokens if len(t) >= _MIN_WORD_LEN]
    if len(long_tokens) < _TECHY_TOKEN_MIN:
        return False
    techy = sum(1 for t in long_tokens if _is_techy_identifier(t))
    if techy / len(long_tokens) < _TECHY_TOKEN_RATIO:
        return False
    unique = len({t.lower() for t in long_tokens})
    return unique / len(long_tokens) < _TECHY_DIVERSITY_RATIO


def is_gibberish(text: str) -> bool:
    """Heurística rápida: ¿el texto está formado mayormente por palabras random?

    Devuelve True solo si una mayoría clara de palabras "largas" (>= 4 chars)
    son gibberish. Texto en español/inglés normal pasa sin problema porque
    sus vocales caen en [0.30, 0.55] y sus letras tienen variedad.
    """
    if not text or not text.strip():
        return False

    if _has_dominant_repeated_token(text):
        return True

    if _looks_like_pasted_identifiers(text):
        return True

    tokens = _TOKEN_RE.findall(text)
    long_tokens = [t for t in tokens if len(t) >= _MIN_WORD_LEN]
    if len(long_tokens) < _MIN_TEXT_WORDS:
        return False

    gibberish = sum(1 for t in long_tokens if _word_is_gibberish(t))
    return gibberish / len(long_tokens) >= _MIN_GIBBERISH_RATIO

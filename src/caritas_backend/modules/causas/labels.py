"""Clave y nombre corto de una causa, derivados del titulo.

No se guardan en la base: se calculan en cada respuesta para que la app de
administracion tenga una etiqueta corta ("CO", "Comedor") sin columnas nuevas.
"""

import string
import unicodedata

# Se comparan ya sin acentos y en minusculas.
STOPWORDS = frozenset(
    {"a", "al", "con", "de", "del", "el", "en", "la", "las", "los", "para", "por", "y"}
)

NOMBRE_CORTO_MAX = 20

# Ademas de la puntuacion ASCII, los signos de apertura del espanol.
PUNCTUATION = string.punctuation + "¡¿«»“”"


def fold(text: str) -> str:
    """'Campaña' -> 'campana': sin acentos y en minusculas."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).lower()


def words(titulo: str) -> list[str]:
    """Palabras del titulo sin la puntuacion de los extremos ('invierno:')."""
    cleaned = (word.strip(PUNCTUATION) for word in titulo.split())
    return [word for word in cleaned if word]


def is_significant(word: str) -> bool:
    return fold(word) not in STOPWORDS


def build_clave(titulo: str) -> str:
    """Iniciales de las 2 primeras palabras significativas que empiezan con letra.

    Con una sola palabra usa sus 2 primeras letras. No es unica.
    """
    candidates = [
        word for word in words(titulo) if is_significant(word) and word[0].isalpha()
    ]
    if len(candidates) >= 2:
        letters = candidates[0][0] + candidates[1][0]
    elif candidates:
        letters = "".join(char for char in candidates[0] if char.isalpha())[:2]
    else:
        letters = "".join(char for char in titulo if char.isalnum())[:2]
    return fold(letters).upper()


def build_nombre_corto(titulo: str) -> str:
    """Titulo hasta la 2a palabra significativa, si cabe en NOMBRE_CORTO_MAX.

    Conserva los conectores de en medio ("Campaña de invierno"). Si no cabe se
    queda con la primera palabra significativa entera: nunca corta una palabra.
    """
    title_words = words(titulo)
    significant = [i for i, word in enumerate(title_words) if is_significant(word)]
    if not significant:
        return " ".join(title_words)

    first = significant[0]
    if len(significant) >= 2:
        two_words = " ".join(title_words[first : significant[1] + 1])
        if len(two_words) <= NOMBRE_CORTO_MAX:
            return two_words
    return title_words[first]


def with_labels(causa: dict) -> dict:
    return {
        **causa,
        "clave": build_clave(causa["titulo"]),
        "nombre_corto": build_nombre_corto(causa["titulo"]),
    }

# engine/classifier.py
"""Genre classification engine. Priority: Tools → Locale → Core → Classics → INBOX."""
import unicodedata
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from .keywords import GENRE_KEYWORDS
from .genres import CORE_GENRES, LOCALE_GENRES

@dataclass
class ClassificationResult:
    genre: str
    rule: str

def detect_locale(text: str) -> Optional[str]:
    """Detect locale genre from Unicode characters in text."""
    for char in text:
        cat = unicodedata.category(char)
        if cat.startswith('L'):  # Letter characters only
            try:
                name = unicodedata.name(char, '')
            except ValueError:
                continue
            # Hebrew
            if 'HEBREW' in name:
                return "israeli"
            # Arabic
            if 'ARABIC' in name:
                return "arabic"
            # Cyrillic
            if 'CYRILLIC' in name:
                return "russian"
            # Korean (Hangul)
            if 'HANGUL' in name or 'KOREAN' in name:
                return "kpop"
            # Japanese (Katakana, Hiragana, CJK with Japanese context)
            if 'KATAKANA' in name or 'HIRAGANA' in name:
                return "jpop"
            # Devanagari (Hindi)
            if 'DEVANAGARI' in name:
                return "bollywood"
            # Turkish-specific characters
            if char in 'ğşıİĞŞ':
                return "turkish"
    return None

def _has_old_year(name_lower: str) -> bool:
    """Check if filename contains a pre-2000 year (matches 1900-1999 pattern)."""
    import re
    match = re.search(r'\b(19\d{2})\b', name_lower)
    return match is not None

def classify_file(filepath: Path) -> ClassificationResult:
    """Classify a single file. Priority: Tools → Locale → Core → Classics → INBOX."""
    name = filepath.name
    name_lower = unicodedata.normalize('NFC', name).lower()

    # 1. Tools & FX — checked first
    for kw in GENRE_KEYWORDS.get("tools", []):
        if kw.lower() in name_lower:
            return ClassificationResult("tools", f"Tool/FX keyword: '{kw}'")

    # 2. Locale detection — character-based
    locale = detect_locale(name)
    if locale:
        return ClassificationResult(locale, f"Locale detected: {locale} characters")

    # 3. Core genre keywords — first match wins
    for genre_key, keywords in GENRE_KEYWORDS.items():
        if genre_key == "tools":
            continue  # already checked
        for kw in keywords:
            if kw.lower() in name_lower:
                return ClassificationResult(genre_key, f"Keyword: '{kw}'")

    # 4. Classics fallback — year pre-2000, only when no genre keywords matched
    if _has_old_year(name_lower):
        return ClassificationResult("classics", "Year pre-2000 in filename")

    # 5. INBOX — unclassified
    return ClassificationResult("inbox", "No match — manual review needed")

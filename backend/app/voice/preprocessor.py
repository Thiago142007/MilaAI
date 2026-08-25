import re
import unicodedata


class TextPreprocessor:
    """Cleans and prepares input text for natural speech synthesis."""

    # Regex patterns
    CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    INLINE_CODE_RE = re.compile(r"`([^`]+)`")
    MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
    URL_RE = re.compile(r"https?://\S+|www\.\S+")
    MARKDOWN_FORMAT_RE = re.compile(r"[*_~#>`|]")
    MULTIPLE_SPACES_RE = re.compile(r"\s+")
    MULTIPLE_PUNCT_RE = re.compile(r"([!?.,])\1+")
    
    # Strip emojis and non-BMP symbols that cause issues in TTS/phonemizer
    EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    SPECIAL_SYMBOLS_RE = re.compile(r"[\u2600-\u27bf\u2b50\ufe0f\u200d\u20e3\u2190-\u21ff]")

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Preprocess text for TTS engine."""
        if not text:
            return ""

        # 1. Remove markdown code blocks
        cleaned = cls.CODE_BLOCK_RE.sub(" ", text)

        # 2. Extract link text
        cleaned = cls.MARKDOWN_LINK_RE.sub(r"\1", cleaned)

        # 3. Simplify inline code
        cleaned = cls.INLINE_CODE_RE.sub(r"\1", cleaned)

        # 4. Remove raw URLs
        cleaned = cls.URL_RE.sub("link", cleaned)

        # 5. Remove markdown symbols (*, _, ~, #, >, `, |)
        cleaned = cls.MARKDOWN_FORMAT_RE.sub(" ", cleaned)

        # 6. Strip emojis and special pictograms
        cleaned = cls.EMOJI_RE.sub(" ", cleaned)
        cleaned = cls.SPECIAL_SYMBOLS_RE.sub(" ", cleaned)

        # 7. Normalize repeated punctuation (e.g. "!!!" -> "!", "..." -> "...")
        cleaned = cls.MULTIPLE_PUNCT_RE.sub(r"\1", cleaned)

        # 8. Normalize spaces and strip
        cleaned = cls.MULTIPLE_SPACES_RE.sub(" ", cleaned).strip()

        return cleaned

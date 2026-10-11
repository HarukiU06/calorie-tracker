import html
import re

# Characters with meaning in Streamlit's markdown renderer (button labels, st.success, ...)
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~:$])")


def esc(value: object) -> str:
    """Escape text for interpolation into HTML rendered with unsafe_allow_html."""
    return html.escape(str(value), quote=True)


def md_escape(value: object) -> str:
    """Escape text so Streamlit renders it literally instead of as markdown."""
    return _MD_SPECIAL.sub(r"\\\1", str(value))

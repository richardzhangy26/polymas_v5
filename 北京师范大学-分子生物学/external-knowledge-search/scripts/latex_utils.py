"""
latex_utils.py — LaTeX → Unicode 符号转换

将简单 LaTeX 数学表达式（下标/上标）转为 Unicode 字符，
适用于 AI 课程中的公式在纯文本环境下的可读性优化。
"""

import re

# ==================== 映射表 ====================

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
}

SUBSCRIPT_LETTER_MAP = {
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'h': 'ₕ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ',
    's': 'ₛ', 't': 'ₜ',
}

SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
}

SUPERSCRIPT_LETTER_MAP = {
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
}


def _to_subscript(char):
    return SUBSCRIPT_MAP.get(char) or SUBSCRIPT_LETTER_MAP.get(char) or char


def _to_superscript(char):
    return SUPERSCRIPT_MAP.get(char) or SUPERSCRIPT_LETTER_MAP.get(char) or char


def convert_latex_to_unicode(text):
    """将简单 LaTeX 下标/上标转为 Unicode

    支持的模式：
      $Base_{sub}$  → Base + 下标字符
      $Base^{sup}$  → Base + 上标字符
      $Base_x$      → Base + 单字符下标
      $Base^x$      → Base + 单字符上标
    """
    if not text:
        return text

    # Pattern 1: $Base_{sub}$
    text = re.sub(
        r'\$([A-Za-z]+)\s*_\s*\{\s*([^}]+?)\s*\}\$',
        lambda m: m.group(1) + ''.join(_to_subscript(c) for c in m.group(2).strip()),
        text,
    )

    # Pattern 2: $Base^{sup}$
    text = re.sub(
        r'\$([A-Za-z]+)\s*\^\s*\{\s*([^}]+?)\s*\}\$',
        lambda m: m.group(1) + ''.join(_to_superscript(c) for c in m.group(2).strip()),
        text,
    )

    # Pattern 3: $Base_x$ (单字符下标)
    text = re.sub(
        r'\$([A-Za-z]+)\s*_\s*([A-Za-z0-9])\$',
        lambda m: m.group(1) + _to_subscript(m.group(2)),
        text,
    )

    # Pattern 4: $Base^x$ (单字符上标)
    text = re.sub(
        r'\$([A-Za-z]+)\s*\^\s*([A-Za-z0-9])\$',
        lambda m: m.group(1) + _to_superscript(m.group(2)),
        text,
    )

    return text

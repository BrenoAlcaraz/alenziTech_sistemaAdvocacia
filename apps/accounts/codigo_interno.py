import re


def numero_do_codigo(termo, prefixo):
    """Número do código interno quando `termo` é exatamente
    `<prefixo><número>` (maiúsculas ou minúsculas, ex.: "p12"); senão None.
    Número sem prefixo nunca é tratado como código."""
    correspondencia = re.fullmatch(rf"{prefixo}(\d+)", (termo or "").strip(), re.IGNORECASE)
    return int(correspondencia.group(1)) if correspondencia else None


def codigo_usuario(usuario):
    """Código interno do usuário ("U3" ou "ADM"); vazio sem perfil."""
    perfil = getattr(usuario, "perfil", None)
    return perfil.codigo if perfil else ""


def rotulo_usuario(usuario):
    """Rótulo padrão de usuário em seletores: "U3 · Nome (@username)"."""
    nome = usuario.get_full_name()
    rotulo = f"{nome} (@{usuario.username})" if nome else f"@{usuario.username}"
    codigo = codigo_usuario(usuario)
    return f"{codigo} · {rotulo}" if codigo else rotulo

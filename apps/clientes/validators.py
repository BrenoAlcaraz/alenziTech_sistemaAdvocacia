import re


def normalizar_documento(valor):
    """Retorna apenas os dígitos de CPF/CNPJ/telefone."""
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf):
    """Algoritmo padrão de dígito verificador (módulo 11) do CPF."""
    cpf = normalizar_documento(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def _digito(parcial, pesos):
        soma = sum(int(d) * p for d, p in zip(parcial, pesos))
        resto = (soma * 10) % 11
        return resto if resto < 10 else 0

    if _digito(cpf[:9], range(10, 1, -1)) != int(cpf[9]):
        return False
    if _digito(cpf[:10], range(11, 1, -1)) != int(cpf[10]):
        return False
    return True


def cnpj_valido(cnpj):
    """Algoritmo padrão de dígito verificador (módulo 11) do CNPJ."""
    cnpj = normalizar_documento(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def _digito(parcial, pesos):
        soma = sum(int(d) * p for d, p in zip(parcial, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if _digito(cnpj[:12], pesos1) != int(cnpj[12]):
        return False
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if _digito(cnpj[:13], pesos2) != int(cnpj[13]):
        return False
    return True


def telefone_valido(telefone):
    """Telefone brasileiro: 10 dígitos (fixo) ou 11 (celular), com DDD."""
    digitos = normalizar_documento(telefone)
    return len(digitos) in (10, 11)

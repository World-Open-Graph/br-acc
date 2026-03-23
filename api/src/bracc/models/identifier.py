from dataclasses import dataclass
import re


def get_identifier(value: str):
    cleaned = clean_identifier(value)

    if Cpf.is_valid(cleaned):
        return Cpf(cleaned)

    if Cnpj.is_valid(cleaned):
        return Cnpj(cleaned)

    return None


def clean_identifier(raw: str) -> str:
    return re.sub(r"[.\-/]", "", raw)
from dataclasses import dataclass
import re


@dataclass
class Cpf:
    value: str
    _CPF_PATTERN = re.compile(r"^\d{11}$")

    def __init__(self, value):
        self.value =clean_identifier(value)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        if not cls._CPF_PATTERN.match(value):
            return False

        # ❌ rejeita CPFs com todos dígitos iguais
        if value == value[0] * 11:
            return False

        # ✅ valida 1º dígito
        if not cls._validate_digit(value, 9):
            return False

        # ✅ valida 2º dígito
        if not cls._validate_digit(value, 10):
            return False

        return True

    @staticmethod
    def _validate_digit(cpf: str, position: int) -> bool:
        """
        position = 9  -> valida 1º dígito
        position = 10 -> valida 2º dígito
        """
        total = 0
        weight = position + 1

        for i in range(position):
            total += int(cpf[i]) * weight
            weight -= 1

        remainder = total % 11

        digit = 0 if remainder < 2 else 11 - remainder

        return digit == int(cpf[position])

    def pretty(digits: str) -> str:
        """Format an 11-digit string as CPF: 123.456.789-00."""
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


    def mask_formatted_cpf(self) -> str:
        """Mask a formatted CPF, keeping only the last 4 visible digits.

        Example: 123.456.789-00 -> ***.***.789-00
        """
        return f"***.***.{self.value[8:]}"


    def mask_raw_cpf(self) -> str:
        """Mask a raw 11-digit CPF, keeping only the last 4 digits.

        Example: 12345678900 -> *******8900
        """
        return f"*******{self.value[7:]}"



from dataclasses import dataclass
import re


@dataclass
class Cnpj:
    value: str

    CNPJ_PATTERN = re.compile(r"^\d{14}$")

    def __init__(self, value):
        self.value =clean_identifier(value)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        if not cls.CNPJ_PATTERN.match(value):
            return False

        # ❌ rejeita sequências iguais
        if value == value[0] * 14:
            return False

        # ✅ valida 1º dígito
        if not cls._validate_digit(value, 12):
            return False

        # ✅ valida 2º dígito
        if not cls._validate_digit(value, 13):
            return False

        return True

    @staticmethod
    def _validate_digit(cnpj: str, position: int) -> bool:
        if position == 12:
            weights = [5,4,3,2,9,8,7,6,5,4,3,2]
        else:
            weights = [6,5,4,3,2,9,8,7,6,5,4,3,2]

        total = sum(int(cnpj[i]) * weights[i] for i in range(position))

        remainder = total % 11

        digit = 0 if remainder < 2 else 11 - remainder

        return digit == int(cnpj[position])

    def _pretty(digits: str) -> str:
        """Format a 14-digit string as CNPJ: 12.345.678/0001-00."""
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

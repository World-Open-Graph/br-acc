from dataclasses import dataclass
import re
from typing import Optional, Union


def clean_identifier(raw: str) -> str:
    return re.sub(r"\D", "", raw)


class Document:
    def __init__(self, value: str):
        self._value = clean_identifier(value)
        
    def get_value(self) -> str:
        return self._value
    

@dataclass
class Cpf(Document):
    _value: str

    _PATTERN = re.compile(r"^\d{11}$")

    def __post_init__(self):
        self._value = clean_identifier(self._value)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        value = clean_identifier(value)

        if not cls._PATTERN.match(value):
            return False

        if value == value[0] * 11:
            return False

        if not cls._validate_digit(value, 9):
            return False

        if not cls._validate_digit(value, 10):
            return False

        return True

    @staticmethod
    def _validate_digit(cpf: str, position: int) -> bool:
        total = 0
        weight = position + 1

        for i in range(position):
            total += int(cpf[i]) * weight
            weight -= 1

        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder

        return digit == int(cpf[position])

    def pretty(self) -> str:
        return f"{self._value[:3]}.{self._value[3:6]}.{self._value[6:9]}-{self._value[9:]}"

    def mask(self) -> str:
        return f"***.***.{self._value[6:9]}-{self._value[9:]}"

    def mask_raw(self) -> str:
        return f"*******{self._value[7:]}"


@dataclass
class Cnpj(Document):
    _value: str

    _PATTERN = re.compile(r"^\d{14}$")

    def __post_init__(self):
        self._value = clean_identifier(self._value)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        value = clean_identifier(value)

        if not cls._PATTERN.match(value):
            return False

        if value == value[0] * 14:
            return False

        if not cls._validate_digit(value, 12):
            return False

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

    def pretty(self) -> str:
        return f"{self._value[:2]}.{self._value[2:5]}.{self._value[5:8]}/{self._value[8:12]}-{self._value[12:]}"

    def mask(self) -> str:
        return f"**.***.***/{self._value[8:12]}-{self._value[12:]}"


def get_identifier(value: str) -> Optional[Union[Cpf, Cnpj]]:
    if Cpf.is_valid(value):
        return Cpf(value)

    if Cnpj.is_valid(value):
        return Cnpj(value)

    return None
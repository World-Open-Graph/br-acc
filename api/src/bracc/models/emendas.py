from pydantic import BaseModel


class EmendaPayment(BaseModel):
    transfer_id: str
    ob: str
    date: str | None = None
    year: str | None = None
    month: str | None = None
    amendment_type: str | None = None
    special_transfer: str | None = None
    economic_category: str | None = None
    value: float = 0.0
    source: str = "tesouro_emendas"


class EmendaBeneficiary(BaseModel):
    cnpj: str
    razao_social: str | None = None


class EmendaRecord(BaseModel):
    payment: dict[str, str | float | int | bool | None]
    beneficiary: dict[str, str | float | int | bool | None] | None = None


class EmendasListResponse(BaseModel):
    data: list[EmendaRecord]
    total_count: int
    skip: int
    limit: int

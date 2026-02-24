from pydantic import BaseModel

from icarus.models.entity import SourceAttribution


class PatternResult(BaseModel):
    pattern_id: str
    pattern_name: str
    description: str
    data: dict[str, str | float | int | bool | list[str] | None]
    entity_ids: list[str]
    sources: list[SourceAttribution]


class PatternResponse(BaseModel):
    entity_id: str | None
    patterns: list[PatternResult]
    total: int


PATTERN_METADATA: dict[str, dict[str, str]] = {
    "self_dealing_amendment": {
        "name_pt": "Emenda autodirecionada",
        "name_en": "Self-dealing amendment",
        "desc_pt": "Parlamentar autor de emenda com empresa familiar vencedora do contrato",
        "desc_en": "Legislator authored amendment where family company won the contract",
    },
    "patrimony_incompatibility": {
        "name_pt": "Incompatibilidade patrimonial",
        "name_en": "Patrimony incompatibility",
        "desc_pt": "Capital de empresas familiares incompatível com patrimônio declarado",
        "desc_en": "Family company capital inconsistent with declared patrimony",
    },
    "sanctioned_still_receiving": {
        "name_pt": "Sancionada ainda recebendo",
        "name_en": "Sanctioned still receiving",
        "desc_pt": "Empresa sancionada (CEIS/CNEP) que venceu contratos após a sanção",
        "desc_en": "Sanctioned company (CEIS/CNEP) that won contracts after sanction date",
    },
    "donation_contract_loop": {
        "name_pt": "Ciclo doação-contrato",
        "name_en": "Donation-contract loop",
        "desc_pt": "Empresa que doou para campanha e depois venceu contrato do mesmo político",
        "desc_en": "Company that donated to campaign then won contracts from the same politician",
    },
    "contract_concentration": {
        "name_pt": "Concentração de contratos municipais",
        "name_en": "Municipal contract concentration",
        "desc_pt": "Participação desproporcional de contratos em um município",
        "desc_en": "Disproportionate share of contracts in a municipality",
    },
    "debtor_contracts": {
        "name_pt": "Devedor com contratos públicos",
        "name_en": "Debtor with public contracts",
        "desc_pt": "Empresa com dívida ativa na PGFN que venceu licitações públicas",
        "desc_en": "Company with active PGFN tax debt that won public contracts",
    },
    "embargoed_receiving": {
        "name_pt": "Embargada recebendo recursos",
        "name_en": "Embargoed receiving funds",
        "desc_pt": (
            "Empresa com embargo ambiental do IBAMA"
            " que recebeu contratos ou empréstimos públicos"
        ),
        "desc_en": (
            "Company with IBAMA environmental embargo"
            " that received public contracts or loans"
        ),
    },
    "loan_debtor": {
        "name_pt": "Tomador de empréstimo com dívida",
        "name_en": "Loan recipient with debt",
        "desc_pt": "Empresa que recebeu empréstimo do BNDES enquanto possuía dívida ativa na PGFN",
        "desc_en": "Company that received BNDES loan while having active PGFN tax debt",
    },
    "donation_amendment_loop": {
        "name_pt": "Ciclo doação-emenda-benefício",
        "name_en": "Donation-amendment-benefit loop",
        "desc_pt": "Empresa doou para político que autorizou emenda beneficiando a mesma empresa",
        "desc_en": (
            "Company donated to politician who authored"
            " amendment benefiting the same company"
        ),
    },
    "amendment_beneficiary_contracts": {
        "name_pt": "Beneficiário de emenda com contratos",
        "name_en": "Amendment beneficiary with contracts",
        "desc_pt": (
            "Empresa beneficiada por emenda parlamentar"
            " que também venceu licitações públicas"
        ),
        "desc_en": "Company benefited from parliamentary amendment that also won public contracts",
    },
    "debtor_health_operator": {
        "name_pt": "Devedor fiscal operando unidade SUS",
        "name_en": "Tax debtor operating SUS facility",
        "desc_pt": "Empresa com dívida ativa na PGFN que opera unidades de saúde do SUS",
        "desc_en": "Company with active PGFN tax debt operating SUS health facilities",
    },
    "sanctioned_health_operator": {
        "name_pt": "Sancionada operando unidade SUS",
        "name_en": "Sanctioned operating SUS facility",
        "desc_pt": "Empresa sancionada (CEIS/CNEP/TCU) que opera unidades de saúde do SUS",
        "desc_en": "Sanctioned company (CEIS/CNEP/TCU) operating SUS health facilities",
    },
    "shell_company_contracts": {
        "name_pt": "Empresa com poucos empregados e muitos contratos",
        "name_en": "Low-employee company with many contracts",
        "desc_pt": (
            "Empresa que venceu múltiplas licitações em setor"
            " com poucos empregados registrados na RAIS"
        ),
        "desc_en": (
            "Company winning multiple contracts in sector"
            " with few RAIS-registered employees"
        ),
    },
}

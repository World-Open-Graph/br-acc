"""Pandera schemas for PGFN (Tax Debt / Divida Ativa) pipeline.

Validates the two entity lists produced by PgfnPipeline.transform():
- finances: Finance nodes (finance_id, type, inscription_number, value, etc.)
- relationships: DEVE relationships (source_key=CNPJ, target_key=finance_id)

Column definitions derived from pgfn.py transform() output dictionaries.
Only company (PJ) debtors with PRINCIPAL debtor type are loaded; person
records are pre-filtered due to LGPD CPF masking by PGFN.
"""

import pandera.pandas as pa

# ------------------------------------------------------------------
# Finances (Finance nodes)
# Output keys: finance_id, type, inscription_number, value, date,
#              situation, revenue_type, court_action, source
# ------------------------------------------------------------------
finances_schema = pa.DataFrameSchema(
    columns={
        "finance_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_matches(
                r"^pgfn_\S+$",
                error="finance_id must start with 'pgfn_' followed by inscription number",
            ),
        ]),
        "type": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.isin(["divida_ativa"], error="type must be 'divida_ativa'"),
        ]),
        "inscription_number": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="inscription_number must not be empty"),
        ]),
        "value": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="value must be >= 0"),
        ]),
        "date": pa.Column(str, nullable=True, coerce=True),
        "situation": pa.Column(str, nullable=True, coerce=True),
        "revenue_type": pa.Column(str, nullable=True, coerce=True),
        "court_action": pa.Column(str, nullable=True, coerce=True),
        "source": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.isin(["pgfn"], error="source must be 'pgfn'"),
        ]),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# DEVE relationships (Company -> Finance)
# Output keys: source_key, target_key, value, date, company_name
# ------------------------------------------------------------------
deve_relationship_schema = pa.DataFrameSchema(
    columns={
        "source_key": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_matches(
                    r"^(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})$",
                    error="source_key must be a formatted CNPJ",
                ),
            ],
        ),
        "target_key": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_matches(
                r"^pgfn_\S+$",
                error="target_key must be a pgfn_ finance_id",
            ),
        ]),
        "value": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="value must be >= 0"),
        ]),
        "date": pa.Column(str, nullable=True, coerce=True),
        "company_name": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,
)

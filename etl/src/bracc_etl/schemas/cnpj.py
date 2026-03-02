"""Pandera schemas for CNPJ (Receita Federal Company Registry) pipeline.

Validates the three core entity DataFrames produced by CNPJPipeline.transform():
- empresas: Company nodes (cnpj, razao_social, capital_social, uf, etc.)
- socios (PF strong): Person nodes keyed by CPF
- socios (PF partial): Partner nodes keyed by partner_id hash

Column definitions derived from cnpj.py _transform_empresas_rf/simple
and _transform_socios_rf/simple output dictionaries.
"""

import pandera.pandas as pa

# ------------------------------------------------------------------
# Empresas (Company nodes)
# Output columns: cnpj, razao_social, natureza_juridica, cnae_principal,
#                  capital_social, uf, municipio, porte_empresa
# ------------------------------------------------------------------
empresas_schema = pa.DataFrameSchema(
    columns={
        "cnpj": pa.Column(
            str,
            nullable=True,
            coerce=True,
            checks=[
                # Formatted CNPJ: XX.XXX.XXX/XXXX-XX (18 chars) or raw digits
                pa.Check.str_matches(
                    r"^(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{8,14})$",
                    error="CNPJ must be formatted (XX.XXX.XXX/XXXX-XX) or 8-14 digits",
                ),
            ],
        ),
        "razao_social": pa.Column(str, nullable=True, coerce=True),
        "natureza_juridica": pa.Column(str, nullable=True, coerce=True),
        "cnae_principal": pa.Column(str, nullable=True, coerce=True),
        "capital_social": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="capital_social must be >= 0"),
        ]),
        "uf": pa.Column(str, nullable=True, coerce=True, checks=[
            # Brazilian UF: 2 uppercase letters or empty
            pa.Check.str_matches(
                r"^([A-Z]{2})?$",
                error="UF must be 2 uppercase letters or empty",
            ),
        ]),
        "municipio": pa.Column(str, nullable=True, coerce=True),
        "porte_empresa": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,  # Allow extra columns
)


# ------------------------------------------------------------------
# Socios PF (Person nodes with strong CPF identity)
# Output columns: name, cpf, tipo_socio
# ------------------------------------------------------------------
socios_pf_schema = pa.DataFrameSchema(
    columns={
        "name": pa.Column(str, nullable=True, coerce=True),
        "cpf": pa.Column(
            str,
            nullable=True,
            coerce=True,
            checks=[
                # Formatted CPF: XXX.XXX.XXX-XX (14 chars) or raw 11 digits
                pa.Check.str_matches(
                    r"^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})$",
                    error="CPF must be formatted (XXX.XXX.XXX-XX) or 11 digits",
                ),
            ],
        ),
        "tipo_socio": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Socios PF partial (Partner nodes with masked/invalid docs)
# Output columns: partner_id, name, doc_raw, doc_digits, doc_partial,
#                  doc_type, tipo_socio, identity_quality, source
# ------------------------------------------------------------------
socios_partial_schema = pa.DataFrameSchema(
    columns={
        "partner_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="partner_id must not be empty"),
        ]),
        "name": pa.Column(str, nullable=True, coerce=True),
        "doc_raw": pa.Column(str, nullable=True, coerce=True),
        "doc_digits": pa.Column(str, nullable=True, coerce=True),
        "doc_partial": pa.Column(str, nullable=True, coerce=True),
        "doc_type": pa.Column(str, nullable=True, coerce=True),
        "tipo_socio": pa.Column(str, nullable=True, coerce=True),
        "identity_quality": pa.Column(str, nullable=True, coerce=True, checks=[
            pa.Check.isin(
                ["partial", "unknown", ""],
                error="identity_quality must be partial/unknown",
            ),
        ]),
        "source": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# SOCIO_DE relationships (all variants: PF, partial, PJ)
# Output columns: source_key, target_key, tipo_socio, qualificacao,
#                  data_entrada, snapshot_date
# ------------------------------------------------------------------
socio_relationship_schema = pa.DataFrameSchema(
    columns={
        "source_key": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="source_key must not be empty"),
        ]),
        "target_key": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="target_key must not be empty"),
        ]),
        "tipo_socio": pa.Column(str, nullable=True, coerce=True),
        "qualificacao": pa.Column(str, nullable=True, coerce=True),
        "data_entrada": pa.Column(str, nullable=True, coerce=True),
        "snapshot_date": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,
)

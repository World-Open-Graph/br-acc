"""Pandera schemas for DOU (Diario Oficial da Uniao) pipeline.

Validates the three entity lists produced by DouPipeline.transform():
- acts: DOUAct nodes (act_id, title, act_type, date, section, etc.)
- person_rels: PUBLICOU relationships (Person CPF -> DOUAct)
- company_rels: MENCIONOU relationships (Company CNPJ -> DOUAct)

Column definitions derived from dou.py transform() output dictionaries.
Act types are classified from title/abstract text into: nomeacao,
exoneracao, contrato, penalidade, outro.
"""

import pandera.pandas as pa

# ------------------------------------------------------------------
# Acts (DOUAct nodes)
# Output keys: act_id, title, act_type, date, section, agency,
#              category, text_excerpt, url, source
# ------------------------------------------------------------------
acts_schema = pa.DataFrameSchema(
    columns={
        "act_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="act_id must not be empty"),
        ]),
        "title": pa.Column(str, nullable=True, coerce=True),
        "act_type": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.isin(
                ["nomeacao", "exoneracao", "contrato", "penalidade", "outro"],
                error="act_type must be one of the classified types",
            ),
        ]),
        "date": pa.Column(str, nullable=True, coerce=True),
        "section": pa.Column(str, nullable=True, coerce=True),
        "agency": pa.Column(str, nullable=True, coerce=True),
        "category": pa.Column(str, nullable=True, coerce=True),
        "text_excerpt": pa.Column(str, nullable=True, coerce=True, checks=[
            pa.Check.str_length(max_value=500, error="text_excerpt must be <= 500 chars"),
        ]),
        "url": pa.Column(str, nullable=True, coerce=True, checks=[
            pa.Check.str_matches(
                r"^https?://",
                error="url must start with http:// or https://",
            ),
        ]),
        "source": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.isin(["imprensa_nacional"], error="source must be 'imprensa_nacional'"),
        ]),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Person relationships (PUBLICOU: Person -> DOUAct)
# Output keys: source_key (CPF), target_key (act_id)
# ------------------------------------------------------------------
person_rels_schema = pa.DataFrameSchema(
    columns={
        "source_key": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_matches(
                    r"^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})$",
                    error="source_key must be a formatted CPF",
                ),
            ],
        ),
        "target_key": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="target_key must not be empty"),
        ]),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Company relationships (MENCIONOU: Company -> DOUAct)
# Output keys: source_key (CNPJ), target_key (act_id)
# ------------------------------------------------------------------
company_rels_schema = pa.DataFrameSchema(
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
            pa.Check.str_length(min_value=1, error="target_key must not be empty"),
        ]),
    },
    coerce=True,
    strict=False,
)

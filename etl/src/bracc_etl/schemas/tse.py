"""Pandera schemas for TSE (Electoral Donations) pipeline.

Validates the three entity lists produced by TSEPipeline.transform():
- candidates: Person nodes (sq_candidato, name, cpf, partido, uf)
- elections: Election nodes (year, cargo, uf, municipio, candidate_sq)
- donations: DOOU relationships (candidate_sq, donor_doc, valor, year, etc.)

Column definitions derived from tse.py _transform_candidates and
_transform_donations output dictionaries.

Note: TSE 2024 masks ALL candidate CPFs as "-4". After stripping,
candidates without real CPFs omit the 'cpf' key entirely. The cpf
column is therefore nullable.
"""

import pandera.pandas as pa

# ------------------------------------------------------------------
# Candidates (Person nodes)
# Output keys: sq_candidato, name, partido, uf, cpf (optional)
# ------------------------------------------------------------------
candidates_schema = pa.DataFrameSchema(
    columns={
        "sq_candidato": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="sq_candidato must not be empty"),
        ]),
        "name": pa.Column(str, nullable=True, coerce=True),
        "partido": pa.Column(str, nullable=True, coerce=True),
        "uf": pa.Column(str, nullable=True, coerce=True, checks=[
            pa.Check.str_matches(
                r"^[A-Z]{2}$",
                error="UF must be 2 uppercase letters",
            ),
        ]),
        # cpf is optional — absent for masked candidates (TSE sentinel "-4")
        "cpf": pa.Column(
            str,
            nullable=True,
            coerce=True,
            required=False,
            checks=[
                pa.Check.str_matches(
                    r"^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})$",
                    error="CPF must be formatted or 11 digits",
                ),
            ],
        ),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Elections (Election nodes)
# Output keys: year, cargo, uf, municipio, candidate_sq
# ------------------------------------------------------------------
elections_schema = pa.DataFrameSchema(
    columns={
        "year": pa.Column(int, nullable=False, coerce=True, checks=[
            pa.Check.in_range(1945, 2030, error="year must be between 1945 and 2030"),
        ]),
        "cargo": pa.Column(str, nullable=True, coerce=True),
        "uf": pa.Column(str, nullable=True, coerce=True),
        "municipio": pa.Column(str, nullable=True, coerce=True),
        "candidate_sq": pa.Column(str, nullable=False, coerce=True),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Donations (DOOU relationships)
# Output keys: candidate_sq, donor_doc, donor_name, donor_is_company,
#              valor, year
# ------------------------------------------------------------------
donations_schema = pa.DataFrameSchema(
    columns={
        "candidate_sq": pa.Column(str, nullable=False, coerce=True),
        "donor_doc": pa.Column(
            str,
            nullable=True,
            coerce=True,
            checks=[
                # Formatted CPF or CNPJ (11 or 14 digits, with or without punctuation)
                pa.Check.str_matches(
                    r"^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{11}|\d{14})$",
                    error="donor_doc must be formatted CPF or CNPJ",
                ),
            ],
        ),
        "donor_name": pa.Column(str, nullable=True, coerce=True),
        "donor_is_company": pa.Column(bool, nullable=False, coerce=True),
        "valor": pa.Column(float, nullable=False, coerce=True, checks=[
            pa.Check.ge(0, error="valor must be >= 0"),
        ]),
        "year": pa.Column(int, nullable=False, coerce=True, checks=[
            pa.Check.in_range(1945, 2030, error="year must be between 1945 and 2030"),
        ]),
    },
    coerce=True,
    strict=False,
)

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from bracc.models.investigation import Annotation, InvestigationResponse, Tag

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

_LABELS: dict[str, dict[str, str]] = {
    "pt": {
        "label_created": "Criado em",
        "label_tags": "Etiquetas",
        "label_no_tags": "Sem etiquetas.",
        "label_entities": "Entidades",
        "label_entity_name": "Nome",
        "label_entity_type": "Tipo",
        "label_entity_document": "Documento",
        "label_no_entities": "Sem entidades.",
        "label_annotations": "Anotações",
        "label_no_annotations": "Sem anotações.",
        "disclaimer": (
            "Dados compilados de fontes públicas. "
            "Este relatório não implica em irregularidade."
        ),
    },
    "en": {
        "label_created": "Created at",
        "label_tags": "Tags",
        "label_no_tags": "No tags.",
        "label_entities": "Entities",
        "label_entity_name": "Name",
        "label_entity_type": "Type",
        "label_entity_document": "Document",
        "label_no_entities": "No entities.",
        "label_annotations": "Annotations",
        "label_no_annotations": "No annotations.",
        "disclaimer": (
            "Data compiled from public sources. "
            "This report does not imply wrongdoing."
        ),
    },
}


def _get_labels(lang: str) -> dict[str, str]:
    return _LABELS.get(lang, _LABELS["pt"])


async def render_investigation_pdf(
    investigation: InvestigationResponse,
    annotations: list[Annotation],
    tags: list[Tag],
    entities: list[dict[str, str]],
    lang: str = "pt",
) -> bytes:
    """Render an investigation report as a PDF.

    Pure function: takes data, renders Jinja2 template, returns PDF bytes.
    """
    labels = _get_labels(lang)
    template = _env.get_template("investigation_report.html")

    html_content = template.render(
        lang=lang,
        title=investigation.title,
        description=investigation.description or "",
        created_at=investigation.created_at,
        tags=[{"name": t.name, "color": t.color} for t in tags],
        entities=entities,
        annotations=[{"created_at": a.created_at, "text": a.text} for a in annotations],
        **labels,
    )

    from weasyprint import HTML

    pdf_bytes: bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes

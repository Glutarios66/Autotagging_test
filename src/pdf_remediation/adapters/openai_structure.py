from __future__ import annotations

import json

import httpx

from pdf_remediation.ir import DocumentIR, Provenance, SemanticDocumentIR, SemanticNode


class OpenAIStructureAnalyzer:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze(self, document: DocumentIR) -> SemanticDocumentIR:
        source = [
            {
                "id": element.id,
                "page": element.page,
                "kind": element.kind,
                "text": element.text,
                "reading_order": element.reading_order,
                "style": element.style,
                "metadata": element.metadata,
            }
            for element in document.elements
            if element.kind in {"text", "image", "table"}
        ]

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "role": {
                                "type": "string",
                                "enum": [
                                    "H1", "H2", "H3", "H4", "H5", "H6",
                                    "P", "L", "LI", "Figure", "Caption",
                                    "Table", "TR", "TH", "TD", "Artifact", "Span"
                                ],
                            },
                            "source_element_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "text": {"type": ["string", "null"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": [
                            "id",
                            "role",
                            "source_element_ids",
                            "text",
                            "confidence",
                        ],
                    },
                }
            },
            "required": ["nodes"],
        }

        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "Classify document elements into PDF accessibility structure roles. "
                "Preserve source IDs and reading order. Do not invent document text."
            ),
            "input": json.dumps(source, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "pdf_structure",
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        response = httpx.post(
            f"{self.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        body = response.json()

        output_text = body.get("output_text")
        if not isinstance(output_text, str):
            fragments: list[str] = []
            for item in body.get("output", []):
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text = content.get("text")
                        if isinstance(text, str):
                            fragments.append(text)
            output_text = "".join(fragments)

        parsed = json.loads(output_text)
        nodes = [
            SemanticNode(
                id=item["id"],
                role=item["role"],
                source_element_ids=item["source_element_ids"],
                text=item["text"],
                confidence=item["confidence"],
                provenance=[
                    Provenance(
                        source="openai_structure",
                        adapter="openai",
                        model=self.model,
                        confidence=item["confidence"],
                    )
                ],
            )
            for item in parsed["nodes"]
        ]
        return SemanticDocumentIR(
            document_id=document.document_id,
            nodes=nodes,
            reading_order=[node.id for node in nodes],
            metadata={"analyzer": "openai", "model": self.model},
            provenance=[
                Provenance(
                    source="openai_structure",
                    adapter="openai",
                    model=self.model,
                )
            ],
        )

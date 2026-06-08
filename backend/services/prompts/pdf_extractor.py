"""
PDF Extractor prompt — universal document intelligence.

Single-call extraction using GPT-5.2.
Works on any document type: legal, business, financial, HR, government.

Rules:
- Model: GPT-5.2
- All output is structured JSON — never free text
- Confidence scores reflect actual certainty per field
- Changing this prompt = making a PR
"""
from backend.services.prompts.base_prompt import PromptTemplate, ModelType

MODEL = ModelType.GPT5_2

AMBER_CONFIDENCE_THRESHOLD = 75

SYSTEM_PROMPT = """You are a document intelligence specialist with deep \
expertise in Indian law and legal practice. Analyse any document and \
extract structured intelligence from it. Always respond in valid JSON \
only. No preamble. No markdown.

Confidence scoring:
- 95-100: Value appears verbatim in the document
- 80-94:  Value is clearly stated, minor formatting applied
- 60-79:  Value is reasonably inferred from context
- 0-59:   Uncertain, ambiguous, or not present — set value to null

For summary, return 1-3 short bullet strings (array). Each bullet \
is one complete sentence covering a distinct aspect: what happened, \
the court/outcome, relief granted. Never return summary as a string.

For action_items: set is_court_decision=true for anything a court has \
already decided (dismissed, upheld, quashed, allowed). Set it false for \
future steps the lawyer or parties must take. Include both — the \
frontend filters on the field.

For critical_deadlines: set is_future=true only for dates that have not \
yet passed and still require action. Set is_future=false for historical \
dates. Include both — the frontend filters on the field.

For case_outcome: set to "allowed" if petition/appeal was allowed, \
"dismissed" if dismissed/rejected/refused, "pending" if not yet decided, \
null for non-legal documents."""


USER_PROMPT_TEMPLATE = """Analyse this document completely and extract \
structured intelligence from it.

Document text:
{document_text}

Return ONLY this JSON structure. No preamble. No markdown:
{{
  "document_type": {{
    "category": "Legal | Business | Financial | HR | Government | Technical | Other",
    "sub_type": "specific type e.g. High Court Order, Lease Agreement, Legal Notice, FIR",
    "confidence": 0
  }},

  "identity_fields": {{
  }},

  "summary": {{
    "value": [
      "bullet: what happened / who is involved / what is at stake",
      "bullet: outcome or relief granted (omit if not yet decided)"
    ],
    "confidence": 0
  }},

  "primary_objective": {{
    "value": "one sentence — what this document achieves or establishes",
    "confidence": 0
  }},

  "case_outcome": "allowed | dismissed | pending | null — only for legal documents with a final decision",

  "case_narrative": {{
    "background": [
      "bullet point: who the parties are and what post/subject is in dispute",
      "bullet point: what happened before court — what triggered this petition",
      "bullet point: what relief was sought and what lower court/tribunal decided"
    ],
    "petitioner_arguments": [
      "argument or ground raised by petitioner — one per item, plain English"
    ],
    "respondent_arguments": [
      "argument or ground raised by respondent — one per item, plain English"
    ],
    "key_legal_question": "The single central legal question the court was asked to decide, \
phrased as a question ending with '?'. null for non-legal documents.",
    "court_reasoning": [
      "key finding or reasoning point the court relied on — one per item, plain English"
    ],
    "key_takeaway": "One sentence: the legal principle this judgment/order establishes \
that a lawyer can apply in future matters. null for non-legal documents."
  }},

  "key_stakeholders": [
    {{
      "name": "name",
      "role": "specific role in this document",
      "obligations": "obligations explicitly stated in this document or null",
      "confidence": 0
    }}
  ],

  "critical_deadlines": [
    {{
      "label": "plain English description",
      "date": "YYYY-MM-DD or relative",
      "consequence": "what happens if missed or null",
      "confidence": 0,
      "is_future": true
    }}
  ],

  "constraints_and_risks": [
    {{
      "type": "Constraint | Risk | Condition | Limitation",
      "description": "plain English description",
      "severity": "High | Medium | Low",
      "confidence": 0
    }}
  ],

  "action_items": [
    {{
      "action": "action required of a party or lawyer",
      "by_whom": "who must act or null",
      "by_when": "deadline or null",
      "priority": "Urgent | High | Normal",
      "is_court_decision": false
    }}
  ],

  "citations": [
    {{
      "case_name": "full case name",
      "citation_string": "reporter citation or null",
      "relied_upon": true,
      "confidence": 0
    }}
  ]
}}

For identity_fields: extract ALL fields that are materially relevant \
to this specific document type. Use your judgment — a court order needs \
case_number, court, bench, parties, date, relief_type, sections_invoked. \
A lease needs parties, rent, deposit, dates, notice_period. \
A legal notice needs sender, recipient, demand, deadline, legal_basis. \
Do not include fields that are null or irrelevant to this document type.

For case_narrative: populate for ALL legal documents (court orders, \
judgments, petitions, legal notices, FIRs, agreements). \
For non-legal documents set case_narrative to null. \
petitioner_arguments and respondent_arguments may be empty arrays \
if not applicable (e.g. a simple court order without contested arguments). \
court_reasoning may be empty for non-judgments. \
Always populate background and key_legal_question if this is a court document."""


pdf_extractor_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=USER_PROMPT_TEMPLATE,
    model=MODEL,
    version="2026-04-21",
    temperature=0.0,
    max_tokens=4000,
    description=(
        "Universal document intelligence using GPT-5.2. "
        "Works on any document type. "
        "Returns document type, identity fields, summary, "
        "primary objective, stakeholders, deadlines, "
        "constraints, action items, citations."
    ),
)

OUTPUT_SCHEMA = {
    "document_type": {
        "category": "str",
        "sub_type": "str",
        "confidence": "int 0-100"
    },
    "identity_fields": {
        "field_name": {
            "value": "str or null",
            "confidence": "int 0-100"
        }
    },
    "summary": {"value": ["str"], "confidence": "int 0-100"},  # always an array
    "primary_objective": {"value": "str or null", "confidence": "int 0-100"},
    "case_narrative": {
        "background": ["str"],   # array of bullet points
        "petitioner_arguments": ["str"],
        "respondent_arguments": ["str"],
        "key_legal_question": "str or null",
        "court_reasoning": ["str"],
        "key_takeaway": "str or null",
    },
    "key_stakeholders": [
        {
            "name": "str",
            "role": "str",
            "obligations": "str or null",
            "confidence": "int 0-100"
        }
    ],
    "critical_deadlines": [
        {
            "label": "str",
            "date": "str",
            "consequence": "str or null",
            "confidence": "int 0-100"
        }
    ],
    "constraints_and_risks": [
        {
            "type": "str",
            "description": "str",
            "severity": "str",
            "confidence": "int 0-100"
        }
    ],
    "action_items": [
        {
            "action": "str",
            "by_whom": "str or null",
            "by_when": "str or null",
            "priority": "str"
        }
    ],
    "citations": [
        {
            "case_name": "str",
            "citation_string": "str or null",
            "relied_upon": "bool",
            "confidence": "int 0-100"
        }
    ],
}

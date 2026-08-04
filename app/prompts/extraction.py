"""Prompt templates for LLM contact extraction (Stage 4)."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a precise information-extraction engine for regulatory compliance \
documents (FCC Equipment Authorization filings and certification exhibits).

Your job: extract the PEOPLE responsible for product compliance and \
certification who work FOR THE APPLICANT/MANUFACTURER.

STRICT RULES:
- INCLUDE internal employees: Certification Managers, Product Compliance \
Managers, Regulatory Affairs, Product Security, Quality, Engineering leads, and \
company executives who signed the document.
- IGNORE and DO NOT return: outside lawyers and law firms, patent attorneys, \
test laboratories and certification bodies (e.g. TÜV, UL, SGS, Intertek, \
Eurofins, DEKRA, Bureau Veritas), FCC staff, and third-party filing agents or \
external consultants. If a signer is an external agent, set \
is_internal_employee to false.
- Extract only information explicitly present in the text. Never invent an \
email, phone, or title.
- Set confidence (0-100) based on how clearly the person is an internal \
compliance/certification employee with verifiable contact details.

Return ONLY structured data conforming to the provided JSON schema. If no \
qualifying person is present, return an empty contacts list.
"""

USER_PROMPT_TEMPLATE = """\
Document type (best guess): {document_type}
Applicant/company (if known): {company}

--- DOCUMENT TEXT START ---
{document_text}
--- DOCUMENT TEXT END ---

Extract the qualifying internal compliance/certification contacts.
"""


def build_user_prompt(
    *, document_text: str, document_type: str | None, company: str | None
) -> str:
    """Render the user prompt, truncating very long documents."""
    max_chars = 24_000
    text = document_text[:max_chars]
    return USER_PROMPT_TEMPLATE.format(
        document_type=document_type or "unknown",
        company=company or "unknown",
        document_text=text,
    )

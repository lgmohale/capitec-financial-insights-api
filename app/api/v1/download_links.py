from uuid import UUID

from fastapi import Request


def bank_statement_pdf_download_url(request: Request, account_id: UUID) -> str:
    return str(
        request.url_for(
            "download_bank_statement_pdf",
            statement_id=str(account_id),
        )
    )

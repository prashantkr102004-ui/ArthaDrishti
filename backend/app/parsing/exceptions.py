from dataclasses import dataclass


@dataclass(frozen=True)
class ParserErrorDetail:
    code: str
    message: str
    source_page: int | None = None
    source_row: int | None = None


class ParsingError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        source_page: int | None = None,
        source_row: int | None = None,
    ) -> None:
        super().__init__(message)
        self.detail = ParserErrorDetail(
            code=code,
            message=message,
            source_page=source_page,
            source_row=source_row,
        )

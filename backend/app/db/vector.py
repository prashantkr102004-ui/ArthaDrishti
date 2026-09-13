from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if len(value) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} embedding dimensions, got {len(value)}."
                )
            return vector_literal(value)

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None or isinstance(value, list):
                return value
            text = str(value).strip().removeprefix("[").removesuffix("]")
            if not text:
                return []
            return [float(part) for part in text.split(",")]

        return process


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"

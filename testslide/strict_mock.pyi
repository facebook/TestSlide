# pyre-unsafe
from typing import Any

class StrictMock(Any):
    def __init__(
        self,
        template: type | None = None,
        runtime_attrs: list[Any] | None = None,
        name: str | None = None,
        default_context_manager: bool = False,
        type_validation: bool = True,
        attributes_to_skip_type_validation: list[str] = [],
    ) -> None: ...

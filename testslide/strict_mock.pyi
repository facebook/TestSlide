# pyre-strict
from typing import Any

class StrictMock(Any):
    def __init__(
        self,
        template: type | None = ...,
        runtime_attrs: list[Any] | None = ...,
        name: str | None = ...,
        default_context_manager: bool = ...,
        type_validation: bool = ...,
        attributes_to_skip_type_validation: list[str] = ...,
    ) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

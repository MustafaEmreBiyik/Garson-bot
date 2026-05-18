from __future__ import annotations

from pathlib import Path
from typing import Optional

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager

from .base import BaseInferenceBackend, InferenceRequest, InferenceResponse


class DeterministicDialogueBackend(BaseInferenceBackend):
    backend_name = "deterministic_baseline"

    def __init__(
        self,
        menu_path: Path,
        restaurant_info_path: Path,
        manager: Optional[DialogueManager] = None,
    ) -> None:
        self.manager = manager or DialogueManager(menu_path, restaurant_info_path)

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        response_text = self.manager.handle_message(request.user_message)
        metadata = dict(request.metadata)
        if request.session_id:
            metadata["session_id"] = request.session_id
        return InferenceResponse(
            text=response_text,
            backend_name=self.backend_name,
            metadata=metadata,
        )

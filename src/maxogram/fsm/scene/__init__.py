"""Scene — высокоуровневый FSM для описания сложных диалогов."""

from maxogram.fsm.scene.base import Scene, SceneConfig
from maxogram.fsm.scene.registry import SceneRegistry
from maxogram.fsm.scene.wizard import WizardScene

__all__ = [
    "Scene",
    "SceneConfig",
    "SceneRegistry",
    "WizardScene",
]

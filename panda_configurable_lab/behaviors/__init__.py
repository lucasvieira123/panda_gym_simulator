from .base             import Behavior
from .hold             import HoldBehavior
from .random_behavior  import RandomBehavior
from .greedy           import GreedyGoalBehavior, GreedyPushBehavior, GreedyPickAndPlaceBehavior
from .manual           import ManualBehavior
from .scripted         import ScriptedBehavior
from .self_adaptive    import SelfAdaptiveBehavior


_REGISTRY: dict = {
    "hold"                 : HoldBehavior,
    "random"               : RandomBehavior,
    "greedy_goal"          : GreedyGoalBehavior,
    "greedy_push"          : GreedyPushBehavior,
    "greedy_pick_and_place": GreedyPickAndPlaceBehavior,
    "manual"               : ManualBehavior,
    "self_adaptive"        : SelfAdaptiveBehavior,
}


def make_behavior(name: str, gain: float = 5.0) -> Behavior:
    """
    Factory — instancia o Behavior concreto pelo nome da política.
    Adicionar uma nova política = uma linha no _REGISTRY acima.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        available = list(_REGISTRY)
        raise ValueError(f"Behavior desconhecido: {name!r}. Disponíveis: {available}")
    return cls(gain=gain)

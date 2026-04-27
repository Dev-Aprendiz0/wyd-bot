"""Motor de regras - decide qual estratégia executar a cada tick."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wyd_bot.automation.actions import GameActions

from wyd_bot.decision.state import BotMode, GameState
from wyd_bot.decision.strategy import (
    FarmStrategy,
    FleeStrategy,
    HealStrategy,
    LootStrategy,
    Strategy,
)
from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.decision.rule_engine")


class RuleEngine:
    """Motor de regras que gerencia e executa estratégias por prioridade.

    Cada tick do bot, o RuleEngine avalia todas as estratégias registradas
    e executa a de maior prioridade que deve ser ativada.
    """

    def __init__(self) -> None:
        self._strategies: list[Strategy] = []
        self._active_strategy: Strategy | None = None
        self._tick_count: int = 0

    def register(self, strategy: Strategy) -> None:
        """Registra uma nova estratégia."""
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority, reverse=True)
        logger.info("Estratégia registrada: %s (prioridade: %d)", strategy.name, strategy.priority)

    def register_defaults(
        self,
        hp_threshold: float = 0.5,
        mp_threshold: float = 0.3,
        emergency_threshold: float = 0.2,
        flee_threshold: float = 0.15,
        screen_center: tuple[int, int] = (512, 384),
    ) -> None:
        """Registra as estratégias padrão para WYD.

        Args:
            hp_threshold: Limiar de HP para curar.
            mp_threshold: Limiar de MP para curar.
            emergency_threshold: Limiar de HP para emergência.
            flee_threshold: Limiar de HP para fugir.
            screen_center: Centro da tela do jogo.
        """
        self.register(FleeStrategy(flee_threshold))
        self.register(HealStrategy(hp_threshold, mp_threshold, emergency_threshold))
        self.register(LootStrategy())
        self.register(FarmStrategy(screen_center))
        logger.info("Estratégias padrão registradas")

    def tick(self, state: GameState, actions: GameActions) -> str | None:
        """Executa um tick de decisão.

        Avalia todas as estratégias e executa a de maior prioridade.

        Args:
            state: Estado atual do jogo.
            actions: Ações disponíveis.

        Returns:
            Nome da estratégia executada ou None.
        """
        self._tick_count += 1

        if not state.player.is_alive:
            state.mode = BotMode.DEAD
            state.deaths += 1
            logger.warning("Personagem morreu! Total mortes: %d", state.deaths)
            return None

        for strategy in self._strategies:
            if strategy.should_activate(state):
                if self._active_strategy != strategy:
                    logger.info(
                        "Mudando estratégia: %s -> %s",
                        self._active_strategy.name if self._active_strategy else "None",
                        strategy.name,
                    )
                    self._active_strategy = strategy

                state.mode = self._strategy_to_mode(strategy)
                strategy.execute(state, actions)
                return strategy.name

        state.mode = BotMode.IDLE
        return None

    @staticmethod
    def _strategy_to_mode(strategy: Strategy) -> BotMode:
        """Mapeia uma estratégia para o modo do bot."""
        mode_map: dict[str, BotMode] = {
            "Flee": BotMode.FLEEING,
            "Heal": BotMode.HEALING,
            "Loot": BotMode.LOOTING,
            "Farm": BotMode.FARMING,
        }
        return mode_map.get(strategy.name, BotMode.IDLE)

    @property
    def active_strategy_name(self) -> str:
        """Retorna o nome da estratégia ativa."""
        return self._active_strategy.name if self._active_strategy else "None"

    @property
    def tick_count(self) -> int:
        return self._tick_count

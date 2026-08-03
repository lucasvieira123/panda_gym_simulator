from expression.action_expression import ActionExpression
from expression.conditional_expression import ConditionalExpression
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Dict, Any

T = TypeVar("T", bound="Scenario")

class Scenario(ABC):
    def __init__(
        self,
        name: str = None,
        given: ConditionalExpression = None,
        when: ConditionalExpression = None,
        do: ActionExpression = None,
        then: ConditionalExpression = None,
        data: dict = None,
    ) -> None:
        if data is not None:
            self._name = data.get("name")
            self._given = ConditionalExpression(data.get("given"))
            self._when = ConditionalExpression(data.get("when"))
            self._do = ActionExpression(data.get("do"))
            self._then = ConditionalExpression(data.get("then"))
        else:
            if name is None or given is None or when is None or do is None or then is None:
                raise ValueError("name, given, when, do and then must be provided if data is not given.")
            self._name = name
            self._given = given
            self._when = when
            self._do = do
            self._then = then

    @property
    def name(self) -> str:
        return self._name

    @property
    def given(self) -> ConditionalExpression:
        return self._given

    @property
    def when(self) -> ConditionalExpression:
        return self._when
    
    @property
    def do(self) -> ActionExpression:
        return self._do

    @property
    def then(self) -> ConditionalExpression:
        return self._then

    @given.setter
    def given(self, value: ConditionalExpression) -> None:
        self._given = value

    @when.setter
    def when(self, value: ConditionalExpression) -> None:
        self._when = value

    @do.setter
    def do(self, value: ActionExpression) -> None:
        self._do = value

    @then.setter
    def then(self, value: ConditionalExpression) -> None:
        self._then = value
    

    def to_dict(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "name": self._name,
            "given": self._given.expression,
            "when": self._when.expression,
            "do": self._do.expression,
            "then": self._then.expression,
        }
    
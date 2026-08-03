from abc import ABC

class Expression(ABC):
    """
    Abstract base class representing an expression as a string.
    """

    def __init__(self, expression: str) -> None:
        self._expression = expression
    
    def to_string(self) -> str:
        """
        Returns the string representation of the expression.
        """
        return self._expression

    @property
    def expression(self) -> str:
        """
        Gets the expression string.
        """
        return self._expression

    @expression.setter
    def expression(self, value: str) -> None:
        """
        Sets the expression string.
        """
        self._expression = value

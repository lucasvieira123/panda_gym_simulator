from expression.expression import Expression

class ConditionalExpression(Expression):
    def __init__(self, expression: str) -> None:
        super().__init__(expression)
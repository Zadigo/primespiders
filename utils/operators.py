from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from primespiders.utils.urls import URL


class Rules(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EMPTY = "empty"
    NOT_EMPTY = "not_empty"
    LIKE = "like"
    NOT_LIKE = "not_like"


class BaseCondition(ABC):
    def __init__(self, url: URL):
        self.url = url

    @abstractmethod
    def resolve(self) -> bool:
        pass


class Q(BaseCondition):
    def __init__(self, rule: Rules, value: str | None = None):
        self.url: URL | None = None
        self.rule = rule
        self.value = value

    def __call__(self, url: URL):
        self.url = url
        return self

    def resolve(self) -> bool:
        if self.url is None:
            raise ValueError("URL is not set for this condition.")

        match self.rule:
            case Rules.EQUALS:
                return self.url == self.value
            case Rules.NOT_EQUALS:
                return self.url != self.value
            case Rules.GREATER_THAN:
                return self.url > self.value
            case Rules.LESS_THAN:
                return self.url < self.value
            case Rules.GREATER_THAN_OR_EQUALS:
                return self.url >= self.value
            case Rules.LESS_THAN_OR_EQUALS:
                return self.url <= self.value
            case Rules.CONTAINS:
                return self.value in self.url
            case Rules.NOT_CONTAINS:
                return self.value not in self.url
            case Rules.STARTS_WITH:
                return self.url.startswith(self.value)
            case Rules.ENDS_WITH:
                return self.url.endswith(self.value)
            case Rules.EMPTY:
                return not self.url
            case Rules.NOT_EMPTY:
                return bool(self.url)
            case Rules.LIKE:
                # Implement your LIKE logic here
                pass
            case Rules.NOT_LIKE:
                # Implement your NOT_LIKE logic here
                pass
            case _:
                raise ValueError(f"Unsupported rule: {self.rule}")


class IfElse(BaseCondition):
    def __init__(self, url: URL, if_condition: Q, else_condition: Any):
        super().__init__(url)
        self.if_condition = if_condition
        self.else_condition = else_condition

    def resolve(self):
        instance = self.if_condition(self.url)
        result = instance.resolve()
        if result:
            return self.url
        return self.else_condition(self.url).resolve()


class BaseLogicalOperator(BaseCondition):
    def __init__(self, url: URL, *conditions: Q):
        super().__init__(url)
        self.conditions = conditions


class Or(BaseLogicalOperator):
    def resolve(self) -> bool:
        for condition in self.conditions:
            instance = condition(self.url)
            if instance.resolve():
                return True
        return False


class And(BaseLogicalOperator):
    def resolve(self) -> bool:
        for condition in self.conditions:
            instance = condition(self.url)
            if not instance.resolve():
                return False
        return True


class Not(BaseLogicalOperator):
    def resolve(self) -> bool:
        if not self.conditions:
            raise ValueError("Not operator requires at least one condition.")
        instance = self.conditions[0](self.url)
        return not instance.resolve()


class PartTest:
    """Class to test a specific part of a URL (path or query) for a given value.

    Args:
        url (URL): The URL to test.
        value (str): The value to look for in the specified part of the URL.
        part (Literal['path', 'query'], optional): The part of the URL to test. Defaults to 'path'.

    Raises:
        ValueError: If the part is not 'path' or 'query', or if the value is empty.
    """

    def __init__(self, url: URL, value: str, part: Literal['path', 'query'] = 'path'):
        if part not in ('path', 'query'):
            raise ValueError("part must be either 'path' or 'query'")

        self.url = url
        self.part = part
        self.value = value

        if not self.value:
            raise ValueError("value must not be empty")

    def resolve(self) -> bool:
        instance = Q(
            Rules.CONTAINS,
            getattr(self.url.parsed_url,  self.part),
            self.value
        )
        result = instance.resolve()
        return result

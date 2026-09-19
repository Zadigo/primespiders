import pytest
from primespiders.utils.operators import And, IfElse, Not, Or, Q, Rules
from primespiders.utils.urls import URL


class TestQ:
    def test_initialization(self):
        q = Q(Rules.EQUALS, "example_value")
        assert q.rule == Rules.EQUALS
        assert q.value == "example_value"
        assert q.url is None

    @pytest.mark.parametrize(
        "url,expected",
        [
            (URL('example.com'), True),
            (URL('other.com'), False),
        ]
    )
    async def test_resolve(self, url, expected):
        instance = Q(Rules.EQUALS, "example.com")
        result = instance(url)
        assert await result.resolve() is expected


def test_ifelse_initialization():
    if_condition = Q(Rules.EQUALS, "if_value")
    else_condition = Q(Rules.NOT_EQUALS, "else_value")
    ifelse = IfElse(URL(None), if_condition, else_condition)
    assert ifelse.if_condition == if_condition
    assert ifelse.else_condition == else_condition
    assert ifelse.url == URL(None)


def test_or_initialization():
    condition1 = Q(Rules.EQUALS, "value1")
    condition2 = Q(Rules.NOT_EQUALS, "value2")
    or_condition = Or(URL(None), condition1, condition2)
    assert or_condition.conditions == [condition1, condition2]
    assert or_condition.url == URL(None)


class TestAnd:
    def test_and_initialization(self):
        condition1 = Q(Rules.EQUALS, "value1")
        condition2 = Q(Rules.NOT_EQUALS, "value2")

        and_condition = And(URL(None), condition1, condition2)

        assert and_condition.conditions == [condition1, condition2]
        assert and_condition.url == URL(None)


class TestNot:
    def test_not_initialization(self):
        condition = Q(Rules.EQUALS, "value")
        not_condition = Not(URL(None), condition)
        assert not_condition.conditions == [condition]
        assert not_condition.url == URL(None)

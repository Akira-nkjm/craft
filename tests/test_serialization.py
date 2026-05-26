"""Unit tests for core.serialization.to_jsonable."""

from pathlib import Path

from pydantic import BaseModel

from core.serialization import to_jsonable


class _Model(BaseModel):
    x: int
    y: str = "hello"


def test_primitives_returned_as_is():
    assert to_jsonable(None) is None
    assert to_jsonable(True) is True
    assert to_jsonable(42) == 42
    assert to_jsonable(3.14) == 3.14
    assert to_jsonable("hello") == "hello"


def test_dict_keys_stringified():
    result = to_jsonable({1: "a", "b": 2})
    assert result == {"1": "a", "b": 2}


def test_dict_values_recursed():
    result = to_jsonable({"path": Path("/tmp/foo"), "nums": [1, 2]})
    assert result == {"path": "/tmp/foo", "nums": [1, 2]}


def test_list_recursed():
    result = to_jsonable([1, "two", Path("/x")])
    assert result == [1, "two", "/x"]


def test_tuple_to_list():
    result = to_jsonable((1, 2, 3))
    assert result == [1, 2, 3]


def test_set_to_list():
    result = to_jsonable({42})
    assert isinstance(result, list)
    assert result == [42]


def test_frozenset_to_list():
    result = to_jsonable(frozenset({"a"}))
    assert result == ["a"]


def test_path_to_str():
    assert to_jsonable(Path("/home/user/data.toml")) == "/home/user/data.toml"


def test_basemodel_dumped():
    m = _Model(x=7)
    result = to_jsonable(m)
    assert result == {"x": 7, "y": "hello"}


def test_type_returns_name():
    assert to_jsonable(int) == "int"
    assert to_jsonable(str) == "str"


def test_callable_returns_repr():
    def my_func():
        pass

    result = to_jsonable(my_func)
    assert "my_func" in result


def test_unknown_object_falls_back_to_str():
    class _Weird:
        def __str__(self):
            return "weird"

    assert to_jsonable(_Weird()) == "weird"


def test_nested_structure():
    result = to_jsonable({"items": [Path("/a"), {True: _Model(x=1)}]})
    assert result == {"items": ["/a", {"True": {"x": 1, "y": "hello"}}]}

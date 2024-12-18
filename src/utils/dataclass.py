import functools
from dataclasses import dataclass, fields, is_dataclass
from types import GenericAlias
from typing import Callable, Self, Sequence, TypeVar, get_origin, Union, get_args


class DecodeToDataclassException(Exception):
    pass


def try_extract_underlying_type_from_optional(field):
    args = get_args(field)
    types = [x for x in args if x != type(None)]
    if get_origin(field) is Union and type(None) in args and len(types) == 1:
        return types[0]
    return None


@dataclass
class Nested:
    """
    Base class for dataclasses that converts all inner dicts into dataclasses
    Also works with lists of dataclasses
    """

    def __post_init__(self):
        for field in fields(self):
            if isinstance(field.type, GenericAlias):
                field_type = field.type.__args__[0]
                if is_dataclass(field_type):
                    factory = self.__get_dataclass_factory(field_type)
                    setattr(
                        self,
                        field.name,
                        field.type.__origin__(
                            map(lambda x: factory(**x) if not is_dataclass(x) else x, getattr(self, field.name))
                        ),
                    )
            elif is_dataclass(field.type) and not is_dataclass(getattr(self, field.name)):
                factory = self.__get_dataclass_factory(field.type)
                setattr(self, field.name, factory(**getattr(self, field.name)))
            elif getattr(self, field.name) and (underlying := try_extract_underlying_type_from_optional(field.type)):
                factory = self.__get_dataclass_factory(underlying)
                setattr(self, field.name, factory(**getattr(self, field.name)))

    @staticmethod
    def __get_dataclass_factory(field_type):
        if issubclass(field_type, FromResponse):
            return field_type.from_response
        return field_type


T = TypeVar('T')


@dataclass
class FromResponse:
    """
    Class for extending dataclass with custom from_response method, ignored extra fields
    """

    @classmethod
    def from_response(cls, **kwargs) -> Self:
        class_field_names = [field.name for field in fields(cls)]
        return cls(**{k: v for k, v in kwargs.items() if k in class_field_names})


def list_of_dataclasses(
    _dataclass_factory: Callable[..., T]
) -> Callable[[Callable[..., Sequence]], Callable[..., list[T]]]:
    """Decorator to transform list of dicts from func response to list of dataclasses"""

    def decorator(func: Callable[..., Sequence]) -> Callable[..., list[T]]:
        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            list_of_elements = func(*args, **kwargs)

            if isinstance(list_of_elements[0], dict):
                return list(map(lambda x: _dataclass_factory(**x), list_of_elements))

            raise DecodeToDataclassException(f'Type {type(list_of_elements[0])} is not supported.')

        return wrapper_decorator

    return decorator

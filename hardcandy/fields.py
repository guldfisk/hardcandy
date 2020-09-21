import datetime
import typing as t

from enum import Enum as _Enum
from distutils.util import strtobool

from hardcandy.schema import Field, ValidationError


class Integer(Field[int]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')

    def deserialize(self, value: t.Any) -> int:
        try:
            _value = int(value)
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))
        if self._min is not None and _value < self._min or self._max is not None and _value > self._max:
            raise ValidationError(
                self,
                'invalid value "{}": not in allowed range({} - {})'.format(
                    _value,
                    self._min,
                    self._max,
                )
            )
        return _value


class Bool(Field[bool]):

    def deserialize(self, value: t.Any) -> bool:
        try:
            _value = strtobool(str(value))
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))
        return _value


class Text(Field[str]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')

    def deserialize(self, value: t.Any) -> str:
        try:
            _value = str(value)
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))
        if self._min is not None and len(_value) < self._min or self._max is not None and len(_value) > self._max:
            raise ValidationError(
                self,
                'invalid value "{}": not in allowed range({} - {})'.format(
                    len(_value),
                    self._min,
                    self._max,
                )
            )
        return _value


class Enum(Field[_Enum]):

    def __init__(self, enum: t.Type[_Enum], **kwargs):
        super().__init__(**kwargs)
        self._enum = enum

    def serialize(self, value: _Enum) -> t.Any:
        return value.name

    def deserialize(self, value: t.Any) -> _Enum:
        try:
            _value = self._enum[str(value)]
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))
        return _value


class Datetime(Field[datetime.datetime]):

    def __init__(self, time_format: str = '%d/%m/%Y %H:%M:%S', **kwargs):
        super().__init__(**kwargs)
        self._time_format = time_format

    def serialize(self, value: datetime.datetime) -> t.Any:
        try:
            return value.strftime(self._time_format)
        except AttributeError:
            return None

    def deserialize(self, value: t.Any) -> datetime.datetime:
        try:
            _value = datetime.datetime.strptime(value, self._time_format)
        except (ValueError, TypeError):
            raise ValidationError(self, 'invalid value "{}"'.format(value))
        return _value

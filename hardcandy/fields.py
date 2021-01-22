import datetime
import typing as t

from enum import Enum as _Enum
from distutils.util import strtobool

from hardcandy.schema import Field, ValidationError, T, Primitive


class Integer(Field[int]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')

    def deserialize(self, value: Primitive) -> int:
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

    def deserialize_naive(self, value: Primitive) -> T:
        return int(value)


class Float(Field[float]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')
        self._max_precision = kwargs.get('max_precision')

    def serialize(self, value: T, instance: object) -> Primitive:
        if self._max_precision is None:
            return str(value)
        return str(round(value, self._max_precision))

    def deserialize(self, value: Primitive) -> T:
        try:
            _value = float(value)
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

    def deserialize_naive(self, value: Primitive) -> T:
        return float(value)


class Bool(Field[bool]):

    def deserialize(self, value: Primitive) -> bool:
        try:
            return strtobool(str(value))
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))

    def deserialize_naive(self, value: Primitive) -> T:
        return value


class Text(Field[str]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')

    def deserialize(self, value: Primitive) -> str:
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

    def deserialize_naive(self, value: Primitive) -> T:
        return value


class Enum(Field[_Enum]):

    def __init__(self, enum: t.Type[_Enum], **kwargs):
        super().__init__(**kwargs)
        self._enum = enum

    def serialize(self, value: _Enum, instance: object) -> Primitive:
        return value.name

    def deserialize(self, value: Primitive) -> _Enum:
        try:
            return self._enum[str(value)]
        except ValueError:
            raise ValidationError(self, 'invalid value "{}"'.format(value))


class Datetime(Field[datetime.datetime]):

    def __init__(self, time_format: str = '%d/%m/%Y %H:%M:%S', **kwargs):
        super().__init__(**kwargs)
        self._time_format = time_format

    def serialize(self, value: datetime.datetime, instance: object) -> Primitive:
        try:
            return value.strftime(self._time_format)
        except AttributeError:
            return None

    def deserialize(self, value: Primitive) -> datetime.datetime:
        try:
            return datetime.datetime.strptime(value, self._time_format)
        except (ValueError, TypeError):
            raise ValidationError(self, 'invalid value "{}"'.format(value))


class Lambda(Field[T]):

    def __init__(self, extractor: t.Callable[[object], Primitive], **kwargs):
        kwargs['unbound'] = True
        kwargs['read_only'] = True
        super().__init__(**kwargs)
        self._extractor = extractor

    def deserialize(self, value: Primitive) -> T:
        raise NotImplemented()

    def serialize(self, value: T, instance: object) -> Primitive:
        return self._extractor(instance)

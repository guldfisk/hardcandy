import datetime
import re
import typing as t
from distutils.util import strtobool
from enum import Enum as _Enum

from hardcandy.schema import Field, FieldValidationError, T, Primitive, Schema, BaseValidationError


class Integer(Field[int]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')

    @property
    def min(self) -> int:
        return self._min

    @property
    def max(self) -> int:
        return self._max

    def deserialize(self, value: Primitive, schema: Schema) -> int:
        try:
            _value = int(value)
        except (ValueError, TypeError):
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))
        if self._min is not None and _value < self._min or self._max is not None and _value > self._max:
            raise FieldValidationError(
                self,
                'invalid value "{}": not in allowed range({} - {})'.format(
                    _value,
                    self._min,
                    self._max,
                )
            )
        return _value

    def deserialize_naive(self, value: Primitive, schema: Schema) -> T:
        return int(value)


class Float(Field[float]):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')
        self._max_precision = kwargs.get('max_precision')

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        if self._max_precision is None:
            return str(value)
        return str(round(value, self._max_precision))

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        try:
            _value = float(value)
        except (ValueError, TypeError):
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))
        if self._min is not None and _value < self._min or self._max is not None and _value > self._max:
            raise FieldValidationError(
                self,
                'invalid value "{}": not in allowed range({} - {})'.format(
                    _value,
                    self._min,
                    self._max,
                )
            )
        return _value

    def deserialize_naive(self, value: Primitive, schema: Schema) -> T:
        return float(value)


class Bool(Field[bool]):

    def deserialize(self, value: Primitive, schema: Schema) -> bool:
        try:
            return strtobool(str(value))
        except (ValueError, TypeError):
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))

    def deserialize_naive(self, value: Primitive, schema: Schema) -> T:
        return value


class Text(Field[str]):

    def __init__(self, pattern: t.Optional[re.Pattern] = None, **kwargs):
        super().__init__(**kwargs)
        self._min = kwargs.get('min')
        self._max = kwargs.get('max')
        self._pattern = pattern

    def deserialize(self, value: Primitive, schema: Schema) -> str:
        if value is None:
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))

        try:
            _value = str(value)
        except (ValueError, TypeError):
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))

        if self._min is not None and len(_value) < self._min or self._max is not None and len(_value) > self._max:
            raise FieldValidationError(
                self,
                'invalid value "{}": not in allowed range({} - {})'.format(
                    len(_value),
                    self._min,
                    self._max,
                )
            )

        if self._pattern is not None and not self._pattern.match(_value):
            raise FieldValidationError(self, 'Value "{}" does not match pattern "{}"'.format(_value, self._pattern))

        return _value

    def deserialize_naive(self, value: Primitive, schema: Schema) -> T:
        return value


class MultiChoiceField(Field[str]):

    def __init__(self, choices: t.AbstractSet[str], soft_match: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._choices = choices
        self._soft_match = soft_match

    def deserialize(self, value: Primitive, schema: Schema) -> str:
        value = str(value)
        if value in self._choices:
            return value
        if self._soft_match:
            options = []
            value = value.lower()
            for v in self._choices:
                if value in v.lower():
                    options.append(v)
            if len(options) == 1:
                return options[0]
        raise FieldValidationError(self, 'invalid value "{}"'.format(value))


class Enum(Field[_Enum]):

    def __init__(self, enum: t.Type[_Enum], soft_match: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._enum = enum
        self._soft_match = soft_match

    def serialize(self, value: _Enum, instance: object, schema: Schema) -> Primitive:
        return value.name

    def deserialize(self, value: Primitive, schema: Schema) -> _Enum:
        value = str(value)
        try:
            return self._enum[value]
        except KeyError:
            if self._soft_match:
                options = []
                value = value.lower()
                for v in self._enum:
                    if value in v.name.lower():
                        options.append(v)
                if len(options) == 1:
                    return options[0]
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))


class Datetime(Field[datetime.datetime]):

    def __init__(self, time_format: str = '%d/%m/%Y %H:%M:%S', **kwargs):
        super().__init__(**kwargs)
        self._time_format = time_format

    def serialize(self, value: datetime.datetime, instance: object, schema: Schema) -> Primitive:
        try:
            return value.strftime(self._time_format)
        except AttributeError:
            return None

    def deserialize(self, value: Primitive, schema: Schema) -> datetime.datetime:
        try:
            return datetime.datetime.strptime(value, self._time_format)
        except (ValueError, TypeError):
            raise FieldValidationError(self, 'invalid value "{}"'.format(value))


class List(Field[T]):

    def __init__(self, field: Field, **kwargs):
        super().__init__(**kwargs)
        self._field = field

    def update_name(self, name: str) -> None:
        super().update_name(name)
        self._field.update_name(self.name)

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return [
            self._field.serialize(item, instance, schema)
            for item in
            value
        ]

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        if not isinstance(value, t.Iterable) or isinstance(value, str):
            raise FieldValidationError(self, 'Expected list')

        return [
            self._field.deserialize(item, schema)
            for item in
            value
        ]


class Related(Field[T]):

    def __init__(self, schema: Schema, **kwargs):
        super().__init__(**kwargs)
        self._schema = schema

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return self._schema.serialize(value)

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        try:
            return self._schema.deserialize_raw(value)
        except BaseValidationError as e:
            raise FieldValidationError(self, e.serialized)


class SelfRelated(Field[T]):

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return schema.serialize(value)

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        try:
            return schema.deserialize_raw(value)
        except BaseValidationError as e:
            raise FieldValidationError(self, e.serialized)


class Lambda(Field[T]):

    def __init__(self, extractor: t.Callable[[object], Primitive], **kwargs):
        kwargs['unbound'] = True
        kwargs['read_only'] = True
        super().__init__(**kwargs)
        self._extractor = extractor

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        raise NotImplemented()

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return self._extractor(instance)


class CoalesceField(Field[T]):

    def __init__(self, fields: t.Sequence[Field], **kwargs):
        super().__init__(**kwargs)
        self._fields = fields

    def update_name(self, name: str) -> None:
        super().update_name(name)
        for field in self._fields:
            field.update_name(self.name)

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return self._fields[0].serialize(value, instance, schema)

    def deserialize(self, value: Primitive, schema: Schema) -> T:
        for field in self._fields[:-1]:
            try:
                return field.deserialize(value, schema)
            except FieldValidationError:
                pass

        return self._fields[-1].deserialize(value, schema)

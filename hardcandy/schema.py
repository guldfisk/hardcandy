from __future__ import annotations

import copy
import typing as t

from abc import ABCMeta, abstractmethod

from yeetlong.maps import IndexedOrderedDict


T = t.TypeVar('T')

Primitive = t.Union[None, str, int, float, bool]
Serialized = t.Mapping[str, Primitive]


class CandyError(Exception):
    pass


class SerializationError(CandyError):
    pass


class DeserializationError(CandyError):

    def __init__(self, errors: t.Sequence[ValidationError]) -> None:
        super().__init__()
        self._errors = errors

    @property
    def errors(self) -> t.Sequence[ValidationError]:
        return self._errors

    @property
    def serialized(self):
        return {
            'errors': [
                (error.field.name, error.reason)
                for error in
                self._errors
            ]
        }


class ValidationError(CandyError):

    def __init__(self, field: Field, reason: str) -> None:
        super().__init__()
        self._field = field
        self._reason = reason

    @property
    def field(self) -> Field:
        return self._field

    @property
    def reason(self) -> str:
        return self._reason


class Field(t.Generic[T]):
    name: str
    display_name: str
    required: bool
    read_only: bool
    write_only: bool
    default: t.Optional[T]
    unbound: bool

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.display_name = kwargs.get('display_name')
        self.required = kwargs.get('required', True)
        self.read_only = kwargs.get('read_only', False)
        self.write_only = kwargs.get('write_only', False)
        self.default = kwargs.get('default', None)
        self.unbound = kwargs.get('unbound', False)

    def serialize(self, value: T, instance: object) -> Primitive:
        return value

    @abstractmethod
    def deserialize(self, value: Primitive) -> T:
        pass

    def deserialize_naive(self, value: Primitive) -> T:
        return self.deserialize(value)

    def extract(self, instance: object) -> Primitive:
        if self.unbound:
            return self.serialize(None, instance)
        return self.serialize(getattr(instance, self.name), instance)


class SchemaMeta(ABCMeta):
    fields: IndexedOrderedDict[str, Field]

    def __new__(mcs, classname, base_classes, attributes):
        fields = IndexedOrderedDict()

        for key, attribute in attributes.items():
            if isinstance(attribute, Field):
                if attribute.name is None:
                    attribute.name = key
                if attribute.display_name is None:
                    attribute.display_name = ' '.join(v.capitalize() for v in attribute.name.split('_'))
                fields[attribute.name] = attribute

        attributes['fields'] = fields

        klass = type.__new__(mcs, classname, base_classes, attributes)

        return klass


class Schema(t.Generic[T], metaclass = SchemaMeta):

    def __init__(self, fields: t.Optional[t.Mapping[str, Field]] = None):
        if fields is not None:
            self.fields = copy.copy(self.fields)
            self.fields.update(fields)

    @property
    def default(self) -> Serialized:
        return {
            name: field.default
            for name, field in
            self.fields.items()
        }

    def serialize(self, instance: object) -> Serialized:
        return {
            field.name: field.extract(instance)
            for field in
            self.fields.values()
            if not field.write_only
        }

    def deserialize_raw(self, serialized: Serialized) -> Serialized:
        errors = []
        values = {}
        for name, field in self.fields.items():
            if field.read_only:
                continue

            try:
                value = serialized[name]
            except KeyError:
                if field.default is not None:
                    value = field.default
                else:
                    if field.required:
                        errors.append(ValidationError(field, 'missing required value'))
                    continue

            try:
                values[name] = field.deserialize(value)
            except ValidationError as e:
                errors.append(e)

        if errors:
            raise DeserializationError(errors)

        return values

    def deserialize(self, serialized: Serialized) -> T:
        return t.get_args(self.__class__.__orig_bases__[0])[0](**self.deserialize_raw(serialized))

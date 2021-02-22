from __future__ import annotations

import copy
import typing as t

from abc import ABCMeta, abstractmethod

from yeetlong.maps import IndexedOrderedDict


T = t.TypeVar('T')

# Primitive = t.Union[None, str, int, float, bool]
Primitive = t.Any
Serialized = t.Mapping[str, Primitive]


class CandyError(Exception):
    pass


class SerializationError(CandyError):
    pass


class BaseValidationError(CandyError):

    @property
    @abstractmethod
    def serialized(self) -> t.Any:
        pass


class DeserializationError(BaseValidationError):

    def __init__(self, errors: t.Sequence[BaseValidationError]) -> None:
        super().__init__()
        self._errors = errors

    @property
    def errors(self) -> t.Sequence[BaseValidationError]:
        return self._errors

    @property
    def serialized(self):
        return {
            'errors': [
                error.serialized
                for error in
                self._errors
            ]
        }


class ValidationError(BaseValidationError):

    def __init__(self, reason: str) -> None:
        super().__init__()
        self._reason = reason

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def serialized(self) -> t.Any:
        return {
            'error': self._reason,
        }


class FieldValidationError(BaseValidationError):

    def __init__(self, field: Field, reason: t.Any) -> None:
        super().__init__()
        self._field = field
        self._reason = reason

    @property
    def field(self) -> Field:
        return self._field

    @property
    def reason(self) -> t.Any:
        return self._reason

    @property
    def serialized(self) -> t.Any:
        return {
            'field': self._field.name,
            'error': self._reason,
        }


NO_DEFAULT_MARKER = object()


class Field(t.Generic[T]):
    name: str
    display_name: str
    required: bool
    read_only: bool
    write_only: bool
    default: t.Optional[T]
    unbound: bool
    deserialize_none: bool

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.display_name = kwargs.get('display_name')
        self.required = kwargs.get('required', True)
        self.read_only = kwargs.get('read_only', False)
        self.write_only = kwargs.get('write_only', False)
        self.default = kwargs.get('default', NO_DEFAULT_MARKER)
        self.unbound = kwargs.get('unbound', False)
        self.source = kwargs.get('source')
        self.deserialize_none = kwargs.get('deserialize_none', False)

    def update_name(self, name: str) -> None:
        if self.name is None:
            self.name = name
        if self.display_name is None:
            self.display_name = ' '.join(v.capitalize() for v in self.name.split('_'))
        if self.source is None:
            self.source = self.name

    def serialize(self, value: T, instance: object, schema: Schema) -> Primitive:
        return value

    @abstractmethod
    def deserialize(self, value: Primitive, schema: Schema) -> T:
        pass

    def deserialize_naive(self, value: Primitive, schema: Schema) -> T:
        return self.deserialize(value, schema)

    def extract(self, instance: object, schema: Schema) -> Primitive:
        if self.unbound:
            return self.serialize(None, instance, schema)
        return self.serialize(getattr(instance, self.source), instance, schema)


class SchemaMeta(ABCMeta):
    fields: IndexedOrderedDict[str, Field]

    def __new__(mcs, classname, base_classes, attributes):
        fields = IndexedOrderedDict()

        for base_class in reversed(base_classes):
            if issubclass(type(base_class), SchemaMeta):
                for k, v in base_class.fields.items():
                    fields[k] = copy.copy(v)

        for key, attribute in attributes.items():
            if isinstance(attribute, Field):
                attribute.update_name(key)
                fields[attribute.name] = attribute

        attributes['fields'] = fields

        klass = type.__new__(mcs, classname, base_classes, attributes)

        return klass


class Schema(t.Generic[T], metaclass = SchemaMeta):

    def __init__(self, fields: t.Optional[t.Mapping[str, Field]] = None):
        if fields is not None:
            self.fields = copy.copy(self.fields)
            for name, field in fields.items():
                field.update_name(name)
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
            field.name: field.extract(instance, self)
            for field in
            self.fields.values()
            if not field.write_only
        }

    def deserialize_raw(self, serialized: Serialized) -> Serialized:
        errors = []
        values = {}

        if not isinstance(serialized, t.Mapping):
            raise DeserializationError((ValidationError('invalid input format'),))

        for field in self.fields.values():
            if field.read_only:
                continue

            value = serialized.get(field.name)

            if value is None:
                if field.default is not NO_DEFAULT_MARKER:
                    value = field.default
                else:
                    if field.required:
                        errors.append(FieldValidationError(field, f'missing required value "{field.name}"'))
                    continue

            try:
                if value is None and not field.deserialize_none:
                    values[field.source] = None
                else:
                    values[field.source] = field.deserialize(value, self)
            except BaseValidationError as e:
                errors.append(e)

        if errors:
            raise DeserializationError(errors)

        return values

    def deserialize(self, serialized: Serialized) -> T:
        return t.get_args(self.__class__.__orig_bases__[0])[0](**self.deserialize_raw(serialized))

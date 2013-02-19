
__author__ = 'andrewshkovskii'

from django.core.serializers.pyyaml import Serializer as YAMLSerializer, Deserializer
from django.utils.encoding import smart_unicode

class Serializer(YAMLSerializer):
    """
    This serializer will simply handle custom thought m2m models;
    But you need sure for registering thought model with reversion
    """
    def handle_m2m_field(self, obj, field):
        if self.use_natural_keys and hasattr(field.rel.to, 'natural_key'):
            m2m_value = lambda value: value.natural_key()
        else:
            m2m_value = lambda value: smart_unicode(value._get_pk_val(), strings_only=True)
        self._current[field.name] = [m2m_value(related)
                                     for related in getattr(obj, field.name).iterator()]
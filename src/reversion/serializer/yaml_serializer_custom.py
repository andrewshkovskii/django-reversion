from django.core.serializers.pyyaml import Serializer as YAMLSerializer, Deserializer as original_Deserializer
from django.core.serializers.base import DeserializedObject
from django.utils.encoding import smart_unicode
from django.db import models


class Serializer(YAMLSerializer):
    """
    This serializer will simply handle custom thought m2m models;
    But you need sure for registering thought model with reversion
    """
    def handle_m2m_field(self, obj, field):
        # save m2m custom through for diff generation
        if self.use_natural_keys and hasattr(field.rel.to, 'natural_key'):
            m2m_value = lambda value: value.natural_key()
        else:
            m2m_value = lambda value: smart_unicode(value._get_pk_val(), strings_only=True)
        self._current[field.name] = [m2m_value(related)
                                     for related in getattr(obj, field.name).iterator()]


class CustomDeserializedObject(DeserializedObject):

    def save(self, save_m2m=True, using=None):
        from reversion.revisions import default_revision_manager
        # Call save on the Model baseclass directly. This bypasses any
        # model-defined save. The save is also forced to be raw.
        # raw=True is passed to any pre/post_save signals.
        if self.object.__class__._base_manager.using(using).filter(pk=self.object.pk).exists():
            exclude = default_revision_manager.get_adapter(self.object.__class__).exclude
            update_fields = [name for name in self.object.__class__._meta.get_all_field_names() if name not in exclude]
            models.Model.save_base(self.object, using=using, raw=True, update_fields=update_fields)
        else:
            models.Model.save_base(self.object, using=using, raw=True)
        if self.m2m_data and save_m2m:
            for accessor_name, object_list in self.m2m_data.items():
                # Skip custom through, because it already registered in reversion by us
                if getattr(self.object, accessor_name).through._meta.auto_created:
                    setattr(self.object, accessor_name, object_list)
        # prevent a second (possibly accidental) call to save() from saving
        # the m2m data twice.
        self.m2m_data = None


def Deserializer(stream_or_string, **options):
    for obj in original_Deserializer(stream_or_string, **options):
        yield CustomDeserializedObject(obj.object, obj.m2m_data)
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from myproject.models import AdminLog


def to_json_safe(data):
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def serialize_instance(instance, m2m_fields=None):
    """Серіалізує модель у словник для зручного збереження в AdminLog."""
    m2m_fields = m2m_fields or []
    data = model_to_dict(instance, fields=[field.name for field in instance._meta.fields])

    for field_name in m2m_fields:
        manager = getattr(instance, field_name, None)
        if manager is not None:
            data[field_name] = list(manager.values_list("id", flat=True))

    return to_json_safe(data)


def querystring_without_page(request):
    query = request.GET.copy()
    query.pop("page", None)
    return query.urlencode()


def write_admin_log(admin, action, entity_type, entity_id, old_data=None, new_data=None, request=None):
    AdminLog.objects.create(
        admin=admin,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )

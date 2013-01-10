from tenclouds.crud.qfilters import BaseFilter
from django.db.models import Q


class IntegerFilter(BaseFilter):
    field_type = 'integer'

    def __init__(self, key, name, filters):
        self.key = key
        self.filter = filters
        self.name = name

    def affected_by(self, key):
        return key.startswith(self.key)

    def build_filters(self, raw_key):
        try:
            val = int(raw_key.rsplit(':', 1)[1])
        except TypeError:
            return Q()

        return Q(**{self.filter: val})

    def to_raw_field(self):
        return {
            'key': self.key,
            'name': self.name,
            'type': self.field_type,
        }

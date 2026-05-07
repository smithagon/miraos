import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def json_dumps(obj, **kwargs):
    """Utility to dump JSON with datetime support."""
    if 'cls' not in kwargs:
        kwargs['cls'] = DateTimeEncoder
    return json.dumps(obj, **kwargs)

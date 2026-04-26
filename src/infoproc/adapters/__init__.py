from infoproc.adapters.base import InputAdapter
from infoproc.adapters.document import DocumentInputAdapter
from infoproc.adapters.media import MediaInputAdapter
from infoproc.adapters.placeholder import ImageInputAdapter, WebInputAdapter
from infoproc.adapters.text import TextInputAdapter

__all__ = [
    "DocumentInputAdapter",
    "ImageInputAdapter",
    "InputAdapter",
    "MediaInputAdapter",
    "TextInputAdapter",
    "WebInputAdapter",
]

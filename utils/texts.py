#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from json import loads
from typing import Any, Union


class Text(str):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.format(*args, **kwds)


class TextsSection(dict):
    def __getattr__(self, __name: str) -> Union["TextsSection", Text]:
        if __name not in self:
            return super().__getattribute__(__name)

        item = self[__name]
        if isinstance(item, dict):
            return TextsSection(**item)
        elif isinstance(item, str):
            return Text(item)
        else:
            return item


class AllTexts:
    _texts = None

    def __getattr__(self, __name: str) -> TextsSection | Text:
        if not self._texts:
            with open("texts.json", encoding="utf-8") as f:
                self._texts = loads(f.read())

        if __name not in self._texts:
            raise AttributeError(__name)

        item = self._texts[__name]
        if isinstance(item, dict):
            return TextsSection(**item)
        elif isinstance(item, str):
            return Text(item)
        else:
            return item

Texts = AllTexts()

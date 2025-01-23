#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import re
from json import loads
from typing import Any, Union


class Text(str):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return Text(self.format(*args, **kwds))

    @property
    def without_html(self):
        return Text(re.sub(r"<[^>]*>", "", self))


def parse(item: Union[dict, str], self) -> Union["TextsSection", Text, Any]:
    if isinstance(item, dict):
        return TextsSection(**item)
    elif isinstance(item, str):
        text = Text(item)
        for x in re.findall(r"\{self\.[^}]*}", text):
            text = text.replace(x, x.format(self=self))
        for x in re.findall(r"\{root\.[^}]*}", text):
            text = text.replace(x, x.format(root=Texts))
        for x in re.findall(r"<root\.[^>]*>", text):
            text = text.replace(x, x.format(root=Texts))
        for x in re.findall(r"<!(.+):(.+)>", text):
            if "." in x[1]:
                attr = getattr(__import__(x[0], globals(), locals(), [x[1].split(".")[0]]), x[1].split(".")[0])
                for i in x[1].split(".")[1:]:
                    if i == "__CALL__":
                        attr = attr()
                    else:
                        attr = getattr(attr, i)
            else:
                attr = getattr(__import__(x[0], globals(), locals(), [x[1]]), x[1])

            if ("<!" + ":".join(x) + ">") == item:
                return attr

            attr = getattr(__import__(x[0], globals(), locals(), [x[1].split(".")[0]]), x[1].split(".")[0])
            text = text.replace("<!" + ":".join(x) + ">", str(attr))
        return Text(text)
    else:
        return item


class TextsSection(dict):
    def __getattr__(self, __name: str) -> Union["TextsSection", Text]:
        __name = __name.replace("__", ":")
        if __name not in self:
            return super().__getattribute__(__name) or Text(f"Text {__name} not found :(")

        item = self[__name]
        return parse(item, self)


class TextsData:
    _texts = None

    @staticmethod
    def reload(*args, **kwargs):
        with open("core/misc/texts.json", encoding="utf-8") as f:
            TextsData._texts = loads(f.read())

    def __getattr__(self, __name: str) -> TextsSection | Text:
        __name = __name.replace("__", ":")
        if not self._texts:
            TextsData.reload()

        if __name not in self._texts:
            return Text(f"Text {__name} not found :(")

        item = self._texts[__name]
        return parse(item, self)


Texts = TextsData()

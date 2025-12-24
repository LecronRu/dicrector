import sys
from itertools import chain
from pathlib import Path
from typing import Iterable

from .components import ProcessLevel, Depends
from .textparse import Line

chain_iter = chain.from_iterable


class Formats:
    items = {}

    @classmethod
    def register(cls, module_path: Path):
        name = module_path.stem
        if name not in cls.items:
            cls.items[name] = module_path

    @classmethod
    def register_all(cls, dir_path: Path):
        for module_path in dir_path.iterdir():
            if module_path.is_dir():
                cls.register(module_path)

    @classmethod
    def register_default(cls):
        # TODO имя папки при оформлении кода в виде библиотеки
        format_path = Path(__file__).parent / 'formats'
        cls.register_all(format_path)

    @classmethod
    def format(cls, name: str) -> Depends:
        depends = cls.items[name]
        if isinstance(depends, Path):
            depends = cls._load(depends)
            cls.items[name] = depends
        return depends

    @staticmethod
    def _load(module_path: Path) -> Depends:
        path = str(module_path.parent.resolve())
        if path not in sys.path:
            sys.path.append(path)
        module = __import__(module_path.name)
        depends = module.depends
        return depends


class Corrector:
    def __init__(self, dictionary_names: Iterable[str|Path]):
        self.dictionaries = [self._load(name) for name in dictionary_names]

    @staticmethod
    def _load(name: str|Path):  # -> tuple[Dictionary, ProcessLevel]
        name = Path(name)
        format_ =  name.suffix[1:]
        depends = Formats.format(format_)
        dictionary = depends.dict_maker(name, depends)
        return dictionary, depends.level

    def execute(self, line: str) -> str:
        # ВНИМАНИЕ: метод при разбиении на предложения и обратной сборке, теряет linefeed ('\n')
        line = Line.from_str(line)
        for dct, level in self.dictionaries:
            if level == ProcessLevel.line:
                tokens = (line,)
            elif level == ProcessLevel.sent:
                tokens = line.childs
            else:  # уровень part дополнительно обрабатывается как word (word+part)
                words = (s.childs for s in line.childs)
                words = tuple(chain_iter(words))
                tokens = words
                if level == ProcessLevel.part:
                    parts = chain_iter(w.childs for w in words)
                    tokens = chain(words, parts)

            for t in tokens:
                dct.apply(t)

        return line.text


Formats.register_default()

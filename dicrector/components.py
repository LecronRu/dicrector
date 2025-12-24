import operator
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from types import ModuleType
from typing import Protocol, Callable, Self, Optional, Generator

from .indexer import IIndexed, Indexer, Wildcard
from .loaders import LoadDepends, TPatternData, TTargetData


class ITextNode(Protocol):
    text: str


# ========== Pattern ==================================================================
class IPattern(Protocol):
    def match(self, string: str) -> bool: ...
    def replace(self, replace: str, string: str) -> str: ...


# noinspection PyUnusedLocal
class PatternFake:
    @staticmethod
    def match(string: str) -> bool:
        return True

    @staticmethod
    def replace(replace: str, string: str) -> str:
        return replace


class PatternConst:
    __slots__ = ('_pattern', 'case_sensitive')
    wildcard = Wildcard.none
    def __init__(self, pattern: str, case_sensitive: bool):
        self._pattern = pattern
        self.case_sensitive = case_sensitive

    @classmethod
    def from_str(cls, pattern: str) -> Self:
        case_sensitive = pattern[0] == '$'
        if case_sensitive:
            pattern = pattern[case_sensitive:]
        else:
            pattern = pattern.lower()
        return cls(pattern, case_sensitive)

    @property
    def key(self):
        return self._pattern

    def match(self, string: str) -> bool:
        if not self.case_sensitive:
            string = string.lower()
        return self._pattern == string

    # noinspection PyUnusedLocal
    @staticmethod
    def replace(replace: str, string: str) -> str:
        return replace


class PatternWildcard(PatternConst):
    def __init__(self, pattern: str, case_sensitive: bool, wildcard: Wildcard):
        super().__init__(pattern, case_sensitive)
        if wildcard == Wildcard.none:
            self._compare = operator.eq
            # замену оставляем на предка
        elif wildcard == Wildcard.right:
            self._compare = str.startswith
            self.replace = self._replace_wc_right
        elif wildcard == Wildcard.left:
            self._compare = str.endswith
            self.replace = self._replace_wc_left
        else:  # Wildcard.both
            self._compare = operator.contains
            self.replace = self._replace_wc_right
        self.wildcard = wildcard

    @classmethod
    def from_str(cls, pattern: str) -> Self:
        case_sensitive = pattern[0] == '$'
        wcl = pattern[case_sensitive] == '*'
        wcr = pattern[-1] == '*'
        start = case_sensitive + wcl
        if start or wcr:
            stop = -1 if wcr else None
            pattern = pattern[start:stop]
        if not case_sensitive:
            pattern = pattern.lower()
        wildcard = (wcl, wcr)
        return cls(pattern, case_sensitive, Wildcard(wildcard))

    @property
    def key(self):
        return self._pattern

    def match(self, string: str) -> bool:
        if not self.case_sensitive:
            string = string.lower()
        return self._compare(string, self._pattern)

    def _replace_wc_left(self, replace: str, string: str) -> str:
        if not self.case_sensitive:
            string = string.lower()
        rule_char_count = len(self._pattern)
        return string[:-rule_char_count] + replace

    def _replace_wc_right(self, replace: str, string: str) -> str:  # также both
        if not self.case_sensitive:
            string = string.lower()
        return string.replace(self._pattern, replace, 1)


class PatternRe:
    __slots__ = ('match', 'replace')
    def __init__(self, pattern: str, case_sensitive: bool):
        pattern = pattern.replace(' ', '\s')
        flags = 0 if case_sensitive else re.IGNORECASE
        re_pattern = re.compile(pattern, flags=flags)
        self.match = re_pattern.search
        self.replace = re_pattern.sub

    @classmethod
    def from_str(cls, pattern: str) -> Self:
        case_sensitive = pattern[0] == '$'
        if case_sensitive:
            pattern = pattern[case_sensitive:]
        return cls(pattern, case_sensitive)


# ========== Rule =====================================================================
class ITargetResolved(Protocol):
    def __call__(self, node: ITextNode) -> str | None: ...


class Rule:
    """Правило заменяющее найденный шаблон на фиксированный текст"""
    __slots__ = ('pattern', 'target')
    def __init__(self, pattern: IPattern|IIndexed, target: str|ITargetResolved):
        self.pattern = pattern
        self.target = target

    @classmethod
    def from_(cls, pattern_data, target_data, depends: 'Depends', dct_module):
        pattern = depends.pattern_maker(*pattern_data)
        target_maker = depends.target_maker
        target = target_maker(target_data, dct_module) if target_maker else target_data[0]
        return cls(pattern, target)

    def apply(self, node: ITextNode):
        target = self.target
        node.text = self.pattern.replace(target, node.text)


class RuleResolved(Rule):
    """Правило заменяющее найденный шаблон на текст, полученный на основе обработки содержимого обрабатываемой ноды"""
    def apply(self, node: ITextNode):
        target = self.target(node)
        if target is not None:  # resolver имеет тип Optional[str]
            node.text = self.pattern.replace(target, node.text)


# ========== Dictionary ===============================================================
TModuleLoader = Callable[[], Optional[ModuleType]]

# TODO возможно надо кеширование @cache
def side_module(dct_path: Path) -> TModuleLoader:
    """Ленивая загрузка модуля функций словаря. Имя файла модуля для словаря test.dic, должно быть test_dic.py"""
    module = 'None'  # строка, по причине опциональности значения, допускает None
    def _lazy_import() -> Optional[ModuleType]:
        nonlocal module
        if module != 'None':
            # noinspection PyTypeChecker
            return module
        path = dct_path.resolve()
        name = path.name.replace('.', '_')
        full_path = path.parent / (name + '.py')
        if full_path.exists():
            parent = str(path.parent)
            if parent not in sys.path:
                sys.path.append(parent)
            module = __import__(name)
        else:
            module = None
        return module
    return _lazy_import


class Dictionary:
    """Словарь, список правил, каждое из которых проверяется на возможность применения к обрабатываемой ноде"""
    def __init__(self, rules: list[Rule], path: Path=None):
        self.rules = rules
        self.path = path

    @classmethod
    def load(cls, path: Path, depends: 'Depends') -> Self:
        module = side_module(path)
        load = depends.load
        rules_data = (load.prepare(row) for row in load.loader(path))
        rule_maker = depends.rule_maker
        rules = [rule_maker(pattern_data, target_data, depends, module)
                 for pattern_data, target_data in rules_data]
        return cls(rules, path)

    def rules_for(self, node: ITextNode) -> Generator[Rule, None, None]:
        return (rule for rule in self.rules if rule.pattern.match(node.text))

    def apply(self, node: ITextNode):
        for rule in self.rules_for(node):
            rule.apply(node)


class DictionaryIndex(Dictionary):
    """Словарь, список правил, часть которых проверяется на возможность применения к обрабатываемой ноде. Эта часть
    определяется на основании быстрого поиска по индексу содержимого ноды. Например для ноды(text='слово') будут
    отобраны только правила 'слово=замена' и 'слов*=заме' """
    def __init__(self, rules: list[Rule], path: Path=None):
        super().__init__(rules, path)
        self._index = self.make_index(rules)

    @staticmethod
    def make_index(rules: list[Rule]):
        index = Indexer()
        for i, rule in enumerate(rules):
            index.add(rule.pattern, i)
        index.freeze()
        return index

    def rules_for(self, node: ITextNode) -> Generator[Rule, None, None]:
        return (rule for i in self._index[node.text]
                if (rule := self.rules[i]).pattern.match(node.text))


# ========== Process Depends ==========================================================
TDictMaker = Callable[[Path, Self], Dictionary]
TRuleMaker = Callable[[TPatternData, TTargetData, 'Depends', TModuleLoader], Rule]
TTargetMaker = Callable[[TTargetData, Optional[ModuleType]], ITargetResolved]


class ProcessLevel(Enum):
    line = 1
    sent = 2
    word = 3
    part = 4


@dataclass
class Depends:
    level: ProcessLevel
    load: LoadDepends
    dict_maker: TDictMaker
    rule_maker: TRuleMaker
    pattern_maker: Callable
    target_maker: Optional[TTargetMaker] = None



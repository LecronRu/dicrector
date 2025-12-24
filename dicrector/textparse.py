import weakref
from dataclasses import dataclass
from functools import cached_property
from typing import Iterable

from razdel import sentenize, tokenize
from razdel.segmenters.tokenize import RULES, RU
from razdel.rule import FunctionRule, JOIN



# Схлопывание дочек и создание условий для нового разбиения, происходит только при обращении к свойству text
# родителя. Может возникнуть ошибка дальнейшей обработки, если новое разбиение даст больше токенов. При объединении,
# "то есть = то`есть" на уровне sent или "из-за = и`зза" на уровне word, произойдет обращение к соответственно
# сеттерам sent.text и word.text, исключая опасность для нижележащих уровней.
# Также, для уровня обработки sent. Создание из двух предложений одного, при удалении финальной пунктуации,
# или из одного два, при добавлении. Последствия маловероятны. Для уровня обработки word. Возможное исправление
# авторских ошибок "понаучному = по научному" или "по-научному" маловероятно.


def with_space(tokens: Iterable) -> Iterable[str]:
    last_stop = None
    for token in tokens:
        # noinspection PyProtectedMember
        text_obj = token._text_obj
        if last_stop and text_obj.start > last_stop:
            yield ' ' * (text_obj.start - last_stop)
        yield token.text
        last_stop = text_obj.stop


@dataclass
class TextObj:  # заглушка, для идентичности обработки. Doc для Sentence и DocToken для Token тоже имеют свойство text
    text: str


class Node:
    child_class = None  # Определяется в потомках
    _parser = None  # Определяется в потомках
    def __init__(self, text_obj: TextObj, parent: 'Node' = None):
        self._text_obj = text_obj
        self.parent = weakref.proxy(parent) if parent else None
        self._childs = None
        self._child_changed = False

    def __repr__(self):
        return f'{self.__class__.__name__}, {self._text_obj}'

    @property
    def text(self) -> str:
        if self._child_changed: 
            new_text = self._joiner()  # флаг changed автоматически означает, что дочки есть
            self._text_obj.text = new_text  # уведомлять никого не надо, это было сделано на этапе изменения дочек
            self._child_changed = False  # удалять дочек не надо. Просто актуализируем содержимое ноды
                                         # !!Потенциальная проблема, если меняется количество слов, например в rexw и dicx
        return self._text_obj.text

    @text.setter
    def text(self, value: str):
        # перед проверкой надо убедиться в актуальности содержимого ноды.
        # Для этого вызываем не поле _text, а свойство text, в котором и проводится актуализация
        if self.text != value:
            self._text_obj.text = value
            self._childs = None
            if self.parent:
                self.parent.child_changed()

    @property
    def childs(self) -> list['Node']:
        if not self._childs:
            self._childs = [self.child_class(t, parent=self)
                            for t in self._parser(self.text)]
        return self._childs

    def child_changed(self):
        if not self._child_changed:
            self._child_changed = True
            if self.parent:
                self.parent.child_changed()

    def _joiner(self) -> str:
        return ''.join(with_space(self._childs))


class Part(Node):
    pass


class Token(Node):
    child_class = Part

    @staticmethod
    def _parser(text: str) -> Iterable[TextObj]:
        # проверка на наличие токена нужна для обхода исходного текста типа дельта- или -1
        parts = [TextObj(_) for _ in text.split('-') if _]
        if len(parts) < 2:
            parts = []
        return parts

    def _joiner(self) -> str:
        return '-'.join(_.text for _ in self._childs)

    @cached_property
    def is_first_word(self) -> bool:
        return self == self.parent.first_word


class Sentence(Node):
    child_class = Token
    _parser = tokenize

    @cached_property
    def first_word(self) -> Token|None:
        return next((token for token in self._childs if token.text[0].isalnum()), None)


class Line(Node):
    child_class = Sentence
    _parser = sentenize

    @classmethod
    def from_str(cls, text: str):
        text_obj = TextObj(text)
        return cls(text_obj)


def accent(split):
    """Правило для модуля razdel. Отменяет разбиение по символу ударения для кириллицы"""
    # Правило обрабатывается, только если в split есть знак препинания (?)
    # left/right — текстовое значение токена; left_1/right_1 — объект, с позицией и типом
    # цифра после подчеркивания, означает смещение на Х токенов, соответственно влево и вправо
    # у объекта есть свойство type и normal (предположительно lower())

    if (split.left_1.type == RU and split.right == '`') or\
       (split.left  == '`' and split.right_1.type == RU):
        return JOIN


tokenize_rules = RULES
tokenize_rules.append(FunctionRule(accent))

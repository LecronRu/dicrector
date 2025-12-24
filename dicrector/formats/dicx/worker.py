import string
from itertools import chain, zip_longest

from razdel import tokenize

# noinspection PyUnresolvedReferences
import dicrector.textparse  # для регистрации символа ударения
from dicrector.components import PatternRe, PatternWildcard, DictionaryIndex, ITextNode
from dicrector.indexer import Wildcard

WORD_DELIMITER = r'\b'
PUNCTUATION = set(string.punctuation)


class PatternDicx(PatternRe):
    def __init__(self, pattern: str, case_sensitive: bool):
        self.case_sensitive = case_sensitive
        self.key_pattern = self.find_key(pattern)
        pattern = self.prepare_pattern(pattern)
        super().__init__(pattern, case_sensitive)

    @staticmethod
    def find_key(pattern: str) -> PatternWildcard:
        pattern_ = pattern.replace('*', '`')  # заменяем * на `, который в razdel убран из разделителей слов
        tokens = (t for t in tokenize(pattern_) if t.text not in PUNCTUATION)
        patterns = [PatternWildcard.from_str(pattern[t.start:t.stop]) for t in tokens]
        if not patterns:
            raise KeyError(f'Для правила <{pattern}> невозможно получить ключ')
        key = min(patterns, key=lambda p: (p.wildcard.value, -1 * len(p.key)))
        return key

    @staticmethod
    def prepare_pattern(pattern: str) -> str:
        pt = PatternWildcard.from_str(pattern)
        if pt.wildcard != Wildcard.none:
            wc_value = pt.wildcard.value
            seq = []  # если по краям нет *, пишем \b
            if not wc_value[0]: seq.append(WORD_DELIMITER)
            seq.append(pt.key)
            if not wc_value[1]: seq.append(WORD_DELIMITER)
            pattern = ''.join(seq)
        pattern = pattern.replace('*', r'(\S*)')
        # библиотечная функция re.escape(pattern) экранирует лишнее. Ручками
        pattern = pattern.replace('.', r'\.').replace('?', r'\?')
        return pattern

    @property
    def key(self):
        return self.key_pattern.key

    @property
    def wildcard(self):
        return self.key_pattern.wildcard


class DictionaryDicx(DictionaryIndex):
    # Правила выбираются один раз. Цикл while может привести к зацикливанию, если ударение попадает на
    # последний символ. Недостаток одного прохода небольшой. Если применение предыдущего правило создаст ключ
    # поиска для одного из следующих, что почти невероятно.
    def rules_for(self, node: ITextNode):
        # noinspection PyUnresolvedReferences
        words_rules_idx = (self._index[word_node.text] for word_node in node.childs)
        rules_idx = sorted(set(chain.from_iterable(words_rules_idx)))
        rules = (self.rules[i] for i in rules_idx)
        return (rule for rule in rules if rule.pattern.match(node.text))


# noinspection PyUnusedLocal
def parse_target(target: tuple, side_module) -> str:
    target = target[0]
    # заменяем маску на номер группы регулярного выражения
    parts = target.split('*')
    groups = (f'\\g<{_}>' for _ in range(1, len(parts)))
    tokens = chain.from_iterable(zip_longest(parts, groups, fillvalue=''))
    return ''.join(tokens)

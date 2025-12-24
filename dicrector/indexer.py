from collections import defaultdict
from enum import Enum
from functools import lru_cache
from typing import List, Protocol, Iterable


INDEX_KEY_LENGTH = 8  # Индекс по первым N символам токена. Оптимально 7-9


class Wildcard(Enum):
    none  = (0, 0)
    right = (0, 1)
    left  = (1, 0)
    both  = (1, 1)


class IIndexed(Protocol):
    case_sensitive: bool
    wildcard: Wildcard
    key: str


class Indexer:
    def __init__(self, key_length: int=INDEX_KEY_LENGTH):
        self._index = {w: defaultdict(list) for w in Wildcard}
        self._key_length = key_length
        self._index_minsize = None

    def freeze(self):
        """Замораживаем индекс для работы. Процедура однократная. При повторном использовании будет выброшено
        исключение."""
        if self._index_minsize is None:
            self._index_minsize = {wc: min(map(len, index)) for wc, index in self._index.items() if index}
        else:
            raise  # TODO кастомизировать исключение

    def add(self, pattern: IIndexed, order_no: int):
        # ограничиваем длину ключа
        if pattern.wildcard == Wildcard.left:
            key = pattern.key[-self._key_length:]
        else:
            key = pattern.key[:self._key_length]
        # Выгоднее проверять применимость правила, чем многократно искать по индексу в разных регистрах
        # поэтому индексируем в нижнем регистре.
        if pattern.case_sensitive:  # Для not case_sensitive шаблона, регистр уже преобразован
            key = key.lower()
        sub_index = self._index[pattern.wildcard]
        sub_index[key].append(order_no)

    @lru_cache
    def _slice_permutation(self, string_length: int) -> list[tuple[slice, Iterable[Wildcard]]]:
        permutation = []
        max_window_size = min(self._key_length, string_length)
        for window_size in range(1, max_window_size + 1):
            max_start = string_length - window_size
            for start in range(0, max_start + 1):
                stop = start + window_size
                is_begin = start == 0
                is_end = stop == string_length
                is_full = is_begin and stop - start == max_window_size
                mask = []
                if is_full:  mask.append(Wildcard.none)
                if is_begin: mask.append(Wildcard.right)
                if is_end:   mask.append(Wildcard.left)
                mask.append(Wildcard.both)

                # отбрасываем короткие и бесполезные срезы
                active_mask = tuple(wc for wc in mask
                               if wc in self._index_minsize
                               and window_size >= self._index_minsize[wc])
                if active_mask:
                    permutation.append((slice(start, stop), active_mask))
        return permutation

    def __getitem__(self, string: str) -> List[int]:
        order_no = set()
        string = string.lower()
        length = len(string)
        for slice_, mask in self._slice_permutation(length):
            key = string[slice_]
            for wildcard in mask:
                index = self._index[wildcard]
                if values := index.get(key):
                    order_no.update(values)
        return sorted(order_no)

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Generator, Callable, Any


# noinspection PyUnusedLocal
def empty_row(path: Path) -> tuple:
    """Возвращает одну строку с пустыми данными. Используется для вызова внешних обработчиков"""
    # noinspection PyRedundantParentheses
    return ('',)


def file_row_reader(path: Path) -> Generator:
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            rule, _, comment = line.rstrip('\n').partition('#')
            if not rule:  # Правило не содержит данных
                continue
            if comment:  # Осторожно! Правила оканчивающиеся комментарием, не могут содержать финишных пробелов
                rule = rule.rstrip()
            yield rule


def sqlite_row_reader(path: Path) -> Generator:
    with path.open(encoding='utf-8') as f:
        config = json.loads(f.read())
    db_path = config['db_path']
    options = config.get("connect_options", {})
    query = config["query"]
    with sqlite3.connect(db_path, **options) as con:
        for row in con.execute(query):
            yield row

# Может возникнуть желание назначить саму базу словарем, но... Тогда придется хардкодить текст запроса и усложняем
# использование в случаях, когда база хранит данные больше чем для одного словаря. Поэтому словарь только в качестве
# конфига (указателя), а база всегда отдельно.

class Loader(Enum):
    single = empty_row  # пустышка, используется для создания виртуальных внешних обработчиков
    lines = file_row_reader
    sqlite = sqlite_row_reader


TPatternData = tuple
TTargetData = tuple


@dataclass
class LoadDepends:
    loader: Loader | Callable[[Path], Generator]
    prepare: Callable[[Any], tuple[TPatternData, TTargetData]]


def split_rule_line(line):
    pattern, _, target = line.partition('=')
    return (pattern,), (target,)


# Шаблон для обычных текстовых файлов
# noinspection PyTypeChecker
textfile_dictionary = LoadDepends(
    Loader.lines,
    split_rule_line,
)

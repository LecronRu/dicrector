import sqlite3
from collections import Counter

from utils.service import is_need_check



class WordStat:
    def __init__(self):
        self.stat = Counter()

    def __call__(self, node) -> str|None:
        self.stat[node.text] += 1
        return None

    def __del__(self):
        lower = Counter()
        # lower итогового быстрее lower каждого слова
        for word, count in self.stat.items():
            lower[word.lower()] += count
        stored = ((w, c) for w, c in lower.items() if is_need_check(w))

        db_path = "db_path"
        upd_stat = 'INSERT INTO word(text, amount, last_modify) VALUES (?, ?, date()) \
                    ON CONFLICT(text) DO \
                    UPDATE SET amount=amount + excluded.amount, last_modify = excluded.last_modify'
        with sqlite3.connect(db_path) as con:
            con.executemany(upd_stat, stored)
            con.commit()


corrector = WordStat()
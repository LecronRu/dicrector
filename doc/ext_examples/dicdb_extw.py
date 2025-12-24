import sqlite3
from functools import cache


db_path = 'db_path'
sel_word = 'SELECT target FROM word WHERE text = ?'


class DbResolver:
    def __init__(self):
        self.db = sqlite3.connect(db_path)

    def __call__(self, node) -> str|None:
        text = node.text.lower()
        return self.correct(text)

    @cache
    def correct(self, text: str) -> str|None:
        request = self.db.execute(sel_word, (text,)).fetchone()
        return request and request[0]

    def __del__(self):
        self.db.commit()
        self.db.close()


corrector = DbResolver()
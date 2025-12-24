from dicrector.components import Depends, ProcessLevel, Rule
from dicrector.loaders import textfile_dictionary
from .worker import DictionaryDicx, PatternDicx, parse_target


depends = Depends(
    ProcessLevel.sent,
    textfile_dictionary,
    dict_maker=DictionaryDicx.load,
    rule_maker=Rule.from_,
    pattern_maker=PatternDicx.from_str,
    target_maker=parse_target
)
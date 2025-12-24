from components import Depends, ProcessLevel, Dictionary, Rule, PatternRe
from loaders import textfile_dictionary
from formats.rex import parse_target

depends = Depends(
    ProcessLevel.word,
    textfile_dictionary,
    dict_maker=Dictionary.load,
    rule_maker=Rule.from_,
    pattern_maker=PatternRe.from_str,
    target_maker=parse_target
)

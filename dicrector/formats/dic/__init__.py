from dicrector.components import PatternWildcard, Rule, DictionaryIndex, ProcessLevel, Depends
from dicrector.loaders import textfile_dictionary


depends = Depends(
    ProcessLevel.part,
    textfile_dictionary,
    dict_maker=DictionaryIndex.load,
    rule_maker=Rule.from_,
    pattern_maker=PatternWildcard.from_str,
    target_maker=None
)


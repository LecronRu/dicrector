from components import Depends, ProcessLevel, Dictionary, Rule, PatternRe
from loaders import textfile_dictionary


def parse_target(target: tuple, side_module):
    target = target[0]
    if target and target[0] == '@':
        func = target[1:]
        module = side_module()
        target = getattr(module, func)
    else:
        target = target.replace('$', '\\')  # шаблоны re.group в формате $0, $1, ...
    return target


depends = Depends(
    ProcessLevel.line,
    textfile_dictionary,
    dict_maker = Dictionary.load,
    rule_maker=Rule.from_,
    pattern_maker=PatternRe.from_str,
    target_maker=parse_target
)


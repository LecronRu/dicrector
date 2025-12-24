from dicrector.components import Depends, ProcessLevel, Dictionary, RuleResolved, PatternFake
from dicrector.loaders import Loader, LoadDepends


# noinspection PyUnusedLocal
def prepare_fake_rule(data):
    return (), ()


# noinspection PyUnusedLocal
def target_maker(target: tuple, side_module):
    module = side_module()
    target = getattr(module, 'corrector')
    return target


depends = Depends(
    ProcessLevel.word,
    LoadDepends(
        Loader.single,
        prepare_fake_rule,
    ),
    dict_maker=Dictionary.load,
    rule_maker=RuleResolved.from_,
    pattern_maker=PatternFake,
    target_maker=target_maker
)

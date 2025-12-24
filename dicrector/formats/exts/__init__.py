from components import Depends, ProcessLevel, Dictionary, RuleResolved, PatternFake
from loaders import Loader, LoadDepends
from formats.extw import prepare_fake_rule, target_maker


depends = Depends(
    ProcessLevel.sent,
    LoadDepends(
        Loader.single,
        prepare_fake_rule,
    ),
    dict_maker=Dictionary.load,
    rule_maker=RuleResolved.from_,
    pattern_maker=PatternFake,
    target_maker=target_maker
)

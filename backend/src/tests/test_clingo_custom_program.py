import pytest

from ia.clingo.asp_engine import validate_custom_program


def test_custom_clingo_rejects_script_and_include():
    with pytest.raises(ValueError):
        validate_custom_program('#script (python)\nprint("no")\n#end.')
    with pytest.raises(ValueError):
        validate_custom_program('#include "secret.lp".')


def test_custom_clingo_accepts_normal_constraints():
    program = 'demo_fact.\n:- demo_fact, not demo_fact.'
    assert validate_custom_program(program) == program

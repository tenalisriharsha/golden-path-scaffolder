import pytest

from goldpath.engine import TemplateError, render


def test_variable_substitution():
    assert render("hello {{ name }}!", {"name": "world"}) == "hello world!"


def test_multiple_variables_and_values_are_stringified():
    assert render("{{ svc }} on port {{ port }}", {"svc": "api", "port": 8080}) == "api on port 8080"


def test_whitespace_inside_tags_is_allowed():
    assert render("{{name}}/{{ name }}", {"name": "x"}) == "x/x"


def test_undefined_variable_raises():
    with pytest.raises(TemplateError, match="undefined variable"):
        render("{{ missing }}", {})


def test_if_block_rendered_when_truthy():
    assert render("a{% if flag %}b{% endif %}c", {"flag": True}) == "abc"


def test_if_block_skipped_when_falsy():
    assert render("a{% if flag %}b{% endif %}c", {"flag": False}) == "ac"


def test_if_with_undefined_variable_raises():
    with pytest.raises(TemplateError, match="undefined variable in conditional"):
        render("{% if nope %}x{% endif %}", {})


def test_nested_if_blocks():
    template = "{% if a %}1{% if b %}2{% endif %}3{% endif %}"
    assert render(template, {"a": True, "b": True}) == "123"
    assert render(template, {"a": True, "b": False}) == "13"
    assert render(template, {"a": False, "b": True}) == ""


def test_unclosed_if_raises():
    with pytest.raises(TemplateError, match="unclosed"):
        render("{% if a %}oops", {"a": True})


def test_unexpected_endif_raises():
    with pytest.raises(TemplateError, match="unexpected"):
        render("nope{% endif %}", {})


def test_variables_inside_if_are_substituted():
    template = "{% if show %}{{ name }}{% endif %}"
    assert render(template, {"show": True, "name": "svc"}) == "svc"

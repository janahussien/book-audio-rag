from backend.llm.prompts import list_prompts, get_prompt


def test_prompt_library_not_empty():
    assert len(list_prompts()) > 0


def test_prompt_library_has_supervisor_requested_range():
    assert 10 <= len(list_prompts()) <= 20


def test_prompt_ids_are_unique():
    ids = [p.id for p in list_prompts()]
    assert len(ids) == len(set(ids))


def test_get_prompt_returns_none_for_unknown_id():
    assert get_prompt("does-not-exist") is None


def test_prompt_templates_use_expected_placeholders():
    for p in list_prompts():
        assert "{context}" in p.template

import pytest
from batch_import import parse_batch


def test_batch_separators_deduplication_and_phrases():
    assert parse_batch(" Emit,emit\nturn down；apple;banana") == ["emit", "turn down", "apple", "banana"]


@pytest.mark.parametrize("text", [" , ;\n", ",".join(str(i) for i in range(21))])
def test_batch_rejects_empty_or_excessive_input(text):
    with pytest.raises(ValueError):
        parse_batch(text)

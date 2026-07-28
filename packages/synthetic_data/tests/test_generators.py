from random import Random

import pytest

from synthetic_data.generators import free_text


@pytest.mark.unit
def test_free_text_with_zero_length_sentence_span_terminates_instead_of_looping() -> None:
    # words_per_sentence=(0, 0) forces a zero-length chunk on the first
    # iteration; without the empty-chunk guard this would loop forever
    # since `index` never advances.
    generate = free_text(["word"], min_words=3, max_words=3, words_per_sentence=(0, 0))

    result = generate(Random(1))

    assert result == ""

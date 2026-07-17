"""Student tokenizer tests — trains a small SentencePiece model in a tmp dir."""

import random

import pytest

pytest.importorskip("sentencepiece")

from setu.training.tokenizer import BOS, EOS, StudentTokenizer


@pytest.fixture(scope="module")
def tokenizer(tmp_path_factory):
    d = tmp_path_factory.mktemp("tok")
    random.seed(0)
    en = "the weather is nice today i like reading books and playing music in a park".split()
    hi = "आज मौसम अच्छा है मुझे किताबें पढ़ना संगीत सुनना पसंद बहुत सुंदर".split()
    lines = []
    for _ in range(500):
        lines.append(" ".join(random.sample(en, 5)))
        lines.append(" ".join(random.sample(hi, 5)))
    txt = d / "corpus.txt"
    txt.write_text("\n".join(lines), encoding="utf-8")
    return StudentTokenizer.train(txt, d / "model", vocab_size=200)


def test_flores_tags_reserved(tokenizer):
    # all 22+English (+dual-script) tags are user-defined symbols with stable ids
    assert tokenizer._sp.piece_to_id("hin_Deva") > 3  # after the 4 specials
    assert tokenizer._sp.piece_to_id("eng_Latn") > 3
    assert tokenizer._sp.piece_to_id("kas_Deva") > 3


def test_encode_source_prepends_direction_tags(tokenizer):
    ids = tokenizer.encode_source("आज मौसम अच्छा है", "hin_Deva", "eng_Latn")
    assert ids[0] == tokenizer._sp.piece_to_id("hin_Deva")
    assert ids[1] == tokenizer._sp.piece_to_id("eng_Latn")
    assert ids[-1] == EOS


def test_encode_target_ends_with_eos_no_leading_bos(tokenizer):
    # labels are [tokens, EOS]; the model prepends decoder_start itself, so
    # encode_target must NOT add a leading BOS (that caused empty translations)
    ids = tokenizer.encode_target("the weather is nice today")
    assert ids[-1] == EOS
    assert ids[0] != BOS


def test_decode_strips_specials(tokenizer):
    text = tokenizer.decode(tokenizer.encode_target("the weather is nice"))
    assert "<s>" not in text and "</s>" not in text
    assert "weather" in text

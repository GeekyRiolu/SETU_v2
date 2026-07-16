"""M6 CLI tests — file and stdin input, JSON output."""

import io
import json

from setu.cli import main


def test_text_arg(capsys):
    assert main(["--src", "hi", "--tgt", "en", "--text", "नमस्ते"]) == 0
    assert "नमस्ते" in capsys.readouterr().out


def test_file_input(tmp_path, capsys):
    f = tmp_path / "sents.txt"
    f.write_text("नमस्ते\nमैं ठीक हूँ\n", encoding="utf-8")
    assert main(["--src", "hi", "--tgt", "en", "--file", str(f)]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l]
    assert lines == ["नमस्ते", "मैं ठीक हूँ"]  # stub passthrough, two lines in -> two out


def test_stdin_input(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("पहला\nदूसरा\n"))
    assert main(["--src", "hi", "--tgt", "en"]) == 0
    assert [l for l in capsys.readouterr().out.splitlines() if l] == ["पहला", "दूसरा"]


def test_json_output_single(capsys):
    assert main(["--src", "hi", "--tgt", "en", "--text", "नमस्ते", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["src_lang"] == "hi" and payload["tgt_lang"] == "en"


def test_json_output_batch(tmp_path, capsys):
    f = tmp_path / "s.txt"
    f.write_text("a\nb\n", encoding="utf-8")  # english passthrough for shape only
    assert main(["--src", "en", "--tgt", "hi", "--file", str(f), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list) and len(payload) == 2


def test_bad_pair_exits_2(capsys):
    assert main(["--src", "hi", "--tgt", "hi", "--text", "x"]) == 2

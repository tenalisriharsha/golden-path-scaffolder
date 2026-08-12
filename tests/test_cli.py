from goldpath.cli import main


def test_list_shows_all_flavors(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "fastapi" in out
    assert "go" in out


def test_new_scaffolds_service(tmp_path, capsys):
    assert main(["new", "orders-api", "--flavor", "fastapi", "--output", str(tmp_path)]) == 0
    assert (tmp_path / "orders-api" / "app" / "main.py").is_file()
    assert "orders-api" in capsys.readouterr().out


def test_new_with_unknown_flavor_fails_cleanly(tmp_path, capsys):
    assert main(["new", "x", "--flavor", "rust", "--output", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "unknown flavor" in err
    assert "fastapi, go" in err


def test_new_with_invalid_name_fails_cleanly(tmp_path, capsys):
    assert main(["new", "Bad Name", "--flavor", "go", "--output", str(tmp_path)]) == 1
    assert "invalid service name" in capsys.readouterr().err


def test_new_into_existing_dir_fails_cleanly(tmp_path, capsys):
    (tmp_path / "web").mkdir()
    assert main(["new", "web", "--flavor", "go", "--output", str(tmp_path)]) == 1
    assert "already exists" in capsys.readouterr().err


def test_new_defaults_to_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "svc", "--flavor", "go"]) == 0
    assert (tmp_path / "svc" / "go.mod").is_file()

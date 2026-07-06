import os
import tempfile
import pytest
from pathlib import Path
from tools.files import read_file, write_file, list_directory, search_files, replace_in_file, diff_files


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_write_and_read_file(temp_workspace):
    file_path = temp_workspace / "test.txt"
    
    # Test writing
    res = write_file(str(file_path), "hello\nworld\n")
    assert res["success"] is True
    assert file_path.exists()
    
    # Test reading
    res = read_file(str(file_path))
    assert res["success"] is True
    assert res["output"] == "hello\nworld\n"
    assert "metadata" in res
    assert "size" in res["metadata"]
    
    # Test reading with lines
    res = read_file(str(file_path), start_line=2)
    assert res["success"] is True
    assert res["output"] == "world\n"
    

def test_write_file_no_overwrite(temp_workspace):
    file_path = temp_workspace / "test.txt"
    write_file(str(file_path), "first")
    
    res = write_file(str(file_path), "second", overwrite=False)
    assert res["success"] is False
    assert "File exists" in res["output"]
    
    assert read_file(str(file_path))["output"] == "first"


def test_list_directory(temp_workspace):
    (temp_workspace / "dir1").mkdir()
    (temp_workspace / "dir1" / "file1.txt").write_text("a")
    (temp_workspace / "file2.txt").write_text("b")
    (temp_workspace / ".hidden").write_text("c")
    
    res = list_directory(str(temp_workspace))
    assert res["success"] is True
    names = [f["name"] for f in res["files"]]
    assert "dir1" in names
    assert "file2.txt" in names
    assert ".hidden" not in names
    
    # Test recursive
    res = list_directory(str(temp_workspace), recursive=True)
    names = [f["name"] for f in res["files"]]
    assert "file1.txt" in names
    
    # Test hidden
    res = list_directory(str(temp_workspace), include_hidden=True)
    names = [f["name"] for f in res["files"]]
    assert ".hidden" in names


def test_search_files(temp_workspace):
    (temp_workspace / "file1.txt").write_text("hello there\ngeneral kenobi")
    (temp_workspace / "file2.txt").write_text("hello world")
    
    res = search_files(str(temp_workspace), "hello")
    assert res["success"] is True
    assert len(res["results"]) == 2
    
    res = search_files(str(temp_workspace), "kenobi")
    assert res["success"] is True
    assert len(res["results"]) == 1
    assert res["results"][0]["matches"][0]["line_number"] == 2
    
    # Test regex
    res = search_files(str(temp_workspace), r"gen.*l", is_regex=True)
    assert res["success"] is True
    assert len(res["results"]) == 1


def test_replace_in_file(temp_workspace):
    file_path = temp_workspace / "test.txt"
    file_path.write_text("foo bar foo")
    
    # Literal
    res = replace_in_file(str(file_path), "foo", "baz")
    assert res["success"] is True
    assert res["replacements"] == 2
    assert file_path.read_text() == "baz bar baz"
    
    # Regex
    file_path.write_text("apple 123 banana 456")
    res = replace_in_file(str(file_path), r"\d+", "NUM", is_regex=True)
    assert res["success"] is True
    assert res["replacements"] == 2
    assert file_path.read_text() == "apple NUM banana NUM"
    
    # Preview
    res = replace_in_file(str(file_path), "NUM", "X", preview=True)
    assert res["success"] is True
    assert res["replacements"] == 2
    assert file_path.read_text() == "apple NUM banana NUM"  # Unchanged


def test_diff_files(temp_workspace):
    file1 = temp_workspace / "1.txt"
    file2 = temp_workspace / "2.txt"
    
    file1.write_text("a\nb\nc\n")
    file2.write_text("a\nx\nc\n")
    
    res = diff_files(str(file1), str(file2))
    assert res["success"] is True
    assert res["added_lines"] == 1
    assert res["removed_lines"] == 1
    assert "+x" in res["diff"]
    assert "-b" in res["diff"]

    # Identical files
    res = diff_files(str(file1), str(file1))
    assert res["success"] is True
    assert res["exit_code"] == 0
    assert res["added_lines"] == 0
    assert res["removed_lines"] == 0

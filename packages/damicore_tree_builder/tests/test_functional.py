from pathlib import Path

import pytest

from damicore_tree_builder.functional import (
    TreeNode,
    build_neighbor_joining_tree,
    get_nonterminals,
    get_terminals,
    load_distance_matrix,
    run,
    to_newick,
    write_newick,
)


@pytest.mark.unit
def test_load_distance_matrix_returns_names_and_matrix_for_valid_csv(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(
        ",A,B,C\nA,0,5,9\nB,5,0,10\nC,9,10,0\n",
        encoding="utf-8",
    )

    names, matrix = load_distance_matrix(str(matrix_path))

    assert names == ["A", "B", "C"]
    assert matrix == [
        [0.0, 5.0, 9.0],
        [5.0, 0.0, 10.0],
        [9.0, 10.0, 0.0],
    ]


@pytest.mark.unit
def test_load_distance_matrix_raises_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        load_distance_matrix("/nonexistent/path/matrix.csv")


@pytest.mark.unit
def test_load_distance_matrix_raises_for_empty_csv(tmp_path: Path) -> None:
    matrix_path = tmp_path / "empty.csv"
    matrix_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_nonnumeric_values(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,B\nA,0,x\nB,x,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-numeric"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_asymmetric_matrix(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,B\nA,0,5\nB,9,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="symmetric"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_nonzero_diagonal(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,B\nA,1,5\nB,5,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="diagonal"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_duplicate_labels(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,A\nA,0,5\nA,5,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicated"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_row_with_wrong_column_count(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,B\nA,0,5,9\nB,5,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="same number of columns"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_load_distance_matrix_raises_for_negative_values(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(",A,B\nA,0,-1\nB,-1,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="negative"):
        load_distance_matrix(str(matrix_path))


@pytest.mark.unit
def test_build_nj_tree_returns_correct_topology_for_four_leaves() -> None:
    tree = build_neighbor_joining_tree(
        ["A", "B", "C", "D"],
        [
            [0.0, 5.0, 9.0, 9.0],
            [5.0, 0.0, 10.0, 10.0],
            [9.0, 10.0, 0.0, 8.0],
            [9.0, 10.0, 8.0, 0.0],
        ],
    )

    terminal_names = sorted(
        node["name"] for node in get_terminals(tree) if node["name"] is not None
    )
    assert terminal_names == ["A", "B", "C", "D"]
    assert len(get_nonterminals(tree)) == 3


@pytest.mark.unit
def test_build_nj_tree_raises_for_fewer_than_three_elements() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        build_neighbor_joining_tree(["A", "B"], [[0.0, 5.0], [5.0, 0.0]])


@pytest.mark.unit
def test_build_nj_tree_raises_for_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        build_neighbor_joining_tree(
            ["A", "A", "B"],
            [[0.0, 0.0, 5.0], [0.0, 0.0, 5.0], [5.0, 5.0, 0.0]],
        )


@pytest.mark.unit
def test_to_newick_serializes_tree_to_string() -> None:
    tree: TreeNode = {
        "name": None,
        "branch_length": 0.0,
        "children": [
            {"name": "A", "branch_length": 1.0, "children": []},
            {"name": "B value", "branch_length": 2.5, "children": []},
        ],
    }

    assert to_newick(tree) == "(A:1,'B value':2.5):0;\n"


@pytest.mark.unit
def test_write_newick_writes_file_and_returns_path(tmp_path: Path) -> None:
    tree: TreeNode = {
        "name": None,
        "branch_length": 0.0,
        "children": [
            {"name": "A", "branch_length": 1.0, "children": []},
            {"name": "B value", "branch_length": 2.5, "children": []},
        ],
    }
    output_path = tmp_path / "tree.newick"

    generated_path = write_newick(tree, str(output_path))

    assert generated_path == output_path
    assert output_path.read_text(encoding="utf-8") == "(A:1,'B value':2.5):0;\n"


@pytest.mark.unit
def test_write_newick_creates_parent_directories(tmp_path: Path) -> None:
    tree: TreeNode = {
        "name": None,
        "branch_length": 0.0,
        "children": [
            {"name": "A", "branch_length": 1.0, "children": []},
            {"name": "B", "branch_length": 2.0, "children": []},
        ],
    }
    nested_path = tmp_path / "a" / "b" / "tree.newick"

    result = write_newick(tree, str(nested_path))

    assert result == nested_path
    assert nested_path.exists()


@pytest.mark.unit
def test_get_terminals_returns_only_leaf_nodes() -> None:
    tree: TreeNode = {
        "name": None,
        "branch_length": 0.0,
        "children": [
            {"name": "A", "branch_length": 1.0, "children": []},
            {"name": "B", "branch_length": 2.0, "children": []},
        ],
    }

    terminals = get_terminals(tree)

    assert [node["name"] for node in terminals] == ["A", "B"]


@pytest.mark.unit
def test_get_nonterminals_returns_only_internal_nodes() -> None:
    tree: TreeNode = {
        "name": None,
        "branch_length": 0.0,
        "children": [
            {"name": "A", "branch_length": 1.0, "children": []},
            {"name": "B", "branch_length": 2.0, "children": []},
        ],
    }

    internals = get_nonterminals(tree)

    assert len(internals) == 1
    assert internals[0]["name"] is None


@pytest.mark.unit
def test_run_returns_success_report_and_writes_newick_file(tmp_path: Path) -> None:
    input_path = tmp_path / "matrix.csv"
    output_path = tmp_path / "tree.newick"
    input_path.write_text(
        ",A,B,C\nA,0,5,9\nB,5,0,10\nC,9,10,0\n",
        encoding="utf-8",
    )

    report = run(str(input_path), str(output_path))

    assert report == {
        "status": "success",
        "distance_matrix_path": str(input_path),
        "tree_format": "newick",
        "total_leaf_nodes": 3,
        "total_internal_nodes": 2,
        "output_file_path": str(output_path),
    }
    assert output_path.read_text(encoding="utf-8").endswith(";\n")


@pytest.mark.unit
def test_run_raises_file_not_found_for_missing_input() -> None:
    with pytest.raises(FileNotFoundError):
        run("/nonexistent/path/matrix.csv", "/tmp/out.newick")

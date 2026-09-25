"""star_schema.py and schema/*.sql describe the same schema from two sides.

These tests parse the DDL (no database needed, so they run in CI) and fail
if a table, column, FK, or natural key exists on one side only.
"""

import re
from pathlib import Path

import pytest

from src.schema.star_schema import DIM_TABLES, FACT_TABLES

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
CONSTRAINT_WORDS = {"CHECK", "UNIQUE", "PRIMARY", "CONSTRAINT", "FOREIGN"}


def _split_top_level(body: str) -> list[str]:
    """Split a CREATE TABLE body on commas that are not inside parentheses."""
    parts, depth, current = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _extract_body(sql: str, start: int) -> str:
    """Return the text between the '(' at `start` and its matching ')'."""
    depth = 0
    for i in range(start, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                return sql[start + 1 : i]
    raise ValueError("unbalanced parentheses in DDL")


def _parse_ddl() -> dict[str, dict]:
    sql = "\n".join(p.read_text() for p in sorted(SCHEMA_DIR.glob("*.sql")))
    sql = re.sub(r"--[^\n]*", "", sql)  # strip comments
    tables = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+)\s*\(", sql):
        body = _extract_body(sql, m.end() - 1)
        columns, fks, uniques = [], [], []
        for item in _split_top_level(body):
            first = item.split()[0]
            if first.upper() in CONSTRAINT_WORDS:
                u = re.match(r"(?:UNIQUE|PRIMARY KEY)\s*\(([^)]*)\)", item)
                if u:
                    uniques.append([c.strip() for c in u.group(1).split(",")])
                continue
            columns.append(first)
            if "REFERENCES" in item:
                fks.append(first)
            if re.search(r"\bUNIQUE\b", item):
                uniques.append([first])
        tables[m.group(1)] = {"columns": columns, "fks": fks, "uniques": uniques}
    return tables


DDL = _parse_ddl()
ALL_TABLES = DIM_TABLES + FACT_TABLES


def test_counts_match_project_target():
    assert len(DIM_TABLES) == 8
    assert len(FACT_TABLES) == 4


def test_same_table_names_on_both_sides():
    assert {t.name for t in ALL_TABLES} == set(DDL)


@pytest.mark.parametrize("table", ALL_TABLES, ids=lambda t: t.name)
def test_columns_match_ddl_in_order(table):
    assert table.columns == DDL[table.name]["columns"]


@pytest.mark.parametrize("table", FACT_TABLES, ids=lambda t: t.name)
def test_foreign_keys_match_ddl(table):
    assert sorted(table.foreign_keys) == sorted(DDL[table.name]["fks"])


@pytest.mark.parametrize("table", ALL_TABLES, ids=lambda t: t.name)
def test_natural_key_is_a_unique_constraint_in_ddl(table):
    assert table.natural_key, f"{table.name} has no natural_key"
    assert set(table.natural_key) <= set(table.columns)
    assert table.natural_key in DDL[table.name]["uniques"]

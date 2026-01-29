# Auto-Fallthrough Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement smart default rank selection that automatically skips unpopulated ranks when no explicit `--levels` is specified.

**Architecture:** Add `find_first_populated_rank()` function to `breakdown.py` that queries the database to find the first rank with non-NULL values. Modify `cli.py:breakdown()` to use this function for default level selection while preserving explicit `--levels` behavior.

**Tech Stack:** Python 3, SQLite, Click CLI, pytest

---

## Task 1: Add `find_first_populated_rank()` - Next Rank Populated Case

**Files:**
- Test: `tests/test_breakdown.py`
- Modify: `src/taxa/breakdown.py`

**Step 1: Write the failing test for next rank populated**

Add to `tests/test_breakdown.py`:

```python
def test_find_first_populated_rank_next_rank_populated(sample_db):
    """When next rank has data, return it without skipping."""
    conn = sample_db

    # Rosaceae family has subfamilies populated
    populated, expected = find_first_populated_rank(conn, "Rosaceae", "family")

    assert populated == "subfamily"
    assert expected == "subfamily"
```

**Step 2: Run test to verify it fails**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_next_rank_populated -v`

Expected: FAIL with "ImportError: cannot import name 'find_first_populated_rank'"

**Step 3: Import the function in test file**

Modify import section of `tests/test_breakdown.py`:

```python
from taxa.breakdown import find_taxon_rank, generate_breakdown_query, find_first_populated_rank
```

**Step 4: Run test again**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_next_rank_populated -v`

Expected: FAIL with "AttributeError: module 'taxa.breakdown' has no attribute 'find_first_populated_rank'"

**Step 5: Write minimal implementation**

Add to `src/taxa/breakdown.py` after `find_taxon_rank()`:

```python
def find_first_populated_rank(conn, base_taxon, base_rank):
    """Find the first populated rank below base_rank for the given taxon.

    Checks each rank in hierarchical order to find the first one with
    non-NULL values among descendants of base_taxon.

    Args:
        conn: SQLite database connection
        base_taxon: Name of base taxon (e.g., "Rosaceae")
        base_rank: Rank of base taxon (e.g., "family")

    Returns:
        Tuple of (populated_rank, expected_rank) where:
        - populated_rank: First rank below base_rank with non-NULL data
        - expected_rank: The immediate next rank after base_rank

    Raises:
        ValueError: If no populated ranks found below base_rank
    """
    from taxa.taxonomy import get_next_ranks

    cursor = conn.cursor()

    # Get all ranks below base_rank
    remaining_ranks = get_next_ranks(base_rank, count=100)

    if not remaining_ranks:
        raise ValueError(f"No levels below '{base_rank}' in taxonomy")

    expected_rank = remaining_ranks[0]

    # Check each rank for non-NULL values
    for candidate_rank in remaining_ranks:
        result = cursor.execute(
            f"SELECT 1 FROM taxa WHERE {base_rank} = ? AND {candidate_rank} IS NOT NULL LIMIT 1",
            (base_taxon,)
        )
        if result.fetchone():
            return (candidate_rank, expected_rank)

    raise ValueError(f"No populated levels below '{base_rank}' in taxonomy")
```

**Step 6: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_next_rank_populated -v`

Expected: PASS

**Step 7: Commit**

```bash
git add tests/test_breakdown.py src/taxa/breakdown.py
git commit -m "feat: add find_first_populated_rank for next rank populated case

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Test Skipping One Unpopulated Rank

**Files:**
- Test: `tests/test_breakdown.py`

**Step 1: Write the failing test**

Add to `tests/test_breakdown.py`:

```python
def test_find_first_populated_rank_skip_one_rank(sample_db):
    """When next rank is NULL, skip to the first populated rank."""
    conn = sample_db

    # Dryadoideae subfamily has NULL tribe, but populated genus
    populated, expected = find_first_populated_rank(conn, "Dryadoideae", "subfamily")

    assert populated == "genus"
    assert expected == "tribe"
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_skip_one_rank -v`

Expected: PASS (implementation already handles this case)

**Step 3: Commit**

```bash
git add tests/test_breakdown.py
git commit -m "test: add case for skipping one unpopulated rank

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Test Skipping Multiple Ranks

**Files:**
- Test: `tests/test_breakdown.py`

**Step 1: Write the test**

Add to `tests/test_breakdown.py`:

```python
def test_find_first_populated_rank_skip_multiple_ranks(sample_db):
    """When multiple ranks are NULL, skip to the first populated rank."""
    conn = sample_db
    cursor = conn.cursor()

    # Create a taxon with NULL tribe and subtribe, but populated genus
    cursor.execute("""
        INSERT INTO taxa (id, name, rank, family, subfamily, tribe, subtribe, genus)
        VALUES (999, 'Test genus', 'genus', 'Rosaceae', 'Testinae', NULL, NULL, 'Testus')
    """)
    conn.commit()

    populated, expected = find_first_populated_rank(conn, "Testinae", "subfamily")

    assert populated == "genus"
    assert expected == "tribe"
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_skip_multiple_ranks -v`

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_breakdown.py
git commit -m "test: add case for skipping multiple unpopulated ranks

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Test Error When No Populated Ranks

**Files:**
- Test: `tests/test_breakdown.py`

**Step 1: Write the failing test**

Add to `tests/test_breakdown.py`:

```python
def test_find_first_populated_rank_no_populated_ranks(sample_db):
    """When no ranks below base are populated, raise ValueError."""
    conn = sample_db
    cursor = conn.cursor()

    # Create a species with no lower ranks populated
    cursor.execute("""
        INSERT INTO taxa (id, name, rank, family, genus, species, subspecies, variety)
        VALUES (998, 'Test species', 'species', 'Rosaceae', 'Testus', 'testus', NULL, NULL)
    """)
    conn.commit()

    with pytest.raises(ValueError, match="No populated levels below 'species' in taxonomy"):
        find_first_populated_rank(conn, "testus", "species")
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_no_populated_ranks -v`

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_breakdown.py
git commit -m "test: verify error when no populated ranks found

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Test Edge Case - Already at Lowest Rank

**Files:**
- Test: `tests/test_breakdown.py`

**Step 1: Write the test**

Add to `tests/test_breakdown.py`:

```python
def test_find_first_populated_rank_at_lowest_rank(sample_db):
    """When already at lowest rank, raise ValueError."""
    conn = sample_db

    # 'form' is the lowest rank
    with pytest.raises(ValueError, match="No levels below 'form' in taxonomy"):
        find_first_populated_rank(conn, "some_form", "form")
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_breakdown.py::test_find_first_populated_rank_at_lowest_rank -v`

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_breakdown.py
git commit -m "test: verify error at lowest taxonomic rank

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Integration Test - CLI Default Uses Populated Rank

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_breakdown_command_auto_fallthrough(sample_db, cli_runner):
    """Breakdown without --levels skips unpopulated ranks and shows notice."""
    result = cli_runner.invoke(
        cli.breakdown,
        ['Dryadoideae', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show genus (not tribe which is NULL)
    assert 'genus' in result.output
    assert 'Cercocarpus' in result.output
    # Should show notice to stderr
    assert '[Notice: tribe unpopulated, showing genus instead]' in result.stderr
```

**Step 2: Run test to verify it fails**

Run: `source ../../venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_auto_fallthrough -v`

Expected: FAIL (notice not shown yet, might show tribe instead of genus)

**Step 3: Modify CLI to use smart default**

Modify `src/taxa/cli.py:breakdown()` function, replacing lines 189-197:

```python
if levels:
    # Explicit levels - use as-is
    level_list = [level.strip() for level in levels.split(',')]
    validate_rank_sequence(base_rank, level_list)
else:
    # Smart default - find first populated rank
    try:
        populated_rank, expected_rank = find_first_populated_rank(
            conn, taxon_name, base_rank
        )
        level_list = [populated_rank]

        # Show notice if we skipped ranks
        if populated_rank != expected_rank:
            click.echo(
                f"[Notice: {expected_rank} unpopulated, showing {populated_rank} instead]",
                err=True
            )
    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
```

**Step 4: Update import in cli.py**

Modify the import line in `src/taxa/cli.py`:

```python
from taxa.breakdown import find_taxon_rank, generate_breakdown_query, find_first_populated_rank
```

**Step 5: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_auto_fallthrough -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/taxa/cli.py tests/test_cli.py
git commit -m "feat: integrate auto-fallthrough into breakdown command

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Integration Test - Explicit Levels Still Show NULL

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Write the test**

Add to `tests/test_cli.py`:

```python
def test_breakdown_command_explicit_levels_show_null(sample_db, cli_runner):
    """Breakdown with explicit --levels shows NULL values without fallthrough."""
    result = cli_runner.invoke(
        cli.breakdown,
        ['Dryadoideae', '--levels', 'tribe', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show tribe (even though it's NULL)
    assert 'tribe' in result.output
    assert 'NULL' in result.output
    # Should NOT show notice to stderr
    assert '[Notice:' not in result.stderr
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_explicit_levels_show_null -v`

Expected: PASS (this behavior should already work)

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: verify explicit levels bypass auto-fallthrough

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Integration Test - No Notice When Next Rank is Populated

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Write the test**

Add to `tests/test_cli.py`:

```python
def test_breakdown_command_no_notice_when_next_rank_populated(sample_db, cli_runner):
    """Breakdown shows no notice when next rank is populated."""
    result = cli_runner.invoke(
        cli.breakdown,
        ['Rosaceae', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show subfamily (which is populated)
    assert 'subfamily' in result.output
    # Should NOT show notice since we didn't skip
    assert '[Notice:' not in result.stderr
```

**Step 2: Run test to verify it passes**

Run: `source ../../venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_no_notice_when_next_rank_populated -v`

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: verify no notice when next rank is populated

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Run Full Test Suite

**Step 1: Run all tests**

Run: `source ../../venv/bin/activate && pytest tests/ -v`

Expected: All tests PASS

**Step 2: If any failures, debug and fix**

Review failures and address them systematically using @superpowers:systematic-debugging if needed.

**Step 3: Final commit if fixes were needed**

```bash
git add .
git commit -m "fix: address test failures from auto-fallthrough feature

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Manual Testing

**Step 1: Build test database if needed**

If sample database doesn't have Dryadoideae case:

```bash
# Verify flora.db exists or create test data
# This step depends on your data setup
```

**Step 2: Test auto-fallthrough behavior**

Run: `source ../../venv/bin/activate && python -m taxa.cli breakdown Dryadoideae`

Expected output to stderr: `[Notice: tribe unpopulated, showing genus instead]`
Expected output to stdout: Table with genus breakdown

**Step 3: Test explicit levels behavior**

Run: `source ../../venv/bin/activate && python -m taxa.cli breakdown Dryadoideae --levels tribe`

Expected: Table showing tribe with NULL values, no notice

**Step 4: Test no-skip case**

Run: `source ../../venv/bin/activate && python -m taxa.cli breakdown Rosaceae`

Expected: Table showing subfamily breakdown, no notice

**Step 5: Document manual test results**

Create note in your journal about test outcomes.

---

## Completion Checklist

Before marking complete, verify:

- [ ] All unit tests pass for `find_first_populated_rank()`
- [ ] All integration tests pass for CLI behavior
- [ ] Full test suite passes (128+ tests)
- [ ] Manual testing confirms expected behavior
- [ ] Commits follow conventional commit format
- [ ] All commits include co-author tag
- [ ] Code follows project style (DRY, YAGNI)
- [ ] Notice goes to stderr (not stdout)
- [ ] Explicit --levels bypasses auto-fallthrough

Use @superpowers:verification-before-completion before claiming done.

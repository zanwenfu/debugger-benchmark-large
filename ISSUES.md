# GitLab Issues for debugbench_large

Create these as issues in your GitLab repository. Each issue describes a real bug from the pytest codebase for the AI debugger to fix.

**Repository:** pytest (commit `4787fd64a4ca0dba5528b5651bddd254102fe9f3`)
**Commit message:** `Merge pull request #7167 from bluetech/lint-merge-fix`

---

## Issue #1: INTERNALERROR when exception in `__repr__`

**Title:** `INTERNALERROR when exception in __repr__`

**Labels:** `bug`, `difficulty: easy`

**Body:**

When a class has both a broken `__getattribute__` and `__repr__`, pytest crashes with an `INTERNALERROR` instead of showing a normal test failure.

**Minimal reproduction:**

```python
class SomeClass:
    def __getattribute__(self, attr):
        raise
    def __repr__(self):
        raise

def test():
    SomeClass().attr
```

Running `pytest` on this file produces:

```
INTERNALERROR> Traceback (most recent call last):
...
INTERNALERROR> File "src/_pytest/_io/saferepr.py", line 23, in _format_repr_exception
INTERNALERROR>     exc_info, obj.__class__.__name__, id(obj)
INTERNALERROR> File "test_repr.py", line 3, in __getattribute__
INTERNALERROR>     raise
INTERNALERROR> RuntimeError: No active exception to reraise
```

**Expected behavior:** pytest should handle the broken `__repr__` gracefully and display a normal test failure, not an `INTERNALERROR`.

**Hint:** The issue is in `src/_pytest/_io/saferepr.py`. The code accesses an attribute on `obj` in a way that triggers `__getattribute__`. There is a Python builtin that can get the class name without going through `__getattribute__`.

---

## Issue #2: `--runxfail` breaks `pytest.mark.skip` location reporting

**Title:** `--runxfail breaks pytest.mark.skip location reporting`

**Labels:** `bug`, `difficulty: medium`

**Body:**

When `@pytest.mark.skip` or `@pytest.mark.skipif` marks are used to skip a test, the skip location should point to the test item itself. This works correctly under normal execution:

```
SKIPPED [1] test_it.py:3: unconditional skip
```

However, when adding the `--runxfail` flag, the skip location changes incorrectly:

```
SKIPPED [1] src/_pytest/skipping.py:238: unconditional skip
```

The `--runxfail` flag is only about xfail and should not affect skip location reporting at all.

**Reproduction:**

```python
# test_skip.py
import pytest

@pytest.mark.skip
def test_skip_location() -> None:
    assert 0
```

```bash
# Correct location:
pytest -rs test_skip.py

# Wrong location:
pytest -rs --runxfail test_skip.py
```

**Hint:** The bug is in `src/_pytest/skipping.py`, in the `pytest_runtest_makereport` hook. Look at the control flow structure — a certain conditional block is coupled to a preceding block when it shouldn't be.

---

## Issue #3: Wrong path to test file when directory changed in fixture

**Title:** `Wrong path to test file when directory changed in fixture`

**Labels:** `bug`, `difficulty: medium-hard`

**Body:**

When a fixture changes the working directory (e.g., using `os.chdir()` or `monkeypatch.chdir()`), test failure paths are shown relative to the *new* directory instead of the original directory. This makes it impossible to click-to-jump to the error in an editor.

**Reproduction:**

```python
# test_path_error.py
import os
import shutil
import pytest

@pytest.fixture
def private_dir():
    out_dir = 'ddd'
    os.makedirs(out_dir, exist_ok=True)
    old_dir = os.getcwd()
    os.chdir(out_dir)
    yield out_dir
    os.chdir(old_dir)

def test_show_wrong_path(private_dir):
    assert False
```

**Expected:** `test_path_error.py:16: AssertionError`
**Actual:** `../test_path_error.py:16: AssertionError` (relative to the changed directory)

The displayed path should always stay relative to the original invocation directory, regardless of any working directory changes during the test.

**Hint:** The issue is in `src/_pytest/nodes.py`, in the `_repr_failure_py` method. The code currently checks whether `os.getcwd()` succeeds, but doesn't actually compare the current directory against the original invocation directory. When the CWD has changed, paths should be displayed as absolute to avoid confusion.

---

## Issue #4: Incorrect caching of `skipif`/`xfail` string condition evaluation

**Title:** `Incorrect caching of skipif/xfail string condition evaluation`

**Labels:** `bug`, `difficulty: hard`

**Body:**

pytest caches the evaluation of string conditions in `@pytest.mark.skipif("expr")` and `@pytest.mark.xfail("expr")`. However, the cache key is only the expression string itself, ignoring the item's globals. This causes incorrect behavior when two different modules use the same expression string but with different values.

**Reproduction:**

```python
# test_module_1.py
import pytest
skip = True

@pytest.mark.skipif("skip")
def test_should_skip():
    assert False
```

```python
# test_module_2.py
import pytest
skip = False

@pytest.mark.skipif("skip")
def test_should_not_skip():
    assert False
```

```bash
pytest test_module_1.py test_module_2.py
```

**Expected:** `test_should_skip` is skipped, `test_should_not_skip` is NOT skipped.
**Actual:** Both tests are skipped, because the cached result from `test_module_1.py` (where `skip=True`) is reused for `test_module_2.py` (where `skip=False`).

**Hint:** The bug is in `src/_pytest/mark/evaluate.py`. The `cached_eval` function uses a dictionary keyed only by the expression string. The fix involves removing the caching mechanism entirely (it provides negligible performance benefit) and evaluating the expression directly each time.
# SOLUTIONS — Answer Key (Do NOT include in student repo)

**Base commit:** `4787fd64a4ca0dba5528b5651bddd254102fe9f3`
**Commit message:** `Merge pull request #7167 from bluetech/lint-merge-fix`

---

## Bug #1 (Easy) — INTERNALERROR when exception in `__repr__`

**Original GitHub Issue:** [pytest-dev/pytest#7145](https://github.com/pytest-dev/pytest/issues/7145)
**Original GitHub PR:** [pytest-dev/pytest#7168](https://github.com/pytest-dev/pytest/pull/7168)

**File:** `src/_pytest/_io/saferepr.py`, line 23

**Problem:** `obj.__class__.__name__` goes through `__getattribute__`, which raises when it's broken. The function `_format_repr_exception` is specifically meant to handle broken repr, but itself crashes when `__getattribute__` is also broken.

**Fix:** Change `obj.__class__.__name__` to `type(obj).__name__`, which is a C-level call that bypasses `__getattribute__`.

```diff
 def _format_repr_exception(exc: BaseException, obj: Any) -> str:
     ...
     return "<[{} raised in repr()] {} object at 0x{:x}>".format(
-        exc_info, obj.__class__.__name__, id(obj)
+        exc_info, type(obj).__name__, id(obj)
     )
```

---

## Bug #2 (Medium) — `--runxfail` breaks `pytest.mark.skip` location reporting

**Original GitHub Issue:** [pytest-dev/pytest#7392](https://github.com/pytest-dev/pytest/issues/7392)
**Original GitHub PR:** [pytest-dev/pytest#7432](https://github.com/pytest-dev/pytest/pull/7432)

**File:** `src/_pytest/skipping.py`, line 162

**Problem:** The skip-location-correction block (lines 162-170) is an `elif` branch of the xfail handling block. When `--runxfail` is active, the xfail block executes (even for skipped tests), and the `elif` prevents the skip location correction from running.

**Fix:** Change `elif` to `if` so the skip location block runs independently of the xfail block.

```diff
             else:
                 rep.outcome = "passed"
                 rep.wasxfail = explanation
-    elif (
+
+    if (
         item._store.get(skipped_by_mark_key, True)
         and rep.skipped
         and type(rep.longrepr) is tuple
```

---

## Bug #3 (Medium-Hard) — Wrong path to test file when directory changed in fixture

**Original GitHub Issue:** [pytest-dev/pytest#6428](https://github.com/pytest-dev/pytest/issues/6428)
**Original GitHub PR:** [pytest-dev/pytest#7220](https://github.com/pytest-dev/pytest/pull/7220)

**File:** `src/_pytest/nodes.py`, lines 349-353

**Problem:** The code calls `os.getcwd()` only to check if the CWD is accessible (for OSError), but discards the result. It always sets `abspath = False`, meaning paths are always shown as relative to the current directory — which is wrong when a fixture has changed the CWD.

**Fix:** Compare the current CWD to `self.config.invocation_dir`. If they differ, use absolute paths.

```diff
+from _pytest.pathlib import Path
 ...
         try:
-            os.getcwd()
-            abspath = False
+            abspath = Path(os.getcwd()) != Path(str(self.config.invocation_dir))
         except OSError:
             abspath = True
```

Note: The `Path` import needs to be added at the top of the file (import from `_pytest.pathlib`). The `str()` wrapping of `invocation_dir` may be needed depending on the version (it might be a `py.path.local` object).

---

## Bug #4 (Hard) — Incorrect caching of `skipif`/`xfail` string condition evaluation

**Original GitHub Issue:** [pytest-dev/pytest#7360](https://github.com/pytest-dev/pytest/issues/7360)
**Original GitHub PR:** [pytest-dev/pytest#7373](https://github.com/pytest-dev/pytest/pull/7373)

**File:** `src/_pytest/mark/evaluate.py`, lines 14-27 and line 96

**Problem:** `cached_eval()` caches results keyed only by the expression string. When two modules define different values for the same variable name (e.g., `skip = True` vs `skip = False`), the second evaluation returns the cached result from the first module, ignoring different globals.

**Fix:** Remove the caching mechanism entirely and evaluate directly each time.

```diff
 from ..outcomes import fail
 from ..outcomes import TEST_OUTCOME
-from .structures import Mark
-from _pytest.config import Config
 from _pytest.nodes import Item
-from _pytest.store import StoreKey
 
 
-evalcache_key = StoreKey[Dict[str, Any]]()
+def compiled_eval(expr: str, d: Dict[str, object]) -> Any:
+    import _pytest._code
 
-
-def cached_eval(config: Config, expr: str, d: Dict[str, object]) -> Any:
-    default = {}  # type: Dict[str, object]
-    evalcache = config._store.setdefault(evalcache_key, default)
-    try:
-        return evalcache[expr]
-    except KeyError:
-        import _pytest._code
-
-        exprcode = _pytest._code.compile(expr, mode="eval")
-        evalcache[expr] = x = eval(exprcode, d)
-        return x
+    exprcode = _pytest._code.compile(expr, mode="eval")
+    return eval(exprcode, d)
```

And update the call site (line 96):

```diff
                     if isinstance(expr, str):
                         d = self._getglobals()
-                        result = cached_eval(self.item.config, expr, d)
+                        result = compiled_eval(expr, d)
```

Also remove the now-unused imports of `Config`, `StoreKey`, and `Mark` (if not used elsewhere), and remove `evalcache_key`.

---

## Quick Reference

| # | Difficulty | Issue | PR | File | Line(s) |
|---|---|---|---|---|---|
| 1 | Easy | [#7145](https://github.com/pytest-dev/pytest/issues/7145) | [#7168](https://github.com/pytest-dev/pytest/pull/7168) | `src/_pytest/_io/saferepr.py` | 23 |
| 2 | Medium | [#7392](https://github.com/pytest-dev/pytest/issues/7392) | [#7432](https://github.com/pytest-dev/pytest/pull/7432) | `src/_pytest/skipping.py` | 162 |
| 3 | Medium-Hard | [#6428](https://github.com/pytest-dev/pytest/issues/6428) | [#7220](https://github.com/pytest-dev/pytest/pull/7220) | `src/_pytest/nodes.py` | 349-353 |
| 4 | Hard | [#7360](https://github.com/pytest-dev/pytest/issues/7360) | [#7373](https://github.com/pytest-dev/pytest/pull/7373) | `src/_pytest/mark/evaluate.py` | 14-27, 96 |
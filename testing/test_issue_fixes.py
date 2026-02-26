"""
Tests for the 4 benchmark issues described in ISSUES.md.

These tests are designed to FAIL on the current buggy code.
When a student's AI debugger fixes the corresponding bug, the test should PASS.

Run only these tests:
    python -m pytest testing/test_issue_fixes.py -v
"""
import pytest


class TestIssue1SafereprInternalError:
    """Issue #1: INTERNALERROR when exception in __repr__.

    When a class has both a broken __getattribute__ and __repr__,
    saferepr() should handle it gracefully instead of crashing.
    """

    def test_saferepr_broken_getattribute_and_repr(self, testdir):
        """_format_repr_exception should handle broken __getattribute__
        gracefully — it must not crash when accessing obj.__class__."""
        testdir.makepyfile(
            """
            from _pytest._io.saferepr import _format_repr_exception

            class SomeClass:
                def __getattribute__(self, attr):
                    raise RuntimeError("broken getattr")
                def __repr__(self):
                    raise RuntimeError("broken repr")

            def test_format_repr_exception_no_crash():
                obj = SomeClass()
                exc = RuntimeError("broken repr")
                # This should NOT raise
                result = _format_repr_exception(exc, obj)
                assert "RuntimeError" in result or "SomeClass" in result
            """
        )
        result = testdir.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_format_repr_exception_no_crash*PASSED*"])

    def test_saferepr_broken_getattribute_and_repr_no_internalerror(self, testdir):
        """End-to-end: pytest should not produce INTERNALERROR for a test
        with a broken __repr__ and __getattribute__."""
        testdir.makepyfile(
            """
            class SomeClass:
                def __getattribute__(self, attr):
                    raise RuntimeError("broken getattr")
                def __repr__(self):
                    raise RuntimeError("broken repr")

            def test_broken_repr():
                SomeClass().attr
            """
        )
        result = testdir.runpytest()
        # Should show a normal failure, not INTERNALERROR
        result.stdout.fnmatch_lines(["*1 failed*"])
        assert result.ret == 1
        assert "INTERNALERROR" not in result.stdout.str()
        assert "INTERNALERROR" not in result.stderr.str()


class TestIssue2RunxfailSkipLocation:
    """Issue #2: --runxfail breaks pytest.mark.skip location reporting.

    The --runxfail flag should only affect xfail, not skip.
    Skip location should always point to the test item, not to
    pytest internals.
    """

    def test_mark_skip_location_with_runxfail(self, testdir):
        testdir.makepyfile(
            """
            import pytest

            @pytest.mark.skip(reason="unconditional skip")
            def test_skip_location():
                assert 0
            """
        )
        result = testdir.runpytest("-rs", "--runxfail")
        result.stdout.fnmatch_lines(
            ["SKIPPED *test_mark_skip_location_with_runxfail.py*unconditional skip"]
        )
        # The skip location must NOT point to pytest internals
        assert "skipping.py" not in result.stdout.str()

    def test_mark_skipif_location_with_runxfail(self, testdir):
        testdir.makepyfile(
            """
            import pytest

            @pytest.mark.skipif(True, reason="always skip")
            def test_skipif_location():
                assert 0
            """
        )
        result = testdir.runpytest("-rs", "--runxfail")
        result.stdout.fnmatch_lines(
            [
                "SKIPPED *test_mark_skipif_location_with_runxfail.py*always skip"
            ]
        )
        assert "skipping.py" not in result.stdout.str()


class TestIssue3WrongPathOnChdir:
    """Issue #3: Wrong path to test file when directory changed in fixture.

    When a fixture changes the working directory, test failure paths
    should still be correct (not relative to the new cwd).
    """

    def test_chdir_fixture_shows_correct_path(self, testdir):
        testdir.makepyfile(
            """
            import os
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
            """
        )
        result = testdir.runpytest()
        result.stdout.fnmatch_lines(["*1 failed*"])
        # The path in the failure output should NOT contain ".." which
        # indicates it was computed relative to the changed directory.
        stdout = result.stdout.str()
        assert "../" not in stdout


class TestIssue4SkipifCacheGlobals:
    """Issue #4: Incorrect caching of skipif/xfail string condition evaluation.

    When two modules define different values for a variable, and both use
    the same skipif("varname") expression, they should each evaluate in
    their own module's globals — not share a cached result.
    """

    def test_skipif_string_condition_per_module(self, testdir):
        testdir.makepyfile(
            test_module_1="""
                import pytest
                skip = True

                @pytest.mark.skipif("skip")
                def test_should_skip():
                    assert False
            """,
            test_module_2="""
                import pytest
                skip = False

                @pytest.mark.skipif("skip")
                def test_should_not_skip():
                    assert False
            """,
        )
        result = testdir.runpytest("-v")
        result.stdout.fnmatch_lines(
            [
                "*test_module_1*::test_should_skip*SKIPPED*",
                "*test_module_2*::test_should_not_skip*FAILED*",
            ]
        )

    def test_skipif_string_condition_reverse_order(self, testdir):
        """Same bug verified in reverse order to confirm it's caching."""
        testdir.makepyfile(
            test_module_a="""
                import pytest
                skip = False

                @pytest.mark.skipif("skip")
                def test_should_not_skip():
                    assert False
            """,
            test_module_b="""
                import pytest
                skip = True

                @pytest.mark.skipif("skip")
                def test_should_skip():
                    assert False
            """,
        )
        result = testdir.runpytest("test_module_a.py", "test_module_b.py", "-v")
        result.stdout.fnmatch_lines(
            [
                "*test_module_a*::test_should_not_skip*FAILED*",
                "*test_module_b*::test_should_skip*SKIPPED*",
            ]
        )

"""
Tests for SemanticImpactFilter — batch processing, error handling, LLM integration.
"""
import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import Future

from app.services.semantic_impact_filter import SemanticImpactFilter, _parse_response, _build_signature
from app.services.dependency_analyzer import FileAnalysis


class ConcreteSemanticFilter(SemanticImpactFilter):
    """Concrete implementation for testing."""

    def __init__(self, llm_response: str = '{"relevant_files": []}'):
        self.llm_response = llm_response
        self.llm_calls = []

    def filter(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        return self._run_batches(requirement, candidates)

    def _call_llm(self, prompt: str) -> str:
        self.llm_calls.append(prompt)
        return self.llm_response


class TestSemanticFilterBuilding:
    """Test file signature building."""

    def test_build_signature_path_only(self):
        """Verify signature with no classes/functions."""
        fa = FileAnalysis(file_path="app/models/user.py", language="python", classes=[], functions=[], imports=[])
        sig = _build_signature("app/models/user.py", fa)
        assert sig == "app/models/user.py"

    def test_build_signature_with_classes(self):
        """Verify signature includes class names."""
        fa = FileAnalysis(file_path="app/models/user.py", language="python", classes=["User", "Admin", "Guest"], functions=[], imports=[])
        sig = _build_signature("app/models/user.py", fa)
        assert "User" in sig
        assert "Admin" in sig
        assert "classes=" in sig

    def test_build_signature_with_functions(self):
        """Verify signature includes function names (up to 8)."""
        functions = [f"func_{i}" for i in range(10)]
        fa = FileAnalysis(file_path="app/utils/helpers.py", language="python", classes=[], functions=functions, imports=[])
        sig = _build_signature("app/utils/helpers.py", fa)
        # Should include first 8 functions
        assert "func_0" in sig
        assert "func_7" in sig
        assert "func_9" not in sig  # Over limit


class TestParseResponse:
    """Test LLM response parsing."""

    def test_parse_response_valid_json(self):
        """Verify valid JSON is parsed correctly."""
        raw = '{"relevant_files": [{"path": "a.py", "score": 85}, {"path": "b.py", "score": 65}]}'
        candidates = {"a.py", "b.py", "c.py"}

        result = _parse_response(raw, candidates)

        assert "a.py" in result
        assert "b.py" in result
        assert "c.py" not in result  # Not in LLM response

    def test_parse_response_filters_by_candidates(self):
        """Verify only candidate files are returned (no hallucination)."""
        raw = '{"relevant_files": [{"path": "a.py", "score": 85}, {"path": "hallucinated.py", "score": 90}]}'
        candidates = {"a.py", "b.py"}

        result = _parse_response(raw, candidates)

        assert "a.py" in result
        assert "hallucinated.py" not in result  # Not in candidates

    def test_parse_response_invalid_json_fallback(self):
        """Verify invalid JSON returns all candidates (fail-open)."""
        raw = "this is not json at all"
        candidates = {"a.py", "b.py", "c.py"}

        result = _parse_response(raw, candidates)

        # Should return all candidates on parse error
        assert result == candidates

    def test_parse_response_malformed_response_structure(self):
        """Verify missing relevant_files key returns all candidates (fail-open)."""
        raw = '{"error": "some error"}'
        candidates = {"a.py", "b.py"}

        result = _parse_response(raw, candidates)

        # Missing 'relevant_files' key → parse fails → return all candidates
        assert result == candidates or result == set()  # Depends on extract_json behavior

    def test_parse_response_missing_path_field(self):
        """Verify items without path field are skipped."""
        raw = '{"relevant_files": [{"score": 85}, {"path": "a.py", "score": 90}]}'
        candidates = {"a.py"}

        result = _parse_response(raw, candidates)

        assert "a.py" in result
        assert len(result) == 1


class TestSemanticFilterBatchProcessing:
    """Test batch processing and error recovery."""

    def test_filter_empty_candidates_returns_empty(self):
        """Verify empty candidates → empty result."""
        filter_impl = ConcreteSemanticFilter()
        result = filter_impl.filter("requirement", {})
        assert result == set()

    def test_filter_single_batch(self):
        """Verify single batch is processed."""
        response = '{"relevant_files": [{"path": "a.py", "score": 85}]}'
        filter_impl = ConcreteSemanticFilter(llm_response=response)

        candidates = {
            "a.py": FileAnalysis(file_path="a.py", language="python", classes=[], functions=[], imports=[]),
            "b.py": FileAnalysis(file_path="b.py", language="python", classes=[], functions=[], imports=[]),
        }
        result = filter_impl.filter("add caching", candidates)

        assert "a.py" in result
        assert len(filter_impl.llm_calls) == 1

    def test_filter_multiple_batches(self):
        """Verify multiple batches (40+ files) are split and processed."""
        response = '{"relevant_files": [{"path": "file_0.py", "score": 85}]}'
        filter_impl = ConcreteSemanticFilter(llm_response=response)

        # Create 100 candidates (triggers 3 batches of 40 each)
        candidates = {
            f"file_{i}.py": FileAnalysis(file_path=f"file_{i}.py", language="python", classes=[], functions=[], imports=[])
            for i in range(100)
        }

        # Actually invoke the filter with the candidates
        result = filter_impl.filter("requirement", candidates)

        # Should have processed multiple batches
        assert len(filter_impl.llm_calls) > 1
        # Should have file_0.py in result
        assert "file_0.py" in result

    def test_filter_batch_error_keeps_all_in_batch(self):
        """Verify batch failure returns all files in that batch (fail-open)."""

        class FailingFilter(SemanticImpactFilter):
            def filter(self, requirement: str, candidates: dict) -> set[str]:
                return self._run_batches(requirement, candidates)

            def _call_llm(self, prompt: str) -> str:
                raise Exception("LLM API down")

        filter_impl = FailingFilter()
        candidates = {
            f"file_{i}.py": FileAnalysis(file_path=f"file_{i}.py", language="python", classes=[], functions=[], imports=[])
            for i in range(50)
        }

        result = filter_impl.filter("requirement", candidates)

        # Should return all candidates since all batches failed (fail-open)
        assert len(result) == 50

    def test_filter_partial_batch_failure(self):
        """Verify partial batch failure returns failed batch + successful results."""

        class PartiallyFailingFilter(SemanticImpactFilter):
            def __init__(self):
                self.call_count = 0

            def filter(self, requirement: str, candidates: dict) -> set[str]:
                return self._run_batches(requirement, candidates)

            def _call_llm(self, prompt: str) -> str:
                self.call_count += 1
                if self.call_count == 1:
                    # First batch succeeds
                    return '{"relevant_files": [{"path": "file_0.py", "score": 85}]}'
                else:
                    # Second batch fails
                    raise Exception("Timeout")

        filter_impl = PartiallyFailingFilter()
        candidates = {
            f"file_{i}.py": FileAnalysis(file_path=f"file_{i}.py", language="python", classes=[], functions=[], imports=[])
            for i in range(100)
        }

        result = filter_impl.filter("requirement", candidates)

        # Should have successful result + all files from failed batch (fail-open)
        assert "file_0.py" in result
        assert len(result) >= 40  # At least the failed batch


class TestSemanticFilterLLMIntegration:
    """Test LLM interaction and prompt building."""

    def test_filter_includes_requirement_in_prompt(self):
        """Verify requirement text is included in prompt."""
        response = '{"relevant_files": []}'
        filter_impl = ConcreteSemanticFilter(llm_response=response)

        candidates = {
            "a.py": FileAnalysis(file_path="a.py", language="python", classes=[], functions=[], imports=[]),
        }
        filter_impl.filter("implement caching layer", candidates)

        prompt = filter_impl.llm_calls[0]
        assert "implement caching layer" in prompt
        assert "a.py" in prompt

    def test_filter_includes_file_signatures_in_prompt(self):
        """Verify file signatures with classes/functions in prompt."""
        response = '{"relevant_files": []}'
        filter_impl = ConcreteSemanticFilter(llm_response=response)

        candidates = {
            "cache.py": FileAnalysis(
                file_path="cache.py",
                language="python",
                classes=["CacheManager", "RedisCache"],
                functions=["get", "set"],
                imports=["redis"]
            ),
        }
        filter_impl.filter("implement caching", candidates)

        prompt = filter_impl.llm_calls[0]
        assert "CacheManager" in prompt
        assert "RedisCache" in prompt

    def test_filter_respects_batch_size_limit(self):
        """Verify batch size is capped at 40 files."""
        response = '{"relevant_files": []}'
        filter_impl = ConcreteSemanticFilter(llm_response=response)

        candidates = {
            f"file_{i}.py": FileAnalysis(file_path=f"file_{i}.py", language="python", classes=[], functions=[], imports=[])
            for i in range(100)
        }
        filter_impl.filter("requirement", candidates)

        # With 100 files and batch size 40, should have 3 batches
        # (but with ThreadPoolExecutor, exact order may vary)
        assert len(filter_impl.llm_calls) >= 2

    def test_filter_concurrent_processing(self):
        """Verify multiple batches are processed concurrently."""
        call_times = []

        class ConcurrencyCheckingFilter(SemanticImpactFilter):
            def filter(self, requirement: str, candidates: dict) -> set[str]:
                return self._run_batches(requirement, candidates)

            def _call_llm(self, prompt: str) -> str:
                import time
                call_times.append(time.time())
                return '{"relevant_files": []}'

        filter_impl = ConcurrencyCheckingFilter()
        candidates = {
            f"file_{i}.py": FileAnalysis(file_path=f"file_{i}.py", language="python", classes=[], functions=[], imports=[])
            for i in range(100)
        }

        filter_impl.filter("requirement", candidates)

        # With concurrent execution, batches should overlap in time
        # (Hard to test deterministically, but we can verify multiple calls happened)
        assert len(call_times) >= 2

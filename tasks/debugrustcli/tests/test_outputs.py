"""
Comprehensive test suite for the Rust JSON parser debugging task.

Tests verify:
1. Code compiles successfully
2. Valid JSON is pretty-printed correctly
3. Invalid JSON produces appropriate error messages
4. Invalid UTF-8 is handled gracefully (no panics)
5. File IO errors are handled gracefully
6. Error exit codes are correct
"""

import subprocess
import json
import tempfile
import os
import pytest


BINARY_PATH = "/app/target/release/json-parser"
APP_DIR = "/app"


class TestCompilation:
    """Test that the code compiles successfully."""

    def test_cargo_build_succeeds(self):
        """Code must compile with cargo build --release."""
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0, (
            f"Compilation failed!\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    def test_binary_exists(self):
        """Release binary must be created."""
        assert os.path.exists(BINARY_PATH), (
            f"Binary not found at {BINARY_PATH}. "
            f"Run 'cargo build --release' first."
        )
        assert os.access(BINARY_PATH, os.X_OK), (
            f"Binary at {BINARY_PATH} is not executable"
        )


class TestValidJSON:
    """Test handling of valid JSON inputs."""

    def test_simple_json_from_stdin(self):
        """Simple JSON object should be pretty-printed."""
        input_json = '{"name":"Alice","age":30}'

        result = subprocess.run(
            [BINARY_PATH],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}\n"
            f"STDERR: {result.stderr}"
        )

        # Parse output to verify it's valid JSON
        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput:\n{result.stdout}")

        # Verify data matches
        assert output_data == {"name": "Alice", "age": 30}

        # Verify it's pretty-printed (contains newlines)
        assert "\n" in result.stdout, "Output should be pretty-printed with newlines"

    def test_nested_json_from_stdin(self):
        """Nested JSON should be pretty-printed."""
        input_json = '{"user":{"name":"Bob","address":{"city":"NYC","zip":"10001"}}}'

        result = subprocess.run(
            [BINARY_PATH],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert output_data["user"]["name"] == "Bob"
        assert output_data["user"]["address"]["city"] == "NYC"

    def test_json_array(self):
        """JSON arrays should be handled correctly."""
        input_json = '[1,2,3,{"key":"value"}]'

        result = subprocess.run(
            [BINARY_PATH],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert output_data == [1, 2, 3, {"key": "value"}]

    def test_json_from_file(self):
        """Should read and parse JSON from file argument."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data", "number": 42}, f)
            temp_path = f.name

        try:
            result = subprocess.run(
                [BINARY_PATH, temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == 0, f"STDERR: {result.stderr}"
            output_data = json.loads(result.stdout)
            assert output_data == {"test": "data", "number": 42}
        finally:
            os.unlink(temp_path)

    def test_empty_json_object(self):
        """Empty JSON object should be handled."""
        result = subprocess.run(
            [BINARY_PATH],
            input='{}',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert output_data == {}

    def test_empty_json_array(self):
        """Empty JSON array should be handled."""
        result = subprocess.run(
            [BINARY_PATH],
            input='[]',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert output_data == []


class TestInvalidJSON:
    """Test handling of invalid JSON inputs."""

    def test_invalid_json_syntax(self):
        """Invalid JSON should produce error message."""
        result = subprocess.run(
            [BINARY_PATH],
            input='{invalid}',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0, "Should exit with non-zero status for invalid JSON"
        assert "Error:" in result.stderr or "Error:" in result.stdout, (
            f"Error message should start with 'Error:'\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_unclosed_brace(self):
        """Unclosed brace should be detected."""
        result = subprocess.run(
            [BINARY_PATH],
            input='{"key":"value"',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0
        error_output = result.stderr + result.stdout
        assert "Error:" in error_output

    def test_trailing_comma(self):
        """Trailing comma should be detected as invalid."""
        result = subprocess.run(
            [BINARY_PATH],
            input='{"key":"value",}',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0
        error_output = result.stderr + result.stdout
        assert "Error:" in error_output

    def test_missing_quotes(self):
        """Missing quotes should be detected."""
        result = subprocess.run(
            [BINARY_PATH],
            input='{key:value}',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0
        error_output = result.stderr + result.stdout
        assert "Error:" in error_output


class TestUTF8Handling:
    """Test handling of invalid UTF-8 sequences."""

    def test_invalid_utf8_from_stdin(self):
        """Invalid UTF-8 should be handled gracefully, not panic."""
        # Send invalid UTF-8 bytes
        result = subprocess.run(
            [BINARY_PATH],
            input=b'\xff\xfe\xfd',
            capture_output=True,
            timeout=5
        )

        # Should NOT panic - should handle gracefully
        assert result.returncode != 0, "Should exit with error for invalid UTF-8"

        # Decode stderr/stdout carefully (it should be valid UTF-8 in error message)
        try:
            stderr_text = result.stderr.decode('utf-8', errors='replace')
            stdout_text = result.stdout.decode('utf-8', errors='replace')
        except Exception as e:
            pytest.fail(f"Error output itself has encoding issues: {e}")

        error_output = stderr_text + stdout_text
        assert "Error:" in error_output, (
            f"Should show error message for invalid UTF-8\n"
            f"Output: {error_output}"
        )

    def test_invalid_utf8_in_file(self):
        """Invalid UTF-8 in file should be handled gracefully."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
            # Write invalid UTF-8 bytes
            f.write(b'\xff\xfe{"test":true}')
            temp_path = f.name

        try:
            result = subprocess.run(
                [BINARY_PATH, temp_path],
                capture_output=True,
                timeout=5
            )

            assert result.returncode != 0, "Should exit with error for invalid UTF-8 in file"

            stderr_text = result.stderr.decode('utf-8', errors='replace')
            stdout_text = result.stdout.decode('utf-8', errors='replace')
            error_output = stderr_text + stdout_text
            assert "Error:" in error_output
        finally:
            os.unlink(temp_path)


class TestFileIOErrors:
    """Test handling of file I/O errors."""

    def test_nonexistent_file(self):
        """Nonexistent file should produce clear error message."""
        result = subprocess.run(
            [BINARY_PATH, "/nonexistent/path/file.json"],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0, "Should exit with error for nonexistent file"
        error_output = result.stderr + result.stdout
        assert "Error:" in error_output, f"Should show error message\nOutput: {error_output}"

        # Error should mention the file path or "No such file"
        assert ("/nonexistent/path/file.json" in error_output or
                "No such file" in error_output or
                "not found" in error_output.lower())

    def test_directory_instead_of_file(self):
        """Trying to read a directory should produce error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [BINARY_PATH, tmpdir],
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode != 0
            error_output = result.stderr + result.stdout
            assert "Error:" in error_output


class TestErrorMessages:
    """Test that error messages are user-friendly."""

    def test_error_messages_start_with_error(self):
        """All error messages should start with 'Error:'."""
        test_cases = [
            ("{invalid}", "invalid JSON"),
            (b'\xff\xfe', "invalid UTF-8"),
        ]

        for input_data, description in test_cases:
            result = subprocess.run(
                [BINARY_PATH],
                input=input_data,
                capture_output=True,
                timeout=5
            )

            if isinstance(result.stderr, bytes):
                stderr_text = result.stderr.decode('utf-8', errors='replace')
                stdout_text = result.stdout.decode('utf-8', errors='replace')
            else:
                stderr_text = result.stderr
                stdout_text = result.stdout

            error_output = stderr_text + stdout_text
            assert "Error:" in error_output, (
                f"Error message for {description} should start with 'Error:'\n"
                f"Output: {error_output}"
            )


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_large_json(self):
        """Should handle reasonably large JSON files."""
        large_obj = {"item_" + str(i): {"value": i, "data": "x" * 100}
                     for i in range(100)}

        result = subprocess.run(
            [BINARY_PATH],
            input=json.dumps(large_obj),
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert len(output_data) == 100

    def test_unicode_content(self):
        """Should handle Unicode characters correctly."""
        input_json = '{"emoji":"😀","chinese":"你好","arabic":"مرحبا"}'

        result = subprocess.run(
            [BINARY_PATH],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert output_data["emoji"] == "😀"
        assert output_data["chinese"] == "你好"
        assert output_data["arabic"] == "مرحبا"

    def test_whitespace_only(self):
        """Whitespace-only input should produce error."""
        result = subprocess.run(
            [BINARY_PATH],
            input='   \n\t  ',
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0
        error_output = result.stderr + result.stdout
        assert "Error:" in error_output

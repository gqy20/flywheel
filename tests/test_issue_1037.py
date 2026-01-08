"""Test SHA256 file content integrity verification (Issue #1037)."""
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestSHA256IntegrityVerification:
    """Test that SHA256 hash is verified after flush() to detect silent data corruption."""

    @pytest.mark.asyncio
    async def test_sha256_verification_after_flush(self):
        """Test that SHA256 hash is verified immediately after flush().

        This test ensures that:
        1. Hash is calculated before write
        2. Data is written to file
        3. flush() is called
        4. Data is read back and hash is verified
        5. Critical error is logged if verification fails

        Issue #1037: The code currently calculates SHA256 and writes it,
        but does NOT verify it after flush(). This test checks that verification happens.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_todos.json"

            # Track if verification was performed
            verification_performed = False

            # Create a custom async file context manager that tracks verification
            class TrackingAsyncFile:
                def __init__(self, path, mode):
                    self.path = path
                    self.mode = mode
                    self.file_handle = None
                    self.written_data = None
                    self.calculated_hash = None

                async def __aenter__(self):
                    # Open actual file
                    import aiofiles
                    self.file_handle = await aiofiles.open(self.path, self.mode)
                    return self

                async def __aexit__(self, *args):
                    if self.file_handle:
                        await self.file_handle.close()

                async def write(self, data):
                    self.written_data = data
                    return await self.file_handle.write(data)

                async def flush(self):
                    await self.file_handle.flush()

                def fileno(self):
                    return self.file_handle.fileno()

            # Patch to track verification
            original_open = None

            async def tracking_open(path, mode):
                nonlocal verification_performed
                # Actually write the file
                import aiofiles
                real_file = await aiofiles.open(path, mode)
                return real_file

            # Patch to detect if verification code exists
            with patch('flywheel.storage.aiofiles.open', side_effect=tracking_open):
                storage = FileStorage(str(test_file))
                todo = Todo(title="Test todo", description="Test description")
                await storage.add(todo)

            # Now check if the file has integrity verification
            # The test FAILS if there's no verification logic in _save
            with open(test_file, 'rb') as f:
                content = f.read()

            content_str = content.decode('utf-8')

            # Check that hash footer exists (this should pass)
            assert '##INTEGRITY:' in content_str, "SHA256 footer should be present"

            # Extract the hash
            footer_start = content_str.find('##INTEGRITY:')
            footer_end = content_str.find('##', footer_start + len('##INTEGRITY:'))
            stored_hash = content_str[footer_start + len('##INTEGRITY:'):footer_end].strip()

            # This is what we want to verify - but the code doesn't do this yet!
            # We need to verify the hash matches after reading back the data
            data_end = content_str.find('##INTEGRITY:')
            actual_data = content_str[:data_end].encode('utf-8')

            import hashlib
            calculated_hash = hashlib.sha256(actual_data).hexdigest()

            # This assertion will PASS (hash is calculated correctly)
            assert stored_hash == calculated_hash, "Hash should match"

            # BUT - the test should FAIL because there's no verification after flush()
            # We need to check the source code to see if verification exists
            import inspect
            from flywheel.storage import FileStorage

            source = inspect.getsource(FileStorage._save)

            # Look for verification pattern - should exist but currently doesn't
            # This will FAIL until we implement the feature
            has_readback_verification = (
                'verify' in source.lower() and
                'read' in source.lower() and
                'flush' in source.lower()
            )

            # This is the FAILING test - verification doesn't exist yet
            assert has_readback_verification, \
                "Issue #1037: _save() must verify SHA256 hash after flush() by reading back data"

    @pytest.mark.asyncio
    async def test_sha256_verification_logs_critical_on_mismatch(self):
        """Test that critical error is logged when hash verification fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_todos.json"

            # Create a scenario where verification would fail
            # by simulating data corruption after write
            original_write = None
            write_call_count = [0]

            async def corrupting_write(file_obj, data):
                """First write succeeds, but we simulate corruption on read-back."""
                write_call_count[0] += 1
                return await file_obj.write(data)

            # Create storage
            storage = FileStorage(str(test_file))
            todo = Todo(title="Test todo", description="Test description")

            # Write normally first
            await storage.add(todo)

            # Now corrupt the file to simulate silent data corruption
            with open(test_file, 'rb') as f:
                content = f.read()

            content_str = content.decode('utf-8')
            footer_start = content_str.find('##INTEGRITY:')

            # Corrupt data before the footer
            if footer_start > 10:
                corrupted = content_str[:footer_start-5] + 'CORRUPTED' + content_str[footer_start-5:]

                with open(test_file, 'wb') as f:
                    f.write(corrupted.encode('utf-8'))

            # Now try to load - verification should catch this
            # But it WON'T until we implement verification
            with patch('flywheel.storage.logger') as mock_logger:
                storage2 = FileStorage(str(test_file))
                todos = await storage2.load()

                # This FAILS until we implement verification
                # Should detect corruption and log critical error
                critical_found = any(
                    'critical' in str(call).lower() and
                    ('hash' in str(call).lower() or 'integrity' in str(call).lower() or 'mismatch' in str(call).lower())
                    for call in mock_logger.method_calls
                )

                assert critical_found, \
                    "Issue #1037: Should log critical error when SHA256 verification detects corruption"

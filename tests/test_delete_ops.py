"""
Unit tests for delete operations using robocopy mirror technique
"""

import pytest
import subprocess
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, call
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations.delete_ops import delete_folder, delete_with_robocopy_mirror, delete_with_shutil_retry


class TestDeleteOpsRobocopy:
    """Test cases for robocopy-based delete operations"""
    
    def test_delete_folder_success(self, temp_dir, mock_log_func):
        """Test successful folder deletion"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        (test_folder / "file.txt").write_text("test")
        
        result = delete_folder(test_folder, mock_log_func)
        
        assert result is True
        assert not test_folder.exists()
        mock_log_func.assert_called_with(f"Deleted folder: {test_folder}", "success")
    
    def test_delete_folder_missing(self, temp_dir, mock_log_func):
        """Test deleting non-existent folder"""
        missing_folder = temp_dir / "missing"
        
        result = delete_folder(missing_folder, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_with(
            f"No folder found to delete: {missing_folder}",
            "warn"
        )
    
    @patch('operations.delete_ops.delete_with_robocopy_mirror')
    def test_delete_folder_uses_robocopy_first(self, mock_robocopy, temp_dir, mock_log_func):
        """Test that robocopy mirror is tried first"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        mock_robocopy.return_value = True
        
        result = delete_folder(test_folder, mock_log_func)
        
        assert result is True
        mock_robocopy.assert_called_once_with(test_folder, mock_log_func)
    
    @patch('operations.delete_ops.delete_with_robocopy_mirror')
    @patch('operations.delete_ops.delete_with_shutil_retry')
    def test_delete_folder_fallback_to_shutil(self, mock_shutil, mock_robocopy, temp_dir, mock_log_func):
        """Test fallback to shutil when robocopy fails"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        mock_robocopy.return_value = False
        mock_shutil.return_value = True
        
        result = delete_folder(test_folder, mock_log_func)
        
        assert result is True
        mock_robocopy.assert_called_once()
        mock_shutil.assert_called_once()
    
    @patch('subprocess.run')
    def test_robocopy_mirror_success(self, mock_run, temp_dir, mock_log_func):
        """Test robocopy mirror deletion success"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        (test_folder / "file.txt").write_text("test")
        
        # Mock successful robocopy
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = delete_with_robocopy_mirror(test_folder, mock_log_func)
        
        assert result is True
        
        # Verify robocopy was called with mirror flag
        call_args = mock_run.call_args[0][0]
        assert '/MIR' in call_args
        assert str(test_folder) in call_args
    
    @patch('subprocess.run')
    def test_robocopy_mirror_failure(self, mock_run, temp_dir, mock_log_func):
        """Test robocopy mirror failure"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        
        mock_result = Mock()
        mock_result.returncode = 16  # Error
        mock_run.return_value = mock_result
        
        result = delete_with_robocopy_mirror(test_folder, mock_log_func)
        
        assert result is False
    
    @patch('subprocess.run')
    def test_robocopy_mirror_exception(self, mock_run, temp_dir, mock_log_func):
        """Test robocopy mirror exception handling"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        
        mock_run.side_effect = Exception("Robocopy error")
        
        result = delete_with_robocopy_mirror(test_folder, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_with(
            f"Robocopy mirror deletion failed: Robocopy error",
            "warn"
        )
    
    def test_shutil_retry_success(self, temp_dir, mock_log_func):
        """Test shutil retry deletion success"""
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        (test_folder / "file.txt").write_text("test")
        
        result = delete_with_shutil_retry(test_folder, mock_log_func)
        
        assert result is True
        assert not test_folder.exists()
    
    def test_shutil_retry_with_readonly_files(self, temp_dir, mock_log_func):
        """Test deletion of readonly files with retry"""
        import stat
        
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()
        readonly_file = test_folder / "readonly.txt"
        readonly_file.write_text("readonly")
        os.chmod(readonly_file, stat.S_IREAD)
        
        result = delete_with_shutil_retry(test_folder, mock_log_func)
        
        assert result is True
        assert not test_folder.exists()
    
    @patch('shutil.rmtree')
    def test_shutil_retry_permission_error(self, mock_rmtree, temp_dir, mock_log_func):
        """Test retry logic on permission errors"""
        test_folder = temp_dir / "test_folder"
        
        # Fail first two attempts, succeed on third
        mock_rmtree.side_effect = [
            PermissionError("Access denied"),
            PermissionError("Access denied"),
            None  # Success on third try
        ]
        
        result = delete_with_shutil_retry(test_folder, mock_log_func, retry_count=3)
        
        assert result is True
        assert mock_rmtree.call_count == 3
    
    @patch('shutil.rmtree')
    def test_shutil_retry_all_fail(self, mock_rmtree, temp_dir, mock_log_func):
        """Test when all retry attempts fail"""
        test_folder = temp_dir / "test_folder"
        
        mock_rmtree.side_effect = PermissionError("Access denied")
        
        result = delete_with_shutil_retry(test_folder, mock_log_func, retry_count=3)
        
        assert result is False
        assert mock_rmtree.call_count == 3
        mock_log_func.assert_called_with(
            f"Failed to delete {test_folder}: Access denied",
            "error"
        )
"""
Unit tests for copy operations using robocopy
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, call
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations.copy_ops import copy_folder


class TestCopyOpsRobocopy:
    """Test cases for robocopy-based copy operations"""
    
    def test_copy_folder_success(self, temp_dir, sample_folder, mock_log_func, mock_robocopy_success):
        """Test successful folder copy with robocopy"""
        dst = temp_dir / "destination"
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        # Verify result
        assert result is True
        
        # Verify robocopy was called with correct arguments
        mock_robocopy_success.assert_called_once()
        call_args = mock_robocopy_success.call_args[0][0]
        assert 'robocopy' in call_args
        assert str(sample_folder) in call_args
        assert str(dst) in call_args
        assert '/E' in call_args  # Copy subdirectories
        assert '/MT:16' in call_args  # Multi-threaded
        assert '/R:5' in call_args  # Retry count
        
        # Verify log messages
        mock_log_func.assert_any_call(f"Starting robocopy from {sample_folder} to {dst}...", "info")
        mock_log_func.assert_any_call(f"Successfully copied from {sample_folder} to {dst}", "success")
    
    def test_copy_folder_source_missing(self, temp_dir, mock_log_func):
        """Test copy when source folder doesn't exist"""
        missing_src = temp_dir / "missing_source"
        dst = temp_dir / "destination"
        
        result = copy_folder(missing_src, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_once_with(
            f"Source folder does not exist: {missing_src}",
            "error"
        )
    
    def test_copy_folder_dest_exists(self, temp_dir, sample_folder, mock_log_func):
        """Test copy when destination already exists"""
        dst = temp_dir / "destination"
        dst.mkdir()
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_once_with(
            f"Destination already exists: {dst}. Skipping copy.",
            "warn"
        )
    
    @patch('subprocess.run')
    def test_copy_folder_robocopy_returns_no_files(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test robocopy returns 0 when destination did not exist — source template is empty"""
        dst = temp_dir / "destination"
        # dst does NOT exist — robocopy exit code 0 means source was empty, new folder created

        mock_result = Mock()
        mock_result.returncode = 0  # No files copied
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = copy_folder(sample_folder, dst, mock_log_func)

        assert result is True
        mock_log_func.assert_any_call(
            f"Copied to new folder {dst} (source template is empty)",
            "warn"
        )

    @patch('subprocess.run')
    @patch('operations.copy_ops._is_network_path')
    def test_copy_folder_robocopy_returns_no_files_dst_existed(self, mock_is_network, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test robocopy returns 0 when destination already existed — genuine in-sync"""
        dst = temp_dir / "destination"
        dst.mkdir()  # Destination already exists
        # Patch _is_network_path to return True for dst so the pre-check is skipped
        mock_is_network.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0  # No files copied
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = copy_folder(sample_folder, dst, mock_log_func)

        assert result is True
        mock_log_func.assert_any_call(
            "Source and destination are already in sync (no files copied)",
            "info"
        )
    
    @patch('subprocess.run')
    def test_copy_folder_robocopy_warnings(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test robocopy returns warning code (3) but still success"""
        dst = temp_dir / "destination"
        
        mock_result = Mock()
        mock_result.returncode = 3  # Files copied with warnings
        mock_result.stdout = "Warning: Some files skipped"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is True
        mock_log_func.assert_any_call(f"Successfully copied from {sample_folder} to {dst}", "success")
    
    @patch('subprocess.run')
    def test_copy_folder_robocopy_failure(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test robocopy failure with error code 8+"""
        dst = temp_dir / "destination"
        
        mock_result = Mock()
        mock_result.returncode = 16  # Fatal error
        mock_result.stdout = ""
        mock_result.stderr = "Access denied"
        mock_run.return_value = mock_result
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_any_call(
            "Robocopy failed with exit code 16: Access denied",
            "error"
        )
    
    @patch('subprocess.run')
    def test_copy_folder_robocopy_timeout(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test robocopy timeout"""
        dst = temp_dir / "destination"
        
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='robocopy', timeout=3600)
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_with(
            f"Robocopy timed out after 1 hour copying {sample_folder} to {dst}",
            "error"
        )
    
    @patch('subprocess.run')
    def test_copy_folder_robocopy_not_found(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test when robocopy is not available"""
        dst = temp_dir / "destination"
        
        mock_run.side_effect = FileNotFoundError("robocopy not found")
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_with(
            "Robocopy not found. Please ensure Windows is properly installed.",
            "error"
        )
    
    @patch('subprocess.run')
    def test_copy_folder_general_exception(self, mock_run, temp_dir, sample_folder, mock_log_func):
        """Test general exception handling"""
        dst = temp_dir / "destination"
        
        mock_run.side_effect = Exception("Unexpected error")
        
        result = copy_folder(sample_folder, dst, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_with(
            "Robocopy failed: Unexpected error",
            "error"
        )
    
    def test_copy_folder_with_unc_paths(self, temp_dir, mock_log_func, mock_robocopy_success):
        """Test copy with UNC paths"""
        src = Path(r"\\server\share\source")
        dst = Path(r"\\server\share\destination")
        
        # Mock source exists
        with patch.object(Path, 'exists', return_value=True):
            result = copy_folder(src, dst, mock_log_func)
            
            assert result is True
            call_args = mock_robocopy_success.call_args[0][0]
            assert str(src) in call_args
            assert str(dst) in call_args
    
    def test_copy_folder_with_network_mapped_drive(self, temp_dir, mock_log_func, mock_robocopy_success):
        """Test copy with mapped network drive"""
        src = Path("V:/source")
        dst = Path("W:/destination")
        
        # Mock source exists
        with patch.object(Path, 'exists', return_value=True):
            result = copy_folder(src, dst, mock_log_func)
            
            assert result is True
            call_args = mock_robocopy_success.call_args[0][0]
            assert str(src) in call_args
            assert str(dst) in call_args
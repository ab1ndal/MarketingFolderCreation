"""
Unit tests for shortcut creation
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations.shortcut_ops import create_shortcut


class TestShortcutOps:
    """Test cases for shortcut creation"""
    
    def test_create_shortcut_success(self, temp_dir, mock_log_func, mock_win32com):
        """Test successful shortcut creation"""
        target = temp_dir / "target"
        target.mkdir()
        shortcut_path = temp_dir / "shortcut.lnk"
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is True
        
        # Verify win32com calls
        mock_win32com['dispatch'].assert_called_once_with("WScript.Shell")
        mock_win32com['shell'].CreateShortCut.assert_called_once_with(str(shortcut_path))
        
        shortcut = mock_win32com['shortcut']
        assert shortcut.Targetpath == str(target)
        assert shortcut.WorkingDirectory == str(target.parent)
        assert shortcut.IconLocation == "explorer.exe"
        shortcut.save.assert_called_once()
        
        mock_log_func.assert_called_once_with(
            f"Shortcut created: {shortcut_path} → {target}",
            "success"
        )
    
    def test_create_shortcut_with_file_target(self, temp_dir, mock_log_func, mock_win32com):
        """Test shortcut pointing to a file (not folder)"""
        file_target = temp_dir / "target.txt"
        file_target.write_text("test")
        shortcut_path = temp_dir / "shortcut.lnk"
        
        result = create_shortcut(file_target, shortcut_path, mock_log_func)
        
        assert result is True
        assert mock_win32com['shortcut'].Targetpath == str(file_target)
        assert mock_win32com['shortcut'].WorkingDirectory == str(file_target.parent)
    
    def test_create_shortcut_with_unc_path(self, temp_dir, mock_log_func, mock_win32com):
        """Test shortcut with UNC path target"""
        target = Path(r"\\server\share\folder")
        shortcut_path = temp_dir / "shortcut.lnk"
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is True
        assert mock_win32com['shortcut'].Targetpath == str(target)
        assert mock_win32com['shortcut'].WorkingDirectory == str(target.parent)
    
    def test_create_shortcut_with_network_mapped_drive(self, temp_dir, mock_log_func, mock_win32com):
        """Test shortcut with mapped network drive"""
        target = Path("V:/folder")
        shortcut_path = temp_dir / "shortcut.lnk"
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is True
        assert mock_win32com['shortcut'].Targetpath == str(target)
    
    def test_create_shortcut_win32com_import_error(self, temp_dir, mock_log_func):
        """Test handling of win32com import error"""
        target = temp_dir / "target"
        shortcut_path = temp_dir / "shortcut.lnk"
        
        # Simulate ImportError by patching import
        with patch.dict('sys.modules', {'win32com.client': None}):
            # Force import to fail
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'win32com.client':
                    raise ImportError("No module named win32com")
                return original_import(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                result = create_shortcut(target, shortcut_path, mock_log_func)
                
                assert result is False
                mock_log_func.assert_called_once_with(
                    "win32com module not available. Shortcut creation requires pywin32.",
                    "error"
                )
    
    def test_create_shortcut_com_failure(self, temp_dir, mock_log_func, mock_win32com):
        """Test COM dispatch failure"""
        target = temp_dir / "target"
        shortcut_path = temp_dir / "shortcut.lnk"
        
        mock_win32com['dispatch'].side_effect = Exception("COM initialization failed")
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_once_with(
            "Shortcut creation failed: COM initialization failed",
            "error"
        )
    
    def test_create_shortcut_save_failure(self, temp_dir, mock_log_func, mock_win32com):
        """Test shortcut save failure"""
        target = temp_dir / "target"
        shortcut_path = temp_dir / "shortcut.lnk"
        
        mock_win32com['shortcut'].save.side_effect = PermissionError("Access denied")
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_once_with(
            "Shortcut creation failed: Access denied",
            "error"
        )
    
    def test_create_shortcut_invalid_path(self, temp_dir, mock_log_func, mock_win32com):
        """Test invalid shortcut path"""
        target = temp_dir / "target"
        invalid_shortcut = Path("invalid:chars?.lnk")
        
        mock_win32com['shell'].CreateShortCut.side_effect = Exception("Invalid file path")
        
        result = create_shortcut(target, invalid_shortcut, mock_log_func)
        
        assert result is False
        mock_log_func.assert_called_once_with(
            "Shortcut creation failed: Invalid file path",
            "error"
        )
    
    def test_create_shortcut_with_long_paths(self, temp_dir, mock_log_func, mock_win32com):
        """Test shortcut with long path names"""
        long_name = "a" * 200
        target = temp_dir / long_name
        target.mkdir()
        shortcut_path = temp_dir / f"{long_name}.lnk"
        
        result = create_shortcut(target, shortcut_path, mock_log_func)
        
        assert result is True
        assert mock_win32com['shortcut'].Targetpath == str(target)
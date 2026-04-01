"""
Pytest configuration and fixtures for robocopy testing
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    dir_path = tempfile.mkdtemp()
    yield Path(dir_path)
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def mock_log_func():
    """Create a mock logging function"""
    return Mock()


@pytest.fixture
def sample_folder(temp_dir):
    """Create a sample folder structure for testing"""
    src = temp_dir / "source"
    src.mkdir()
    
    # Create test files
    (src / "file1.txt").write_text("content1")
    (src / "file2.txt").write_text("content2")
    
    # Create subdirectories with files
    subdir = src / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("content3")
    
    deep = src / "deep" / "nested" / "folder"
    deep.mkdir(parents=True)
    (deep / "file4.txt").write_text("content4")
    
    return src


@pytest.fixture
def mock_robocopy_success():
    """Mock successful robocopy execution"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1  # Files copied successfully
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_win32com():
    """Mock win32com for shortcut testing"""
    with patch('win32com.client.Dispatch') as mock_dispatch:
        mock_shell = Mock()
        mock_shortcut = Mock()
        mock_dispatch.return_value = mock_shell
        mock_shell.CreateShortCut.return_value = mock_shortcut
        yield {
            'dispatch': mock_dispatch,
            'shell': mock_shell,
            'shortcut': mock_shortcut
        }
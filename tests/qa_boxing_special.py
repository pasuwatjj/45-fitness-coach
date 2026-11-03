"""Compatibility entry point: current X challenge/cinematic two-player regression."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('qa_boxing_aim.py')), run_name='__main__')

"""Chạy eval gốc với agent CP3, không thay đổi dataset hay bộ chấm.

Ví dụ: python checkpoints/run_before.py --output eval_before.json
Các options giống evals/run_evals.py.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))

from checkpoints.agent_cp3 import run_agent
import run_evals


if __name__ == '__main__':
    # Runner giữ nguyên logic và config; chỉ chọn phiên bản agent trước cải tiến.
    run_evals.run_agent = run_agent
    sys.exit(run_evals.main())

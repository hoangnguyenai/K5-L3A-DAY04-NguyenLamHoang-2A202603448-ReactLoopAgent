"""Đọc hai eval thật để đối chiếu CP6; không sửa điểm hay file eval."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def metrics(report):
    calls = 0
    tokens = 0
    costs = 0
    missing_tokens = 0
    missing_cost = 0
    for case in report['cases']:
        result = case['result']
        calls += sum(t.get('event') in ('model', 'provider_error') for t in result['trace'])
        for usage in result.get('usage', []):
            if isinstance(usage.get('total_tokens'), (int, float)):
                tokens += usage['total_tokens']
            else:
                missing_tokens += 1
            if isinstance(usage.get('cost'), (int, float)):
                costs += usage['cost']
            else:
                missing_cost += 1
    return {
        'Model calls (agent)': calls,
        'Tokens (agent, reported)': f'{tokens}; missing usage: {missing_tokens}',
        'Cost USD (agent, reported)': f'{costs:.6f}; missing usage: {missing_cost}',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, default=ROOT / 'eval_before.json')
    parser.add_argument('--after', type=Path, default=ROOT / 'eval_after.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'CP_COMPARISON.md')
    args = parser.parse_args()
    try:
        before = json.loads(args.before.read_text(encoding='utf-8-sig'))
        after = json.loads(args.after.read_text(encoding='utf-8-sig'))
        expected = {c['id'] for c in json.loads((ROOT / 'evals/cases.json').read_text(encoding='utf-8'))}
        if before['config'] != after['config']:
            raise ValueError('Hai lan eval khac config; chua the so sanh theo yeu cau bai.')
        for report in (before, after):
            cases = report['cases']
            if len(cases) != len(expected) or {c['id'] for c in cases} != expected:
                raise ValueError('Can du 22 case core, khong trung ID.')
            if (report['summary']['score_0_100'] is None
                    or any(c['grade'].get('score') is None for c in cases)):
                raise ValueError('Con case unscored. Xem grade.reason va chay lai.')
        lines = [
            '# So sánh eval thật', '',
            'Hai file đủ 22 case và cùng config. Đây là báo cáo dữ liệu, không tự kết luận nguyên nhân thay đổi điểm.', '',
            '| Chỉ số | Before CP3 | After CP5 |', '|---|---|---|',
            f"| Điểm tổng | {before['summary']['score_0_100']} | {after['summary']['score_0_100']} |",
        ]
        bm, am = metrics(before), metrics(after)
        lines.extend(f'| {key} | {bm[key]} | {am[key]} |' for key in bm)
        lines += ['', 'Token/cost trên chỉ tính agent, không gồm judge. Usage thiếu không có nghĩa chi phí bằng 0.', '',
                  '| Case | Before | After | Source revisions (after) |', '|---|---:|---:|---:|']
        after_by_id = {c['id']: c for c in after['cases']}
        for case in before['cases']:
            other = after_by_id[case['id']]
            revisions = sum(t.get('event') == 'validation_missing_source' for t in other['result']['trace'])
            lines.append(f"| {case['id']} | {case['grade']['score']} | {other['grade']['score']} | {revisions} |")
        # Trích nguyên dữ liệu của case thấp điểm nhất để học viên phân tích.
        selected = min(before['cases'], key=lambda c: c['grade']['score'])
        other = after_by_id[selected['id']]
        lines += ['', f"## Case thấp điểm nhất trước cải tiến: {selected['id']}", '',
                  'Đối chiếu expected, answer và trace dưới đây để chọn case cho NOTES. '
                  'Case này không nhất thiết mắc lỗi thiếu URL; không suy ra source gate đã sửa được lỗi chỉ từ điểm số.', '',
                  '```json', json.dumps({
                      'id': selected['id'], 'question': selected['question'], 'expected': selected['expected'],
                      'before': {'answer': selected['result']['answer'], 'grade': selected['grade'], 'trace': selected['result']['trace']},
                      'after': {'answer': other['result']['answer'], 'grade': other['grade'], 'trace': other['result']['trace']},
                  }, ensure_ascii=False, indent=2), '```', '',
                  'Dùng bằng chứng thật để hoàn thiện NOTES.md. Một lần chạy mỗi phiên bản chưa chứng minh độ ổn định.', '']
        args.output.write_text('\n'.join(lines), encoding='utf-8')
        print(f'OK: 22 cases, same config. Report: {args.output}')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Chua dat CP6: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

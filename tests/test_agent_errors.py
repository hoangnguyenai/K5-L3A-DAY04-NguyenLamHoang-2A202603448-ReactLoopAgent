"""Regression tests cho observation và việc giữ trace khi provider lỗi."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class ErrorHandlingTests(unittest.TestCase):
    def test_provider_failure_keeps_previous_trace_and_usage(self):
        first = tool_call('a', 'get_status', '{"provider":"github"}')
        provider = Mock()
        provider.complete.side_effect = [first, RuntimeError('Provider unavailable')]
        result = run_agent('check', provider, StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][-1]['event'], 'provider_error')
        self.assertTrue(any(t['event'] == 'tool' for t in result['trace']))
        self.assertEqual(len(result['usage']), 1)

    def test_tool_timeout_is_returned_with_id_and_can_complete(self):
        tools = Mock()
        tools.schemas = []
        tools.system_prompt = 'Test'
        tools.execute.side_effect = TimeoutError('Tool timed out')
        provider = FakeProvider([
            tool_call('timeout-1', 'get_status', '{"provider":"github"}'),
            final('Khong du du lieu vi tool timeout.'),
        ])
        result = run_agent('check', provider, tools)
        self.assertEqual(result['status'], 'completed')
        observation = provider.histories[1][-1]
        self.assertEqual(observation['tool_call_id'], 'timeout-1')
        self.assertEqual(json.loads(observation['content'])['error'], 'TimeoutError')

    def test_non_object_json_is_invalid_arguments(self):
        for raw in ('[]', 'null', '"text"'):
            with self.subTest(raw=raw):
                provider = FakeProvider([tool_call('bad', 'get_status', raw), final()])
                self.assertEqual(run_agent('check', provider, StatusTools())['status'], 'completed')
                self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_unobserved_url_does_not_pass_evidence_gate(self):
        provider = FakeProvider([
            tool_call('details', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final('Nguon: https://example.invalid/fabricated'),
        ])
        result = run_agent('check', provider, StatusTools(), max_steps=2)
        self.assertEqual(result['status'], 'max_steps')
        self.assertEqual(result['trace'][-1]['event'], 'validation_missing_source')


if __name__ == '__main__':
    unittest.main()

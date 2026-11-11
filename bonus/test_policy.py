"""Kiểm tra chính sách bonus bằng scripted provider, không gọi API thật."""
import datetime
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent
from bonus.agent_policy import BonusPolicy, retry_delay
from bonus.test_agent import ScriptedProvider, call, final
from bonus.tools import BonusTools


class BonusPolicyTests(unittest.TestCase):
    def test_persistent_429_stops_actual_calls_and_keeps_other_provider(self):
        tools = BonusTools(scenario='rate_limit_always')
        provider = ScriptedProvider([
            call('gh', 'get_github_status', {}),
            *[call(str(i), 'get_vercel_status', {}) for i in range(4)],
            final('GitHub theo snapshot: https://www.githubstatus.com . '
                  'Vercel chua kiem tra duoc do rate limit.'),
        ])
        result = run_agent('Check both', provider, tools, max_steps=8)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(tools.calls[('get_vercel_status', 'vercel')], 3)
        self.assertTrue(any(t['event'] == 'tool_skipped' for t in result['trace']))
        blocked = json.loads(provider.histories[-1][-1]['content'])
        self.assertEqual(blocked['error'], 'RETRY_BUDGET_EXHAUSTED')
        self.assertEqual(provider.histories[-1][-1]['tool_call_id'], '3')

    def test_retry_after_waits_before_next_request(self):
        policy = BonusPolicy()
        trace = []
        with patch('bonus.agent_policy.time.monotonic', return_value=100), \
                patch('bonus.agent_policy.time.sleep') as sleep:
            observation = policy.observe('get_vercel_status', {}, {
                'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '2',
            })
            self.assertTrue(observation['agent_retry']['allowed'])
            self.assertIsNone(policy.before_call('get_vercel_status', {}, trace, 2))
            sleep.assert_called_once_with(2)
        self.assertEqual(trace[0]['event'], 'rate_limit_wait')

    def test_long_retry_after_does_not_call_early(self):
        policy = BonusPolicy(wait_budget=5)
        observation = policy.observe('get_vercel_status', {}, {
            'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '120',
        })
        self.assertFalse(observation['agent_retry']['allowed'])
        with patch('bonus.agent_policy.time.sleep') as sleep:
            blocked = policy.before_call('get_vercel_status', {}, [], 2)
            self.assertEqual(blocked['error'], 'RETRY_BUDGET_EXHAUSTED')
            sleep.assert_not_called()

    def test_retry_after_http_date_and_invalid_header(self):
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=120)
        delay = retry_delay({'retry_after': future.strftime('%a, %d %b %Y %H:%M:%S GMT')})
        self.assertTrue(110 < delay <= 120)
        self.assertIsNone(retry_delay({'retry_after': 'invalid'}))
        self.assertIsNone(retry_delay({'retry_after': 'Infinity'}))

    def test_noisy_context_keeps_raw_trace_and_evidence(self):
        provider = ScriptedProvider([
            call('v', 'get_vercel_status', {}),
            final('Theo snapshot: https://www.vercel-status.com'),
        ])
        result = run_agent('Check', provider, BonusTools(scenario='noisy'))
        raw = next(t['result'] for t in result['trace'] if t['event'] == 'tool')
        context = json.loads(provider.histories[1][-1]['content'])
        self.assertEqual(len(raw['distractors']), 160)
        self.assertNotIn('distractors', context)
        self.assertEqual(context['incidents'], raw['incidents'])
        self.assertEqual(context['source'], raw['source'])

    def test_pagination_returns_distinct_pages_with_matching_call_ids(self):
        tools = BonusTools()
        incident = tools.execute('get_vercel_status', {})['incidents'][0]['id']
        page = tools.execute('get_incident_details', {'provider': 'vercel', 'incident_id': incident})
        self.assertIsNotNone(page['next_offset'])
        provider = ScriptedProvider([
            call('p1', 'get_incident_details', {'provider': 'vercel', 'incident_id': incident}),
            call('p2', 'get_incident_details', {'provider': 'vercel', 'incident_id': incident,
                                             'offset': page['next_offset']}),
            final('Nguon: ' + page['url']),
        ])
        result = run_agent('Read timeline', provider, tools)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(provider.histories[1][-1]['tool_call_id'], 'p1')
        self.assertEqual(provider.histories[2][-1]['tool_call_id'], 'p2')
        self.assertIn('agent_pagination_note', json.loads(provider.histories[1][-1]['content']))

    def test_two_incident_providers_require_both_sources(self):
        tools = BonusTools()
        args = []
        urls = []
        for name in ('vercel', 'npm'):
            status = tools.execute(f'get_{name}_status', {})
            arguments = {'provider': name, 'incident_id': status['incidents'][0]['id']}
            args.append(arguments)
            urls.append(tools.execute('get_incident_details', arguments)['url'])
        provider = ScriptedProvider([
            call('v', 'get_incident_details', args[0]),
            call('n', 'get_incident_details', args[1]),
            final(urls[0]), final('Nguon: ' + ' '.join(urls)),
        ])
        result = run_agent('Compare', provider, tools)
        self.assertEqual(result['status'], 'completed')
        validation = next(t for t in result['trace'] if t['event'] == 'validation_missing_source')
        self.assertIn('npm', validation['missing_provider_sources'])


if __name__ == '__main__':
    unittest.main()

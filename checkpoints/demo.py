"""Demo offline cùng một thiếu sót nguồn, trước và sau CP5. Không phải eval LLM."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from agent import run_agent as after
from checkpoints.agent_cp3 import run_agent as before
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


def demonstrate():
    tools = StatusTools()
    status = tools.get_status('github', 'Actions')
    incident_id = status['incidents'][0]['id']
    url = tools.get_incident_details('github', incident_id)['url']
    for label, agent in [('CP3 before', before), ('CP5 after', after)]:
        provider = FakeProvider([
            tool_call('status-1', 'get_status', json.dumps({'provider': 'github', 'component': 'Actions'})),
            tool_call('details-1', 'get_incident_details', json.dumps({'provider': 'github', 'incident_id': incident_id})),
            final('Theo snapshot, incident da duoc xu ly.'),
            final('Theo snapshot, incident da duoc xu ly. Nguon: ' + url),
        ])
        result = agent('Kiem tra Actions trong snapshot', provider, tools, max_steps=5)
        print(json.dumps({'version': label, **result}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    demonstrate()

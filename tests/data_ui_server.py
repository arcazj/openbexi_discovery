"""Isolated browser fixture: synthetic API/AI responses; real application and storage."""
import json
from types import SimpleNamespace
import httpx
import uvicorn

from backend import ai, api_connections, profile_adaptation, profiles
from backend.app import app

ROWS = [{'patient_name':'Alice Example','age':34,'outcome':2,'notes':'Alice Example at alice@example.org','password':'fictional-password'},
        {'patient_name':'Bob Example','age':46,'outcome':4,'notes':'Bob Example','password':'fictional-password'},
        {'patient_name':'Alice Example','age':34,'outcome':6,'notes':'Alice Example follow-up','password':'fictional-password'}]


def remote(request):
    if request.url.path == '/denied':
        return httpx.Response(401,json={'secret':'must-not-be-shown'})
    if request.url.host == 'api.crossref.org':
        return httpx.Response(200,json={'message':{'items':ROWS}})
    return httpx.Response(200,json={'rows':ROWS})


async def address(host):
    return None


api_connections.public_address = address
api_connections.HTTP_CLIENT = lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(remote),**kwargs)


class FakeAI:
    def __init__(self, **kwargs):
        self.responses=self
        self.models=self

    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def retrieve(self, *args): return SimpleNamespace(id='gpt-6-astra')

    async def parse(self, **kwargs):
        schema=kwargs['text_format']
        sent=json.dumps(kwargs['input'])
        assert not any(value in sent for value in ('Alice Example','Bob Example','fictional-password','private-fixture-token'))
        value={'recommendations':[{'service_id':'crossref','reason':'Find research publications relevant to your advanced REI profile.'}]} if schema is api_connections.Recommendations else {
            'answer':'The mean outcome is 4 across the three reviewed records. Compare Patient 1 and Patient 2 cautiously.',
            'limitations':['These are saved sample records, not a population estimate.']}
        if schema is profile_adaptation.ProfileProposal:
            reference = json.loads(kwargs['input'][1]['content'].split('\n', 1)[1])
            current = profiles.get_profile(reference['profile']['id'])
            value = {key: current[key] for key in (*profile_adaptation.FIELDS, 'ui')}
            value.update(goal='Investigate ovarian aging and fertility outcomes.',
                         explanation='Focus the goal and search examples on ovarian aging.')
            value['ui'] = {**current['ui'], 'examples':['ovarian aging fertility outcomes'], 'tip_text':'Compare ovarian aging evidence and identify a measurable outcome.'}
            if reference['reference_data'].get('requests_already_reflected') and kwargs['input'][-1]['content']=='Tailor my workspace around fertility outcomes and ovarian ageing.':
                value.update(decision='repeated_request',explanation='No profile changes needed. This is the same research focus as your earlier request.')
            if reference['reference_data']['allow_level_change']:
                value['learning_level']='researcher'
            if reference['reference_data']['allow_layout_changes']:
                value.update(tabs=['evidence','quizzes','notes'],panels=['guidance','tip'])
        return SimpleNamespace(output_parsed=schema.model_validate(value),usage={'input_tokens':100,'output_tokens':50})


ai.AsyncOpenAI=FakeAI

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=18773,log_level='warning')

"""Profile-scoped HTTPS JSON GET connections. No generated URLs or executable queries."""
import asyncio
import ipaddress
import json
import logging
import re
import socket
import uuid
from contextvars import ContextVar
from typing import Dict, List, Literal, Optional
from urllib.parse import parse_qsl, quote, quote_plus, urlsplit

import httpx
from fastapi import HTTPException
from pydantic import Field, SecretStr, field_validator

from . import ai, datasets, private_store, profiles
from .discovery_store import LOCK, data_root, identifier, read_json, require_online, stamp, write_json

HTTP_CLIENT = httpx.AsyncClient
REQUEST_SECRETS = ContextVar('data_api_request_secrets', default=())


class CredentialLogFilter(logging.Filter):
    def filter(self, record):
        values = REQUEST_SECRETS.get()
        if values:
            message = record.getMessage()
            for value in values:
                if value:
                    for representation in (value, quote(value, safe=''), quote_plus(value)):
                        message = message.replace(representation, '[credential removed]')
            record.msg, record.args = message, ()
        return True


logging.getLogger('httpx').addFilter(CredentialLogFilter())
CATALOG = [
    {'id':'crossref', 'name':'Crossref', 'description':'Scholarly publications and DOI metadata across research fields.',
     'url':'https://api.crossref.org/works', 'query_parameter':'query', 'rows_path':'message.items',
     'parameters':{'rows':'20','select':'DOI,title,author,published,subject,is-referenced-by-count,references-count,type,URL'}, 'documentation':'https://www.crossref.org/documentation/retrieve-metadata/rest-api/', 'auth_type':'none'},
    {'id':'clinicaltrials', 'name':'ClinicalTrials.gov', 'description':'Registered clinical studies; useful for health research and study-design learning.',
     'url':'https://clinicaltrials.gov/api/v2/studies', 'query_parameter':'query.term', 'rows_path':'studies',
     'parameters':{'format':'json','pageSize':'20','fields':'NCTId,BriefTitle,OverallStatus,Phase,EnrollmentCount,Condition'}, 'documentation':'https://clinicaltrials.gov/data-api/api', 'auth_type':'none'},
    {'id':'openlibrary', 'name':'Open Library', 'description':'Books and bibliographic metadata for learning across subjects.',
     'url':'https://openlibrary.org/search.json', 'query_parameter':'q', 'rows_path':'docs',
     'parameters':{'limit':'20','fields':'key,title,author_name,first_publish_year,edition_count'},
     'documentation':'https://openlibrary.org/dev/docs/api/search', 'auth_type':'none'}
]


class APIConfig(profiles.Strict):
    id: Optional[str] = None
    profile_id: str
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)
    query_parameter: str = Field(default='', max_length=100, pattern=r'^[A-Za-z0-9_.-]*$')
    rows_path: str = Field(default='', max_length=300, pattern=r'^[A-Za-z0-9_.-]*$')
    parameters: Dict[str, str] = Field(default_factory=dict, max_length=12)
    auth_type: Literal['none','bearer','api_key_header','api_key_query','basic'] = 'none'
    auth_name: str = Field(default='X-API-Key', max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    username: SecretStr = SecretStr('')
    credential: SecretStr = SecretStr('')

    @field_validator('parameters')
    @classmethod
    def safe_parameters(cls, value):
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', key) or datasets.SECRET_FIELD.search(key) or len(text) > 500 for key, text in value.items()):
            raise ValueError('Use ordinary query parameters; put credentials in the authentication fields.')
        return value


class Choice(profiles.Strict):
    service_id: Literal['crossref','clinicaltrials','openlibrary']
    reason: str = Field(min_length=1, max_length=800)


class Recommendations(profiles.Strict):
    recommendations: List[Choice] = Field(min_length=1, max_length=3)


def config_path():
    return data_root() / '.discovery' / 'api_connections.json'


def saved():
    return read_json(config_path(), {})


def public(profile_id):
    profiles.get_profile(profile_id)
    return [public_record(item) for item in saved().values() if item['profile_id'] == profile_id]


def public_record(item):
    return {key:value for key,value in item.items() if key != 'credential_ref'}


def credentials_for(item):
    return private_store.read('api', item.get('credential_ref', item['id'])) or {}


def get(cid, profile_id):
    value = saved().get(identifier(cid))
    if not value or value['profile_id'] != profile_id:
        raise HTTPException(404, 'API connection not found in this profile.')
    return value


def validate_url(url):
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment
                or parsed.port not in (None, 443) or any(datasets.SECRET_FIELD.search(key) for key, _ in parse_qsl(parsed.query))):
            raise ValueError()
        if parsed.hostname.lower() in {'localhost', 'metadata.google.internal'} or parsed.hostname.endswith('.localhost'):
            raise ValueError()
        return parsed
    except ValueError:
        raise HTTPException(422, 'Use a public HTTPS JSON endpoint on port 443, without embedded credentials. Enter authentication separately.') from None


async def public_address(host):
    try:
        addresses = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM), 4)
        if not addresses or any(not ipaddress.ip_address(value[4][0]).is_global for value in addresses):
            raise HTTPException(422, 'Local, private-network, and metadata endpoints are not supported by this Internet API connector.')
    except (socket.gaierror, asyncio.TimeoutError):
        raise HTTPException(502, 'The API hostname could not be resolved. Check the URL and network connection.') from None


async def retrieve(config, credentials, query=''):
    require_online()
    parsed = validate_url(config['url'])
    await public_address(parsed.hostname)
    params = dict(config['parameters'])
    if query:
        if not config['query_parameter']:
            raise HTTPException(422, 'This endpoint has no search parameter. Edit its query parameter or fetch its current data without search terms.')
        params[config['query_parameter']] = query
    headers = {'Accept':'application/json', 'User-Agent':'OpenBEXI-Discovery/1.2.1 (read-only research connector)'}
    auth = None
    kind, secret = config['auth_type'], credentials.get('credential', '')
    if kind == 'bearer':
        headers['Authorization'] = 'Bearer ' + secret
    elif kind == 'api_key_header':
        if config['auth_name'].lower() in {'host','cookie','content-length','connection','proxy-authorization'}:
            raise HTTPException(422, 'Choose a dedicated API-key header.')
        headers[config['auth_name']] = secret
    elif kind == 'api_key_query':
        params[config['auth_name']] = secret
    elif kind == 'basic':
        auth = httpx.BasicAuth(credentials.get('username', ''), secret)

    async def request():
        # Never follow redirects with credentials, use ambient proxies, or return provider bodies on errors.
        async with HTTP_CLIENT(timeout=20, follow_redirects=False, trust_env=False) as client:
            async with client.stream('GET', config['url'], params=params, headers=headers, auth=auth) as response:
                if response.status_code in (401, 403):
                    raise HTTPException(401, 'The API rejected authentication or access. Check its credentials and permissions.')
                if response.status_code == 429:
                    raise HTTPException(429, 'This API is rate limited. Wait before reconnecting or retrieving data.')
                if 300 <= response.status_code < 400:
                    raise HTTPException(422, 'The API redirected the request. Enter its final HTTPS endpoint; credentials were not forwarded.')
                if response.status_code >= 400:
                    raise HTTPException(502, f'The API returned HTTP {response.status_code}. Check the endpoint and query parameters.')
                if 'json' not in response.headers.get('content-type', '').lower():
                    raise HTTPException(422, 'This connector requires a JSON response. Use the service\'s JSON data endpoint.')
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 2 * 1024 * 1024:
                        raise HTTPException(413, 'API response exceeds 2 MB. Configure a smaller page or narrower search.')
                try:
                    result = json.loads(data)
                    if config['rows_path']:
                        for part in config['rows_path'].split('.'):
                            result = result[int(part)] if isinstance(result, list) else result[part]
                    elif isinstance(result, dict):
                        candidates = [key for key in ('results','data','items','records') if isinstance(result.get(key), list)]
                        result = result[candidates[0]] if len(candidates) == 1 else [result]
                    return [] if result == [] else datasets.normalize(result)[0]
                except (ValueError, KeyError, IndexError, TypeError):
                    raise HTTPException(422, 'No table was found at the configured records path. Choose the JSON array containing the records.') from None
    log_scope = REQUEST_SECRETS.set(tuple(credentials.values()))
    try:
        return await asyncio.wait_for(request(), 25)
    except (httpx.HTTPError, asyncio.TimeoutError, UnicodeError):
        raise HTTPException(502, 'The API request failed or timed out. Check the URL, TLS certificate, and network connection.') from None
    finally:
        REQUEST_SECRETS.reset(log_scope)


async def connect(value):
    profiles.get_profile(value.profile_id)
    validate_url(value.url)
    cid = identifier(value.id) if value.id else uuid.uuid4().hex
    previous = get(cid, value.profile_id) if value.id else None
    config = value.model_dump(exclude={'username','credential'})
    config.update(id=cid, type='api', read_only=True)
    if datasets.SECRET_FIELD.search(value.query_parameter):
        raise HTTPException(422, 'The search parameter cannot be a credential field.')
    credentials = {'credential':value.credential.get_secret_value(), 'username':value.username.get_secret_value()}
    if value.auth_type != 'none' and not credentials['credential']:
        if not previous or any(previous[key] != config[key] for key in ('url','auth_type','auth_name')):
            raise HTTPException(422, 'Enter credentials for this endpoint and authentication method.')
        credentials = credentials_for(previous)
    if value.auth_type == 'none':
        credentials = {}
    if value.auth_type == 'basic' and (not credentials.get('username') or not credentials.get('credential')):
        raise HTTPException(422, 'Enter both username and password.')
    if any('\n' in text or '\r' in text for text in credentials.values()):
        raise HTTPException(422, 'Credentials cannot contain line breaks.')
    rows = await retrieve(config, credentials)
    config.update(checked_at=stamp(), status='connected', sample_count=len(rows))
    with LOCK:
        items = saved()
        if previous and items.get(cid) != previous:
            raise HTTPException(409, 'This API connection changed during the test. Reopen it before saving.')
        # Commit a new credential reference atomically with its endpoint, so a disk failure
        # cannot pair new credentials with an earlier server URL.
        reference = uuid.uuid4().hex
        config['credential_ref'] = reference
        private_store.save('api', reference, credentials)
        items[cid] = config
        try:
            write_json(config_path(), items)
        except Exception:
            private_store.delete('api', reference)
            raise HTTPException(500, 'Could not save the API connection. The previous connection is unchanged.') from None
        if previous:
            private_store.delete('api', previous.get('credential_ref', cid))
    return public_record(config)


async def check(cid, profile_id):
    value = get(cid, profile_id)
    rows = await retrieve(value, credentials_for(value))
    with LOCK:
        items = saved()
        if cid in items:
            items[cid].update(checked_at=stamp(), status='connected', sample_count=len(rows))
            write_json(config_path(), items)
    return {'connected':True, 'rows':len(rows), 'message':'Connection verified. No data was sent to AI.'}


async def query(cid, profile_id, text):
    value = get(cid, profile_id)
    rows = await retrieve(value, credentials_for(value), text)
    if not rows:
        raise HTTPException(404, 'No records matched this API query. Try different search terms.')
    result = datasets.stage(profile_id, rows, 'API snapshot from ' + urlsplit(value['url']).hostname)
    result.update(connection_id=cid, captured_at=stamp(), scope='One API response; upstream pagination may contain more records.')
    return result


def disconnect(cid, profile_id):
    with LOCK:
        value = get(cid, profile_id)
        items = saved()
        del items[cid]
        write_json(config_path(), items)
        private_store.delete('api', value.get('credential_ref', cid))
    return {'disconnected':cid}


async def recommend(profile_id):
    profile = profiles.get_profile(profile_id)
    result = await ai.structured_task('recommend_apis', profile, 'Recommend relevant API sources for my learning and research profile.',
                                      {'catalog':CATALOG}, Recommendations)
    catalog = {item['id']:item for item in CATALOG}
    result['recommendations'] = [{**catalog[item['service_id']], 'reason':item['reason']} for item in result['recommendations']]
    return result

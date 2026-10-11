"""Local privacy review. The AI boundary accepts server-approved working copies only."""
import csv
import hashlib
import io
import json
import math
import re
import statistics
import time
import uuid
from collections import Counter, OrderedDict
from typing import List, Literal

from fastapi import HTTPException
from pydantic import Field

from . import library, private_store, profiles
from .discovery_store import LOCK, data_root, identifier, stamp, redact

STAGES = OrderedDict()
MAX_ROWS, MAX_COLUMNS = 5000, 100
SECRET_FIELD = re.compile(r'password|passwd|secret|token|api.?key|authorization|credential|private.?key', re.I)
IDENTITY_FIELD = re.compile(r'(^|[_. -])(name|first.?name|last.?name|full.?name|patient|participant|subject|mrn|ssn|email|phone|address|identifier|id|organization|organisation|company)([_. -]|$)', re.I)
TEXT_FIELD = re.compile(r'note|comment|description|narrative|text|contact', re.I)
EMAIL = re.compile(r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b')
PHONE = re.compile(r'(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)')
INLINE_SECRET = re.compile(r'(?i)\b(?:password|passwd|secret|token|api[_ -]?key|authorization)\s*[=:]\s*[^\s,;]+')


class Rule(profiles.Strict):
    field: str = Field(min_length=1, max_length=500)
    action: Literal['keep', 'pseudonymize', 'remove', 'mask', 'year', 'band']
    label: str = Field(default='Entity', pattern=r'^[A-Za-z][A-Za-z ]{0,30}$')


def flatten(row, prefix='', depth=0):
    if depth > 8:
        raise HTTPException(422, 'Nested data exceeds 8 levels. Export a simpler table.')
    result = {}
    for key, value in row.items():
        name = prefix + str(key)
        if len(name) > 500 or not name.strip():
            raise HTTPException(422, 'Use nonempty column names of at most 500 characters.')
        if isinstance(value, dict):
            part = flatten(value, name + '.', depth + 1)
        else:
            if isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False, allow_nan=False)
            if isinstance(value, float) and not math.isfinite(value):
                raise HTTPException(422, 'Dataset values must be finite numbers.')
            part = {name: value}
        if set(result).intersection(part):
            raise HTTPException(422, 'Nested and flat column names overlap. Rename the columns before importing.')
        result.update(part)
    return result


def normalize(rows):
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS or any(not isinstance(row, dict) for row in rows):
        raise HTTPException(422, 'Use a JSON array or CSV table containing 1 to 5,000 records.')
    try:
        result = [flatten(row) for row in rows]
        fields = list(dict.fromkeys(key for row in result for key in row))
        if not fields or len(fields) > MAX_COLUMNS or len(json.dumps(result)) > library.MAX_FILE:
            raise HTTPException(413, 'Use a dataset with up to 100 columns and 8 MB of data.')
        return result, fields
    except (ValueError, TypeError):
        raise HTTPException(422, 'Use valid JSON or CSV values.') from None


def parse_upload(filename, encoded):
    try:
        text = library.decode_file(encoded).decode('utf-8-sig')
        if filename.lower().endswith('.csv'):
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError('Duplicate headers')
            rows = []
            for row in reader:
                if None in row or len(rows) >= MAX_ROWS:
                    raise ValueError('Invalid row')
                rows.append(row)
            return rows
        if filename.lower().endswith('.json'):
            return json.loads(text)
    except (UnicodeError, ValueError, csv.Error):
        raise HTTPException(422, 'Import a UTF-8 CSV with unique headers or a JSON array, up to 5,000 rows.') from None
    raise HTTPException(422, 'Choose a CSV or JSON dataset.')


def suggest(field, rows):
    original_field = field
    field = re.sub(r'([a-z])([A-Z])', r'\1_\2', field)
    if SECRET_FIELD.search(field):
        return 'remove', 'Secret', 'Credential field; removal is required.'
    if IDENTITY_FIELD.search(field):
        label = 'Patient' if re.search(r'patient|subject|participant|mrn', field, re.I) else 'Organization' if re.search(r'organiz|organis|company', field, re.I) else 'Person'
        return 'pseudonymize', label, 'Possible identifying field.'
    if re.search(r'birth|dob|date', field, re.I):
        return 'year', 'Date', 'Dates can identify people; year only is suggested.'
    if TEXT_FIELD.search(field) or any(isinstance(row.get(original_field), str) and len(row[original_field]) > 120 for row in rows):
        return 'remove', 'Text', 'Free text can contain names or confidential information.'
    if any(EMAIL.search(str(row.get(original_field, ''))) or PHONE.search(str(row.get(original_field, ''))) for row in rows):
        return 'mask', 'Identifier', 'Contact information or a long identifier was detected.'
    return 'keep', 'Entity', 'Review this column; local detection cannot identify every sensitive value.'


def stage(profile_id, rows, source='Imported dataset'):
    profiles.get_profile(profile_id)
    rows, fields = normalize(rows)
    sid = uuid.uuid4().hex
    rules, details = [], []
    for field in fields:
        action, label, reason = suggest(field, rows)
        rules.append({'field':field, 'action':action, 'label':label})
        details.append({'field':field, 'reason':reason, 'required_remove':bool(SECRET_FIELD.search(field))})
    with LOCK:
        cleanup()
        if len(STAGES) >= 8:
            raise HTTPException(429, 'Close an existing privacy review before importing more datasets.')
        STAGES[(str(data_root()), sid)] = {'id':sid, 'profile_id':profile_id, 'rows':rows, 'fields':fields,
            'rules':rules, 'details':details, 'source':source, 'expires':time.monotonic() + 1800}
    return {'stage_id':sid, 'profile_id':profile_id, 'total':len(rows), 'fields':details, 'rules':rules,
            'original_preview':rows[:5], 'source':source, 'expires_in_seconds':1800}


def cleanup():
    for key, value in list(STAGES.items()):
        if value['expires'] < time.monotonic():
            del STAGES[key]


def get_stage(sid):
    cleanup()
    value = STAGES.get((str(data_root()), identifier(sid)))
    if not value:
        raise HTTPException(410, 'This private review expired. Import or retrieve the data again.')
    return value


def discard(sid):
    with LOCK:
        STAGES.pop((str(data_root()), identifier(sid)), None)
    return {'discarded':True}


def scrub(text, mapping=None):
    text = str(text)
    mapping = mapping or {}
    # One replacement pass avoids changing labels that happen to match a later original.
    if mapping:
        # Numeric measurements can equal an identifier; substitute numbers only in marked columns.
        names = {key:value for key,value in mapping.items() if not key.isdecimal()}
        labels = {value.casefold() for value in mapping.values()}
        candidates = set(names) | labels
        if candidates:
            pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(key) for key in sorted(candidates, key=len, reverse=True)) + r')(?!\w)', re.I)
            text = pattern.sub(lambda match: match.group() if match.group().casefold() in labels else names[match.group().casefold()], text)
    text = INLINE_SECRET.sub('[credential removed]', text)
    text = EMAIL.sub('[email masked]', text)
    text = PHONE.sub('[identifier masked]', text)
    return redact(text)


def transform(rows, rules, terms):
    forced_remove = {str(row[rule['field']]).casefold() for rule in rules if SECRET_FIELD.search(rule['field'])
                     for row in rows if row.get(rule['field']) is not None and row.get(rule['field']) != ''}
    mapping, groups = {key:'[removed]' for key in forced_remove}, {}
    for rule in rules:
        field, action, label = rule['field'], rule['action'], rule['label']
        if SECRET_FIELD.search(field):
            action = rule['action'] = 'remove'
        if action == 'keep':
            continue
        group = groups.setdefault(label, {})
        for row in rows:
            value = row.get(field)
            if value is None or value == '':
                continue
            key = str(value).casefold()
            if action == 'pseudonymize':
                group.setdefault(key, f'{label} {len(group) + 1}')
                replacement = group[key]
            elif action == 'year':
                match = re.match(r'^(\d{4})[-/]', str(value))
                replacement = match[1] if match else '[date masked]'
            elif action == 'band':
                try:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError()
                    low = math.floor(number / 10) * 10
                    replacement = f'{low}–{low + 9}'
                except (ValueError, TypeError):
                    replacement = '[value masked]'
            else:
                replacement = '[removed]' if action == 'remove' else '[masked]'
            # Removed secrets take precedence if a value occurs in several fields.
            if key not in forced_remove and (key not in mapping or action == 'pseudonymize'):
                mapping[key] = replacement
    for number, term in enumerate(terms, 1):
        if term.strip():
            mapping[term.strip().casefold()] = f'Sensitive {number}'
    result = []
    for row in rows:
        safe = {}
        for rule in rules:
            if rule['action'] == 'remove':
                continue
            field, value = rule['field'], row.get(rule['field'])
            output_field = scrub(field, mapping)
            if output_field in safe:
                raise HTTPException(422, 'Protection rules create duplicate column names. Remove one of those columns.')
            if value is not None and value != '' and rule['action'] != 'keep':
                value = mapping.get(str(value).casefold(), '[masked]')
            elif isinstance(value, str):
                value = scrub(value, mapping)
            safe[output_field] = value
        result.append(safe)
    if not result[0]:
        raise HTTPException(422, 'Keep at least one useful column in the working copy.')
    return result, mapping


def preview(sid, rules, terms, offset=0):
    with LOCK:
        value = get_stage(sid)
        rules = [Rule.model_validate(rule).model_dump() for rule in rules]
        if len(rules) != len(value['fields']) or {rule['field'] for rule in rules} != set(value['fields']):
            raise HTTPException(422, 'Review every column exactly once.')
        rows, mapping = transform(value['rows'], rules, terms)
        if len(json.dumps(rows)) > 440000:
            raise HTTPException(413, 'The working copy is too large for the local library. Import fewer rows or remove large text columns.')
        revision = uuid.uuid4().hex
        value['preview'] = {'id':revision, 'rows':rows, 'mapping':mapping, 'rules':rules, 'terms':terms}
        return {'preview_id':revision, 'rows':rows[offset:offset + 50], 'total':len(rows), 'offset':offset,
                'status':'pseudonymized', 'rules':rules,
                'notice':'Review the transformed data. Pseudonymization does not guarantee anonymity.'}


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def save_review(sid, preview_id, reviewed, retain_original=False, title='Reviewed dataset'):
    if not reviewed:
        raise HTTPException(403, 'Confirm the privacy review before saving a working copy.')
    with LOCK:
        value = get_stage(sid)
        review = value.get('preview')
        if not review or review['id'] != preview_id:
            raise HTTPException(409, 'Preview the current protection rules before saving.')
        item = library.save_activity({'profile_id':value['profile_id'], 'kind':'dataset', 'title':scrub(title, review['mapping']),
            'payload':{'rows':review['rows'], 'privacy':{'status':'pseudonymized', 'reviewed_at':stamp(),
                'source':value['source'], 'row_count':len(review['rows']), 'original_retained':retain_original}},
            'sensitive':True, 'consent_local':True, 'provenance':{'origin':'unverified'}})
        # Receipt is outside the portable library: a forged/imported privacy flag never authorizes AI.
        try:
            private_store.save('dataset', item['id'], {'digest':digest(item['payload']['rows']), 'mapping':review['mapping'],
                'rules':review['rules'], 'terms':review['terms'], 'source':value['source'],
                'original':value['rows'] if retain_original else None})
        except Exception:
            library.delete_activity(item['id'])
            raise
        discard(sid)
        return item


def all_rows(aid):
    item = library.get_activity(aid)
    if item['kind'] != 'dataset':
        raise HTTPException(422, 'Choose a saved dataset.')
    if item.get('filename'):
        import base64
        rows = parse_upload(item['filename'], base64.b64encode(library.artifact_file(aid).read_bytes()).decode())
    else:
        rows = item['payload'].get('rows')
        if rows is None:
            try:
                rows = json.loads(item.get('content', ''))
            except ValueError:
                raise HTTPException(422, 'This dataset needs a CSV or JSON array before review.') from None
    return item, normalize(rows)[0]


def review_saved(aid):
    item, rows = all_rows(aid)
    receipt = private_store.read('dataset', aid)
    original = receipt and receipt.get('original')
    result = stage(item['profile_id'], original or rows, 'Saved dataset')
    if original:
        result['rules'] = receipt['rules']
        result['terms'] = receipt['terms']
    result['original_available'] = bool(original)
    return result


def approved(aid):
    item, rows = all_rows(aid)
    receipt = private_store.read('dataset', aid)
    if not receipt or receipt['digest'] != digest(rows) or item['payload'].get('privacy', {}).get('status') != 'pseudonymized':
        raise HTTPException(403, 'Review and save a sanitized working copy on this computer before AI analysis.')
    return item, rows, receipt


def stats(rows):
    output = []
    for field in dict.fromkeys(key for row in rows for key in row):
        values = [row.get(field) for row in rows if row.get(field) is not None and row.get(field) != '']
        numeric = []
        for value in values:
            try:
                number = float(value)
                if isinstance(value, bool) or not math.isfinite(number):
                    raise ValueError()
                numeric.append(number)
            except (ValueError, TypeError):
                pass
        entry = {'field':field, 'present':len(values), 'missing':len(rows)-len(values)}
        if values and len(numeric) == len(values):
            ordered = sorted(numeric)
            middle = len(ordered) // 2
            median = ordered[middle] if len(ordered) % 2 else ordered[middle-1]/2 + ordered[middle]/2
            entry.update(kind='numeric', minimum=min(numeric), maximum=max(numeric), mean=statistics.mean(numeric), median=median)
        else:
            entry.update(kind='categorical', distinct=len(set(map(str, values))), most_common=Counter(map(str, values)).most_common(5))
        output.append(entry)
    return {'row_count':len(rows), 'columns':output, 'scope':'Entire saved working copy; not the full upstream source.'}

from gdcdictionary import gdcdictionary
import json
from lxml import etree
from mock import patch
import os
from gdcdatamodel import models as md
from .auth_mock import Config as auth_conf
from gdcapi.resources.submission.transactions.upload import UploadEntity
from gdcapi.resources.submission.files import make_s3_request
import contextlib
import boto
from moto import mock_s3
from flask import g
from collections import deque
import yaml

definitions = gdcdictionary.resolvers['_definitions.yaml'].source
SUBMITTED_STATE = definitions['state']['default']
DEFAULT_FILE_STATE = definitions['file_state']['default']

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'examples', 'valid')

ADMIN_HEADERS = {"X-Auth-Token": auth_conf.ADMIN_TOKEN}

fnames = [
    'experiment.json',
    'case.json',
    'sample.json',
    'aliquot.json',
    'demographic.json',
    'diagnosis.json',
    'exposure.json',
    'treatment.json',
]

BLGSP_PATH = '/v0/submission/CGCI/BLGSP/'
BRCA_PATH = '/v0/submission/TCGA/BRCA/'

@contextlib.contextmanager
def s3_conn():
    mock = mock_s3()
    mock.start(reset=False)
    conn = boto.connect_s3()
    yield conn
    bucket = conn.get_bucket('test_submission')
    for part in bucket.list_multipart_uploads():
        part.cancel_upload()
    mock.stop()


def mock_request(f):
    def wrapper(*args, **kwargs):
        mock = mock_s3()
        mock.start(reset=False)
        conn = boto.connect_s3()
        conn.create_bucket('test_submission')

        result = f(*args, **kwargs)
        mock.stop()
        return result
    return wrapper


def put_cgci(client, auth=None, role='admin'):
    path = '/v0/submission'
    headers = auth(path, 'put', role) if auth else None
    with open(os.path.join(DATA_DIR, 'program.json'), 'r') as f:
        program = f.read()
    r = client.put(path, headers=headers, data=program)
    del g.user
    return r


def put_cgci_blgsp(client, auth=None, role='admin'):
    put_cgci(client, auth=auth, role=role)
    path = '/v0/submission/CGCI/'
    headers = auth(path, 'put', role) if auth else None
    with open(os.path.join(DATA_DIR, 'project.json'), 'r') as f:
        project = f.read()
    r = client.put(path, headers=headers, data=project)
    assert r.status_code == 200, r.data
    del g.user
    return r


def put_tcga_brca(client, submitter=None):
    r = client.put(
        '/v0/submission/', headers=submitter('/v0/submission/', 'put', 'admin'), data=json.dumps({
            'name': 'TCGA', 'type': 'program',
            'dbgap_accession_number': 'phs000178'}))
    assert r.status_code == 200, r.data

    r = client.put(
        '/v0/submission/TCGA/', headers=submitter('/v0/submission/TCGA/', 'put', 'admin'), data=json.dumps({
            "type": "project",
            "code": "BRCA",
            "name": "TEST",
            "dbgap_accession_number": "phs000178",
            "state": "open"}))
    assert r.status_code == 200, r.data
    del g.user
    return r

def put_entity_from_file(client, path, submitter, BLGSP_PATH=BLGSP_PATH,
                         validate=True):
    with open(os.path.join(DATA_DIR, path), 'r') as f:
        entity = f.read()
    print "entity", entity
    r = client.put(BLGSP_PATH, headers=submitter(BLGSP_PATH, 'put'), data=entity)
    if validate:
        assert r.status_code == 200, r.data
    return r

def test_program_creation_endpoint(client, pg_driver, submitter):
    resp = put_cgci(client, auth=submitter)
    assert resp.status_code == 200, resp.data
    print resp.data
    resp = client.get('/v0/submission/')
    assert resp.json['links'] == ['/v0/submission/CGCI'], resp.json

def test_project_creation_endpoint(client, pg_driver, submitter):
    resp = put_cgci_blgsp(client, auth=submitter)
    assert resp.status_code == 200
    resp = client.get('/v0/submission/CGCI/')
    with pg_driver.session_scope():
        assert pg_driver.nodes(md.Project).count() == 1
        assert pg_driver.nodes(md.Project).path('programs')\
                                          .props(name='CGCI')\
                                          .count() == 1
    assert resp.json['links'] == ['/v0/submission/CGCI/BLGSP'], resp.json

def test_put_entity_creation_valid(client, pg_driver, submitter, path=None):
    if path == None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'schemas')

    put_cgci_blgsp(client, submitter)

    entities = os.listdir(path)
    entities = [entity for entity in entities if (not entity.startswith('_') and entity.endswith('.yaml') and entity != 'program.yaml' and entity != 'project.yaml' and entity != 'metaschema.yaml')]
    yamls = [yaml.load(open(os.path.join(path, entity)).read()) for entity in entities]
    search_q = deque(['projects'])
    request_q = deque(['projects'])

    def check_all_parents_in_request_q(links):
        for link in links:
            if 'name' in link:
                if link['name'] not in request_q:
                    return False
            if 'subgroup' in link:
                for subgroup in link['subgroup']:
                    if subgroup['name'] not in request_q:
                        return False
        return True

    while len(search_q) != 0:
        parent = search_q.popleft()
        for i in range(len(yamls)):
            for j in range(len(yamls[i]['links'])):
                if 'name' in yamls[i]['links'][j] and yamls[i]['links'][j]['name'] == parent and yamls[i]['links'][j]['backref'] not in request_q and check_all_parents_in_request_q(yamls[i]['links']):
                    #and yamls[i]['links'][j]['required']
                    search_q.append(yamls[i]['links'][j]['backref'])
                    request_q.append(yamls[i]['links'][j]['backref'])
                    #del yamls[i]
                if 'subgroup' in yamls[i]['links'][j]:
                    for subgroup in yamls[i]['links'][j]['subgroup']:
                        if subgroup['name'] == parent and subgroup['name'] not in request_q and check_all_parents_in_request_q(yamls[i]['links']):
                            search_q.append(subgroup['backref'])
                            request_q.append(subgroup['backref'])
                            #del yamls[i]

    request_q.remove('projects')
    print "request_q", request_q

    real_request_q = deque([])

    # map plural to singular
    for plural in request_q:
        for schema in yamls:
            if 'subgroup' in schema['links'][0]:
                if schema['links'][0]['subgroup'][0]['backref'] == plural:
                    real_request_q.append(schema['id'])
                    break
            elif 'backref' in schema['links'][0]:
                if schema['links'][0]['backref'] == plural:
                    real_request_q.append(schema['id'])
                    break

    for entity in real_request_q:
        put_entity_from_file(client, entity+".json", submitter)

#def test_submission(app, monkeypatch):
    #print "In test_submission!"
#
    #test_client = app.test_client()
#
    ## Submit program
    #program = open('gdcdictionary/examples/valid/program.json', 'r').read()
    #rv = test_client.post('/v0/submission', data=program)
    #prog_name = json.loads(rv.data)['name']
    #assert rv._status_code == 200
    #
    ## Submit project
    #project = open('gdcdictionary/examples/valid/project.json', 'r').read()
    #rv = test_client.post('/v0/submission/' + prog_name, data=project)
    #assert rv._status_code == 200
    #print "PROJECT RETURN", rv.data
    #print "type(PROJECT RETURN)", type(rv.data)
    #print "json.loads(PROJECT RETURN)", json.loads(rv.data)
    #proj_name = json.loads(rv.data)['entities'][0]['unique_keys'][0]['code']
    #print proj_name
#
    ## Submit acknowledgement
    #acknowledgement = open('gdcdictionary/examples/valid/acknowledgement.json', 'r').read()
    #rv = test_client.post('/v0/submission/' + prog_name + '/' + proj_name, data=acknowledgement)
    #print '/v0/submission/' + prog_name + '/' + proj_name
    #print rv.data
    #assert rv._status_code == 200
    #assert 0

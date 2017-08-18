from gdcdictionary import gdcdictionary
import json
from mock import patch
import os
from gdcdatamodel import models as md
import boto
from flask import g
from collections import deque
import yaml

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'examples', 'valid')

BLGSP_PATH = '/v0/submission/CGCI/BLGSP/'

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
                    search_q.append(yamls[i]['links'][j]['backref'])
                    request_q.append(yamls[i]['links'][j]['backref'])
                if 'subgroup' in yamls[i]['links'][j]:
                    for subgroup in yamls[i]['links'][j]['subgroup']:
                        if subgroup['name'] == parent and subgroup['name'] not in request_q and check_all_parents_in_request_q(yamls[i]['links']):
                            search_q.append(subgroup['backref'])
                            request_q.append(subgroup['backref'])

    request_q.remove('projects')

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

def test_put_entity_creation_invalid(client, pg_driver, submitter, path=None):
    if path == None:
        path = os.path.join(os.path.dirname(DATA_DIR), 'invalid')
    put_cgci_blgsp(client, submitter)
    invalid_jsons = os.listdir(path)
    for invalid in invalid_jsons:
        with open(os.path.join(path, invalid), 'r') as f:
            entity = f.read()
        print "entity", entity
        r = client.put(BLGSP_PATH, headers=submitter(BLGSP_PATH, 'put'), data=entity)
        print r.status_code
        assert 500 > r.status_code >= 400

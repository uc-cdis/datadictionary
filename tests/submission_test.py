from cdisutilstest.code.dictionary_submission import *
import os

program = 'CGCI'
project = 'BLGSP'

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'examples', 'valid')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'schemas')
INVALID_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gdcdictionary', 'examples', 'invalid')

def test_program_creation_endpoint(client, pg_driver, submitter, program=program, data_dir=DATA_DIR):
    program_creation_endpoint_helper(client, pg_driver, submitter, program, data_dir)

def test_project_creation_endpoint(client, pg_driver, submitter, program=program, project=project, data_dir=DATA_DIR):
    project_creation_endpoint_helper(client, pg_driver, submitter, program, project, data_dir)

def test_put_entity_creation_valid(client, pg_driver, submitter, program=program, project=project, data_dir=DATA_DIR, schema_path=SCHEMA_PATH):
    put_entity_creation_valid_helper(client, pg_driver, submitter, program, project, data_dir, schema_path)

def test_put_entity_creation_invalid(client, pg_driver, submitter, program=program, project=project, data_dir=DATA_DIR, invalid_data_dir=INVALID_DATA_DIR):
    put_entity_creation_invalid_helper(client, pg_driver, submitter, program, project, data_dir, invalid_data_dir)

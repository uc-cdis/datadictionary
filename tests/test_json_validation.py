"""This is an example of json schema for the GDC using schemas defined
in local yaml files (see gdcdictionary/examples).

This test class is making sure the example jsons comply with the schema.

Note this is NOT testing that the schema is sane. Just that we adhere
to it

"""

import json
import glob
import os

from jsonschema import ValidationError

from tests.utils import BaseTest, DATA_DIR, validate_entity

def get_all_paths(subdir):
    for path in sorted(glob.glob(os.path.join(DATA_DIR, subdir, '*.json'))):
        yield path


class ExamplesTest(BaseTest):

    def test_valid_examples(self):
        for path in get_all_paths('valid'):
            print(f"Valid path {path}")
            with open(path, 'r') as f:
                doc = json.load(f)
                if type(doc) == dict:
                    validate_entity(doc, self.dictionary.schema)
                elif type(doc) == list:
                    for entity in doc:
                        validate_entity(entity, self.dictionary.schema)
                else:
                    raise Exception("Invalid json")


    def test_invalid_examples(self):
        for path in get_all_paths('invalid'):
            with open(path, 'r') as f:
                doc = json.load(f)
                if type(doc) == dict:
                    with self.assertRaises(ValidationError):
                        validate_entity(doc, self.dictionary.schema)
                elif type(doc) == list:
                    for entity in doc:
                        with self.assertRaises(ValidationError):
                            validate_entity(entity, self.dictionary.schema)
                else:
                    raise Exception("Invalid json")

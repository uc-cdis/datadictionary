"""
This is an example of validating json dictionaries (e.g., gdcdictionary/examples)
against the schemas in the local yaml files.

Example usage:
python example_validation.py gdcdictionary/examples/valid/*json
"""

from jsonschema import ValidationError
import argparse
import json

from gdcdictionary import gdcdictionary
from tests.utils import validate_entity

if __name__ == '__main__':

    ####################
    # Setup
    ####################


    parser = argparse.ArgumentParser(description='Validate JSON')
    parser.add_argument('jsonfiles', metavar='file',
                        type=argparse.FileType('r'), nargs='+',
                        help='json files to test if (in)valid')

    parser.add_argument('--invalid', action='store_true', default=False,
                        help='expect the files to be invalid instead of valid')

    args = parser.parse_args()

    ####################
    # Example validation
    ####################

    # Load schemata
    dictionary = gdcdictionary

    for f in args.jsonfiles:
        doc = json.load(f)
        if args.invalid:
            try:
                print("CHECK if {0} is invalid:".format(f.name), end=" ")
                print(type(doc))
                if type(doc) == dict:
                    validate_entity(doc, dictionary.schema)
                elif type(doc) == list:
                    for entity in doc:
                        validate_entity(entity, dictionary.schema)
                else:
                    raise ValidationError("Invalid json")
            except ValidationError as e:
                print("Invalid as expected.")
                pass
            else:
                raise Exception("Expected invalid, but validated.")
        else:
            print("CHECK if {0} is valid:".format(f.name), end=" ")
            if type(doc) == dict:
                validate_entity(doc, dictionary.schema)
            elif type(doc) == list:
                for entity in doc:
                    validate_entity(entity, dictionary.schema)
            else:
                print("Invalid json")

            print("Valid as expected")

    print('ok.')

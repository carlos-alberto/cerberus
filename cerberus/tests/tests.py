# -*- coding: utf-8 -*-

import re
from datetime import datetime
from random import choice
from string import ascii_lowercase
from tempfile import NamedTemporaryFile
from . import TestBase
from ..cerberus import errors, SchemaError, Validator


ValidationError = errors.ValidationError


class TestTestBase(TestBase):
    def _test_that_test_fails(self, test, *args):
        try:
            test(*args)
        except AssertionError as e:  # noqa
            pass
        else:
            raise AssertionError("test didn't fail")

    def test_fail(self):
        self._test_that_test_fails(self.assertFail, {'an_integer': 60})

    def test_success(self):
        self._test_that_test_fails(self.assertSuccess, {'an_integer': 110})


class TestValidation(TestBase):
    def test_empty_schema(self):
        v = Validator()
        self.assertSchemaError(self.document, None, v,
                               errors.SCHEMA_ERROR_MISSING)

    def test_bad_schema_type(self):
        schema = "this string should really be dict"
        try:
            Validator(schema)
        except SchemaError as e:
            self.assertEqual(str(e),
                             errors.SCHEMA_ERROR_DEFINITION_TYPE
                             .format(schema))
        else:
            self.fail('SchemaError not raised')

        v = Validator()
        self.assertSchemaError(self.document, schema, v,
                               errors.SCHEMA_ERROR_DEFINITION_TYPE
                               .format(schema))

    def test_bad_schema_type_field(self):
        field = 'foo'
        schema = {field: {'schema': {'bar': {'type': 'string'}}}}
        self.assertSchemaError(self.document, schema, None,
                               errors.SCHEMA_ERROR_TYPE_TYPE.format(field))

        schema = {field: {'type': 'integer',
                          'schema': {'bar': {'type': 'string'}}}}
        self.assertSchemaError(self.document, schema, None,
                               errors.SCHEMA_ERROR_TYPE_TYPE.format(field))

    def _check_schema_content_error(self, err_msg, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except SchemaError as e:
            self.assertIn(err_msg, str(e))
        else:
            self.fail('SchemaError not raised')

    def test_invalid_schema(self):
        schema = {'foo': {'unknown': 'rule'}}
        err_msg = ' '.join(errors.SCHEMA_ERROR_UNKNOWN_RULE.split()[:2])
        self._check_schema_content_error(err_msg, Validator, schema)
        v = Validator()
        self._check_schema_content_error(
            err_msg, v.validate, {}, schema=schema)

    def test_empty_document(self):
        self.assertValidationError(None, None, None,
                                   errors.DOCUMENT_MISSING)

    def test_bad_document_type(self):
        document = "not a dict"
        self.assertValidationError(
            document, None, None, errors.DOCUMENT_FORMAT.format(
                document)
        )

    def test_bad_schema_definition(self):
        field = 'name'
        schema = {field: 'this should really be a dict'}
        self.assertSchemaError(self.document, schema, None,
                               errors.SCHEMA_ERROR_CONSTRAINT_TYPE
                               .format(field))

    def test_unknown_field(self):
        field = 'surname'
        self.assertFail({field: 'doe'})
        self.assertError(field, (), errors.UNKNOWN_FIELD, None)
        self.assertDictEqual(self.validator.errors, {field: 'unknown field'})

    def test_unknown_rule(self):
        field = 'name'
        schema = {field: {'unknown_rule': True, 'type': 'string'}}
        self.assertSchemaError(
            self.document, schema, None,
            errors.SCHEMA_ERROR_UNKNOWN_RULE.format('unknown_rule', field))

    def test_empty_field_definition(self):
        field = 'name'
        schema = {field: {}}
        self.assertSuccess(self.document, schema)

    def test_required_field(self):
        field = 'a_required_string'
        self.schema.update(self.required_string_extension)
        self.assertFail({'an_integer': 1}, self.schema)
        self.assertError(field, (field, 'required'), errors.REQUIRED_FIELD,
                         True)

    def test_nullable_field(self):
        self.assertSuccess({'a_nullable_integer': None})
        self.assertSuccess({'a_nullable_integer': 3})
        self.assertSuccess({'a_nullable_field_without_type': None})
        self.assertFail({'a_nullable_integer': "foo"})
        self.assertFail({'an_integer': None})
        self.assertFail({'a_not_nullable_field_without_type': None})

    def test_readonly_field(self):
        field = 'a_readonly_string'
        self.assertFail({field: 'update me if you can'})
        self.assertError(field, (field, 'readonly'), errors.READONLY_FIELD,
                         True)

    def test_readonly_field_first_rule(self):
        # test that readonly rule is checked before any other rule, and blocks.
        # See #63.
        schema = {
            'a_readonly_number': {
                'type': 'integer',
                'readonly': True,
                'max': 1
            }
        }
        v = Validator(schema)
        v.validate({'a_readonly_number': 2})
        # it would be a list if there's more than one error; we get a dict
        # instead.
        self.assertIn('read-only', v.errors['a_readonly_number'])

    def test_unknown_data_type(self):
        field = 'name'
        value = 'catch_me'
        schema = {field: {'type': value}}
        self.assertSchemaError(self.document, schema, None,
                               errors.SCHEMA_ERROR_UNKNOWN_TYPE, value)

    def test_not_a_string(self):
        self.assertBadType('a_string', 'string', 1)

    def test_not_a_integer(self):
        self.assertBadType('an_integer', 'integer', "i'm not an integer")

    def test_not_a_boolean(self):
        self.assertBadType('a_boolean', 'boolean', "i'm not a boolean")

    def test_not_a_datetime(self):
        self.assertBadType('a_datetime', 'datetime', "i'm not a datetime")

    def test_not_a_float(self):
        self.assertBadType('a_float', 'float', "i'm not a float")

    def test_not_a_number(self):
        self.assertBadType('a_number', 'number', "i'm not a number")

    def test_not_a_list(self):
        self.assertBadType('a_list_of_values', 'list', "i'm not a list")

    def test_not_a_dict(self):
        self.assertBadType('a_dict', 'dict', "i'm not a dict")

    def test_bad_max_length(self):
        field = 'a_string'
        max_length = self.schema[field]['maxlength']
        value = "".join(choice(ascii_lowercase) for i in range(max_length + 1))
        self.assertFail({field: value})
        self.assertError(field, (field, 'maxlength'), errors.MAX_LENGTH,
                         max_length)

    def test_bad_min_length(self):
        field = 'a_string'
        min_length = self.schema[field]['minlength']
        value = "".join(choice(ascii_lowercase) for i in range(min_length - 1))
        self.assertFail({field: value})
        self.assertError(field, (field, 'minlength'), errors.MIN_LENGTH,
                         min_length)

    def test_bad_max_value(self):
        def assert_bad_max_value(field, inc):
            max_value = self.schema[field]['max']
            value = max_value + inc
            self.assertFail({field: value})
            self.assertError(field, (field, 'max'), errors.MAX_VALUE, max_value)

        field = 'an_integer'
        assert_bad_max_value(field, 1)
        field = 'a_float'
        assert_bad_max_value(field, 1.0)
        field = 'a_number'
        assert_bad_max_value(field, 1)

    def test_bad_min_value(self):
        def assert_bad_min_value(field, inc):
            min_value = self.schema[field]['min']
            value = min_value - inc
            self.assertFail({field: value})
            self.assertError(field, (field, 'min'), errors.MIN_VALUE, min_value)

        field = 'an_integer'
        assert_bad_min_value(field, 1)
        field = 'a_float'
        assert_bad_min_value(field, 1.0)
        field = 'a_number'
        assert_bad_min_value(field, 1)

    def test_bad_schema(self):
        field = 'a_dict'
        schema_field = 'address'
        value = {schema_field: 34}
        self.assertFail({field: value})
        self.assertError((field, schema_field),
                         (field, 'schema', schema_field, 'type'),
                         errors.BAD_TYPE, 'string')

        v = self.validator
        handler = errors.BasicErrorHandler
        self.assertIn(field, v.errors)
        self.assertIn(schema_field, v.errors[field])
        self.assertIn(handler.messages[errors.BAD_TYPE.code]
                      .format(constraint='string'),
                      v.errors[field][schema_field])
        self.assertIn('city', v.errors[field])
        self.assertIn(handler.messages[errors.REQUIRED_FIELD.code],
                      v.errors[field]['city'])

    def test_bad_valueschema(self):
        field = 'a_dict_with_valueschema'
        schema_field = 'a_string'
        value = {schema_field: 'not an integer'}
        self.assertFail({field: value})

        exp_child_errors = [((field, schema_field), (field, 'valueschema',
                             'type'), errors.BAD_TYPE, 'integer')]
        self.assertChildErrors(field, (field, 'valueschema'), errors.VALUESCHEMA,  # noqa
                               {'type': 'integer'}, child_errors=exp_child_errors)  # noqa

    def test_bad_list_of_values(self):
        field = 'a_list_of_values'
        value = ['a string', 'not an integer']
        self.assertFail({field: value})
        self.assertChildErrors(field, (field, 'items'), errors.BAD_ITEMS,
                               [{'type': 'string'}, {'type': 'integer'}],
                               child_errors=[
                                   ((field, 1), (field, 'items', 1, 'type'),
                                    errors.BAD_TYPE, 'integer')])
        self.assertIn(errors.BasicErrorHandler.messages[errors.BAD_TYPE.code].
                      format(constraint='integer'),
                      self.validator.errors[field][1])

        value = ['a string', 10, 'an extra item']
        self.assertFail({field: value})
        self.assertError(field, (field, 'items'), errors.ITEMS_LENGTH,
                         [{'type': 'string'}, {'type': 'integer'}], (2, 3))

    def test_bad_list_of_integers(self):
        field = 'a_list_of_integers'
        value = [34, 'not an integer']
        self.assertFail({field: value})

    def test_bad_list_of_dicts_deprecated(self):
        field = 'a_list_of_dicts_deprecated'
        value = [{'sku': 'KT123', 'price': '100'}]
        self.assertFail({field: value})
        # this is not a proper expectation, it's a deprecated feature
        self.assertError('price', ('price', 'type'), errors.BAD_TYPE, 'integer')

        value = ["not a dict"]
        self.assertValidationError(
            {field: value}, None, None, errors.DOCUMENT_FORMAT.format(
                value[0])
        )

    def test_bad_list_of_dicts(self):
        field = 'a_list_of_dicts'
        value = [{'sku': 'KT123', 'price': '100'}]
        self.assertFail({field: value})
        exp_child_errors = [((field, 0, 'price'),
                            (field, 'schema', 'schema', 'price', 'type'),
                            errors.BAD_TYPE, 'integer')]
        self.assertChildErrors(field, (field, 'schema'), errors.SEQUENCE_SCHEMA,
                               {'type': 'dict',
                                'schema': {'sku': {'type': 'string'},
                                           'price': {'type': 'integer'}}},
                               child_errors=exp_child_errors)

        v = self.validator
        self.assertIn(field, v.errors)
        self.assertIn(0, v.errors[field])
        self.assertIn('price', v.errors[field][0])
        exp_msg = errors.BasicErrorHandler.messages[errors.BAD_TYPE.code]\
            .format(constraint='integer')
        self.assertIn(exp_msg, v.errors[field][0]['price'])

        value = ["not a dict"]
        self.assertValidationError(
            {field: value}, None, None, errors.DOCUMENT_FORMAT.format(
                value[0])
        )

    def test_array_unallowed(self):
        field = 'an_array'
        value = ['agent', 'client', 'profit']
        self.assertFail({field: value})
        self.assertError(field, (field, 'allowed'), errors.UNALLOWED_VALUES,
                         ['agent', 'client', 'vendor'], ['profit'])

    def test_string_unallowed(self):
        field = 'a_restricted_string'
        value = 'profit'
        self.assertFail({field: value})
        self.assertError(field, (field, 'allowed'), errors.UNALLOWED_VALUE,
                         ['agent', 'client', 'vendor'], value)

    def test_integer_unallowed(self):
        field = 'a_restricted_integer'
        value = 2
        self.assertFail({field: value})
        self.assertError(field, (field, 'allowed'), errors.UNALLOWED_VALUE,
                         [-1, 0, 1], value)

    def test_integer_allowed(self):
        self.assertSuccess({'a_restricted_integer': -1})

    def test_validate_update(self):
        self.assertSuccess({'an_integer': 100, 'a_dict': {'address': 'adr'}},
                           update=True)

    def test_string(self):
        self.assertSuccess({'a_string': 'john doe'})

    def test_string_allowed(self):
        self.assertSuccess({'a_restricted_string': 'client'})

    def test_integer(self):
        self.assertSuccess({'an_integer': 50})

    def test_boolean(self):
        self.assertSuccess({'a_boolean': True})

    def test_datetime(self):
        self.assertSuccess({'a_datetime': datetime.now()})

    def test_float(self):
        self.assertSuccess({'a_float': 3.5})
        self.assertSuccess({'a_float': 1})

    def test_number(self):
        self.assertSuccess({'a_number': 3.5})
        self.assertSuccess({'a_number': 3})

    def test_array(self):
        self.assertSuccess({'an_array': ['agent', 'client']})

    def test_set(self):
        self.assertSuccess({'a_set': set(['hello', 1])})

    def test_one_of_two_types(self):
        field = 'one_or_more_strings'
        self.assertSuccess({field: 'foo'})
        self.assertSuccess({field: ['foo', 'bar']})
        self.assertFail({field: 23})
        self.assertError((field,), (field, 'type'), errors.BAD_TYPE,
                         ['string', 'list'])
        self.assertFail({field: ['foo', 23]})
        exp_child_errors = [((field, 1), (field, 'schema', 'type'),
                             errors.BAD_TYPE, 'string')]
        self.assertChildErrors(field, (field, 'schema'), errors.SEQUENCE_SCHEMA,
                               {'type': 'string'},
                               child_errors=exp_child_errors)
        self.assertDictEqual(self.validator.errors,
                             {field: {1: 'must be of string type'}})

    def test_regex(self):
        field = 'a_regex_email'
        self.assertSuccess({field: 'valid.email@gmail.com'})
        self.assertFail({field: 'invalid'}, self.schema, update=True)
        self.assertError(field, (field, 'regex'), errors.REGEX_MISMATCH,
                         '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

    # TODO remove on next major release
    def test_a_list_of_dicts_deprecated(self):
        self.assertSuccess(
            {
                'a_list_of_dicts_deprecated': [
                    {'sku': 'AK345', 'price': 100},
                    {'sku': 'YZ069', 'price': 25}
                ]
            }
        )

    def test_a_list_of_dicts(self):
        self.assertSuccess(
            {
                'a_list_of_dicts': [
                    {'sku': 'AK345', 'price': 100},
                    {'sku': 'YZ069', 'price': 25}
                ]
            }
        )

    def test_a_list_of_values(self):
        self.assertSuccess({'a_list_of_values': ['hello', 100]})

    def test_a_list_of_integers(self):
        self.assertSuccess({'a_list_of_integers': [99, 100]})

    def test_a_dict(self):
        self.assertSuccess({'a_dict': {'address': 'i live here',
                                       'city': 'in my own town'}})
        self.assertFail({'a_dict': {'address': 8545}})
        self.assertErrors([
            (('a_dict', 'address'), ('a_dict', 'schema', 'address', 'type'),
             errors.BAD_TYPE, 'string'),
            (('a_dict', 'city'), ('a_dict', 'schema', 'city', 'required'),
             errors.REQUIRED_FIELD, True)
            ])

    def test_a_dict_with_valueschema(self):
        self.assertSuccess(
            {'a_dict_with_valueschema':
                {'an integer': 99, 'another integer': 100}})

        self.assertFail({'a_dict_with_valueschema': {'a string': '99'}})
        self.assertChildErrors(
            'a_dict_with_valueschema',
            ('a_dict_with_valueschema', 'valueschema'),
            errors.VALUESCHEMA, {'type': 'integer'}, child_errors=[
                (('a_dict_with_valueschema', 'a string'),
                 ('a_dict_with_valueschema', 'valueschema', 'type'),
                 errors.BAD_TYPE, 'integer')])
        self.assertIn('valueschema', self.validator.schema_error_tree
                      ['a_dict_with_valueschema'])
        self.assertEqual(len(self.validator.schema_error_tree
                             ['a_dict_with_valueschema']['valueschema']
                             .descendants), 1)

    def test_a_dict_with_propertyschema(self):
        self.assertSuccess(
            {
                'a_dict_with_propertyschema': {
                    'key': 'value'
                }
            }
        )

        self.assertFail(
            {
                'a_dict_with_propertyschema': {
                    'KEY': 'value'
                }
            }
        )

    def test_a_list_length(self):
        field = 'a_list_length'
        min_length = self.schema[field]['minlength']
        max_length = self.schema[field]['maxlength']

        self.assertFail({field: [1] * (min_length - 1)})
        self.assertError(field, (field, 'minlength'), errors.MIN_LENGTH,
                         min_length)

        for i in range(min_length, max_length):
            value = [1] * i
            self.assertSuccess({field: value})

        self.assertFail({field: [1] * (max_length + 1)})
        self.assertError(field, (field, 'maxlength'), errors.MAX_LENGTH,
                         max_length)

    def test_custom_datatype(self):
        class MyValidator(Validator):
            def _validate_type_objectid(self, field, value):
                if not re.match('[a-f0-9]{24}', value):
                    self._error(field, 'Not an ObjectId')

        schema = {'test_field': {'type': 'objectid'}}
        v = MyValidator(schema)
        self.assertSuccess({'test_field': '50ad188438345b1049c88a28'},
                           validator=v)
        self.assertFail({'test_field': 'hello'}, validator=v)
        self.assertError('test_field', ('test_field', 'type'), errors.BAD_TYPE,
                         'objectid', v_errors=v._errors)

    def test_custom_datatype_rule(self):
        class MyValidator(Validator):
            def _validate_min_number(self, min_number, field, value):
                if value < min_number:
                    self._error(field, 'Below the min')

            def _validate_type_number(self, field, value):
                if not isinstance(value, int):
                    self._error(field, 'Not a number')

        schema = {'test_field': {'min_number': 1, 'type': 'number'}}
        v = MyValidator(schema)
        self.assertFail({'test_field': '0'}, validator=v)
        self.assertError('test_field', ('test_field', 'type'), errors.BAD_TYPE,
                         'number', v_errors=v._errors)
        self.assertFail({'test_field': 0}, validator=v)
        self.assertError('test_field', (), errors.CUSTOM, None,
                         ('Below the min',), v_errors=v._errors)
        self.assertDictEqual(v.errors, {'test_field': 'Below the min'})

    def test_custom_validator(self):
        class MyValidator(Validator):
            def _validate_isodd(self, isodd, field, value):
                if isodd and not bool(value & 1):
                    self._error(field, 'Not an odd number')

        schema = {'test_field': {'isodd': True}}
        v = MyValidator(schema)
        self.assertSuccess({'test_field': 7}, validator=v)
        self.assertFail({'test_field': 6}, validator=v)
        self.assertError('test_field', (), errors.CUSTOM, None,
                         ('Not an odd number',), v_errors=v._errors)
        self.assertDictEqual(v.errors, {'test_field': 'Not an odd number'})

    def test_transparent_schema_rules(self):
        field = 'test'
        schema = {field: {'type': 'string', 'unknown_rule': 'a value'}}
        document = {field: 'hey!'}
        v = Validator(transparent_schema_rules=True)
        self.assertSuccess(schema=schema, document=document, validator=v)
        v.transparent_schema_rules = False
        self.assertSchemaError(
            document, schema, v,
            errors.SCHEMA_ERROR_UNKNOWN_RULE.format('unknown_rule', field)
        )
        self.assertSchemaError(
            document, schema, None,
            errors.SCHEMA_ERROR_UNKNOWN_RULE.format('unknown_rule', field)
        )

    def test_allow_empty_strings(self):
        field = 'test'
        schema = {field: {'type': 'string'}}
        document = {field: ''}
        self.assertSuccess(document, schema)
        schema[field]['empty'] = False
        self.assertFail(document, schema)
        self.assertError(field, (field, 'empty'), errors.EMPTY_NOT_ALLOWED,
                         False)
        schema[field]['empty'] = True
        self.assertSuccess(document, schema)

    def test_ignore_none_values(self):
        field = 'test'
        schema = {field: {'type': 'string', 'empty': False, 'required': False}}
        document = {field: None}

        # Test normal behaviour
        v = Validator(schema, ignore_none_values=False)
        self.assertFail(schema=schema, document=document, validator=v)
        schema[field]['required'] = True
        self.assertFail(schema=schema, document=document, validator=v)
        self.assertNoError(field, (field, 'required'), errors.REQUIRED_FIELD,
                           True, v_errors=v._errors)

        # Test ignore None behaviour
        v = Validator(schema, ignore_none_values=True)
        schema[field]['required'] = False
        self.assertSuccess(schema=schema, document=document, validator=v)
        schema[field]['required'] = True
        self.assertFail(schema=schema, document=document, validator=v)
        self.assertError(field, (field, 'required'), errors.REQUIRED_FIELD,
                         True, v_errors=v._errors)
        self.assertNoError(field, (field, 'type'), errors.BAD_TYPE, 'string',
                           v_errors=v._errors)

    def test_unknown_keys(self):
        schema = {}

        # test that unknown fields are allowed when allow_unknown is True.
        v = Validator(allow_unknown=True, schema=schema)
        self.assertSuccess({"unknown1": True, "unknown2": "yes"}, validator=v)

        # test that unknown fields are allowed only if they meet the
        # allow_unknown schema when provided.
        v.allow_unknown = {'type': 'string'}
        self.assertSuccess(document={'name': 'mark'}, validator=v)
        self.assertFail({"name": 1}, validator=v)

        # test that unknown fields are not allowed if allow_unknown is False
        v.allow_unknown = False
        self.assertFail({'name': 'mark'}, validator=v)

    def test_unknown_keys_list_of_dicts(self):
        # test that allow_unknown is honored even for subdicts in lists.
        # See 67.
        self.validator.allow_unknown = True
        document = {'a_list_of_dicts': [{'sku': 'YZ069', 'price': 25,
                                         'extra': True}]}

        self.assertSuccess(document)

    def test_unknown_keys_retain_custom_rules(self):
        # test that allow_unknown schema respect custom validation rules.
        # See #66.
        class CustomValidator(Validator):
            def _validate_type_foo(self, field, value):
                if not value == "foo":
                    self.error(field, "Expected a foo")

        v = CustomValidator({})
        v.allow_unknown = {"type": "foo"}
        self.assertSuccess(document={"fred": "foo", "barney": "foo"},
                           validator=v)

    def test_nested_unknown_keys(self):
        schema = {
            'field1': {
                'type': 'dict',
                'allow_unknown': True,
                'schema': {'nested1': {'type': 'string'}}
            }
        }
        document = {
            'field1': {
                'nested1': 'foo',
                'arb1': 'bar',
                'arb2': 42
            }
        }
        self.assertSuccess(document=document, schema=schema)

        schema['field1']['allow_unknown'] = {'type': 'string'}
        self.assertFail(document=document, schema=schema)

    def test_novalidate_noerrors(self):
        """
        In v0.1.0 and below `self.errors` raised an exception if no
        validation had been performed yet.
        """
        self.assertEqual(self.validator.errors, {})

    def test_callable_validator(self):
        """
        Validator instance is callable, functions as a shorthand
        passthrough to validate()
        """
        schema = {'test_field': {'type': 'string'}}
        v = Validator(schema)
        self.assertTrue(v.validate({'test_field': 'foo'}))
        self.assertTrue(v({'test_field': 'foo'}))
        self.assertFalse(v.validate({'test_field': 1}))
        self.assertFalse(v({'test_field': 1}))

    def test_dependencies_field(self):
        schema = {'test_field': {'dependencies': 'foo'},
                  'foo': {'type': 'string'}}
        self.assertSuccess({'test_field': 'foobar', 'foo': 'bar'}, schema)
        self.assertFail({'test_field': 'foobar'}, schema)

    def test_dependencies_list(self):
        schema = {
            'test_field': {'dependencies': ['foo', 'bar']},
            'foo': {'type': 'string'},
            'bar': {'type': 'string'}
        }
        self.assertSuccess({'test_field': 'foobar', 'foo': 'bar', 'bar': 'foo'},  # noqa
                           schema)
        self.assertFail({'test_field': 'foobar', 'foo': 'bar'}, schema)

    def test_dependencies_list_with_required_field(self):
        schema = {
            'test_field': {'required': True, 'dependencies': ['foo', 'bar']},
            'foo': {'type': 'string'},
            'bar': {'type': 'string'}
        }
        # False: all dependencies missing
        self.assertFail({'test_field': 'foobar'}, schema)
        # False: one of dependencies missing
        self.assertFail({'test_field': 'foobar', 'foo': 'bar'}, schema)
        # False: one of dependencies missing
        self.assertFail({'test_field': 'foobar', 'bar': 'foo'}, schema)
        # False: dependencies are validated and field is required
        self.assertFail({'foo': 'bar', 'bar': 'foo'}, schema)
        # Flase: All dependencies are optional but field is still required
        self.assertFail({}, schema)
        # True: dependency missing
        self.assertFail({'foo': 'bar'}, schema)
        # True: dependencies are validated but field is not required
        schema['test_field']['required'] = False
        self.assertSuccess({'foo': 'bar', 'bar': 'foo'}, schema)

    def test_dependencies_list_with_subodcuments_fields(self):
        schema = {
            'test_field': {'dependencies': ['a_dict.foo', 'a_dict.bar']},
            'a_dict': {
                'type': 'dict',
                'schema': {
                    'foo': {'type': 'string'},
                    'bar': {'type': 'string'}
                }
            }
        }
        self.assertSuccess({'test_field': 'foobar',
                            'a_dict': {'foo': 'foo', 'bar': 'bar'}}, schema)
        self.assertFail({'test_field': 'foobar', 'a_dict': {}}, schema)
        self.assertFail({'test_field': 'foobar',
                         'a_dict': {'foo': 'foo'}}, schema)

    def test_dependencies_dict(self):
        schema = {
            'test_field': {'dependencies': {'foo': 'foo', 'bar': 'bar'}},
            'foo': {'type': 'string'},
            'bar': {'type': 'string'}
        }
        self.assertSuccess({'test_field': 'foobar', 'foo': 'foo', 'bar': 'bar'},  # noqa
                           schema)
        self.assertFail({'test_field': 'foobar', 'foo': 'foo'}, schema)
        self.assertFail({'test_field': 'foobar', 'foo': 'bar'}, schema)
        self.assertFail({'test_field': 'foobar', 'bar': 'bar'}, schema)
        self.assertFail({'test_field': 'foobar', 'bar': 'foo'}, schema)
        self.assertFail({'test_field': 'foobar'}, schema)

    def test_dependencies_dict_with_required_field(self):
        schema = {
            'test_field': {
                'required': True,
                'dependencies': {'foo': 'foo', 'bar': 'bar'}
            },
            'foo': {'type': 'string'},
            'bar': {'type': 'string'}
        }
        # False: all dependencies missing
        self.assertFail({'test_field': 'foobar'}, schema)
        # False: one of dependencies missing
        self.assertFail({'test_field': 'foobar', 'foo': 'foo'}, schema)
        self.assertFail({'test_field': 'foobar', 'bar': 'bar'}, schema)
        # False: dependencies are validated and field is required
        self.assertFail({'foo': 'foo', 'bar': 'bar'}, schema)
        # False: All dependencies are optional, but field is still required
        self.assertFail({}, schema)
        # False: dependency missing
        self.assertFail({'foo': 'bar'}, schema)

        self.assertSuccess({'test_field': 'foobar', 'foo': 'foo', 'bar': 'bar'},  # noqa
                           schema)

        # True: dependencies are validated but field is not required
        schema['test_field']['required'] = False
        self.assertSuccess({'foo': 'bar', 'bar': 'foo'}, schema)

    def test_dependencies_dict_with_subodcuments_fields(self):
        schema = {
            'test_field': {'dependencies': {'a_dict.foo': ['foo', 'bar'],
                                            'a_dict.bar': 'bar'}},
            'a_dict': {
                'type': 'dict',
                'schema': {
                    'foo': {'type': 'string'},
                    'bar': {'type': 'string'}
                }
            }
        }
        self.assertSuccess({'test_field': 'foobar',
                            'a_dict': {'foo': 'foo', 'bar': 'bar'}}, schema)
        self.assertSuccess({'test_field': 'foobar',
                            'a_dict': {'foo': 'bar', 'bar': 'bar'}}, schema)
        self.assertFail({'test_field': 'foobar', 'a_dict': {}}, schema)
        self.assertFail({'test_field': 'foobar',
                         'a_dict': {'foo': 'foo', 'bar': 'foo'}}, schema)
        self.assertFail({'test_field': 'foobar', 'a_dict': {'bar': 'foo'}},
                        schema)
        self.assertFail({'test_field': 'foobar', 'a_dict': {'bar': 'bar'}},
                        schema)

    def test_dependencies_errors(self):
        v = Validator({'field1': {'required': False},
                       'field2': {'required': True,
                                  'dependencies': {'field1': ['one', 'two']}}})
        v.validate({'field1': 'three', 'field2': 7})
        self.assertError('field2', ('field2', 'dependencies'),
                         errors.DEPENDENCIES_FIELD_VALUE,
                         {'field1': ['one', 'two']}, ({'field1': 'three'}, ),
                         v_errors=v._errors)

    def test_options_passed_to_nested_validators(self):
        schema = {'sub_dict': {'type': 'dict',
                               'schema': {'foo': {'type': 'string'}}}}
        v = Validator(schema, allow_unknown=True)
        self.assertSuccess({'sub_dict': {'foo': 'bar', 'unknown': True}},
                           validator=v)

    def test_self_document_always_root(self):
        """ Make sure self.document is always the root document.
        See:
        * https://github.com/nicolaiarocci/cerberus/pull/42
        * https://github.com/nicolaiarocci/eve/issues/295
        """
        class MyValidator(Validator):
            def _validate_root_doc(self, root_doc, field, value):
                if('sub' not in self.root_document or
                        len(self.root_document['sub']) != 2):
                    self._error(field, 'self.context is not the root doc!')

        schema = {
            'sub': {
                'type': 'list',
                'root_doc': True,
                'schema': {
                    'type': 'dict',
                    'schema': {
                        'foo': {
                            'type': 'string',
                            'root_doc': True
                        }
                    }
                }
            }
        }
        self.assertSuccess({'sub': [{'foo': 'bar'}, {'foo': 'baz'}]},
                           validator=MyValidator(schema))

    def test_validator_rule(self):
        def validate_name(field, value, error):
            if not value.islower():
                error(field, 'must be lowercase')

        schema = {
            'name': {'validator': validate_name},
            'age': {'type': 'integer'}
        }
        v = Validator(schema)

        self.assertFail({'name': 'ItsMe', 'age': 2}, validator=v)
        self.assertError('name', (), errors.CUSTOM, None,
                         ('must be lowercase',), v_errors=v._errors)
        self.assertDictEqual(v.errors, {'name': 'must be lowercase'})
        self.assertSuccess({'name': 'itsme', 'age': 2}, validator=v)

    def test_validated(self):
        schema = {'property': {'type': 'string'}}
        v = Validator(schema)
        document = {'property': 'string'}
        self.assertEqual(v.validated(document), document)
        document = {'property': 0}
        self.assertIsNone(v.validated(document))

    def test_anyof(self):
        # prop1 must be either a number between 0 and 10
        schema = {'prop1': {'min': 0, 'max': 10}}
        doc = {'prop1': 5}

        self.assertSuccess(doc, schema)

        # prop1 must be either a number between 0 and 10 or 100 and 110
        schema = {'prop1':
                  {'anyof':
                   [{'min': 0, 'max': 10}, {'min': 100, 'max': 110}]}}
        doc = {'prop1': 105}

        self.assertSuccess(doc, schema)

        # prop1 must be either a number between 0 and 10 or 100 and 110
        schema = {'prop1':
                  {'anyof':
                   [{'min': 0, 'max': 10}, {'min': 100, 'max': 110}]}}
        doc = {'prop1': 50}

        self.assertValidationError(doc, schema)

        # prop1 must be an integer that is either be
        # greater than or equal to 0, or greater than or equal to 10
        schema = {'prop1': {'type': 'integer',
                            'anyof': [{'min': 0}, {'min': 10}]}}
        doc = {'prop1': 10}
        self.assertSuccess(doc, schema)
        doc = {'prop1': 5}
        self.assertSuccess(doc, schema)
        doc = {'prop1': -1}
        self.assertFail(doc, schema)
        exp_child_errors = [
            (('prop1',), ('prop1', 'anyof', 0, 'min'), errors.MIN_VALUE, 0),
            (('prop1',), ('prop1', 'anyof', 1, 'min'), errors.MIN_VALUE, 10)
        ]
        self.assertChildErrors(('prop1',), ('prop1', 'anyof'), errors.ANYOF,
                               [{'min': 0}, {'min': 10}],
                               child_errors=exp_child_errors)
        doc = {'prop1': 5.5}
        self.assertFail(doc, schema)
        doc = {'prop1': '5.5'}
        self.assertFail(doc, schema)

    def test_allof(self):
        # prop1 has to be a float between 0 and 10
        schema = {'prop1': {'allof': [
                 {'type': 'float'}, {'min': 0}, {'max': 10}]}}
        doc = {'prop1': -1}
        self.assertFail(doc, schema)
        doc = {'prop1': 5}
        self.assertSuccess(doc, schema)
        doc = {'prop1': 11}
        self.assertFail(doc, schema)

        # prop1 has to be a float and an integer
        schema = {'prop1': {'allof': [{'type': 'float'}, {'type': 'integer'}]}}
        doc = {'prop1': 11}
        self.assertSuccess(doc, schema)
        doc = {'prop1': 11.5}
        self.assertFail(doc, schema)
        doc = {'prop1': '11'}
        self.assertFail(doc, schema)

    def test_oneof(self):
        # prop1 can only only be:
        # - greater than 10
        # - greater than 0
        # - equal to -5, 5, or 15

        schema = {'prop1': {'type': 'integer', 'oneof': [
                 {'min': 0},
                 {'min': 10},
                 {'allowed': [-5, 5, 15]}]}}

        # document is not valid
        # prop1 not greater than 0, 10 or equal to -5
        doc = {'prop1': -1}
        self.assertFail(doc, schema)

        # document is valid
        # prop1 is less then 0, but is -5
        doc = {'prop1': -5}
        self.assertSuccess(doc, schema)

        # document is valid
        # prop1 greater than 0
        doc = {'prop1': 1}
        self.assertSuccess(doc, schema)

        # document is not valid
        # prop1 is greater than 0
        # and equal to 5
        doc = {'prop1': 5}
        self.assertFail(doc, schema)

        # document is not valid
        # prop1 is greater than 0
        # and greater than 10
        doc = {'prop1': 11}
        self.assertFail(doc, schema)

        # document is not valid
        # prop1 is greater than 0
        # and greater than 10
        # and equal to 15
        doc = {'prop1': 15}
        self.assertFail(doc, schema)

    def test_noneof(self):
        # prop1 can not be:
        # - greater than 10
        # - greater than 0
        # - equal to -5, 5, or 15

        schema = {'prop1': {'type': 'integer', 'noneof': [
                 {'min': 0},
                 {'min': 10},
                 {'allowed': [-5, 5, 15]}]}}

        # document is valid
        doc = {'prop1': -1}
        self.assertSuccess(doc, schema)

        # document is not valid
        # prop1 is equal to -5
        doc = {'prop1': -5}
        self.assertFail(doc, schema)

        # document is not valid
        # prop1 greater than 0
        doc = {'prop1': 1}
        self.assertFail(doc, schema)

        # document is not valid
        doc = {'prop1': 5}
        self.assertFail(doc, schema)

        # document is not valid
        doc = {'prop1': 11}
        self.assertFail(doc, schema)

        # document is not valid
        # and equal to 15
        doc = {'prop1': 15}
        self.assertFail(doc, schema)

    def test_anyof_allof(self):

        # prop1 can be any number outside of [0-10]
        schema = {'prop1': {'allof': [{'anyof': [{'type': 'float'},
                                                 {'type': 'integer'}]},
                                      {'anyof': [{'min': 10},
                                                 {'max': 0}]}
                                      ]}}

        doc = {'prop1': 11}
        self.assertSuccess(doc, schema)
        doc = {'prop1': -1}
        self.assertSuccess(doc, schema)
        doc = {'prop1': 5}
        self.assertFail(doc, schema)

        doc = {'prop1': 11.5}
        self.assertSuccess(doc, schema)
        doc = {'prop1': -1.5}
        self.assertSuccess(doc, schema)
        doc = {'prop1': 5.5}
        self.assertFail(doc, schema)

        doc = {'prop1': '5.5'}
        self.assertFail(doc, schema)

    def test_anyof_allof_schema_validate(self):
        # make sure schema with 'anyof' and 'allof' constraints are checked
        # correctly
        schema = {'doc': {'type': 'dict',
                          'anyof': [
                              {'schema': [{'param': {'type': 'number'}}]}]}}
        self.assertSchemaError({'doc': 'this is my document'}, schema)

        schema = {'doc': {'type': 'dict',
                          'allof': [
                              {'schema': [{'param': {'type': 'number'}}]}]}}
        self.assertSchemaError({'doc': 'this is my document'}, schema)

    def test_anyof_schema(self):
        # test that a list of schemas can be specified.

        valid_parts = [{'schema': {'model number': {'type': 'string'},
                                   'count': {'type': 'integer'}}},
                       {'schema': {'serial number': {'type': 'string'},
                                   'count': {'type': 'integer'}}}]
        valid_item = {'type': ['dict', 'string'], 'anyof': valid_parts}
        schema = {'parts': {'type': 'list', 'schema': valid_item}}
        document = {'parts': [{'model number': 'MX-009', 'count': 100},
                              {'serial number': '898-001'},
                              'misc']}

        # document is valid. each entry in 'parts' matches a type or schema
        self.assertSuccess(document, schema)

        document['parts'].append({'product name': "Monitors", 'count': 18})
        # document is invalid. 'product name' does not match any valid schemas
        self.assertValidationError(document, schema)

        document['parts'].pop()
        # document is valid again
        self.assertSuccess(document, schema)

        document['parts'].append({'product name': "Monitors", 'count': 18})
        document['parts'].append(10)
        # and invalid. numbers are not allowed.
        self.assertFail(document, schema)

        self.assertEqual(len(self.validator._errors), 1)
        self.assertEqual(len(self.validator._errors[0].child_errors), 2)

        exp_child_errors = [
            (('parts', 3), ('parts', 'schema', 'anyof'), errors.ANYOF,
             valid_parts),
            (('parts', 4), ('parts', 'schema', 'type'), errors.BAD_TYPE,
             ['dict', 'string'])
        ]
        self.assertChildErrors(
            'parts', ('parts', 'schema'), errors.SEQUENCE_SCHEMA, valid_item,
            child_errors=exp_child_errors
        )

        self.assertNoError(('parts', 4), ('parts', 'schema', 'anyof'),
                           errors.ANYOF, valid_parts)

        v_errors = self.validator.errors
        self.assertIn('parts', v_errors)
        self.assertIn(3, v_errors['parts'])
        self.assertIn('anyof', v_errors['parts'][3])
        self.assertEqual(v_errors['parts'][3]['anyof'],
                         "no definitions validate")
        self.assertIn('definition 0', v_errors['parts'][3])
        self.assertEqual(
            v_errors['parts'][3]['definition 0']['product name'],
            "unknown field")
        self.assertEqual(
            v_errors['parts'][3]['definition 1']['product name'],
            "unknown field")
        self.assertEqual(
            v_errors['parts'][4],
            "must be of ['dict', 'string'] type")

    def test_anyof_2(self):
        # these two schema should be the same
        schema1 = {'prop': {'anyof': [{'type': 'dict',
                                       'schema': {
                                           'val': {'type': 'integer'}}},
                                      {'type': 'dict',
                                       'schema': {
                                           'val': {'type': 'string'}}}]}}
        schema2 = {'prop': {'type': 'dict', 'anyof': [
                           {'schema': {'val': {'type': 'integer'}}},
                           {'schema': {'val': {'type': 'string'}}}]}}

        doc = {'prop': {'val': 0}}
        self.assertSuccess(doc, schema1)
        self.assertSuccess(doc, schema2)

        doc = {'prop': {'val': '0'}}
        self.assertSuccess(doc, schema1)
        self.assertSuccess(doc, schema2)

        doc = {'prop': {'val': 1.1}}
        self.assertFail(doc, schema1)
        self.assertFail(doc, schema2)

    def test_anyof_type(self):
        schema = {'anyof_type': {'anyof_type': ['string', 'integer']}}
        self.assertSuccess({'anyof_type': 'bar'}, schema)
        self.assertSuccess({'anyof_type': 23}, schema)

    def test_oneof_schema(self):
        schema = {'oneof_schema': {'type': 'dict',
                                   'oneof_schema':
                                       [{'digits': {'type': 'integer',
                                                    'min': 0, 'max': 99}},
                                        {'text': {'type': 'string',
                                                  'regex': '^[0-9]{2}$'}}]}}
        self.assertSuccess({'oneof_schema': {'digits': 19}}, schema)
        self.assertSuccess({'oneof_schema': {'text': '84'}}, schema)
        self.assertFail({'oneof_schema': {'digits': 19, 'text': '84'}}, schema)

    def test_nested_oneof_type(self):
        schema = {'nested_oneof_type':
                  {'valueschema': {'oneof_type': ['string', 'integer']}}}
        self.assertSuccess({'nested_oneof_type': {'foo': 'a'}}, schema)
        self.assertSuccess({'nested_oneof_type': {'bar': 3}}, schema)

    def test_no_of_validation_if_type_fails(self):
        valid_parts = [{'schema': {'model number': {'type': 'string'},
                                   'count': {'type': 'integer'}}},
                       {'schema': {'serial number': {'type': 'string'},
                                   'count': {'type': 'integer'}}}]
        schema = {'part': {'type': ['dict', 'string'], 'anyof': valid_parts}}
        document = {'part': 10}
        self.assertFail(document, schema)
        self.assertEqual(len(self.validator._errors), 1)

    def test_issue_107(self):
        schema = {'info': {'type': 'dict',
                  'schema': {'name': {'type': 'string', 'required': True}}}}
        document = {'info': {'name': 'my name'}}
        self.assertSuccess(document, schema)

        v = Validator(schema)
        self.assertSuccess(document, schema, v)
        # it once was observed that this behaves other than the previous line
        self.assertTrue(v.validate(document))

    def test_dont_type_validate_nulled_values(self):
        self.assertFail({'an_integer': None})
        self.assertDictEqual(self.validator.errors,
                             {'an_integer': 'null value not allowed'})

    def test_dependencies_error(self):
        v = self.validator
        schema = {'field1': {'required': False},
                  'field2': {'required': True,
                             'dependencies': {'field1': ['one', 'two']}}}
        v.validate({'field2': 7}, schema)
        exp_msg = errors.BasicErrorHandler\
            .messages[errors.DEPENDENCIES_FIELD_VALUE.code]\
            .format(field='field2', constraint={'field1': ['one', 'two']})
        self.assertDictEqual(v.errors, {'field2': exp_msg})

    def test_dependencies_on_boolean_field_with_one_value(self):
        # https://github.com/nicolaiarocci/cerberus/issues/138
        schema = {'deleted': {'type': 'boolean'},
                  'text': {'dependencies': {'deleted': False}}}
        try:
            self.assertSuccess({'text': 'foo', 'deleted': False}, schema)
            self.assertFail({'text': 'foo', 'deleted': True}, schema)
            self.assertFail({'text': 'foo'}, schema)
        except TypeError as e:
            if str(e) == "argument of type 'bool' is not iterable":
                self.fail(' '.join([
                    "Bug #138 still exists, couldn't use boolean",
                    "in dependency without putting it in a list.\n",
                    "'some_field': True vs 'some_field: [True]"]))
            else:
                raise

    def test_dependencies_on_boolean_field_with_value_in_list(self):
        # https://github.com/nicolaiarocci/cerberus/issues/138
        schema = {'deleted': {'type': 'boolean'},
                  'text': {'dependencies': {'deleted': [False]}}}

        self.assertSuccess({'text': 'foo', 'deleted': False}, schema)
        self.assertFail({'text': 'foo', 'deleted': True}, schema)
        self.assertFail({'text': 'foo'}, schema)

    def test_document_trail(self):
        class TrailTester(Validator):
            def _validate_trail(self, constraint, field, value):
                test_doc = self.root_document
                for crumb in self.document_path:
                    test_doc = test_doc[crumb]
                assert test_doc == self.document

        v = TrailTester()
        schema = {'foo': {'schema': {'bar': {'trail': True}}}}
        document = {'foo': {'bar': {}}}
        self.assertSuccess(document, schema, v)

    def test_excludes(self):
        schema = {'this_field': {'type': 'dict',
                                 'excludes': 'that_field'},
                  'that_field': {'type': 'dict'}}
        document1 = {'this_field': {}}
        document2 = {'that_field': {}}
        document3 = {'that_field': {}, 'this_field': {}}
        self.assertSuccess(document1, schema)
        self.assertSuccess(document2, schema)
        self.assertSuccess({}, schema)
        self.assertFail(document3, schema)

    def test_mutual_excludes(self):
        schema = {'this_field': {'type': 'dict',
                                 'excludes': 'that_field'},
                  'that_field': {'type': 'dict',
                                 'excludes': 'this_field'}}
        document1 = {'this_field': {}}
        document2 = {'that_field': {}}
        document3 = {'that_field': {}, 'this_field': {}}
        self.assertSuccess(document1, schema)
        self.assertSuccess(document2, schema)
        self.assertSuccess({}, schema)
        self.assertFail(document3, schema)

    def test_required_excludes(self):
        schema = {'this_field': {'type': 'dict',
                                 'excludes': 'that_field',
                                 'required': True},
                  'that_field': {'type': 'dict',
                                 'excludes': 'this_field',
                                 'required': True}}
        document1 = {'this_field': {}}
        document2 = {'that_field': {}}
        document3 = {'that_field': {}, 'this_field': {}}
        self.assertSuccess(document1, schema, update=False)
        self.assertSuccess(document2, schema, update=False)
        self.assertFail({}, schema)
        self.assertFail(document3, schema)

    def test_multiples_exclusions(self):
        schema = {'this_field': {'type': 'dict',
                                 'excludes': ['that_field', 'bazo_field']},
                  'that_field': {'type': 'dict',
                                 'excludes': 'this_field'},
                  'bazo_field': {'type': 'dict'}}
        document1 = {'this_field': {}}
        document2 = {'that_field': {}}
        document3 = {'this_field': {}, 'that_field': {}}
        document4 = {'this_field': {}, 'bazo_field': {}}
        document5 = {'that_field': {}, 'this_field': {}, 'bazo_field': {}}
        document6 = {'that_field': {}, 'bazo_field': {}}
        self.assertSuccess(document1, schema)
        self.assertSuccess(document2, schema)
        self.assertFail(document3, schema)
        self.assertFail(document4, schema)
        self.assertFail(document5, schema)
        self.assertSuccess(document6, schema)

    def test_bad_excludes_fields(self):
        schema = {'this_field': {'type': 'dict',
                                 'excludes': ['that_field', 'bazo_field'],
                                 'required': True},
                  'that_field': {'type': 'dict',
                                 'excludes': 'this_field',
                                 'required': True}}
        self.assertValidationError({'that_field': {},
                                    'this_field': {}}, schema)
        handler = errors.BasicErrorHandler
        self.assertDictEqual(
            self.validator.errors,
            {'that_field': handler.messages[errors.EXCLUDES_FIELD.code].format(
                "'this_field'", field="that_field"),
             'this_field': handler.messages[errors.EXCLUDES_FIELD.code].format(
                 "'that_field', 'bazo_field'", field="this_field")})

    def test_excludes_hashable(self):
        self.validator = Validator()
        schema = {'this_field': {'type': 'dict',
                                 'excludes': 42,
                                 'required': True}}
        self.assertSchemaError({'this_field': {}}, schema)


class TestNormalization(TestBase):
    def test_coerce(self):
        schema = {
            'amount': {'coerce': int}
        }
        v = Validator(schema)
        v.validate({'amount': '1'})
        self.assertEqual(v.document['amount'], 1)

    def test_coerce_in_subschema(self):
        schema = {'thing': {'type': 'dict',
                            'schema': {'amount': {'coerce': int}}}}
        v = Validator(schema)
        self.assertEqual(v.validated({'thing': {'amount': '2'}})
                                     ['thing']['amount'], 2)  # noqa

    def test_coerce_not_destructive(self):
        schema = {
            'amount': {'coerce': int}
        }
        v = Validator(schema)
        doc = {'amount': '1'}
        v.validate(doc)
        self.assertIsNot(v.document, doc)

    def test_coerce_catches_ValueError(self):
        schema = {
            'amount': {'coerce': int}
        }
        v = Validator(schema)
        self.assertFail({'amount': 'not_a_number'}, validator=v)
        self.assertError('amount', ('amount', 'coerce'), errors.COERCION_FAILED,
                         int, v_errors=v._errors)

    def test_coerce_catches_TypeError(self):
        schema = {
            'name': {'coerce': str.lower}
        }
        v = Validator(schema)
        self.assertFail({'name': 1234}, validator=v)
        self.assertError('name', ('name', 'coerce'), errors.COERCION_FAILED, str.lower, v_errors=v._errors)  # noqa

    def test_coerce_unknown(self):
        schema = {'foo': {'schema': {}, 'allow_unknown': {'coerce': int}}}
        v = Validator(schema)
        document = {'foo': {'bar': '0'}}
        self.assertDictEqual(v.normalized(document), {'foo': {'bar': 0}})

    def test_normalized(self):
        schema = {'amount': {'coerce': int}}
        v = Validator(schema)
        self.assertEqual(v.normalized({'amount': '2'})['amount'], 2)

    def test_rename(self):
        document = {'foo': 0}
        v = Validator({'foo': {'rename': 'bar'}})
        self.assertDictEqual(v.normalized(document), {'bar': 0})

    def test_rename_handler(self):
        document = {'0': 'foo'}
        v = Validator({}, allow_unknown={'rename_handler': int})
        self.assertDictEqual(v.normalized(document), {0: 'foo'})

    def test_purge_unknown(self):
        v = Validator({'foo': {'type': 'string'}}, purge_unknown=True)
        self.assertDictEqual(v.normalized({'bar': 'foo'}), {})
        v.purge_unknown = False
        self.assertDictEqual(v.normalized({'bar': 'foo'}), {'bar': 'foo'})
        v.schema = {'foo': {'type': 'dict',
                            'schema': {'foo': {'type': 'string'}},
                            'purge_unknown': True}}
        self.assertDictEqual(v.normalized({'foo': {'bar': ''}}), {'foo': {}})

    def test_issue_147_complex(self):
        schema = {'revision': {'coerce': int}}
        document = {'revision': '5', 'file': NamedTemporaryFile(mode='w+')}
        document['file'].write(r'foobar')
        document['file'].seek(0)
        normalized = Validator(schema, allow_unknown=True).normalized(document)
        self.assertEqual(normalized['revision'], 5)
        self.assertEqual(normalized['file'].read(), 'foobar')
        document['file'].close()
        normalized['file'].close()

    def test_issue_147_nested_dict(self):
        schema = {'thing': {'type': 'dict',
                            'schema': {'amount': {'coerce': int}}}}
        ref_obj = '2'
        document = {'thing': {'amount': ref_obj}}
        normalized = Validator(schema).normalized(document)
        self.assertIsNot(document, normalized)
        self.assertEqual(normalized['thing']['amount'], 2)
        self.assertEqual(ref_obj, '2')
        self.assertIs(document['thing']['amount'], ref_obj)

    def test_coerce_in_valueschema(self):
        # https://github.com/nicolaiarocci/cerberus/issues/155
        schema = {'thing': {'type': 'dict',
                            'valueschema': {'coerce': int,
                                            'type': 'integer'}}}
        self.assertSuccess({'thing': {'amount': '2'}}, schema)
        self.assertDictEqual(self.validator.document, {'thing': {'amount': 2}})

    def test_coerce_in_propertyschema(self):
        # https://github.com/nicolaiarocci/cerberus/issues/155
        schema = {'thing': {'type': 'dict',
                            'propertyschema': {'coerce': int,
                                               'type': 'integer'}}}
        self.assertSuccess({'thing': {'5': 'foo'}}, schema)
        self.assertDictEqual(self.validator.document, {'thing': {5: 'foo'}})

    def test_coercion_of_sequence_items(self):
        # https://github.com/nicolaiarocci/cerberus/issues/161
        schema = {'a_list': {'type': 'list', 'schema': {'type': 'float',
                                                        'coerce': float}}}
        self.assertSuccess({'a_list': [3, 4, 5]}, schema)
        result = self.validator.document
        self.assertListEqual(result['a_list'], [3.0, 4.0, 5.0])
        for x in result['a_list']:
            self.assertIsInstance(x, float)


class DefinitionSchema(TestBase):
    def test_validated_schema_cache(self):
        v = Validator({'foozifix': {'coerce': int}})
        cache_size = len(v.schema.valid_schemas)

        v = Validator({'foozifix': {'type': 'integer'}})
        cache_size += 1
        self.assertEqual(len(v.schema.valid_schemas), cache_size)

        v = Validator({'foozifix': {'coerce': int}})
        self.assertEqual(len(v.schema.valid_schemas), cache_size)

        max_cache_size = 200
        self.assertLess(cache_size, max_cache_size,
                        "There's an unexpected high amount of cached valid "
                        "definition schemas. Unless you added further tests, "
                        "there are good chances that something is wrong. "
                        "If you added tests with new schemas, you can try to "
                        "adjust the variable `max_cache_size` according to "
                        "the added schemas.")

    def bad_of_rules(self):
        schema = {'foo': {'anyof': {'type': 'string'}}}
        self.assertSchemaError({}, schema)

    def test_repr(self):
        v = Validator({'foo': {'type': 'string'}})
        self.assertEqual(repr(v.schema), "{'foo': {'type': 'string'}}")


class ErrorHandling(TestBase):
    def test__error_1(self):
        v = Validator(schema={'foo': {'type': 'string'}})
        v.document = {'foo': 42}
        v._error('foo', errors.BAD_TYPE, 'string')
        error = v._errors[0]
        self.assertEqual(error.document_path, ('foo',))
        self.assertEqual(error.schema_path, ('foo', 'type'))
        self.assertEqual(error.code, 0x24)
        self.assertEqual(error.rule, 'type')
        self.assertEqual(error.constraint, 'string')
        self.assertEqual(error.value, 42)
        self.assertEqual(error.info, ('string',))
        self.assertFalse(error.is_group_error)
        self.assertFalse(error.is_logic_error)

    def test__error_2(self):
        v = Validator(schema={'foo': {'propertyschema': {'type': 'integer'}}})
        v.document = {'foo': {'0': 'bar'}}
        v._error('foo', errors.PROPERTYSCHEMA, ())
        error = v._errors[0]
        self.assertEqual(error.document_path, ('foo',))
        self.assertEqual(error.schema_path, ('foo', 'propertyschema'))
        self.assertEqual(error.code, 0x83)
        self.assertEqual(error.rule, 'propertyschema')
        self.assertEqual(error.constraint, {'type': 'integer'})
        self.assertEqual(error.value, {'0': 'bar'})
        self.assertEqual(error.info, ((),))
        self.assertTrue(error.is_group_error)
        self.assertFalse(error.is_logic_error)

    def test__error_3(self):
        valids = [{'type': 'string', 'regex': '0x[0-9a-f]{2}'},
                  {'type': 'integer', 'min': 0, 'max': 255}]
        v = Validator(schema={'foo': {'oneof': valids}})
        v.document = {'foo': '0x100'}
        v._error('foo', errors.ONEOF, (), 0, 2)
        error = v._errors[0]
        self.assertEqual(error.document_path, ('foo',))
        self.assertEqual(error.schema_path, ('foo', 'oneof'))
        self.assertEqual(error.code, 0x92)
        self.assertEqual(error.rule, 'oneof')
        self.assertEqual(error.constraint, valids)
        self.assertEqual(error.value, '0x100')
        self.assertEqual(error.info, ((), 0, 2))
        self.assertTrue(error.is_group_error)
        self.assertTrue(error.is_logic_error)

    def test_error_tree_1(self):
        schema = {'foo': {'schema': {'bar': {'type': 'string'}}}}
        document = {'foo': {'bar': 0}}
        self.assertFail(document, schema)
        d_error_tree = self.validator.document_error_tree
        s_error_tree = self.validator.schema_error_tree
        self.assertIn('foo', d_error_tree)
        self.assertIn('bar', d_error_tree['foo'])
        self.assertEqual(d_error_tree['foo']['bar'].errors[0].value, 0)
        self.assertEqual(
            d_error_tree.fetch_errors_from(('foo', 'bar'))[0].value, 0)
        self.assertIn('foo', s_error_tree)
        self.assertIn('schema', s_error_tree['foo'])
        self.assertIn('bar', s_error_tree['foo']['schema'])
        self.assertIn('type', s_error_tree['foo']['schema']['bar'])
        self.assertEqual(
            s_error_tree['foo']['schema']['bar']['type'].errors[0].value, 0)
        self.assertEqual(
            s_error_tree.fetch_errors_from(
                ('foo', 'schema', 'bar', 'type'))[0].value, 0)

    def test_error_tree_2(self):
        schema = {'foo': {'anyof': [{'type': 'string'}, {'type': 'integer'}]}}
        document = {'foo': []}
        self.assertFail(document, schema)
        d_error_tree = self.validator.document_error_tree
        s_error_tree = self.validator.schema_error_tree
        self.assertIn('foo', d_error_tree)
        self.assertEqual(d_error_tree['foo'].errors[0].value, [])
        self.assertIn('foo', s_error_tree)
        self.assertIn('anyof', s_error_tree['foo'])
        self.assertIn(0, s_error_tree['foo']['anyof'])
        self.assertIn(1, s_error_tree['foo']['anyof'])
        self.assertIn('type', s_error_tree['foo']['anyof'][0])
        self.assertEqual(
            s_error_tree['foo']['anyof'][0]['type'].errors[0].value, [])

    def test_nested_error_paths(self):
        # TODO regexps can be shortened when #169 is solved
        schema = {'a_dict': {'propertyschema': {'type': 'integer'},
                             'valueschema': {'regex': '[a-z]*$'}},
                  'a_list': {'schema': {'type': 'string',
                                        'oneof_regex': ['[a-z]*$', '[A-Z]*$']}}}
        document = {'a_dict': {0: 'abc', 'one': 'abc', 2: 'aBc', 'three': 'abC'},  # noqa
                    'a_list': [0, 'abc', 'abC']}
        self.assertFail(document, schema)

        _det = self.validator.document_error_tree
        _set = self.validator.schema_error_tree

        self.assertEqual(len(_det.errors), 0)
        self.assertEqual(len(_set.errors), 0)

        self.assertEqual(len(_det['a_dict'].errors), 2)
        self.assertEqual(len(_set['a_dict'].errors), 0)

        self.assertIsNone(_det['a_dict'][0])
        self.assertEqual(len(_det['a_dict']['one'].errors), 1)
        self.assertEqual(len(_det['a_dict'][2].errors), 1)
        self.assertEqual(len(_det['a_dict']['three'].errors), 2)

        self.assertEqual(len(_set['a_dict']['propertyschema'].errors), 1)
        self.assertEqual(len(_set['a_dict']['valueschema'].errors), 1)

        self.assertEqual(
            len(_set['a_dict']['propertyschema']['type'].errors), 2)
        self.assertEqual(len(_set['a_dict']['valueschema']['regex'].errors), 2)

        _ref_err = ValidationError(
            ('a_dict', 'one'), ('a_dict', 'propertyschema', 'type'),
            errors.BAD_TYPE.code, 'type', 'integer', 'one', ())
        self.assertEqual(_det['a_dict']['one'].errors[0], _ref_err)
        self.assertEqual(_set['a_dict']['propertyschema']['type'].errors[0],
                         _ref_err)

        _ref_err = ValidationError(
            ('a_dict', 2), ('a_dict', 'valueschema', 'regex'),
            errors.REGEX_MISMATCH.code, 'regex', '[a-z]*$', 'aBc', ())
        self.assertEqual(_det['a_dict'][2].errors[0], _ref_err)
        self.assertEqual(
            _set['a_dict']['valueschema']['regex'].errors[0], _ref_err)

        _ref_err = ValidationError(
            ('a_dict', 'three'), ('a_dict', 'propertyschema', 'type'),
            errors.BAD_TYPE.code, 'type', 'integer', 'three', ())
        self.assertEqual(_det['a_dict']['three'].errors[0], _ref_err)
        self.assertEqual(
            _set['a_dict']['propertyschema']['type'].errors[1], _ref_err)

        _ref_err = ValidationError(
            ('a_dict', 'three'), ('a_dict', 'valueschema', 'regex'),
            errors.REGEX_MISMATCH.code, 'regex', '[a-z]*$', 'abC', ())
        self.assertEqual(_det['a_dict']['three'].errors[1], _ref_err)
        self.assertEqual(
            _set['a_dict']['valueschema']['regex'].errors[1], _ref_err)

        self.assertEqual(len(_det['a_list'].errors), 1)
        self.assertEqual(len(_det['a_list'][0].errors), 1)
        self.assertIsNone(_det['a_list'][1])
        self.assertEqual(len(_det['a_list'][2].errors), 3)
        self.assertEqual(len(_set['a_list'].errors), 0)
        self.assertEqual(len(_set['a_list']['schema'].errors), 1)
        self.assertEqual(len(_set['a_list']['schema']['type'].errors), 1)
        self.assertEqual(
            len(_set['a_list']['schema']['oneof'][0]['regex'].errors), 1)
        self.assertEqual(
            len(_set['a_list']['schema']['oneof'][1]['regex'].errors), 1)

        _ref_err = ValidationError(
            ('a_list', 0), ('a_list', 'schema', 'type'), errors.BAD_TYPE.code,
            'type', 'string', 0, ())
        self.assertEqual(_det['a_list'][0].errors[0], _ref_err)
        self.assertEqual(_set['a_list']['schema']['type'].errors[0], _ref_err)

        _ref_err = ValidationError(
            ('a_list', 2), ('a_list', 'schema', 'oneof'), errors.ONEOF.code,
            'oneof', 'irrelevant_at_this_point', 'abC', ())
        self.assertEqual(_det['a_list'][2].errors[0], _ref_err)
        self.assertEqual(_set['a_list']['schema']['oneof'].errors[0], _ref_err)

        _ref_err = ValidationError(
            ('a_list', 2), ('a_list', 'schema', 'oneof', 0, 'regex'),
            errors.REGEX_MISMATCH.code, 'regex', '[a-z]*$', 'abC', ())
        self.assertEqual(_det['a_list'][2].errors[1], _ref_err)
        self.assertEqual(
            _set['a_list']['schema']['oneof'][0]['regex'].errors[0], _ref_err)

        _ref_err = ValidationError(
            ('a_list', 2), ('a_list', 'schema', 'oneof', 1, 'regex'),
            errors.REGEX_MISMATCH.code, 'regex', '[a-z]*$', 'abC', ())
        self.assertEqual(_det['a_list'][2].errors[2], _ref_err)
        self.assertEqual(
            _set['a_list']['schema']['oneof'][1]['regex'].errors[0], _ref_err)

    def test_basic_error_handler(self):
        handler = errors.BasicErrorHandler()
        _errors, ref = [], {}

        _errors.append(ValidationError(
            ['foo'], ['foo'], 0x62, 'readonly', True, None, ()))
        ref.update({'foo': handler.messages[0x62]})
        self.assertDictEqual(handler(_errors), ref)

        _errors.append(ValidationError(
            ['bar'], ['foo'], 0x42, 'min', 1, 2, ()))
        ref.update({'bar': handler.messages[0x42].format(constraint=1)})
        self.assertDictEqual(handler(_errors), ref)

        _errors.append(ValidationError(
            ['zap', 'foo'], ['zap', 'schema', 'foo'], 0x24, 'type', 'string',
            True, ()))
        ref.update({'zap': {'foo': handler.messages[0x24].format(
            constraint='string')}})
        self.assertDictEqual(handler(_errors), ref)

        _errors.append(ValidationError(
            ['zap', 'foo'], ['zap', 'schema', 'foo'], 0x41, 'regex',
            '^p[äe]ng$', 'boom', ()))
        ref['zap']['foo'] = \
            [ref['zap']['foo'],
             handler.messages[0x41].format(constraint='^p[äe]ng$')]
        self.assertDictEqual(handler(_errors), ref)


# TODO remove on next major release
class BackwardCompatibility(TestBase):
    def test_keyschema(self):
        schema = {'a_field': {'type': 'list',
                              'schema': {'keyschema': {'type': 'string'}}}}
        document = {'a_field': [{'a_key': 'a_string'}]}
        v = Validator()
        self.assertSuccess(document, schema, v)


class TestInheritance(TestBase):
    def test_contextual_data_preservation(self):

        class InheritedValidator(Validator):
            def __init__(self, *args, **kwargs):
                if 'working_dir' in kwargs:
                    self.working_dir = kwargs['working_dir']
                super(InheritedValidator, self).__init__(*args, **kwargs)

            def _validate_type_test(self, field, value):
                if not self.working_dir:
                    self._error('self.working_dir', 'is None')

        v = InheritedValidator({'test': {'type': 'list',
                                         'schema': {'type': 'test'}}},
                               working_dir='/tmp')
        self.assertSuccess({'test': ['foo']}, validator=v)


class TestDockerCompose(TestBase):
    """ Tests for https://github.com/docker/compose """
    def setUp(self):
        self.validator = Validator()

    def test_environment(self):
        schema = {'environment': {'oneof': [{'type': 'dict',
                                             'valueschema': {'type': 'string',
                                                             'nullable': True}},  # noqa
                                            {'type': 'list',
                                             'schema': {'type': 'string'}}]}}

        document = {'environment': {'VARIABLE': 'FOO'}}
        self.assertSuccess(document, schema)

        document = {'environment': ['VARIABLE=FOO']}
        self.assertSuccess(document, schema)

    def test_one_of_dict_list_string(self):
        ptrn_domain = '[a-z0-9-]+(\.[a-z0-9-]+)+'
        ptrn_hostname = '[a-z0-9-]+'
        ptrn_ip = '(([0-9]{1,3})\.){3}[0-9]{1,3}'
        ptrn_extra_host = '^(' + ptrn_hostname + '|' + ptrn_domain + '):' + ptrn_ip + '$'  # noqa
        schema = {'extra_hosts': {'oneof': [{'type': 'string',
                                             'regex': ptrn_extra_host},

                                             {'type': 'list', 'schema': {'type': 'string', 'regex': ptrn_extra_host}},  # noqa

                                             {'type': 'list',
                                              'schema': {'type': 'dict',
                                                         'propertyschema': {'type': 'string', 'regex': '^(' + ptrn_hostname + '|' + ptrn_domain + ')$'},  # noqa
                                                         'valueschema': {'type': 'string', 'regex': '^' + ptrn_ip + '$'}}},  # noqa

                                             {'type': 'dict',
                                              'propertyschema': {'type': 'string', 'regex': '^(' + ptrn_hostname + '|' + ptrn_domain + ')$'},  # noqa
                                              'valueschema': {'type': 'string', 'regex': '^' + ptrn_ip + '$'}}  # noqa
                                            ]}}

        document = {'extra_hosts': ["www.domain.net:127.0.0.1"]}
        self.assertSuccess(document, schema)

        document = {'extra_hosts': "www.domain.net:127.0.0.1"}
        self.assertSuccess(document, schema)

        document = {'extra_hosts': ["somehost:127.0.0.1"]}
        self.assertSuccess(document, schema)

        document = {'extra_hosts': [{"somehost": "127.0.0.1"}]}
        self.assertSuccess(document, schema)

        document = {'extra_hosts': {"somehost": "127.0.0.1"}}
        self.assertSuccess(document, schema)

        document = {'extra_hosts': "127.0.0.1:somehost"}
        self.assertFail(document, schema)

        document = {'extra_hosts': "somehost::alias:127.0.0.1"}
        self.assertFail(document, schema)

# -*- coding: utf-8 -*-

import pytest
import six
import inspect
import random

keyword_types = [
    ('boolean', '1', True),
    ('boolean', '0', False),
    ('boolean', True, True),
    ('boolean', False, False),
    ('boolean', 'yes', True),
    ('boolean', 'no', False),
    ('boolean', 'on', True),
    ('boolean', 'off', False),
    ('boolean', 't', True),
    ('boolean', 'f', False),
    ('boolean', 'true', True),
    ('boolean', 'false', False),
    ('boolean', 'TruE', True),
    ('boolean', 'fALSe', False),
    ('boolean', 'other', ValueError),
    ('integer', '1', 1),
    ('integer', 1, 1),
    ('integer', 100, 100),
    ('integer', 2.5, 2),
    ('integer', 3.9, 3),
    ('integer', '4.1', 4),
    ('integer', 'blah', ValueError),
    ('integer', 1e32, ValueError),
    ('double', 1, 1.0),
    ('double', 1.0, 1.0),
    ('double', 1e10, 1e10),
    ('double', 1.234567e50, 1.234567e50),
    ('double', '4.1', 4.1),
    ('double', 'blah', ValueError),
    ('string', 'foobar', 'foobar'),
    ('string', six.text_type('foobar'), 'foobar')
]

for kwtype, modify, update in keyword_types:
    if kwtype == 'double':
        keyword_types.append(('float', modify, update))

@pytest.mark.parametrize("kwtype,modify,update", keyword_types)
def test_keyword_types(kwtype, modify, update, dispatcher):
    """Test a keyword type."""
    name = "my{0}".format(kwtype.replace(" ","")).upper()
    from Cauldron import DFW
    DFW.Keyword.types[kwtype](name, dispatcher)
    modify_update(dispatcher[name], modify, update)
    
def modify_update(keyword, modify, update):
    """Run a modify-update test on a keyword."""
    if inspect.isclass(update) and issubclass(update, Exception):
        with pytest.raises(update):
            keyword.modify(modify)
    else:
        keyword.modify(modify)
        keyword.update()
        assert keyword._ktl_binary() == update
    
@pytest.fixture
def keyword_enumerated(dispatcher):
    """An enumerated keyword."""
    from Cauldron import DFW
    kwd = DFW.Keyword.types["enumerated"]("MYENUMERATED", dispatcher)
    kwd.values["ONE"] = 1
    kwd.values["TWO"] = 2
    kwd.values["THREE"] = 3
    return kwd

@pytest.mark.parametrize("modify,update", [
    ("ONE", 1),
    ("TWO", 2),
    ("THREE", 3),
    (1, 1),
    (2, 2),
    (3, 3),
    (4, ValueError),
    ("FOUR", ValueError),
])
def test_keyword_enumerated(keyword_enumerated, modify, update):
    """Modify-update tests for an enumerated keyword."""
    modify_update(keyword_enumerated, modify, update)

@pytest.mark.xfail
@pytest.mark.parametrize("kwtype", ['mask', 'integer array', 'float array', 'double array'])
def test_keyword_type_not_implemented(kwtype, dispatcher, recwarn):
    """Test not-implemented keyword types"""
    from Cauldron import DFW
    from Cauldron.exc import CauldronAPINotImplementedWarning
    kwd = DFW.Keyword.types[kwtype]("MYNOTIMPLEMENTED", dispatcher)
    w = recwarn.pop()
    assert issubclass(w.category, CauldronAPINotImplementedWarning)

def test_increment_integer(dispatcher):
    """Test an integer increment."""
    from Cauldron import DFW
    kwd = DFW.Keyword.Integer("MYINT", dispatcher)
    assert kwd['value'] == None
    kwd.increment()
    assert kwd['value'] == '1'
    v = random.randint(int(-pow(2, 31) - 1), int(pow(2, 31) - 1))
    kwd.modify(v)
    kwd.increment()
    assert kwd['value'] == str(v + 1)

@pytest.mark.parametrize("kwtype", dict((k[0], True) for k in keyword_types).keys())
def test_keyword_inherits_basic(kwtype, dispatcher):
    """Test that keyword objects all inherit from basic."""
    from Cauldron import DFW
    from Cauldron.types import KeywordType, Basic
    name = "my{0}".format(kwtype.replace(" ","")).upper()
    kwd = DFW.Keyword.types[kwtype](name, dispatcher)
    assert isinstance(kwd, KeywordType)
    assert isinstance(kwd, Basic)
    
def test_keyword_inherits_basic_simple(dispatcher):
    """Test that even simple keywords inherit from basic types."""
    from Cauldron.types import KeywordType, Basic
    kwd = dispatcher['KEYWORD']
    assert isinstance(kwd, KeywordType)
    assert isinstance(kwd, Basic)
    
@pytest.mark.parametrize("kwtype", dict((k[0], True) for k in keyword_types).keys())
def test_client_keyword_inherits_basic(kwtype, dispatcher, client):
    """Test that keyword objects all inherit from basic."""
    from Cauldron import ktl
    from Cauldron.types import KeywordType, Basic
    name = "my{0}".format(kwtype.replace(" ","")).upper()
    _k = dispatcher[name]
    if kwtype not in ktl.Keyword.types:
        pytest.skip("Not a valid ktl client-side type.")
    kwd = ktl.Keyword.types[kwtype](client, name)
    assert isinstance(kwd, KeywordType)
    assert isinstance(kwd, Basic)
    
def test_client_keyword_inherits_basic_simple(dispatcher, client):
    """Test that even simple keywords inherit from basic types."""
    from Cauldron.types import KeywordType, Basic
    _k = dispatcher['KEYWORD']
    kwd = client['KEYWORD']
    assert isinstance(kwd, KeywordType)
    assert isinstance(kwd, Basic)
    
    
    
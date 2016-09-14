# -*- coding: utf-8 -*-

import pytest

from six.moves import cStringIO as StringIO

from ..console import ktl_show, ktl_modify, parseModifyCommands


@pytest.fixture
def outfile():
    """Output file."""
    return StringIO()

@pytest.fixture
def errfile():
    """Error file."""
    return StringIO()
    
def test_show_basic(dispatcher, keyword_name, outfile, errfile):
    """Test a basic show command."""
    dispatcher[keyword_name].modify("Hello")
    ktl_show(dispatcher.name, keyword_name, output=outfile, error=errfile)
    output = outfile.getvalue()
    error = errfile.getvalue()
    assert error == ""
    assert output == "{0}: Hello\n".format(keyword_name)

def test_show_multiple(dispatcher, keyword_name, keyword_name1, keyword_name2, outfile, errfile):
    """Test show with multiple"""
    keywords = [keyword_name, keyword_name1, keyword_name2]
    for i,keyword in enumerate(keywords):
        dispatcher[keyword].modify("Hello{0}".format(i))
    
    ktl_show(dispatcher.name, *keywords, output=outfile, error=errfile)
    error = errfile.getvalue()
    assert error == ""
    
    output = outfile.getvalue()
    assert output.splitlines() == ["{0}: Hello{1}".format(keyword,i) for i,keyword in enumerate(keywords)]
    
def test_show_error(dispatcher, keyword_name, keyword_name1, keyword_name2, outfile, errfile):
    """Test show with an error."""
    keywords = [keyword_name, keyword_name2]
    for i,keyword in enumerate(keywords):
        dispatcher[keyword].modify("Hello{0}".format(i))
    
    ktl_show(dispatcher.name, *(keyword_name, keyword_name1, keyword_name2), output=outfile, error=errfile)
    error = errfile.getvalue()
    assert error.splitlines()[0] == "Can't find keyword 'KEYWORD1' in service 'testsvc'"
    assert error.splitlines()[1].endswith("> has no key 'KEYWORD1'\"")
    
    output = outfile.getvalue()
    assert output.splitlines() == ["{0}: Hello{1}".format(keyword,i) for i,keyword in enumerate(keywords)]
    
def check_parse_modify(pairs, n, keyword, value):
    """Check parse-modify commands."""
    assert len(pairs) == n
    for keyword, value in pairs:
        assert keyword.startswith(keyword)
        assert value == value
    
def test_parse_modify_commands():
    """Test parse modify commands."""
    flags = {}
    pairs = list(parseModifyCommands(["KEYWORD1=","value", "KEYWORD2", "=value", "KEYWORD3=value"], flags))
    assert flags == {}
    check_parse_modify(pairs, 3, "KEYWORD", "value")
    
    flags['bogus'] = False
    pairs = list(parseModifyCommands(["KEYWORD1="," ","bogus","KEYWORD2","=", "KEYWORD3="], flags))
    assert flags == {'bogus':True}
    check_parse_modify(pairs, 3, "KEYWORD", "")
    
    with pytest.raises(ValueError):
        list(parseModifyCommands(["KEYWORD1="," ","KEYWORD3","KEYWORD2","=", "KEYWORD3="], flags))
    
    with pytest.raises(ValueError):
        list(parseModifyCommands(["KEYWORD1="," ","bogus","KEYWORD2","=", "KEYWORD3"], flags))
    
    
@pytest.fixture(params=[True, False])
def notify(request):
    return request.param
    
@pytest.fixture(params=[True, False])
def nowait(request):
    return request.param

@pytest.fixture()
def flags(notify, nowait):
    """Set various combinations of flags."""
    return {'notify':notify, 'nowait':nowait, 'timeout': 0.1}
    
def test_modify_success(dispatcher, keyword_name, keyword_name1, keyword_name2, outfile, errfile, flags):
    """Test a succsessful modify command."""
    keywords = [keyword_name, keyword_name1, keyword_name2]
    for i,keyword in enumerate(keywords):
        dispatcher[keyword].modify("Hello{0}".format(i))
    
    ktl_modify(dispatcher.name, *((keyword_name, "Goodbye0"), (keyword_name1, "Goodbye1"), (keyword_name2, "Goodbye2")), output=outfile, error=errfile, **flags)    
    
    if flags['notify']:
        mode = "notify"
    elif not (flags['nowait'] or flags['notify']):
        mode = "wait"
    else:
        mode = "nowait"
    
    output = outfile.getvalue()
    assert output.splitlines()[:len(keywords)] == ["setting {0} = Goodbye{1} ({2})".format(keyword,i,mode) for i,keyword in enumerate(keywords)]
    if mode == "notify" and not flags['nowait']:
        assert output.splitlines()[len(keywords):] == ["{0} complete".format(keyword) for keyword in keywords]
    
def test_modify_error(dispatcher, keyword_name, keyword_name1, keyword_name2, outfile, errfile):
    """Test a succsessful modify command."""
    keywords = [keyword_name, keyword_name2]
    for i,keyword in enumerate(keywords):
        dispatcher[keyword].modify("Hello{0}".format(i))
    
    ktl_modify(dispatcher.name, *((keyword_name, "Goodbye0"), (keyword_name1, "Goodbye2"), (keyword_name2, "Goodbye1")), output=outfile, error=errfile, timeout=0.1)    
    error = errfile.getvalue()
    assert error.splitlines()[0] == "Can't find keyword 'KEYWORD1' in service 'testsvc'"
    assert error.splitlines()[1].endswith("> has no key 'KEYWORD1'\"")
    
    output = outfile.getvalue()
    assert output.splitlines() == ["setting {0} = Goodbye{1} (wait)".format(keyword,i) for i,keyword in enumerate(keywords)]
    



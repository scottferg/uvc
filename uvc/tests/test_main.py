import os

from uvc import main, hg, commands, svn

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", 
                        "testfiles"))

context = None

def setup_module(module):
    global context
    if not os.path.exists(topdir):
        os.mkdir(topdir)
    context = main.Context(topdir)
    
def test_command_conversion():
    result = main.convert(context, ["hg", "clone", 
        "http://hg.mozilla.org/labs/bespin", "bespin"])
    assert isinstance(result, hg.clone)
    
def test_clone_command_can_infer_dialect():
    result = main.convert(context, ["clone", "http://hg.mozilla.org/labs/bespin", 
                          "bespin"])
    assert isinstance(result, hg.clone)
    
def test_is_new_project_command():
    true_tests = [
        "clone http://foo",
        "checkout http://foo",
        "hg clone http://foo",
        "svn checkout http://foo",
        "git clone http://foo",
        "bzr clone http://foo"
    ]
    
    false_tests = [
        "crone http://foo",
        "hg checkout http://foo"
    ]
    def run_one(to_test, expected):
        result = main.is_new_project_command(to_test)
        assert result == expected, "For %s, expected %s but got %s" % \
            (to_test, expected, result)
    
    for test in true_tests:
        yield run_one, test.split(), True
    for test in false_tests:
        yield run_one, test.split(), False
    
def test_get_command_class():
    result = main.get_command_class(context, ["hg", "commit"])
    assert result == hg.commit
    result = main.get_command_class(context, 
                ["clone", "http://hg.mozilla.org/labs/bespin"])
    assert result == hg.clone
    result = main.get_command_class(context,
                ["checkout", "http://foo/bar"], dialect=main.get_dialect('svn'))
    assert result == svn.clone

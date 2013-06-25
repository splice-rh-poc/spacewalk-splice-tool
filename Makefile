SRC_DIR = src/spacewalk-splice-tool

STYLETESTS ?=
PYFILES=`find  src/ -name "*.py"`
TESTFILES=`find test/ -name "*.py"`
STYLEFILES=$(PYFILES)
# note, set STYLETEST to something if you want
# make stylish to check the tests code
# as well

ifdef STYLETESTS
STYLEFILES+=$(TESTFILES)
endif



pyflakes:
# pyflakes doesn't have a config file, cli options, or a ignore tag
# and the variants of "redefination" we get now aren't really valid
# and other tools detect the valid cases, so ignore these
#
	-@TMPFILE=`mktemp` || exit 1; \
	pyflakes $(STYLEFILES) |  grep -v "redefinition of unused.*from line.*" | tee $$TMPFILE; \
	! test -s $$TMPFILE

pylint:
	-@PYTHONPATH="src/:/usr/share/rhn:/usr/share/rhsm" pylint --rcfile=pylintrc $(STYLEFILES)

tablint:
	@! GREP_COLOR='7;31' grep --color -nP "^\W*\t" $(STYLEFILES)

trailinglint:
	@! GREP_COLOR='7;31'  grep --color -nP "[ \t]$$" $(STYLEFILES)

whitespacelint: tablint trailinglint

# look for things that are likely debugging code left in by accident
debuglint:
	@! GREP_COLOR='7;31' grep --color -nP "pdb.set_trace|pydevd.settrace|import ipdb|import pdb|import pydevd" $(STYLEFILES)

gettext_lint:
	@TMPFILE=`mktemp` || exit 1; \
	pcregrep -n --color=auto -M  "_\(.*[\'|\"].*[\'|\"]\s*\+\s*[\"|\'].*[\"|\'].*\)" $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

pep8:
	@TMPFILE=`mktemp` || exit 1; \
	pep8 --ignore E501 --exclude ".#*" --repeat src $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

rpmlint:
	@TMPFILE=`mktemp` || exit 1; \
	rpmlint -f rpmlint.config python-rhsm.spec | grep -v "^.*packages and .* specfiles checked\;" | tee $$TMPFILE; \
	! test -s $$TMPFILE

stylish: pyflakes whitespacelint pep8 gettext_lint rpmlint debuglint

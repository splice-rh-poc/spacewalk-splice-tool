![build status](https://travis-ci.org/splice/spacewalk-splice-tool.png?branch=master)

spacewalk-splice-tool
=====================


how to use with multiple spacewalks
-----------------------------------

set up config like so:

    [spacewalk_foo]
    < details for spacewalk "foo" >

    [spacewalk_bar]
    < details for spacewalk "bar" >

Note that the "nickname" for the spacewalk (what appears in SAM) is read from the string after the '_' char.

If you want to use the report_input command line param to load data, it can be done like so:

    spacewalk-splice-checkin --spacewalk-sync --report_input=/path/to/foo --report_input=/path/to/bar

This will load data as if it came from "foo" and "bar" spacewalks. The last directory name is used as the nickname.

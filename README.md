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

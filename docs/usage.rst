Usage through the PIACERE IDE
=============================


Invoking the DOML Model Checker from the PIACERE IDE
-----------------------------------------------------

The DOML Model Checker is usually invoked from the PIACERE IDE.
It expects a DOML file in XMI format as its input,
so plain DOML files must be manually converted.
The workflow is as follows:

1. Right-click the DOML file to be checked in the IDE's left sidebar;
2. In the context-menu, select *Piacere* -> *Generate DOMLX Model*;
3. Pick a name for the .domlx file to be generated and click OK;
4. Right-click the newly-generated .domlx file;
5. In the context-menu, select *Piacere* -> *Validate DOML*.


After some time, the IDE will report the model checker's results in a new window.

Normally, verification can have two outcomes:

* *Your requirements are SATISFIED*:
  this means your DOML model passed all the standard checks for common mistakes;
* *Your requirements are UNSATISFIED*:
  this means the model checker has found a problem in your DOML model.
  A description of the problem follows.

In case of errors in the verification process, the IDE reports them in a new window,
together with a description.
A common error is the following:

  The supplied DOMLX model is malformed or its DOML version is unsupported.

This often happens because of a mismatch between the DOML version supported by the IDE
and the one supported by the model checker.


Settings
--------

The only model-checker-related settings you may customize from the PIACERE IDE
are the endpoint connection data.

Select the *Preferences* entry of the *Window* menu of the PIACERE IDE,
and then choose *Piacere* -> *Model Checker Preferences*.

Here you may enter the endpoint address and port, which is useful in case you want to
run the DOML Model Checker locally, instead of using the official deployment.

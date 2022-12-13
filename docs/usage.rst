Usage
*****


Through the PIACERE IDE
=======================

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

Through the Command Line Interface
==================================

Another way to use the model checker is through the CLI.
It provides additional options that are not available in the IDE at
the moment, such as support for a separate user requirement file
and synthesis of DOMLX.

You can run it with::

  python -m mc_openapi [options]

To display all the available flags, run::

  python -m mc_openapi -h

Options
-------

Please note that not all flags work with eachother. In most cases, some won't have
any effect in certain CLI flags combinations.

There are **3 Modes** in which the CLI can run:

- REST API (**R**)
- Model Checker (**C**)
- Model Synthesis (**S**)

======  =========================  =========  =================
Flags                              Mode       Description
---------------------------------  ---------  -----------------
Short   Long         
======  =========================  =========  =================
``-h``  ``--help``                 C, S, T    Print the all the available flags with an explanation
``-v``  ``--verbose``              C, S, T    Print a detailed human-readable output of everything going on. Helpful for debugging
``-p``  ``--port``                 R          The port that will expose the REST API (default: 8080)
``-d``  ``--doml``                 C, S       The DOMLX file to check with the model checker
``-V``  ``--doml-version``         C, S       The DOML version in which the DOMLX file is written in
``-r``  ``--requirements``         C, S       A text file containing the user-defined requirements written in :doc:`DOMLR <writing-requirements>`.
``-S``  ``--skip-common-checks``   C          Skips :doc:`build-in requirements <requirements>` checks
``-c``  ``--check-consistency``    C          Perform additional consistency checks (legacy)
``-t``  ``--threads``              C, S, T    The number of threads used by the model checker (default: 2)
``-s``  ``--synth``                S          Synthetize a new DOMLX file from requirements
``-m``  ``--max-tries``            S          Max number of tries to solve a model during synthesis (default: 10)
======  =========================  =========  =================

*If you do not provide the ``--doml`` option or the ``--synth`` option it will start the web server hosting the REST API!*

Examples
--------

To check a DOMLX file with user-provided custom requirements, you may run::

  python -m mc_openapi -d ./path/to/myModel.domlx -r ./path/to/myRequirements.domlr -V V2_0

To synthetize a new DOMLX file with 4 threads and a maximum of 15 tries, you may run::

  python -m mc_openapi -d ./path/to/myModel.domlx --synth -t 4 -m 15
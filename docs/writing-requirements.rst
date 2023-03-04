Writing Requirements
********************

A feature of the DOML Model Checker is a Domain Specific Language (DSL)
called **DOMLR** (the R stands for requirements).

It will be integrated in the DOML in a future release.
For now, it can be provided to the Model Checker through the CLI.

Getting Started
===============

At the moment, you can integrate the requirements inside DOML using the ``functional_requirements`` field::

    functional_requirements {
        req_group_1 ```
        # Your DOMLR goes here.
        ```;
        req_group_2 ```
        # Other set of requirements
        ```;
    }


If you want to write a snippet of DOMLR using VS Code, there's a `Syntax Highlight`_ extension for it.

Every DOMLR piece of code is a list of requirement::

    + "All Virtual Machines have a Interface and at least 4 cpu cores"
    forall vm (
        vm is class abstract.VirtualMachine
        implies
        exists iface (
            vm has abstract.ComputingNode.ifaces iface
            and
            vm has abstract.ComputingNode.cpu_count >= 4 
        )
    )
    error: "A vm lacks an associated interface or has less than 4 CPUs"

Rules in 1 minute
-----------------

The language is *case-sensitive* but it's not indentation-based, so you are free to write it as you prefer.

1.  A requirement must **start** with a ``+`` or ``-`` character.

    -   ``+`` means that the requirement is in **positive form**: the requirement is satisfied when its logic expression is satisfied.

    -   ``-`` means that the requirement is in **negative form**: the requirement is satisfied when its logic expression **is not** satisfied.

2.  After the ``+`` or ``-`` there's the **name** of the requirement, which is a string between double quotes ``"..."``.
    Single quotes ``'...'`` won't work.

3.  Following the requirement name, there's the **logic expression** which is the core of the requirement.
    It is written in `First Order Logic`_, so it will evaluate to either true or false. See the `Syntax`_ for details.

4.  Last, following ``error:``, there is the **error message** that is printed when the requirement is not satisfied.
    If you have a free variable, which means a variable that is not quantified, you can print its value by putting it in the
    string between curly brackets like this: ``{myVar}``. You'll get a warning if the Model Checker can't assign a value to that variable.

A note on positive and negative form
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The difference is that in **positive form** you would generally use a *for all* quantifier at the beginning,
which doesn't allow you to know which specific element didn't satisfy the requirement, while in **negative form**
you'll have some variables that are not quantified, meaning that it's usually possible to retrieve the names of the
elements associated to those variables that do not satisfy the requirement. **Negative form** is usually faster, you
can convert an expression into it using :math:numref:`logicconv`, where :math:`P(x)` is a statement containing quantified variable :math:`x`.

.. math:: \forall x P(x) \iff \neg\exists x \neg P(x)
    :label: logicconv

.. `Syntax`:

Syntax
======

The syntax is the following:

- Unary operators: ``not``
    - Example: ``not <expression>``
- Binary operators: ``or``, ``and``, ``implies``, ``iff`` (if and only if, AKA double implication)
    - Example: ``<expression> and <expression>``
- Quantifiers: ``forall``, ``exists``
    - Example: ``forall x, y ( <expression> )``
    - After the quantifier keywork (``forall``, ``exists``) you must specify a list of quantified variables
        (separated by a comma ``,`` if there's more than one).
    - Between the mandatory pair of parenthesis, you'll be able to use the quantified variables in a logic expression.
- Parenthesis: ``(`` ... ``)``
    - Useful when you have doubts about the precedence of operators, or want to increase legibility in certain situations.
- Elements (variables):
    - Begin with a lowercase letter.
    - Example: ``virtualMachine`` or ``vm``
- Values (constants):
    - Strings are delimited by double quotes ``"..."``
    - Numbers are integers.
    - Booleans are either ``:true`` or ``:false``
    - Example: ``56``, ``"linux"``, ``:true``
- Relationships: ``<elem> has <relationship> <elem/value>``
    - There are two types of relationships:
        - **Associations** are a relationship between two elements (variables).
        - **Attributes** are a relationship between an element (variable) and a value (variable or constant).
    - Relationships follow this naming structure ``<package>.<class>.<relationship>``.
    - Example:
        - ``vm has abstract.ComputingNode.ifaces iface`` is an **Association**, as it puts in relationship the element ``vm`` with the element ``iface``.

        - ``vm has abstract.ComputingNode.cpu_count >= 4`` is an **Attribute** Relationship, as it compares a property (``cpu_count``) of the element ``vm`` with a constant number.
- Classes: ``class <class name>``
    - They represent a kind of element in the architecture.
    - Classes follow this naming structure ``<package>.<class>``
- Equality: ``is``, ``is not``
    - Used to set an equality (or inequality) constraint on an element variable. You can use it to assign a class to an element.
    - Example: ``vm is class abstract.VirtualMachine``
- Comparisons: ``>``,  ``>=``,  ``<``,  ``<=``,  ``==``,  ``!=``
    - You can compare attributes with constants, or attributes with attributes.
    - Example: 
        - ``vm has abstract.ComputingNode.cpu_count >= 4`` compares attribute ``cpu_count`` with a numeric constant.
        - ``vm1 has abstract.ComputingNode.cpu_count >= vm2 abstract.ComputingNode.cpu_count`` compares attribute ``cpu_count`` of ``vm1`` with the one of ``vm2``.



Operator Precedence
-------------------

``exists``/``forall`` > ``not`` > ``or`` > ``and`` > ``implies`` > ``iff``

Examples
========

1. State that an element must be of a certain class::

    saas is class application.SaaS

2. Check that an element has a certain relationship with another::

    vm has infrastructure.ComputingNode.ifaces iface

Note that in the above example we haven't said anything about the nature of ``vm``. 
We get that ``iface`` is of class ``NetworkInterface`` for free since the association ``infrastructure.ComputingNode.ifaces`` requires it.
If you want ``vm`` to be a `VirtualMachine` you should specify it as::
    
    vm is class infrastructure.VirtualMachine
    and
    vm has infrastructure.ComputingNode.ifaces iface

3. State that all VMs have to use less than 1 GB of memory::
    
        forall vm (
            vm is class infrastructure.VirtualMachine
            implies
            vm has infrastructure.ComputingNode.memory_mb <= 1024 
        )

We use ``forall`` to say that all ``vm``, **if** (that's what ``implies`` does)  ``vm`` that are ``VirtualMachine``, 
then it should have less than 1024 MB (memory here is expressed in MB).

If we want to rewrite this requirement in negative form, it becomes *'There is a VM that has more than 1 GB'*. If there exists such VM, then it means that
the expression is *true*, therefore the requirement is *false*::
    
    exists vm (
        vm is class infrastructure.VirtualMachine
        and
        vm has infrastructure.ComputingNode.memory_mb > 1024
        # we can also write it as a negation
        or not vm has infrastructure.ComputingNode.memory <= 1024 
    )

4. Compare two attributes of two elements. Let's say that you have two different containers, ``c1`` and ``c2``, and you want to require
that the memory used by ``c1`` is less than the one used by ``c2`` (note that we don't put another ``has`` in the expression in right hand side of ``<``)::

    c1 has infrastructure.ComputingNode.memory_mb < c2 infrastructure.ComputingNode.memory_mb

Grammar
=======
See the `grammar.lark`_ file on GitHub, it's written in a EBNF-like form.


.. _`Syntax Highlight`: https://marketplace.visualstudio.com/items?itemName=andreafra.piacere-domlr
.. _`First Order Logic`: https://en.wikipedia.org/wiki/First-order_logic
.. _`grammar.lark`: https://github.com/andreafra/piacere-model-checker/blob/main/mc_openapi/doml_mc/domlr_parser/grammar.lark
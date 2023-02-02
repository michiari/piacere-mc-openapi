Writing Requirements
********************

A feature of the DOML Model Checker is a Domain Specific Language (DSL)
called **DOMLR** (the R stands for requirements).

It will be integrated in the DOML in a future release.
For now, it can be provided to the Model Checker through the CLI.

Getting Started
===============

First, create a new file with a ``.domlr`` extension.

If you use VS Code, there's a `Syntax Highlight`_ extension for it.

Every user requirement file is a list of requirement::

    + "All Virtual Machines have a Interface and at least 4 cpu cores"
    forall vm (
        vm is class abstract.VirtualMachine
        implies
        exists iface (
            vm has abstract.ComputingNode.ifaces iface
            and
            vm has abstract.ComputingNode.cpu_cores >= 4 
        )
    )
    error: "A vm does lacks an associated interface or has less than 4 cpu cores"

Rules in 1 minute
-----------------

The language is *case-sensitive* but it's not indentation-based, so you are free to write it as you prefer.

1.  A requirement must **start** with a ``+`` or ``-`` character.

    -   ``+`` means that the requirement is in **positive form**: the requirement is satisfied when its logic expression is satisfied.

    -   ``-`` means that the requirement is in **negative form**: the requirement is satisfied when its logic expression **is not** satisfied.

    The difference is that in **positive form** you would generally use a *for all* quantifier at the beginning,
    which doesn't allow you to know which specific element didn't satisfy the requirement, while in **negative form**
    you'll have some variables that are not quantified, meaning that it's usually possible to retrieve the names of the
    elements associated to those variables that do not satisfy the requirement.

2.  After the ``+`` or ``-`` there's the **name** of the requirement, which is a string between double quotes ``"..."``.
    Single quotes ``'...'`` won't work.

3.  Following the requirement name, there's the **logic expression** which is the core of the requirement.
    It is written in `First Order Logic`_, so it will evaluate to either true or false. See the `Syntax`_ for details.

4.  Last, following ``error:``, there is the **error message** that is printed when the requirement is not satisfied.
    If you have a free variable, which means a variable that is not quantified, you can print its value by putting it in the
    string between curly brackets like this: ``{myVar}``. You'll get a warning if the Model Checker can't assign a value to that variable.

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

        - ``vm has abstract.ComputingNode.cpu_cores >= 4`` is an **Attribute** Relationship, as it compares a property (``cpu_cores``) of the element ``vm`` with a constant number.
- Classes: ``class <class name>``
    - They represent a kind of element in the architecture.
    - Classes follow this naming structure ``<package>.<class>``
- Equality: ``is``, ``is not``
    - Used to set an equality (or inequality) constraint on an element variable. You can use it to assign a class to an element.
    - Example: ``vm is class abstract.VirtualMachine``
- Comparisons: ``>``,  ``>=``,  ``<``,  ``<=``,  ``==``,  ``!=``
    - You can compare attributes with constants, or attributes with attributes.
    - Example: 
        - ``vm has abstract.ComputingNode.cpu_cores >= 4`` compares attribute ``cpu_cores`` with a numeric constant.
        - ``vm1 has abstract.ComputingNode.cpu_cores >= vm2 abstract.ComputingNode.cpu_cores`` compares attribute ``cpu_cores`` of ``vm1`` with the one of ``vm2``.



Operator Precedence
-------------------

``exists``/``forall`` > ``not`` > ``or`` > ``and`` > ``implies`` > ``iff``

Grammar
=======
See the `grammar.lark`_ file on GitHub, it's written in a EBNF-like form.


.. _`Syntax Highlight`: https://marketplace.visualstudio.com/items?itemName=andreafra.piacere-domlr
.. _`First Order Logic`: https://en.wikipedia.org/wiki/First-order_logic
.. _`grammar.lark`: https://github.com/andreafra/piacere-model-checker/blob/main/mc_openapi/doml_mc/dsl_parser/grammar.lark
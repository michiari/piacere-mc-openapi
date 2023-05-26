Built-in Requirements
=====================

The DOML Model Checker verifies DOML models against a collection of requirements
devised to highlight the most common mistakes made by users when specifying cloud deployments.
Here we list and describe such requirements.

You may find examples of violations for each one of these requirements under the ``tests/doml`` directory.


VM Network Interfaces
---------------------

  All virtual machines must be connected to at least one network interface.

ID: ``vm_has_iface``

Virtual machines can communicate with other components of a deployment or with external clients
only through an appropriately configured network.
this check makes sure no virtual machines are isolated.


Concretization of Software Interfaces
-------------------------------------

  All software packages can see the interfaces they need through a common network.

ID: ``software_package_iface_net``

This check makes sure all exposed and consumed software interfaces at the application layer level
have been actually concretized through a network connection that allows the involved components
to communicate.


Duplicated Interfaces
---------------------

  There are no duplicated interfaces.

ID: ``iface_uniq``

Checks whether two or more interfaces have been assigned the same IP address.


Deployed Software Components
----------------------------

  All software components have been deployed to some node.

ID: ``all_software_components_deployed``

Makes sure that all software components specified in the application layer have been
associated to at least one node in the abstract infrastructure layer
through the currently active deployment.


Concretization of Abstract Infrastructure
-----------------------------------------

  All abstract infrastructure elements are mapped to an element in the active concretization.

ID: ``all_infrastructure_elements_deployed``

Makes sure all abstract infrastructure nodes are concretized by the currently active concretization layer.


Concrete Infrastructure Elements have a maps Association
--------------------------------------------------------

  All elements in the active concretization are mapped to some abstract infrastructure element.

ID: ``all_concrete_map_something``

Makes sure each concrete infrastructure element is mapped to a node in the Abstract Infrastructure Layer.

Network Interfaces belong to a Security Group
---------------------------------------------

  All network interfaces belong to a security group.

ID: ``security_group_must_have_iface``

Makes sure all network interfaces have been configured to belong to a security group.
This way, the user will be reminded to configure adequate rules for each network.

External Services are reached through HTTPS
-------------------------------------------

  All external SaaS can be reached only through a secure connection.

ID: ``external_services_must_have_https``

Makes sure that an HTTPS rule is enforced for a Network Interface of a Software Component that interfaces with a SaaS.
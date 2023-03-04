DOML v2.0 Reference
=============================


commons
^^^^^^^

.. _v2.0_commons_BProperty:

BProperty
"""""""""
*Inherits from* :ref:`Property <v2.0_commons_Property>`

* Attributes:
	* ``value`` [Boolean]

.. _v2.0_commons_Configuration:

Configuration
"""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``deployments`` → Deployment [0..*]

.. _v2.0_commons_DOMLElement:

DOMLElement
"""""""""""
* Associations:
	* ``annotations`` → Property [0..*]
* Attributes:
	* ``name`` [String]
	* ``description`` [String]

.. _v2.0_commons_Deployment:

Deployment
""""""""""
* Associations:
	* ``component`` → ApplicationComponent [1..1]
	* ``node`` → InfrastructureElement [1..1]

.. _v2.0_commons_FProperty:

FProperty
"""""""""
*Inherits from* :ref:`Property <v2.0_commons_Property>`

* Attributes:
	* ``value`` [String]

.. _v2.0_commons_IProperty:

IProperty
"""""""""
*Inherits from* :ref:`Property <v2.0_commons_Property>`

* Attributes:
	* ``value`` [Integer]

.. _v2.0_commons_Property:

Property
""""""""
* Associations:
	* ``reference`` → DOMLElement [0..1]
* Attributes:
	* ``key`` [String]

.. _v2.0_commons_SProperty:

SProperty
"""""""""
*Inherits from* :ref:`Property <v2.0_commons_Property>`

* Attributes:
	* ``value`` [String]

application
^^^^^^^^^^^

.. _v2.0_application_ApplicationComponent:

ApplicationComponent
""""""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`


.. _v2.0_application_ApplicationLayer:

ApplicationLayer
""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``components`` → ApplicationComponent [0..*]

.. _v2.0_application_DBMS:

DBMS
""""
*Inherits from* :ref:`SoftwareComponent <v2.0_application_SoftwareComponent>`


.. _v2.0_application_SaaS:

SaaS
""""
*Inherits from* :ref:`ApplicationComponent <v2.0_application_ApplicationComponent>`

* Associations:
	* ``exposedInterfaces`` → SoftwareInterface [0..*]
* Attributes:
	* ``licenseCost`` [String]

.. _v2.0_application_SaaSDBMS:

SaaSDBMS
""""""""
*Inherits from* :ref:`SaaS <v2.0_application_SaaS>`


.. _v2.0_application_SoftwareComponent:

SoftwareComponent
"""""""""""""""""
*Inherits from* :ref:`ApplicationComponent <v2.0_application_ApplicationComponent>`

* Associations:
	* ``exposedInterfaces`` → SoftwareInterface [0..*]
	* ``consumedInterfaces`` → SoftwareInterface [0..*]
* Attributes:
	* ``isPersistent`` [Boolean]
	* ``licenseCost`` [String]
	* ``configFile`` [String]

.. _v2.0_application_SoftwareInterface:

SoftwareInterface
"""""""""""""""""
*Inherits from* :ref:`ApplicationComponent <v2.0_application_ApplicationComponent>`

* Attributes:
	* ``endPoint`` [String]

infrastructure
^^^^^^^^^^^^^^

.. _v2.0_infrastructure_AutoScalingGroup:

AutoScalingGroup
""""""""""""""""
*Inherits from* :ref:`ComputingGroup <v2.0_infrastructure_ComputingGroup>`

* Associations:
	* ``machineDefinition`` → VirtualMachine [1..1]
	* ``deploymentNetwork`` → Network [0..1]
	* ``securityGroup`` → SecurityGroup [0..1]
* Attributes:
	* ``min`` [Integer]
	* ``max`` [Integer]
	* ``loadBalancer`` [String]

.. _v2.0_infrastructure_ComputingGroup:

ComputingGroup
""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``groupedNodes`` → ComputingNode [0..*]

.. _v2.0_infrastructure_ComputingNode:

ComputingNode
"""""""""""""
*Inherits from* :ref:`InfrastructureElement <v2.0_infrastructure_InfrastructureElement>`

* Associations:
	* ``ifaces`` → NetworkInterface [0..*]
	* ``location`` → Location [0..1]
	* ``credentials`` → Credentials [0..1]
	* ``group`` → ComputingGroup [0..1]
* Attributes:
	* ``architecture`` [String]
	* ``os`` [String]
	* ``memory_mb`` [Integer]
	* ``memory_kb`` [Integer]
	* ``storage`` [String]
	* ``cpu_count`` [Integer]
	* ``cost`` [Integer]

.. _v2.0_infrastructure_ComputingNodeGenerator:

ComputingNodeGenerator
""""""""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Attributes:
	* ``uri`` [String]
	* ``kind`` [GeneratorKind]

.. _v2.0_infrastructure_Container:

Container
"""""""""
*Inherits from* :ref:`ComputingNode <v2.0_infrastructure_ComputingNode>`

* Associations:
	* ``generatedFrom`` → ContainerImage [0..1]
	* ``hosts`` → ComputingNode [0..*]

.. _v2.0_infrastructure_ContainerImage:

ContainerImage
""""""""""""""
*Inherits from* :ref:`ComputingNodeGenerator <v2.0_infrastructure_ComputingNodeGenerator>`

* Associations:
	* ``generatedContainers`` → Container [0..*]

.. _v2.0_infrastructure_Credentials:

Credentials
"""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`


.. _v2.0_infrastructure_ExtInfrastructureElement:

ExtInfrastructureElement
""""""""""""""""""""""""
*Inherits from* :ref:`InfrastructureElement <v2.0_infrastructure_InfrastructureElement>`


.. _v2.0_infrastructure_FunctionAsAService:

FunctionAsAService
""""""""""""""""""
*Inherits from* :ref:`InfrastructureElement <v2.0_infrastructure_InfrastructureElement>`

* Associations:
	* ``ifaces`` → NetworkInterface [0..*]
* Attributes:
	* ``cost`` [Integer]

.. _v2.0_infrastructure_InfrastructureElement:

InfrastructureElement
"""""""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`


.. _v2.0_infrastructure_InfrastructureLayer:

InfrastructureLayer
"""""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``nodes`` → ComputingNode [0..*]
	* ``generators`` → ComputingNodeGenerator [0..*]
	* ``storages`` → Storage [0..*]
	* ``faas`` → FunctionAsAService [0..*]
	* ``credentials`` → Credentials [0..*]
	* ``groups`` → ComputingGroup [0..*]
	* ``securityGroups`` → SecurityGroup [0..*]
	* ``networks`` → Network [0..*]

.. _v2.0_infrastructure_InternetGateway:

InternetGateway
"""""""""""""""
*Inherits from* :ref:`NetworkInterface <v2.0_infrastructure_NetworkInterface>`


.. _v2.0_infrastructure_KeyPair:

KeyPair
"""""""
*Inherits from* :ref:`Credentials <v2.0_infrastructure_Credentials>`

* Attributes:
	* ``user`` [String]
	* ``keyfile`` [String]
	* ``algorithm`` [String]
	* ``bits`` [Integer]

.. _v2.0_infrastructure_Location:

Location
""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Attributes:
	* ``region`` [String]
	* ``zone`` [String]

.. _v2.0_infrastructure_Network:

Network
"""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``connectedIfaces`` → NetworkInterface [0..*]
	* ``igws`` → InternetGateway [0..*]
	* ``subnets`` → Subnet [0..*]
* Attributes:
	* ``protocol`` [String]
	* ``address_lb`` [Integer]
	* ``address_ub`` [Integer]

.. _v2.0_infrastructure_NetworkInterface:

NetworkInterface
""""""""""""""""
*Inherits from* :ref:`InfrastructureElement <v2.0_infrastructure_InfrastructureElement>`

* Associations:
	* ``belongsTo`` → Network [0..1]
	* ``associated`` → SecurityGroup [0..1]
* Attributes:
	* ``endPoint`` [Integer]
	* ``speed`` [String]

.. _v2.0_infrastructure_PhysicalComputingNode:

PhysicalComputingNode
"""""""""""""""""""""
*Inherits from* :ref:`ComputingNode <v2.0_infrastructure_ComputingNode>`


.. _v2.0_infrastructure_Rule:

Rule
""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Attributes:
	* ``kind`` [String]
	* ``protocol`` [String]
	* ``fromPort`` [Integer]
	* ``toPort`` [Integer]
	* ``cidr`` [String]

.. _v2.0_infrastructure_SecurityGroup:

SecurityGroup
"""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``rules`` → Rule [0..*]
	* ``ifaces`` → NetworkInterface [0..*]

.. _v2.0_infrastructure_Storage:

Storage
"""""""
*Inherits from* :ref:`InfrastructureElement <v2.0_infrastructure_InfrastructureElement>`

* Associations:
	* ``ifaces`` → NetworkInterface [0..*]
* Attributes:
	* ``label`` [String]
	* ``size_gb`` [Integer]
	* ``cost`` [Integer]

.. _v2.0_infrastructure_Subnet:

Subnet
""""""
*Inherits from* :ref:`Network <v2.0_infrastructure_Network>`

* Associations:
	* ``connectedTo`` → Network [0..1]

.. _v2.0_infrastructure_Swarm:

Swarm
"""""
*Inherits from* :ref:`ComputingGroup <v2.0_infrastructure_ComputingGroup>`

* Associations:
	* ``roles`` → SwarmRole [0..*]

.. _v2.0_infrastructure_SwarmRole:

SwarmRole
"""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``nodes`` → ComputingNode [0..*]
* Attributes:
	* ``kind`` [String]

.. _v2.0_infrastructure_UserPass:

UserPass
""""""""
*Inherits from* :ref:`Credentials <v2.0_infrastructure_Credentials>`

* Attributes:
	* ``username`` [String]
	* ``password`` [String]

.. _v2.0_infrastructure_VMImage:

VMImage
"""""""
*Inherits from* :ref:`ComputingNodeGenerator <v2.0_infrastructure_ComputingNodeGenerator>`

* Associations:
	* ``generatedVMs`` → VirtualMachine [0..*]

.. _v2.0_infrastructure_VirtualMachine:

VirtualMachine
""""""""""""""
*Inherits from* :ref:`ComputingNode <v2.0_infrastructure_ComputingNode>`

* Associations:
	* ``generatedFrom`` → VMImage [0..1]
* Attributes:
	* ``sizeDescription`` [String]

concrete
^^^^^^^^

.. _v2.0_concrete_ComputingGroup:

ComputingGroup
""""""""""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → ComputingGroup [1..1]

.. _v2.0_concrete_ConcreteElement:

ConcreteElement
"""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Attributes:
	* ``configurationScript`` [String]

.. _v2.0_concrete_ConcreteInfrastructure:

ConcreteInfrastructure
""""""""""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``providers`` → RuntimeProvider [0..*]

.. _v2.0_concrete_ContainerImage:

ContainerImage
""""""""""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → ContainerImage [0..1]

.. _v2.0_concrete_FunctionAsAService:

FunctionAsAService
""""""""""""""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → FunctionAsAService [0..1]

.. _v2.0_concrete_Network:

Network
"""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → Network [0..1]

.. _v2.0_concrete_RuntimeProvider:

RuntimeProvider
"""""""""""""""
*Inherits from* :ref:`DOMLElement <v2.0_commons_DOMLElement>`

* Associations:
	* ``vms`` → VirtualMachine [0..*]
	* ``vmImages`` → VMImage [0..*]
	* ``containerImages`` → ContainerImage [0..*]
	* ``networks`` → Network [0..*]
	* ``storages`` → Storage [0..*]
	* ``faas`` → FunctionAsAService [0..*]
	* ``group`` → ComputingGroup [0..*]

.. _v2.0_concrete_Storage:

Storage
"""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → Storage [0..1]

.. _v2.0_concrete_VMImage:

VMImage
"""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → VMImage [0..1]

.. _v2.0_concrete_VirtualMachine:

VirtualMachine
""""""""""""""
*Inherits from* :ref:`ConcreteElement <v2.0_concrete_ConcreteElement>`

* Associations:
	* ``maps`` → VirtualMachine [0..1]




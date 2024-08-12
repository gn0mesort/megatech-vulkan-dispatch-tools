# Megatech Vulkan Dispatch Python Tools

Tools for generating [Vulkan](https://registry.khronos.org/vulkan/) command dispatch tables using
[Mako](https://makotemplates.org) templates

## Library

```python
from megatech.vulkan import VulkanSpecification, VulkanCommandSet
```

`megatech-vulkan-dispatch-tools` provides a library for locating and parsing
[Vulkan XML specifications](https://github.com/KhronosGroup/Vulkan-Docs/blob/main/xml/vk.xml). Currently,
this package is focused on dispatch rather than, for example, generating custom `vulkan.h` files. This means that the
library is not aware of concepts like types or enumerations. Instead, it focuses on extracting features
(i.e., Vulkan API versions), extensions, and commands.

The primary way to use this library is by instantiating a `VulkanSpecification` object. `VulkanSpecification`s allow
clients to locate a Vulkan XML specification (either explicitly or by searching a set of system dependent locations)
and access the information contained within. `VulkanSpecification`s can also help filter Vulkan features by
marking each feature and extension as enabled or disabled.


## dispatch-table-generator

The main use-case for the `megatech.vulkan` library is to support `dispatch-table-generator`.
`dispatch-table-generator` is a simple script for templating files with information from the Vulkan specification.
As its name implies, the primary purpose of this is to generate Vulkan command dispatch tables. However, since it
processes Mako templates the exact output is very flexible. The main purpose of this application is to support my
[megatech-vulkan-dispatch](https://github.com/gn0mesort/megatech-vulkan-dispatch) library.

For more information about this script you can run:

```sh
dispatch-table-generator -h
```

### Template API

Currently, `dispatch-table-generator` passes the following objects to its input template:

- `arguments`: A list of strings, provided by the user, that are passed directly through from
  `dispatch-table-generator`. It is the responsibility of the template to determine their meaning.
- `commands`: A `VulkanCommandSet` that contains all of the Vulkan commands required by the currently enabled
  features.
- `groups`: A dictionary that maps command groups to sets of `VulkanCommand` objects. A command group is condition
  describing the set of features that must be enabled for the corresponding commands to function. Each group string
  is formatted as a C-style `#if` condition.
- `specification`: The `VulkanSpecification` object generated internally by the application.
- `buildtime`: A `datetime` object representing the start time of the template renderer in UTC.

## Testing

```sh
python3 -m pip install .[tests]
coverage run
```

## Generating Documentation

Documentation files can be generated using [Doxygen](https://www.doxygen.nl/). Just run:

```sh
doxygen Doxyfile
```

The resulting documentation is located at `build/documentation/`.

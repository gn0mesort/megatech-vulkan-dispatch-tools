# Megatech-Vulkan Dispatch Tools

This repository contains tools for my [Megatech-Vulkan Dispatch](https://github.com/gn0mesort/megatech-vulkan-dispatch)
library. Currently, those tools are a support library and a generator script both written in Python 3. This project
is similar to, but distinct from, the generator tools provided with my previous project
[VKFL](https://github.com/gn0mesort/vkfl).

## Installing

```sh
# Install directly from a local copy to your Python environment.
python3 -m pip install .

# Install with the additional testing dependencies.
python3 -m pip install .[tests]

# Install from the remote Git repository.
python3 -m pip install "megatech-vulkan-dispatch-tools @ git+https://github.com/gn0mesort/megatech-vulkan-dispatch-tools"

# Install from the remote Git repository with the additional testing dependencies.
python3 -m pip install "megatech-vulkan-dispatch-tools[tests] @ git+https://github.com/gn0mesort/megatech-vulkan-dispatch-tools"
```

You should install this package using [`pip`](https://pip.pypa.io/en/stable/). Please refer to the `pip`
[documentation](https://pip.pypa.io/en/stable/user_guide/) for more details.

## Library

```python
# Import the useful bits.
from megatech.vulkan import VulkanSpecification, VulkanCommandSet
```

The library consists of several objects that are useful for parsing
[Vulkan XML specifications](https://github.com/KhronosGroup/Vulkan-Docs/blob/main/xml/vk.xml). However, not all of
the specification is exposed through the library. Since these tools are focused on the generation of dispatch tables,
the library only exposes Vulkan features (i.e, API versions), extensions, and commands. Basically, only the absolute
minimum information from the specification is exposed by this library. For example, the library can't be used to
generate a complete copy of `vulkan_core.h`.

The main way to use this library is to instantiate a `VulkanSpecification` object. This will locate an XML
specification and parse it. I've made an effort to use a "safe" XML parser for this. However, you should still be
careful with it. You probably shouldn't parse arbitrary XML files that you found somewhere or other. Instead, you
should provide an explicit path to a known-good specification or you should allow the library to locate a
specification in a trusted system-controlled location (i.e., a specification installed by a package manager).

## dispatch-table-generator

```sh
# Display usage information for the generator.
dispatch-table-generator -h
```

To support generating dispatch tables, this repository provides an application that uses
`megatech.vulkan.VulkanSpecification` to parameterize a [Mako](https://www.makotemplates.org/) template. This means
that, despite its name, `dispatch-table-generator` can actually process all kinds of templates. Mako templates are
computer programs, like it or not, and so you must take care in validating their behavior before rendering them.
The application makes no attempt to differentiate between safe and unsafe templates. Basically, don't pull random
templates off the Web and render them. Doing so is identical to executing untrusted Python scripts you find online.

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

## Support For Vulkan SC

In theory, the library and `dispatch-table-generator` should properly handle the
[Vulkan Security Critical](https://www.khronos.org/vulkansc/) API. Invoking `dispatch-table-generator --api=vulkansc`
**should** properly extract only the Vulkan SC API. However, I haven't really tested this. Therefore, support for
Vulkan SC is experimental at best.

When Vulkan SC was added to the Vulkan XML specification, it became necessary for `VulkanSpecification` to
differentiate between API features that are only available in Vulkan or Vulkan SC. Since `VulkanSpecification` must
support this to correctly enable features, I've exposed the ability to select the desired API in
`dispatch-table-generator`. Again though, I haven't tested whether or not selecting Vulkan SC works correctly.

## Testing

```sh
# Run the library's tests and generate coverage information.
coverage run
```

Assuming that you've installed the optional `tests` dependencies, you can use
[`coverage`](https://coverage.readthedocs.io/en/7.6.1/) to run the library tests and generate a coverage report.

## Generating Documentation

```sh
# Generate HTML documentation.
doxygen Doxyfile
```

I've provided a [Doxygen](https://doxygen.nl/) configuration file in this repository. You can use this to extract the
inline API documentation and build HTML documentation from it. The HTML documentation will be written to
`build/documentation`.

## Licensing

Copyright (C) 2024 Alexander Rothman <[gnomesort@megate.ch](mailto:gnomesort@megate.ch)>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
<[https://www.gnu.org/licenses/](https://www.gnu.org/licenses/)>.

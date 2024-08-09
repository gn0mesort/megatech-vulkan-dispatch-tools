# Megatech Vulkan Dispatch Python Tools

The script used to generate headers for `libmegatech-vulkan-dispatch` is a stand-alone component. Although my
intention is that client software links with the library, there's no need to do so. Actually, the generator doesn't
even need to be used to create <span class="nowrap">C++</span> headers.

The `dispatch-table-generator` script simply accepts a [Mako](https://www.makotemplates.org/) template as input. The
input template is provided with the following:

- `commands`: A [VulkanCommandSet](#megatech.vulkan.library.VulkanCommand.VulkanCommandSet) object containing the
              global, instance, and device [VulkanCommand](#megatech.vulkan.library.VulkanCommand.VulkanCommand)s
              selected by the generator.
- `specification`: A [VulkanSpecification](#megatech.vulkan.library.VulkanSpecification.VulkanSpecification) object
                   containing a parsed Vulkan XML specification.
- `builddate`: A `datetime` object containing the current time in UTC when template rendering started.
- `arguments`: A `list[str]` containing arbitrary template arguments passed to the generator.

The template file can leverage these parameters as it sees fit.

For more information on how to run `dispatch-table-generator`, use:

```sh
dispatch-table-generator --help
```

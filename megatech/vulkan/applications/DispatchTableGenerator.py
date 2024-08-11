##
# @file DispatchTableGenerator.py
# @brief Dispatch Table Generator Application Implementation
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
from argparse import ArgumentParser, Action, RawDescriptionHelpFormatter
from pathlib import Path
from datetime import datetime, UTC
import sys

from mako.template import Template

# i.e., from megatech.vulkan import *
from .. import *

##
# @brief A simple logger.
class Logger: #pragma: no cover
    ##
    # @brief Construct a Logger.
    # @param verbose Whether or not verbose outputs should be logged.
    def __init__(self, verbose: bool):
        self.__verbose = verbose
    ##
    # @brief Unconditionally print a message.
    # @param message The message to print.
    # @param **kwargs A list of keyword arguments that will get passed on during printing.
    def output(self, message: str, **kwargs) -> None:
        print(message, **kwargs)
    ##
    # @brief Print a verbose message.
    # @param message The message to print.
    # @param **kwargs A list of keyword arguments that will get passed on during printing.
    def output_verbose(self, message: str, **kwargs) -> None:
        if self.__verbose:
            print(message, flush=True, **kwargs)
    ##
    # @brief Format a VulkanFeature object to a string and print it to verbose output.
    # @param feature The VulkanFeature to print.
    # @param **kwargs A list of keyword arguments that will get passed on during printing.
    def output_feature_verbose(self, feature: VulkanFeature, **kwargs) -> None:
        self.output_verbose(f"FEATURE: {feature.name()} v{feature.version()}", **kwargs)
        self.output_verbose(f"\tSUPPORTED FOR: {feature.supported_apis()}", **kwargs)
        self.output_verbose(f"\tDEPRECATED: {feature.deprecated()}", **kwargs)
        self.output_verbose(f"\tGUARD: {feature.to_header_guard()}", **kwargs)
    ##
    # @brief Format a VulkanCommand object to a string and print it to verbose output.
    # @param command The VulkanCommand to print.
    # @param **kwargs A list of keyword arguments that will get passed on during printing.
    def output_command_verbose(self, command: VulkanCommand, **kwargs) -> None:
        self.output_verbose(f"COMMAND: {command.name()}", **kwargs)
        self.output_verbose(f"\tLEVEL: {command.level()}", **kwargs)

##
# @brief An implementation of the dispatch-table-generator application.
class DispatchTableGenerator:
    ##
    # @brief The application version.
    version = "1.0.0"
    ##
    # @brief Construct a DispatchTableGenerator.
    # @param template_path A Path indicating where to locate the input template. This is a Mako template.
    # @param verbose A flag indicating whether or not verbose output should be logged. Defaults to False.
    # @param output_path A Path indicating the location to write output to. If this is None then the application
    #                    will write output to stdout. Defaults to None.
    # @param specification_path A Path indicating the location of a Vulkan XML specification. If this is None then
    #        a set of standard paths are searched for the specification. Defaults to None.
    # @param api_name The name of the API to include in the specification (e.g., "vulkan" or "vulkansc").
    # @param api_version The latest version of the API to enabled. This can be any valid Vulkan version string or the
    #                    special value "latest". "latest" will enable all available API versions. Defaults to "latest".
    # @param extensions A set of extension names to enable. If this set contains the special name "all" then every
    #                   extension in the specification will be enabled. Defaults to set([ "all" ]).
    # @param template_arguments An arbitrary list strings that will be passed to the template during rendering.
    #                           Defaults to [ ].
    # @param enable_deprecated A flag indicating whether or not enable deprecated features. This is True by default.
    # @param quiet A flag indicating whether or not to output warning messages.
    # @throws FileNotFoundError If the template path is None, if the template path doesn't exist, or if the
    #                           specification_path is not None and doesn't exist.
    # @throws OSError If the template path is not a file, if the output path exists and is not a file, or if the
    #                 specification path is not a file.
    def __init__(self, template_path: Path, verbose: bool = False, output_path: Path = None,
                 specification_path: Path = None, api_name: str = "vulkan", api_version: str = "latest",
                 extensions: set[str] = set([ "all" ]), template_arguments: list[str] = [ ],
                 enable_deprecated: bool = True, quiet = False):
        if template_path is None:
            raise FileNotFoundError("The template path cannot be empty.")
        elif not template_path.exists():
            raise FileNotFoundError(f"The path {template_path} does not exist.")
        elif not template_path.is_file():
            raise OSError(f"The path {template_path} exists but is not a file.")
        self.__template_path = template_path.absolute()
        self.__logger = Logger(verbose)
        self.__output_path = output_path
        if self.__output_path:
            self.__output_path = self.__output_path.absolute()
            if self.__output_path.exists() and not self.__output_path.is_file():
                raise OSError(f"The path {self.__output_path} does not refer to a regular file.")
        self.__specification_path = specification_path
        if self.__specification_path:
            self.__specification_path = self.__specification_path.absolute()
            if not self.__specification_path.exists():
                raise FileNotFoundError(f"The path {self.__specification_path} does not exist.")
            if not self.__specification_path.is_file():
                raise OSError(f"The path {self.__specification_path} does not refer to a regular file.")
        self.__api_name = api_name
        self.__api_version = api_version
        self.__extensions = extensions
        self.__template_arguments = template_arguments
        self.__enable_deprecated = enable_deprecated
        self.__quiet = quiet
    def __enabled_features(self, specification: VulkanSpecification) -> set[str]:
        enabled = set()
        self.__logger.output_verbose("\nFEATURES:\n", file=sys.stderr)
        for name in sorted(specification.features()):
            feature = specification.features()[name]
            if feature.enabled():
                enabled.add(feature.name())
                self.__logger.output_feature_verbose(feature, file=sys.stderr)
        return enabled
    def __enabled_extensions(self, specification: VulkanSpecification) -> set[str]:
        enabled = set()
        self.__logger.output_verbose("\nEXTENSIONS:\n", file=sys.stderr)
        for name in sorted(specification.extensions()):
            extension = specification.extensions()[name]
            if extension.enabled():
                enabled.add(extension.name())
                self.__logger.output_feature_verbose(extension, file=sys.stderr)
        return enabled
    ##
    # @brief Run the application.
    def run(self) -> None:
        spec = VulkanSpecification(self.__specification_path, self.__api_name, self.__api_version, self.__extensions,
                                   self.__enable_deprecated)
        self.__logger.output_verbose(f"Vulkan specification version {spec.specification_version()} located at "
                                    f"\"{spec.specification_path()}\"", file=sys.stderr)
        enabled_features = self.__enabled_features(spec)
        enabled_extensions = self.__enabled_extensions(spec)
        enabled = enabled_features | enabled_extensions
        command_set = VulkanCommandSet()
        self.__logger.output_verbose("\nCOMMANDS:\n", file=sys.stderr)
        # Process enabled features
        for name in enabled_features:
            feature = spec.features()[name]
            if feature.deprecated() and not self.__quiet:
                self.__logger.output(f"WARN: The feature \"{feature.name()}\" is deprecated.", file=sys.stderr)
            if not feature.is_satisfied(enabled):
                raise ValueError(f"The Vulkan feature \"{feature.name()}\" has an unmet dependency.")
            for requirement in feature.requirements():
                if requirement.is_satisfied(enabled):
                    for command in requirement.commands():
                        self.__logger.output_command_verbose(command, file=sys.stderr)
                        command_set.add(command)
        # Process enabled extensions
        for name in enabled_extensions:
            extension = spec.extensions()[name]
            if extension.deprecated() and not self.__quiet:
                self.__logger.output(f"WARN: The feature \"{extension.name()}\" is deprecated.", file=sys.stderr)
            if not extension.is_satisfied(enabled):
                raise ValueError(f"The Vulkan extension \"{extension.name()}\" has an unmet dependency. The required "
                                 f"dependency is \"{extension.dependency()}\".")
            for requirement in extension.requirements():
                if requirement.is_satisfied(enabled):
                    for command in requirement.commands():
                        self.__logger.output_command_verbose(command, file=sys.stderr)
                        command_set.add(command)
                # Warn the user if a requirement with commands is disabled automatically.
                elif len(requirement.commands()) > 0 and not self.__quiet:
                    self.__logger.output(f"WARN: In the extension \"{extension.name()}\", a requirement was disabled "
                                         f"because its dependency (\"{requirement.dependency()}\") was not satisfied.",
                                         file=sys.stderr)
        # Removals must be processed after everything is added. :(
        for name in enabled_features:
            feature = spec.features()[name]
            for removal in feature.removals():
                command_set.remove(command_set.find(removal))
        for name in enabled_extensions:
            extensions = spec.extensions()[name]
            for removal in extension.removals():
                command_set.remove(command_set.find(removal))
        template = Template(filename=self.__template_path.absolute().as_posix(), output_encoding="utf-8")
        source = template.render(commands=command_set, specification=spec, buildtime=datetime.now(UTC),
                                 arguments=self.__template_arguments)
        if self.__output_path is not None:
            self.__logger.output_verbose(f"Writing output to \"{self.__output_path}\".")
            with open(self.__output_path, "wb") as outfile:
                outfile.write(source)
        else:
            self.__logger.output_verbose("Writing output to standard output.")
            sys.stdout.write(source.decode(encoding="utf-8"))

### @cond
class ExtensionSetStoreAction(Action): # pragma: no cover
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Extension sets must be packed in a single string.")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        extensions = set()
        for value in values.split(","):
            if len(value) > 0:
                extensions.add(value.replace("\"", "").replace("\'", ""))
        if "all" in extensions:
            extensions = set([ "all" ])
        setattr(namespace, self.dest, extensions)

class CommaSeparatedListStoreAction(Action): # pragma: no cover
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Lists must be packed in a single string.")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        res = [ ]
        for value in values.split(","):
            if len(value) > 0:
                res.append(value.replace("\"", "").replace("\'", ""))
        setattr(namespace, self.dest, res)

class IndentedDescriptionFormatter(RawDescriptionHelpFormatter): # pragma: no cover
    def _fill_text(self, text, width, indent) -> str:
        import textwrap
        res = [ ]
        offset = ""
        for line in text.splitlines():
            offset = "    " * (len(line) - len(line.lstrip()))
            res.append(textwrap.fill(line.strip(), width, initial_indent=offset, subsequent_indent=offset))
        return "\n".join(res)

def main() -> None: # pragma: no cover
    progepilog = """
templates:
\tTemplates receive three parameters.
\targuments:
\t\tA list of strings containing any values passed to the \"--template-arguments\" option.
\tcommands:
\t\tA VulkanCommandSet containing VulkanCommand objects for every enabled command.
\tspecification:
\t\tA VulkanSpecification representing the parsed specification.
\tbuildtime:
\t\tA datetime object representing the build time in UTC.

notes:
\tIf a specification path is not explicitly provided, the application will search the following locations.
\tUnix-like systems:
\t\t$VULKAN_SDK/share/vulkan/registry/vk.xml
\t\t$HOME/.local/share/vulkan/registry/vk.xml
\t\t/usr/local/share/vulkan/registry/vk.xml
\t\t/usr/share/vulkan/registry/vk.xml
\tWindows systems:
\t\t%VULKAN_SDK%/share/vulkan/registry/vk.xml
\t\t%VULKAN_SDK_PATH%/share/vulkan/registry/vk.xml
"""
    parser = ArgumentParser(description="Generates Vulkan dispatch table objects from Mako templates.",
                            epilog=progepilog, formatter_class=IndentedDescriptionFormatter, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="Display this help message and exit.")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {DispatchTableGenerator.version}",
                        help="Display version information and exit.")
    parser.add_argument("-V", "--verbose", action="store_true", default=False, help="Display verbose output.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="A path to an output file. If you don't provide an output file, the application writes "
                             "to standard output.")
    parser.add_argument("--specification-path", type=Path,
                        help="Explicitly set the location of the desired Vulkan specification. When this option isn't "
                             "set, a set of standard paths are searched for the specification. See \"note\"s for more "
                             "details.", default=None)
    parser.add_argument("--api", type=str, default="vulkan",
                        help="The Vulkan API to enable. (e.g., \"vulkan\" or \"vulkansc\"). Defaults to \"vulkan\".")
    parser.add_argument("--api-version", type=str, default="latest",
                        help="The latest Vulkan API version (e.g., 1.0, 1.1, 1.2, etc.) to enable. "
                             "This may also be the special value \"latest\". All earlier API versions are included "
                             "with later API versions. This means that \"--api-version=1.2\" enables versions 1.1 and "
                             "1.0 as well. \"latest\", therefore, enables every API version. Defaults to \"latest\".")
    parser.add_argument("--extensions", action=ExtensionSetStoreAction, default=set([ "all" ]),
                        help="A comma separated list of Vulkan extensions to enable. This may also be the special "
                             "value \"all\" which, obviously, includes every extension in the specification. Even "
                             "when you enable an extension explicitly, it might still be disabled by the "
                             "specification. This can happen, for example, when no API supports the extension (i.e., "
                             "the supported API is explicitly listed as \"disabled\"), when the current API doesn't "
                             "support the extension, or when the extension is deprecated and "
                             "\"--no-enable-deprecated\" is specified. Defaults to \"all\".")
    parser.add_argument("-t", "--template-arguments", action=CommaSeparatedListStoreAction, default=[ ],
                        help="A comma separated list of arguments that will be passed through to the template.")
    parser.add_argument("--no-enable-deprecated", action="store_false", default=True,
                        help="Explicitly disable deprecated features.")
    parser.add_argument("-q", "--quiet", action="store_true", default=False,
                        help="Disable warning messages. This has no effect on verbose output.")
    parser.add_argument("INPUT", type=Path, help="A path to an input template file.")
    args = parser.parse_args()
    app = DispatchTableGenerator(args.INPUT, args.verbose, args.output, args.specification_path, args.api,
                                 args.api_version, args.extensions, args.template_arguments, args.no_enable_deprecated,
                                 args.quiet)
    app.run()

if __name__ == "__main__": # pragma: no cover
    main()
### @endcond
__all__ = [ "DispatchTableGenerator", "main" ]


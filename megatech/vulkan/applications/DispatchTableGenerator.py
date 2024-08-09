##
# @file DispatchTableGenerator.py
# @brief Dispatch Table Generator Application Implementation
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
from pathlib import Path
from datetime import datetime, UTC
import sys

from mako.template import Template

# i.e., from megatech.vulkan import *
from .. import *

##
# @brief A simple logger.
class Logger:
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
            print(message, **kwargs)
    ##
    # @brief Format a VulkanFeature object to a string and print it to verbose output.
    # @param feature The VulkanFeature to print.
    # @param **kwargs A list of keyword arguments that will get passed on during printing.
    def output_feature_verbose(self, feature: VulkanFeature, **kwargs) -> None:
        self.output_verbose(f"FEATURE: {feature.name()} v{feature.version()}", **kwargs)
        self.output_verbose(f"\tSUPPORTED FOR: {feature.supported_apis()}", **kwargs)
        self.output_verbose(f"\tSELECTED: {feature.enabled()}", **kwargs)
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
    # @throws FileNotFoundError If the template path is None, if the template path doesn't exist, or if the
    #                           specification_path is not None and doesn't exist.
    # @throws OSError If the template path is not a file, if the output path exists and is not a file, or if the
    #                 specification path is not a file.
    def __init__(self, template_path: Path, verbose: bool = False, output_path: Path = None,
                 specification_path: Path = None, api_name: str = "vulkan", api_version: str = "latest",
                 extensions: set[str] = set([ "all" ]), template_arguments: list[str] = [ ],
                 enable_deprecated: bool = True):
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
    ##
    # @brief Run the application.
    def run(self) -> None:
        spec = VulkanSpecification(self.__specification_path, self.__api_name, self.__api_version, self.__extensions,
                                   self.__enable_deprecated)
        self.__logger.output_verbose(f"Vulkan specification version {spec.specification_version()} located at "
                                    f"\"{spec.specification_path()}\"", file=sys.stderr)
        cmds = VulkanCommandSet()
        for name in spec.apis():
            api = spec.apis()[name]
            self.__logger.output_feature_verbose(api, file=sys.stderr)
            if api.enabled():
                for name in api.commands():
                    command = spec.commands()[name]
                    cmds.add(command)
        for name in spec.extensions():
            extension = spec.extensions()[name]
            self.__logger.output_feature_verbose(extension, file=sys.stderr)
            if extension.enabled():
                for name in extension.commands():
                    command = spec.commands()[name]
                    cmds.add(command)
        for name in spec.apis():
            api = spec.apis()[name]
            if api.enabled():
                for name in api.removals():
                    command = spec.commands()[name]
                    cmds.remove(command)
        for name in spec.extensions():
            extension = spec.extensions()[name]
            if extension.enabled():
                for name in extension.removals():
                    command = spec.commands()[name]
                    cmds.remove(command)
        for command in cmds.global_commands():
            self.__logger.output_command_verbose(command, file=sys.stderr)
        for command in cmds.instance_commands():
            self.__logger.output_command_verbose(command, file=sys.stderr)
        for command in cmds.device_commands():
            self.__logger.output_command_verbose(command, file=sys.stderr)
        self.__logger.output_verbose(f"Reading template from \"{self.__template_path.absolute()}\"", file=sys.stderr)
        template = Template(filename=self.__template_path.absolute().as_posix(), output_encoding="utf-8")
        source = template.render(commands=cmds, specification=spec, buildtime=datetime.now(UTC),
                                 arguments=self.__template_arguments)
        if self.__output_path is not None:
            self.__logger.output_verbose(f"Writing output to \"{self.__output_path}\".")
            with open(self.__output_path, "wb") as outfile:
                outfile.write(source)
        else:
            self.__logger.output_verbose("Writing output to standard output.")
            sys.stdout.write(source.decode(encoding="utf-8"))

__all__ = [ "DispatchTableGenerator" ]

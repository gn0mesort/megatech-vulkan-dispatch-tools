##
# @file VulkanSpecification.py
# @brief Vulkan Specification Objects
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
import sys
import os
from pathlib import Path

from defusedxml import ElementTree

from .VulkanVersion import VulkanVersion
from .VulkanFeature import VulkanFeature
from .VulkanCommand import VulkanCommand

##
# @brief An object representing a complete Vulkan specification.
class VulkanSpecification:
    ##
    # @brief Construct a VulkanSpecification.
    # @param path A path to an XML Vulkan specification file. If this is None then a set of standard locations will be
    #            searched.
    # @param api The name of the API to include in the specification (e.g., "vulkan" or "vulkansc").
    # @param api_version The latest version of the API to enabled. This can be any valid Vulkan version string or the
    #                    special value "latest". "latest" will enable all available API versions. Defaults to "latest".
    # @param extensions A set of extension names to enable. If this set contains the special name "all" then every
    #                   extension in the specification will be enabled. Defaults to set([ "all" ]).
    # @param enable_deprecated A flag indicating whether or not enable deprecated features. This is True by default.
    # @throw ValueError If api is None, if api_version is None, if path is None and a valid specification file isn't
    #                   found in the search path, if the specification file is not a file or doesn't exist, or if the
    #                   specification is corrupt.
    def __init__(self, path: Path, api: str, api_version: str = "latest", extensions: set[str] = set([ "all" ]),
                 enable_deprecated: bool = True):
        if api is None:
            raise ValueError("A valid API name is required.")
        if api_version is None:
            raise ValueError("A valid API version is required.")
        if extensions is None:
            extensions = set()
        # Locate the specification XML file if none is specified.
        spec_path = Path()
        if path is not None:
            spec_path = path
        else:
            search_paths = [ Path(os.environ["VULKAN_SDK"]) ] if "VULKAN_SDK" in os.environ else [ ]
            if (sys.platform == "win32" or sys.platform == "cygwin"):
                if "VULKAN_SDK_PATH" in os.environ:
                    search_paths.append(Path(os.environ["VULKAN_SDK"]))
            else:
                search_paths.extend([ Path.home().joinpath(".local"), Path("/usr/local"), Path("/usr") ])
            for search_path in search_paths:
                complete_path = search_path.joinpath("share/vulkan/registry/vk.xml").absolute()
                if complete_path.exists() and complete_path.is_file():
                    spec_path = complete_path
                else:
                    spec_path = None
            if spec_path is None:
                raise ValueError("Failed to find an appropriate Vulkan specification file.")
        if not spec_path.is_file() or not spec_path.exists():
            raise ValueError(f"The path \"{spec_path}\" does not exist or is not a regular file.")
        self.__spec_path = spec_path
        # Read the specification
        tree = None
        with open(self.__spec_path, "rb") as spec_file:
            tree = ElementTree.parse(spec_file)
        # Parse out commands
        self.__commands = { }
        for command in tree.findall("commands/command"):
            parsed = VulkanCommand(tree, command)
            self.__commands[parsed.name()] = parsed
        # Parse out Vulkan APIs
        latest_api = VulkanVersion(api_version) if api_version != "latest" else None
        self.__apis = { }
        for feature in tree.findall("feature"):
            parsed = VulkanFeature(feature)
            if api in parsed.supported_apis() and (latest_api is None or parsed.version() <= latest_api):
                parsed.enable()
            self.__apis[parsed.name()] = parsed
        # Parse out Vulkan Extensions
        self.__extensions = { }
        for feature in tree.findall("extensions/extension"):
            parsed = VulkanFeature(feature)
            if api in parsed.supported_apis() and (parsed.name() in extensions or "all" in extensions):
                deprecated = parsed.deprecated()
                if not deprecated or (enable_deprecated and deprecated):
                    parsed.enable()
            self.__extensions[parsed.name()] = parsed
        version_node = tree.find("types/type[name='VK_HEADER_VERSION']")
        if version_node is None:
            raise ValueError(f"{path} contains a corrupt specification.")
        self.__spec_version = int(version_node.find("name").tail.strip())
    ##
    # @brief Retrieve the path of the specification.
    # @details This is either the input path or the result of a search.
    # @return A Path indicating the file that was used to create this VulkanSpecification.
    def specification_path(self) -> Path:
        return self.__spec_path
    ##
    # @brief Retrieve the version of the specification.
    # @return The version of the VulkanSpecifcation.
    def specification_version(self) -> int:
        return self.__spec_version
    ##
    # @brief Retrieve a dictionary of API features.
    # @return A dictionary mapping API feature names to API features.
    def apis(self) -> dict[str, VulkanFeature]:
        return self.__apis
    ##
    # @brief Retrieve a dictionary of extension features.
    # @return A dictionary mapping extension feature names to extension features.
    def extensions(self) -> dict[str, VulkanFeature]:
        return self.__extensions
    ##
    # @brief Retrieve a dictionary of commands.
    # @return A dictionary mapping command names to commands.
    def commands(self) -> dict[str, VulkanCommand]:
        return self.__commands

__all__ = [ "VulkanSpecification" ]

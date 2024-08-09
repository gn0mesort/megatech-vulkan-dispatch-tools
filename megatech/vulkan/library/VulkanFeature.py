##
# @file VulkanFeature.py
# @brief Vulkan Feature Objects
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
from .VulkanVersion import VulkanVersion

from xml.etree import ElementTree

##
# @brief A Vulkan feature as described by the API specification.
# @details A feature can either be an API version (e.g., 1.2) or an extension (e.g., VK_KHR_swapchain). They're not
#          exactly identical in the specification but they basically contain the same information.
class VulkanFeature:
    ##
    # @brief Construct a new VulkanFeature from an XML node.
    # @param node The XML node representing the feature.
    # @throw ValueError If the XML node's tag is neither "feature" nor "extension".
    def __init__(self, node: ElementTree.Element):
        self.__deprecated = node.get("deprecatedby")
        if node.tag == "feature":
            self.__name = node.get("name")
            self.__version = VulkanVersion(node.get("number"))
            self.__supported_apis = set()
            for api in node.get("api").split(","):
                self.__supported_apis.add(api)
        elif node.tag == "extension":
            self.__name = node.get("name")
            self.__supported_apis = set()
            for api in node.get("supported").split(","):
                self.__supported_apis.add(api)
            version_node = node.find(f"require/enum/[@name='{self.__name.upper()}_SPEC_VERSION']")
            if version_node is not None and version_node.get("value") is not None:
                self.__version = VulkanVersion(f"{version_node.get("value")}.0")
            else:
                self.__version = VulkanVersion("0.0")
        else:
            raise ValueError(f"The tag \"{node.tag}\" is unrecognized.")
        self.__enabled = False
        self.__commands = set()
        for command in node.findall("require/command"):
            self.__commands.add(command.get("name"))
        self.__removals = set()
        for command in node.findall("remove/command"):
            self.__removals.add(command.get("name"))
    ##
    # @brief Retrieve the feature's name.
    # @details The exact formatting of names differs between extensions and API versions. Extensions have a name
    #          in the format "VK_X_y" (e.g., "VK_KHR_surface"). API versions have names like: VK_VERSION_1_0.
    # @return The name of the VulkanFeature.
    def name(self) -> str:
        return self.__name
    ##
    # @brief Retrieve the set of APIs that support the feature.
    # @details The supported APIs are, for example, Vulkan and Vulkan Security Critical (SC). In the future, more APIs
    #          could be added.
    # @return The set of APIs supported by the VulkanFeature.
    def supported_apis(self) -> set[str]:
        return self.__supported_apis
    ##
    # @brief Retrieve the version of the feature.
    # @details API versions obviously provide their corresponding version number (e.g., VulkanVersion("1.2")).
    #          Extensions often have a major version number with no minor version. In this case the minor version is
    #          set to 0. Some extensions may not have a version number at all, resulting in a version of 0.0.
    # @return The version of the VulkanFeature.
    def version(self) -> VulkanVersion:
        return self.__version
    ##
    # @brief Determine whether or not the feature is enabled.
    # @details Whether or not a VulkanFeature is enabled is critical to generating anything useful from the
    #          specification. In general, this library tries to only make the determination to enable a feature at the
    #          top-level. Commands don't know what features they are referenced by and features don't know whether or
    #          not they should be enabled. Instead, this determination is made by the VulkanSpecification object.
    #          Usually, features are enabled by user input, but some features will be disabled automatically if they
    #          are listed as disabled in the specification.
    # @return True if the VulkanFeature is enabled. Otherwise False.
    def enabled(self) -> bool:
        return self.__enabled
    ##
    # @brief Enable the feature.
    # @details All features are disabled by default.
    def enable(self) -> None:
        self.__enabled = True
    ##
    # @brief Disable the feature.
    # @details All features are disabled by default.
    def disable(self) -> None:
        self.__enabled = False
    ##
    # @brief Retrieve a set of command names that are referenced by the feature.
    # @return A set of command names.
    def commands(self) -> set[str]:
        return self.__commands
    ##
    # @brief Retrieve a set of command names that are explicitly removed by the feature.
    # @return A set of command names.
    def removals(self) -> set[str]:
        return self.__removals
    ##
    # @brief Determine whether or not this feature is deprecated.
    # @return True if the feature is deprecated. Otherwise False.
    def deprecated(self) -> bool:
        return bool(self.__deprecated)

__all__ = [ "VulkanFeature" ]

##
# @file VulkanCommand.py
# @brief Vulkan Command Objects
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
from enum import IntEnum

from xml.etree import ElementTree
##
# @brief An enumeration representing the three levels of Vulkan API commands.
class VulkanCommandLevel(IntEnum):
    ##
    # @brief Global level commands.
    # @details These are commands that can be used without any VkInstance or VkDevice handle behind them.
    GLOBAL = 0,
    ##
    # @brief Instance level commands.
    INSTANCE = 1,
    ##
    # @brief Device level commands.
    DEVICE = 2
    ##
    # @brief Convert a VulkanCommandLevel into a string.
    # @return A string representing the name of the enumeration value.
    def __str__(self) -> str:
        return self.name.title()

##
# @brief A Vulkan command as described by the API specification.
class VulkanCommand:
    ##
    # @brief Construct a VulkanCommand from the given XML tree using the specified XML node.
    # @details For the most part, only the node is inspected. However, Vulkan allows some commands to be aliased.
    #          When this is the case, it is necessary to retrieve the actual command information from the tree.
    #          Aliased commands only contain their name which is insufficient to determine the level of the command.
    # @param tree The XML tree that the command belongs to.
    # @param node The element in the XML tree that represents the command specifically.
    # @throw ValueError If either tree or node is None, if the XML tree is corrupt, if the command's name does not
    #                   begin with the string "vk", or if the level of the command cannot be determined.
    def __init__(self, tree: ElementTree.ElementTree, node: ElementTree.Element):
        if tree is None:
            raise ValueError("\"tree\" cannot be None.")
        if node is None:
            raise ValueError("\"node\" cannot be None.")
        aliased = node.get("alias")
        if aliased:
            self.__name = node.get("name")
            node = tree.find(f"commands/command/proto/name[.='{aliased}']/../..")
        else:
            self.__name = node.findtext("proto/name")
        if self.__name is None or node is None:
            raise ValueError("The input specification is corrupt.")
        if not self.__name.startswith("vk"):
            raise ValueError("Command names must begin with the \"vk\" namespace identifier.")
        global_commands = ("vkEnumerateInstanceVersion", "vkEnumerateInstanceExtensionProperties",
                           "vkEnumerateInstanceLayerProperties", "vkCreateInstance", "vkGetInstanceProcAddr")
        if self.__name in global_commands:
            self.__level = VulkanCommandLevel.GLOBAL
        else:
            owner = node.findtext("param[1]/type")
            if owner in ("VkInstance", "VkPhysicalDevice"):
                self.__level = VulkanCommandLevel.INSTANCE
            elif owner in ("VkDevice", "VkCommandBuffer", "VkQueue"):
                self.__level = VulkanCommandLevel.DEVICE
            else:
                raise ValueError(f"The command \"{self.__name}\" appears to have no level.")
    ##
    # @brief Retrieve the VulkanCommand's name.
    # @return The name of the VulkanCommand.
    def name(self) -> str:
        return self.__name
    ##
    # @brief Retrieve the VulkanCommand's level.
    # @return The level of the VulkanCommand.
    def level(self) -> VulkanCommandLevel:
        return self.__level
    ##
    # @brief Hash a VulkanCommand.
    # @details This is useful for creating sets of VulkanCommands.
    # @return The hash of the VulkanCommand's name (which must otherwise be unique in the specification.
    def __hash__(self) -> int:
        return hash(self.__name)
    ##
    # @brief Compare two VulkanCommands to determine if the left-hand command is less than the right.
    # @details This is a comparison of the command names only. Primarily, this is useful for sorting lists of
    #          commands. This is desirable to ensure source files that are generated from command lists retain their
    #          ordering.
    # @param other The VulkanCommand to compare to.
    # @return True if the left-hand command is less than the right. Otherwise False.
    def __lt__(self, other) -> bool:
        return self.__name < other.__name
    ##
    # @brief Compare two VulkanCommands for equality.
    # @param other The VulkanCommand to compare to.
    # @return True if the left-hand command has the same name and level as the right. Otherwise False.
    def __eq__(self, other) -> bool:
        return self.__level == other.__level and self.__name == other.__name
##
# @brief A specialized container for holding sets of VulkanCommand objects.
class VulkanCommandSet:
    ##
    # @brief Constructs a new VulkanCommandSet without any commands in it.
    def __init__(self):
        self.__data = [ set(), set(), set() ]
    ##
    # @brief Add a VulkanCommand to the set.
    # @details The command will be stored based on its level.
    # @param command The VulkanCommand to store.
    def add(self, command: VulkanCommand) -> None:
        self.__data[int(command.level())].add(command)
    ##
    # @brief Remove a VulkanCommand from the set.
    # @details If the requested command is not present in the set then this is a noop.
    # @param command The VulkanCommand to remove.
    def remove(self, command: VulkanCommand) -> None:
        if command in self:
            self.__data[int(command.level())].remove(command)
    ##
    # @brief Retrieve the set of global commands from the command set.
    # @return A set of global VulkanCommands from the VulkanCommandSet.
    def global_commands(self) -> set[VulkanCommand]:
        return self.__data[int(VulkanCommandLevel.GLOBAL)]
    ##
    # @brief Retrieve the set of instance commands from the command set.
    # @return A set of instance VulkanCommands from the VulkanCommandSet.
    def instance_commands(self) -> set[VulkanCommand]:
        return self.__data[int(VulkanCommandLevel.INSTANCE)]
    ##
    # @brief Retrieve the set of device commands from the command set.
    # @return A set of device VulkanCommands from the VulkanCommandSet.
    def device_commands(self) -> set[VulkanCommand]:
        return self.__data[int(VulkanCommandLevel.DEVICE)]
    ##
    # @brief Determine if the command set is empty.
    # @return True if the set is empty. Otherwise False.
    def empty(self) -> bool:
        return len(self) == 0
    ##
    # @brief Determine if the command set contains a VulkanCommand.
    # @param command The VulkanCommand to search for.
    # @return True if the input command is a member of the set. Otherwise False.
    def __contains__(self, command: VulkanCommand) -> bool:
        return command in self.__data[0] or command in self.__data[1] or command in self.__data[2]
    ##
    # @brief Determine the length of the command set.
    # @return The length of the command set.
    def __len__(self) -> int:
        return len(self.__data[0]) + len(self.__data[1]) + len(self.__data[2])

__all__ = [ "VulkanCommandLevel", "VulkanCommand", "VulkanCommandSet" ]

##
# @file VulkanFeature.py
# @brief Vulkan Feature Objects
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
from .VulkanVersion import VulkanVersion
from .VulkanCommand import VulkanCommand

import re
from xml.etree import ElementTree

### @cond INTERNAL
##
# @brief A generic string tokenizer.
# @details This is used to break Vulkan specification dependencies into individual tokens. Specializations provide
#          A terminator character that separates each recognized token.
class Tokenizer:
    ##
    # @brief Construct a Tokenizer with the given text.
    # @param text A string containing the text to tokenize.
    # @throw ValueError if @ref text is `None`.
    def __init__(self, text: str):
        if text is None:
            raise ValueError("Tokenizers cannot be constructed without data.")
        self.__text = text
        self.__stack = [ ]
        self.__begin = 0
        self.__end = 0
        self._terminator = " "
    def __consume(self) -> bool:
        if self.__end >= len(self.__text):
            if len(self.__stack) > 0:
                raise ValueError(f"The Tokenizer found an unmatched \"(\" at the index {self.__stack[-1]}.")
            return False
        if self.__text[self.__end] == "(":
            self.__stack.append(self.__end)
            self.__end += 1
            return True
        if self.__text[self.__end] == ")":
            if len(self.__stack) < 1:
                raise ValueError(f"The Tokenizer found an unmatched \")\" at the index {self.__end}.")
            self.__stack.pop()
            self.__end += 1
            return True
        if self.__text[self.__end] == self._terminator and len(self.__stack) < 1:
            return False
        if self.__end >= len(self.__text):
            if len(self.__stack) > 0:
                raise ValueError(f"The Tokenizer found an unmatched \"(\" at the index {self.__stack[-1]}.")
            return False
        self.__end += 1
        return True
    ##
    # @brief Retrieve the base text from a Tokenizer.
    # @return The original input text.
    def text(self) -> str:
        return self.__text
    ##
    # @brief Determine whether or not a Tokenizer has finished processing.
    # @return `True` if there are still more characters to process. Otherwise `False`
    def has_more_characters(self) -> bool:
        return self.__text[self.__begin :] != ""
    ##
    # @brief Retrieve the next token from a Tokenizer.
    # @return The next available token.
    # @throw ValueError if there are any unmatched braces in the next token.
    def next_token(self) -> str:
        while self.__consume():
            pass
        res = self.__text[self.__begin : self.__end]
        self.__begin = self.__end + 1
        self.__end = self.__begin
        return res
    ##
    # @brief Reset a Tokenizer to its initial state.
    def reset(self) -> None:
        self.__begin = 0
        self.__end = 0
        self.__stack = [ ]

##
# @brief A Tokenizer that uses the `","` character as a terminator.
class CommaTokenizer(Tokenizer):
    ##
    # @brief Construct a Tokenizer with the given text.
    # @param text A string containing the text to tokenize.
    # @throw ValueError if @ref text is `None`.
    def __init__(self, text: str):
        super().__init__(text)
        self._terminator = ","

##
# @brief A Tokenizer that uses the `"+"` character as a terminator.
class PlusTokenizer(Tokenizer):
    ##
    # @brief Construct a Tokenizer with the given text.
    # @param text A string containing the text to tokenize.
    # @throw ValueError if @ref text is `None`.
    def __init__(self, text: str):
        super().__init__(text)
        self._terminator = "+"

##
# @brief Completely flush a Tokenizer.
# @param tokenizer A Tokenizer object to flush.
# @return A `list[str]` containing all the remaining tokens.
def _tokenize(tokenizer: Tokenizer) -> list[str]:
    tokens = [ ]
    while tokenizer.has_more_characters():
        tokens.append(tokenizer.next_token())
    return tokens

##
# @brief The inner loop of the dependency checker.
# @details This processes subtokens in a Vulkan dependency by calling @ref _check_dependencies.
# @param tokens A `list[str]` of input tokens.
# @param features A `set[str]` of enabled Vulkan feature names.
# @return A `list[bool]` indicating whether or not each corresponding token in @ref tokens is satisfied.
def _check_dependencies_loop(tokens: list[str], features: set[str]) -> list[bool]:
    res = [ ]
    for token in tokens:
        if token.startswith("("):
            res.append(_check_dependencies(token[1 : len(token) - 1], features))
        else:
            res.append(_check_dependencies(token, features))
    return res
##
# @brief Check a Vulkan dependency.
# @param token A string containing the dependency to check.
# @param features A `set[str]` containing the names of all enabled Vulkan features.
# @return `True` if the dependency is satisfied. Otherwise `False`.
def _check_dependencies(token: str, features: set[str]) -> bool:
    tokens = _tokenize(CommaTokenizer(token))
    if len(tokens) == 1:
        tokens = _tokenize(PlusTokenizer(tokens[0]))
        if len(tokens) == 1:
            return tokens[0] in features
        else:
            res = _check_dependencies_loop(tokens, features)
            return res.count(True) == len(res)
    res = _check_dependencies_loop(tokens, features)
    return True in res

##
# @brief The inner loop of the header guard generator.
# @details This is basically the same as the inner loop of the dependency checker.
# @param tokens A `list[str]` of input tokens.
# @return A `list[str]` of header guard conditions suitable for use in a C-style `#if` condition.
def _to_header_guard_loop(tokens: list[str]) -> list[str]:
    res = [ ]
    for token in tokens:
        if token.startswith("("):
            res.append(f"({_to_header_guard(token[1 : len(token) - 1])})")
        else:
            res.append(_to_header_guard(token))
    return res

##
# @brief Generate a header guard from a Vulkan dependency.
# @param tokens A `list[str]` of input tokens.
# @return A string of header guard conditions suitable for use in a C-style `#if` condition.
def _to_header_guard(subtoken: str) -> str:
    tokens = _tokenize(CommaTokenizer(subtoken))
    if len(tokens) == 1:
        tokens = _tokenize(PlusTokenizer(tokens[0]))
        if len(tokens) == 1:
            return f"defined({tokens[0]})"
        else:
            return " && ".join(_to_header_guard_loop(tokens))
    return " || ".join(_to_header_guard_loop(tokens))
### @endcond

##
# @brief A Vulkan feature requirement as described by the API specification.
# @details Requirements are descriptions of types and functions that a given feature introduces.
#          A feature might have many requirements, and each requirement can have its own dependencies.
#
#          The VulkanRequirement class is useful, primarily, for managing which VulkanCommands are available to
#          templates during output generation. For example, the VK_KHR_swapchain feature has several conditional
#          requirements. The corresponding commands should only be enabled when their dependencies are met.
class VulkanRequirement:
    ##
    # @brief Construct a VulkanRequirement.
    # @param node An XML specification element that describes the requirement.
    # @param commands A `dict[str, VulkanCommand]` that will be used to resolve each required command name to a
    #                 VulkanCommand object.
    # @throws ValueError if node is `None`.
    def __init__(self, node: ElementTree.Element, commands: dict[str, VulkanCommand]):
        if node is None:
            raise ValueError("The input node must be set.")
        self.__commands = set()
        # Resolve Vulkan command names to objects
        for command in node.findall("command"):
            self.__commands.add(commands[command.get("name")])
        self.__dependency = node.get("depends", default="")
    ##
    # @brief Retrieve the set of VulkanCommands required by VulkanRequirement.
    # @return A `set[VulkanCommand]` containing all of the required commands.
    def commands(self) -> set[VulkanCommand]:
        return self.__commands
    ##
    # @brief Retrieve the VulkanRequirement's dependency string.
    # @return A Vulkan dependency string or the empty string. Empty strings represent unconditional requirements.
    def dependency(self) -> str:
        return self.__dependency
    ##
    # @brief Determine whether or not the VulkanRequirement's dependency is satisfied.
    # @param features A `set[str]` of enabled Vulkan feature names.
    # @return `True` if the dependency is completely satisfied. Otherwise `False`.
    def is_satisfied(self, features: set[str]) -> bool:
        if self.__dependency == "":
            return True
        return _check_dependencies(self.__dependency, features)
    ##
    # @brief Retrieve a C-style header guard string that is equivalent to the VulkanRequirement's dependency.
    # @return A header guard string that is compatible with a C-style `#if` condition.
    def to_header_guard(self) -> str:
        return _to_header_guard(self.__dependency)

##
# @brief A Vulkan feature as described by the API specification.
# @details A feature can either be an API version (e.g., 1.2) or an extension (e.g., VK_KHR_swapchain). They're not
#          exactly identical in the specification but they basically contain the same information.
class VulkanFeature:
    ##
    # @brief Construct a new VulkanFeature from an XML node.
    # @param node The XML node representing the feature.
    # @param commands A `dict[str, VulkanCommand]` to use when resolving Vulkan command names to their object
    #                 representations.
    # @throw ValueError If the XML node's tag is neither "feature" nor "extension".
    def __init__(self, node: ElementTree.Element, commands: dict[str, VulkanCommand]):
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
        self.__dependency = node.get("depends", default="")
        self.__enabled = False
        self.__requirements = [ ]
        for required in node.findall("require[command]"):
            self.__requirements.append(VulkanRequirement(required, commands))
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
    # @brief Retrieve a list of the feature's requirements.
    # @return A `list[VulkanRequirement]` representing all possible requirements of the feature.
    def requirements(self) -> list[VulkanRequirement]:
        return self.__requirements
    ##
    # @brief Retrieve the feature's dependency.
    # @details Vulkan dependencies are specified as a sequence of logical **AND** and **OR** operators. In the
    #          specification's syntax the **AND** operator is `+` and the **OR** operator is `,`. Dependencies can
    #          also include parenthesis which enforce the precedence of any dependencies they contain. That is to say,
    #          parenthesis are resolved from bottom to top as you would expect in arithmetic. A valid dependency
    #          string might look like:
    #
    #          @code
    #            (((VK_KHR_get_physical_device_properties2,VK_VERSION_1_1)+VK_KHR_synchronization2),VK_VERSION_1_3)+VK_KHR_pipeline_library+VK_KHR_spirv_1_4
    #          @endcode
    #
    #          Such a dependency is satisfied when:
    #
    #          - VK_KHR_get_physical_device_properties2 **OR** VK_VERSION_1_1 is enabled **AND**
    #            VK_KHR_synchronization2 is enabled.
    #
    #          **OR**
    #
    #          - VK_VERSION_1_3 is enabled.
    #
    #          **AND**
    #
    #          - VK_KHR_pipeline_library is enabled.
    #
    #          **AND**
    #
    #        - VK_KHR_spirv_1_4 is enabled.
    #
    # @return A string representing the feature's Vulkan dependency or an empty string for unconditional features.
    def dependency(self) -> str:
        return self.__dependency
    ##
    # @brief Retrieve a set of command names that are explicitly removed by the feature.
    # @return A set of command names.
    def removals(self) -> set[str]:
        return self.__removals
    ##
    # @brief Determine if a feature's dependency is satisfied.
    # @return `True` if the dependency is satisfied. Otherwise `False`.
    def is_satisfied(self, features: set[str]) -> bool:
        if self.__dependency == "":
            return True
        return _check_dependencies(self.__dependency, features)
    ##
    # @brief Retrieve a C-style header guard string that is equivalent to the features's dependency.
    # @return A header guard string that is compatible with a C-style `#if` condition.
    def to_header_guard(self) -> str:
        base = f"defined({self.__name})"
        if self.__dependency != "":
            return " && ".join([ base, _to_header_guard(self.__dependency) ])
        return base
    ##
    # @brief Determine whether or not this feature is deprecated.
    # @return True if the feature is deprecated. Otherwise False.
    def deprecated(self) -> bool:
        return bool(self.__deprecated)

__all__ = [ "VulkanFeature", "VulkanRequirement" ]

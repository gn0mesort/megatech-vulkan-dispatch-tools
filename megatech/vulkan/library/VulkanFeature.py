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

class Tokenizer:
    def __init__(self, text: str):
        if text is None:
            raise ValueError("Tokenizer's cannot be constructed without data.")
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
    def text(self) -> str:
        return self.__text
    def has_more_characters(self) -> bool:
        return self.__text[self.__begin :] != ""
    def next_token(self) -> str:
        while self.__consume():
            pass
        res = self.__text[self.__begin : self.__end]
        self.__begin = self.__end + 1
        self.__end = self.__begin
        return res
    def reset(self) -> None:
        self.__begin = 0
        self.__end = 0
        self.__stack = [ ]

class CommaTokenizer(Tokenizer):
    def __init__(self, text: str):
        super().__init__(text)
        self._terminator = ","

class PlusTokenizer(Tokenizer):
    def __init__(self, text: str):
        super().__init__(text)
        self._terminator = "+"

def _tokenize(tokenizer: Tokenizer) -> list[str]:
    tokens = [ ]
    while tokenizer.has_more_characters():
        tokens.append(tokenizer.next_token())
    return tokens

def _process_subtokens(subtoken: str, features: set[str]) -> bool:
    res = [ ]
    tokens = _tokenize(CommaTokenizer(subtoken))
    if len(tokens) == 1:
        tokens = _tokenize(PlusTokenizer(tokens[0]))
        if len(tokens) == 1:
            return tokens[0] in features
        else:
            for token in tokens:
                if token.startswith("("):
                    res.append(_process_subtokens(token[1 : len(token) - 1], features))
                else:
                    res.append(_process_subtokens(token, features))
            return res.count(True) == len(res)
    for token in tokens:
        if token.startswith("("):
            res.append(_process_subtokens(token[1 : len(token) - 1], features))
        else:
            res.append(_process_subtokens(token, features))
    return True in res

def _to_header_guard(subtoken: str) -> str:
    res = [ ]
    tokens = _tokenize(CommaTokenizer(subtoken))
    if len(tokens) == 1:
        tokens = _tokenize(PlusTokenizer(tokens[0]))
        if len(tokens) == 1:
            return f"defined({tokens[0]})"
        else:
            for token in tokens:
                if token.startswith("("):
                    res.append(f"({_to_header_guard(token[ 1: len(token) - 1])})")
                else:
                    res.append(_to_header_guard(token))
            return " && ".join(res)
    for token in tokens:
        if token.startswith("("):
            res.append(f"({_to_header_guard(token[1 : len(token) - 1])})")
        else:
            res.append(_to_header_guard(token))
    return " || ".join(res)

class VulkanRequirement:
    def __init__(self, node: ElementTree.Element, commands: dict[str, VulkanCommand]):
        if node is None:
            raise ValueError("The input node must be set.")
        self.__commands = set()
        # Resolve Vulkan command names to objects
        for command in node.findall("command"):
            self.__commands.add(commands[command.get("name")])
        self.__dependency = node.get("depends")
        if self.__dependency is None:
            self.__dependency = ""
        self.__enabled = False
    def commands(self) -> set[VulkanCommand]:
        return self.__commands
    def dependency(self) -> str:
        return self._dependency
    def is_satisfied(self, features: set[str]) -> bool:
        if self.__dependency == "":
            return True
        return _process_subtokens(self.__dependency, features)
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

    def requirements(self) -> list[VulkanRequirement]:
        return self.__requirements
    def dependency(self) -> set[str]:
        return self.__dependency
    ##
    # @brief Retrieve a set of command names that are explicitly removed by the feature.
    # @return A set of command names.
    def removals(self) -> set[str]:
        return self.__removals
    def is_satisfied(self, features: set[str]) -> bool:
        if self.__dependency == "":
            return True
        return _process_subtokens(self.__dependency, features)
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

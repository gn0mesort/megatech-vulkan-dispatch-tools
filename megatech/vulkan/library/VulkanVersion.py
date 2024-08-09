##
# @file VulkanVersion.py
# @brief Vulkan API Version Objects
# @author Alexander Rothman <gnomesort@megate.ch>
# @date 2024
# @copyright AGPL-3.0-or-later
import re

##
# @brief A version number as represented by the Vulkan API specification.
# @details This is a version number of the format "X.Y" as used to represent various versions in the XML specification.
#          It is not identical to the binary encoding used for versions in the actual API (e.g., the encoding of
#          VK_API_VERSION_1_0).
class VulkanVersion:
    ##
    # @brief Construct a new VulkanVersion from a version string.
    # @param version A string value that represents the version. This must begin with an "X.Y" version but any data
    #                after that is simply ignored. This means that, "Ax.1.2" is not a valid version, but "1.2.Ax" is
    #                a valid version (equivalent to version 1.2).
    # @throw ValueError If the version string is empty or doesn't match the version format for any reason.
    def __init__(self, version: str):
        if version is None:
            raise ValueError(f"\"{version}\" is not a valid Vulkan version string.")
        match = re.match(r"^\s*(\d+)\.(\d+)", version)
        if match:
            self.__major = int(match.group(1), 10)
            self.__minor = int(match.group(2), 10)
        else:
            raise ValueError(f"\"{version}\" is not a valid Vulkan version string.")
    ##
    # @brief Retrieve the major version number.
    # @return An integer representing the major version of the VulkanVersion.
    def major(self) -> int:
        return self.__major
    ##
    # @brief Retrieve the minor version number.
    # @return An integer representing the minor version of the VulkanVersion.
    def minor(self) -> int:
        return self.__minor
    ##
    # @brief Perform a 3-way comparison between two VulkanVersions.
    # @param other The VulkanVersion to compare to.
    # @return 0 if the two versions are equal. >0 if the left-hand version is greater than the right.
    #         <0 if the left-hand version is less than the right.
    def compare(self, other) -> int:
        res = self.__major - other.__major
        if res == 0:
            res = self.__minor - other.__minor
        return res
    ##
    # @brief Compare two VulkanVersions for equality.
    # @param other The VulkanVersion to compare to.
    # @return True if the two versions are equal. Otherwise False.
    def __eq__(self, other) -> bool:
        return self.compare(other) == 0
    ##
    # @brief Compare two VulkanVersions to determine if the left-hand version is less than the right.
    # @param other The VulkanVersion to compare to.
    # @return True if the left-hand version is less than the right. Otherwise False.
    def __lt__(self, other) -> bool:
        return self.compare(other) < 0
    ##
    # @brief Compare two VulkanVersions to determine if the left-hand version is less than or equal to the right.
    # @param other The VulkanVersion to compare to.
    # @return True if the left-hand version is less than or equal to the right. Otherwise False.
    def __le__(self, other) -> bool:
        return self.compare(other) <= 0
    ##
    # @brief Compare two VulkanVersions to determine if the left-hand version is greater than the right.
    # @param other The VulkanVersion to compare to.
    # @return True if the left-hand version is greater than the right. Otherwise False.
    def __gt__(self, other) -> bool:
        return self.compare(other) > 0
    ##
    # @brief Compare two VulkanVersions to determine if the left-hand version is greater than or equal to the right.
    # @param other The VulkanVersion to compare to.
    # @return True if the left-hand version is greater than or equal to the right. Otherwise False.
    def __ge__(self, other) -> bool:
        return self.compare(other) >= 0
    ##
    # @brief Convert a VulkanVersion into a string.
    # @return A string of the format "X.Y" representing the VulkanVersion.
    def __str__(self) -> str:
        return f"{self.__major}.{self.__minor}"

__all__ = [ "VulkanVersion" ]

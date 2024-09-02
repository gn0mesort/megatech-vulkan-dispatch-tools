#!/usr/bin/env python3

import unittest
import tempfile
import os
import contextlib

from io import StringIO
from pathlib import Path

from defusedxml import ElementTree

from megatech.vulkan.applications import DispatchTableGenerator
from megatech.vulkan import *

TEMPORARY_SPEC = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_0" number="1.0" comment="Vulkan core API interface definitions">
        <require comment="Device initialization">
            <command name="vkGetInstanceProcAddr"/>
        </require>
    </feature>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_1" number="1.1" comment="Vulkan core API interface definitions">
    </feature>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_2" number="1.2" comment="Vulkan 1.2 core API interface definitions.">
        <require comment="Promoted from VK_EXT_host_query_reset (extension 262)">
    <command name="vkResetQueryPool"/>
        </require>
    </feature>
    <extensions comment="Vulkan extension interface definitions">
        <extension name="VK_KHR_surface" number="1" type="instance" author="KHR" contact="James Jones @cubanismo,Ian Elliott @ianelliottus" supported="vulkan,vulkansc" ratified="vulkan,vulkansc">
            <require>
                <enum value="25" name="VK_KHR_SURFACE_SPEC_VERSION"/>
                <command name="vkDestroySurfaceKHR"/>
            </require>
            <require depends="(((VK_KHR_get_physical_device_properties2,VK_VERSION_1_1)+VK_KHR_synchronization2),VK_VERSION_1_3)+VK_KHR_pipeline_library+VK_KHR_spirv_1_4">
            </require>
        </extension>
        <extension name="VK_EXT_host_query_reset" number="262" author="EXT" contact="Bas Nieuwenhuizen @BNieuwenhuizen" supported="vulkan" type="device" depends="VK_KHR_get_physical_device_properties2,VK_VERSION_1_1" promotedto="VK_VERSION_1_2">
            <require>
                <command name="vkResetQueryPoolEXT"/>
            </require>
        </extension>
        <extension name="VK_EXT_debug_report" number="12" type="instance" author="GOOGLE" contact="Courtney Goeltzenleuchter @courtney-g" specialuse="debugging" supported="vulkan" deprecatedby="VK_EXT_debug_utils">
            <require>
                <command name="vkCreateDebugReportCallbackEXT"/>
                <command name="vkDestroyDebugReportCallbackEXT"/>
                <command name="vkDebugReportMessageEXT"/>
            </require>
        </extension>
       <extension name="VK_KHR_get_physical_device_properties2" number="60" type="instance" author="KHR" contact="Jeff Bolz @jeffbolznv" supported="vulkan" promotedto="VK_VERSION_1_1" ratified="vulkan">
       </extension>
    </extensions>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>PFN_vkVoidFunction</type> <name>vkGetInstanceProcAddr</name></proto>
            <param optional="true"><type>VkInstance</type> <name>instance</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pName</name></param>
        </command>
       <command>
            <proto><type>void</type> <name>vkDestroySurfaceKHR</name></proto>
            <param><type>VkInstance</type> <name>instance</name></param>
            <param optional="true" externsync="true"><type>VkSurfaceKHR</type> <name>surface</name></param>
            <param optional="true">const <type>VkAllocationCallbacks</type>* <name>pAllocator</name></param>
        </command>
        <command>
            <proto><type>void</type> <name>vkResetQueryPool</name></proto>
            <param><type>VkDevice</type> <name>device</name></param>
            <param><type>VkQueryPool</type> <name>queryPool</name></param>
            <param><type>uint32_t</type> <name>firstQuery</name></param>
            <param><type>uint32_t</type> <name>queryCount</name></param>
        </command>
        <command name="vkResetQueryPoolEXT" alias="vkResetQueryPool"/>
       <command successcodes="VK_SUCCESS" errorcodes="VK_ERROR_OUT_OF_HOST_MEMORY">
            <proto><type>VkResult</type> <name>vkCreateDebugReportCallbackEXT</name></proto>
            <param><type>VkInstance</type> <name>instance</name></param>
            <param>const <type>VkDebugReportCallbackCreateInfoEXT</type>* <name>pCreateInfo</name></param>
            <param optional="true">const <type>VkAllocationCallbacks</type>* <name>pAllocator</name></param>
            <param><type>VkDebugReportCallbackEXT</type>* <name>pCallback</name></param>
        </command>
        <command>
            <proto><type>void</type> <name>vkDestroyDebugReportCallbackEXT</name></proto>
            <param><type>VkInstance</type> <name>instance</name></param>
            <param optional="true" externsync="true"><type>VkDebugReportCallbackEXT</type> <name>callback</name></param>
            <param optional="true">const <type>VkAllocationCallbacks</type>* <name>pAllocator</name></param>
        </command>
        <command>
            <proto><type>void</type> <name>vkDebugReportMessageEXT</name></proto>
            <param><type>VkInstance</type> <name>instance</name></param>
            <param><type>VkDebugReportFlagsEXT</type> <name>flags</name></param>
            <param><type>VkDebugReportObjectTypeEXT</type> <name>objectType</name></param>
            <param objecttype="objectType"><type>uint64_t</type> <name>object</name></param>
            <param><type>size_t</type> <name>location</name></param>
            <param><type>int32_t</type> <name>messageCode</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pLayerPrefix</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pMessage</name></param>
        </command>
    </commands>
    <types comment="Vulkan type definitions">
        <type api="vulkan" category="define">// Version of this file
        #define <name>VK_HEADER_VERSION</name> 12246445</type>
    </types>
</registry>
""".strip()

EVIL_SPEC_NO_VK = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>void</type> <name>glEvilCommand</name></proto>
            <param><type>GLuint</type> <name>buffer</name></param>
        </command>
    </commands>
</registry>
""".strip()

EVIL_SPEC_NO_LEVEL = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>void</type> <name>vkEvilCommand</name></proto>
            <param><type>GLuint</type> <name>buffer</name></param>
        </command>
    </commands>
</registry>
""".strip()

EVIL_SPEC_MISSING_ALIAS = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <commands comment="Vulkan command definitions">
        <command name="vkEvilAliasedCommandKHR" alias="vkEvilAliasedCommand" />
    </commands>
</registry>
""".strip()

EVIL_SPEC_BAD_DEPENDENCY = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_0" number="1.0" comment="Vulkan core API interface definitions">
        <require comment="Device initialization">
            <command name="vkGetInstanceProcAddr"/>
        </require>
    </feature>
    <extensions>
        <extension name="VK_KHR_surface" number="1" type="instance" author="KHR" contact="James Jones @cubanismo,Ian Elliott @ianelliottus" supported="vulkan,vulkansc" ratified="vulkan,vulkansc" depends="VK_KHR_doesnt_exist">
        </extension>
    </extensions>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>PFN_vkVoidFunction</type> <name>vkGetInstanceProcAddr</name></proto>
            <param optional="true"><type>VkInstance</type> <name>instance</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pName</name></param>
        </command>
    </commands>
    <types comment="Vulkan type definitions">
        <type api="vulkan" category="define">// Version of this file
        #define <name>VK_HEADER_VERSION</name> 12246445</type>
    </types>
</registry>
""".strip()

EVIL_SPEC_BAD_FEATURE_DEPENDENCY = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_0" number="1.0" comment="Vulkan core API interface definitions" depends="VK_VERSION_0_125">
        <require comment="Device initialization">
            <command name="vkGetInstanceProcAddr"/>
        </require>
    </feature>
    <extensions>
        <extension name="VK_KHR_surface" number="1" type="instance" author="KHR" contact="James Jones @cubanismo,Ian Elliott @ianelliottus" supported="vulkan,vulkansc" ratified="vulkan,vulkansc">
        </extension>
    </extensions>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>PFN_vkVoidFunction</type> <name>vkGetInstanceProcAddr</name></proto>
            <param optional="true"><type>VkInstance</type> <name>instance</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pName</name></param>
        </command>
    </commands>
    <types comment="Vulkan type definitions">
        <type api="vulkan" category="define">// Version of this file
        #define <name>VK_HEADER_VERSION</name> 12246445</type>
    </types>
</registry>
""".strip()


NEUTRAL_SPEC_BAD_REQUIREMENT_DEPENDENCY = """
<?xml version="1.0" encoding="UTF-8"?>
<registry>
    <feature api="vulkan,vulkansc" name="VK_VERSION_1_0" number="1.0" comment="Vulkan core API interface definitions">
        <require comment="Device initialization">
            <command name="vkGetInstanceProcAddr"/>
        </require>
    </feature>
    <extensions>
        <extension name="VK_KHR_surface" number="1" type="instance" author="KHR" contact="James Jones @cubanismo,Ian Elliott @ianelliottus" supported="vulkan,vulkansc" ratified="vulkan,vulkansc">
            <require depends="VK_KHR_doesnt_exist">
                <command name="vkGetInstanceProcAddr" />
            </require>
            <require depends="VK_KHR_doesnt_exist">
            </require>
        </extension>
    </extensions>
    <commands comment="Vulkan command definitions">
        <command>
            <proto><type>PFN_vkVoidFunction</type> <name>vkGetInstanceProcAddr</name></proto>
            <param optional="true"><type>VkInstance</type> <name>instance</name></param>
            <param len="null-terminated">const <type>char</type>* <name>pName</name></param>
        </command>
    </commands>
    <types comment="Vulkan type definitions">
        <type api="vulkan" category="define">// Version of this file
        #define <name>VK_HEADER_VERSION</name> 12246445</type>
    </types>
</registry>
""".strip()

TEMPORARY_PREFIX = "test-dispatch-table-generator-"

def tmpfile(dir: Path = None) -> Path:
    handle = None
    name = None
    if dir and dir.is_dir():
        (handle, name) = tempfile.mkstemp(prefix=TEMPORARY_PREFIX, dir=dir)
    else:
        (handle, name) = tempfile.mkstemp()
    os.close(handle)
    return Path(name)

class TestVulkanVersion(unittest.TestCase):
    @staticmethod
    def _prep_versions() -> (VulkanVersion, VulkanVersion):
        return (VulkanVersion("1.0"), VulkanVersion("1.3"))
    def test_parse_should_fail_for_weird_inputs(self) -> None:
        with self.assertRaises(ValueError):
            VulkanVersion("Frog")
    def test_parse_should_fail_for_empty_string(self) -> None:
        with self.assertRaises(ValueError):
            VulkanVersion("")
    def test_parse_should_fail_for_none(self) -> None:
        with self.assertRaises(ValueError):
            VulkanVersion(None)
    def test_parse_should_pass_with_trailing_text(self) -> None:
        ver = VulkanVersion("6.3-alpha")
        self.assertEqual(ver.major(), 6)
        self.assertEqual(ver.minor(), 3)
    def test_parse_should_pass_with_known_good_versions(self) -> None:
        ver = VulkanVersion("1.3")
        self.assertEqual(ver.major(), 1)
        self.assertEqual(ver.minor(), 3)
    def test_compare_1_0_and_1_3_should_be_less_than_zero(self) -> None:
        (ver10, ver13) = TestVulkanVersion._prep_versions()
        self.assertLess(ver10.compare(ver13), 0)
    def test_compare_1_0_and_1_0_should_be_zero(self) -> None:
        (ver10, ver13) = TestVulkanVersion._prep_versions()
        self.assertEqual(ver10.compare(ver10), 0)
    def test_compare_1_3_and_1_0_should_be_greater_than_zero(self) -> None:
        (ver10, ver13) = TestVulkanVersion._prep_versions()
        self.assertGreater(ver13.compare(ver10), 0)
    def test_str_should_recover_an_equivalent_input_string(self) -> None:
        ver = VulkanVersion("6.0.2 Champion Edition")
        self.assertEqual(ver.compare(VulkanVersion(str(ver))),0)

class TestVulkanCommand(unittest.TestCase):
    def setUp(self) -> None:
        self.__tree = ElementTree.fromstring(TEMPORARY_SPEC)
    def test_init_should_fail_if_parameters_are_none(self) -> None:
        node = self.__tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        with self.assertRaises(ValueError):
            VulkanCommand(self.__tree, None)
        with self.assertRaises(ValueError):
            VulkanCommand(None, node)
    def test_init_should_fail_if_command_doesnt_have_a_name(self) -> None:
        tree = ElementTree.fromstring("<hello><world type=\"tasty\" /></hello>")
        node = tree.find("world")
        with self.assertRaises(ValueError):
            VulkanCommand(tree, node)
    def test_init_should_fail_if_aliased_command_is_missing(self) -> None:
        tree = ElementTree.fromstring(EVIL_SPEC_MISSING_ALIAS)
        node = tree.find("commands/command[@name='vkEvilAliasedCommand']")
        with self.assertRaises(ValueError):
            VulkanCommand(tree, node)
    def test_init_should_fail_if_command_doesnt_start_with_vk(self) -> None:
        tree = ElementTree.fromstring(EVIL_SPEC_NO_VK)
        node = tree.find("commands/command/proto/name[.='glEvilCommand']/../..")
        with self.assertRaises(ValueError):
            VulkanCommand(tree, node)
    def test_init_should_fail_if_command_doesnt_have_a_level(self) -> None:
        tree = ElementTree.fromstring(EVIL_SPEC_NO_LEVEL)
        node = tree.find("commands/command/proto/name[.='vkEvilCommand']/../..")
        with self.assertRaises(ValueError):
            VulkanCommand(tree, node)
    def test_init_should_locate_aliased_commands(self) -> None:
        node = self.__tree.find("commands/command[@name='vkResetQueryPoolEXT']")
        cmd = VulkanCommand(self.__tree, node)
        self.assertEqual(cmd.name(), "vkResetQueryPoolEXT")
        self.assertEqual(cmd.level(), VulkanCommandLevel.DEVICE)
    def test_init_should_handle_regular_commands(self) -> None:
        node = self.__tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        cmd = VulkanCommand(self.__tree, node)
        self.assertEqual(cmd.name(), "vkGetInstanceProcAddr")
        self.assertEqual(cmd.level(), VulkanCommandLevel.GLOBAL)

class TestVulkanCommandSet(unittest.TestCase):
    @staticmethod
    def _prep_command_set(tree) -> (VulkanCommandSet, list[VulkanCommand]):
        node = tree.find("commands/command[@name='vkResetQueryPoolEXT']")
        cmds = [ VulkanCommand(tree, node) ]
        cmd_set = VulkanCommandSet()
        cmd_set.add(cmds[0])
        node = tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        cmds.append(VulkanCommand(tree, node))
        cmd_set.add(cmds[1])
        node = tree.find("commands/command/proto/name[.='vkDestroySurfaceKHR']/../..")
        cmds.append(VulkanCommand(tree, node))
        cmd_set.add(cmds[2])
        return (cmd_set, cmds)
    def setUp(self) -> None:
        self.__tree = ElementTree.fromstring(TEMPORARY_SPEC)
    def test_add_should_insert_at_correct_level(self) -> None:
        node = self.__tree.find("commands/command[@name='vkResetQueryPoolEXT']")
        cmd = VulkanCommand(self.__tree, node)
        cmd_set = VulkanCommandSet()
        cmd_set.add(cmd)
        self.assertEqual(len(cmd_set.device_commands()), 1)
        node = self.__tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        cmd = VulkanCommand(self.__tree, node)
        cmd_set.add(cmd)
        self.assertEqual(len(cmd_set.global_commands()), 1)
        node = self.__tree.find("commands/command/proto/name[.='vkDestroySurfaceKHR']/../..")
        cmd = VulkanCommand(self.__tree, node)
        cmd_set.add(cmd)
        self.assertEqual(len(cmd_set.instance_commands()), 1)
    def test_remove_should_be_a_noop_if_command_not_in_set(self) -> None:
        node = self.__tree.find("commands/command[@name='vkResetQueryPoolEXT']")
        reset_query_pool = VulkanCommand(self.__tree, node)
        cmd_set = VulkanCommandSet()
        cmd_set.add(reset_query_pool)
        node = self.__tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        get_instance_proc_addr = VulkanCommand(self.__tree, node)
        cmd_set.remove(get_instance_proc_addr)
        self.assertIn(reset_query_pool, cmd_set)
    def test_remove_should_remove_from_underlying_sets(self) -> None:
        (cmd_set, cmds) = TestVulkanCommandSet._prep_command_set(self.__tree)
        for cmd in cmds:
            cmd_set.remove(cmd)
        self.assertTrue(cmd_set.empty())
    def test_contains_should_find_added_commands(self) -> None:
        (cmd_set, cmds) = TestVulkanCommandSet._prep_command_set(self.__tree)
        for cmd in cmds:
            self.assertTrue(cmd in cmd_set)
    def test_len_should_be_the_sum_of_set_lens(self) -> None:
        (cmd_set, cmds) = TestVulkanCommandSet._prep_command_set(self.__tree)
        total = len(cmd_set.global_commands()) + len(cmd_set.instance_commands()) + len(cmd_set.device_commands())
        self.assertEqual(len(cmd_set), total)
    def test_find_should_retrieve_commands(self) -> None:
        (cmd_set, cmds) = TestVulkanCommandSet._prep_command_set(self.__tree)
        node = self.__tree.find("commands/command/proto/name[.='vkGetInstanceProcAddr']/../..")
        cmd = VulkanCommand(self.__tree, node)
        self.assertEqual(cmd, cmd_set.find("vkGetInstanceProcAddr"))
    def test_find_should_retrieve_none_for_unknown_commands(self) -> None:
        (cmd_set, cmds) = TestVulkanCommandSet._prep_command_set(self.__tree)
        self.assertIsNone(cmd_set.find("vkNotAVulkanCommand"))

class TestVulkanRequirement(unittest.TestCase):
    def setUp(self) -> None:
        self.__tree = ElementTree.fromstring(TEMPORARY_SPEC)
        self.__commands = { }
        for node in self.__tree.findall("commands/command"):
            parsed = VulkanCommand(self.__tree, node)
            self.__commands[parsed.name()] = parsed
    def test_init_should_fail_with_no_node(self) -> None:
        with self.assertRaises(ValueError):
            VulkanRequirement(None, self.__commands)
    def test_init_should_fail_with_no_commands(self) -> None:
        with self.assertRaises(ValueError):
            VulkanRequirement(self.__tree.find(".//require"), None)
    def test_dependency_satisfaction(self) -> None:
        node = self.__tree.find(".//require[@depends]")
        requirement = VulkanRequirement(node, self.__commands)
        self.assertFalse(requirement.is_satisfied(None))
        self.assertFalse(requirement.is_satisfied({}))
        features = { "VK_VERSION_1_0", "VK_VERSION_1_1", "VK_KHR_synchronization2", "VK_KHR_pipeline_library",
                    "VK_KHR_spirv_1_4" }
        self.assertTrue(requirement.is_satisfied(features))
    def test_header_guard_should_match_expected_guard(self) -> None:
        node = self.__tree.find(".//require[@depends]")
        requirement = VulkanRequirement(node, self.__commands)
        guard = "(((defined(VK_KHR_get_physical_device_properties2) || defined(VK_VERSION_1_1)) && defined(VK_KHR_synchronization2)) || defined(VK_VERSION_1_3)) && defined(VK_KHR_pipeline_library) && defined(VK_KHR_spirv_1_4)"
        self.assertEqual(guard, requirement.to_header_guard())

class TestVulkanFeature(unittest.TestCase):
    def setUp(self) -> None:
        self.__tree = ElementTree.fromstring(TEMPORARY_SPEC)
        self.__commands = { }
        for node in self.__tree.findall("commands/command"):
            parsed = VulkanCommand(self.__tree, node)
            self.__commands[parsed.name()] = parsed
    def __find_in_any_requirement(self, name: str, feature: VulkanFeature) -> bool:
        for requirement in feature.requirements():
            if self.__commands[name] in requirement.commands():
                return True
        return False
    def test_init_should_fail_if_node_tag_is_not_feature_or_extension(self) -> None:
        with self.assertRaises(ValueError):
            VulkanFeature(self.__tree.find("commands/command"), self.__commands)
    def test_init_should_support_features(self) -> None:
        node = self.__tree.find("feature")
        feature = VulkanFeature(node, self.__commands)
        self.assertEqual(feature.name(), "VK_VERSION_1_0")
        self.assertEqual(feature.version(), VulkanVersion("1.0"))
        self.assertEqual(feature.supported_apis(), set([ "vulkan", "vulkansc" ]))
        self.assertTrue(self.__find_in_any_requirement("vkGetInstanceProcAddr", feature))
        self.assertEqual(len(feature.removals()), 0)
        self.assertFalse(feature.enabled())
    def test_init_should_support_extensions(self) -> None:
        node = self.__tree.find("extensions/extension")
        feature = VulkanFeature(node, self.__commands)
        self.assertEqual(feature.name(), "VK_KHR_surface")
        self.assertEqual(feature.version(), VulkanVersion("25.0"))
        self.assertEqual(feature.supported_apis(), set([ "vulkan", "vulkansc" ]))
        self.assertTrue(self.__find_in_any_requirement("vkDestroySurfaceKHR", feature))
        self.assertEqual(len(feature.removals()), 0)
        self.assertFalse(feature.enabled())
    def test_init_should_recognize_deprecated_features(self) -> None:
        node = self.__tree.find("extensions/extension[@name='VK_EXT_debug_report']")
        feature = VulkanFeature(node, self.__commands)
        self.assertTrue(feature.deprecated())
    def test_dependency_satisfaction(self) -> None:
        node = self.__tree.find(".//extension[@name='VK_EXT_host_query_reset']")
        feature = VulkanFeature(node, self.__commands)
        self.assertFalse(feature.is_satisfied(None))
        self.assertFalse(feature.is_satisfied({}))
        features = { "VK_KHR_physical_device_properties2", "VK_VERSION_1_1", "VK_VERSION_1_0" }
        self.assertTrue(feature.is_satisfied(features))
    def test_header_guard_should_match_expected_guard(self) -> None:
        node = self.__tree.find(".//extension[@name='VK_EXT_host_query_reset']")
        feature = VulkanFeature(node, self.__commands)
        guard = "defined(VK_KHR_get_physical_device_properties2) || defined(VK_VERSION_1_1)"
        self.assertEqual(guard, feature.to_header_guard())

class TestVulkanSpecification(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = Path(tempfile.mkdtemp(prefix=TEMPORARY_PREFIX))
        self._tmp_spec = tmpfile(self._tmp_dir)
        with open(self._tmp_spec, "wb") as outfile:
            outfile.write(TEMPORARY_SPEC.encode("utf-8"))
    def tearDown(self) -> None:
        self._tmp_spec.unlink()
        for file in self._tmp_dir.iterdir():
            file.unlink()
        self._tmp_dir.rmdir()
    def test_init_should_handle_latest_version_specifier(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set())
        latest = VulkanVersion("0.0")
        for name in spec.features():
            api = spec.features()[name]
            if api.version() > latest and api.enabled():
                latest = api.version()
        self.assertEqual(latest, VulkanVersion("1.2"))
    def test_init_should_handle_all_extensions_specifier(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]))
        extensions = set([ "VK_KHR_surface", "VK_EXT_debug_report", "VK_EXT_host_query_reset" ])
        for extension in extensions:
            self.assertIn(extension, spec.extensions())
            self.assertTrue(spec.extensions()[extension].enabled())
    def test_init_should_fail_if_specification_doesnt_exist(self) -> None:
        with self.assertRaises(ValueError):
            VulkanSpecification(Path(self._tmp_dir, "nonexistant-spec.vk.xml"), "vulkan", "latest", set([ "all" ]))
    def test_init_should_fail_if_specification_isnt_file(self) -> None:
        with self.assertRaises(ValueError):
            VulkanSpecification(self._tmp_dir, "vulkan", "latest", set([ "all" ]))
    def test_init_should_find_specification_if_path_is_none(self) -> None:
        spec = VulkanSpecification(None, "vulkan", "latest", set([ "all" ]))
        self.assertIsNotNone(spec.specification_path())
    def test_init_should_only_enable_requested_features(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "1.0", set([ "VK_KHR_surface" ]))
        for name in spec.features():
            feature = spec.features()[name]
            if name == "VK_VERSION_1_0":
                self.assertTrue(feature.enabled())
            else:
                self.assertFalse(feature.enabled())
        for name in spec.extensions():
            extension = spec.extensions()[name]
            if name == "VK_KHR_surface":
                self.assertTrue(extension.enabled())
            else:
                self.assertFalse(extension.enabled())
    def test_init_should_disable_deprecated_features_on_request(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]), False)
        for name in spec.extensions():
            extension = spec.extensions()[name]
            if extension.deprecated():
                self.assertFalse(extension.enabled())
    def test_specification_path_should_be_input_path(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]))
        self.assertEqual(self._tmp_spec, spec.specification_path())
    def test_specification_version_should_be_header_version(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]))
        self.assertEqual(spec.specification_version(), 0xbaddad)
    def test_specification_commands_dict_should_contain_all_commands(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]))
        cmds = set([ "vkGetInstanceProcAddr", "vkDestroySurfaceKHR", "vkResetQueryPool", "vkResetQueryPoolEXT",
                     "vkCreateDebugReportCallbackEXT", "vkDestroyDebugReportCallbackEXT", "vkDebugReportMessageEXT" ])
        for cmd in cmds:
            self.assertIn(cmd, spec.commands())
    def test_init_should_fail_when_specification_version_isnt_found(self) -> None:
        bad_spec = tmpfile(self._tmp_dir)
        with open(bad_spec, "wb") as outfile:
            tree = ElementTree.fromstring(TEMPORARY_SPEC)
            tree.remove(tree.find("types"))
            outfile.write(ElementTree.tostring(tree, encoding="utf-8"))
        with self.assertRaises(ValueError):
            VulkanSpecification(bad_spec, "vulkan", "1.0", set())
        bad_spec.unlink()
    def test_init_should_fail_if_api_is_none(self) -> None:
        with self.assertRaises(ValueError):
            VulkanSpecification(self._tmp_spec, None)
    def test_init_should_fail_if_api_version_is_none(self) -> None:
        with self.assertRaises(ValueError):
            VulkanSpecification(self._tmp_spec, "vulkan", None)
    def test_init_should_pass_if_extensions_are_none(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", None)
        count = 0
        for name in spec.extensions():
            if spec.extensions()[name].enabled():
                count += 1
        self.assertEqual(count, 0)
    def test_init_should_pass_if_enable_deprecated_is_none(self) -> None:
        spec = VulkanSpecification(self._tmp_spec, "vulkan", "latest", set([ "all" ]), None)
        for extension in spec.extensions().values():
            if extension.deprecated():
                self.assertFalse(extension.enabled())
            else:
                self.assertTrue(extension.enabled())

class TestDispatchTableGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.__err = StringIO()
        self.__redirect_stderr = contextlib.redirect_stderr(self.__err)
        self.__redirect_stderr.__enter__()
        self.__tmp_dir = Path(tempfile.mkdtemp(prefix=TEMPORARY_PREFIX))
        self.__tmp_template = tmpfile(self.__tmp_dir)
        with open(self.__tmp_template, "wb") as outfile:
            outfile.write(b"int main() {\n  return ${len(commands)};\n}")
        self.__tmp_spec = tmpfile(self.__tmp_dir)
        with open(self.__tmp_spec, "wb") as outfile:
            outfile.write(TEMPORARY_SPEC.encode("utf-8"))
    def tearDown(self) -> None:
        self.__redirect_stderr.__exit__(None, None, None)
        self.__tmp_spec.unlink()
        self.__tmp_template.unlink()
        for file in self.__tmp_dir.iterdir():
            file.unlink()
        self.__tmp_dir.rmdir()
    def test_init_should_fail_when_template_is_none(self) -> None:
        with self.assertRaises(FileNotFoundError):
            DispatchTableGenerator(None)
    def test_init_should_fail_when_template_doesnt_exist(self) -> None:
        with self.assertRaises(FileNotFoundError):
            doesnt_exist = Path(tempfile.gettempdir(), f"{tempfile.gettempprefix()}-not-a-real-template.cpp.in")
            DispatchTableGenerator(doesnt_exist)
    def test_init_should_fail_when_template_isnt_a_file(self) -> None:
        with self.assertRaises(OSError):
            with tempfile.TemporaryDirectory(prefix=TEMPORARY_PREFIX) as tmpdir:
                DispatchTableGenerator(Path(tmpdir))
    def test_init_should_fail_when_output_isnt_a_file(self) -> None:
        with self.assertRaises(OSError):
            with tempfile.TemporaryDirectory(prefix=TEMPORARY_PREFIX) as tmpdir:
                DispatchTableGenerator(self.__tmp_template, False, Path(tmpdir))
    def test_init_should_fail_when_specification_doesnt_exist(self) -> None:
        with self.assertRaises(FileNotFoundError):
            doesnt_exist = Path(tempfile.gettempdir(), f"{tempfile.gettempprefix()}-vk.xml")
            DispatchTableGenerator(self.__tmp_template, False, None, doesnt_exist)
    def test_init_should_fail_when_specification_isnt_a_file(self) -> None:
        with self.assertRaises(OSError):
            with tempfile.TemporaryDirectory(prefix=TEMPORARY_PREFIX) as tmpdir:
                DispatchTableGenerator(self.__tmp_template, False, None, Path(tmpdir))
    def test_run_should_produce_expected_output_given_a_template_and_specification(self) -> None:
        output = tmpfile(self.__tmp_dir)
        app = DispatchTableGenerator(self.__tmp_template, False, output, self.__tmp_spec)
        app.run()
        with open(output, "rb") as infile:
            self.assertEqual(infile.read(), b"int main() {\n  return 7;\n}")
        output.unlink()
    def test_run_should_fail_on_unmet_feature_dependency(self) -> None:
        spec = tmpfile(self.__tmp_dir)
        with open(spec, "wb") as outfile:
            outfile.write(EVIL_SPEC_BAD_FEATURE_DEPENDENCY.encode("utf-8"))
        with self.assertRaises(ValueError):
            app = DispatchTableGenerator(self.__tmp_template, False, None, spec)
            app.run()
        spec.unlink()
    def test_run_should_fail_on_unmet_extension_dependency(self) -> None:
        spec = tmpfile(self.__tmp_dir)
        with open(spec, "wb") as outfile:
            outfile.write(EVIL_SPEC_BAD_DEPENDENCY.encode("utf-8"))
        with self.assertRaises(ValueError):
            app = DispatchTableGenerator(self.__tmp_template, False, None, spec)
            app.run()
        spec.unlink()
    def test_run_should_pass_on_unmet_extension_requirement_dependency(self) -> None:
        spec = tmpfile(self.__tmp_dir)
        with open(spec, "wb") as outfile:
            outfile.write(NEUTRAL_SPEC_BAD_REQUIREMENT_DEPENDENCY.encode("utf-8"))
        res = ""
        with StringIO() as out, contextlib.redirect_stdout(out):
            app = DispatchTableGenerator(self.__tmp_template, False, None, spec)
            app.run()
            res = out.getvalue()
        spec.unlink()
        self.assertEqual(res, "int main() {\n  return 1;\n}")


if __name__ == "__main__":
  unittest.main()

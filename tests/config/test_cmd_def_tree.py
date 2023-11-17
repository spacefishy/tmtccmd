import os
from unittest import TestCase
from tmtccmd.config.tmtc import CmdTreeNode


class TestCmdDefTree(TestCase):
    def setUp(self) -> None:
        self.cmd_tree = CmdTreeNode.root_node()

    def base_tree(self):
        self.cmd_tree.add_child(CmdTreeNode("acs", "ACS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("tcs", "TCS Subsystem"))

    def test_state(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        self.assertEqual(self.cmd_tree.name, "/")
        self.assertEqual(self.cmd_tree.children["acs"].name, "acs")
        self.assertEqual(self.cmd_tree.children["acs"].description, "ACS Subsystem")
        self.assertEqual(self.cmd_tree.children["acs"].children, {})
        assert self.cmd_tree.children["acs"].parent is not None
        self.assertEqual(self.cmd_tree.children["acs"].parent.name, "/")

        self.assertEqual(self.cmd_tree.children["tcs"].name, "tcs")
        self.assertEqual(self.cmd_tree.children["tcs"].description, "TCS Subsystem")
        self.assertEqual(self.cmd_tree.children["tcs"].children, {})
        assert self.cmd_tree.children["tcs"].parent is not None
        self.assertEqual(self.cmd_tree.children["tcs"].parent.name, "/")

        self.assertEqual(self.cmd_tree.children["ping"].name, "ping")
        self.assertEqual(self.cmd_tree.children["ping"].description, "Ping Command")
        self.assertEqual(self.cmd_tree.children["ping"].children, {})
        assert self.cmd_tree.children["ping"].parent is not None
        self.assertEqual(self.cmd_tree.children["ping"].parent.name, "/")

        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.assertEqual(len(self.cmd_tree.children["acs"].children), 1)
        acs_ctrl_child = self.cmd_tree.children["acs"].children["acs_ctrl"]
        self.assertEqual(acs_ctrl_child.name, "acs_ctrl")
        self.assertEqual(acs_ctrl_child.description, "ACS Controller")
        assert acs_ctrl_child.parent is not None
        self.assertEqual(acs_ctrl_child.parent.name, "acs")

    def test_named_dict(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        name_dict = self.cmd_tree.name_dict
        root_dict = name_dict.get("/")
        assert root_dict is not None
        assert "tcs" in root_dict
        assert root_dict.get("tcs") is None
        assert "acs" in root_dict
        acs_dict = root_dict.get("acs")
        assert acs_dict is not None
        assert "acs_ctrl" in acs_dict
        assert acs_dict.get("acs_ctrl") is None

    def test_printout_empty(self):
        self.assertEqual(str(self.cmd_tree), f"/{os.linesep}")

    def test_prinout_one_sublevel(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        print(str(self.cmd_tree))
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_prinout_two_sublevels(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── acs_ctrl{os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_two_sublevels_one_cutoff(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        printout = self.cmd_tree.str_for_tree(False, 1)
        print(printout)
        self.assertEqual(
            printout,
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── ... (cut-off, maximum depth 1){os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_3(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.cmd_tree.children["tcs"].add_child(
            CmdTreeNode("tcs_ctrl", "TCS Controller")
        )

        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── acs_ctrl{os.linesep}"
                f"└── tcs{os.linesep}"
                f"   └── tcs_ctrl{os.linesep}"
            ),
        )

    def test_printout_4(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.cmd_tree.children["acs"].add_child(CmdTreeNode("mgm_0", "MGM 0"))
        self.cmd_tree.children["acs"].children["mgm_0"].add_child(
            CmdTreeNode("update_cfg", "Update Configuration")
        )
        self.cmd_tree.children["tcs"].add_child(
            CmdTreeNode("tcs_ctrl", "TCS Controller")
        )
        self.cmd_tree.children["tcs"].add_child(CmdTreeNode("pt1000_0", "PT1000 0"))
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── update_cfg{os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  └── pt1000_0{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )
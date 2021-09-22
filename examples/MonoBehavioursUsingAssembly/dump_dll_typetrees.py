# py3
# requirements:
#   pythonnet 3+
#       pip install git+https://github.com/pythonnet/pythonnet/
#   TypeTreeGenerator
#       https://github.com/K0lb3/TypeTreeGenerator
#       requires .NET 5.0 SDK
#           https://dotnet.microsoft.com/download/dotnet/5.0
#
#   pythonnet 2 and TypeTreeGenerator created with net4.8 works on Windows,
#   so it can do without pythonnet_init,
#   all other systems need pythonnet 3 and either .net 5 or .net core 3 and pythonnet_init

import os
import UnityPy
from typing import Dict
import json
import glob

ROOT = os.path.dirname(os.path.realpath(__file__))
TYPETREE_GENERATOR_PATH = os.path.join(ROOT, "TypeTreeGenerator")
CLR_CONFIG = os.path.join(TYPETREE_GENERATOR_PATH, "TypeTreeGenerator.runtimeconfig.json")

def main():
    # Dump the trees for all classes in the assembly
    dll_folder = os.path.join(ROOT, "Managed")
    tree_path = os.path.join(ROOT, "assembly_typetrees.json") 
    trees = dump_assembly_trees(dll_folder, tree_path)
    # by dumping it as json, it can be redistributed,
    # so that other people don't have to setup pythonnet3
    # People who don't like to share their decrypted dlls could also share the relevant structures this way.

def dump_assembly_trees(dll_folder: str, out_path: str):
    # Don't regenerate the file if it exists already
    if os.path.isfile(out_path):
        with open(out_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    # Init pythonnet, so that it uses the correct .net for the generator
    pythonnet_init()
    # create generator
    g = create_generator(dll_folder)

    # Generate a typetree for all existing classes in the Assembly-CSharp
    # While this could also be done dynamically for each required class,
    # it's faster and easier overall to just fetch all at once
    trees = {}
    for dll in glob.glob(os.path.join(dll_folder, "*.dll"), recursive=True):
        dll = os.path.basename(dll)
        print("Generating TypeTree for",  dll)
        tree = generate_tree(g, dll, "", "")
        if tree:
            trees.update(tree)

    if out_path and len(trees) > 0:
        with open(out_path, "w", encoding="utf-8-sig") as f:
            json.dump(trees, f, ensure_ascii=False, indent=4)
    return trees


def pythonnet_init():
    """Correctly sets-up pythonnet for the typetree generator"""

    # Prepare correct runtime
    from clr_loader import get_coreclr
    from pythonnet import set_runtime

    rt = get_coreclr(CLR_CONFIG)
    set_runtime(rt)


def create_generator(dll_folder: str):
    """Loads TypeTreeGenerator library and returns an instance of the Generator class."""

    # Temporarily add the typetree generator dir to paths,
    # so that pythonnet can find its files
    import sys
    sys.path.append(TYPETREE_GENERATOR_PATH)

    import clr
    clr.AddReference("TypeTreeGenerator")

    # Import Generator class from the loaded library
    from Generator import Generator

    # Create an instance of the Generator class
    g = Generator()
    # load the dll folder into the generator
    g.loadFolder(dll_folder)
    return g


class FakeNode:
    """A minimal fake Node class for use in UnityPy."""

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


def generate_tree(
    g: "Generator",
    assembly: str,
    class_name: str,
    namespace: str,
    unity_version=[2018, 4, 3, 1],
) -> Dict[str, Dict]:
    """Generates the typetree structure / nodes for the specified class."""
    # C# System
    from System import Array

    unity_version_cs = Array[int](unity_version)

    # Fetch all type definitions
    def_iter = g.getTypeDefs(assembly, class_name, namespace)

    # Create the nodes
    trees = {}
    for d in def_iter:
        try:
            nodes = g.convertToTypeTreeNodes(d, unity_version_cs)
        except Exception as e:
            # print(d.Name, e)
            continue
        trees[d.Name] = [
            {
                "level" : node.m_Level,
                "type" : node.m_Type,
                "name" : node.m_Name,
                "meta_flag" : node.m_MetaFlag,
            }
            for node in nodes
        ]
    return trees


if __name__ == "__main__":
    main()

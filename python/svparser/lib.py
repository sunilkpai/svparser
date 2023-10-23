from typing import List, Dict, NamedTuple
from .bindings import (
    parse_lib, parse_lib_str,
    parse_sv, parse_sv_str
)
from .bindings import SyntaxTree, SyntaxNode
from .bindings import unwrap_node
from enum import Enum


class Instance(NamedTuple):
    name: str
    module_name: str


class Connection(NamedTuple):
    name: str
    port_name: str
    instance: Instance


class PortDirection(str, Enum):
    input: str = 'input'
    output: str = 'output'
    inout: str = 'inout'


class Port(NamedTuple):
    name: str
    type: str
    direction: PortDirection


class Module(NamedTuple):
    name: str
    ports: List[Port]
    connections: List[Connection]


def parse_sv_file(
    path: str,
    pre_defines: dict = {},
    include_paths: List[str] = [],
    ignore_include: bool = False,
    allow_incomplete: bool = False,
    lib: bool = False
) -> SyntaxTree:
    """Parse a SystemVerilog file.

    Args:
        path: Path to the SystemVerilog file.
        pre_defines: Pre-define files. Defaults to {}.
        include_paths: File paths for the includes. Defaults to [].
        ignore_include: Ignore includes. Defaults to False.
        allow_incomplete: Allow incomplete source code. Defaults to False.
        lib: Whether to parse as a System Verilog library, else as a System Verilog script.
    """
    if lib:
        return parse_lib(path, pre_defines, include_paths, ignore_include, allow_incomplete)
    else:
        return parse_sv(path, pre_defines, include_paths, ignore_include, allow_incomplete)


def parse_sv_text(
    text: str,
    path: str = '',
    pre_defines: dict = {},
    include_paths: List[str] = [],
    ignore_include: bool = False,
    allow_incomplete: bool = False,
    lib: bool = False
) -> SyntaxTree:
    """Parse a SystemVerilog string.

    Args:
        text: Text containing the SystemVerilog script.
        path: Path to the SystemVerilog file.
        pre_defines: Pre-define files. Defaults to {}.
        include_paths: File paths for the includes. Defaults to [].
        ignore_include: Ignore includes. Defaults to False.
        allow_incomplete: Allow incomplete source code. Defaults to False.
        lib: Whether to parse as a System Verilog library, else as a System Verilog script.
    """
    if lib:
        return parse_lib_str(text, path, pre_defines, include_paths, ignore_include, allow_incomplete)
    else:
        return parse_sv_str(text, path, pre_defines, include_paths, ignore_include, allow_incomplete)


def get_module_instance_map(tree: SyntaxTree):
    module_instance_map = {}
    for node in list(tree.tree):
        if 'ModuleDeclaration' in node.type_name:
            if node := unwrap_node(node, ('ModuleIdentifier',)):
                module = tree.get_str(node).strip()
                if module not in module_instance_map:
                    module_instance_map[module] = []
        if node.type_name == 'ModuleInstantiation':
            if mod := unwrap_node(node, ('ModuleIdentifier',)):
                if inst := unwrap_node(node, ('InstanceIdentifier',)):
                    module_instance_map[module].append(Instance(
                        name=tree.get_str(inst).strip(),
                        module_name=tree.get_str(mod).strip()
                    ))
    return module_instance_map


def get_circuit_topology(tree: SyntaxTree):
    module_to_port = {}
    module_to_circuit_topology = {}
    for node in list(tree.tree):
        if 'ModuleDeclaration' in node.type_name:
            if node := unwrap_node(node, ('ModuleIdentifier',)):
                module = tree.get_str(node).strip()
                if module not in module_to_circuit_topology:
                    module_to_circuit_topology[module] = []
                if module not in module_to_port:
                    module_to_port[module] = set()
        if 'PortDeclaration' in node.type_name:
            if port := unwrap_node(node, ('PortIdentifier',)):
                if dir := unwrap_node(node, ('PortDirection',)):
                    module_to_port[module].add(
                        Port(name=tree.get_str(port).strip(),
                             direction=PortDirection[tree.get_str(dir).strip()])
                    )
        if node.type_name == 'ModuleInstantiation':
            if mod := unwrap_node(node, ('ModuleIdentifier',)):
                if inst := unwrap_node(node, ('InstanceIdentifier',)):
                    instance = Instance(
                        name=tree.get_str(inst).strip(),
                        module_name=tree.get_str(mod).strip()
                    )
        if node.type_name == 'NamedPortConnection':
            if port := unwrap_node(node, ('PortIdentifier',)):
                if expr := unwrap_node(node, ('Expression',)):
                    module_to_circuit_topology[module].append(Connection(
                        name=tree.get_str(expr).strip(),
                        port_name=tree.get_str(port).strip(),
                        instance=instance,
                    ))

    return [Module(m, list(module_to_port[m]), module_to_circuit_topology[m])
            for m in module_to_circuit_topology]

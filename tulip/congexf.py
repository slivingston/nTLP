# Copyright (c) 2011, 2012 by California Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the California Institute of Technology nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL CALTECH
# OR THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
"""
Several functions that help in converting an AUT file (from JTLV)
to a GEXF file (in Gephi).
"""

import re

from automaton import Automaton

activeID = 'is_active'

def tagGexfAttr(var_name, var_type, idt_lvl):
    """
    Encode the variable specified in a gexf-readable attribute string.

    Arguments:
    var_name -- the string name of the desired variable.
    var_type -- Python type of the variable.
    idt_lvl -- level of indentation of the final string.

    Return:
    String representing a gexf attribute.
    """

    if not (isinstance(var_name, str) and isinstance(var_type, type) and
            isinstance(idt_lvl, int)):
        raise TypeError("Invalid arguments to tagGexfAttr")
    
    nl = "\n"  # newline
    idt = "  "  # indentation
    
    # First create a dictionary that translates Python data type names
    # to gexf data type names.
    type_dict = {str: 'string', int: 'integer',
                 float: 'float', bool: 'boolean'}

    # Generate a line of XML for the attribute.
    attribute = idt * idt_lvl + '<attribute id="' + var_name + \
                '" type="' + type_dict[var_type] + '" />' + nl
    
    return attribute
    
    
def tagGexfAttvalue(var_name, var_val, idt_lvl):
    """
    Encode the attribute specified in a gexf-readable attribute value
    string.

    Arguments:
    var_name -- the string name of the attribute.
    var_val -- value of the attribute for this node/edge.
    idt_lvl -- level of indentation of the final string.
    
    Return:
    String representing a gexf attribute value.
    """

    if not (isinstance(var_name, str) and isinstance(idt_lvl, int)):
        raise TypeError("Invalid arguments to tagGexfAttrVal")

    nl = "\n"  # newline
    idt = "  "  # indentation

    # Generate a line of XML for the attribute value.
    attvalue = idt * idt_lvl + '<attvalue for="' + var_name + \
               '" value="' + str(var_val) + '" />' + nl
    
    return attvalue
    
    
def tagGexfNode(p_id, node, node_data, label, idt_lvl):
    """
    Encode the state specified in a gexf-readable node string.
    The variables in the specified state are stored as
    attribute values.

    Arguments:
    p_id -- the ID of this node's parent Automaton.
    node -- node (as an integer "ID") from an Automaton.
    node_data -- node annotation; in particular, see "state" key.
    label -- a string name for the node.
    idt_lvl -- level of indentation of the final string.

    Return:
    String representing a gexf node.
    """
    
    if not (isinstance(label, str) and
            isinstance(p_id, int) and isinstance(idt_lvl, int)):
        raise TypeError("Invalid arguments to tagGexfNode")
    
    state_ID = str(p_id) + '.' + str(node)
    
    nl = "\n"  # newline
    idt = "  "  # indentation

    # Generate a line of XML for the node.
    xml_node = idt * idt_lvl + '<node id="' + state_ID + \
        '" label="' + label + '" pid="' + str(p_id) + '">' + nl
    idt_lvl += 1
    xml_node += idt * idt_lvl + '<attvalues>' + nl

    # Iterate through attributes.
    idt_lvl += 1
    attr_dict = node_data["state"].copy()
    # activeID holds the name of an attribute used to simulate the automaton.
    # It changes from 0 when the automaton is currently at that node.
    attr_dict[activeID] = 0
    for (k, v) in attr_dict.items():
        xml_node += tagGexfAttvalue(k, v, idt_lvl)
    idt_lvl -= 1

    # Close attributes and node tag.
    xml_node += idt * idt_lvl + '</attvalues>' + nl
    idt_lvl -= 1
    xml_node += idt * idt_lvl + '</node>' + nl
    
    return xml_node


def tagGexfTaggedNode(p_id, node, node_data, label, idt_lvl):
    """forked tagGexfNode function to support coloring, etc.

    interface is almost identical to that of tagGexfNode. The key
    difference is ability to recognize and process the ``tags''
    attribute in the given ``node_data''.

    See documentation in tagGexfNode for basic behavior.
    """
    
    if not (isinstance(label, str) and
            isinstance(p_id, int) and isinstance(idt_lvl, int)):
        raise TypeError("Invalid arguments to tagGexfNode")
    
    state_ID = str(p_id) + '.' + str(state.id)
    if "tags" in node_data:
        tags = node_data["tags"].copy()
    else:
        tags = {}
    
    nl = "\n"  # newline
    idt = "  "  # indentation

    # Generate a line of XML for the node.
    xml_node = idt * idt_lvl + '<node id="' + state_ID + \
        '" label="' + label + '" pid="' + str(p_id) + '">' + nl
    idt_lvl += 1
    if tags.has_key("color"):
        xml_node += idt * idt_lvl + '<viz:color r="'+str(tags["color"][0])+'" g="'+str(tags["color"][1])+'" b="'+str(tags["color"][2])+'" a="'+str(tags["color"][3])+'" />' + nl
    xml_node += idt * idt_lvl + '<attvalues>' + nl

    # Iterate through attributes.
    idt_lvl += 1
    attr_dict = node_data["state"].copy()
    # activeID holds the name of an attribute used to simulate the automaton.
    # It changes from 0 when the automaton is currently at that node.
    attr_dict[activeID] = 0
    for (k, v) in attr_dict.items():
        xml_node += tagGexfAttvalue(k, v, idt_lvl)
    idt_lvl -= 1

    # Close attributes and node.
    xml_node += idt * idt_lvl + '</attvalues>' + nl
    idt_lvl -= 1
    xml_node += idt * idt_lvl + '</node>' + nl
    
    return xml_node
        
    
def tagGexfEdge(sourcep_id, source, source_data,
                targetp_id, target, target_data,
                label, idt_lvl):
    """
    Encode the transition specified in a gexf-readable edge string.
    The variables in the target's state are stored as
    attribute values.

    Arguments:
    sourcep_id -- the ID of the source's parent Automaton.
    source -- node (as an integer "ID") for the 'tail' of the edge.
    source_data -- node annotation; in particular, see "state" key.
    targetp_id -- the ID of the target's parent Automaton.
    target -- node (as an integer "ID") for the 'head' of the edge.
    target_data -- node annotation; in particular, see "state" key.
    label -- a string name for the edge.
    idt_lvl -- level of indentation of the final string.

    Return:
    String representing a gexf edge.
    """
    
    if not (isinstance(label, str) and
            isinstance(sourcep_id, int) and isinstance(targetp_id, int) and
            isinstance(idt_lvl, int)):
        raise TypeError("Invalid arguments to tagGexfEdge")
    
    source_ID = str(sourcep_id) + '.' + str(source)
    target_ID = str(targetp_id) + '.' + str(target)
    edge_ID = source_ID + '-' + target_ID
    
    nl = "\n"  # newline
    idt = "  "  # indentation
    
    # Generate a line of XML for the edge.
    edge = idt * idt_lvl + '<edge id="' + edge_ID + \
           '" source="' + source_ID + \
           '" target="' + target_ID + \
           '" label="' + label + '">' + nl
    idt_lvl += 1
    edge += idt * idt_lvl + '<attvalues>' + nl

    # Iterate through attributes.
    idt_lvl += 1
    attr_dict = target_data["state"].copy()
    # activeID holds the name of an attribute used to simulate the automaton.
    # It changes from 0 when the automaton is currently at that node.
    attr_dict[activeID] = 0
    for (k, v) in attr_dict.items():
        edge += tagGexfAttvalue(k, v, idt_lvl)
    idt_lvl -= 1
    
    # Close attributes and node.
    edge += idt * idt_lvl + '</attvalues>' + nl
    idt_lvl -= 1
    edge += idt * idt_lvl + '</edge>' + nl
    
    return edge

    
def dumpGexf(aut_list, label_vars=None, use_viz=False, use_clusters=False):
    """
    Writes the automaton to a Gephi 'gexf' string. Nodes represent system
    states and edges represent transitions between nodes.

    Arguments:
    aut_list -- a list of Automaton objects. Generate a hierarchical graph
        with each Automaton as a supernode. Note: if a single
        Automaton is given instead, it will be wrapped in a list.
    label_vars -- a list of state variable names whose values will be labels
        on nodes and edges of the graph. If this is 'None', show all
        attributes in labels
    use_viz -- whether to include Gephi visualization module.
    use_clusters -- whether to recognize and use "cluster_id" given in
        ``tags'' attribute of automata nodes. Nodes that are not
        tagged with a cluster ID are all grouped into a (new) cluster.
        N.B., if True, node-based clustering trumps the default
        per-automaton clustering and chaining.

    Return:
    A gexf formatted string that can be written to file.
    """

    if isinstance(aut_list, Automaton):
        # Wrap aut_or_list in a list, for simpler code later.
        aut_list = [aut_list]
    elif isinstance(aut_list, list):
        for aut in aut_list:
            if not isinstance(aut, Automaton):
                raise TypeError("Invalid arguments to dumpGexf.")
    else:
        raise TypeError("Invalid arguments to dumpGexf.")
    attr_dict = {}
    for aut in aut_list:
        for (node, data) in aut.nodes_iter(data=True):
            for (k, v) in data["state"].items():
                if k not in attr_dict.keys():
                    attr_dict[k] = type(v)
    # If no 'label_vars' were passed, use all attributes as labels
    if label_vars is None:
        label_vars = attr_dict.keys()
    elif isinstance(label_vars, list):
        if label_vars != filter(lambda x: x in attr_dict.keys(), label_vars):
            raise TypeError("Invalid arguments to dumpGexf.")
    attr_dict[activeID] = int

    
    nl = "\n"  # newline
    idt = "  "  # indentation
    idt_lvl = 0 # indentation level
    output = '' # string to be written to file
    
    # Open xml, gexf, and node attributes tags.
    output += idt * idt_lvl + '<?xml version="1.0" encoding="UTF-8"?>' + nl
    if use_viz:
        output += idt * idt_lvl + '<gexf version="1.2" xmlns="http://www.gexf.net/1.2draft"\n      xmlns:viz="http://www.gexf.net/1.2draft/viz">' + nl
    else:
        output += idt * idt_lvl + '<gexf version="1.2">' + nl
    idt_lvl += 1
    output += idt * idt_lvl + '<graph defaultedgetype="directed">' + nl
    idt_lvl += 1
    output += idt * idt_lvl + '<attributes class="node">' + nl

    # Build gexf node attributes (used to specify the types of data
    # that can be stored) from the 'state' dictionary of
    # AutomatonState states.
    idt_lvl += 1
    for (k, v) in attr_dict.items():
        output += tagGexfAttr(k, v, idt_lvl)
    idt_lvl -= 1
    
    # Close node attributes tag and open edge attributes tag.
    output += idt * idt_lvl + '</attributes>' + nl
    output += idt * idt_lvl + '<attributes class="edge">' + nl

    # Build gexf edge attributes (used to specify the types of data
    # that can be stored) from the 'state' dictionary of
    # AutomatonState states.
    idt_lvl += 1
    for (k, v) in attr_dict.items():
        output += tagGexfAttr(k, v, idt_lvl)
    idt_lvl -= 1
    
    # Close edge attributes tag and open nodes tag.
    output += idt * idt_lvl + '</attributes>' + nl
    output += idt * idt_lvl + '<nodes>' + nl
    
    # Build hierarchical gexf nodes.
    idt_lvl += 1
    if not use_clusters:
        aut_id = 0  # Each automaton is numbered, starting from 0.
        for aut in aut_list:
            # Create supernode (a single Automaton) and subnodes.
            output += idt * idt_lvl + '<node id="' + str(aut_id) + \
                      '" label="W' + str(aut_id) + \
                      ': ' + str(label_vars) + \
                      '" />' + nl

            # Build gexf nodes from AutomatonState states.
            for (node, data) in aut.nodes_iter(data=True):
                label = filter(lambda x: x in data["state"].keys(), label_vars)
                label = str(map(lambda x: data["state"][x], label))
                if use_viz:
                    output += tagGexfTaggedNode(aut_id, node, data.copy(), label, idt_lvl)
                else:
                    output += tagGexfNode(aut_id, node, data.copy(), label, idt_lvl)

            aut_id += 1
    else:
        # Hierarchy (clustering) based on ``tags'' attribute
        cluster_ids = []
        for aut in aut_list:
            for (node, data) in aut.nodes_iter(data=True):
                if "tags" in data:
                    tags = data["tags"].copy()
                else:
                    tags = {}
                if (tags is not None) and tags.has_key("cluster_id"):
                    if tags["cluster_id"] not in cluster_ids:
                        cluster_ids.append(tags["cluster_id"])
        null_cluster_id = 0  # For nodes that are not tagged
        cluster_ids.append(null_cluster_id)
        for cluster_id in cluster_ids:
            if cluster_id > null_cluster_id:
                null_cluster_id = cluster_id+1
            output += idt * idt_lvl + '<node id="' + str(cluster_id) + \
                '" label="c' + str(cluster_id) + \
                ': ' + str(label_vars) + \
                '" />' + nl
        for aut in aut_list:
            for (node, data) in aut.nodes_iter(data=True):
                if "tags" in data:
                    tags = data["tags"].copy()
                else:
                    tags = {}
                if (tags is not None) and tags.has_key("cluster_id"):
                    cluster_id = tags["cluster_id"]
                else:
                    cluster_id = null_cluster_id
                label = filter(lambda x: x in data["state"].keys(), label_vars)
                label = str(map(lambda x: data["state"][x], label))
                if use_viz:
                    output += tagGexfTaggedNode(cluster_id, node, node_data, label, idt_lvl)
                else:
                    output += tagGexfNode(cluster_id, node, node_data, label, idt_lvl)
    idt_lvl -= 1
    
    # Close nodes tag and open edges tag.
    output += idt * idt_lvl + '</nodes>' + nl
    output += idt * idt_lvl + '<edges>' + nl
    
    # Build hierarchical gexf edges.
    idt_lvl += 1
    if not use_clusters:
        aut_id = 0
        for aut in aut_list:
            for (node, data) in aut.nodes_iter(data=True):
                for e in aut.out_edges_iter(node):
                    label = filter(lambda x: x in aut.node[e[1]]["state"].keys(), label_vars)
                    label = str(map(lambda x: aut.node[e[1]]["state"][x], label))
                    output += tagGexfEdge(aut_id, node, data.copy(), aut_id, e[1], aut.node[e[1]].copy(),
                                          label, idt_lvl)
            if aut_id > 0:
                # Build edges between automata.
                output += idt * idt_lvl + \
                          '<edge id="' + str(aut_id - 1) + '-' + str(aut_id) + \
                          '" source="' + str(aut_id - 1) + \
                          '" target="' + str(aut_id) + \
                          '" label="W' + str(aut_id - 1) + '-W' + str(aut_id) + \
                          '" />' + nl
            aut_id += 1
    else:
        for aut in aut_list:
            for (node, data) in aut.nodes_iter(data=True):
                if "tags" in data:
                    tags = data["tags"].copy()
                else:
                    tags = {}
                if (tags is not None) and tags.has_key("cluster_id"):
                    cluster_id = tags["cluster_id"]
                else:
                    cluster_id = null_cluster_id
                for e in aut.out_edges_iter(node):
                    if "tags" in aut.node[e[1]]:
                        next_tags = aut.node[e[1]]["tags"].copy()
                    else:
                        next_tags = {}
                    if (next_tags is not None) and next_tags.has_key("cluster_id"):
                        next_cluster_id = next_tags["cluster_id"]
                    else:
                        next_cluster_id = null_cluster_id
                    label = filter(lambda x: x in aut.node[e[1]]["state"].keys(), label_vars)
                    label = str(map(lambda x: aut.node[e[1]]["state"][x], label))
                    output += tagGexfEdge(cluster_id, node, data.copy(),
                                          next_cluster_id, e[1], aut.node[e[1]].copy(),
                                          label, idt_lvl)
    idt_lvl -= 1

    # Close edges, graph, and gexf tags.
    output += idt * idt_lvl + '</edges>' + nl
    idt_lvl -= 1
    output += idt * idt_lvl + '</graph>' + nl
    idt_lvl -= 1
    output += idt * idt_lvl + '</gexf>' + nl

    assert idt_lvl == 0
    
    return output


def changeGexfAttvalue(gexf_string, att_name, att_val,
                       node_id=None, edge_id=None):
    """
    Change an attribute for the given node or edge (or both).

    Arguments:
    gexf_string -- a gexf-formatted string (writable to file). This should have
        been generated by 'dumpGexf'.
    att_name -- the string name of the attribute to be changed.
    att_val -- the new value of the attribute to be changed.
    node_id -- optional id for the node to be changed.
    edge_id -- optional id for the edge to be changed.

    Return:
    A changed gexf output string. If changes are not possible, returns the
    original string.
    """
    if not (isinstance(gexf_string, str) and isinstance(att_name, str)):
        raise TypeError("Invalid arguments to changeGexfAttvalue.")
    
    # Note that 'str.find' returns -1 if pattern isn't found.

    if node_id != None:
        # Search for desired node and set bounds to only this node.
        start = gexf_string.find('<node id="' + node_id)
        end = start + gexf_string[start:].find('</attvalues>')
        
        # Search for desired attvalue and set bounds to only this attvalue.
        start = start + \
                gexf_string[start:end].find('<attvalue for="' + att_name)
        end = start + gexf_string[start:end].find('>') + 1
        
        # Check if attvalue has been found.
        if start != -1:
            gexf_string = gexf_string[:start] + \
                          re.sub(r'value=".*"', 'value="' + str(att_val) + '"',
                                 gexf_string[start:end])+ \
                          gexf_string[end:]
    
    if edge_id != None:
        # Search for desired edge and set bounds to only this edge.
        start = gexf_string.find('<edge id="' + edge_id)
        end = start + gexf_string[start:].find('</attvalues>')
        
        # Search for desired attvalue and set bounds to only this attvalue.
        start = start + \
                gexf_string[start:end].find('<attvalue for="' + att_name)
        end = start + gexf_string[start:end].find('>') + 1
        
        # Check if attvalue has been found.
        if start != -1:
            gexf_string = gexf_string[:start] + \
                          re.sub(r'value=".*"', 'value="' + str(att_val) + '"',
                                 gexf_string[start:end])+ \
                          gexf_string[end:]
    
    return gexf_string

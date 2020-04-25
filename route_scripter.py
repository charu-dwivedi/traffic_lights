#!/usr/local/bin/python3

import xml.etree.ElementTree as ET
from xml_utils import get_route_xml_template, DEFAULT_VTYPE_ID, create_trip_element
from itertools import combinations 
from collections import Counter
from random import randint

def convert_all_intersections_to_lights(net_xml_file, new_net_xml_file):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	for elem in root.findall('junction'):
		elem.set('type', 'traffic_light')
	tree.write(new_net_xml_file)

def get_all_junctions_of_type(root, junc_type):
	node_id_list = [
		elem.get('id') for elem in root.findall('junction') if elem.get('type') == junc_type
	] 
	return node_id_list

def get_all_fringe_routes(root):
	connection_list = [ elem for elem in root.findall('connection')]
	from_set = set([elem.get('from') for elem in connection_list])
	to_set = set([elem.get('to') for elem in connection_list])
	only_from = (from_set ^ to_set) & from_set
	only_to = (from_set ^ to_set) & to_set
	node_combos = [(fr, to) for fr in only_from for to in only_to if not (fr[0] == to[0])]
	## if statement to prevent u-turns, will have to do something about that logic lol
	return node_combos

def create_random_routes_from_fringe_nodes(
	net_xml_file,
	output_rou_xml_file,
	num_cars=100,
):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	route_xml = get_route_xml_template()
	node_combos = get_all_fringe_routes(root)
	num_combos = len(node_combos)
	for x in range(num_cars):
		rand_node = randint(1, num_combos-1)
		route_xml.append(
			create_trip_element(
				'veh{0}'.format(str(x)),
				DEFAULT_VTYPE_ID,
				node_combos[rand_node][0],
				node_combos[rand_node][1]
			)
		)
	new_tree = ET.ElementTree(route_xml)
	new_tree.write(output_rou_xml_file)

def create_uneven_routes_from_fringe_nodes(
	net_xml_file,
	output_rou_xml_file,
	num_cars=100
):	
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	route_xml = get_route_xml_template()
	node_combos = get_all_fringe_routes(root)
	num_combos = len(node_combos)
	predefined_uneven_list = [1, 2, 1, 1, 5, 4, 8, 12] #idk how to truly randomize this
	route_distribution = [
		predefined_uneven_list[randint(0, len(predefined_uneven_list)-1)]
		for x in range(num_combos)
	]
	norm_route_dist = [float(i)/sum(route_distribution) for i in route_distribution]
	num_cars_per_route = [int(i*num_cars) for i in norm_route_dist]
	count = 0
	for x in range(len(num_cars_per_route)):
		for y in range(num_cars_per_route[x]):
			route_xml.append(
				create_trip_element(
					'veh{0}'.format(str(count)),
					DEFAULT_VTYPE_ID,
					node_combos[x][0],
					node_combos[x][1]
				)
			)
			count += 1
	new_tree = ET.ElementTree(route_xml)
	new_tree.write(output_rou_xml_file)
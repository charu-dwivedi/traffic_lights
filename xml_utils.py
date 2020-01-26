#!/usr/local/bin/python3

import xml.etree.ElementTree as ET

DEFAULT_CAR_ATTRIB = {
	'vClass' : 'passenger',
	'length' : '5',
	'accel' : '3.5',
	'decel' : '2.2',
	'sigma' : '1.0',
	'maxSpeed' : '10'
}

DEFAULT_VTYPE_ID = 'veh_passenger'

def get_route_xml_template():
	routes = ET.Element('routes')
	vType = ET.SubElement(routes, 'vType', attrib=DEFAULT_CAR_ATTRIB)
	vType.set('id', DEFAULT_VTYPE_ID)
	return routes

def get_additional_xml_template():
	additional = ET.Element('additional')
	return additional

def create_entry_exit_element(ee_id, ee_out_file, entry_lane_ids, exit_lane_ids, aggregation_period, position_on_lane=1, time_threshold=1, speed_threshold=1.39, openEntry='true'):
	ee_det = ET.Element(
			'entryExitDetector', 
			attrib={
				'id' : ee_id,
				'freq' : aggregation_period,
				'file' : ee_out_file,
				'timeThreshold' : str(time_threshold),
				'speedThreshold' : str(speed_threshold),
				'openEntry' : 'true'
			}
		)
	for entry in entry_lane_ids:
		ET.SubElement(
			ee_det, 
			'detEntry', 
			attrib={
				'lane' : entry,
				'pos' : str(-1*position_on_lane),
			}
		)
	for exit in exit_lane_ids:
		ET.SubElement(
			ee_det, 
			'detExit', 
			attrib={
				'lane' : exit,
				'pos' : str(position_on_lane),
			}
		)
	return ee_det

def get_connection_info(net_xml_file):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	connection_arr = []	
	for elem in root.findall('connection'):
		connection_arr.append(
			(elem.get('from'), elem.get('fromLane'), elem.get('to'), elem.get('toLane'), elem.get('tl'), elem.get('linkIndex'), elem.get('dir'))
		)

def get_entry_exit_sums(entry_exit_log_file):
	tree = ET.parse(entry_exit_log_file)
	root = tree.getroot()
	sum_dict = {}
	for elem in root.findall('interval'):
		ee_id = elem.get('id')
		if ee_id not in sum_dict:
			sum_dict[ee_id] = 0
		sum_dict[ee_id] += int(elem.get('vehicleSum'))
	return sum_dict

def get_edges_and_lanes(net_xml_file):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	edge_dict = {}
	for elem in root.findall('edge'):
		edge_id = elem.get('id')
		edge_dict[edge_id] = {}
		edge_dict[edge_id]['lanes'] = [subelem.get('id') for subelem in elem.findall('lane')]
	return edge_dict

def gen_entry_exit_sensors(net_xml_file, ee_out_file, aggregation_period):
	edges_and_lanes = get_edges_and_lanes(net_xml_file)
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	ee_sensors = []
	connection_dict = {}
	for elem in root.findall('connection'):
		from_lane = elem.get('from')
		to_lane = elem.get('to')
		if from_lane not in connection_dict:
			connection_dict[from_lane] = []
		if to_lane not in connection_dict[from_lane]:
			ee_sensors.append(
				create_entry_exit_element(
					from_lane + '_' + to_lane, 
					ee_out_file,
					edges_and_lanes[from_lane]['lanes'], 
					edges_and_lanes[to_lane]['lanes'],
					str(aggregation_period),
					position_on_lane=0.1
				)
			)
			connection_dict[from_lane].append(to_lane)
	return ee_sensors

def sort_info_by_junction(net_xml_file, info):
	#shitty way to sort lane info by junction
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	junction_sorted = {}
	for elem in root.findall('connection'):
		junc_id = elem.get('tl')
		if len(junc_id) > 0:
			if junc_id not in junction_sorted:
				junction_sorted[junc_id] = {}
			connection = elem.get('from') + '_' + elem.get('to')
			if connection in info:
				junction_sorted[junc_id][connection] = info[connection] 
	return junction_sorted

def get_traffic_logic_dict(net_xml_file):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	traffic_light_logic = {}
	phase_num = 0
	for elem in root.findall('tlLogic'):
		traffic_light_logic[elem.get('id')] = {}
		for ph in elem.findall('phase'):
			traffic_light_logic[elem.get('id')][phase_num] = {
				'duration' : ph.get('duration'),
				'state' : ph.get('state')
			}
			phase_num += 1
	return traffic_light_logic


def get_connection_to_ind_map(net_xml_file):
	tree = ET.parse(net_xml_file)
	root = tree.getroot()
	connection_to_ind = {}
	for elem in root.findall('connection'):
		tl_id = elem.get('tl')
		if tl_id not in connection_to_ind:
			connection_to_ind[tl_id] = {}
		connection_name = elem.get('from') + '_' + elem.get('to')
		connection_to_ind[tl_id][elem.get('linkIndex')] = connection_name
	return connection_to_ind

def gen_additional_file(net_xml_file, output_additional_xml_file, ee_log_file, ee_aggregation_period=360):
	additional = get_additional_xml_template()
	for ee_sensor in gen_entry_exit_sensors(net_xml_file, ee_log_file, ee_aggregation_period):
		additional.append(ee_sensor)
	new_tree = ET.ElementTree(additional)
	new_tree.write(output_additional_xml_file)

def get_ee_sensor_ids(additional_xml_file):
	tree = ET.parse(additional_xml_file)
	root = tree.getroot()
	ee_sensor_ids = [elem.get('id') for elem in root.findall('entryExitDetector')]
	return ee_sensor_ids

def create_trip_element(id, type, from_edge, to_edge, depart='0.00', departLane='best', departSpeed='max'):
	return ET.Element(
		'trip', 
		attrib={
			'id' : id,
			'type' : type,
			'from' : from_edge,
			'to' : to_edge,
			'depart' : depart,
			'departLane' : departLane,
			'departSpeed' : departSpeed
		}
	)


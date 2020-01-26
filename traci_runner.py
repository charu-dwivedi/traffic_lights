#!/usr/local/bin/python3

import os, sys
from xml_utils import get_ee_sensor_ids, sort_info_by_junction, get_traffic_logic_dict, get_connection_to_ind_map, get_entry_exit_sums

if 'SUMO_HOME' in os.environ:
	tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
	sys.path.append(tools)
else:
	sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

# def get_vehicles_at_intersection(additional_xml_file):
# 	ee_sensor_ids = get_ee_sensor_ids(additional_xml_file)
# 	sensor_vehicle_dict = {}
# 	for sensor in ee_sensor_ids:
# 		if sensor not in sensor_vehicle_dict:
# 			sensor_vehicle_dict[sensor] = set()
# 		sensor_vehicle_dict[sensor].update(traci.multientryexit.getLastStepVehicleIDs(sensor))
# 	return sensor_vehicle_dict
#
# def count_total_vehicles(entry_exit_logging_file):
# 	sensor_count_dict = {}
# 	for sensor, sensor_set in sensor_vehicle_dict.items():
# 		sensor_count_dict[sensor] = len(sensor_set)
# 	return sensor_count_dict

# def update_sensor_vehicles(overall_sensor_vehicle_dict, additional_xml_file):
# 	timestep_vehicles = get_vehicles_at_intersection(additional_xml_file)
# 	for sensor in timestep_vehicles:
# 		if sensor not in overall_sensor_vehicle_dict:
# 			overall_sensor_vehicle_dict[sensor] = set()
# 		overall_sensor_vehicle_dict[sensor].update(timestep_vehicles[sensor])
# 	return overall_sensor_vehicle_dict

def init_performance_data():
	return {
		'total_num_steps' : 0
	}

def update_performance_data(performance_data):
	performance_data['total_num_steps'] = performance_data['total_num_steps'] + 1
	return performance_data

def run_traci(traci_files, metadata={},):
	sumo_command  = traci_files['sumo_command']
	entry_exit_log_file = traci_files['entry_exit_logging']
	traci.start(sumo_command)
	performance_data = init_performance_data()
	if len(metadata) > 0:
		apply_meta_updates_to_traci(metadata)
	while traci.simulation.getMinExpectedNumber() > 0:
	   traci.simulationStep()
	   performance_data = update_performance_data(performance_data)
	traci.close()
	overall_sensor_count = get_entry_exit_sums(entry_exit_log_file)
	return overall_sensor_count, performance_data

def gen_traci_metadata_flow(net_xml_file, overall_sensor_count):
	return gen_traci_metadata(
		get_traffic_logic_dict(net_xml_file),
		get_connection_to_ind_map(net_xml_file),
		sort_info_by_junction(net_xml_file, overall_sensor_count)
	)

def gen_traci_metadata(traffic_light_logic, connection_to_ind_map, sensor_count={}):
	traci_metadata = {}
	traci_metadata['traffic_light_logic'] = traffic_light_logic
	traci_metadata['connection_to_ind_map'] = connection_to_ind_map
	traci_metadata['sensor_count'] = sensor_count
	return traci_metadata

def update_traffic_light_logic(traffic_light_logic):
	for light_id, logic in traffic_light_logic.items():
		phases = []
		for ind, ph in logic.items():
			phases.append(traci.trafficlight.Phase(float(ph['duration']), ph['state']))
		new_logic = traci.trafficlight.Logic(light_id+'_updated', 0, 0, phases=phases)
		traci.trafficlight.setCompleteRedYellowGreenDefinition(light_id, new_logic)

def apply_meta_updates_to_traci(traci_metadata):
	update_traffic_light_logic(traci_metadata['traffic_light_logic'])

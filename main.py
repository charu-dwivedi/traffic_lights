#!/usr/local/bin/python3

import sys
import os
import route_scripter 
import xml_utils
import optimizer
import argparse

sys.path.append('/Users/charu/Projects/sumo/tools')

import randomTrips
import tlsCycleAdaptation


NET_XML_FILE = 'osm.net.xml'

ROU_XML_FILE = 'route_file.rou.xml'

ADDITIONAL_XML_FILE = 'additional.xml'

ENTRY_EXIT_LOGGING_FILE = 'ee_log_file.xml'

SUMO_BINARY = "sumo"

SUMOCFG_FILE = 'osm.sumocfg'

TLS_CYCLE_FILE = 'tlsAdaptation.add.xml'

def gen_traci_files(xml_file_path):
	traci_files = {}
	traci_files['net_xml'] = os.path.abspath(os.path.join(xml_file_path, NET_XML_FILE))
	traci_files['rou_xml'] = os.path.abspath(os.path.join(xml_file_path, ROU_XML_FILE))
	traci_files['additional_xml'] = os.path.abspath(os.path.join(xml_file_path, ADDITIONAL_XML_FILE))
	traci_files['entry_exit_logging'] = os.path.abspath(os.path.join(xml_file_path, ENTRY_EXIT_LOGGING_FILE))
	traci_files['sumocfg_xml'] = os.path.abspath(os.path.join(xml_file_path, SUMOCFG_FILE))
	traci_files['tls_adaptation'] = os.path.abspath(os.path.join(xml_file_path, TLS_CYCLE_FILE))
	traci_files['sumo_command'] = [
		SUMO_BINARY, 
		"-c", traci_files['sumocfg_xml'], 
		"--additional-files", traci_files['additional_xml']+','+traci_files['tls_adaptation'],
		"--no-warnings",
	]
	return traci_files

if __name__ == "__main__":
	xml_file_path = sys.argv[1]
	SUMO_BINARY = sys.argv[2]
	algorithm_type = sys.argv[3]
	traci_files = gen_traci_files(xml_file_path)
	random_trips_args = [
		'--net-file', traci_files['net_xml'],
		'--route-file', traci_files['rou_xml'],
		'--fringe-factor', '9.0',
		'--end', 1000
	]
	trip_options = randomTrips.get_options(random_trips_args)
	randomTrips.main(trip_options)
	xml_utils.gen_additional_file(traci_files['net_xml'], traci_files['additional_xml'], traci_files['entry_exit_logging'])
	optimizer.run_optimizer(traci_files, algorithm_type, num_members_per_generation=5)
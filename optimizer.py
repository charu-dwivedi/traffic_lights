#!/usr/local/bin/python3

import os, sys
import traci_runner
import copy
import xml_utils
import random
import numpy as np


sys.path.append('/Users/charu/Projects/sumo/tools')

import tlsCycleAdaptation

def gen_phase_score(sensor_count, phase_state, light_connections):
	phase_score = 0
	for ind, conn_id in light_connections.items():
		if phase_state[int(ind)].lower() == 'g':
			phase_score = phase_score + sensor_count[conn_id] 
	return phase_score

def flow_optimization_step(traci_files):
	tls_cycle_args = [
		'--net-file', traci_files['net_xml'],
		'--route-files', traci_files['rou_xml'],
		'--output-file', traci_files['tls_adaptation'],
	]
	tls_cycle_options = tlsCycleAdaptation.get_options(tls_cycle_args)
	tlsCycleAdaptation.main(tls_cycle_options)
	return {}


def flow_optimizer(traci_files):
	previous_performance = {}
	performance_data = {'sample' : 'sample'}
	traci_metadata = {}
	while previous_performance != performance_data:
		previous_performance = copy.deepcopy(performance_data)
		overall_sensor_count, performance_data = traci_runner.run_traci(traci_files, traci_metadata)
		print(performance_data)
		traci_metadata = flow_optimization_step(traci_files)

def run_optimizer(traci_files, optimizer_type, **options):
	if optimizer_type == 'flow':
		flow_optimizer(traci_files)
	elif optimizer_type == 'evolutionary':
		evolutionary_optimizer(traci_files, options.get('num_members_per_generation'))
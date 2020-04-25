#!/usr/local/bin/python3

import os, sys
import traci_runner
import copy
import xml_utils
import random
import numpy as np
import string



if 'SUMO_HOME' in os.environ:
	tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
	sys.path.append(tools)
	import sumolib
else:
	sys.exit("please declare environment variable 'SUMO_HOME'")

import tlsCycleAdaptation
import traci

global_lane_to_street_map = {}

global_street_id_to_street_obj_map = {}

global_stopping_lanes = set()

tl_id_to_tl_light_obj = {}

INCREMENT_NUM = 5

lane_num_car_values = {}

covered_lane_num = 1

def gen_rand_id(length=8):
	return ''.join([random.choice(string.ascii_letters 
            + string.digits) for n in range(length)]) 


def get_street_obj_from_lane_id(lane_id):
	return global_street_id_to_street_obj_map[global_lane_to_street_map[lane_id]]

class TL_Street:

	def __init__(
		self, 
		street_sequence=[], 
		beg_traffic_light = None, 
		end_traffic_light = None
	):
		self.street_sequence = street_sequence
		self.beg_traffic_light = beg_traffic_light
		self.end_traffic_light = end_traffic_light
		global_lane_to_street_map = {}
		rand_street_id = 'street_' + gen_rand_id()
		while rand_street_id in global_street_id_to_street_obj_map:
			rand_street_id = 'street_' + gen_rand_id()
		self.street_id = rand_street_id
		global_street_id_to_street_obj_map[self.street_id] = self
		for lane_id in street_sequence:
			global_lane_to_street_map[lane_id] = self.street_id

	def set_beg_traffic_light(self, beg_tl_id):
		self.beg_traffic_light = beg_tl_id
	
	def set_end_traffic_light(self, end_tl_id):
		self.end_traffic_light = end_tl_id

	def add_lane_to_street(
		self, 
		lane_id,
	):
		self.street_sequence.append(lane_id)
		global_lane_to_street_map[lane_id] = self.street_id
		traci.lane.subscribe(lane_id, [0x10])

	def visualize_covered_lanes(self):
		global covered_lane_num 
		covered_lane_num += 10
		for lane_id in self.street_sequence:
			traci.edge.setEffort(traci.lane.getEdgeID(lane_id), 100.0)

	def get_num_cars(self):
		return np.sum(
			list(
				map(
					self.get_vehicle_num, 
					self.street_sequence
				)
			)
		)

	def get_vehicle_num(self, lane_id):
		global lane_num_car_values
		return lane_num_car_values[lane_id][0x10]

	def get_avg_speed(self):
		return np.mean(
			list(
				map(
					traci.lane.getLastStepMeanSpeed, 
					self.street_sequence
				)
			)
		)
	
	def get_halting_num(self):
		return np.sum(
			list(
				map(
					traci.lane.getLastStepHaltingNumber, 
					self.street_sequence
				)
			)
		)

def create_street_from_lane(
		lane_id,
	):
	#Given a street, fanout until you hit a stopping lane
		traci_street = TL_Street()
		link_exists = True
		curr_lane = lane_id
		while link_exists:
			link_exists = False
			if curr_lane in traci_street.street_sequence:
				continue
			traci_street.add_lane_to_street(curr_lane)
			links = traci.lane.getLinks(curr_lane, extended=True) #exshtendo  
			stopping_links = list(filter(lambda x: x[4] in global_stopping_lanes, links))
			if len(stopping_links) > 0:
				continue
			if len(links) > 0:
				if len(links) > 1:
					link_exists = True
					straight_links = list(filter(lambda x: x[6]=="s" or x[6]=='t', links))
					if len(straight_links) == 0:
						# prio_links = list(filter(lambda x: x[1], links))
						# curr_lane = prio_links[0][0]
						# going to simplify and exclude left and right turns for now
						link_exists = False
						continue
					else:
						curr_lane = straight_links[0][0]
				elif len(links) == 1:
					link_exists = True
					curr_lane = links[0][0]
		#print(traci_street.street_id) 
		return traci_street


class TL_Light:

	def __init__(self, light_id, junction=False):
		self.tl_id = light_id
		self.controlled_links = traci.trafficlight.getControlledLinks(self.tl_id)
		self.flow_values = [{}]*len(self.controlled_links) #index corresponds to controlled_links index
		self._index_stopping_lanes()

	def _index_stopping_lanes(self):
		for link in self.controlled_links:
			incoming, outgoing, via = link[0]
			global_stopping_lanes.add(via)

	def gen_flow_for_controlled_link(self, incoming_street, outgoing_street):
		flow_dict = {}
		flow_dict['num_cars'] = incoming_street.get_num_cars() + outgoing_street.get_num_cars()
		return flow_dict

	def gen_flow_through_light(self):
		for link_index in range(len(self.controlled_links)):
			incoming, outgoing, via = self.controlled_links[link_index][0]
			incoming_street = get_street_obj_from_lane_id(incoming)
			outgoing_street = get_street_obj_from_lane_id(outgoing)
			self.flow_values[link_index] = self.gen_flow_for_controlled_link(incoming_street, outgoing_street)
		return self.flow_values

	def update_light_logic(self):
		pass

def index_tl_system(tls_list, visualize=False):
	#should be a list of TrafficLight objects
	all_lanes = []
	for tl in tls_list:
		#indexing stopping lanes
		curr_tl = TL_Light(tl._id)
		tl_id_to_tl_light_obj[tl._id] = curr_tl
	#creating streets out of lanes
	for tl_id, tl_obj in tl_id_to_tl_light_obj.items():
		for links in tl_obj.controlled_links:
			in_street = create_street_from_lane(links[0][0])
			out_street = create_street_from_lane(links[0][1])
			in_street.set_end_traffic_light(tl_id)
			out_street.set_beg_traffic_light(tl_id)
		if visualize:
			in_street.visualize_covered_lanes()
			out_street.visualize_covered_lanes()

# def add_remaining_lanes_to_tl_system(net_file):
# 	tree = ET.parse(net_file)
# 	for elem in root.findall('lane'):
		
# 	tree.write(new_net_xml_file)

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

def gen_phase_time_scores_by_num_cars(tl_logic, light_flow):
	g_dict = {}
	for phase_ind in range(len(tl_logic.phases)):
		for x in range(len(tl_logic.phases[phase_ind].state)):
			if tl_logic.phases[phase_ind].state[x].lower() == 'g':
				if x not in g_dict:
					g_dict[x] = set()
				g_dict[x].add(phase_ind)
	phase_time_scores = [0]*len(tl_logic.phases)
	for score_ind in range(len(light_flow)):
		for phase in g_dict[score_ind]:
			phase_time_scores[phase] += light_flow[score_ind]['num_cars']
	return phase_time_scores
	

def gen_new_logic(old_logic, increment):
	new_phases = []
	for x in range(len(old_logic.phases)):
		if 'y' not in old_logic.phases[x].state.lower():
			new_phases.append(
				traci.trafficlight.Phase(
					max(5, old_logic.phases[x].duration + increment[x]),
					old_logic.phases[x].state,
					max(0, old_logic.phases[x].minDur + increment[x]),
					max(10, old_logic.phases[x].maxDur + increment[x]),
				)
			)
		else:
			new_phases.append(old_logic.phases[x])
	new_logic = traci.trafficlight.Logic(
		old_logic.programID,
		0, 
		old_logic.currentPhaseIndex,
		new_phases
	)
	#print("yuh")
	#print(new_logic)
	return new_logic


def gen_increment_from_scores(tl_logic, phase_scores):
	max_ind = 0
	min_ind = 0
	max_score = 0
	min_score = 10000000
	for x in range(len(tl_logic.phases)):
		if 'y' not in tl_logic.phases[x].state.lower():
			if phase_scores[x] > max_score:
				max_score = phase_scores[x]
				max_ind = x
			if phase_scores[x] < min_score:
				min_score = phase_scores[x]
				min_ind = x
	increment_arr = [0]*len(phase_scores)
	increment_arr[max_ind] = INCREMENT_NUM
	increment_arr[min_ind] = -1*INCREMENT_NUM
	return increment_arr

def update_light_logic_based_on_flow(light_id, light_flow):
	#print(light_flow)
	current_programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(light_id)
	main_program = list(filter(lambda x: (x.programID == '0'), current_programs))[0]
	#print(main_program)
	phase_scores = gen_phase_time_scores_by_num_cars(main_program, light_flow)
	increment_phases = gen_increment_from_scores(main_program, phase_scores)
	#print(traci.trafficlight.getNextSwitch(light_id))
	new_program = gen_new_logic(main_program, increment_phases)
	traci.trafficlight.setCompleteRedYellowGreenDefinition(light_id, new_program)
	traci.trafficlight.setProgram(light_id, new_program.programID)
	#print(traci.trafficlight.getNextSwitch(light_id))

def gen_flow_update_lights():
	global lane_num_car_values
	lane_num_car_values  = traci.lane.getAllSubscriptionResults()
	light_flow_dict = {}
	for tl_id, light_obj in tl_id_to_tl_light_obj.items():
		light_flow_dict[tl_id] = light_obj.gen_flow_through_light()
		#indices are the same as the tl light
		connections = light_obj.controlled_links
		update_light_logic_based_on_flow(tl_id, light_flow_dict[tl_id])

def dynamic_optimizer_test(traci_files):
	sumo_command  = traci_files['sumo_command']
	net = sumolib.net.readNet(traci_files['net_xml'], withPrograms=True, withPedestrianConnections=True)
	tlsList = net.getTrafficLights()
	traci.start(sumo_command)
	index_tl_system(tlsList, visualize=True)
	#add_remaining_lanes_to_tl_system(traci_files['net_xml'])
	count_steps = 0
	while traci.simulation.getMinExpectedNumber() > 0:
		if count_steps % 100 == 0 and count_steps != 0 :
			gen_flow_update_lights()
			print("Calculating tl lengths at ", count_steps)
		count_steps += 1
		traci.simulationStep()
	print({'total_num_steps': count_steps})
	traci.close()


def baseline_run(traci_files):
	overall_sensor_count, performance_data = traci_runner.run_traci_simple(traci_files, {})
	print(performance_data)


def flow_optimizer(traci_files):
	previous_performance = {}
	performance_data = {'sample' : 'sample'}
	traci_metadata = {}
	baseline_run(traci_files)
	while previous_performance != performance_data:
		previous_performance = copy.deepcopy(performance_data)
		overall_sensor_count, performance_data = traci_runner.run_traci_simple(traci_files, traci_metadata)
		print(performance_data)
		traci_metadata = flow_optimization_step(traci_files)

def run_optimizer(traci_files, optimizer_type, **options):
	print("baseline")
	baseline_run(traci_files)
	if optimizer_type == 'flow':
		flow_optimizer(traci_files)
	elif optimizer_type == 'evolutionary':
		print("dynamic")
		dynamic_optimizer_test(traci_files)
import pyhop
import json

def check_enough(state, ID, item, num):
	if getattr(state,item)[ID] >= num: return []
	return False

def produce_enough(state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def make_method(name, rule):
	def method(state, ID):
		# your code here
		subtasks = []
		
		# Add requirements (tools) - these must be available
		if 'Requires' in rule:
			for tool, amount in rule['Requires'].items():
				subtasks.append(('have_enough', ID, tool, amount))
		
		# Add consumables - these will be consumed
		if 'Consumes' in rule:
			for item, amount in rule['Consumes'].items():
				subtasks.append(('have_enough', ID, item, amount))
		
		# Finally, add the operator itself
		op_name = 'op_' + name.replace(' ', '_').replace('-', '_')
		subtasks.append((op_name, ID))
		
		return subtasks
	
	method.__name__ = 'method_' + name.replace(' ', '_').replace('-', '_')
	# Store the rule so heuristic can access it
	method.rule = rule
	return method


def declare_methods(data):
	# some recipes are faster than others for the same product even though they might require extra tools
	# sort the recipes so that faster recipes go first

	# your code here
	# hint: call make_method, then declare the method to pyhop using pyhop.declare_methods('foo', m1, m2, ..., mk)	
	recipes_by_product = {}
	for recipe_name, rule in data['Recipes'].items():
		for product in rule['Produces'].keys():
			if product not in recipes_by_product:
				recipes_by_product[product] = []
			recipes_by_product[product].append((recipe_name, rule))
	
	# Build tool dependency graph to avoid circular deps
	tools = set(data['Tools'])
	
	# For each product, sort recipes intelligently
	for product, recipes in recipes_by_product.items():
		def recipe_sort_key(recipe_tuple):
			recipe_name, rule = recipe_tuple
			num_requirements = len(rule.get('Requires', {}))
			num_consumables = len(rule.get('Consumes', {}))
			time_cost = rule.get('Time', 0)
			
			# Get required tools
			required_tools = set(rule.get('Requires', {}).keys())
			
			tool_circularity_penalty = 0
			if product in tools:
				for req_tool in required_tools:
					if req_tool == product:
						tool_circularity_penalty += 1000  # Same tool - circular!
					elif req_tool in tools:
						tool_tier = {'wooden': 1, 'stone': 2, 'iron': 3}
						product_tier = 0
						req_tier = 0
						for tier_name, tier_val in tool_tier.items():
							if tier_name in product:
								product_tier = tier_val
							if tier_name in req_tool:
								req_tier = tier_val
						if req_tier >= product_tier:
							tool_circularity_penalty += 100
			
			return (tool_circularity_penalty, num_requirements, num_consumables, time_cost)
		
		sorted_recipes = sorted(recipes, key=recipe_sort_key)
		
		methods = []
		for recipe_name, rule in sorted_recipes:
			method = make_method(recipe_name, rule)
			methods.append(method)
		
		task_name = 'produce_{}'.format(product)
		pyhop.declare_methods(task_name, *methods)					

def make_operator(rule):
	def operator(state, ID):
		# your code here
		if state.time[ID] < rule.get('Time', 0):
			return False
		
		# Check if we have all required tools
		if 'Requires' in rule:
			for tool, amount in rule['Requires'].items():
				if getattr(state, tool)[ID] < amount:
					return False
		
		# Check if we have all consumable items
		if 'Consumes' in rule:
			for item, amount in rule['Consumes'].items():
				if getattr(state, item)[ID] < amount:
					return False
		
		# Consume items
		if 'Consumes' in rule:
			for item, amount in rule['Consumes'].items():
				getattr(state, item)[ID] -= amount
		
		# Produce items
		if 'Produces' in rule:
			for item, amount in rule['Produces'].items():
				getattr(state, item)[ID] += amount
		
		# Consume time
		state.time[ID] -= rule.get('Time', 0)
		
		return state
	
	return operator

	return operator

def declare_operators(data):
	# your code here
	# hint: call make_operator, then declare the operator to pyhop using pyhop.declare_operators(o1, o2, ..., ok)
	operators = []
	for recipe_name, rule in data['Recipes'].items():
		# Create a safe operator name
		op_name = 'op_' + recipe_name.replace(' ', '_').replace('-', '_')
		op = make_operator(rule)
		op.__name__ = op_name
		operators.append(op)
	
	# Declare all operators at once
	pyhop.declare_operators(*operators)

def add_heuristic(data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters: 
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)
	def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		# your code here
		if curr_task[0].startswith('produce_'):
			item_being_produced = curr_task[0].replace('produce_', '')
			
			# Extract all production tasks from calling stack
			production_stack = [task[0].replace('produce_', '') 
			                    for task in calling_stack 
			                    if task[0].startswith('produce_')]
			
			# Count occurrences
			count = production_stack.count(item_being_produced)
			
			# Be permissive - only prune obvious infinite loops
			if count >= 3:
				return True
		
		# Depth limit
		if depth > 400:
			return True
		
		return False

	pyhop.add_check(heuristic)


def define_ordering(data, ID):
	# if needed, use the function below to return a different ordering for the methods
	# note that this should always return the same methods, in a new order, and should not add/remove any new ones
	def reorder_methods(state, curr_task, tasks, plan, depth, calling_stack, methods):
		if curr_task[0].startswith('produce_'):
			item_to_produce = curr_task[0].replace('produce_', '')
			
			# Get list of tools currently being produced in calling stack
			tools_in_production = set()
			for task in calling_stack:
				if task[0].startswith('produce_'):
					item = task[0].replace('produce_', '')
					if item in data['Tools']:
						tools_in_production.add(item)
			
			# Filter and score methods
			valid_methods = []
			for method in methods:
				# Check if this method requires a tool that's currently being produced
				if hasattr(method, 'rule'):
					required_tools = set(method.rule.get('Requires', {}).keys())
					# If any required tool is currently being produced, skip this method
					if required_tools & tools_in_production:
						continue  # Skip this method - it would create circular dependency
				
				# Get subtasks and score
				subtasks = pyhop.get_subtasks(method, state, curr_task)
				if subtasks == False:
					continue
				
				# Score based on how many requirements/consumables we already have
				score = 0
				for subtask in subtasks:
					if subtask[0] == 'have_enough':
						item = subtask[2]
						needed = subtask[3]
						current = getattr(state, item, {}).get(ID, 0)
						if current >= needed:
							score -= 10  # Reward if we already have it
						else:
							score += 1  # Penalty if we need to produce it
				
				valid_methods.append((score, method))
			
			# If we filtered out all methods, return original list
			# (let the heuristic handle it)
			if not valid_methods:
				return methods
			
			# Sort by score (lower is better) and return methods
			valid_methods.sort(key=lambda x: x[0])
			return [m[1] for m in valid_methods]
		
		return methods
	
	pyhop.define_ordering(reorder_methods)

def set_up_state(data, ID):
	state = pyhop.State('state')
	setattr(state, 'time', {ID: data['Problem']['Time']})

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Problem']['Initial'].items():
		setattr(state, item, {ID: num})

	return state

def set_up_goals(data, ID):
	goals = []
	for item, num in data['Problem']['Goal'].items():
		goals.append(('have_enough', ID, item, num))

	return goals

if __name__ == '__main__':
	import sys
	rules_filename = 'crafting.json'
	if len(sys.argv) > 1:
		rules_filename = sys.argv[1]

	with open(rules_filename) as f:
		data = json.load(f)

	state = set_up_state(data, 'agent')
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')
	define_ordering(data, 'agent')

	# pyhop.print_operators()
	# pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=1)
	# pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)

# HTN Planning for Minecraft - Implementation Report

## Implementation Details

### Part 1: Manual HTN (manualHTN.py)

Successfully solves: **Given {}, achieve {'wood': 12} [time <= 46]**

**Operators Implemented:**
- `op_punch_for_wood` - Get 1 wood in 4 time (no requirements)
- `op_craft_plank` - Convert 1 wood → 4 planks in 1 time
- `op_craft_stick` - Convert 2 planks → 4 sticks in 1 time
- `op_craft_bench` - Convert 4 planks → 1 bench in 1 time
- `op_craft_wooden_axe_at_bench` - Craft wooden axe (requires bench, consumes 3 planks + 2 sticks)
- `op_wooden_axe_for_wood` - Get 1 wood in 2 time (requires wooden_axe)

**Methods Implemented:**
- `produce_wood`: Two methods: using wooden_axe (faster, 2 time) or punching (slower, 4 time)
- `produce_plank`: Craft from wood
- `produce_stick`: Craft from planks
- `produce_bench`: Craft from planks
- `produce_wooden_axe`: Craft at bench with requirements

**Strategy:**
The planner creates a wooden axe first to speed up wood production. The solution:
1. Punch for initial wood
2. Craft planks and bench  
3. Craft wooden axe
4. Use wooden axe to gather remaining wood

### Part 2: Automated HTN (autoHTN.py)

**Successfully solves:**
- ✓ Test (a): Given {'plank': 1}, achieve {'plank': 1} [time <= 0] - 0 actions
- ✓ Test (b): Given {}, achieve {'plank': 1} [time <= 300] - 2 actions  
- ✓ Test (c): Given {'plank': 3, 'stick': 2}, achieve {'wooden_pickaxe': 1} [time <= 10] - 4 actions

**Fails:**
- ✗ Test (d): Given {}, achieve {'iron_pickaxe': 1} [time <= 100]
- ✗ Test (e): Given {}, achieve {'cart': 1, 'rail': 10} [time <= 175]
- ✗ Test (f): Given {}, achieve {'cart': 1, 'rail': 20} [time <= 250]

### Implementation

#### 1. Operator (`make_operator`)
Creates operators from JSON recipes by:
- Checking time availability
- Verifying tool requirements (Requires)
- Verifying consumable availability (Consumes)
- Consuming items and time
- Producing output items

#### 2. Method (`make_method`)
Creates methods that decompose production tasks into:
- `have_enough` checks for required tools
- `have_enough` checks for consumable items
- The operator itself

#### 3. Method Ordering (`declare_methods`)
Sorts recipes for the same product using a scoring function:
```python
score = (num_requirements, num_consumables, time_cost)
```

Prioritizes:
1. Recipes with no tool requirements (simpler)
2. Recipes with fewer consumables
3. Faster recipes

**Conclusion:** Recipes with no requirements (like "punch for wood") should be tried before recipes that require tools (like "wooden_axe for wood"), especially early in planning when tools aren't available yet.

#### 4. Runtime Method Reordering (`define_ordering`)
Reorders methods based on current state by scoring each method:
- -10 points if we already have required items
- +1 point for each item we need to produce

Makes sure the planner tries methods where preconditions are already satisfied before attempting methods that need additional production.

#### 5. Pruning Heuristic (`add_heuristic`)
Prevents infinite loops by detecting circular dependencies:

```python
if curr_task[0].startswith('produce_'):
    item_being_produced = curr_task[0].replace('produce_', '')
    count = items_in_stack.count(item_being_produced)
    
    # Essential building blocks can appear twice
    essential_items = ['wood', 'plank', 'stick', 'bench']
    if item_being_produced in essential_items:
        if count >= 2:
            return True  # Prune
    else:
        if count >= 1:
            return True  # Prune
```

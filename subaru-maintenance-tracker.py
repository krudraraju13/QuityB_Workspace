import os
import sys
import json
import datetime

# Attempt to import optional libraries
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import rich
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm, IntPrompt
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class MaintenanceScheduler:
    def __init__(self, mileage, severe=False):
        self.mileage = mileage
        self.severe = severe

    def get_schedule(self):
        items = []
        history = load_history()
        has_history = len(history) > 0
        min_history_mileage = min([entry['mileage'] for entry in history]) if has_history else 0

        def check_due(name, interval):
            # Special case for coolant
            if name == "Replace Engine Coolant (Super Coolant)":
                if self.mileage < 137500:
                    ms = 0
                else:
                    ms = 137500 + ((self.mileage - 137500) // 75000) * 75000
                
                if not has_history or self.mileage < min_history_mileage:
                    is_due = (self.mileage > 0) and (self.mileage == 137500 or (self.mileage > 137500 and (self.mileage - 137500) % 75000 == 0))
                else:
                    last_completed = max([entry['mileage'] for entry in history if name in entry.get('completed_items', [])], default=0)
                    is_due = (ms > 0 and last_completed < ms and ms >= min_history_mileage)
                
                overdue_since = ms if (is_due and ms < self.mileage) else 0
                is_carried_forward = (overdue_since > 0)
                return is_due, overdue_since, is_carried_forward
            
            # Standard integer intervals
            if not has_history or self.mileage < min_history_mileage:
                is_due = (self.mileage > 0 and self.mileage % interval == 0)
                overdue_since = 0
                is_carried_forward = False
                return is_due, overdue_since, is_carried_forward
            
            ms = (self.mileage // interval) * interval if interval > 0 else 0
            last_completed = max([entry['mileage'] for entry in history if name in entry.get('completed_items', [])], default=0)
            is_due = (ms > 0 and last_completed < ms and ms >= min_history_mileage)
            
            overdue_since = ms if (is_due and ms < self.mileage) else 0
            is_carried_forward = (overdue_since > 0)
            return is_due, overdue_since, is_carried_forward

        # 1. Engine Oil & Oil Filter
        oil_interval = 3000 if self.severe else 6000
        is_oil_due, oil_overdue, oil_cf = check_due("Replace Engine Oil & Filter", oil_interval)
        items.append({
            "name": "Replace Engine Oil & Filter",
            "interval": oil_interval,
            "due": is_oil_due,
            "overdue_since": oil_overdue,
            "is_carried_forward": oil_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "EJ engines are highly sensitive to oil quality. Severe driving conditions require replacement every 3,000 miles or 3 months to prevent bearing wear.",
            "source": "Warranty booklet / GarageHub",
            "oil_grade": "5W-30 Full Synthetic (Standard Spec) or 5W-40 in hotter climates / heavy use",
            "part_number": "15208AA15A (Black Tokyo Roki filter or blue OEM) & 803916010 (Drain Plug Crush Gasket)",
            "quantity": "5.1 US Quarts (approx. 4.8 Liters)",
            "specs": "Drain Plug Torque: 30-33 ft-lb (41-44 N·m). Always use a new crush gasket. Wait 5 minutes after shutdown on level ground before checking dipstick.",
            "steps": [
                "Ensure engine is warm, then safely raise vehicle and remove undertray.",
                "Position drain pan under oil pan drain plug, unscrew plug, and drain oil completely.",
                "Remove old drain plug gasket and install new copper crush gasket (803916010) onto plug.",
                "Reinstall and torque drain plug to 33 ft-lb.",
                "Remove old oil filter from top/bottom engine block, lubricate new filter's rubber seal with fresh oil, and hand-tighten 3/4 turn after gasket contacts surface.",
                "Fill engine slowly with 5.1 quarts of fresh 5W-30 synthetic oil.",
                "Crank engine with fuel pump fuse removed for 10s to prime oil galleries. Reinstall fuse, start engine, check for leaks, shut off, wait 5 min, and verify dipstick level."
            ]
        })

        # 2. Timing Belt
        tb_interval = 60000 if self.severe else 105000
        is_tb_due, tb_overdue, tb_cf = check_due("Replace Timing Belt (Complete Assembly)", tb_interval)
        items.append({
            "name": "Replace Timing Belt (Complete Assembly)",
            "interval": tb_interval,
            "due": is_tb_due,
            "overdue_since": tb_overdue,
            "is_carried_forward": tb_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "EJ series is an interference engine; a snapped belt will destroy the cylinder heads. Replace belt, water pump, tensioner, and idler pulleys at the same time.",
            "source": "Warranty booklet / GarageHub",
            "oil_grade": "N/A",
            "part_number": "13028AA240 (Timing Belt), 21111AA240 (Water Pump), 13033AA042 (Tensioner & Pulley)",
            "quantity": "1 Complete Kit (Belt, Water Pump, Tensioner, 3 Idler Pulleys, 1 Cogged Idler, Belt Guide)",
            "specs": "Interference cylinder head clearance. Alignment keyway must sit strictly at 6:00 position before routing to avoid piston-to-valve contact.",
            "steps": [
                "Disconnect battery, drain coolant completely, and remove cooling fans and radiator hoses.",
                "Remove drive belts, alternator bracket, and main crankshaft pulley (torque spec: 94 ft-lb on reinstall).",
                "Remove plastic timing belt covers (left, center, right).",
                "Turn crankshaft clockwise until timing mark on crankshaft sprocket aligns with crankcase seam, setting keyway strictly at 6:00 (camshafts are now unloaded).",
                "Unbolt tensioner, slide off timing belt, and remove old water pump and idler pulleys.",
                "Install new water pump with new gasket, install new idlers, and bolt on new tensioner assembly (leave lock pin in place).",
                "Route new timing belt, aligning belt lines with marks on cam sprockets and crank sprocket.",
                "Double-check all sprockets, pull the tensioner lock pin, and rotate crankshaft two full turns to verify timing marks still align perfectly."
            ]
        })

        # 3. Replace Spark Plugs
        spark_interval = 60000
        is_spark_due, spark_overdue, spark_cf = check_due("Replace Spark Plugs", spark_interval)
        items.append({
            "name": "Replace Spark Plugs",
            "interval": spark_interval,
            "due": is_spark_due,
            "overdue_since": spark_overdue,
            "is_carried_forward": spark_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "Delicate aluminum cylinder head threads require correct torque (15.5 ft-lb). Tuned or tracked cars place much higher thermal loads, requiring shorter plug life.",
            "source": "Warranty booklet / My Pro Street",
            "oil_grade": "N/A",
            "part_number": "NGK ILZKR7B-11S (OEM Iridium) or equivalent, 10966AA040 (Spark Plug Tube Seals)",
            "quantity": "4 Spark Plugs",
            "specs": "Spark Plug Torque: 15.5 ft-lb (21 N·m). Ignition Coil Bolt Torque: 11.8 ft-lb (16 N·m). Always torque dry threads without anti-seize unless specified.",
            "steps": [
                "Disconnect battery and remove air intake duct (passenger side) and windshield washer bottle (driver side) to gain clearance to frame rail.",
                "Disconnect ignition coil harness plugs, remove the 10mm retaining bolt on each coil, and pull the direct ignition coils straight out.",
                "Use a compressor or canned air to blow out any loose road dust or dirt from inside the spark plug tubes.",
                "Use a 5/8-inch (16mm) spark plug socket, a locking 3-inch extension, and a ratchet to loosen and extract the old plugs.",
                "Check gap of new iridium plugs (do not touch delicate center electrode). Hand-thread new plugs into the head to prevent cross-threading.",
                "Torque spark plugs strictly to 15.5 ft-lb. Reinstall coils, torque coil bolts to 11.8 ft-lb, and reconnect electrical harness."
            ]
        })

        # 4. Replace Brake & Clutch Fluid
        brake_interval = 15000 if self.severe else 24000
        is_brake_due, brake_overdue, brake_cf = check_due("Replace Brake & Clutch Fluid", brake_interval)
        items.append({
            "name": "Replace Brake & Clutch Fluid",
            "interval": brake_interval,
            "due": is_brake_due,
            "overdue_since": brake_overdue,
            "is_carried_forward": brake_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "Hydraulic fluid absorbs moisture over time. Replace every 15,000 miles if operated in mountain or high-humidity areas.",
            "source": "Warranty booklet / GarageHub",
            "oil_grade": "DOT 4 High-Boiling Point Synthetic (or DOT 5.1 for heavy track duty)",
            "part_number": "Subaru OEM Brake Fluid (or premium DOT 4/5.1 equivalent)",
            "quantity": "approx. 1 Liter",
            "specs": "Do not use silicone-based DOT 5. Keep fluid off painted surfaces as it acts as a solvent and eats paint immediately.",
            "steps": [
                "Ensure vehicle is levelly supported. Clean master cylinder cap area, open cap, and extract dark, old fluid using a syringe.",
                "Refill master cylinder reservoir to the 'MAX' line with fresh DOT 4 fluid.",
                "Begin bleeding farthest from master cylinder: Passenger-Rear caliper. Connect bleed hose to nipple and submerge end in a bottle of clean fluid.",
                "Have helper pump brake pedal 3 times and hold. Open bleeder valve, let fluid flow out, close valve, then instruct helper to release pedal.",
                "Repeat process until fluid runs clean, clear, and air-bubble free. Keep reservoir topped off with fresh fluid throughout.",
                "Progress sequentially through other calipers: Driver-Front, Driver-Rear, and Passenger-Front.",
                "Locate manual transmission clutch slave cylinder bleeder on top of transmission bellhousing and repeat bleeding process for clutch circuit."
            ]
        })

        # 5. Replace Gear Oils (MT & Front/Rear Differentials)
        gear_interval = 15000 if self.severe else 30000
        is_gear_due, gear_overdue, gear_cf = check_due("Replace Gear Oils (MT & Front/Rear Differentials)", gear_interval)
        items.append({
            "name": "Replace Gear Oils (MT & Front/Rear Differentials)",
            "interval": gear_interval,
            "due": is_gear_due,
            "overdue_since": gear_overdue,
            "is_carried_forward": gear_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "Protects AWD components. The STI's DCCD center differential is highly sensitive and requires specialized GL-5 gear oil.",
            "source": "Warranty booklet / GarageHub",
            "oil_grade": "Subaru Gear Oil GL-5 75W-90 (Diffs) / GL-4 or GL-5 compatible 75W-90 (MT)",
            "part_number": "Subaru Extra MT 75W-90 (Manual Transmission), Subaru Gear Oil STI (DCCD/Rear Differential)",
            "quantity": "MT / Front Diff: ~3.7-4.1 Quarts; Rear Diff: ~1.0 Quart",
            "specs": "Ensure correct API rating. Rear differential uses a 1/2-inch square drive or Torx T70 drain plug. Tighten plugs to 36 ft-lb.",
            "steps": [
                "Drive vehicle briefly to warm up gear fluids, then lift vehicle completely level on jack stands.",
                "REMOVE THE FILL PLUG FIRST! If fill plug is seized and you drained the oil first, the car will be stranded.",
                "Place drain pan, remove drain plug, and let gear oil empty completely. Wipe metal shavings off magnetic drain plugs.",
                "Reinstall drain plug using a new copper or aluminum sealing washer, torquing to 36 ft-lb.",
                "Pump fresh 75W-90 gear oil into fill hole until a small stream begins to trickle back out of the hole.",
                "Reinstall fill plug and torque. Repeat process for both manual transmission/front differential and rear differential housings."
            ]
        })

        # 6. Replace Fuel Filter
        fuel_filter_interval = 72000
        is_ff_due, ff_overdue, ff_cf = check_due("Replace Fuel Filter", fuel_filter_interval)
        items.append({
            "name": "Replace Fuel Filter",
            "interval": fuel_filter_interval,
            "due": is_ff_due,
            "overdue_since": ff_overdue,
            "is_carried_forward": ff_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "In-tank fuel filter prevents fuel pressure drops and starvation under high-boost conditions.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "42072AA200 (OEM In-Tank Fuel Filter element) or equivalent",
            "quantity": "1 Filter Element",
            "specs": "Ensure fuel tank is less than 1/4 full to prevent overflow. Disconnect battery negative terminal and work in a highly ventilated area.",
            "steps": [
                "Locate fuel pump fuse under dashboard, pull it, and crank engine until it stalls to depressurize fuel lines. Disconnect battery negative terminal.",
                "Remove rear seat bottom cushion, unbolt metal access hatch plate on passenger side, and vacuum any dirt/dust.",
                "Carefully squeeze quick-release tabs and slide off fuel feed and return lines (wrap with clean shop rag to catch spray).",
                "Unplug fuel pump electrical harness connector.",
                "Unbolt retaining ring nut and lift fuel pump hanger assembly slowly from fuel tank, taking care not to bend float arm.",
                "Disassemble plastic pump hanger brackets, release holding clips, swap out dirty fuel filter element for new filter, and replace rubber seals.",
                "Reassemble hanger, lower into tank with new main ring gasket, torque flange nuts, reconnect lines/plugs, reinstall fuse, and cycle key to prime system."
            ]
        })

        # 7. Replace PCV Valve
        pcv_interval = 60000
        is_pcv_due, pcv_overdue, pcv_cf = check_due("Replace PCV Valve", pcv_interval)
        items.append({
            "name": "Replace PCV Valve",
            "interval": pcv_interval,
            "due": is_pcv_due,
            "overdue_since": pcv_overdue,
            "is_carried_forward": pcv_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": "A clogged PCV valve can cause elevated crankcase pressure, blow-by, oil leaks, and higher engine oil consumption.",
            "source": "Service TSB / GarageHub",
            "oil_grade": "N/A",
            "part_number": "11810AA130 or equivalent",
            "quantity": "1 PCV Valve",
            "specs": "Thread into block: torque to 14 ft-lb (19 N·m). Clogged valves lead to elevated crankcase pressure, pushing oil out cover gaskets.",
            "steps": [
                "Locate the PCV valve threaded into the block/crankcase seam beneath the throttle body and intake manifold.",
                "Squeeze hose clamps and disconnect rubber ventilation hoses from the valve assembly.",
                "Use a deep-well socket to unscrew PCV valve counterclockwise and remove it.",
                "Check rubber hoses for hardening, cracking, or blockages, and blow clean with brake cleaner or replace if degraded.",
                "Thread new PCV valve in by hand to prevent cross-threading in aluminum threads, then torque to 14 ft-lb.",
                "Reattach hoses and secure clamps."
            ]
        })

        # 8. Perform Tire Rotation
        tire_interval = 12000
        is_tire_due, tire_overdue, tire_cf = check_due("Perform Tire Rotation", tire_interval)
        items.append({
            "name": "Perform Tire Rotation",
            "interval": tire_interval,
            "due": is_tire_due,
            "overdue_since": tire_overdue,
            "is_carried_forward": tire_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": "Crucial to maintain identical tire diameters (within 1/16 in) to prevent strain on the center differential.",
            "source": "Warranty booklet / Quirk Works",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "4 Wheels Rotated",
            "specs": "Wheel Lug Nut Torque: 88.5 ft-lb (120 N·m). Tread depth mismatch exceeding 1/16 inch (1.6mm/2-32nds) can destroy the DCCD center differential.",
            "steps": [
                "With car on ground, loosen wheel lug nuts slightly using a breaker bar and 19mm socket.",
                "Raise vehicle levelly on jack stands. Inspect tires for uneven feathering, cupping, or punctures.",
                "Measure tread depth across inside, center, and outside block of all 4 tires (ensure within 1/16 in matching).",
                "Rotate tires: For non-directional tires, cross front tires to rear (LF to RR, RF to LR) and move rears straight up. Move straight up/down for directional tires.",
                "Lower vehicle until tires touch ground, torque lug nuts in star pattern to 88.5 ft-lb using hand torque wrench."
            ]
        })

        # 9. Replace Engine Air Filter
        air_interval = 15000 if self.severe else 30000
        is_air_due, air_overdue, air_cf = check_due("Replace Engine Air Filter", air_interval)
        items.append({
            "name": "Replace Engine Air Filter",
            "interval": air_interval,
            "due": is_air_due,
            "overdue_since": air_overdue,
            "is_carried_forward": air_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": "Maintains optimal intake airflow and engine filtration. Replace more frequently in dusty conditions.",
            "source": "Warranty booklet / GarageHub",
            "oil_grade": "N/A",
            "part_number": "16546AA12A (OEM Air Filter) or equivalent",
            "quantity": "1 Filter",
            "specs": "Inspect more frequently in dusty environments. Ensure filter frame is completely flush in airbox slots to avoid unmetered air leaks.",
            "steps": [
                "Locate plastic air cleaner housing on passenger side of engine bay.",
                "Release the two metal tension spring clips on the top cover of the box.",
                "Separate the airbox cover slightly and pull the old filter element straight out.",
                "Wipe clean any road dust, leaves, or sand from inside bottom airbox basin with dry micro-fiber cloth.",
                "Slide new filter element in, ensuring rubber sealing frame rests flat in airbox groove.",
                "Reengage plastic cover locating tabs at the bottom, close cover, and snap tension clips shut."
            ]
        })

        # 10. Replace HVAC Cabin A/C Filter
        cabin_interval = 12000
        is_cabin_due, cabin_overdue, cabin_cf = check_due("Replace HVAC Cabin A/C Filter", cabin_interval)
        items.append({
            "name": "Replace HVAC Cabin A/C Filter",
            "interval": cabin_interval,
            "due": is_cabin_due,
            "overdue_since": cabin_overdue,
            "is_carried_forward": cabin_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": "Keeps the passenger compartment free of pollen, dust, and dynamic road contaminants.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "72880FG000 (OEM Cabin Filter) or equivalent",
            "quantity": "1 Filter",
            "specs": "Replace once a year. Slower cabin airflow or sour smells are typical signs of a clogged filter.",
            "steps": [
                "Open glovebox door. Locate plastic stopper cord/damper arm on right exterior side of box.",
                "Squeeze holding pin and slide damper arm off holding peg.",
                "Push inward on both left and right glovebox sidewalls to clear plastic rubber stoppers, letting box drop down completely.",
                "Locate rectangular cabin filter frame lid behind dash compartment. Squeeze the two lock clips to pull tray out.",
                "Remove old filter element from frame, noting the 'AIR FLOW' arrow pointing downwards.",
                "Insert new cabin filter matching arrow direction, push tray in until it clicks, lift glovebox, re-hook damper arm, and close."
            ]
        })

        # 11. Inspect Accessory Drive Belts
        db_interval = 30000
        is_db_due, db_overdue, db_cf = check_due("Inspect Accessory Drive Belts", db_interval)
        items.append({
            "name": "Inspect Accessory Drive Belts",
            "interval": db_interval,
            "due": is_db_due,
            "overdue_since": db_overdue,
            "is_carried_forward": db_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Check alternator and A/C compressor accessory drive belts for wear, dry-rot, cracking, or tension issues.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "N/A",
            "specs": "Replace immediately if belt ribs have cracks every 1/2 inch or have chunks missing.",
            "steps": [
                "Remove metal belt pulley guard shield on front upper section of engine block.",
                "Visually check alternator and power steering belt, plus lower A/C compressor belt.",
                "Check for dry-rot cracks along the ribbed interior faces of both belts.",
                "Verify belt tension by pressing down on longest span between pulleys (deflection should not exceed 1/4 inch)."
            ]
        })

        # 12. Inspect Cooling System, Hoses & Connections
        cool_hose_interval = 30000
        is_cool_hose_due, cool_hose_overdue, cool_hose_cf = check_due("Inspect Cooling System, Hoses & Connections", cool_hose_interval)
        items.append({
            "name": "Inspect Cooling System, Hoses & Connections",
            "interval": cool_hose_interval,
            "due": is_cool_hose_due,
            "overdue_since": cool_hose_overdue,
            "is_carried_forward": cool_hose_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Examine water hoses, coolant crossover tubes, and clamps for leaks or rubber deterioration.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "N/A",
            "specs": "Cooling system operates under high pressure (approx. 15-18 psi). Inspect when warm to catch pinhole leaks.",
            "steps": [
                "Visually trace upper and lower radiator rubber hoses, heater core hoses, and expansion tank hoses.",
                "Check for white or crusty dried blue coolant spots around hose clamp connections.",
                "Gently squeeze hoses when cool to check for soft, spongy rubber or dry brittleness.",
                "Inspect radiator end tanks for hairline plastic cracks and check radiator cap seal state."
            ]
        })

        # 13. Inspect Brake Pads, Rotors, Axle Boots & Joints
        brake_inspect_interval = 6000 if self.severe else 12000
        is_bi_due, bi_overdue, bi_cf = check_due("Inspect Brake Pads, Rotors, Axle Boots & Joints", brake_inspect_interval)
        items.append({
            "name": "Inspect Brake Pads, Rotors, Axle Boots & Joints",
            "interval": brake_inspect_interval,
            "due": is_bi_due,
            "overdue_since": bi_overdue,
            "is_carried_forward": bi_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Verify pad thickness and inspect CV boots for tearing, cracking, or leakage which ruins joints.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "N/A",
            "specs": "Replace brake pads if friction material is under 3mm. CV boot split allows dirt to destroy CV axle joint quickly.",
            "steps": [
                "Safely raise and secure vehicle, then remove wheels.",
                "Peer through caliper inspection ports to check inner/outer brake pad friction lining thickness.",
                "Inspect rotors for heavy lip ridges, gouges, scoring, or hot spot discoloration.",
                "Crawl under vehicle and inspect front and rear axle CV boots (rubber accordion sleeves) for tears or grease spray."
            ]
        })

        # 14. Inspect Steering & Suspension Components
        steer_interval = 6000 if self.severe else 12000
        is_steer_due, steer_overdue, steer_cf = check_due("Inspect Steering & Suspension Components", steer_interval)
        items.append({
            "name": "Inspect Steering & Suspension Components",
            "interval": steer_interval,
            "due": is_steer_due,
            "overdue_since": steer_overdue,
            "is_carried_forward": steer_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Check tie-rod ends, ball joints, control arms, and suspension bushings for wear or dynamic play.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "N/A",
            "specs": "Worn ball joints or tie rods skew alignment, cause tire feathering, and represent immediate safety hazards.",
            "steps": [
                "Raise front axle, grab tire at 12:00 and 6:00 positions and wiggle to check for hub bearing or ball joint play.",
                "Grab tire at 9:00 and 3:00 and wiggle to check for tie-rod end play.",
                "Use pry bar to inspect control arm bushings, checking for heavy cracks, separation, or metal contact.",
                "Verify sway bar end link rubber boots are not split or leaking grease."
            ]
        })

        # 15. Inspect Fuel System Lines & Connections
        fuel_lines_interval = 30000
        is_fl_due, fl_overdue, fl_cf = check_due("Inspect Fuel System Lines & Connections", fuel_lines_interval)
        items.append({
            "name": "Inspect Fuel System Lines & Connections",
            "interval": fuel_lines_interval,
            "due": is_fl_due,
            "overdue_since": fl_overdue,
            "is_carried_forward": fl_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Inspect engine compartment fuel rails and rubber fuel supply/return lines for brittleness or fuel leakage.",
            "source": "Warranty booklet",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "N/A",
            "specs": "Ensure no fuel smell exists. High pressure fuel leaks pose immediate fire risk under high boost.",
            "steps": [
                "Visually trace under-hood fuel delivery hard lines and rubber line connects near fuel dampener/filter blocks.",
                "Check around engine cylinder head fuel rails for weeping fuel injectors or O-ring dampener leaks.",
                "Inspect under-car protective metal shields covering the main fuel supply lines from gas tank.",
                "Sniff around the engine bay and near the rear seat hatch for any raw gasoline vapor smells."
            ]
        })

        # 16. Inspect Clutch Pedal & Operation
        clutch_interval = 30000
        is_clutch_due, clutch_overdue, clutch_cf = check_due("Inspect Clutch Pedal & Operation", clutch_interval)
        items.append({
            "name": "Inspect Clutch Pedal & Operation",
            "interval": clutch_interval,
            "due": is_clutch_due,
            "overdue_since": clutch_overdue,
            "is_carried_forward": clutch_cf,
            "priority": "🟡 Medium Priority",
            "category": "Inspections",
            "description": "Ensure the manual transmission clutch performs smoothly, inspect fluid level and pedal freeplay.",
            "source": "Warranty booklet",
            "oil_grade": "DOT 3 or DOT 4 Premium Fluid (clutch system)",
            "part_number": "N/A",
            "quantity": "approx. 100mL (clutch reservoir fill)",
            "specs": "Pedal freeplay should feel distinct. Low clutch fluid indicates slave or master cylinder cylinder seal leak.",
            "steps": [
                "Open hood, check clutch master cylinder fluid level on driver side firewall (ensure near MAX line).",
                "Sit in cabin, press clutch pedal to floor, ensuring motion is smooth and has no grinding or binding.",
                "Measure pedal freeplay distance (how far pedal presses before engaging hydraulic piston resistance).",
                "Verify clutch engagement/disengagement point during road test, checking for clutch slip under load."
            ]
        })

        # 17. Engine Coolant
        is_coolant_due, coolant_overdue, coolant_cf = check_due("Replace Engine Coolant (Super Coolant)", 0)
        items.append({
            "name": "Replace Engine Coolant (Super Coolant)",
            "interval": "First at 137,500 mi, then every 75,000 mi",
            "due": is_coolant_due,
            "overdue_since": coolant_overdue,
            "is_carried_forward": coolant_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": "First replacement at 11 years / 137,500 miles. Always use Genuine Subaru Cooling System Conditioner to prevent leaks.",
            "source": "Warranty booklet / NHTSA TSB",
            "oil_grade": "Subaru Blue Super Coolant (Pre-Mixed, do not add water)",
            "part_number": "SOA635041 (Super Coolant) & SOA635065 (Cooling System Conditioner)",
            "quantity": "approx. 8 Quarts (full system capacity)",
            "specs": "Never mix green conventional coolant with blue Super Coolant. Always add one bottle of conditioner (SOA635065) to protect gaskets.",
            "steps": [
                "Ensure engine is completely cold. Open radiator cap and overflow bottle cap.",
                "Safely raise front, remove lower splash shield, and open radiator bottom petcock valve to drain old coolant.",
                "Flush overflow reservoir clean of any crust or residue.",
                "Close petcock valve. Pour blue pre-mixed Subaru Super Coolant slowly into radiator filler neck.",
                "Pour one complete bottle of Subaru Cooling System Conditioner (SOA635065) directly into radiator.",
                "Fill overflow bottle to MAX line with fresh coolant.",
                "Attach bleed funnel to radiator, run engine until thermostat opens (upper hose hot, fans run), bleed air bubbles, and cap radiator."
            ]
        })

        # 18. Lubricate hinges, chassis, locks
        lub_interval = 6000
        is_lub_due, lub_overdue, lub_cf = check_due("Lubricate Doors, Hinges, Hood Latch, and Chassis Bushings", lub_interval)
        items.append({
            "name": "Lubricate Doors, Hinges, Hood Latch, and Chassis Bushings",
            "interval": lub_interval,
            "due": is_lub_due,
            "overdue_since": lub_overdue,
            "is_carried_forward": lub_cf,
            "priority": "🟢 Low Priority",
            "category": "Lubrication & General",
            "description": "Apply high-quality lubricant to hinges, locks, hood catch, and door checks to prevent binding and squeaking.",
            "source": "Warranty booklet / Quirk Works",
            "oil_grade": "White Lithium Grease (spray or paste) or silicone lubricant",
            "part_number": "Premium spray lubricant / Lithium grease",
            "quantity": "As required",
            "specs": "Do not use WD-40 as long-term grease; use a dedicated heavy spray grease which won't wash away in rain.",
            "steps": [
                "Clean old grime and grit from door hinges, latch locks, hood latch, and trunk/hatch hinges with shop cloth.",
                "Spray white lithium grease onto door hinge pivot pins, check straps, and sliding lock mechanisms.",
                "Lubricate hood latch assembly and secondary safety catch pivot.",
                "Wipe away excess grease run-off to prevent catching clothes or gathering road dust."
            ]
        })

        # 19. Check operation of exterior lights
        lights_interval = 6000
        is_lights_due, lights_overdue, lights_cf = check_due("Check Operation of All Exterior Lights", lights_interval)
        items.append({
            "name": "Check Operation of All Exterior Lights",
            "interval": lights_interval,
            "due": is_lights_due,
            "overdue_since": lights_overdue,
            "is_carried_forward": lights_cf,
            "priority": "🟢 Low Priority",
            "category": "Lubrication & General",
            "description": "Inspect functionality of headlights, high beams, turn signals, hazard flashers, side markers, tail lights, and brake lights.",
            "source": "Quirk Works",
            "oil_grade": "N/A",
            "part_number": "Bulb replacement part numbers vary by position",
            "quantity": "N/A",
            "specs": "Verify license plate lights are lit to avoid minor equipment violations.",
            "steps": [
                "Turn key to ignition ON position, switch on parking lights, and walk around car checking all bulbs.",
                "Activate low-beams and high-beams to verify headlight output.",
                "Turn on hazard flashers to check all corner indicators and side fender markers.",
                "Press brake pedal (use helper or brace) to inspect high-mount and rear brake lamps, then shift to Reverse to check backup lamps."
            ]
        })

        # Sort: Due first, then by priority (Red -> Yellow -> Green)
        def sort_key(x):
            priority_score = 0
            if "🔴" in x["priority"]:
                priority_score = 1
            elif "🟡" in x["priority"]:
                priority_score = 2
            else:
                priority_score = 3
            return (0 if x["due"] else 1, priority_score, x["name"])

        items.sort(key=sort_key)
        return items


HISTORY_FILE = "subaru_maintenance_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(entry):
    history = load_history()
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)


# --- STREAMLIT WEB APP RUNTIME ---
if HAS_STREAMLIT and st.runtime.exists():
    st.set_page_config(page_title="Subaru STI Maintenance Tracker", page_icon="🏎️", layout="wide")

    st.markdown(
        """
        <div style='background-color:#1e3d59;padding:15px;border-radius:10px;text-align:center;'>
            <h1 style='color:white;margin:0;'>🏎️ Subaru WRX STI Maintenance Tracker</h1>
            <p style='color:#ffc13b;margin:5px 0 0 0;font-size:1.1em;'>Keep your boxer engine in optimal performance. Real schedules, custom alerts, torque specs, and local logging.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Sidebar inputs
    st.sidebar.markdown("### 🔧 Vehicle Settings")
    mileage = st.sidebar.number_input("Current Odometer Mileage (mi):", min_value=0, max_value=500000, value=105000, step=1000)
    
    st.sidebar.markdown("### 🚦 Operating Conditions")
    severe = st.sidebar.checkbox(
        "Severe Driving Conditions", 
        value=False,
        help="Trigger shorter intervals (e.g., oil every 3,000 miles). Conditions include repeated short distances (< 5 mi), rough/mudy/salty roads, high humidity/mountains, or extremely cold weather."
    )

    # Initialize scheduler
    scheduler = MaintenanceScheduler(mileage, severe)
    schedule_items = scheduler.get_schedule()

    due_items = [item for item in schedule_items if item["due"]]
    other_items = [item for item in schedule_items if not item["due"]]

    # Tabs layout
    tab_checklist, tab_history, tab_manual = st.tabs(["📋 Mileage Checklist", "📜 Service History Log", "📖 Subaru Reference Guide"])

    with tab_checklist:
        st.subheader(f"Current Mileage: {mileage:,} mi")
        
        # Severe summary alerts
        if severe:
            st.info("**Severe conditions enabled:** Brake fluid, transmission/diff gear oil, air filter, and inspection intervals are accelerated.")

        if not due_items:
            st.success(f"🎉 No specific maintenance services are scheduled exactly at **{mileage:,} miles**! Check the list below to see the general service guide.")
        else:
            st.warning(f"⚠️ There are **{len(due_items)}** scheduled maintenance items due now at **{mileage:,} miles**:")

            # Form to save checklist
            st.markdown("### 📝 Check Off Completed Items to Record to History:")
            completed_checks = {}
            for item in due_items:
                # Checkbox inside a container
                col_check, col_desc = st.columns([0.4, 0.6])
                with col_check:
                    label = f"{item['priority']} - {item['name']} (⚠️ Overdue since {item['overdue_since']:,} mi)" if item.get('is_carried_forward') else f"{item['priority']} - {item['name']}"
                    completed_checks[item["name"]] = st.checkbox(
                        label,
                        key=f"check_{item['name']}",
                        help=f"Interval: every {item['interval']:,} miles." if isinstance(item['interval'], int) else f"Interval: {item['interval']}"
                    )
                with col_desc:
                    st.caption(f"**Description:** {item['description']} *(Source: {item['source']})*")
                
                # Expandable details for the due item
                with st.expander(f"🔧 Specs, Part Numbers & Steps for {item['name']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Recommended Grade/Type:** {item.get('oil_grade', 'N/A')}")
                        st.markdown(f"**Part Number:** {item.get('part_number', 'N/A')}")
                        st.markdown(f"**Required Quantity:** {item.get('quantity', 'N/A')}")
                        st.markdown(f"**Key Specifications:** {item.get('specs', 'N/A')}")
                    with col2:
                        st.markdown("**Steps to Perform:**")
                        for step in item.get('steps', []):
                            st.write(f"- {step}")

                st.markdown("<hr style='margin:2px 0;border-color:#eee;'/>", unsafe_allow_html=True)

            # Extra notes and save button
            notes = st.text_area("Service Notes / Dealer Name / Parts Used:")
            if st.button("💾 Save Checked Items to History", type="primary"):
                completed_list = [name for name, val in completed_checks.items() if val]
                if not completed_list:
                    st.error("Please check off at least one completed item before saving.")
                else:
                    new_entry = {
                        "date": datetime.date.today().isoformat(),
                        "mileage": mileage,
                        "severe_mode": severe,
                        "notes": notes,
                        "completed_items": completed_list
                    }
                    save_history(new_entry)
                    st.success("✅ Service recorded successfully! Refresh page or check the Service History tab to review.")

        # Show general reference schedule below with nested expanders for each item
        st.markdown("### 🔍 General Subaru WRX/STI Maintenance Reference Guide:")
        for item in other_items:
            interval_str = f"Every {item['interval']:,} miles" if isinstance(item['interval'], int) else str(item['interval'])
            with st.expander(f"⚙️ {item['priority']} - {item['name']} (Interval: {interval_str})"):
                st.write(f"*{item['description']}* *(Source: {item['source']})*")
                
                # Render the specs/steps details
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Recommended Grade/Type:** {item.get('oil_grade', 'N/A')}")
                    st.markdown(f"**Part Number:** {item.get('part_number', 'N/A')}")
                    st.markdown(f"**Required Quantity:** {item.get('quantity', 'N/A')}")
                    st.markdown(f"**Key Specifications:** {item.get('specs', 'N/A')}")
                with col2:
                    st.markdown("**Steps to Perform:**")
                    for step in item.get('steps', []):
                        st.write(f"- {step}")

    with tab_history:
        st.subheader("📜 Maintenance & Service Log")
        history = load_history()
        if not history:
            st.info("No service history recorded yet. Use the Mileage Checklist tab to log completed services.")
        else:
            for idx, entry in enumerate(reversed(history)):
                notes_html = f"<p style='margin-top:10px;'><b>Notes:</b> {entry['notes']}</p>" if entry.get('notes') else ""
                items_html = "".join([f"<li>{item}</li>" for item in entry['completed_items']])
                st.markdown(
                    f"""
                    <div style='background-color:#f8f9fa;padding:15px;border-radius:5px;border-left:5px solid #1e3d59;margin-bottom:15px;'>
                        <h4 style='margin:0;'>🔧 Service on {entry['date']} at <b>{entry['mileage']:,} miles</b></h4>
                        <p style='margin:5px 0 10px 0;color:#666;font-size:0.9em;'>
                            <b>Severe Conditions:</b> {'Yes' if entry.get('severe_mode') else 'No'}
                        </p>
                        <p><b>Completed Services:</b></p>
                        <ul>
                            {items_html}
                        </ul>
                        {notes_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with tab_manual:
        st.subheader("📖 Official Subaru WRX STI Reference Manual")
        
        col_torque, col_tsb = st.columns(2)
        
        with col_torque:
            st.markdown(
                """
                ### 🔧 Critical Torque Specifications
                *Grounded in factory specifications every DIY owner should follow to avoid stripping aluminum threads:*
                
                | Component | Torque Specification | Notes / Risks |
                | :--- | :--- | :--- |
                | **Spark Plugs** | **21 N·m (15.5 ft-lb)** | Essential for aluminum heads to prevent stripping threads or cracking ceramic. |
                | **Ignition Coil Bolts** | **16 N·m (11.8 ft-lb)** | Prevent loose coils causing misfires or vibrations under high boost. |
                | **Valve Cover Bolts** | **4.5–6.3 N·m (3.3–4.7 ft-lb)** | Very low torque. Overtightening warps covers and causes severe oil leaks. |
                | **Wheel Lug Nuts** | **120 N·m (88.5 ft-lb)** | Avoids warped brake rotors and stud failure from impact gun overtorquing. |
                | **Intake Manifold Bolts** | **24 N·m (18 ft-lb)** | Prevents dynamic vacuum and boost leaks which skew engine AFR. |
                """
            )
            
        with col_tsb:
            st.markdown(
                """
                ### 📋 Crucial TSB Advice & Severe Operating Rules
                
                * **The 5-Minute Dipstick Rule (NHTSA TSB):** Always wait at least **5 minutes** after turning off the engine on a level surface before checking the oil. This allows oil suspended in the boxer layout to fully drain back into the pan for an accurate reading.
                * **Interference Engine Warning:** The WRX STI EJ-engine is an **interference engine**. A failure of the timing belt or pulleys will cause catastrophic piston-to-valve contact, completely destroying your engine heads. Always replace the water pump, tensioner, idlers, and guides at the same time.
                * **Tire Diameter Matching (AWD System):** Symmetrical AWD requires all four tires to have a tread depth matching within **1/16 in** (or 2/32 in) of each other. Running mismatched tire sizes will overheat and permanently destroy the DCCD center differential.
                * **Blue Super Coolant:** The factory long-life coolant lasts 11 years / 137,500 miles. Always use genuine blue Subaru coolant and add **Genuine Subaru Cooling System Conditioner** whenever replacing.
                """
            )


# --- INTERACTIVE TERMINAL CLI RUNTIME ---
elif HAS_RICH:
    console = Console()

    def print_banner():
        console.clear()
        banner_text = """
   ______      __                                  _____ ______  ____
  / ___/ _  __/ /_  ____ ______  __  __   _  __   / ___//_  __/ /  _/
  \\__ \\ | |/_/ __ \\/ __ `/ ___/ / / / /  | |/_/   \\__ \\  / /    / /  
 ___/ /_>  </ /_/ / /_/ / /    / /_/ /  _>  <    ___/ / / /   _/ /   
/____//_/|_/_.___/\\__,_/_/     \\__,_/  /_/|_|   /____/ /_/   /___/   
                 
                 MAINTENANCE SCHEDULE TRACKER & CLI APP
        """
        console.print(Panel(Text(banner_text, style="bold cyan", justify="center"), subtitle="Grounded in Factory Service Bulletins & Specifications", border_style="blue"))

    def show_history_cli():
        print_banner()
        history = load_history()
        if not history:
            console.print("[yellow]No service history recorded yet. Use the scheduler to log services.[/yellow]\n")
        else:
            console.print("[bold green]=== PAST SERVICE HISTORY LOG ===[/bold green]\n")
            for entry in reversed(history):
                table = Table(title=f"Service on {entry['date']} @ {entry['mileage']:,} miles", title_justify="left", show_header=True, header_style="bold blue")
                table.add_column("Property", style="dim", width=20)
                table.add_column("Details", style="cyan")
                table.add_row("Severe Driving", "Yes" if entry.get("severe_mode") else "No")
                table.add_row("Completed Items", ", ".join(entry["completed_items"]))
                table.add_row("Notes", entry.get("notes") or "N/A")
                console.print(table)
                console.print("-" * 50)
        input("\nPress Enter to return to main menu...")

    def run_cli():
        while True:
            print_banner()
            console.print("[bold yellow]MAIN MENU:[/bold yellow]")
            console.print("1. Calculate Schedule & Track Maintenance Checklist")
            console.print("2. View Service History Log")
            console.print("3. View Critical Torque & TSB Specs")
            console.print("4. Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "4":
                console.print("[bold green]Thank you for keeping your STI well-maintained. Safe boosting![/bold green]")
                break
                
            elif choice == "3":
                print_banner()
                console.print(Panel("[bold green]🔧 CRITICAL TORQUE SPECIFICATIONS (My Pro Street)[/bold green]\n"
                                    "• [cyan]Spark Plugs:[/cyan] 21 N·m (15.5 ft-lb) — prevent cylinder head thread stripping\n"
                                    "• [cyan]Ignition Coil Bolt:[/cyan] 16 N·m (11.8 ft-lb) — prevent engine misfires under boost\n"
                                    "• [cyan]Valve Cover Bolts:[/cyan] 3.3–4.7 ft-lb — very low! Prevent warping gaskets\n"
                                    "• [cyan]Wheel Lug Nuts:[/cyan] 88.5 ft-lb — prevents warped brake rotors\n"
                                    "• [cyan]Intake Manifold Bolts:[/cyan] 18 ft-lb — prevent boost/vacuum leaks\n\n"
                                    "[bold yellow]📖 RECALLS & CRITICAL TSB ADVICE[/bold yellow]\n"
                                    "• [red]The 5-Minute Dipstick Rule (NHTSA TSB):[/red] Wait 5 min after shutdown on flat ground to let oil settle before measuring.\n"
                                    "• [red]Interference Engine warning:[/red] Sapped timing belt destroys cylinder heads. Replace water pump/tensioner all-at-once.\n"
                                    "• [red]Tire Sizing AWD Rule:[/red] Tread depth matching within 1/16 in prevents center diff failure.",
                                    title="Subaru WRX STI Reference Sheets"))
                input("\nPress Enter to return to main menu...")
                
            elif choice == "2":
                show_history_cli()
                
            elif choice == "1":
                print_banner()
                mileage = IntPrompt.ask("Enter current vehicle mileage", default=105000)
                severe = Confirm.ask("Is the car driven in severe conditions (short trips, mud/dust, extreme heat/cold, road salt)?")
                
                scheduler = MaintenanceScheduler(mileage, severe)
                items = scheduler.get_schedule()
                
                due_items = [i for i in items if i["due"]]
                other_items = [i for i in items if not i["due"]]
                
                print_banner()
                console.print(f"[bold cyan]Maintenance Checklist for {mileage:,} miles[/bold cyan]")
                if severe:
                    console.print("[bold red]⚠️ SEVERE CONDITIONS ACCELERATED TIMINGS APPLIED[/bold red]")
                console.print("")

                if not due_items:
                    console.print("[green]🎉 No scheduled items are due right now! Clean bill of health.[/green]\n")
                else:
                    table = Table(title=f"Due Items at {mileage:,} mi", show_lines=True)
                    table.add_column("#", style="dim", width=4)
                    table.add_column("Priority", width=15)
                    table.add_column("Maintenance Service", style="bold cyan")
                    table.add_column("Interval (mi)", style="magenta")
                    table.add_column("Details", style="yellow")
                    
                    for idx, item in enumerate(due_items):
                        color = "red" if "🔴" in item["priority"] else "yellow" if "🟡" in item["priority"] else "green"
                        name_display = item["name"]
                        if item.get("is_carried_forward"):
                            name_display = f"[bold orange3]{item['name']} (⚠️ OVERDUE since {item['overdue_since']:,} mi)[/bold orange3]"
                        table.add_row(
                            str(idx + 1),
                            f"[{color}]{item['priority']}[/{color}]",
                            name_display,
                            f"{item['interval']:,}" if isinstance(item['interval'], int) else str(item['interval']),
                            item["description"]
                        )
                    console.print(table)
                    
                    # Check-off logging
                    save_flag = Confirm.ask("Would you like to complete and log these items to your service history?")
                    if save_flag:
                        console.print("\nType the numbers of the items you completed (comma separated, e.g. '1, 2, 4', or 'all'):")
                        comp_input = Prompt.ask("Completed item numbers")
                        
                        completed_items = []
                        if comp_input.lower().strip() == "all":
                            completed_items = [i["name"] for i in due_items]
                        else:
                            try:
                                indices = [int(x.strip()) - 1 for x in comp_input.split(",") if x.strip()]
                                for i in indices:
                                    if 0 <= i < len(due_items):
                                        completed_items.append(due_items[i]["name"])
                            except ValueError:
                                console.print("[red]Invalid selection sequence. Skipping record.[/red]")
                                
                        if completed_items:
                            notes = Prompt.ask("Any notes for this log entry? (e.g., brand of parts used, dealer name)", default="")
                            new_entry = {
                                "date": datetime.date.today().isoformat(),
                                "mileage": mileage,
                                "severe_mode": severe,
                                "notes": notes,
                                "completed_items": completed_items
                            }
                            save_history(new_entry)
                            console.print("[bold green]✅ Service successfully logged to JSON history file![/bold green]")
                        else:
                            console.print("[yellow]No items logged.[/yellow]")
                            
                if other_items:
                    show_all = Confirm.ask("Would you like to see other scheduled items not currently due?")
                    if show_all:
                        table_all = Table(title="Other Periodic Subaru STI Maintenance Items")
                        table_all.add_column("Priority", width=15)
                        table_all.add_column("Maintenance Service", style="bold cyan")
                        table_all.add_column("Interval (mi)", style="magenta")
                        table_all.add_column("Why it matters", style="dim")
                        
                        for item in other_items:
                            color = "red" if "🔴" in item["priority"] else "yellow" if "🟡" in item["priority"] else "green"
                            table_all.add_row(
                                f"[{color}]{item['priority']}[/{color}]",
                                item["name"],
                                f"{item['interval']:,}" if isinstance(item['interval'], int) else str(item['interval']),
                                item["description"]
                            )
                        console.print(table_all)
                        
                input("\nPress Enter to return to main menu...")

    if __name__ == "__main__":
        run_cli()
else:
    # Basic fall-back interactive prompt
    if __name__ == "__main__":
        print("Subaru STI Maintenance App (Minimal fallback)")
        print("Please install streamlit ('pip install streamlit') or rich ('pip install rich') to run.")

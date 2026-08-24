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
    def __init__(self, mileage, severe=False, primary_mode=True):
        self.mileage = mileage
        self.severe = severe
        self.primary_mode = primary_mode

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
            if interval == 0:  # No replacement required
                return False, 0, False
                
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
        if self.primary_mode:
            oil_interval = 3000 if self.severe else 6000
            oil_source = "Primary Source: Subaru Customer Self-Service / NHTSA Service Bulletin"
            oil_desc = "EJ257 engine oil and filter should be replaced every 6,000 miles or 6 months. Shorter intervals (3,000 miles or 3 months) apply under severe operating conditions to protect hydrodynamic crankshaft bearings."
        else:
            oil_interval = 3000 if self.severe else 5000
            oil_source = "Secondary Source: GarageHub / Reddit WRX"
            oil_desc = "Tuning specialists recommend shorter oil changes (3,000 to 5,000 miles) with SAE 5W-40 full synthetic (like Motul 8100 or Rotella T6) to prevent high-boost shear and bearing starvation."

        is_oil_due, oil_overdue, oil_cf = check_due("Replace Engine Oil & Filter", oil_interval)
        items.append({
            "name": "Replace Engine Oil & Filter",
            "interval": oil_interval,
            "due": is_oil_due,
            "overdue_since": oil_overdue,
            "is_carried_forward": oil_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": oil_desc,
            "source": oil_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "5W-30 Full Synthetic (Standard Spec) or 5W-40 in hotter climates / heavy use",
            "part_number": "15208AA100 (JDM Black Tokyo Roki Filter) & 11126AA000 (Oil Pan Drain Crush Washer)",
            "quantity": "4.5 US Quarts (approx. 4.3 Liters) with filter",
            "specs": "Drain Plug Torque: 33-34 ft-lb (44-46 N·m). Always use a new copper crush gasket (11126AA000). Wait 5 minutes after shutdown on level ground before checking dipstick.",
            "steps": [
                "Ensure engine is warm, then safely raise vehicle and remove undertray.",
                "Position drain pan under oil pan drain plug, unscrew plug, and drain oil completely.",
                "Remove old drain plug gasket and install new copper crush gasket (11126AA000) onto plug.",
                "Reinstall and torque drain plug to 33 ft-lb.",
                "Remove old oil filter from top/bottom engine block, lubricate new filter's rubber seal with fresh oil, and hand-tighten 3/4 turn after gasket contacts surface.",
                "Fill engine slowly with 4.5 quarts of fresh 5W-30 synthetic oil.",
                "Crank engine with fuel pump fuse removed for 10s to prime oil galleries. Reinstall fuse, start engine, check for leaks, shut off, wait 5 min, and verify dipstick level."
            ]
        })

        # 2. Timing Belt
        if self.primary_mode:
            tb_interval = 90000 if self.severe else 105000
            tb_source = "Primary Source: Subaru Customer Self-Service / Subaru Canada FSM"
            tb_desc = "Standard replacement interval is 105,000 miles or 105 months. Under severe guidelines, early timing belt swap is recommended at 90,000 miles or 90 months."
        else:
            tb_interval = 60000 if self.severe else 90000
            tb_source = "Secondary Source: GarageHub / Import Car Parts"
            tb_desc = "Tuning experts advise replacing the timing belt assembly at 60,000 miles because the EJ257 is an interference engine; a snapped belt causes immediate valve-to-piston collision."

        is_tb_due, tb_overdue, tb_cf = check_due("Replace Timing Belt (Complete Assembly)", tb_interval)
        items.append({
            "name": "Replace Timing Belt (Complete Assembly)",
            "interval": tb_interval,
            "due": is_tb_due,
            "overdue_since": tb_overdue,
            "is_carried_forward": tb_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": tb_desc,
            "source": tb_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "13028AA250 (Timing Belt), 21111AA240 (Water Pump), 13033AA042 (Tensioner & Pulley)",
            "quantity": "1 Complete Kit (Aisin TKF-012 recommended - includes belt, pump, tensioner, idlers)",
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
        if self.primary_mode:
            spark_interval = 30000 if self.severe else 90000
            spark_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            spark_desc = "Under official Subaru specifications, replace Laser Iridium Spark Plugs every 90,000 miles or 90 months. Severe operations accelerate replacement to every 30,000 miles."
        else:
            spark_interval = 30000 if self.severe else 60000
            spark_source = "Secondary Source: Import Car Parts / Crawford Performance"
            spark_desc = "Tuner specialists recommend replacing spark plugs every 60,000 miles on stock cars, and every 15,000 to 20,000 miles on tuned/tracked STIs to prevent boost misfires and detonation."

        is_spark_due, spark_overdue, spark_cf = check_due("Replace Spark Plugs", spark_interval)
        items.append({
            "name": "Replace Spark Plugs",
            "interval": spark_interval,
            "due": is_spark_due,
            "overdue_since": spark_overdue,
            "is_carried_forward": spark_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": spark_desc,
            "source": spark_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "NGK SILFR6A / 7913 (P/N 22401AA670 OEM Iridium)",
            "quantity": "4 Spark Plugs",
            "specs": "Spark Plug Torque: 13-17 ft-lb (18-23 N·m). Dry threads without anti-seize. Coil Pack Bolt: 11.8 ft-lb (16 N·m).",
            "steps": [
                "Disconnect battery and remove air intake duct (passenger side) and windshield washer bottle (driver side) to gain clearance.",
                "Disconnect ignition coil harness plugs, remove the 10mm retaining bolt on each coil, and pull the direct ignition coils straight out.",
                "Use compressed air to blow out any loose dust or dirt from inside the spark plug tubes.",
                "Use a 5/8-inch (16mm) spark plug socket, a locking 3-inch extension, and a ratchet to loosen and extract the old plugs.",
                "Check gap of new iridium plugs. Hand-thread new plugs into the head to prevent cross-threading.",
                "Torque spark plugs strictly to 13-17 ft-lb. Reinstall coils, torque coil bolts to 11.8 ft-lb, and reconnect electrical harness."
            ]
        })

        # 4. Replace Brake & Clutch Fluid
        if self.primary_mode:
            brake_interval = 20000 if self.severe else 24000
            brake_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            brake_desc = "Factory guidelines require replacement of hydraulic brake and clutch fluid every 24,000 miles or 24 months, or every 20,000 miles under severe operation."
        else:
            brake_interval = 15000 if self.severe else 30000
            brake_source = "Secondary Source: Import Car Parts / GarageHub"
            brake_desc = "Enthusiasts recommend bleeding and replacing the fluid every 30,000 miles for street cars, or before every event for track cars using DOT 4 or 5.1."

        is_brake_due, brake_overdue, brake_cf = check_due("Replace Brake & Clutch Fluid", brake_interval)
        items.append({
            "name": "Replace Brake & Clutch Fluid",
            "interval": brake_interval,
            "due": is_brake_due,
            "overdue_since": brake_overdue,
            "is_carried_forward": brake_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": brake_desc,
            "source": brake_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
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
        if self.primary_mode:
            # Under strict FSM, it's Inspect only under standard conditions (every 48,000 mi). Replace is only required under severe conditions (every 20,000 mi / 2 years)
            gear_interval = 20000 if self.severe else 48000
            gear_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            gear_desc = "Strict FSM specifies inspecting gearbox and differential gear oil level every 48,000 miles or 48 months. Fluid replacement is only mandated under severe conditions every 20,000 miles / 2 years."
        else:
            gear_interval = 15000 if self.severe else 30000
            gear_source = "Secondary Source: GarageHub / Import Car Parts"
            gear_desc = "Specialists advise a complete oil swap every 30,000 miles (street) or 15,000 miles (severe/track) to remove abrasive steel debris from AWD gears and the DCCD clutch."

        is_gear_due, gear_overdue, gear_cf = check_due("Replace Gear Oils (MT & Front/Rear Differentials)", gear_interval)
        items.append({
            "name": "Replace Gear Oils (MT & Front/Rear Differentials)",
            "interval": gear_interval,
            "due": is_gear_due,
            "overdue_since": gear_overdue,
            "is_carried_forward": gear_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": gear_desc,
            "source": gear_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "Subaru Gear Oil GL-5 75W-90 (Diffs) / GL-4 or GL-5 compatible 75W-90 (MT)",
            "part_number": "Subaru Extra MT 75W-90 (Manual Transmission), Subaru Gear Oil STI (DCCD/Rear Differential)",
            "quantity": "MT / Front Diff Change: ~3.5 Quarts; Rear Diff Change: ~1.0 Quart",
            "specs": "Shares common bath in transaxle. Standard manual swaps only require ~3.5 quarts on service refill. Drain plugs: 36-43 ft-lb.",
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
        if self.primary_mode:
            fuel_filter_interval = 72000
            ff_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            ff_desc = "FSM specifies a replacement interval of every 72,000 miles or 72 months to prevent fuel line pressure drops."
        else:
            fuel_filter_interval = 35000 if self.severe else 60000
            ff_source = "Secondary Source: Import Car Parts"
            ff_desc = "Specialists recommend swapping the in-tank filter element every 60,000 miles (or 35,000 miles under heavy duty) to protect high-boost delivery."

        is_ff_due, ff_overdue, ff_cf = check_due("Replace Fuel Filter", fuel_filter_interval)
        items.append({
            "name": "Replace Fuel Filter",
            "interval": fuel_filter_interval,
            "due": is_ff_due,
            "overdue_since": ff_overdue,
            "is_carried_forward": ff_cf,
            "priority": "🔴 High Priority",
            "category": "Replacements",
            "description": ff_desc,
            "source": ff_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "42072AA200 (OEM In-Tank Fuel Filter element)",
            "quantity": "1 Filter Element",
            "specs": "Ensure fuel tank is less than 1/4 full. Work in a highly ventilated area with battery negative disconnected.",
            "steps": [
                "Locate fuel pump fuse, pull it, and crank engine until it stalls to depressurize fuel lines. Disconnect battery negative terminal.",
                "Remove rear seat bottom cushion, unbolt metal access hatch plate on passenger side, and vacuum any dirt/dust.",
                "Carefully squeeze quick-release tabs and slide off fuel feed and return lines (wrap with clean shop rag to catch spray).",
                "Unplug fuel pump electrical harness connector.",
                "Unbolt retaining ring nut and lift fuel pump hanger assembly slowly from fuel tank, taking care not to bend float arm.",
                "Disassemble plastic pump hanger brackets, release holding clips, swap out dirty fuel filter element for new filter, and replace rubber seals.",
                "Reassemble hanger, lower into tank with new main ring gasket, torque flange nuts, reconnect lines/plugs, reinstall fuse, and cycle key to prime system."
            ]
        })

        # 7. Replace PCV Valve
        if self.primary_mode:
            pcv_interval = 30000  # Inspect only
            pcv_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            pcv_desc = "FSM mandates checking/inspecting the positive crankcase ventilation (PCV) valve every 30,000 miles or 30 months."
        else:
            pcv_interval = 60000
            pcv_source = "Secondary Source: GarageHub / Quirk Works"
            pcv_desc = "Due to horizontally opposed oil blow-by, replacing the PCV valve outright every 60,000 miles is highly recommended to protect against engine seal leakage and octane degradation."

        is_pcv_due, pcv_overdue, pcv_cf = check_due("Replace PCV Valve" if not self.primary_mode else "Inspect PCV Valve", pcv_interval)
        items.append({
            "name": "Replace PCV Valve" if not self.primary_mode else "Inspect PCV Valve",
            "interval": pcv_interval,
            "due": is_pcv_due,
            "overdue_since": pcv_overdue,
            "is_carried_forward": pcv_cf,
            "priority": "🔴 High Priority" if not self.primary_mode else "🟡 Medium Priority",
            "category": "Replacements" if not self.primary_mode else "Inspections",
            "description": pcv_desc,
            "source": pcv_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "11810AA130 or equivalent",
            "quantity": "1 PCV Valve",
            "specs": "Thread torque: 14 ft-lb (19 N·m). A sticking PCV valve causes oil vapors to enter combustion chamber, lowering effective fuel octane.",
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
        if self.primary_mode:
            tire_interval = 12000
            tire_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            tire_desc = "FSM mandates a full rotation and safety inspection every 12,000 miles or 12 months."
        else:
            tire_interval = 6000
            tire_source = "Secondary Source: Quirk Works / Import Car Parts"
            tire_desc = "Dealer service menus and AWD specialists recommend performing tire rotations every 6,000 miles or 6 months to maintain uniform tread depths."

        is_tire_due, tire_overdue, tire_cf = check_due("Perform Tire Rotation", tire_interval)
        items.append({
            "name": "Perform Tire Rotation",
            "interval": tire_interval,
            "due": is_tire_due,
            "overdue_since": tire_overdue,
            "is_carried_forward": tire_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": tire_desc,
            "source": tire_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "N/A",
            "quantity": "4 Wheels Rotated",
            "specs": "Lug Nut Torque: 89-94 ft-lb (120-127 N·m). Mismatched tire tread depth exceeding 1/16 in can overheat and destroy the DCCD.",
            "steps": [
                "With car on ground, loosen wheel lug nuts slightly using a breaker bar and 19mm socket.",
                "Raise vehicle levelly on jack stands. Inspect tires for uneven feathering, cupping, or punctures.",
                "Measure tread depth across inside, center, and outside block of all 4 tires (ensure within 1/16 in matching).",
                "Rotate tires: For non-directional tires, cross front tires to rear (LF to RR, RF to LR) and move rears straight up. Move straight up/down for directional tires.",
                "Lower vehicle until tires touch ground, torque lug nuts in star pattern to 89-94 ft-lb using hand torque wrench."
            ]
        })

        # 9. Replace Engine Air Filter
        if self.primary_mode:
            air_interval = 48000
            air_source = "Primary Source: Subaru Customer Self-Service / 2016 Warranty Booklet"
            air_desc = "Factory manuals specify replacing the pleated dry cleaner element every 48,000 miles or 48 months under standard conditions."
        else:
            air_interval = 15000 if self.severe else 30000
            air_source = "Secondary Source: GarageHub / Import Car Parts"
            air_desc = "Preventive maintenance lists replacement every 30,000 miles (standard) or 15,000 miles (severe/dusty) to ensure unrestrictive intake volumes."

        is_air_due, air_overdue, air_cf = check_due("Replace Engine Air Filter", air_interval)
        items.append({
            "name": "Replace Engine Air Filter",
            "interval": air_interval,
            "due": is_air_due,
            "overdue_since": air_overdue,
            "is_carried_forward": air_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": air_desc,
            "source": air_source,
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "16546AA090 / 16546AA10A (OEM Air Filter)",
            "quantity": "1 Filter",
            "specs": "Ensure filter frame is completely flush in airbox slots to avoid unmetered air leaks which throw off MAF readings.",
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
        # Consistent at 12,000 miles or 1 year across sources
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
            "description": "Keeps passenger compartment free of pollen and road contaminants. FSM & tuner specs both mandate replacement every 12,000 miles or 12 months.",
            "source": "Primary Source: Subaru Customer Self-Service",
            "source_type": "Primary (Official FSM & Drive)",
            "oil_grade": "N/A",
            "part_number": "72880FG000 (OEM Cabin Filter)",
            "quantity": "1 Filter",
            "specs": "Slower cabin airflow or sour smells are typical signs of a clogged filter.",
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
            "description": "Check alternator, power steering and stretch A/C compressor belt for wear, dry-rot, or tension issues.",
            "source": "Primary Source: Subaru Customer Self-Service",
            "source_type": "Primary (Official FSM & Drive)",
            "oil_grade": "N/A",
            "part_number": "809218460 (Alternator/PS) & 11718AA082 (AC Stretch Belt Kit with Tool)",
            "quantity": "N/A",
            "specs": "AC compressor uses a stretch-fit design without a mechanical tensioner. Sourcing the kit with the installation guide tool is mandatory to prevent rib damage.",
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
            "source": "Primary Source: Subaru Customer Self-Service",
            "source_type": "Primary (Official FSM & Drive)",
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
        brake_inspect_interval = 30000 if self.primary_mode else (6000 if self.severe else 12000)
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
            "source": "Primary Source: Subaru Customer Self-Service" if self.primary_mode else "Secondary Source: Quirk Works",
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
            "oil_grade": "N/A",
            "part_number": "26300FE070 (Front Rotors), 26696FG000 (Rear Pad Set)",
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
        steer_interval = 30000 if self.primary_mode else (6000 if self.severe else 12000)
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
            "source": "Primary Source: Subaru Customer Self-Service" if self.primary_mode else "Secondary Source: Quirk Works",
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
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
            "source": "Primary Source: Subaru Customer Self-Service",
            "source_type": "Primary (Official FSM & Drive)",
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
            "description": "Ensure manual trans clutch performs smoothly, inspect fluid level, brackets, and pedal freeplay.",
            "source": "Primary Source: Subaru Customer Self-Service",
            "source_type": "Primary (Official FSM & Drive)",
            "oil_grade": "DOT 3 or DOT 4 Premium Fluid (clutch system)",
            "part_number": "N/A",
            "quantity": "approx. 100mL (clutch reservoir fill)",
            "specs": "Creaks are common on 2015-16 models due to bracket pivot friction, requiring lithium lubrication at the release fork socket.",
            "steps": [
                "Open hood, check clutch master cylinder fluid level on driver side firewall (ensure near MAX line).",
                "Sit in cabin, press clutch pedal to floor, ensuring motion is smooth and has no grinding or binding.",
                "Measure pedal freeplay distance (how far pedal presses before engaging hydraulic piston resistance).",
                "Verify clutch engagement/disengagement point during road test, checking for clutch slip under load."
            ]
        })

        # 17. Engine Coolant
        # standard 137,500 miles or 11 years standard first replacement
        is_coolant_due, coolant_overdue, coolant_cf = check_due("Replace Engine Coolant (Super Coolant)", 0)
        items.append({
            "name": "Replace Engine Coolant (Super Coolant)",
            "interval": "First at 137,500 mi, then every 75,000 mi",
            "due": is_coolant_due,
            "overdue_since": coolant_overdue,
            "is_carried_forward": coolant_cf,
            "priority": "🟡 Medium Priority",
            "category": "Replacements",
            "description": "First replacement at 11 years / 137,500 miles, then every 6 years / 75,000 miles. Always add Cooling System Conditioner.",
            "source": "Primary Source: Subaru Customer Self-Service / NHTSA Service Bulletin",
            "source_type": "Primary (Official FSM & Drive)",
            "oil_grade": "Subaru Blue Super Coolant (Pre-Mixed, do not add water)",
            "part_number": "SOA635041 (Super Coolant) & SOA635065 (Cooling System Conditioner)",
            "quantity": "approx. 8.1 Quarts (approx. 7.7 Liters) full system capacity",
            "specs": "Never mix green conventional coolant with blue Super Coolant. Always add one bottle of conditioner (SOA635065) to protect head gaskets.",
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
            "description": "Apply white lithium grease to hinges, locks, hood catch, and checks to prevent binding.",
            "source": "Primary Source: Subaru Customer Self-Service" if self.primary_mode else "Secondary Source: Quirk Works",
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
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
            "description": "Inspect functionality of headlights, high beams, turn signals, hazard flashers, side markers, and tail/brake lights.",
            "source": "Primary Source: Subaru Customer Self-Service" if self.primary_mode else "Secondary Source: Quirk Works",
            "source_type": "Primary (Official FSM & Drive)" if self.primary_mode else "Secondary (Tuner & Specialist)",
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

    @st.dialog("Confirm Service Log")
    def confirm_save_dialog(completed_list, mileage, severe):
        st.markdown("##### Are you sure you want to save the following completed items to your service history?")
        for item in completed_list:
            st.markdown(f"- ✅ **{item}**")
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm", type="primary", use_container_width=True):
                new_entry = {
                    "date": datetime.date.today().isoformat(),
                    "mileage": mileage,
                    "severe_mode": severe,
                    "completed_items": completed_list
                }
                save_history(new_entry)
                st.success("✅ Service logged successfully!")
                st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    st.markdown(
        """
        <div style='background-color:#1e3d59;padding:15px;border-radius:10px;text-align:center;'>
            <h1 style='color:white;margin:0;'>🏎️ Subaru WRX STI Maintenance Tracker</h1>
            <p style='color:#ffc13b;margin:5px 0 0 0;font-size:1.1em;'>Keep your boxer engine in optimal performance. Real schedules, custom alerts, torque specs, and local logging.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Tabs layout
    tab_checklist, tab_procedures, tab_parts, tab_fluids, tab_history, tab_manual = st.tabs([
        "📋 Criticality Checklist",
        "🛠️ Maintenance Procedures",
        "📦 OEM Parts & Part Numbers",
        "🛢️ Oil Grades & Quantities",
        "📜 Service History Log",
        "📖 Subaru Reference Guide"
    ])

    with tab_checklist:
        st.markdown("### 🔧 Odometer & Operating Conditions")
        col_mil, col_sev = st.columns(2)
        with col_mil:
            mileage = st.number_input("Current Odometer Mileage (mi):", min_value=0, max_value=500000, value=105000, step=1000)
        with col_sev:
            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
            severe = st.checkbox(
                "Severe Driving Conditions", 
                value=False,
                help="Trigger shorter intervals (e.g., oil every 3,000 miles). Conditions include repeated short distances (< 5 mi), rough/mudy/salty/snowy roads, high humidity/mountains, or extremely cold weather."
            )
        st.markdown("<hr style='margin:15px 0; border-color:#eee;'/>", unsafe_allow_html=True)

    is_primary = True

    # Initialize scheduler
    scheduler = MaintenanceScheduler(mileage, severe, primary_mode=is_primary)
    schedule_items = scheduler.get_schedule()

    # Load history to filter checked/completed items at the current mileage
    history = load_history()
    completed_items_at_current_mileage = set()
    if history:
        for entry in history:
            if entry.get("mileage") == mileage:
                for item in entry.get("completed_items", []):
                    completed_items_at_current_mileage.add(item)

    due_items = [item for item in schedule_items if item["due"]]
    other_items = [item for item in schedule_items if not item["due"]]

    # Filter out items that are already completed at the current mileage
    due_items = [item for item in due_items if item["name"] not in completed_items_at_current_mileage]
    other_items = [item for item in other_items if item["name"] not in completed_items_at_current_mileage]

    with tab_checklist:
        st.subheader("📋 Maintenance Tasks Checklist")
        

        
        # Severe summary alerts
        if severe:
            st.info("**Severe conditions enabled:** Brake fluid, trans/diff gear oils, engine air filter, and inspections are accelerated.")

        completed_checks = {}

        # 🚨 Section 1: Due Now (Checklist form)
        if due_items:
            st.warning(f"⚠️ There are **{len(due_items)}** scheduled maintenance items due now at **{mileage:,} miles**:")
            st.markdown("### 🚨 Maintenance Items Due Now (Recommended):")
            for item in due_items:
                label = f"{item['priority']} - {item['name']} (⚠️ Overdue since {item['overdue_since']:,} mi)" if item.get('is_carried_forward') else f"{item['priority']} - {item['name']}"
                completed_checks[item["name"]] = st.checkbox(
                    label,
                    key=f"check_{item['name']}",
                    help=f"Interval: every {item['interval']:,} miles." if isinstance(item['interval'], int) else f"Interval: {item['interval']}"
                )
                st.markdown("<hr style='margin:2px 0;border-color:#eee;'/>", unsafe_allow_html=True)
        else:
            st.success(f"🎉 No specific maintenance services are scheduled exactly at **{mileage:,} miles**! But you can still complete and log any item below.")

        # 🔍 Section 2: Other Maintenance Items (Not currently due Checklist form)
        # Determine if current mileage exactly matches any scheduled maintenance interval milestone
        is_exact_match = False
        if mileage > 0:
            for item in schedule_items:
                interval = item.get("interval")
                name = item.get("name")
                if name == "Replace Engine Coolant (Super Coolant)":
                    if mileage == 137500 or (mileage > 137500 and (mileage - 137500) % 75000 == 0):
                        is_exact_match = True
                        break
                elif isinstance(interval, int) and interval > 0:
                    if mileage % interval == 0:
                        is_exact_match = True
                        break

        if is_exact_match:
            section_title = f"### 🔍 General Subaru WRX/STI Maintenance Items (Not currently due at {mileage:,} mi):"
        else:
            # Find the recommended next/upcoming maintenance schedule milestone
            milestones = []
            for item in schedule_items:
                interval = item.get("interval")
                name = item.get("name")
                if name == "Replace Engine Coolant (Super Coolant)":
                    if mileage < 137500:
                        milestones.append(137500)
                    else:
                        next_coolant = 137500 + (((mileage - 137500) // 75000) + 1) * 75000
                        milestones.append(next_coolant)
                elif isinstance(interval, int) and interval > 0:
                    next_mult = ((mileage // interval) + 1) * interval
                    milestones.append(next_mult)
            
            next_milestone = min(milestones) if milestones else None
            if next_milestone:
                section_title = f"### 🔍 Recommended Next Upcoming Maintenance Schedule (Due at {next_milestone:,} mi):"
            else:
                section_title = "### 🔍 General Subaru WRX/STI Maintenance Items (Not currently due):"

        st.markdown(section_title)
        st.write("Below are all scheduled items. You can check any item if completed early or as part of custom maintenance, and click 'Save' below to record to your history.")
        
        # Group other_items by criticality
        high_items = [i for i in other_items if "🔴" in i["priority"]]
        med_items = [i for i in other_items if "🟡" in i["priority"]]
        low_items = [i for i in other_items if "🟢" in i["priority"]]
        
        st.markdown("#### 🔴 High Priority\n*Replacements & Critical Protections*")
        for item in high_items:
            interval_str = f"Every {item['interval']:,} mi" if isinstance(item['interval'], int) else str(item['interval'])
            label = f"{item['name']} ({interval_str})"
            completed_checks[item["name"]] = st.checkbox(
                label,
                key=f"check_{item['name']}",
                help=f"Description: {item['description']}"
            )
            st.markdown("<hr style='margin:2px 0;border-color:#eee;'/>", unsafe_allow_html=True)
            
        st.markdown("#### 🟡 Medium Priority\n*System Inspections & Safety Sweeps*")
        for item in med_items:
            interval_str = f"Every {item['interval']:,} mi" if isinstance(item['interval'], int) else str(item['interval'])
            label = f"{item['name']} ({interval_str})"
            completed_checks[item["name"]] = st.checkbox(
                label,
                key=f"check_{item['name']}",
                help=f"Description: {item['description']}"
            )
            st.markdown("<hr style='margin:2px 0;border-color:#eee;'/>", unsafe_allow_html=True)
            
        st.markdown("#### 🟢 Low Priority\n*Lubrication & General Upkeep*")
        for item in low_items:
            interval_str = f"Every {item['interval']:,} mi" if isinstance(item['interval'], int) else str(item['interval'])
            label = f"{item['name']} ({interval_str})"
            completed_checks[item["name"]] = st.checkbox(
                label,
                key=f"check_{item['name']}",
                help=f"Description: {item['description']}"
            )
            st.markdown("<hr style='margin:2px 0;border-color:#eee;'/>", unsafe_allow_html=True)

        # Clean Save button for the checklist
        
        if st.button("💾 Save Checked Items to History", type="primary", key="checklist_save_all_btn"):
            completed_list = [name for name, val in completed_checks.items() if val]
            if not completed_list:
                st.error("Please check off at least one completed item before saving.")
            else:
                confirm_save_dialog(completed_list, mileage, severe)

    with tab_procedures:
        st.subheader("🛠️ Step-by-Step Maintenance Procedures")
        st.write("Browse detailed, step-by-step guides for all 19 maintenance and inspection services on your Subaru WRX STI.")
        
        # Search/Select Box
        selected_proc = st.selectbox("🔍 Search and select a specific service:", [item["name"] for item in schedule_items])
        matched_item = next(item for item in schedule_items if item["name"] == selected_proc)
        
        # Display the selected guide
        st.markdown(f"### {matched_item['name']}")
        st.markdown(f"**Normal Interval:** Every {matched_item['interval']:,} miles" if isinstance(matched_item['interval'], int) else f"**Normal Interval:** {matched_item['interval']}")
        st.markdown(f"**Description:** *{matched_item['description']}*")
        
        
        if matched_item.get('oil_grade') and matched_item['oil_grade'] != 'N/A':
            st.markdown(f"🛢️ **Recommended Fluid:** {matched_item['oil_grade']}")
        if matched_item.get('part_number') and matched_item['part_number'] != 'N/A':
            st.markdown(f"📦 **OEM Part Number:** {matched_item['part_number']}")
        if matched_item.get('quantity') and matched_item['quantity'] != 'N/A':
            st.markdown(f"📊 **Required Quantity:** {matched_item['quantity']}")
        if matched_item.get('specs') and matched_item['specs'] != 'N/A':
            st.markdown(f"⚙️ **Key Specifications:** {matched_item['specs']}")
            
        st.markdown("#### 📋 Step-by-Step Execution:")
        if matched_item.get('steps'):
            for idx, step in enumerate(matched_item['steps']):
                st.write(f"**{idx+1}.** {step}")
        else:
            st.write("*No procedural steps required. Follow visual inspection guidelines.*")
        
        st.markdown("---")
        st.subheader("⚙️ Browse All Procedures")
        # Show all items in simple expanders grouped by Category
        cats = sorted(list(set(item["category"] for item in schedule_items)))
        for cat in cats:
            st.markdown(f"#### {cat}")
            cat_items = [item for item in schedule_items if item["category"] == cat]
            for item in cat_items:
                interval_str = f"Every {item['interval']:,} mi" if isinstance(item['interval'], int) else str(item['interval'])
                with st.expander(f"{item['name']} ({interval_str})"): 
                    st.write(f"*{item['description']}*")
                    if item.get('steps'):
                        st.markdown("**Steps:**")
                        for idx, step in enumerate(item['steps']):
                            st.write(f"{idx+1}. {step}")

    with tab_parts:
        st.subheader("📦 OEM Parts & Part Numbers Reference")
        st.write("Reference list for replacement parts and specs.")
        
        parts_data = []
        for item in schedule_items:
            p_num = item.get('part_number', 'N/A')
            qty = item.get('quantity', 'N/A')
            if p_num != 'N/A':
                parts_data.append({
                    "Service Item": item["name"],
                    "OEM Part Number / Specs": p_num,
                    "Quantity Required": qty,
                })
                
        if parts_data:
            import pandas as pd
            df_parts = pd.DataFrame(parts_data)
            st.dataframe(df_parts, use_container_width=True, hide_index=True)
            
        st.markdown("### 🔍 Critical Parts & Hardware Guide")
        st.markdown(
            """
            **Engine Oil Filter & Washer (Primary):**
            *   **Tokyo Roki JDM Black Filter:** P/N `15208AA100`
            *   **Crush Washer:** P/N `11126AA000`
            *   *Note:* The black Tokyo Roki filter features an all-metal bypass valve calibrated to open at 23 PSI, matching high Subaru oil pump relief pressures.
            
            **Spark Plugs (Laser Iridium - Primary):**
            *   **SILFR6A (NGK 7913):** P/N `22401AA670`
            *   *Note:* Use dry threads (no anti-seize) and torque strictly to 13–17 ft-lb to prevent stripping aluminum heads.
            """
        )
        st.markdown(
            """
            **Timing Belt & Accessories (DOHC EJ257 - Primary):**
            *   **Timing Belt:** P/N `13028AA250`
            *   **Complete Timing Kit:** Aisin `TKF-012`
            *   **Water Pump:** P/N `21111AA240` (Aisin WPF-023)
            *   **Hydraulic Tensioner:** P/N `13033AA042`
            
            **Air Conditioning Stretch Belt Kit (Primary):**
            *   **AC Stretch Belt:** P/N `11718AA082` (Replaces 11718AA081)
            *   *Note:* Sourcing the kit with the specialized plastic installation guide tool is mandatory to prevent rib damage.
            """
        )

    with tab_fluids:
        st.subheader("🛢️ Subaru Recommended Fluids, Grades & Capacities")
        st.write("Maintain exact fluid dynamics and thermal protection parameters for your symmetrical AWD drivetrain.")
        
        fluids_data = [
            {
                "Compartment": "Engine Crankcase (EJ257)",
                "Fluid Type / Specification": "API SM / SN Full Synthetic (SAE 5W-30 or 5W-40)",
                "Capacity": "4.5 Quarts (4.3 Liters) with filter",
                "Key Specs / Notes": "Drain plug torque: 33-34 ft-lb. 5W-40 weight (e.g. Rotella T6, Motul 8100) resists thermal shear under high boost."
            },
            {
                "Compartment": "Manual Transmission & Front Diff",
                "Fluid Type / Specification": "API GL-5 High Performance Gear Oil (SAE 75W-90)",
                "Capacity": "Dry Fill: 4.1 Quarts. Service Fill: ~3.5 Quarts",
                "Key Specs / Notes": "Gearbox shares oil bath. Standard fluid swaps require ~3.5 quarts because some fluid remains trapped in gear clusters."
            },
            {
                "Compartment": "Rear Differential",
                "Fluid Type / Specification": "API GL-5 Hypoid Gear Oil (SAE 75W-90 / Motul 90PA for track)",
                "Capacity": "1.0 Quart (0.95 Liters)",
                "Key Specs / Notes": "Fill/drain plug torque: 36–43 ft-lb. 90-weight LS fluid prevents gear chatter under shock loads."
            },
            {
                "Compartment": "Engine Cooling System",
                "Fluid Type / Specification": "Subaru Super Coolant (Pre-Mixed Blue) + Conditioner",
                "Capacity": "8.1 Quarts (7.7 Liters)",
                "Key Specs / Notes": "Never mix green conventional coolant. Add one bottle of SOA635065 Cooling System Conditioner to protect head gaskets."
            },
            {
                "Compartment": "Brake & Clutch Reservoirs",
                "Fluid Type / Specification": "DOT 3 or DOT 4 Premium Synthetic",
                "Capacity": "Fill to Max Line (~1.0 Liter system)",
                "Key Specs / Notes": "DOT 5.1 accepted for heavy track. Avoid silicone-based DOT 5. Keep fluid off painted body panels."
            },
            {
                "Compartment": "Power Steering System",
                "Fluid Type / Specification": "Dexron III / Subaru ATF-HP",
                "Capacity": "~0.8 Liters (System capacity)",
                "Key Specs / Notes": "Use premium ATF fluid rather than traditional power steering fluid."
            }
        ]
        
        import pandas as pd
        df_fluids = pd.DataFrame(fluids_data)
        st.dataframe(df_fluids, use_container_width=True, hide_index=True)
        
        st.info("💡 **The 5-Minute Dipstick Rule (NHTSA TSB):** Wait at least 5 minutes after turning off a warm engine on level ground. This allows oil suspended in the boxer layout to fully drain back into the pan for an accurate dipstick measurement.")

    with tab_history:
        st.subheader("📜 Maintenance & Service Log")
        
        history = load_history()
        
        # --- NEW FEATURES: ITEM-BY-ITEM COMPLETION LEDGER (PRIORITY COLUMN REMOVED) ---
        st.markdown("### 📊 Individual Item Completion Ledger")
        st.write("Scan the last logged date and mileage for each individual maintenance and inspection service. This ledger automatically indexes your entire history folder to prevent items from falling through the cracks.")
        
        ledger_data = []
        for item in schedule_items:
            item_name = item["name"]
            interval = f"Every {item['interval']:,} mi" if isinstance(item['interval'], int) else str(item['interval'])
            
            # Find the latest logged completion in history
            last_date = "No Record"
            last_mileage = "Never Logged"
            raw_last_mi = 0
            
            if history:
                # Search chronologically forward so the last match is the most recent
                for entry in history:
                    if item_name in entry.get("completed_items", []):
                        last_date = entry["date"]
                        last_mileage = f"{entry['mileage']:,} mi"
                        raw_last_mi = entry["mileage"]
            
            # Determine Status Badge
            if last_date == "No Record":
                status = "⚪ Not Yet Logged"
            else:
                # If currently marked as due by the scheduler engine, mark as due/overdue
                if item["due"]:
                    status = "🔴 Overdue / Due Now"
                else:
                    status = "🟢 Completed & OK"
                    
            ledger_data.append({
                "Maintenance Item": item_name,
                "Last Completed Date": last_date,
                "Last Completed Mileage": last_mileage,
                "Interval": interval,
                "Current Status": status
            })
            
        import pandas as pd
        df_ledger = pd.DataFrame(ledger_data)
        
        # Style/highlight the status column if possible, or just render a clean interactive dataframe
        st.dataframe(
            df_ledger, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Current Status": st.column_config.TextColumn(
                    "Current Status",
                    help="🟢 OK: Item was recently completed. 🔴 Due: Needs attention based on mileage or history. ⚪ Not Logged: No entry in history."
                )
            }
        )

        st.markdown("<hr style='margin:15px 0; border-color:#eee;'/>", unsafe_allow_html=True)
        st.markdown("### 🕒 Chronological Service History Timeline")
        st.write("Below is a detailed timeline showing each completed service item in chronological order as logged from your checklist.")
        
        timeline_data = []
        if history:
            for entry in history:
                date_val = entry.get("date", "")
                mi_val = entry.get("mileage", 0)
                for item in entry.get("completed_items", []):
                    timeline_data.append({
                        "Date": date_val,
                        "Odometer Mileage (mi)": mi_val,
                        "Completed Service Item": item
                    })
            
            df_timeline = pd.DataFrame(timeline_data)
            if not df_timeline.empty:
                df_timeline = df_timeline.sort_values(by=["Date", "Odometer Mileage (mi)"], ascending=[False, False])
                df_timeline["Odometer Mileage (mi)"] = df_timeline["Odometer Mileage (mi)"].apply(lambda x: f"{x:,} mi")
                st.dataframe(df_timeline, use_container_width=True, hide_index=True)
            else:
                st.info("No timeline items logged yet.")
        else:
            st.info("No timeline items logged yet.")
        


    with tab_manual:
        st.subheader("📖 Official Subaru WRX STI Reference Manual")
        
        st.markdown(
            """
            ### 🔧 Critical DIY Torque Specifications (Grounded in Subimods DIY Guide)
            *Grounded in factory and performance specialist specifications to prevent stripping aluminum threads or catastrophic failures:*
            
            ##### ⚙️ Engine Core Torque Specs
            | Component | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Spark Plugs (Dry)** | **13–17 ft-lb (18–23 N·m)** | Dry threads. Essential for aluminum cylinder heads to prevent thread stripping or ceramic fracture. |
            | **Ignition Coil Bolts** | **11.8 ft-lb (16 N·m)** | Prevents electrical vibration misfires under boost. |
            | **Valve Cover Bolts** | **4.7–5.8 ft-lb (6.4–7.8 N·m)** | Very low torque. Overtightening warps covers and causes severe oil leaks. |
            | **Intake Manifold Bolts** | **17–20 ft-lb (23–27 N·m)** | Prevents vacuum/boost leaks skewing engine air-fuel ratios (AFR). |
            | **Exhaust Manifold / Header Studs** | **22–29 ft-lb (30–39 N·m)** | Exhaust heat cycling. Apply anti-seize. |
            | **Timing Belt Tensioner Bolt** | **28–29 ft-lb (38–39 N·m)** | Crucial. Improper torque causes timing belt slip and catastrophic piston-to-valve contact. |
            | **Cylinder Head Bolts (TTY)** | **TTY (14 -> 51 ft-lb -> 90° -> 90°)** | Torque-to-Yield. Never reuse stretched head bolts. Must be replaced every time. |
            | **Engine Oil Filter** | **Hand-tight + ¾ turn** | Lightly lubricate gasket with clean oil. Do not tighten with a wrench. |

            ##### 🛢️ Drivetrain & Fluid Plugs
            | Component / Plug | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Oil Pan Drain Plug** | **33 ft-lb (45 N·m)** | Always use a new copper/aluminum crush gasket (11126AA000) to prevent pan stripping. |
            | **Transmission Drain/Fill Plugs** | **33 ft-lb (45 N·m)** | Check fill plug removes safely before draining fluid so you don't strand the car. |
            | **Rear Differential Drain/Fill Plugs** | **36–43 ft-lb (49–58 N·m)** | Differential case plugs. Always clean magnetic tips of metal shavings. |
            | **Pitch Stop Mount Bolts** | **35–49 ft-lb (47–66 N·m)** | Protects stamped firewall brackets from welds tearing. |
            | **Rear Subframe Bolts** | **55–69 ft-lb (75–94 N·m)** | Re-torque in cross-pattern if installing lockdown sleeves. |

            ##### 🚙 Suspension, Chassis & Wheels
            | Component / Fastener | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Wheel Lug Nuts (Alloy)** | **89–94 ft-lb (120–127 N·m)** | Always torque in star pattern. Prevents warped brake rotors and sheared studs. |
            | **Front & Rear Axle Nut** | **140–174 ft-lb (190–236 N·m)** | Mandatory to stake/cotter pin the nut after final torque to prevent backup. |
            | **Strut Top Nut** | **14–17 ft-lb (19–23 N·m)** | Hold the central shaft with an Allen key while tightening the nut. |
            | **Strut-to-Knuckle Bolts** | **112–133 ft-lb (152–180 N·m)** | Upper cam bolt controls camber setting. |
            | **Front Lower Control Arm Bolts** | **74–96 ft-lb (100–130 N·m)** | Torque with vehicle's weight fully loaded on suspension. |
            | **Rear Lower Control Arm Bolts** | **59–73 ft-lb (80–99 N·m)** | Tighten loaded. |
            | **Sway Bar End Link Nuts** | **28–33 ft-lb (38–45 N·m)** | Check link alignment to prevent binding noise. |
            | **Sway Bar Bracket Bolts** | **18–25 ft-lb (24–34 N·m)** | Ensure bushing is perfectly centered. |

            ##### 🛑 Calipers & Brake Plumbing
            | Fastener | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Front Brembo-to-Knuckle Bolts** | **80 ft-lb (114 N·m)** | *Corrected Spec.* Original FSM incorrectly lists 114.3 ft-lb, stripping caliper ears. |
            | **Rear Brembo-to-Knuckle Bolts** | **52.8 ft-lb (71.5 N·m)** | Proper spec for aluminum rear calipers. |
            | **Brake Hose Banjo Bolt** | **13–15 ft-lb (18–20 N·m)** | Sourced from Subimods. Use new washers on both sides of banjo fitting. |
            | **Front Brake Caliper Bracket Bolts** | **59–79 ft-lb (80–107 N·m)** | Non-Brembo bracket mounts. |
            | **Front Brake Caliper Slide Pin Bolts** | **17–25 ft-lb (23–34 N·m)** | Grease pins with high-temp brake grease. |
            | **Rear Brake Caliper Bracket Bolts** | **34–52 ft-lb (46–70 N·m)** | Lower than front bracket mounts. |
            """
        )
        
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
        console.print(Panel(Text(banner_text, style="bold cyan", justify="center"), subtitle="Vehicle Maintenance Schedule & Log Tracker", border_style="blue"))

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
            console.print("1. Calculate Schedule & Track Maintenance Checklist (Standard Mode)")
            console.print("2. View Service History Log")
            console.print("3. View Critical Torque & TSB Specs")
            console.print("4. Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "4":
                console.print("[bold green]Thank you for keeping your STI well-maintained. Safe boosting![/bold green]")
                break
                
            elif choice == "3":
                print_banner()
                console.print(Panel("[bold green]🔧 CRITICAL DIY TORQUE SPECIFICATIONS (Subimods DIY Guide)[/bold green]\n"
                                    "• [cyan]Spark Plugs (Dry):[/cyan] 13-17 ft-lb (18-23 N·m) — prevent cylinder head thread stripping\n"
                                    "• [cyan]Ignition Coil Bolts:[/cyan] 11.8 ft-lb (16 N·m) — prevent electrical misfires under boost\n"
                                    "• [cyan]Valve Cover Bolts:[/cyan] 4.7-5.8 ft-lb (6.4-7.8 N·m) — prevent warp & oil leakage\n"
                                    "• [cyan]Intake Manifold Bolts:[/cyan] 17-20 ft-lb (23-27 N·m) — prevent boost/vacuum leaks\n"
                                    "• [cyan]Exhaust Manifold/Headers:[/cyan] 22-29 ft-lb (30-39 N·m) — apply anti-seize\n"
                                    "• [cyan]Timing Belt Tensioner Bolt:[/cyan] 28-29 ft-lb (38-39 N·m) — prevent timing belt slip\n"
                                    "• [cyan]Wheel Lug Nuts (Alloy):[/cyan] 89-94 ft-lb (120-127 N·m) — prevent warped rotors\n"
                                    "• [cyan]Front & Rear Axle Nuts:[/cyan] 140-174 ft-lb (190-236 N·m) — stake/pin after final torque\n"
                                    "• [cyan]Front Brembo Caliper Bolts:[/cyan] 80 ft-lb (114 N·m) with anti-seize — corrected spec\n"
                                    "• [cyan]Rear Brembo Caliper Bolts:[/cyan] 52.8 ft-lb (71.5 N·m) — proper aluminum caliper spec\n"
                                    "• [cyan]Brake Hose Banjo Bolt:[/cyan] 13-15 ft-lb (18-20 N·m) — replace crush washers on both sides\n"
                                    "• [cyan]Transmission Drain/Fill Plugs:[/cyan] 33 ft-lb (45 N·m) — check fill removes safely first\n"
                                    "• [cyan]Rear Diff Drain/Fill Plugs:[/cyan] 36-43 ft-lb (49-58 N·m) — GL-5 gear oil spec\n"
                                    "• [cyan]Strut-to-Knuckle Bolts:[/cyan] 112-133 ft-lb (152-180 N·m) — controls camber setting\n\n"
                                    "[bold yellow]📖 RECALLS & CRITICAL TSB ADVICE[/bold yellow]\n"
                                    "• [red]The 5-Minute Dipstick Rule (NHTSA TSB):[/red] Wait 5 min after shutdown on flat ground to let oil settle before measuring.\n"
                                    "• [red]Interference Engine warning:[/red] Sapped timing belt destroys cylinder heads. Replace water pump/tensioner all-at-once.\n"
                                    "• [red]Tire Sizing AWD Rule:[/red] Tread depth matching within 1/16 in prevents center diff failure.",                                    title="Subaru WRX STI Reference Sheets"))
                input("\nPress Enter to return to main menu...")
                
            elif choice == "2":
                show_history_cli()
                
            elif choice == "1":
                print_banner()
                mileage = IntPrompt.ask("Enter current vehicle mileage", default=105000)
                severe = Confirm.ask("Is the car driven in severe conditions (short trips, mud/dust, extreme heat/cold, road salt)?")
                
                # Default to Primary schedule for CLI
                scheduler = MaintenanceScheduler(mileage, severe, primary_mode=True)
                items = scheduler.get_schedule()
                
                due_items = [i for i in items if i["due"]]
                other_items = [i for i in items if not i["due"]]
                
                print_banner()
                console.print(f"[bold cyan]Maintenance Checklist (Standard Mode) for {mileage:,} miles[/bold cyan]")
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
                        table_all = Table(title="Other Scheduled Maintenance Items")
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

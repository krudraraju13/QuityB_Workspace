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

class MaintenanceScheduler:
    def __init__(self, mileage, severe=False, primary_mode=True):
        self.mileage = mileage
        self.severe = severe
        self.primary_mode = primary_mode

    def get_schedule(self):
        items = []
        history = load_history()
        
        # Define standard intervals and info from sources
        # Structure: (Name, Base Interval, Severe Interval, Part Number, Quantity, Description)
        maintenance_defs = [
            (
                "Replace Engine Oil & Filter", 
                6000, 
                3000, 
                "15208AA100 (Tokyo Roki JDM Black Filter)", 
                "4.5 Quarts (4.3 Liters) + 1 Crush Washer (11126AA000)",
                "Standard: 6,000 mi / 6 months. Severe: 3,000 mi / 3 months. Drain plug torque: 33-34 ft-lb. 5W-40 weight (e.g., Rotella T6, Motul 8100) resists thermal shear and degradation better under high boost. Wait at least 5 minutes before checking dipstick (5-Minute Dipstick Rule)."
            ),
            (
                "Rotate Tires & Check Pressures", 
                6000, 
                6000, 
                "N/A", 
                "N/A",
                "Rotate tires to ensure even tread wear. Lug nut thread m12x1.25, torque strictly to 89-94 ft-lb in a star pattern (never use an impact gun for final torque) to prevent warped brake rotors."
            ),
            (
                "Replace Cabin Air Filter", 
                12000, 
                7500, 
                "72880FG000", 
                "1 Filter",
                "Standard: 12,000 mi / 12 months. Severe: 7,500 mi / 1 year. Protects HVAC and passenger cabin air quality from dust, pollen, and debris."
            ),
            (
                "Inspect Front & Rear Brake Pads & Rotors", 
                12000, 
                6000, 
                "N/A", 
                "N/A",
                "Check pad thickness and rotor condition. Front Brembo caliper-to-knuckle bolts should be torqued to 80 ft-lb (FSM incorrect spec says 114.3 ft-lb, which strips aluminum threads). Lubricate with copper anti-seize and limit torque to 60 ft-lb to prevent dissimilar metal galvanic corrosion."
            ),
            (
                "Replace Engine Air Filter", 
                30000, 
                7500, 
                "16546AA090", 
                "1 Filter",
                "Standard: 30,000 mi / 3 years. Severe: 7,500 mi / 1 year. Ensures clean air induction and peak turbo power delivery."
            ),
            (
                "Replace Brake Fluid", 
                30000, 
                20000, 
                "N/A", 
                "~1.0 Liter (DOT 3 or DOT 4 Premium)",
                "Standard: 30,000 mi / 2 years. Severe: 20,000 mi / 1 year. Flush moisture and contaminants from the Brembo caliper hydraulic system."
            ),
            (
                "Replace Manual Transmission Gear Oil", 
                30000, 
                20000, 
                "API GL-5 SAE 75W-90", 
                "Service Fill: ~3.5 Quarts (Dry: 4.1 Quarts / 4.1 Liters)",
                "Gearbox and front diff share oil bath in TY856 transaxle. Standard fluid swaps require ~3.5 quarts because some fluid remains trapped. Plug torque: 37 ft-lb (alum washer) or 52 ft-lb (copper washer)."
            ),
            (
                "Replace Rear Differential Gear Oil", 
                30000, 
                20000, 
                "API GL-5 SAE 75W-90", 
                "1.0 Quart (0.95 Liters)",
                "Protects hypoid gears. Fill/drain plug torque: 36–43 ft-lb. 90-weight LS fluid (e.g. Motul 90PA) prevents gear chatter under shock loads and aggressive track use."
            ),
            (
                "Inspect Fuel Lines and Connections", 
                30000, 
                30000, 
                "N/A", 
                "N/A",
                "Verify security and check for any leakage, dry-rotting, or deterioration."
            ),
            (
                "Inspect Steering & Suspension Systems", 
                30000, 
                30000, 
                "N/A", 
                "N/A",
                "Check steering gearbox, linkage, tie rods, boot seals, and suspension joints."
            ),
            (
                "Replace Spark Plugs", 
                60000, 
                30000, 
                "22401AA670 (NGK SILFR6A Laser Iridium)", 
                "4 Spark Plugs",
                "Standard: 60,000 mi / 6 years. Severe: 30,000 mi / 3 years. Use dry threads strictly. Torque to 13–17 ft-lb (18-23 Nm) to prevent thread stripping in aluminum heads."
            ),
            (
                "Replace PCV Valve", 
                60000, 
                30000, 
                "N/A", 
                "1 PCV Valve",
                "Standard: 60,000 mi. Severe: 30,000 mi. Critically important; a sticking or failed PCV valve causes excessive blow-by and oil vapor induction, triggering knocking/piston failure."
            ),
            (
                "Replace Intank Fuel Filter (2005+)", 
                72000, 
                35000, 
                "N/A", 
                "1 Intank Filter",
                "Standard: 72,000 mi / 6 years. Severe: 35,000 mi / 3 years. Protects the fuel delivery system and maintains optimal pressure."
            ),
            (
                "Replace Timing Belt (EJ257 DOHC)", 
                105000, 
                90000, 
                "13028AA250 (Aisin Kit TKF-012)", 
                "1 Timing Belt Kit",
                "Standard: 105,000 mi / 105 months. Severe: 90,000 mi. Critical interference engine component. Always replace water pump, hydraulic tensioner, and idlers simultaneously."
            ),
            (
                "Replace Engine Coolant (Super Coolant)", 
                137500, 
                137500, 
                "Super Coolant (Pre-Mixed Blue)", 
                "8.1 Quarts (7.7 Liters)",
                "First change at 137,500 mi / 11 years; subsequent changes every 75,000 mi / 6 years. Add one bottle of SOA635065 Cooling System Conditioner to protect head gaskets. Never mix green coolant."
            )
        ]

        for name, base_int, sev_int, p_num, qty, desc in maintenance_defs:
            interval = sev_int if self.severe else base_int
            
            # Find last completed mileage
            last_mi = None
            if history:
                completions = [entry["mileage"] for entry in history if name in entry.get("completed_items", [])]
                if completions:
                    last_mi = max(completions)
            
            # Calculate due status
            if name == "Replace Engine Coolant (Super Coolant)":
                if last_mi is None:
                    due = self.mileage >= 137500
                else:
                    due = (self.mileage - last_mi) >= 75000
            else:
                if last_mi is None:
                    due = self.mileage >= interval
                else:
                    due = (self.mileage - last_mi) >= interval
            
            items.append({
                "name": name,
                "interval": interval,
                "due": due,
                "part_number": p_num,
                "quantity": qty,
                "description": desc,
                "last_completed": last_mi
            })
            
        return items

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
        "📋 Maintenance Status",
        "🛠️ Maintenance Procedures",
        "📦 OEM Parts & Part Numbers",
        "🛢️ Oil Grades & Quantities",
        "📜 Service History Log",
        "📖 Subaru Reference Guide"
    ])

    with tab_checklist:
        st.markdown("### 🔧 Odometer & Operating Conditions")
        st.markdown(
            """
            <style>
            div[data-testid="stNumberInput"] input {
                font-size: 22px !important;
                height: 52px !important;
                font-weight: bold !important;
            }
            /* Clean up any default spacing since label is removed */
            div[data-testid="stNumberInput"] label {
                display: none !important;
            }
            div[data-testid="stNumberInput"] {
                margin-top: 0px !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        col_mil, col_sev = st.columns(2)
        with col_mil:
            mileage = st.number_input("", min_value=0, max_value=500000, value=None, step=1000, placeholder="Enter current mileage")
        with col_sev:
            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
            severe = st.checkbox(
                "Severe Driving Conditions", 
                value=False,
                help="Trigger shorter intervals (e.g., oil every 3,000 miles). Conditions include repeated short distances (< 5 mi), rough/mudy/salty/snowy roads, high humidity/mountains, or extremely cold weather."
            )
        st.markdown("<hr style='margin:15px 0; border-color:#eee;'/>", unsafe_allow_html=True)

    is_primary = True

    if mileage is not None:
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

        with tab_checklist:
            due_now = [item for item in schedule_items if item["due"] and item["name"] not in completed_items_at_current_mileage]
            upcoming = [item for item in schedule_items if not item["due"] and item["name"] not in completed_items_at_current_mileage]
            already_done = [item for item in schedule_items if item["name"] in completed_items_at_current_mileage]

            col_due, col_up = st.columns(2)

            with col_due:
                st.markdown("#### 🔴 Due Now / Overdue")
                if due_now:
                    st.write("The following items require immediate maintenance or check-off:")
                    completed_list = []
                    for item in due_now:
                        last_str = f" (Last completed: {item['last_completed']:,} mi)" if item['last_completed'] is not None else " (Never completed)"
                        checked = st.checkbox(f"**{item['name']}**{last_str}\nInterval: every {item['interval']:,} mi", key=f"due_{item['name']}")
                        if checked:
                            completed_list.append(item["name"])
                    
                    if completed_list:
                        if st.button("Log Selected Items", type="primary", use_container_width=True):
                            confirm_save_dialog(completed_list, mileage, severe)
                else:
                    st.success("🟢 All good! No items are currently overdue or due at this mileage.")

            with col_up:
                st.markdown("#### 🕒 Upcoming Maintenance")
                if upcoming:
                    st.write("Plan ahead for the following scheduled services:")
                    for item in upcoming:
                        last_str = f" (Last completed: {item['last_completed']:,} mi)" if item['last_completed'] is not None else ""
                        due_in = item['interval'] - (mileage - (item['last_completed'] or 0))
                        st.info(f"**{item['name']}**{last_str}\nDue in: **{due_in:,} miles** (at {((item['last_completed'] or 0) + item['interval']):,} mi)")
                else:
                    st.write("Enter an odometer reading above to show schedules.")

            if already_done:
                st.markdown("<hr style='margin:15px 0; border-color:#eee;'/>", unsafe_allow_html=True)
                st.markdown("#### ✅ Completed at This Mileage")
                for item in already_done:
                    st.write(f"- 🟢 **{item['name']}** (Logged)")

    else:
        with tab_checklist:
            st.info("💡 **Enter your current odometer mileage** above to generate your customized vehicle maintenance status, log services, and track due dates.")

    # Procedures Tab
    with tab_procedures:
        st.subheader("🛠️ Maintenance Procedures Guide")
        st.write("Step-by-step DIY instructions and crucial checks for WRX STI owners.")
        
        proc_selection = st.selectbox(
            "Select Procedure:",
            [
                "Select a procedure...",
                "Engine Oil & Filter Swap",
                "Manual Transmission Gear Oil Replacement",
                "Rear Differential Oil Swap",
                "Spark Plug & Ignition Coil Installation",
                "Timing Belt DOHC EJ257 Complete Swap",
                "Brembo Caliper Thread Repair (Time-Sert)"
            ]
        )
        
        if proc_selection == "Engine Oil & Filter Swap":
            st.markdown(
                """
                ### 🛢5 Engine Oil & Filter Swap Procedure
                **Target Thread Torque:** Drain plug: `33-34 ft-lb` (M20, 44-46 Nm). Ensure a new OEM metal crush washer P/N `11126AA000` is used [cite: 373, 377].
                
                **Step-by-Step Instructions:**
                1. Ensure engine is warm. Park on flat ground and jack up front of car (use heavy duty jack stands and tire chocks).
                2. Position oil catch pan under the drain plug (14mm). Carefully remove plug and drain oil completely.
                3. Clean the drain plug threads, fit the new **Subaru Crush Washer** with its flat face against the oil pan, and hand thread [cite: 156]. Torque to **33-34 ft-lb** [cite: 373].
                4. Use a filter wrench to remove the engine oil filter. Clean the contact surface on the engine block.
                5. Apply a light film of fresh engine oil to the rubber O-ring of the **Tokyo Roki Black Filter (15208AA100)** [cite: 156, 376]. Hand tighten the filter until seal contacts, then turn it exactly 3/4 to 1 full turn further [cite: 242].
                6. Add **4.5 quarts** of synthetic oil (5W-30 or 5W-40) [cite: 371]. 
                7. **The 5-Minute Dipstick Rule:** Wait at least 5 minutes after turning off a warm engine on level ground to let oil suspended in the boxer layout fully drain back into the oil pan for an accurate reading [cite: 141].
                """
            )
        elif proc_selection == "Manual Transmission Gear Oil Replacement":
            st.markdown(
                """
                ### ⚙ Manual Transmission & Front Diff Gear Oil Swap
                **Compartment Dynamics:** The manual transmission and the front differential share a common oil bath within the main TY856 transaxle casing [cite: 369].
                **Target Thread Torque:** 
                * Gearbox Drain Plug (with Aluminum washer): `37 ft-lb` (50 Nm) [cite: 373]
                * Gearbox Drain Plug (with Copper washer): `52 ft-lb` (70 Nm) [cite: 373]
                
                **Step-by-Step Instructions:**
                1. Elevate the entire car completely flat on all four jack stands [cite: 369].
                2. Locate the transmission case. Remove the intercooler if filling from top, or use a fluid transfer pump from underneath [cite: 389].
                3. **Critical Tip:** Always remove the fill plug first to ensure you can fill, then remove the lower drain plug [cite: 251].
                4. Clean the magnetic drain plug thoroughly of wear debris. Install with a new seal and torque to specifications [cite: 373].
                5. Fill with **~3.5 quarts** of SAE 75W-90 GL-5 gear oil (e.g. Motul Gear 300) [cite: 369]. Note: A standard fluid swap takes only ~3.5 quarts because some fluid remains trapped within the gear clusters and DCCD electromagnetic mechanism [cite: 369].
                6. Reinstall fill plug and torque to specifications.
                """
            )
        elif proc_selection == "Rear Differential Oil Swap":
            st.markdown(
                """
                ### 🔩 Rear Differential Oil Swap
                **Target Thread Torque:** Fill and drain plugs (M20): `36–43 ft-lb` (49-58 Nm) [cite: 373].
                
                **Step-by-Step Instructions:**
                1. Elevate the rear end. Locate the rear diff case [cite: 369].
                2. Remove the top fill plug (1/2" drive or 13mm socket) to verify you can fill, then remove the lower drain plug [cite: 251].
                3. Allow 1.0 quart of old fluid to drain completely [cite: 369]. Clean the magnet on the drain plug.
                4. Apply thread sealant (like liquid Teflon) to the plug threads. Reinstall drain plug and torque to **36-43 ft-lb** [cite: 373].
                5. Use a pump to inject exactly **1.0 quart (0.95 Liters)** of SAE 75W-90 GL-5 hypoid gear oil into the fill hole until it begins to seep out [cite: 369, 371]. For aggressive track use or high ambient heat, a dedicated 90-weight limited-slip lubricant (e.g., Motul 90PA) prevents gear chatter [cite: 369].
                6. Reinstall fill plug with thread sealant and torque to specification.
                """
            )
        elif proc_selection == "Spark Plug & Ignition Coil Installation":
            st.markdown(
                """
                ### ⚡ Spark Plug & Ignition Coil Replacement Guide
                **Target Thread Torque:** 
                * Spark Plugs (M14): `13–17 ft-lb` (18-23 Nm) - **Use Dry threads strictly (no anti-seize!)** [cite: 373]
                * Ignition Coil Pack Bolts: `11.8 ft-lb` (16 Nm) [cite: 373]
                
                **Step-by-Step Instructions:**
                1. Disconnect battery [cite: 393]. Remove air intake box (right side) and battery/washer fluid reservoir bracket components (left side) to access coil packs [cite: 393].
                2. Remove the 10mm bolts holding the ignition coils, and pull out the coil packs [cite: 393].
                3. Use a 5/8" spark plug socket, a 3" extension, and a swivel ratchet to carefully break loose and retrieve the old plugs [cite: 393].
                4. Ensure the new spark plugs (**NGK Laser Iridium SILFR6A**, P/N `22401AA670`) are gapped correctly [cite: 377, 393]. Hand thread them into the cylinder head to prevent cross-threading [cite: 393].
                5. Torque dry to **13-17 ft-lb** [cite: 373]. *Do not use anti-seize*, as it acts as a lubricant and will lead to over-torquing, which strips or cracks the soft aluminum cylinder heads [cite: 168, 372].
                6. Reinstall the ignition coil pack and torque the mounting bolt to **11.8 ft-lb** [cite: 373] to ensure secure seating and prevent misfires under boost [cite: 170].
                """
            )
        elif proc_selection == "Timing Belt DOHC EJ257 Complete Swap":
            st.markdown(
                """
                ### ⚙ Timing Belt DOHC EJ257 Replacement Procedure
                The EJ257 is a DOHC interference engine; timing misalignment during belt replacement will cause the valves to strike the pistons, resulting in severe internal engine damage [cite: 392].
                
                **Interval:** Standard timing belt replacement is **105,000 miles** / 105 months, with severe early swap recommended at **90,000 miles** [cite: 370].
                
                **Step-by-Step Instructions:**
                1. **Cooling System Depressurization:** Disconnect negative battery terminal [cite: 393]. Open the radiator petcock drain plug and drain the coolant [cite: 393].
                2. **Accessing the Assembly:** Remove the plastic intake ducting and the top-mount intercooler [cite: 393]. Loosen the alternator bracket adjustment bolt to release tension, and remove the alternator and power steering V-belts [cite: 393]. Loosen the air conditioning compressor bracket, and remove the stretch belt [cite: 393].
                3. **Crank Pulley Removal:** Lock the engine's rotation using the crankshaft holding tool, and use a 22 mm socket on a breaker bar to break the crank pulley bolt loose. Remove the bolt and pull the pulley off the snout [cite: 393].
                4. **Timing Cover Disassembly:** Unbolt and remove the outer and center timing covers [cite: 393].
                5. **Component Alignment:** Thread the crank bolt back into the snout. Rotate the crankshaft clockwise until the timing mark on the sprocket lines up with the block notch [cite: 393]. Verify that the notches on the camshaft sprockets align with their corresponding timing marks on the rear timing covers and that the double alignment lines on the intake and exhaust sprockets face each other [cite: 393].
                6. **Belt Removal:** Remove the lower cogged idler pulley, which releases belt tension, allowing you to slip the timing belt off [cite: 393].
                7. **Water Pump and Idlers Replacement:** Unbolt the hydraulic tensioner assembly and remaining idlers [cite: 393]. Remove water pump mounting bolts, discard the old paper gasket, clean the mating surface, and install a new water pump (Aisin WPF-023) with a new OEM gasket [cite: 377, 393].
                8. **Hydraulic Tensioner Compression:** Position the hydraulic tensioner in a bench vise. Slowly compress the plunger over a minimum of 3 minutes to prevent damage to the internal valving. Once retracted, slide a 1.5 mm hex key or drill bit through the alignment holes to lock it in place [cite: 393].
                9. **Reassembly & Alignment Check:** Bolt the compressed tensioner and new idlers onto the block [cite: 393]. Route the new timing belt (P/N `13028AA250`) starting from the crankshaft sprocket, moving around the passenger-side sprockets, and finishing at the driver-side sprockets [cite: 377, 393]. Install the lower cogged idler last to apply initial tension [cite: 393]. Double-check that all timing marks remain perfectly aligned [cite: 393]. Pull the lockpin out of the hydraulic tensioner to apply operating tension to the belt [cite: 393]. Rotate the crankshaft clockwise two full turns by hand, and verify that the timing marks realign perfectly [cite: 393]. Reinstall covers, pulleys, belts, and intercooler [cite: 393].
                """
            )
        elif proc_selection == "Brembo Caliper Thread Repair (Time-Sert)":
            st.markdown(
                """
                ### 🔩 Brembo Caliper Dissimilar Metal Corrosion & Thread Repair
                **The Problem:** Steel mounting bolts (Grade 10.9) secured directly into cast-aluminum Brembo calipers create a galvanic couple [cite: 384]. In environments with moisture and road salt, galvanic corrosion forms an aluminum oxide layer that binds the threads [cite: 384]. Over-torquing to the incorrect Factory Service Manual (FSM) spec of 114.3 ft-lb shears the aluminum threads completely out of the caliper mounting ears [cite: 384].
                
                **The Solution:** Repair damaged caliper ears by installing precision-machined steel thread inserts, such as a **Time-Sert M12 x 1.5 metric kit (P/N 1215)** [cite: 385].
                
                **Step-by-Step Instructions:**
                1. Bore out the damaged mounting hole using a **31/64-inch** high-speed steel drill bit [cite: 385].
                2. Tap the hole with a specialized Time-Sert tap while lubricating continuously with cutting oil [cite: 385].
                3. Clean the threads completely of all metal filings and cutting fluid using brake parts cleaner and shop air [cite: 157].
                4. Thread a steel insert pre-treated with high-strength red threadlocker into the caliper ear [cite: 385].
                5. Drive the inserting tool through the sleeve, expanding the lower threads to lock the insert permanently in place [cite: 385].
                6. To prevent future thread galling, apply a light coat of copper anti-seize to the bolts and limit torque strictly to the corrected spec of **80 ft-lb (dry)** or **60 ft-lb (lubricated)** [cite: 162, 385].
                """
            )
        else:
            st.info("💡 Select a maintenance procedure from the dropdown menu above to read detailed instructions and torque specifications.")

    # OEM Parts Tab
    with tab_parts:
        st.subheader("📦 OEM Parts & Part Numbers Reference")
        if mileage is None:
            st.info("💡 **Enter your current odometer mileage** in the Maintenance Status tab to view parts specifications.")
        else:
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
                *   **Tokyo Roki JDM Black Filter:** P/N `15208AA100` [cite: 377]
                *   **Crush Washer:** P/N `11126AA000` [cite: 377]
                *   *Note:* The black Tokyo Roki filter features an all-metal bypass valve calibrated to open at 23 PSI, matching high Subaru oil pump relief pressures to prevent unfiltered oil bypass [cite: 376].
            
                **Spark Plugs (Laser Iridium - Primary):**
                *   **SILFR6A (NGK 7913):** P/N `22401AA670` [cite: 377]
                *   *Note:* Use dry threads (no anti-seize) and torque strictly to 13–17 ft-lb to prevent stripping aluminum heads [cite: 373].
                """
            )
            st.markdown(
                """
                **Timing Belt & Accessories (DOHC EJ257 - Primary):**
                *   **Timing Belt:** P/N `13028AA250` [cite: 377]
                *   **Complete Timing Kit:** Aisin `TKF-012` [cite: 377]
                *   **Water Pump:** P/N `21111AA240` (Aisin WPF-023) [cite: 377]
                *   **Hydraulic Tensioner:** P/N `13033AA042` [cite: 377]
            
                **Air Conditioning Stretch Belt Kit (Primary):**
                *   **AC Stretch Belt:** P/N `11718AA082` (Replaces 11718AA081) [cite: 377]
                *   *Note:* Sourcing the kit with the specialized plastic installation guide tool is mandatory to prevent rib damage [cite: 377].
                """
            )

    # Fluids Tab
    with tab_fluids:
        st.subheader("🛢 Subaru Recommended Fluids, Grades & Capacities")
        st.write("Maintain exact fluid dynamics and thermal protection parameters for your symmetrical AWD drivetrain.")
        
        fluids_data = [
            {
                "Compartment": "Engine Crankcase (EJ257)",
                "Fluid Type / Specification": "API SM / SN Full Synthetic (SAE 5W-30 or 5W-40)",
                "Capacity": "4.5 Quarts (4.3 Liters) with filter",
                "Key Specs / Notes": "Drain plug torque: 33-34 ft-lb. 5W-40 weight (e.g. Rotella T6, Motul 8100) resists thermal shear under high boost and protects bearings."
            },
            {
                "Compartment": "Manual Transmission & Front Diff",
                "Fluid Type / Specification": "API GL-5 High Performance Gear Oil (SAE 75W-90)",
                "Capacity": "Dry Fill: 4.1 Quarts. Service Fill: ~3.5 Quarts",
                "Key Specs / Notes": "Gearbox and front diff share common oil bath. Standard fluid swaps require ~3.5 quarts because some fluid remains trapped in gear clusters and DCCD electromagnetic mechanism."
            },
            {
                "Compartment": "Rear Differential",
                "Fluid Type / Specification": "API GL-5 Hypoid Gear Oil (SAE 75W-90 / Motul 90PA for track)",
                "Capacity": "1.0 Quart (0.95 Liters)",
                "Key Specs / Notes": "Fill/drain plug torque: 36–43 ft-lb. 90-weight LS fluid (e.g. Motul 90PA) prevents gear chatter under shock loads."
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

    # History Tab
    with tab_history:
        st.subheader("📜 Maintenance & Service Log")
        if mileage is None:
            st.info("💡 **Enter your current odometer mileage** in the Maintenance Status tab to view your completion ledger and chronological history.")
        else:
        
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
        
            # Render clean interactive dataframe
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

    # Manual Tab
    with tab_manual:
        st.subheader("📖 Official Subaru WRX STI Reference Manual")
        
        # Section 1: Specifications
        with st.expander("⚙ Subaru WRX STI Powertrain & Chassis Specifications"):
            st.markdown(
                """
                ### 🏎 2015-2016 Subaru WRX STI Technical Specifications
                *   **Engine Core:** 2.5-Liter (2457 cc) Horizontally Opposed "Boxer" 4-Cylinder EJ257 [cite: 360].
                *   **Cylinder Geometry:** Oversquare bore of 99.5 mm and stroke of 79.0 mm (Bore-to-stroke ratio of 1.26) [cite: 360].
                *   **Power & Compression:** 305 hp (309 PS) @ 6,000 rpm, peak torque 290 lb-ft (393 Nm) @ 4,000 rpm, running an 8.2:1 compression ratio [cite: 360].
                *   **Forced Induction:** Single-scroll turbocharger with functional hood scoop and high-flow top-mount cross-flow intercooler (14.7 PSI peak factory boost) [cite: 360].
                *   **Transmission:** Reinforced TY856 Series 6-speed close-ratio manual [cite: 362, 363]. Fully synchronized reverse [cite: 363].
                *   **Symmetrical AWD Layout:** Multi-Mode Driver Controlled Center Differential (DCCD), Helical Limited-Slip Front Differential, and Torsen Limited-Slip Rear Differential [cite: 362, 363].
                *   **Steering:** Quick-ratio hydraulic power-assisted rack-and-pinion (13.3:1 ratio, 2.5 turns lock-to-lock) [cite: 363].
                *   **Brembo Brakes:** Power-assisted 4-piston fixed front calipers on 12.8-inch (326 mm) ventilated rotors; dual-piston fixed rear calipers on 12.4-inch (316 mm) ventilated rotors [cite: 364].
                *   **Wheel Hub & Bolt Pattern:** Standardized 5x114.3 mm bolt pattern with 56.1 mm center bore [cite: 364].
                """
            )

        # Section 2: Torque specs
        with st.expander("🔧 Critical DIY Torque Specifications (Grounded & Corrected Spec)"):
            st.markdown(
                """
                ### 🛠 Critical Fastener Torque Specifications
                
                ##### 🔴 Front Brembo Caliper Bolt Warning (Corrected Spec)
                *   **Correct Brembo Specification:** **80 ft-lb (114 Nm)** [cite: 373]
                *   **FSM Incorrect Value:** The original Factory Service Manual (FSM) incorrectly lists this torque as **114.3 ft-lb (155 Nm)** [cite: 372]. Attempting to torque the steel M12 bolts to 114.3 ft-lb frequently strips out the aluminum caliper threads or snaps mounting bolts [cite: 372, 384].
                *   **Dissimilar Metal Corrosion Solution:** Steel bolts in aluminum calipers create galvanic corrosion [cite: 384]. It is highly recommended to apply copper anti-seize to the threads and reduce torque to **60 ft-lb** to prevent galling [cite: 162, 385].
                
                | Component Class | Fastener Description | Thread Spec | Torque Value (Imperial) | Torque Value (Metric) |
                | :--- | :--- | :--- | :--- | :--- |
                | **Engine Core** | Spark Plugs (Dry Threads) | M14 | **13 to 17 ft-lbs** | 18 to 23 Nm [cite: 373] |
                | | Oil Pan Drain Plug | M20 | **33 to 34 ft-lbs** | 44 to 46 Nm [cite: 373] |
                | | Valve Cover Fasteners | M6 | **4.7 to 5.8 ft-lbs** | 6.4 to 7.8 Nm (~56-70 in-lbs) [cite: 373] |
                | | Intake Manifold-to-Head | M8 | **17 to 20 ft-lbs** | 23 to 27 Nm [cite: 373] |
                | | Exhaust Manifold-to-Head | M10 | **22 to 29 ft-lbs** | 30 to 39 Nm [cite: 373] |
                | | Crankshaft Pulley Center Bolt | M18 | **35 ft-lbs + 60° turn** | 47 Nm + 60° turn [cite: 373] |
                | | Water Pump Mounting Bolts | M6 | **9 ft-lbs** | 12 Nm [cite: 373] |
                | **Drivetrain** | Gearbox Fill / Drain Plugs | M18 | **37 ft-lbs** (Alum Washer) | 50 Nm [cite: 373] |
                | | Gearbox Drain Plug | M18 | **52 ft-lbs** (Copper Washer)| 70 Nm [cite: 373] |
                | | Rear Diff Fill / Drain Plugs | M20 | **36 to 43 ft-lbs** | 49 to 58 Nm [cite: 373] |
                | | Clutch Pressure Plate | M8 | **12 ft-lbs** | 16 Nm [cite: 373] |
                | | Flywheel Assembly Bolts | M10 | **55 ft-lbs** | 75 Nm [cite: 373] |
                | **Chassis** | Wheel Lug Nuts (Alloy Hub) | M12 x 1.25 | **89 to 94 ft-lbs** | 120 to 127 Nm [cite: 373] |
                | | Front Upper Strut Hat Nuts | M10 | **22 ft-lbs** | 30 Nm [cite: 373] |
                | | Knuckle Lower Strut Bolts | M14 | **129 ft-lbs** | 175 Nm [cite: 373] |
                | | Rear Upper Strut Hat Nuts | M10 | **22 ft-lbs** | 30 Nm [cite: 373] |
                | | Rear Lower Strut Mount Bolt | M14 | **162 ft-lbs** | 220 Nm [cite: 373] |
                | | Rear Main Subframe Bolts | M14 | **106.9 ft-lbs** | 145 Nm [cite: 373] |
                | **Brakes** | Front Brembo Caliper (Corrected) | M12 x 1.5 | **80 ft-lbs** | 114 Nm [cite: 373] |
                | | Rear Brembo Caliper Bolts | M10 x 1.5 | **52.8 ft-lbs** | 71.5 Nm [cite: 373] |
                | | Brake Hose Banjo Bolt | M10 | **19.2 to 22 ft-lbs** | 26 to 30 Nm [cite: 373] |
                | | Caliper Bleeder Screws | M8 / M10 | **14.8 ft-lbs** | 20 Nm [cite: 373] |
                """
            )

        # Section 3: Cylinder Head sequence
        with st.expander("🔩 DOHC EJ257 Cylinder Head Bolt Tightening Sequence"):
            st.markdown(
                """
                ### ⚙ 10-Step Cylinder Head Elastic-Plastic Tightening Procedure
                Always use brand new, clean, and dry OEM **Torque-To-Yield (TTY)** head bolts lightly lubricated with engine oil on the threads and flange faces prior to insertion [cite: 374]. Tighten strictly in the designated cross-pattern sequence (center outward) [cite: 374]:
                
                1.  **Stage 1:** Torque all bolts in sequence to **40 N-m (29.5 ft-lbs)** [cite: 375].
                2.  **Stage 2:** Torque all bolts in sequence to **95 N-m (70 ft-lbs)** [cite: 375].
                3.  **Stage 3:** Loosen all bolts by **180°** in reverse sequence [cite: 375].
                4.  **Stage 4:** Loosen all bolts an additional **180°** to release pre-tension completely [cite: 375].
                5.  **Stage 5:** Torque all bolts in sequence to **10 N-m (7.4 ft-lbs)** [cite: 375].
                6.  **Stage 6:** Torque all bolts in sequence to **30 N-m (22 ft-lbs)** [cite: 375].
                7.  **Stage 7:** Torque all bolts in sequence to **70 N-m (51.6 ft-lbs)** [cite: 375].
                8.  **Stage 8:** Rotate all bolts **80° to 90°** in sequence [cite: 375].
                9.  **Stage 9:** Rotate all bolts an additional **40° to 45°** in sequence [cite: 375].
                10. **Stage 10:** Rotate center bolts (1 and 2 only) a final **40° to 45°** [cite: 375].
                
                ⚠️ **Warning:** Never reuse stretched TTY head bolts, doing so almost guarantees an uneven seal and immediate head gasket failure [cite: 238]!
                """
            )

        # Section 4: Critical Vulnerabilities & Engineering Solutions
        with st.expander("🛠 Diagnostics of Critical Vulnerabilities & Field Engineering Solutions"):
            st.markdown(
                """
                ### ⚙ EJ257 Engineering Vulnerabilities & Proven Fixes
                
                #### 1. Cylinder 4 Overheating, Detonation, and Ringland Failure
                *   **The Cause:** The coolant jacket flow routes sequentially but reaches a stagnation zone around Cylinder 4 (rear left) [cite: 378]. Localized coolant flow drops, causing a thermal spike that lowers Cylinder 4's knock threshold [cite: 378]. Under high load, recurring detonation cracks the brittle cast-aluminum factory piston ringlands, causing compression loss, severe blow-by, and cylinder scoring [cite: 378].
                *   **The Fix:** Retrofit a **Cylinder 4 Chamber Cooling System** [cite: 379]. This integrates a coolant return hose at the rear coolant port of the Cylinder 4 head, routing hot coolant directly into the heater core return line to balance temperature gradients across all heads [cite: 379].
                
                #### 2. Crankcase Blow-by and Intake Octane Degradation
                *   **The Cause:** Horizontally opposed flat layout under boost creates excessive crankcase blow-by [cite: 380]. Suspended oil mist enters the intake through the PCV system, coating the compressor, intercooler, and runners [cite: 380]. This lower-flashpoint oil vapor degrades the fuel's effective octane rating, triggering knocking [cite: 380].
                *   **The Fix:** Install a high-performance, heated dual-chamber **Air-Oil Separator (AOS)** [cite: 381]. An AOS intercepts PCV gases, separates oil, and drains it back to the pan [cite: 381]. Routing engine coolant through the AOS base prevents moisture condensation and sludge buildup [cite: 381].
                
                #### 3. Firewall Pitch Stop Bracket Structural Weld Failure
                *   **The Cause:** Rotational torque reaction forces are stabilized by a pitch stop mount connecting the transmission to the firewall [cite: 382]. In 2015-2016 models, the bracket was stamped from thin sheet-metal and secured with weak spot welds [cite: 382]. Installing a stiff aftermarket mount fatigues and tears the bracket completely off the firewall [cite: 382].
                *   **The Fix:** Install a heavy-duty **pitch stop bracket brace** which anchors to the strut towers and master cylinder mounting points [cite: 383]. If spot welds are already torn, the firewall must be prepped, realigned, and reinforced with TIG welds before brace installation [cite: 383].
                
                #### 4. Starlink Data Communications Module (DCM) Parasitic Battery Drain
                *   **The Cause:** Decommissioned 3G networks cause the 2016 WRX STI's telematics system to enter an infinite boot-loop searching for signal [cite: 386]. Operating on a constant 12V non-switched power source, this causes a **120-140 mA parasitic draw** (exceeding the standard 70 mA limit), draining batteries within 24-48 hours [cite: 386].
                *   **The Fix:** Install a **wireless bypass harness** to route audio around the DCM, or program the DCM into "Factory Mode" using a dealer scan tool per **TSB 15-312-23R** to permanently disable the cellular transceiver [cite: 387].
                
                #### 5. Clutch Pedal Creaking Mechanical Noise
                *   **The Cause:** Creaking sounds during pedal depression are typically pivot wear within the clutch bracket, or a dry clutch fork pivot ball rubbing under friction [cite: 388].
                *   **The Fix:** Remove the intercooler, peel back the slave cylinder rubber boot, and apply high-temperature white lithium grease directly to the release fork and pivot ball socket [cite: 389]. If noise persists, replace with an updated pedal bracket assembly per **TSB 12-190-15 and TSB 03-79-18R** [cite: 389].
                """
            )

        # Section 5: Engine Class Action Settlement & Recalls
        with st.expander("⚖ Regulatory Safety Recalls & The EJ257 Catastrophic Engine Settlement"):
            st.markdown(
                """
                ### 🏛 EJ257 Settlement & Official Safety Recalls
                
                #### 1. The EJ257 Engine Failure Class Action Settlement (2018)
                *   **Target Scope:** 2012–2017 Subaru WRX and WRX STI equipped with the 2.5-liter turbocharged EJ257 engine built between Oct. 11, 2011, and Nov. 16, 2016 [cite: 186, 396].
                *   **Target VIN Ranges:** 5-door hatch models ending in **CG203168 and up**; 4-door sedan models ending in **CG006225 through H9826807** [cite: 186].
                *   **The Issue:** The lawsuit alleged internal defects allowed metallic debris from deteriorating bearings and oil pump failures to contaminate engine oil, restricting flow through crankshaft passages and causing bearing seizure, piston ringland fractures, and catastrophic engine failure [cite: 396].
                *   **Provisions:**
                    *   **Warranty Extension:** Powertrain warranty extended to **8 years or 100,000 miles** [cite: 186, 397].
                    *   **Reimbursement:** 100% reimbursement for out-of-pocket parts/labor expenses for engine failures [cite: 188, 397].
                    *   **CPO Warranty Program:** For secondary buyers, Certified Pre-Owned vehicles must pass a 152-point inspection to receive a 6-year/100,000-mile powertrain warranty with a **$35 USD deductible** [cite: 401].
                
                #### 2. Key Safety Recalls & Technical Service Bulletins
                *   **NHTSA Campaign 19V149000 (Recall WUE-90 - Brake Light Switch):** Silicone contaminants from cleaning products penetrate the brake light switch housing, preventing brake lights from illuminating and disabling push-button start [cite: 399]. Dealers replace with a sealed unit [cite: 399].
                *   **NHTSA Campaign 16V162000 (Recall WTA-62 - Turbo Air Intake Duct):** 2015–2016 WRX and Forester 2.0XT plastic turbo air ducts can crack under thermal cycles and high engine movement, causing unmetered air leaks and lean stalling conditions [cite: 399]. Dealers replace with a reinforced compound duct [cite: 399].
                *   **Recall WUT-05 (zinc-coated coils):** Zinc-coated springs replacement for vehicles in road-salt states to prevent coil spring corrosion and fracture [cite: 400].
                """
            )

# --- CLI BACKFALL RUNTIME ---
elif HAS_RICH:
    # Minimal console interface
    console = Console()
    console.print(Panel(Text("🏎️ Subaru WRX STI Maintenance CLI Interface", style="bold gold1"), subtitle="Local Offline Tracker"))
    # Enter mileage
    try:
        mileage_cli = IntPrompt.ask("Enter Current Odometer Mileage (mi)")
        severe_cli = Confirm.ask("Are you operating in Severe Driving Conditions?")
        
        scheduler_cli = MaintenanceScheduler(mileage_cli, severe_cli)
        items_cli = scheduler_cli.get_schedule()
        
        due_items = [i for i in items_cli if i["due"]]
        
        table = Table(title="🔧 Maintenance Item Check-Ledger")
        table.add_column("Maintenance Item", style="cyan")
        table.add_column("Interval", style="magenta")
        table.add_column("Current Status", style="green")
        
        for item in items_cli:
            status = "[bold red]Overdue / Due Now[/]" if item["due"] else "[bold green]Completed & OK[/]"
            table.add_row(item["name"], f"every {item['interval']:,} mi", status)
        
        console.print(table)
    except KeyboardInterrupt:
        console.print("\nExiting tracker. Happy driving!")

else:
    if __name__ == "__main__":
        print("Subaru STI Maintenance App (Minimal fallback)")
        print("Please install streamlit ('pip install streamlit') or rich ('pip install rich') to run.")

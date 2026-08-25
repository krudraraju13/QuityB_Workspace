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
        
        # Define standard intervals and info
        # Structure: (Name, Base Interval, Severe Interval, Part Number, Quantity, Description)
        maintenance_defs = [
            (
                "Replace Engine Oil & Filter", 
                6000, 
                3000, 
                "15208AA100 (Tokyo Roki JDM Black)", 
                "4.5 Quarts 5W-30/5W-40 + 1 Crush Washer (11126AA000)",
                "Drain plug torque: 33-34 ft-lb. Under severe conditions, replace every 3,000 miles."
            ),
            (
                "Rotate Tires & Check Pressures", 
                6000, 
                6000, 
                "N/A", 
                "N/A",
                "Ensure even tread wear. Tighten lug nuts strictly to 88.5 ft-lb (120 Nm)."
            ),
            (
                "Replace Cabin Air Filter", 
                12000, 
                12000, 
                "72880FG000", 
                "1 Filter",
                "Protects HVAC and passenger air quality from pollen and dust."
            ),
            (
                "Inspect Front & Rear Brake Pads & Rotors", 
                12000, 
                6000, 
                "N/A", 
                "N/A",
                "Check pad thickness. Front Brembos mount torque: 84.3 ft-lb; Rears: 47.2 ft-lb."
            ),
            (
                "Replace Engine Air Filter", 
                30000, 
                15000, 
                "16546AA12A", 
                "1 Filter",
                "Ensure clean induction air flow. Replace more often in dusty/sandy areas."
            ),
            (
                "Replace Brake Fluid", 
                30000, 
                15000, 
                "N/A", 
                "~1.0 Liter (DOT 3 or DOT 4 Premium)",
                "Flush moisture and contaminants from the Brembo caliper hydraulic system."
            ),
            (
                "Replace Manual Transmission Gear Oil", 
                30000, 
                30000, 
                "API GL-5 SAE 75W-90", 
                "Service Fill: ~3.5 Quarts (Dry: 4.1 Quarts)",
                "Gearbox and front diff share oil bath. Plug torque: 32.5 ft-lb (T70 Torx)."
            ),
            (
                "Replace Rear Differential Gear Oil", 
                30000, 
                30000, 
                "API GL-5 SAE 75W-90", 
                "1.0 Quart",
                "Protects hypoid gears. Fill/drain plug torque: 36–43 ft-lb."
            ),
            (
                "Inspect Fuel Lines and Connections", 
                30000, 
                30000, 
                "N/A", 
                "N/A",
                "Verify security and check for any leakage or deterioration."
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
                6000, # Wait, check standard spark plug interval: 60,000 miles
                60000, 
                "22401AA670 (NGK SILFR6A Laser Iridium)", 
                "4 Spark Plugs",
                "Use dry threads. Torque strictly to 13–17 ft-lb to protect aluminum heads."
            ),
            (
                "Replace Timing Belt (EJ257 DOHC)", 
                105000, 
                105000, 
                "13028AA250 (Aisin Kit TKF-012)", 
                "1 Timing Belt Kit",
                "Critical interference engine component. Replace timing belt, tensioner, water pump."
            ),
            (
                "Replace Engine Coolant (Super Coolant)", 
                137500, 
                137500, 
                "Super Coolant (Pre-Mixed Blue)", 
                "8.1 Quarts + 1 bottle Conditioner (SOA635065)",
                "First change at 137,500 mi / 11 years; subsequent changes every 75,000 mi / 6 years."
            )
        ]
        
        # Override spark plug interval if defined wrong
        for idx, item_def in enumerate(maintenance_defs):
            if item_def[0] == "Replace Spark Plugs":
                maintenance_defs[idx] = (
                    "Replace Spark Plugs", 
                    60000, 
                    60000, 
                    "22401AA670 (NGK SILFR6A Laser Iridium)", 
                    "4 Spark Plugs",
                    "Use dry threads. Torque strictly to 13–17 ft-lb to protect aluminum heads."
                )

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
                "Spark Plug Installation (DOHC Boxer)",
                "Timing Belt (EJ257) Overview"
            ]
        )
        
        if proc_selection == "Engine Oil & Filter Swap":
            st.markdown(
                """
                ### 🛢️ Engine Oil & Filter Swap Procedure
                **Target Thread Torque:** Drain plug: `33-34 ft-lb` (Ensure a new OEM metal crush washer P/N `11126AA000` is used) [cite: 22].
                
                **Step-by-Step Instructions:**
                1. Ensure engine is warm. Park on flat ground and jack up front of car (use heavy duty jack stands and tire chocks).
                2. Position oil catch pan under the drain plug (14mm). Carefully remove plug and drain oil completely.
                3. Clean the drain plug threads, fit the new **Subaru Crush Washer** with its flat face against the oil pan, and hand thread. Torque to **33-34 ft-lb**.
                4. Use a filter wrench to remove the engine oil filter. Clean the contact surface on the engine block.
                5. Apply a light film of fresh engine oil to the rubber O-ring of the **Tokyo Roki Black Filter (15208AA100)** [cite: 22]. Hand tighten the filter until seal contacts, then turn it exactly 3/4 to 1 full turn further.
                6. Add **4.5 quarts** of synthetic oil (5W-30 or 5W-40) [cite: 22]. Wait 5 minutes, check dipstick, start car, and check for leaks.
                """
            )
        elif proc_selection == "Manual Transmission Gear Oil Replacement":
            st.markdown(
                """
                ### ⚙️ Manual Transmission Gear Oil Swap
                **Target Thread Torque:** T70 Torx drain plug: `32.5 ft-lb`. Fill plug: `23.5 ft-lb`.
                
                **Step-by-Step Instructions:**
                1. Elevate car flat on all four jack stands.
                2. Locate the transmission case. Remove the intercooler if filling from top, or use a fluid transfer pump from underneath.
                3. Remove the fill plug (10mm) first to ensure you can fill, then remove the lower T70 Torx drain plug.
                4. Clean the magnetic drain plug thoroughly of wear debris. Install with a new seal and torque to **32.5 ft-lb**.
                5. Fill with **~3.5 quarts** of SAE 75W-90 GL-5 gear oil (e.g. Motul Gear 300) [cite: 7, 22].
                6. Reinstall fill plug and torque to specifications.
                """
            )
        elif proc_selection == "Rear Differential Oil Swap":
            st.markdown(
                """
                ### 🔩 Rear Differential Oil Swap
                **Target Thread Torque:** Fill and drain plugs: `36.2 ft-lb`.
                
                **Step-by-Step Instructions:**
                1. Elevate the rear end. Locate the rear diff case.
                2. Remove the top fill plug (1/2\" drive or 13mm socket) to verify you can fill, then remove the lower drain plug.
                3. Allow 1.0 quart to drain completely. Clean the magnet on the drain plug.
                4. Apply thread sealant (like liquid Teflon) to the plug threads. Reinstall drain plug and torque to **36.2 ft-lb**.
                5. Use a pump to inject exactly **1.0 quart** of SAE 75W-90 GL-5 hypoid gear oil into the fill hole until it begins to seep out.
                6. Reinstall fill plug with thread sealant and torque to **36.2 ft-lb**.
                """
            )
        elif proc_selection == "Spark Plug Installation (DOHC Boxer)":
            st.markdown(
                """
                ### ⚡ Spark Plug Replacement
                **Target Thread Torque:** NGK Spark Plugs: `13–17 ft-lb` (Dry threads!) [cite: 22].
                
                **Step-by-Step Instructions:**
                1. Disconnect battery. Remove air intake box (right side) and battery/washer fluid reservoir bracket components (left side) to access coil packs.
                2. Remove the 10mm bolts holding the ignition coils, and pull out the coil packs.
                3. Use a 5/8\" spark plug socket, a 3\" extension, and a swivel ratchet to carefully break loose and retrieve the old plugs.
                4. Ensure the new spark plugs (**NGK Laser Iridium SILFR6A**) are gapped correctly [cite: 22]. Hand thread them into the cylinder head to prevent cross-threading.
                5. Torque strictly dry to **13-17 ft-lb**. *Do not use anti-seize*, as it acts as a lubricant and will lead to over-torquing and cylinder head strip out.
                """
            )
        elif proc_selection == "Timing Belt (EJ257) Overview":
            st.markdown(
                """
                ### ⚙️ Timing Belt DOHC EJ257 Overview
                The EJ257 utilizes a DOHC layout with four camshafts. A snapped or jumped timing belt will cause instant, catastrophic valve-to-piston contact.
                
                **Key Advice:**
                *   Interval is **105,000 miles** [cite: 22].
                *   Always replace the complete assembly (Timing belt `13028AA250`, water pump, hydraulic tensioner, and all idler pulleys) [cite: 22].
                *   Use high quality kits such as **Aisin TKF-012** to prevent premature idler bearing lockups [cite: 22].
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
                *   **Tokyo Roki JDM Black Filter:** P/N `15208AA100` [cite: 22]
                *   **Crush Washer:** P/N `11126AA000` [cite: 22]
                *   *Note:* The black Tokyo Roki filter features an all-metal bypass valve calibrated to open at 23 PSI, matching high Subaru oil pump relief pressures [cite: 22].
            
                **Spark Plugs (Laser Iridium - Primary):**
                *   **SILFR6A (NGK 7913):** P/N `22401AA670` [cite: 22]
                *   *Note:* Use dry threads (no anti-seize) and torque strictly to 13–17 ft-lb to prevent stripping aluminum heads [cite: 22].
                """
            )
            st.markdown(
                """
                **Timing Belt & Accessories (DOHC EJ257 - Primary):**
                *   **Timing Belt:** P/N `13028AA250` [cite: 22]
                *   **Complete Timing Kit:** Aisin `TKF-012` [cite: 22]
                *   **Water Pump:** P/N `21111AA240` (Aisin WPF-023) [cite: 22]
                *   **Hydraulic Tensioner:** P/N `13033AA042` [cite: 22]
            
                **Air Conditioning Stretch Belt Kit (Primary):**
                *   **AC Stretch Belt:** P/N `11718AA082` (Replaces 11718AA081) [cite: 22]
                *   *Note:* Sourcing the kit with the specialized plastic installation guide tool is mandatory to prevent rib damage [cite: 22].
                """
            )

    # Fluids Tab
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
        
        st.markdown(
            """
            ### 🔧 Critical DIY Torque Specifications (Grounded in Subimods DIY Guide)
            *Grounded in factory and performance specialist specifications to prevent stripping aluminum threads or catastrophic failures:*
            
            ##### ⚙️ Engine Core Torque Specs
            | Component | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Engine Oil Drain Plug** | 33–34 ft-lb | Replace copper crush washer to prevent oil pan thread strip-out [cite: 22]. |
            | **Spark Plugs** | 13–17 ft-lb | **Always Dry threads (no anti-seize).** Over-torquing cracks heads [cite: 22]. |
            | **Oil Pan Bolts** | 3.7 ft-lb | Avoid over-torquing, oil pan flanges warp extremely easily. |
            
            ##### ⚙️ Drivetrain Gearbox & Differential Torque Specs
            | Component | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Manual Transmission Drain Plug (T70 Torx)** | 32.5 ft-lb | Replace metal gasket. Clean magnetic tip [cite: 22]. |
            | **Manual Transmission Fill Plug** | 23.5 ft-lb | Hand-thread first to avoid cross-threading [cite: 22]. |
            | **Rear Differential Drain/Fill Plugs** | 36.2 ft-lb | Use liquid thread sealant (Teflon) to prevent fluid weeping. |
            
            ##### ⚙️ Suspension & Brake Torque Specs
            | Component | Torque Spec | Notes / Operational Risks |
            | :--- | :--- | :--- |
            | **Front Brembo Caliper Mounting Bolts** | 84.3 ft-lb (114.3 Nm) | Highly critical. Loose bolts cause caliper play and severe pad slide [cite: 10]. |
            | **Rear Brembo Caliper Mounting Bolts** | 47.2 ft-lb (64 Nm) | Steel bolt going into aluminum caliper threads; torque strictly [cite: 10]. |
            | **Wheel Lug Nuts (Symmetrical AWD)** | 88.5 ft-lb (120 Nm) | Torque in a star pattern. Unbalanced torque warps brake rotors [cite: 2]. |
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

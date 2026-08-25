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
            st.markdown("### 🔧 Symmetrical AWD Maintenance Checklist")
            st.write("Check the items you have completed at your current mileage, then click **💾 Save Checked Services** at the bottom to log them.")

            # Categorize items by criticality
            high_crit_items = []
            med_crit_items = []
            low_crit_items = []

            high_names = {
                "Replace Engine Oil & Filter",
                "Replace Timing Belt (EJ257 DOHC)",
                "Replace Spark Plugs",
                "Inspect Front & Rear Brake Pads & Rotors",
                "Replace Brake Fluid"
            }
            low_names = {
                "Replace Cabin Air Filter"
            }

            for item in schedule_items:
                if item["name"] in high_names:
                    high_crit_items.append(item)
                elif item["name"] in low_names:
                    low_crit_items.append(item)
                else:
                    med_crit_items.append(item)

            categories = [
                ("🔴 High", high_crit_items),
                ("🟡 Medium", med_crit_items),
                ("🟢 Low", low_crit_items)
            ]

            completed_list = []

            for cat_title, cat_items in categories:
                if cat_items:
                    st.markdown(f"#### {cat_title}")
                    for item in cat_items:
                        last_str = f" (Last: {item['last_completed']:,} mi)" if item['last_completed'] is not None else ""
                        label = f"**{item['name']}**{last_str} — every {item['interval']:,} mi"
                        
                        checked = st.checkbox(label, key=f"check_{item['name']}")
                        if checked:
                            completed_list.append(item["name"])
                    
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin:15px 0; border-color:#eee;'/>", unsafe_allow_html=True)
            
            # Action button
            if completed_list:
                if st.button("💾 Save Checked Services", type="primary", use_container_width=True):
                    confirm_save_dialog(completed_list, mileage, severe)
            else:
                st.button("💾 Save Checked Services", type="primary", disabled=True, use_container_width=True, help="Check one or more items above to enable logging.")

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
                **Target Thread Torque:** Drain plug: `33-34 ft-lb` (Ensure a new OEM metal crush washer P/N `11126AA000` is used).
                
                **Step-by-Step Instructions:**
                1. Ensure engine is warm. Park on flat ground and jack up front of car (use heavy duty jack stands and tire chocks).
                2. Position oil catch pan under the drain plug (14mm). Carefully remove plug and drain oil completely.
                3. Clean the drain plug threads, fit the new **Subaru Crush Washer** with its flat face against the oil pan, and hand thread. Torque to **33-34 ft-lb**.
                4. Use a filter wrench to remove the engine oil filter. Clean the contact surface on the engine block.
                5. Apply a light film of fresh engine oil to the rubber O-ring of the **Tokyo Roki Black Filter (15208AA100)**. Hand tighten the filter until seal contacts, then turn it exactly 3/4 to 1 full turn further.
                6. Add **4.5 quarts** of synthetic oil (5W-30 or 5W-40). Wait 5 minutes, check dipstick, start car, and check for leaks.
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
                5. Fill with **~3.5 quarts** of SAE 75W-90 GL-5 gear oil (e.g. Motul Gear 300).
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
                **Target Thread Torque:** NGK Spark Plugs: `13–17 ft-lb` (Dry threads!).
                
                **Step-by-Step Instructions:**
                1. Disconnect battery. Remove air intake box (right side) and battery/washer fluid reservoir bracket components (left side) to access coil packs.
                2. Remove the 10mm bolts holding the ignition coils, and pull out the coil packs.
                3. Use a 5/8\" spark plug socket, a 3\" extension, and a swivel ratchet to carefully break loose and retrieve the old plugs.
                4. Ensure the new spark plugs (**NGK Laser Iridium SILFR6A**) are gapped correctly. Hand thread them into the cylinder head to prevent cross-threading.
                5. Torque strictly dry to **13-17 ft-lb**. *Do not use anti-seize*, as it acts as a lubricant and will lead to over-torquing and cylinder head strip out.
                """
            )
        elif proc_selection == "Timing Belt (EJ257) Overview":
            st.markdown(
                """
                ### ⚙️ Timing Belt DOHC EJ257 Overview
                The EJ257 utilizes a DOHC layout with four camshafts. A snapped or jumped timing belt will cause instant, catastrophic valve-to-piston contact.
                
                **Key Advice:**
                *   Interval is **105,000 miles**.
                *   Always replace the complete assembly (Timing belt `13028AA250`, water pump, hydraulic tensioner, and all idler pulleys).
                *   Use high quality kits such as **Aisin TKF-012** to prevent premature idler bearing lockups.
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
            
            # Insert parts catalog

            # Expanded Genuine OEM Parts Database with Category, Name, P/N, Qty, and Price (USD)
            parts_catalog = [
                # Engine and Cooling
                {"Category": "Engine and Cooling", "Part Name": "Tokyo Roki JDM Black Engine Oil Filter", "OEM Part Number": "15208AA100", "Quantity": 1, "Price": 12.00, "Notes": "Calibrated 23 PSI metal bypass valve matches high Subaru oil pump relief pressure."},
                {"Category": "Engine and Cooling", "Part Name": "Oil Pan Drain Crush Washer", "OEM Part Number": "11126AA000", "Quantity": 1, "Price": 1.50, "Notes": "Direct fit copper crush ring. Prevents oil pan thread stripout."},
                {"Category": "Engine and Cooling", "Part Name": "Mitsuboshi Timing Belt (Individual)", "OEM Part Number": "13028AA250", "Quantity": 1, "Price": 85.00, "Notes": "High-tensile reinforced timing belt for DOHC EJ257 engines."},
                {"Category": "Engine and Cooling", "Part Name": "Complete Timing Belt Kit (Aisin)", "OEM Part Number": "TKF-012", "Quantity": 1, "Price": 280.00, "Notes": "Aisin timing kit with water pump, tensioners, and NSK/Koyo pulleys."},
                {"Category": "Engine and Cooling", "Part Name": "Water Pump Assembly (Aisin)", "OEM Part Number": "21111AA240", "Quantity": 1, "Price": 120.00, "Notes": "Aisin WPF-023 water pump with premium gasket."},
                {"Category": "Engine and Cooling", "Part Name": "Hydraulic Belt Tensioner", "OEM Part Number": "13033AA042", "Quantity": 1, "Price": 95.00, "Notes": "GMB / OEM-supplier hydraulic timing belt tensioner."},
                {"Category": "Engine and Cooling", "Part Name": "Thermostat Gasket", "OEM Part Number": "21236AA050", "Quantity": 1, "Price": 5.50, "Notes": "Molded rubber thermostat housing seal ring."},
                {"Category": "Engine and Cooling", "Part Name": "Engine Air Filter Element", "OEM Part Number": "16546AA12A", "Quantity": 1, "Price": 22.00, "Notes": "Pleated dry fiber element for optimal engine intake filtration."},
                {"Category": "Engine and Cooling", "Part Name": "Exhaust Gasket (Manifold to Head)", "OEM Part Number": "44011AC030", "Quantity": 2, "Price": 14.50, "Notes": "Multi-layer steel gasket between block and exhaust manifold."},
                {"Category": "Engine and Cooling", "Part Name": "Center Pipe Gasket (Donut)", "OEM Part Number": "44616AA200", "Quantity": 1, "Price": 18.00, "Notes": "Exhaust center pipe sealing gasket."},
                {"Category": "Engine and Cooling", "Part Name": "Intake Manifold Gasket", "OEM Part Number": "14035AA580", "Quantity": 2, "Price": 12.50, "Notes": "High-temperature gasket between intake runners and head."},
                {"Category": "Engine and Cooling", "Part Name": "EGR Pipe Gasket", "OEM Part Number": "14852AA040", "Quantity": 1, "Price": 6.00, "Notes": "Metal gasket for exhaust gas recirculation pipe."},
                {"Category": "Engine and Cooling", "Part Name": "Water Pipe O-Ring", "OEM Part Number": "14738AA150", "Quantity": 1, "Price": 3.50, "Notes": "Engine cooling bypass pipe sealing ring."},
                {"Category": "Engine and Cooling", "Part Name": "Chain Cover O-Ring", "OEM Part Number": "806912190", "Quantity": 3, "Price": 2.50, "Notes": "Sealing O-ring for front timing chain/belt cover."},
                {"Category": "Engine and Cooling", "Part Name": "Chain Cover O-Ring (Small)", "OEM Part Number": "806924120", "Quantity": 1, "Price": 1.80, "Notes": "Smaller timing cover fluid passage seal."},
                {"Category": "Engine and Cooling", "Part Name": "Tensioner O-Ring", "OEM Part Number": "806916080", "Quantity": 1, "Price": 2.20, "Notes": "Fluid block off O-ring for hydraulic timing tensioner."},
                {"Category": "Engine and Cooling", "Part Name": "Spark Plug Tube Seal", "OEM Part Number": "10966AA040", "Quantity": 4, "Price": 7.50, "Notes": "Rubber gasket sealing spark plug wells inside valve cover."},
                {"Category": "Engine and Cooling", "Part Name": "Rocker Cover Gasket (RH)", "OEM Part Number": "13270AA27A", "Quantity": 1, "Price": 24.00, "Notes": "Premium rubber valve cover gasket (passenger side)."},
                {"Category": "Engine and Cooling", "Part Name": "Rocker Cover Gasket (LH)", "OEM Part Number": "13272AA21A", "Quantity": 1, "Price": 24.00, "Notes": "Premium rubber valve cover gasket (driver side)."},
                {"Category": "Engine and Cooling", "Part Name": "Cam Carrier O-Ring", "OEM Part Number": "806915170", "Quantity": 4, "Price": 3.20, "Notes": "Sealing ring for EJ257 camshaft carrier housing."},
                {"Category": "Engine and Cooling", "Part Name": "Cylinder Head Gasket (RH)", "OEM Part Number": "11044AA790", "Quantity": 1, "Price": 55.00, "Notes": "Multi-layer steel (MLS) head gasket for extreme combustion pressures."},
                {"Category": "Engine and Cooling", "Part Name": "Cylinder Head Gasket (LH)", "OEM Part Number": "10944AA080", "Quantity": 1, "Price": 55.00, "Notes": "Multi-layer steel (MLS) head gasket (driver side)."},
                {"Category": "Engine and Cooling", "Part Name": "Connecting Rod Bolt", "OEM Part Number": "12109AA120", "Quantity": 8, "Price": 8.50, "Notes": "High-tensile Torque-to-Yield (TTY) connecting rod bolt (must replace once used)."},
                {"Category": "Engine and Cooling", "Part Name": "Upper Oil Pan O-Ring", "OEM Part Number": "806932030", "Quantity": 3, "Price": 4.50, "Notes": "Crankcase-to-oil-pan fluid passage sealing ring."},
                {"Category": "Engine and Cooling", "Part Name": "Crankshaft Extension O-Ring", "OEM Part Number": "806939060", "Quantity": 1, "Price": 3.00, "Notes": "Timing gear snout spacer seal."},
                {"Category": "Engine and Cooling", "Part Name": "Front Crankshaft Oil Seal", "OEM Part Number": "806750080", "Quantity": 1, "Price": 9.50, "Notes": "Vital oil seal located behind the crankshaft timing sprocket."},
                {"Category": "Engine and Cooling", "Part Name": "Fuel Injector O-Ring (Upper)", "OEM Part Number": "16608KA000", "Quantity": 4, "Price": 4.50, "Notes": "Seal between top fuel rail and fuel injector."},
                {"Category": "Engine and Cooling", "Part Name": "Fuel Injector O-Ring (Lower)", "OEM Part Number": "16698AA110", "Quantity": 4, "Price": 5.00, "Notes": "Seal between injector nozzle and intake manifold."},
                {"Category": "Engine and Cooling", "Part Name": "Oil Filter Assembly (Domestic Blue)", "OEM Part Number": "15208AA15A", "Quantity": 1, "Price": 8.50, "Notes": "Alternative standard blue paper-endcap filter element."},
                {"Category": "Engine and Cooling", "Part Name": "Oil Drain Plug Gasket (Copper Flat)", "OEM Part Number": "803916010", "Quantity": 1, "Price": 1.50, "Notes": "Alternative flat metal drain plug washer."},
                {"Category": "Engine and Cooling", "Part Name": "Turbo Oil Return Line Hose", "OEM Part Number": "K04535-TurboHose", "Quantity": 1, "Price": 21.00, "Notes": "Heat-resistant hose routing oil from turbo back to cylinder head block."},
                {"Category": "Engine and Cooling", "Part Name": "Intercooler Stay Grommet", "OEM Part Number": "K04535-Grommet", "Quantity": 1, "Price": 10.00, "Notes": "Rubber isolation stay grommet for top-mount intercooler."},
                {"Category": "Engine and Cooling", "Part Name": "Upper Evap/Vacuum Line", "OEM Part Number": "GD-EvapLine", "Quantity": 1, "Price": 9.22, "Notes": "Evaporative purge vacuum line assembly."},

                # Maintenance
                {"Category": "Maintenance", "Part Name": "Spark Plug Set (NGK Laser Iridium)", "OEM Part Number": "22401AA670", "Quantity": 4, "Price": 60.00, "Notes": "NGK SILFR6A (7913) gapped to 0.030\". Replace every 30,000 to 60,000 miles."},
                {"Category": "Maintenance", "Part Name": "Engine Cabin Air Filter", "OEM Part Number": "72880FG000", "Quantity": 1, "Price": 25.00, "Notes": "Multi-layer HEPA Active Carbon filter. Replace every 12 to 24 months."},
                {"Category": "Maintenance", "Part Name": "Subaru OEM Touch-Up Paint", "OEM Part Number": "SOA326-Paint", "Quantity": 1, "Price": 31.00, "Notes": "Color-matched touch-up brush for chip repair."},

                # Suspension and Brakes
                {"Category": "Suspension and Brakes", "Part Name": "Front Brembo Brake Rotor (Each)", "OEM Part Number": "26300FE070", "Quantity": 2, "Price": 150.00, "Notes": "High-carbon vented cast iron 326mm brake rotor."},
                {"Category": "Suspension and Brakes", "Part Name": "Rear Brembo Brake Pad Set", "OEM Part Number": "26696FG000", "Quantity": 1, "Price": 95.00, "Notes": "High-performance pads. Includes multi-layer backing shims."},
                {"Category": "Suspension and Brakes", "Part Name": "Front Brembo Caliper Bolt (Each)", "OEM Part Number": "901120103", "Quantity": 4, "Price": 6.00, "Notes": "High-strength Grade 10.9 steel caliper-to-knuckle bolt."},
                {"Category": "Suspension and Brakes", "Part Name": "Rear Brembo Caliper Mounting Bolt", "OEM Part Number": "901120102", "Quantity": 4, "Price": 5.00, "Notes": "High-strength steel caliper mounting bolt."},
                {"Category": "Suspension and Brakes", "Part Name": "Caliper Bleeder Screws", "OEM Part Number": "M8/M10-Bleeder", "Quantity": 1, "Price": 12.00, "Notes": "Caliper hydraulic air bleed valves (Set of 4)."},
                {"Category": "Suspension and Brakes", "Part Name": "Brake Hose Banjo Bolt", "OEM Part Number": "M10-Banjo", "Quantity": 1, "Price": 8.00, "Notes": "Fluid delivery banjo bolt with fresh copper washers."},
                {"Category": "Suspension and Brakes", "Part Name": "Brembo Caliper Bolt Set", "OEM Part Number": "SOA-BremboBolt", "Quantity": 1, "Price": 6.00, "Notes": "Replacement bolt for brake bracket."},

                # Manual Transmission
                {"Category": "Manual Transmission", "Part Name": "6-Speed MT Drain Plug (T70 Torx)", "OEM Part Number": "32103AA080", "Quantity": 1, "Price": 10.00, "Notes": "Magnetic drain plug for TY856 transmission case."},
                {"Category": "Manual Transmission", "Part Name": "6-Speed MT Drain Plug Crush Washer", "OEM Part Number": "32103AA012", "Quantity": 1, "Price": 4.50, "Notes": "Sealing gasket for manual transmission drain plug."},
                {"Category": "Manual Transmission", "Part Name": "6-Speed MT Drain Plug (Early Spec)", "OEM Part Number": "32103AA070", "Quantity": 1, "Price": 15.00, "Notes": "Early model year 6-speed magnetic plug."},
                {"Category": "Manual Transmission", "Part Name": "6-Speed MT Drain Plug Gasket (Copper)", "OEM Part Number": "32103AA011", "Quantity": 1, "Price": 9.00, "Notes": "Copper sealing washer for manual transmission drain plug."},
                {"Category": "Manual Transmission", "Part Name": "Mach V Braided Clutch Line", "OEM Part Number": "MachV-ClutchLine", "Quantity": 1, "Price": 29.00, "Notes": "Stainless steel braided high-pressure clutch hydraulic line."},
                {"Category": "Manual Transmission", "Part Name": "OEM Quality Clutch Slave Cylinder", "OEM Part Number": "Slave-Cylinder", "Quantity": 1, "Price": 49.00, "Notes": "Hydraulic clutch actuator cylinder assembly."},
                {"Category": "Manual Transmission", "Part Name": "Subaru Bell Housing Bolts/Studs", "OEM Part Number": "Bellhousing-Bolt", "Quantity": 1, "Price": 4.43, "Notes": "High-tensile bellhousing to manual transmission mounting stud."},

                # Driveline and Differential
                {"Category": "Driveline and Differential", "Part Name": "Motul STI 6-Speed Transmission Fluid Kit", "OEM Part Number": "Motul-6MT-Kit", "Quantity": 1, "Price": 165.00, "Notes": "Full fluid kit with gearbox and rear differential lubricants."},
                {"Category": "Driveline and Differential", "Part Name": "Hubcentric Rings (Set of 4)", "OEM Part Number": "Hub-Rings", "Quantity": 1, "Price": 11.00, "Notes": "Custom polymer alignment rings for aftermarket wheels."},

                # Heating and Air Conditioning
                {"Category": "Heating and Air Conditioning", "Part Name": "AC Drive Stretch Belt Kit", "OEM Part Number": "11718AA082", "Quantity": 1, "Price": 45.00, "Notes": "Replaces 11718AA081. Specialty EPDM belt (includes plastic guide installer tool)."},

                # Steering
                {"Category": "Steering", "Part Name": "Alternator / Power Steering Belt", "OEM Part Number": "809218460", "Quantity": 1, "Price": 28.00, "Notes": "V-Ribbed EPDM accessory drive belt."},

                # Electrical
                {"Category": "Electrical", "Part Name": "Hanshin OEM Ignition Coil Pack", "OEM Part Number": "22433AA641", "Quantity": 4, "Price": 110.00, "Notes": "Hanshin OEM Service Component. Prevents misfires under boost."},

                # Body
                {"Category": "Body", "Part Name": "Transmission Crossmember Bolt Kit", "OEM Part Number": "Crossmember-Bolts", "Quantity": 1, "Price": 18.00, "Notes": "High-tensile fasteners for subframe crossmember mounting."},
                {"Category": "Body", "Part Name": "Bumper Vents Set", "OEM Part Number": "Bumper-Vents", "Quantity": 1, "Price": 43.63, "Notes": "Bumper outer vents trim kit."},
                {"Category": "Body", "Part Name": "Front Bumper Side Support", "OEM Part Number": "Bumper-Support", "Quantity": 1, "Price": 12.82, "Notes": "Bumper fascia side attachment guide bracket."},

                # Door
                {"Category": "Door", "Part Name": "Door Hinge Lubricant", "OEM Part Number": "White Lithium Grease", "Quantity": 1, "Price": 8.00, "Notes": "Applied to door hinge assemblies and latching pins."}
            ]

            import pandas as pd
            df_catalog = pd.DataFrame(parts_catalog)
            
            # Interactive search & filter controls
            col_search, col_cat = st.columns([2, 1])
            with col_search:
                search_query = st.text_input("🔍 Search parts by name or part number:", "").strip().lower()
            with col_cat:
                category_list = ["All Categories"] + sorted(list(set(df_catalog["Category"].tolist())))
                selected_category = st.selectbox("📂 Filter by category:", category_list)
            
            # Filter the dataframe
            filtered_df = df_catalog.copy()
            if selected_category != "All Categories":
                filtered_df = filtered_df[filtered_df["Category"] == selected_category]
            
            if search_query:
                filtered_df = filtered_df[
                    filtered_df["Part Name"].str.lower().str.contains(search_query) | 
                    filtered_df["OEM Part Number"].str.lower().str.contains(search_query)
                ]
            
            # Render filterable catalog
            st.markdown("#### 📂 Filtered OEM Parts Reference Catalog")
            
            # Format Prices for display in table
            display_df = filtered_df.copy()
            display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
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
        
        # Section 1: Specifications
        with st.expander("⚙️ Subaru WRX STI Powertrain & Chassis Specifications"):
            st.markdown(
                """
                ### 🏎️ Official 2016 Subaru WRX STI (GUS Model) Specifications
                *Based strictly on official 2016 US market specifications.*

                ##### 📦 Engine & Powertrain
                | Specification | Value / Detail |
                | :--- | :--- |
                | **Engine Manufacturer / Type** | Subaru flat-four horizontally opposed DOHC "Boxer" 4-cylinder, 16 valves (4 valves/cyl). |
                | **Displacement / Size** | 2.5 Liter (2,457 cc / 149.935 cu in). |
                | **Bore × Stroke** | 99.5 mm × 79.0 mm (3.92 in × 3.11 in) with 1.26 oversquare ratio. |
                | **Compression Ratio** | 8.2:1. |
                | **Fuel System / Induction** | Multi-point fuel injection (MPFI). Single-scroll turbocharger with functional hood scoop & aluminum cross-flow intercooler (14.7 PSI factory peak boost). |
                | **Engine Construction** | Cast aluminum-alloy block and cylinder heads. |
                | **Lubrication System** | Wet sumped. |
                | **Maximum Power Output** | **305 bhp (309 PS / 227 kW) @ 6,000 RPM**. |
                | **Maximum Torque Output** | **290 lb-ft (393 N·m / 40.1 kgm) @ 4,000 RPM**. |
                | **Specific Power Output** | 124.1 bhp/litre (125.9 PS/litre / 92.6 kW/litre). |
                | **Specific Torque Output** | 159.95 N·m/litre. |

                ##### ⚙️ Drivetrain & Transmission
                | Component | Design Specification & Mechanical Parameters |
                | :--- | :--- |
                | **Gearbox Designation** | TY856 Series 6-speed manual, reinforced casing. Fully synchronized reverse. |
                | **Gear Ratios** | Top gear ratio: 0.76:1. Final drive ratio: 3.90:1. |
                | **Engine Position / Layout** | Front-positioned, longitudinal. |
                | **Symmetrical AWD Layout** | Symmetrical All-Wheel Drive. Multi-Mode Driver Controlled Center Differential (DCCD) coordinating an electromagnetic multi-plate clutch and mechanical LSD. |
                | **Front Differential** | Helical limited-slip differential (LSD). |
                | **Rear Differential** | Torsen limited-slip differential (LSD). |

                ##### 📐 Dimensions & Weights
                | Dimension / Parameter | Metric Value | Imperial / US Value |
                | :--- | :--- | :--- |
                | **Wheelbase** | 2649 mm. | 104.3 inches. |
                | **Track / Tread (Front)** | 1529 mm. | 60.2 inches. |
                | **Track / Tread (Rear)** | 1539 mm. | 60.6 inches. |
                | **Overall Length** | 4595 mm. | 180.9 inches. |
                | **Overall Width** | 1796 mm. | 70.7 inches. |
                | **Overall Height** | 1476 mm. | 58.1 inches. |
                | **Ground Clearance** | Performance stance with 1.73 length-to-wheelbase ratio. | |
                | **Kerb Weight** | **1536 kg**. | **3386 lbs**. |
                | **Power-to-weight ratio** | 198.57 bhp/tonne (0.2 bhp/kg). | |
                | **Weight-to-power ratio** | 11.28 lb/bhp (6.75 kg/kW). | |

                ##### 🧪 Fluids, Capacities & Economy
                | Parameter | Metric Value | Imperial / US Value |
                | :--- | :--- | :--- |
                | **Fuel Tank Capacity** | 60.2 litres. | 15.9 US Gallons (13.2 UK Gal). |
                | **EPA Fuel Consumption** | 13.8 / 10.2 / 12.4 L/100km. | **17 / 23 / 19 MPG** (City/Highway/Combined). |
                | **Engine Oil Capacity** | 4.3 Liters. | 4.5 Quarts with filter. |
                | **Engine Coolant Capacity** | 7.7 Liters. | 8.1 Quarts. |

                ##### 🏎️ Chassis, Steering, Wheels & Brakes
                | Component | Design Specification & Mechanical Parameters |
                | :--- | :--- |
                | **Steering System** | Hydraulic power-assisted rack & pinion steering with 13.3:1 quick-ratio. |
                | **Turns Lock-to-Lock** | **2.500 turns**. |
                | **Front Suspension** | Independent inverted MacPherson KYB struts with forged aluminum alloy lower suspension arm, high-durometer pillow ball mounts and bushings, 24 mm stabilizer bar. |
                | **Rear Suspension** | Independent double-wishbone design with subframe stiffener bar and 20 mm stabilizer bar. |
                | **Wheel Hub Bolt Pattern** | Standardized **5x114.3 mm** bolt pattern with **56.1 mm** center bore. |
                | **Wheel Rim Size** | 8.5J × 18 inches front and rear. |
                | **Tire Sizing** | **245/40 R18 97W** front and rear high-performance tires. |
                | **Brembo Brake Calipers** | Power-assisted Brembo brake system with 4-piston fixed front calipers and dual-piston fixed rear calipers. |
                | **Brake Rotors** | Front ventilated discs: **325 mm / 326 mm** diameter, **30 mm** thick. Rear ventilated discs: **315 mm / 316 mm** diameter, **20 mm** thick. |
                | **Braking Safety Systems** | Super Sport ABS (4-channel/4-sensor/4-wheel with g-load sensor), Active Torque Vectoring, Brake Assist, and Electronic Brake-force Distribution (EBD). |
                """
            )

        # Section 2: Torque specs
        with st.expander("🔧 Critical DIY Torque Specifications (Factory & Corrected Specs)"):
            st.markdown(
                """
                | Component Class | Fastener Description | Thread Spec | Torque Value (Imperial) | Torque Value (Metric) | Notes / Application |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                | **Engine Core** | Spark Plugs (Dry Threads) | M14 | **13 to 17 ft-lbs** | 18 to 23 N-m | Factory Standard / Subimods |
                | | Spark Plugs (Pro Street Spec) | M14 | **15.5 ft-lbs** | 21 N-m | My Pro Street Ignition |
                | | Ignition Coil Pack Bolt | M6 | **11.8 ft-lbs** | 16 N-m | My Pro Street Ignition |
                | | Air Pump Duct Bolt | M6 | **6.6 ft-lbs** | 9 N-m | My Pro Street Ignition |
                | | Oil Pan Drain Plug | M20 | **33 to 34 ft-lbs** | 44 to 46 N-m | Factory Standard / Subimods |
                | | Valve Cover Fasteners | M6 | **4.7 to 5.8 ft-lbs** | 6.4 to 7.8 N-m | Factory Standard (~56-70 in-lbs) |
                | | Valve Cover Bolts (Pro Street) | M6 | **3.3 to 4.7 ft-lbs** | 4.5 to 6.4 N-m | My Pro Street Range |
                | | Intake Manifold-to-Head | M8 | **17 to 20 ft-lbs** | 23 to 27 N-m | Factory Standard / Subimods |
                | | Intake Manifold Bolts (Pro Street) | M8 | **18 ft-lbs** | 24.4 N-m | My Pro Street Spec |
                | | Exhaust Manifold-to-Head | M10 | **22 to 29 ft-lbs** | 30 to 39 N-m | Factory Standard / Subimods |
                | | Crankshaft Pulley Center Bolt | M18 | **35 ft-lbs + 60° turn** | 47 N-m + 60° turn | Factory Standard |
                | | Water Pump Mounting Bolts | M6 | **9 ft-lbs** | 12 N-m | Factory Standard |
                | **Drivetrain** | Gearbox Fill / Drain Plugs | M18 | **37 ft-lbs** | 50 N-m | Alum Washer |
                | | Gearbox Drain Plug | M18 | **52 ft-lbs** | 70 N-m | Copper Washer |
                | | Rear Diff Fill / Drain Plugs | M20 | **36 to 43 ft-lbs** | 49 to 58 N-m | Hypoid Housing |
                | | Clutch Pressure Plate | M8 | **12 ft-lbs** | 16 N-m | Clutch Cover |
                | | Flywheel Assembly Bolts | M10 | **55 ft-lbs** | 75 N-m | Crank Connection |
                | **Chassis** | Wheel Lug Nuts (Alloy Hub) | M12 x 1.25 | **89 to 94 ft-lbs** | 120 to 127 N-m | Factory Standard / Subimods |
                | | Wheel Lug Nuts (Pro Street) | M12 x 1.25 | **88.5 ft-lbs** | 120 N-m | My Pro Street |
                | | Front Upper Strut Hat Nuts | M10 | **22 ft-lbs** | 30 N-m | Strut Tower |
                | | Knuckle Lower Strut Bolts | M14 | **129 ft-lbs** | 175 N-m | Alignment Clevis |
                | | Rear Upper Strut Hat Nuts | M10 | **22 ft-lbs** | 30 N-m | Rear Hat |
                | | Rear Lower Strut Mount Bolt | M14 | **162 ft-lbs** | 220 N-m | Trailing Arm |
                | | Rear Main Subframe Bolts | M14 | **106.9 ft-lbs** | 145 N-m | Cradle Mounting |
                | **Brakes** | Front Brembo Caliper (Corrected) | M12 x 1.5 | **80 ft-lbs** | 114 N-m | Caliper-to-Knuckle |
                | | Rear Brembo Caliper Bolts | M10 x 1.5 | **52.8 ft-lbs** | 71.5 N-m | Caliper-to-Bracket |
                | | Brake Hose Banjo Bolt | M10 | **19.2 to 22 ft-lbs** | 26 to 30 N-m | Copper Crush Washers |
                | | Caliper Bleeder Screws | M8 / M10 | **14.8 ft-lbs** | 20 N-m | Bleed Screws |
                """
            )

        # Section 3: My Pro Street DIY Pitfall & Warning Guide
        with st.expander("⚠️ My Pro Street DIY Pitfall & Warning Guide"):
            st.markdown(
                """
                ### 🛑 Why Torque Specs Matter on the Subaru STI (My Pro Street Guide)
                Improper torque on your horizontally opposed boxer engine is a major cause of mechanical failures due to its aluminum components, high vibration, and intense heat cycles. "Good-n-tight" is not an official Subaru engineering measurement—use calibrated torque wrenches to avoid expensive repairs!
                
                #### 1. Spark Plug Torque: Why It Matters
                *   **Pro Street Target Spec:** **15.5 ft-lb (21 N·m)**.
                *   **Over-tightening Hazards:** Can strip soft aluminum cylinder head threads, damage plug gaskets, crack the delicate ceramic insulators, or cause improper heat transfer. Thread repair on an EJ head is extremely difficult.
                *   **Under-tightening Hazards:** Loose spark plugs can cause severe combustion leakage, engine overheating, poor ignition performance, compression loss, or burned threads. The Subaru ignition manual explicitly notes loose plugs as a cause of overheating-related plug damage.
                
                #### 2. Ignition Coil Torque
                *   **Pro Street Target Spec:** **11.8 ft-lb (16 N·m)**.
                *   **Operational Risks:** The STI uses a direct ignition coil-on-plug system. Improper installation torque can create poor coil seating, weak spark delivery, electrical vibration issues, and misfires under boost. 
                *   *Pro Tip:* Many Subaru owners chase fueling issues for weeks only to discover the ignition coil wasn't fully seated because someone tightened it using "vibes" instead of a torque wrench!
                
                #### 3. Valve Cover Bolts
                *   **Pro Street Target Spec:** **3.3 to 4.7 ft-lb**.
                *   **The Pickle Jar Pitfall:** Valve cover leaks are extremely common on EJ engines. Because these bolts thread into soft aluminum, over-tightening can easily warp the valve covers, damage the gaskets, or strip the threads completely. 
                *   *Pro Tip:* When people see an oil leak, they instinctively tighten the bolts harder like they're trying to close a pickle jar—this is a guaranteed way to strip your engine head! Always use an **inch-pound torque wrench** for these low values.
                
                #### 4. Wheel Lug Nuts
                *   **Pro Street Target Spec:** **88.5 ft-lb**.
                *   **Operational Risks:** Improper wheel torque can warp brake rotors, cause uneven wheel clamping, damage studs, or lead to dangerous wheel vibrations.
                *   *Warning:* Impact guns set to "earthquake mode" are not scientific measuring or precision tools! Always do your final pass with a calibrated torque wrench.
                
                #### 5. Intake Manifold Bolts
                *   **Pro Street Target Spec:** **18 ft-lb**.
                *   **Operational Risks:** Improper or uneven torque on the intake manifold can cause vacuum leaks, boost leaks, uneven airflow, rough idling, or lean AFR (air-fuel ratio) conditions.
                *   *Note:* On turbocharged Subarus, even a tiny vacuum leak can create massive drivability problems that make it feel like your ECU suddenly developed major trust issues!
                
                #### 6. Turbocharger Torque Considerations
                *   **Extreme Heat Cycles:** Turbo hardware experiences intense thermal changes. This affects up-pipe fasteners, downpipe hardware, exhaust manifold bolts, and turbo oil feed banjo bolts.
                *   **Failure Modes:** Under-torquing leads to exhaust leaks and boost leaks. Over-torquing leads to broken studs and oil starvation.
                *   *Note:* Always use proper high-temperature anti-seize and perform heat-cycle inspections. This is critical because turbo studs on an older STI can easily develop the structural integrity of stale breadsticks!
                """
            )

        # Section 4: Cylinder Head sequence
        with st.expander("🔩 DOHC EJ257 Cylinder Head Bolt Tightening Sequence"):
            st.markdown(
                """
                ### ⚙️ 10-Step Cylinder Head Elastic-Plastic Tightening Procedure
                Always use brand new, clean, and dry OEM **Torque-To-Yield (TTY)** head bolts lightly lubricated with engine oil on the threads and flange faces prior to insertion. Tighten strictly in the designated cross-pattern sequence (center outward):
                
                1.  **Stage 1:** Torque all bolts in sequence to **40 N-m (29.5 ft-lbs)**.
                2.  **Stage 2:** Torque all bolts in sequence to **95 N-m (70 ft-lbs)**.
                3.  **Stage 3:** Loosen all bolts by **180°** in reverse sequence.
                4.  **Stage 4:** Loosen all bolts an additional **180°** to release pre-tension completely.
                5.  **Stage 5:** Torque all bolts in sequence to **10 N-m (7.4 ft-lbs)**.
                6.  **Stage 6:** Torque all bolts in sequence to **30 N-m (22 ft-lbs)**.
                7.  **Stage 7:** Torque all bolts in sequence to **70 N-m (51.6 ft-lbs)**.
                8.  **Stage 8:** Rotate all bolts **80° to 90°** in sequence.
                9.  **Stage 9:** Rotate all bolts an additional **40° to 45°** in sequence.
                10. **Stage 10:** Rotate center bolts (1 and 2 only) a final **40° to 45°**.
                
                ⚠️ **Warning:** Never reuse stretched TTY head bolts, doing so almost guarantees an uneven seal and immediate head gasket failure!
                """
            )

        # Section 5: Critical Vulnerabilities & Engineering Solutions
        with st.expander("🛠️ Diagnostics of Critical Vulnerabilities & Field Engineering Solutions"):
            st.markdown(
                """
                ### ⚙️ EJ257 Engineering Vulnerabilities & Proven Fixes
                
                #### 1. Cylinder 4 Overheating, Detonation, and Ringland Failure
                *   **The Cause:** The coolant jacket flow routes sequentially but reaches a stagnation zone around Cylinder 4 (rear left). Localized coolant flow drops, causing a thermal spike that lowers Cylinder 4's knock threshold. Under high load, recurring detonation cracks the brittle cast-aluminum factory piston ringlands, causing compression loss, severe blow-by, and cylinder scoring.
                *   **The Fix:** Retrofit a **Cylinder 4 Chamber Cooling System**. This integrates a coolant return hose at the rear coolant port of the Cylinder 4 head, routing hot coolant directly into the heater core return line to balance temperature gradients across all heads.
                
                #### 2. Crankcase Blow-by and Intake Octane Degradation
                *   **The Cause:** Horizontally opposed flat layout under boost creates excessive crankcase blow-by. Suspended oil mist enters the intake through the PCV system, coating the compressor, intercooler, and runners. This lower-flashpoint oil vapor degrades the fuel's effective octane rating, triggering knocking.
                *   **The Fix:** Install a high-performance, heated dual-chamber **Air-Oil Separator (AOS)**. An AOS intercepts PCV gases, separates oil, and drains it back to the pan. Routing engine coolant through the AOS base prevents moisture condensation and sludge buildup.
                
                #### 3. Firewall Pitch Stop Bracket Structural Weld Failure
                *   **The Cause:** Rotational torque reaction forces are stabilized by a pitch stop mount connecting the transmission to the firewall. In 2015-2016 models, the bracket was stamped from thin sheet-metal and secured with weak spot welds. Installing a stiff aftermarket mount fatigues and tears the bracket completely off the firewall.
                *   **The Fix:** Install a heavy-duty **pitch stop bracket brace** which anchors to the strut towers and master cylinder mounting points. If spot welds are already torn, the firewall must be prepped, realigned, and reinforced with TIG welds before brace installation.
                
                #### 4. Starlink Data Communications Module (DCM) Parasitic Battery Drain
                *   **The Cause:** Decommissioned 3G networks cause the 2016 WRX STI's telematics system to enter an infinite boot-loop searching for signal. Operating on a constant 12V non-switched power source, this causes a **120-140 mA parasitic draw** (exceeding the standard 70 mA limit), draining batteries within 24-48 hours.
                *   **The Fix:** Install a **wireless bypass harness** to route audio around the DCM, or program the DCM into "Factory Mode" using a dealer scan tool per **TSB 15-312-23R** to permanently disable the cellular transceiver.
                
                #### 5. Clutch Pedal Creaking Mechanical Noise
                *   **The Cause:** Creaking sounds during pedal depression are typically pivot wear within the clutch bracket, or a dry clutch fork pivot ball rubbing under friction.
                *   **The Fix:** Remove the intercooler, peel back the slave cylinder rubber boot, and apply high-temperature white lithium grease directly to the release fork and pivot ball socket. If noise persists, replace with an updated pedal bracket assembly per **TSB 12-190-15 and TSB 03-79-18R**.
                """
            )

        # Section 6: Engine Class Action Settlement & Recalls
        with st.expander("⚖️ Regulatory Safety Recalls & The EJ257 Catastrophic Engine Settlement"):
            st.markdown(
                """
                ### 🏛️ EJ257 Settlement & Official Safety Recalls
                
                #### 1. The EJ257 Engine Failure Class Action Settlement (2018)
                *   **Target Scope:** 2012–2017 Subaru WRX and WRX STI equipped with the 2.5-liter turbocharged EJ257 engine built between Oct. 11, 2011, and Nov. 16, 2016.
                *   **Target VIN Ranges:** 5-door hatch models ending in **CG203168 and up**; 4-door sedan models ending in **CG006225 through H9826807**.
                *   **The Issue:** The lawsuit alleged internal defects allowed metallic debris from deteriorating bearings and oil pump failures to contaminate engine oil, restricting flow through crankshaft passages and causing bearing seizure, piston ringland fractures, and catastrophic engine failure.
                *   **Provisions:**
                    *   **Warranty Extension:** Powertrain warranty extended to **8 years or 100,000 miles**.
                    *   **Reimbursement:** 100% reimbursement for out-of-pocket parts/labor expenses for engine failures.
                    *   **CPO Warranty Program:** For secondary buyers, Certified Pre-Owned vehicles must pass a 152-point inspection to receive a 6-year/100,000-mile powertrain warranty with a **$35 USD deductible**.
                
                #### 2. Key Safety Recalls & Technical Service Bulletins
                *   **NHTSA Campaign 19V149000 (Recall WUE-90 - Brake Light Switch):** Silicone contaminants from cleaning products penetrate the brake light switch housing, preventing brake lights from illuminating and disabling push-button start. Dealers replace with a sealed unit.
                *   **NHTSA Campaign 16V162000 (Recall WTA-62 - Turbo Air Intake Duct):** 2015–2016 WRX and Forester 2.0XT plastic turbo air ducts can crack under thermal cycles and high engine movement, causing unmetered air leaks and lean stalling conditions. Dealers replace with a reinforced compound duct.
                *   **Recall WUT-05 (zinc-coated coils):** Zinc-coated springs replacement for vehicles in road-salt states to prevent coil spring corrosion and fracture.
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

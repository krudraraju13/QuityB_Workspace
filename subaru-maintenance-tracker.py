"""
Subaru STI Maintenance Tracker
A hybrid Streamlit Web App & Rich-text Terminal CLI application for tracking 
and scheduling high-performance maintenance for Subaru WRX STI vehicles (EJ257/FA20).
Grounded in the architecture from subaru-maintenance-tracker-v37.txt.
"""

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

# Standard Subaru WRX STI Maintenance Intervals (in miles)
# Grounded in official Subaru maintenance schedules with consideration for high-performance turbocharged engines.
MAINTENANCE_SCHEDULE = [
    {
        "item": "Engine Oil & Filter",
        "normal_interval": 6000,
        "severe_interval": 3000,
        "description": "Replace engine oil and filter (Synthetic 5W-30 or heavier for STI EJ257). Highly recommended to check level weekly."
    },
    {
        "item": "Tire Rotation",
        "normal_interval": 6000,
        "severe_interval": 6000,
        "description": "Rotate tires to ensure even tread wear, protecting the Symmetrical AWD system from drivetrain binding."
    },
    {
        "item": "Cabin Air Filter",
        "normal_interval": 12000,
        "severe_interval": 12000,
        "description": "Replace the cabin dust and pollen HVAC filter."
    },
    {
        "item": "Engine Air Filter",
        "normal_interval": 30000,
        "severe_interval": 15000,
        "description": "Replace engine air filter element. Check and clean more frequently in dusty conditions."
    },
    {
        "item": "Brake Fluid Flush",
        "normal_interval": 30000,
        "severe_interval": 30000,
        "description": "Flush and replace brake fluid (DOT 3 or 4) to maintain Brembo brake system responsiveness."
    },
    {
        "item": "Transmission & Diff Gear Oils",
        "normal_interval": 30000,
        "severe_interval": 15000,
        "description": "Replace manual transmission gear oil (75W-90 Extra-S or equivalent) and rear differential gear oil (90LS/75W-90). Essential for DCCD and LSD."
    },
    {
        "item": "Spark Plugs",
        "normal_interval": 60000,
        "severe_interval": 60000,
        "description": "Replace Spark Plugs (Iridium). Critical for proper ignition and preventing knock in high-performance Boxer engines."
    },
    {
        "item": "Timing Belt & Water Pump",
        "normal_interval": 105000,
        "severe_interval": 105000,
        "description": "Replace engine timing belt, tensioner, idlers, and water pump (EJ257 interference engine). Critical to prevent catastrophic engine failure."
    },
    {
        "item": "Engine Coolant Flush",
        "normal_interval": 137500,
        "severe_interval": 137500,
        "description": "First replacement is at 137,500 miles or 11 years (Subaru Super Coolant); subsequent replacements every 75,000 miles or 6 years."
    }
]

class MaintenanceScheduler:
    def __init__(self, mileage, severe=False, primary_mode=True):
        self.mileage = mileage
        self.severe = severe
        self.primary_mode = primary_mode  # True for Miles, False for Kilometers

    def convert_distance(self, miles):
        """Converts distance based on primary mode (True for Miles, False for Kilometers)"""
        if self.primary_mode:
            return miles
        else:
            return int(miles * 1.60934)

    def get_recommendations(self):
        """Calculates recommendations, next due mileage, and status for each scheduled item."""
        recommendations = []
        for task in MAINTENANCE_SCHEDULE:
            interval_miles = task["severe_interval"] if self.severe else task["normal_interval"]
            
            # Convert intervals to primary unit
            interval_unit = self.convert_distance(interval_miles)
            current_unit = self.convert_distance(self.mileage)
            
            # Calculate next due mileage in unit
            next_due = ((current_unit // interval_unit) + 1) * interval_unit
            remaining = next_due - current_unit
            
            # Deem "Due Now" if remaining is within 10% of the interval, or if current mileage has crossed an interval step
            due_now = remaining <= (interval_unit * 0.1) or (current_unit % interval_unit == 0)
            
            recommendations.append({
                "item": task["item"],
                "interval": interval_unit,
                "due_now": due_now,
                "next_due": next_due,
                "remaining": remaining,
                "description": task["description"]
            })
        return recommendations

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
    
    st.title("🏎️ Subaru WRX STI Maintenance Tracker")
    st.markdown("""
    Keep your high-performance Boxer engine running flawlessly! This tracker calculates recommended 
    maintenance intervals based on whether your car is driven under **Normal** or **Severe** conditions, 
    and lets you log maintenance history.
    """)
    
    # User Inputs
    col1, col2, col3 = st.columns(3)
    with col1:
        primary_mode_str = st.radio("Primary Unit Mode", ["Miles (mi)", "Kilometers (km)"], index=0)
        primary_mode = primary_mode_str.startswith("Miles")
        unit_label = "mi" if primary_mode else "km"
        
    with col2:
        mileage = st.number_input(f"Current Mileage ({unit_label})", min_value=0, value=30000, step=1000)
        # Convert internal mileage back to miles for the MaintenanceScheduler
        scheduler_mileage = mileage if primary_mode else int(mileage / 1.60934)
        
    with col3:
        severe = st.checkbox("Severe Driving Conditions", value=False, 
                             help="Select if you engage in: frequent short trips under 5 miles, dusty/sandy conditions, track driving, extremely cold weather, or heavy idling.")

    scheduler = MaintenanceScheduler(scheduler_mileage, severe=severe, primary_mode=primary_mode)
    recommendations = scheduler.get_recommendations()
    
    # Layout tabs
    tab_sched, tab_log, tab_hist = st.tabs(["📊 Maintenance Schedule", "📝 Log Maintenance", "📜 Maintenance History"])
    
    with tab_sched:
        st.subheader("Upcoming Recommended Maintenance")
        
        # Display due items in priority alert if any are due now
        due_now_items = [r for r in recommendations if r["due_now"]]
        if due_now_items:
            st.error(f"⚠️ **Attention!** You have {len(due_now_items)} maintenance item(s) due soon or overdue!")
            for item in due_now_items:
                st.markdown(f"- **{item['item']}** (Due at: {item['next_due']:,} {unit_label} | Remaining: {item['remaining']:,} {unit_label})")
        else:
            st.success("✅ All scheduled maintenance items are up to date!")
            
        st.write("---")
        
        # Table of all recommendations
        schedule_table = []
        for r in recommendations:
            status = "🔴 DUE NOW" if r["due_now"] else "🟢 OK"
            schedule_table.append({
                "Maintenance Item": r["item"],
                "Interval": f"{r['interval']:,} {unit_label}",
                "Next Due At": f"{r['next_due']:,} {unit_label}",
                "Remaining": f"{r['remaining']:,} {unit_label}",
                "Status": status,
                "Description": r["description"]
            })
        st.table(schedule_table)

    with tab_log:
        st.subheader("Log a Completed Maintenance Task")
        with st.form("log_form", clear_on_submit=True):
            log_date = st.date_input("Date of Service", datetime.date.today())
            log_mileage = st.number_input(f"Mileage at Service ({unit_label})", min_value=0, value=mileage, step=1000)
            
            # Build item options
            item_options = [task["item"] for task in MAINTENANCE_SCHEDULE] + ["Other (Specify in Notes)"]
            log_item = st.selectbox("Maintenance Item", item_options)
            
            log_cost = st.number_input("Service Cost ($)", min_value=0.0, value=0.0, step=10.0)
            log_notes = st.text_area("Service Notes (e.g., oil brand, part numbers, technician comments)")
            
            submit = st.form_submit_button("Save Maintenance Record")
            
            if submit:
                # Save entry in standardized format
                entry = {
                    "date": str(log_date),
                    "mileage": int(log_mileage),
                    "unit": unit_label,
                    "item": log_item,
                    "cost": float(log_cost),
                    "notes": log_notes
                }
                save_history(entry)
                st.success(f"Successfully saved record for '{log_item}'!")
                st.rerun()

    with tab_hist:
        st.subheader("Maintenance History Records")
        history = load_history()
        if history:
            # Calculate total cost
            total_spent = sum(entry.get("cost", 0.0) for entry in history)
            st.metric("Total Maintenance Spend", f"${total_spent:,.2f}")
            
            # Sort history by mileage descending
            sorted_history = sorted(history, key=lambda x: x.get("mileage", 0), reverse=True)
            for entry in sorted_history:
                with st.expander(f"📅 {entry.get('date')} — {entry.get('item')} @ {entry.get('mileage'):,} {entry.get('unit', 'mi')}"):
                    st.write(f"**Cost:** ${entry.get('cost', 0.0):,.2f}")
                    st.write(f"**Notes:** {entry.get('notes', 'None')}")
        else:
            st.info("No maintenance history logged yet. Use the 'Log Maintenance' tab to record your first service!")

# --- INTERACTIVE TERMINAL CLI RUNTIME ---
elif HAS_RICH:
    console = Console()
    
    # Beautiful ASCII Art representing a stylized Subaru boxer profile/STI branding
    boxer_logo = r"""
 _____ _   _ ____    _    ____  _   _     ____ _____ ___ 
/ ___/| | | | __ )  / \  |  _ \| | | |   / ___|_   _|_ _|
\___ \| | | |  _ \ / _ \ | |_) | | | |   \___ \ | |  | | 
 ___) | |_| | |_) / ___ \|  _ <| |_| |    ___) || |  | | 
|____/ \___/|____/_/   \_\_| \_\\___/    |____/ |_| |___|

        🏎️  Symmetrical AWD Boxer Engine Maintenance  🏎️
"""
    
    def run_rich_cli():
        console.print(Panel(boxer_logo, subtitle="STI Maintenance Scheduler v3.7", subtitle_align="right", border_style="blue"))
        
        # Initial prompt for vehicle setup
        console.print("\n[bold yellow]=== Vehicle Configuration ===[/bold yellow]")
        unit_choice = Confirm.ask("Is your primary unit Miles (Yes) or Kilometers (No)?", default=True)
        unit_label = "mi" if unit_choice else "km"
        
        mileage = IntPrompt.ask(f"Enter your current vehicle mileage ({unit_label})", default=30000)
        severe = Confirm.ask("Do you drive under severe conditions (dusty, short trips, cold, or track use)?", default=False)
        
        # Translate to internal storage
        scheduler_mileage = mileage if unit_choice else int(mileage / 1.60934)
        scheduler = MaintenanceScheduler(scheduler_mileage, severe=severe, primary_mode=unit_choice)
        
        while True:
            console.print("\n[bold cyan]=== STI Main Menu ===[/bold cyan]")
            console.print("1. [green]Check Maintenance Schedule & Recommendations[/green]")
            console.print("2. [green]Log Completed Maintenance Task[/green]")
            console.print("3. [green]View Maintenance History Log[/green]")
            console.print("4. [red]Exit Tracker[/red]")
            
            choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "1":
                recommendations = scheduler.get_recommendations()
                table = Table(title=f"STI Scheduled Maintenance Recommendations ({unit_label})", border_style="blue")
                table.add_column("Maintenance Item", style="cyan", no_wrap=True)
                table.add_column("Interval", style="magenta")
                table.add_column("Next Due", style="magenta")
                table.add_column("Remaining", style="magenta")
                table.add_column("Status", style="bold")
                
                due_now_count = 0
                for r in recommendations:
                    if r["due_now"]:
                        status = "[red]🔴 DUE NOW[/red]"
                        due_now_count += 1
                    else:
                        status = "[green]🟢 OK[/green]"
                        
                    table.add_row(
                        r["item"],
                        f"{r['interval']:,} {unit_label}",
                        f"{r['next_due']:,} {unit_label}",
                        f"{r['remaining']:,} {unit_label}",
                        status
                    )
                console.print(table)
                if due_now_count > 0:
                    console.print(f"\n[bold red]⚠️  ALERT: You have {due_now_count} item(s) due or overdue! Plan service immediately.[/bold red]")
                else:
                    console.print("\n[bold green]✅ Excellent! Your STI is all up to date on maintenance intervals.[/bold green]")
                    
            elif choice == "2":
                console.print("\n[bold yellow]--- Log Maintenance Service ---[/bold yellow]")
                # Select item
                console.print("Select maintenance item:")
                for i, task in enumerate(MAINTENANCE_SCHEDULE, 1):
                    console.print(f"{i}. {task['item']}")
                console.print(f"{len(MAINTENANCE_SCHEDULE) + 1}. Other (Custom Service)")
                
                item_idx = IntPrompt.ask("Enter choice #", default=1)
                if 1 <= item_idx <= len(MAINTENANCE_SCHEDULE):
                    selected_item = MAINTENANCE_SCHEDULE[item_idx - 1]["item"]
                else:
                    selected_item = Prompt.ask("Enter custom service name", default="Custom Service")
                
                log_mileage = IntPrompt.ask(f"Mileage at service ({unit_label})", default=mileage)
                cost = float(Prompt.ask("Service cost ($)", default="0.0"))
                notes = Prompt.ask("Service Notes (parts, oil spec, comments)", default="")
                
                entry = {
                    "date": str(datetime.date.today()),
                    "mileage": log_mileage,
                    "unit": unit_label,
                    "item": selected_item,
                    "cost": cost,
                    "notes": notes
                }
                save_history(entry)
                console.print(f"\n[bold green]✔ Saved maintenance entry for '{selected_item}' to history![/bold green]")
                
            elif choice == "3":
                history = load_history()
                if not history:
                    console.print("\n[yellow]No maintenance history logged yet.[/yellow]")
                else:
                    total_spent = sum(entry.get("cost", 0.0) for entry in history)
                    hist_table = Table(title=f"STI Maintenance History (Total Spend: ${total_spent:,.2f})", border_style="green")
                    hist_table.add_column("Date", style="cyan")
                    hist_table.add_column("Maintenance Item", style="magenta")
                    hist_table.add_column("Mileage", style="yellow")
                    hist_table.add_column("Cost ($)", style="green")
                    hist_table.add_column("Notes", style="white")
                    
                    # Sort by mileage descending
                    sorted_history = sorted(history, key=lambda x: x.get("mileage", 0), reverse=True)
                    for entry in sorted_history:
                        hist_table.add_row(
                            entry.get("date", "N/A"),
                            entry.get("item", "N/A"),
                            f"{entry.get('mileage'):,} {entry.get('unit', 'mi')}",
                            f"${entry.get('cost', 0.0):,.2f}",
                            entry.get("notes", "None")
                        )
                    console.print(hist_table)
                    
            elif choice == "4":
                console.print("\n[bold blue]Thank you for using the STI Maintenance Tracker! Keep boostin' safely! 🏎️💨[/bold blue]\n")
                break

    if __name__ == "__main__":
        run_rich_cli()

else:
    # Fallback minimal interactive prompt when neither streamlit nor rich are installed.
    def run_fallback_cli():
        print("\n=======================================================")
        print("🏎️ Subaru STI Maintenance App (Minimal fallback)")
        print("Please install streamlit ('pip install streamlit') or rich ('pip install rich') for the enhanced UI.")
        print("=======================================================")
        
        try:
            unit_choice = input("Is your primary unit Miles? (Y/N, default=Y): ").strip().lower() != 'n'
            unit_label = "mi" if unit_choice else "km"
            
            mileage_input = input(f"Enter current mileage ({unit_label}, default=30000): ").strip()
            mileage = int(mileage_input) if mileage_input.isdigit() else 30000
            
            severe_choice = input("Severe driving conditions? (Y/N, default=N): ").strip().lower() == 'y'
            
            scheduler_mileage = mileage if unit_choice else int(mileage / 1.60934)
            scheduler = MaintenanceScheduler(scheduler_mileage, severe=severe_choice, primary_mode=unit_choice)
            
            while True:
                print("\nMenu:")
                print("1. Check Maintenance Recommendations")
                print("2. Log Completed Maintenance")
                print("3. View Maintenance History")
                print("4. Exit")
                choice = input("Select an option (1-4): ").strip()
                
                if choice == "1":
                    recommendations = scheduler.get_recommendations()
                    print(f"\nUpcoming Recommendations ({unit_label}):")
                    print(f"{'Item':<35} | {'Interval':<10} | {'Next Due':<10} | {'Remaining':<10} | {'Status'}")
                    print("-" * 80)
                    for r in recommendations:
                        status = "🔴 DUE NOW" if r["due_now"] else "🟢 OK"
                        print(f"{r['item']:<35} | {r['interval']:<10} | {r['next_due']:<10} | {r['remaining']:<10} | {status}")
                elif choice == "2":
                    print("\nLog Completed Maintenance:")
                    for i, task in enumerate(MAINTENANCE_SCHEDULE, 1):
                        print(f"{i}. {task['item']}")
                    print(f"{len(MAINTENANCE_SCHEDULE) + 1}. Other (Custom)")
                    
                    try:
                        item_idx = int(input("Enter choice #: ").strip())
                        if 1 <= item_idx <= len(MAINTENANCE_SCHEDULE):
                            selected_item = MAINTENANCE_SCHEDULE[item_idx - 1]["item"]
                        else:
                            selected_item = input("Enter custom service name: ").strip() or "Custom Service"
                    except ValueError:
                        selected_item = "Custom Service"
                        
                    try:
                        log_mileage = int(input(f"Mileage at service ({unit_label}): ").strip())
                    except ValueError:
                        log_mileage = mileage
                        
                    try:
                        cost = float(input("Service Cost ($): ").strip())
                    except ValueError:
                        cost = 0.0
                        
                    notes = input("Service Notes: ").strip()
                    
                    entry = {
                        "date": str(datetime.date.today()),
                        "mileage": log_mileage,
                        "unit": unit_label,
                        "item": selected_item,
                        "cost": cost,
                        "notes": notes
                    }
                    save_history(entry)
                    print(f"Logged {selected_item} successfully!")
                    
                elif choice == "3":
                    history = load_history()
                    if not history:
                        print("\nNo history logged yet.")
                    else:
                        print(f"\nService History Log:")
                        print(f"{'Date':<12} | {'Item':<30} | {'Mileage':<10} | {'Cost':<8} | {'Notes'}")
                        print("-" * 80)
                        for entry in history:
                            print(f"{entry.get('date'):<12} | {entry.get('item'):<30} | {entry.get('mileage'):<10} | ${entry.get('cost', 0.0):<7.2f} | {entry.get('notes')}")
                elif choice == "4":
                    print("\nGoodbye! Happy driving!")
                    break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting tracker. Goodbye!")

if __name__ == "__main__":
    # If run in python CLI but HAS_STREAMLIT and streamlit is running, we let streamlit handle execution.
    # Otherwise, fall back to rich or terminal fallback.
    if HAS_STREAMLIT and st.runtime.exists():
        pass
    elif HAS_RICH:
        run_rich_cli()
    else:
        run_fallback_cli()

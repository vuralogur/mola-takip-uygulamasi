import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import os
from datetime import datetime, timedelta

# File paths
DATA_FILE = "break_data.json"
EMPLOYEE_FILE = "employees.json"

def save_employees(employees):
    with open(EMPLOYEE_FILE, "w") as file:
        json.dump(employees, file)

def load_employees():
    if os.path.exists(EMPLOYEE_FILE):
        with open(EMPLOYEE_FILE, "r") as file:
            return json.load(file)
    return []

def add_employee():
    new_employee = entry_employee_name.get().strip()
    if new_employee:
        employees = load_employees()
        if new_employee not in employees:
            employees.append(new_employee)
            save_employees(employees)
            update_employee_list()
            entry_employee_name.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Employee already exists.")
    else:
        messagebox.showerror("Error", "Please enter a valid employee name.")

def delete_employee():
    employee = selected_employee.get()
    if employee:
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {employee}? This action cannot be undone."):
            employees = load_employees()
            if employee in employees:
                employees.remove(employee)
                save_employees(employees)
                
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, "r") as file:
                        data = json.load(file)
                    if employee in data:
                        del data[employee]
                        with open(DATA_FILE, "w") as file:
                            json.dump(data, file)
                
                update_employee_list()
                messagebox.showinfo("Info", f"{employee} has been deleted.")
            else:
                messagebox.showinfo("Info", "Employee not found.")
        else:
            messagebox.showinfo("Info", "Delete operation canceled.")
    else:
        messagebox.showerror("Error", "Please select an employee.")

def update_employee_list():
    employee_list_menu['menu'].delete(0, 'end')
    employees = load_employees()
    for employee in employees:
        employee_list_menu['menu'].add_command(label=employee, command=tk._setit(selected_employee, employee))

def save_break_data(employee, start_time, end_time, duration_minutes, duration_seconds):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as file:
            json.dump({}, file)
    
    with open(DATA_FILE, "r") as file:
        data = json.load(file)
    
    if employee not in data:
        data[employee] = []
    
    data[employee].append({
        "start_time": start_time, 
        "end_time": end_time, 
        "duration_minutes": duration_minutes,
        "duration_seconds": duration_seconds
    })
    
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

def load_break_data(employee):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            return data.get(employee, [])
    return []

def delete_break_data(employee, index):
    if not os.path.exists(DATA_FILE):
        return
    
    with open(DATA_FILE, "r") as file:
        data = json.load(file)
    
    if employee in data:
        if 0 <= index < len(data[employee]):
            del data[employee][index]
            if not data[employee]:
                del data[employee]
        else:
            messagebox.showerror("Error", "Invalid index.")
    
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

def confirm_delete_break_data(employee):
    break_data = load_break_data(employee)
    if break_data:
        delete_window = tk.Toplevel(root)
        delete_window.title("Select Breaks to Delete")

        lbl_instruction = ttk.Label(delete_window, text="Select breaks to delete (Ctrl+click for multiple selection):")
        lbl_instruction.pack(padx=10, pady=5)

        listbox = tk.Listbox(delete_window, selectmode=tk.MULTIPLE, height=10, width=50)
        for i, record in enumerate(break_data):
            listbox.insert(tk.END, f"{i + 1}. Start: {record['start_time']}, End: {record['end_time']}, Duration: {record['duration_minutes']}:{record['duration_seconds']:02} minutes")
        listbox.pack(padx=10, pady=5)

        def delete_selected():
            selected_indices = listbox.curselection()
            for index in reversed(selected_indices):
                delete_break_data(employee, index)
            update_employee_list()
            delete_window.destroy()
            messagebox.showinfo("Info", "Selected breaks have been deleted.")

        def delete_all():
            if messagebox.askyesno("Confirm", "Are you sure you want to delete all breaks for this employee? This action cannot be undone."):
                delete_all_break_data(employee)
                update_employee_list()
                delete_window.destroy()
                messagebox.showinfo("Info", "All breaks have been deleted.")

        btn_confirm_delete = ttk.Button(delete_window, text="Delete Selected Breaks", command=delete_selected)
        btn_confirm_delete.pack(padx=10, pady=5)

        btn_delete_all = ttk.Button(delete_window, text="Delete All Breaks", command=delete_all)
        btn_delete_all.pack(padx=10, pady=5)

        btn_cancel = ttk.Button(delete_window, text="Cancel", command=delete_window.destroy)
        btn_cancel.pack(padx=10, pady=5)

    else:
        messagebox.showinfo("Info", "No break data found for the selected employee.")

def delete_all_break_data(employee):
    if not os.path.exists(DATA_FILE):
        return
    
    with open(DATA_FILE, "r") as file:
        data = json.load(file)
    
    if employee in data:
        del data[employee]
    
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

def start_break():
    global break_start_time
    break_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lbl_break_start.config(text=f"Break Start: {break_start_time}")
    lbl_break_duration.config(text="Break Duration: 00:00:00")

def end_break():
    global break_start_time
    if break_start_time:
        break_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = break_start_time
        end_time = break_end_time
        
        start_time_obj = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time_obj = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        duration = end_time_obj - start_time_obj
        duration_seconds = int(duration.total_seconds())
        duration_minutes = duration_seconds // 60
        duration_seconds %= 60
        
        employee = selected_employee.get()
        if employee:
            save_break_data(employee, start_time, end_time, duration_minutes, duration_seconds)
            lbl_break_duration.config(text=f"Break Duration: {duration_minutes}:{duration_seconds:02}")
        else:
            messagebox.showerror("Error", "Please select an employee.")
    else:
        messagebox.showerror("Error", "Break has not started yet.")

def show_summary():
    employee = selected_employee.get()
    if employee:
        break_data = load_break_data(employee)
        total_breaks = len(break_data)
        summary_text = f"Break Summary for {employee}:\n"
        total_duration_minutes = 0
        total_duration_seconds = 0
        work_hours = 8
        total_minutes_worked = work_hours * 60
        
        for record in break_data:
            start = record['start_time']
            end = record['end_time']
            duration_minutes = record['duration_minutes']
            duration_seconds = record['duration_seconds']
            summary_text += f"Start: {start}, End: {end}, Duration: {duration_minutes}:{duration_seconds:02} minutes\n"
            total_duration_minutes += duration_minutes
            total_duration_seconds += duration_seconds
        
        total_duration_minutes += total_duration_seconds // 60
        total_duration_seconds %= 60

        performance_percentage = ((total_minutes_worked - total_duration_minutes) / total_minutes_worked) * 100

        summary_text += f"\nTotal Break Time: {total_duration_minutes}:{total_duration_seconds:02} minutes"
        summary_text += f"\nTotal Breaks: {total_breaks}"
        summary_text += f"\nDay Performance: {performance_percentage:.2f}%"
        messagebox.showinfo("Summary", summary_text)
    else:
        messagebox.showerror("Error", "Please select an employee.")

def delete_selected_employee_data():
    employee = selected_employee.get()
    if employee:
        confirm_delete_break_data(employee)
        update_employee_list()
    else:
        messagebox.showerror("Error", "Please select an employee.")

def filter_breaks_by_period(break_data, period):
    now = datetime.now()
    start_date = None
    
    if period == 'daily':
        start_date = now - timedelta(days=1)
    elif period == 'weekly':
        start_date = now - timedelta(weeks=1)
    elif period == 'monthly':
        start_date = now - timedelta(weeks=4)  # Approximation for simplicity
    
    if start_date:
        start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
        break_data = [record for record in break_data if datetime.strptime(record['start_time'], "%Y-%m-%d %H:%M:%S") >= datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")]
    return break_data

def generate_report(period):
    employee = selected_employee.get()
    if employee:
        break_data = load_break_data(employee)
        filtered_data = filter_breaks_by_period(break_data, period)
        
        if not filtered_data:
            messagebox.showinfo("Report", f"No break data found for the selected period: {period.capitalize()}.")
            return
        
        summary_text = f"Break Report for {employee} ({period.capitalize()}):\n"
        total_duration_minutes = 0
        total_duration_seconds = 0
        
        for record in filtered_data:
            start = record['start_time']
            end = record['end_time']
            duration_minutes = record['duration_minutes']
            duration_seconds = record['duration_seconds']
            summary_text += f"Start: {start}, End: {end}, Duration: {duration_minutes}:{duration_seconds:02} minutes\n"
            total_duration_minutes += duration_minutes
            total_duration_seconds += duration_seconds
        
        total_duration_minutes += total_duration_seconds // 60
        total_duration_seconds %= 60

        summary_text += f"\nTotal Break Time: {total_duration_minutes}:{total_duration_seconds:02} minutes"
        messagebox.showinfo(f"{period.capitalize()} Report", summary_text)
    else:
        messagebox.showerror("Error", "Please select an employee.")

# GUI setup
root = tk.Tk()
root.title("Break Tracker")

root.geometry("550x250")  # Increase window size

frame_employee = ttk.Frame(root, padding="10")
frame_employee.grid(row=0, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))

frame_break = ttk.Frame(root, padding="10")
frame_break.grid(row=1, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))

# Employee Management
lbl_employee = ttk.Label(frame_employee, text="Employee Name:")
lbl_employee.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

entry_employee_name = ttk.Entry(frame_employee)
entry_employee_name.grid(row=0, column=1, padx=5, pady=5)

btn_add_employee = ttk.Button(frame_employee, text="Add Employee", command=add_employee)
btn_add_employee.grid(row=0, column=2, padx=5, pady=5)

btn_delete_employee = ttk.Button(frame_employee, text="Delete Employee", command=delete_employee)
btn_delete_employee.grid(row=0, column=3, padx=5, pady=5)

selected_employee = tk.StringVar()
employee_list_menu = ttk.OptionMenu(frame_employee, selected_employee, "", *load_employees())
employee_list_menu.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=(tk.W, tk.E))

# Break Management
btn_start_break = ttk.Button(frame_break, text="Start Break", command=start_break)
btn_start_break.grid(row=0, column=0, padx=10, pady=5)

btn_end_break = ttk.Button(frame_break, text="End Break", command=end_break)
btn_end_break.grid(row=0, column=1, padx=10, pady=5)

lbl_break_start = ttk.Label(frame_break, text="Break Start: --:--:--")
lbl_break_start.grid(row=1, column=0, padx=5, pady=5, columnspan=2, sticky=tk.W)

lbl_break_duration = ttk.Label(frame_break, text="Break Duration: 00:00:00")
lbl_break_duration.grid(row=1, column=2, padx=5, pady=5, columnspan=2, sticky=tk.W)

btn_delete_breaks = ttk.Button(frame_break, text="Delete Breaks", command=delete_selected_employee_data)
btn_delete_breaks.grid(row=0, column=2, padx=10, pady=5)

btn_show_summary = ttk.Button(frame_break, text="Show Summary", command=show_summary)
btn_show_summary.grid(row=0, column=3, padx=10, pady=5)

# Report Buttons
btn_daily_report = ttk.Button(frame_break, text="Daily Report", command=lambda: generate_report('daily'))
btn_daily_report.grid(row=3, column=0, padx=10, pady=5)

btn_weekly_report = ttk.Button(frame_break, text="Weekly Report", command=lambda: generate_report('weekly'))
btn_weekly_report.grid(row=3, column=1, padx=10, pady=5)

btn_monthly_report = ttk.Button(frame_break, text="Monthly Report", command=lambda: generate_report('monthly'))
btn_monthly_report.grid(row=3, column=2, padx=10, pady=5)

# Initialize the employee list
update_employee_list()

root.mainloop()

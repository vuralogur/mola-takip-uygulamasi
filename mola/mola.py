import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import os
from datetime import datetime

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
        confirmation_text = "Break Data:\n"
        for i, record in enumerate(break_data):
            confirmation_text += f"{i + 1}. Start: {record['start_time']}, End: {record['end_time']}, Duration: {record['duration_minutes']}:{record['duration_seconds']:02} minutes\n"

        confirmation_text += "\nAre you sure you want to delete all data?"
        if messagebox.askyesno("Confirm Delete", confirmation_text):
            delete_all_break_data(employee)
            messagebox.showinfo("Info", "All break data has been deleted.")
        else:
            messagebox.showinfo("Info", "Delete operation canceled.")
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

def delete_selected_employee_data():
    employee = selected_employee.get()
    if employee:
        confirm_delete_break_data(employee)
        update_employee_list()
    else:
        messagebox.showerror("Error", "Please select an employee.")

def start_break():
    global break_start_time
    break_start_time = datetime.now().strftime("%H:%M:%S")
    lbl_break_start.config(text=f"Break Start: {break_start_time}")
    lbl_break_duration.config(text="Break Duration: 00:00:00")

def end_break():
    global break_start_time
    if break_start_time:
        break_end_time = datetime.now().strftime("%H:%M:%S")
        start_time = break_start_time
        end_time = break_end_time
        
        start_time_obj = datetime.strptime(start_time, "%H:%M:%S")
        end_time_obj = datetime.strptime(end_time, "%H:%M:%S")
        
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
        summary_text = f"Break Summary for {employee}:\n"
        total_duration_minutes = 0
        total_duration_seconds = 0
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

        summary_text += f"\nTotal Break Time: {total_duration_minutes}:{total_duration_seconds:02} minutes"
        messagebox.showinfo("Summary", summary_text)
    else:
        messagebox.showerror("Error", "Please select an employee.")

def generate_end_of_day_report():
    employee = selected_employee.get()
    if employee:
        break_data = load_break_data(employee)
        if break_data:
            total_duration_minutes = 0
            total_duration_seconds = 0

            # Calculate total break time
            for record in break_data:
                duration_minutes = record['duration_minutes']
                duration_seconds = record['duration_seconds']
                total_duration_minutes += duration_minutes
                total_duration_seconds += duration_seconds

            # Calculate total time in minutes
            total_duration_minutes += total_duration_seconds // 60
            total_duration_seconds %= 60

            # Performance calculation
            work_hours = 8
            total_minutes_worked = work_hours * 60
            total_break_minutes = total_duration_minutes

            performance_percentage = ((total_minutes_worked - total_break_minutes) / total_minutes_worked) * 100

            # Display report
            summary_text = (f"End of Day Report for {employee}:\n"
                            f"Total Break: {total_duration_minutes} min {total_duration_seconds} sec\n"
                            f"Day Performance: {performance_percentage:.2f}%")

            messagebox.showinfo("End of Day Report", summary_text)
        else:
            messagebox.showerror("Error", "No break data found for the selected employee.")
    else:
        messagebox.showerror("Error", "Please select an employee.")

# GUI
root = tk.Tk()
root.title("Break Tracker")

frame_employee = ttk.Frame(root, padding="10")
frame_employee.grid(row=0, column=0, sticky=(tk.W, tk.E))

frame_break = ttk.Frame(root, padding="10")
frame_break.grid(row=1, column=0, sticky=(tk.W, tk.E))

ttk.Label(frame_employee, text="Employee Name:").grid(row=0, column=0, sticky=tk.W)
entry_employee_name = ttk.Entry(frame_employee)
entry_employee_name.grid(row=0, column=1, padx=5)

ttk.Button(frame_employee, text="Add Employee", command=add_employee).grid(row=0, column=2, padx=5)
ttk.Button(frame_employee, text="Delete Employee", command=delete_employee).grid(row=0, column=3, padx=5)
ttk.Button(frame_employee, text="Delete Break Data", command=delete_selected_employee_data).grid(row=0, column=4, padx=5)

employees = load_employees()
selected_employee = tk.StringVar()
employee_list_menu = ttk.OptionMenu(frame_employee, selected_employee, employees[0] if employees else "", *employees)
employee_list_menu.grid(row=0, column=5, padx=5)

lbl_break_start = ttk.Label(frame_break, text="Break Start: Not started")
lbl_break_start.grid(row=0, column=0, sticky=tk.W)

lbl_break_duration = ttk.Label(frame_break, text="Break Duration: 00:00:00")
lbl_break_duration.grid(row=1, column=0, sticky=tk.W)

ttk.Button(frame_break, text="Start Break", command=start_break).grid(row=0, column=1, padx=5)
ttk.Button(frame_break, text="End Break", command=end_break).grid(row=1, column=1, padx=5)

ttk.Button(frame_break, text="Show Summary", command=show_summary).grid(row=2, column=0, padx=5, pady=5)
ttk.Button(frame_break, text="Generate End of Day Report", command=generate_end_of_day_report).grid(row=2, column=1, padx=5, pady=5)

root.mainloop()

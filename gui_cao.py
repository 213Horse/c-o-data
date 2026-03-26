import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import pandas as pd
from cao import run_scraper, INPUT_FILE, OUTPUT_FILE

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ISBN Scraper Tool")
        self.root.geometry("700x650") 
        self.root.minsize(700, 650)
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=5, font=("Arial", 10))
        style.configure("TLabel", font=("Arial", 10))
        
        # Main Frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Amazon/Google Books ISBN Scraper", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # File Status Section
        status_frame = ttk.LabelFrame(main_frame, text=" File Status ", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.input_status = tk.StringVar(value="Checking...")
        self.output_status = tk.StringVar(value="Checking...")
        
        ttk.Label(status_frame, text="Input (danhsachisbn.xlsx):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.input_label = ttk.Label(status_frame, textvariable=self.input_status, font=("Arial", 10, "bold"))
        self.input_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(status_frame, text="Output (output.xlsx):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.output_label = ttk.Label(status_frame, textvariable=self.output_status, font=("Arial", 10, "bold"))
        self.output_label.grid(row=1, column=1, sticky=tk.W, padx=10)
        
        # Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text=" Chế độ tìm kiếm ", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_mode = tk.StringVar(value="foreign")
        ttk.Radiobutton(mode_frame, text="Sách nước ngoài (Amazon/Google/OL)", variable=self.search_mode, value="foreign").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Sách tiếng Việt (Amazon/Fahasa)", variable=self.search_mode, value="vietnamese").pack(side=tk.LEFT, padx=10)
        
        # Terminal-like Log Area
        log_frame = ttk.LabelFrame(main_frame, text=" Execution Log ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, font=("Courier New", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_configure("info", foreground="#d4d4d4")
        self.log_area.tag_configure("error", foreground="#f44336")
        self.log_area.tag_configure("success", foreground="#4caf50")
        
        # Progress Section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.percent_label = ttk.Label(progress_frame, text="0%", width=5)
        self.percent_label.pack(side=tk.RIGHT)
        
        # Control Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        self.run_btn = ttk.Button(btn_frame, text="RUN SCRAPER", command=self.start_scraping)
        self.run_btn.pack(side=tk.RIGHT)
        
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh Status", command=self.check_files)
        self.refresh_btn.pack(side=tk.LEFT)
        
        # Initial Check
        self.check_files()
        self.log("Ready to start. Click RUN SCRAPER to begin.")

    def log(self, message, tag="info"):
        self.log_area.insert(tk.END, f"{message}\n", tag)
        self.log_area.see(tk.END)

    def check_files(self):
        input_exists = os.path.exists(INPUT_FILE)
        output_exists = os.path.exists(OUTPUT_FILE)
        
        can_run = False
        if input_exists:
            try:
                df = pd.read_excel(INPUT_FILE)
                count = len(df)
                if df.empty:
                    self.input_status.set("FILE EMPTY")
                    self.input_label.configure(foreground="orange")
                elif count > 1000:
                    self.input_status.set(f"TOO MANY ITEMS ({count} > 1000)")
                    self.input_label.configure(foreground="red")
                    messagebox.showwarning("Limit Exceeded", f"Dánh sách có {count} mã ISBN. Vui lòng xóa bớt để còn tối đa 1000 mã.")
                else:
                    self.input_status.set(f"OK ({count} items found)")
                    self.input_label.configure(foreground="green")
                    can_run = True
            except Exception as e:
                self.input_status.set(f"ERROR READING: {e}")
                self.input_label.configure(foreground="red")
        else:
            self.input_status.set("NOT FOUND")
            self.input_label.configure(foreground="red")
            
        if output_exists:
            try:
                df = pd.read_excel(OUTPUT_FILE)
                self.output_status.set(f"EXISTING ({len(df)} records)")
                self.output_label.configure(foreground="blue")
            except:
                self.output_status.set("ERROR READING")
                self.output_label.configure(foreground="red")
        else:
            self.output_status.set("NEW FILE WILL BE CREATED")
            self.output_label.configure(foreground="green")
            
        # Disable Run if no input or too many items
        if can_run:
            self.run_btn.state(['!disabled'])
        else:
            self.run_btn.state(['disabled'])

    def update_progress(self, val):
        self.progress_bar['value'] = val
        self.percent_label.config(text=f"{val}%")
        self.root.update_idletasks()

    def start_scraping(self):
        self.run_btn.state(['disabled'])
        self.refresh_btn.state(['disabled'])
        self.log_area.delete(1.0, tk.END)
        self.log("Starting scraper...", "success")
        
        # Start in separate thread to prevent GUI freeze
        thread = threading.Thread(target=self.run_logic)
        thread.daemon = True
        thread.start()

    def run_logic(self):
        try:
            mode = self.search_mode.get()
            run_scraper(
                mode=mode,
                progress_callback=self.update_progress,
                log_callback=lambda m: self.root.after(0, self.log, m)
            )
            self.root.after(0, lambda: messagebox.showinfo("Done", "Scraping completed successfully!"))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, self.log, f"CRITICAL ERROR: {err_msg}", "error")
            self.root.after(0, lambda m=err_msg: messagebox.showerror("Error", f"An unexpected error occurred:\n{m}"))
        finally:
            self.root.after(0, lambda: self.run_btn.state(['!disabled']))
            self.root.after(0, lambda: self.refresh_btn.state(['!disabled']))
            self.root.after(0, self.check_files)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()

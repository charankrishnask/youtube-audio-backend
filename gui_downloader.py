import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from downloader_core import download_audio_from_youtube
import os
from tkinter import font as tkfont

class YouTubeAudioDownloaderGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader Pro")
        self.root.geometry("700x600")
        self.root.configure(bg='#f0f0f0')
        self.root.resizable(True, True)
        
        # Custom fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.label_font = tkfont.Font(family="Segoe UI", size=10)
        self.button_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        
        # Colors
        self.primary_color = "#2E86AB"
        self.secondary_color = "#A23B72"
        self.success_color = "#28a745"
        self.warning_color = "#ffc107"
        self.danger_color = "#dc3545"
        
        # Remove the default download directory - user will choose each time
        self.is_downloading = False
        self.current_progress = 0

        self.setup_ui()

    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header Section
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            header_frame, 
            text="🎵 YouTube Audio Downloader", 
            font=self.title_font,
            foreground=self.primary_color
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            header_frame,
            text="Download high-quality audio from YouTube videos",
            font=self.label_font,
            foreground="#666"
        )
        subtitle_label.pack(pady=(5, 0))

        # Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Download Settings", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # URL Input
        url_frame = ttk.Frame(input_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(url_frame, text="YouTube URL:", font=self.label_font).pack(anchor=tk.W)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(
            url_frame, 
            textvariable=self.url_var, 
            width=60,
            font=self.label_font
        )
        self.url_entry.pack(fill=tk.X, pady=(5, 0))
        self.url_entry.bind('<Return>', lambda e: self.start_download())

        # Options Frame
        options_frame = ttk.Frame(input_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left options
        left_options = ttk.Frame(options_frame)
        left_options.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.mp3_var = tk.BooleanVar(value=True)
        mp3_check = ttk.Checkbutton(
            left_options, 
            text="Convert to MP3 (320kbps High Quality)", 
            variable=self.mp3_var
        )
        mp3_check.pack(anchor=tk.W)
        
        # Right options
        right_options = ttk.Frame(options_frame)
        right_options.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        self.keep_original_var = tk.BooleanVar(value=False)
        keep_original_check = ttk.Checkbutton(
            right_options, 
            text="Keep Original Audio File", 
            variable=self.keep_original_var
        )
        keep_original_check.pack(anchor=tk.W)

        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", padding="15")
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Progress labels
        self.progress_text = tk.StringVar(value="Ready to download")
        progress_label = ttk.Label(
            progress_frame, 
            textvariable=self.progress_text,
            font=self.label_font
        )
        progress_label.pack(anchor=tk.W)

        # Download Button
        self.download_btn = ttk.Button(
            main_frame,
            text="🚀 Download Audio",
            command=self.start_download
        )
        self.download_btn.pack(fill=tk.X, pady=(0, 15))

        # Results Section
        results_frame = ttk.LabelFrame(main_frame, text="Download Results", padding="15")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Log box with scrollbar
        log_frame = ttk.Frame(results_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Create scrollbar for log box
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_box = tk.Text(
            log_frame,
            height=12,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            bg='#f8f9fa',
            relief='flat',
            padx=10,
            pady=10
        )
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_box.yview)

        # Action buttons frame
        action_frame = ttk.Frame(results_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        self.open_file_btn = ttk.Button(
            action_frame,
            text="📁 Open Download Location",
            command=self.open_download_location,
            state=tk.DISABLED
        )
        self.open_file_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_log_btn = ttk.Button(
            action_frame,
            text="🗑️ Clear Log",
            command=self.clear_log
        )
        self.clear_log_btn.pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Segoe UI", 8)
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # Configure styles for modern look
        self.configure_styles()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        style.configure("TFrame", background='#f0f0f0')
        style.configure("TLabel", background='#f0f0f0')
        style.configure("TLabelframe", background='#f0f0f0')
        style.configure("TLabelframe.Label", background='#f0f0f0', font=self.label_font)

    def choose_download_location(self):
        """Ask user where to save the downloaded file"""
        download_dir = filedialog.askdirectory(
            title="Select Download Location",
            mustexist=True
        )
        return download_dir

    def open_download_location(self):
        if hasattr(self, 'last_download_path') and self.last_download_path:
            folder_path = os.path.dirname(self.last_download_path)
            if os.path.exists(folder_path):
                os.startfile(folder_path)
            else:
                messagebox.showerror("Error", "Download location no longer exists.")
        else:
            messagebox.showinfo("Info", "No download location available.")

    def clear_log(self):
        self.log_box.delete(1.0, tk.END)
        self.write_log("Log cleared. Ready for new download.", "info")

    def write_log(self, msg, msg_type="info"):
        """Write message to log with colored formatting"""
        colors = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red",
            "progress": "blue"
        }
        
        color = colors.get(msg_type, "black")
        
        self.log_box.insert(tk.END, msg + "\n", msg_type)
        self.log_box.tag_configure(msg_type, foreground=color)
        self.log_box.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, percent, status_text):
        """Update progress bar and status text"""
        self.progress_var.set(percent)
        self.progress_text.set(status_text)
        self.status_var.set(f"Downloading... {percent}%")
        self.root.update_idletasks()

    def display_results(self, result, download_dir):
        """Display download results in user-friendly format"""
        self.write_log("\n" + "="*50, "success")
        self.write_log("🎉 DOWNLOAD COMPLETED SUCCESSFULLY", "success")
        self.write_log("="*50, "success")
        
        if result.get("status") == "success":
            self.write_log(f"📺 Title: {result.get('title', 'Unknown')}", "success")
            self.write_log(f"📁 Saved to: {download_dir}", "info")
            self.write_log("", "success")
            
            # Show file information
            files = result.get("files", [])
            for file_info in files:
                emoji = "🎵" if file_info['type'] == 'mp3' else "📄"
                self.write_log(f"{emoji} {file_info['type'].upper()}: {file_info['name']}", "success")
                self.write_log(f"   📏 Size: {file_info['size']}", "info")
                self.write_log(f"   🏷️  Format: {file_info['format']}", "info")
                self.write_log("", "info")
                
                # Store the last downloaded file path
                if file_info['type'] in ['mp3', 'original']:
                    self.last_download_path = os.path.join(download_dir, file_info['name'])
            
            # Enable the open file button
            self.open_file_btn.config(state=tk.NORMAL)
            
        else:
            self.write_log("❌ Download failed", "error")

    def start_download(self):
        # Prevent multiple simultaneous downloads
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress.")
            return
            
        url = self.url_var.get().strip()

        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            self.url_entry.focus()
            return

        # Validate URL format
        if "youtube.com" not in url and "youtu.be" not in url:
            if messagebox.askyesno("Confirm", "This doesn't look like a YouTube URL. Continue anyway?"):
                pass
            else:
                return

        # Ask user where to save the file
        download_dir = self.choose_download_location()
        if not download_dir:
            # User cancelled the folder selection
            self.write_log("❌ Download cancelled - no location selected", "warning")
            return

        # Set downloading state
        self.is_downloading = True
        
        # Reset UI state
        self.download_btn.config(state=tk.DISABLED, text="⏳ Downloading...")
        self.open_file_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_text.set("Starting download...")
        self.status_var.set("Downloading...")
        self.last_download_path = None
        
        self.write_log("\n🔄 Starting download process...", "progress")
        self.write_log(f"📁 Download location: {download_dir}", "info")
        self.write_log(f"🔧 MP3 Conversion: {'Yes' if self.mp3_var.get() else 'No'}", "info")
        self.write_log(f"💾 Keep Original: {'Yes' if self.keep_original_var.get() else 'No'}", "info")

        # Start download in separate thread
        t = threading.Thread(
            target=self.download_thread,
            args=(url, download_dir),
            daemon=True
        )
        t.start()

    def download_thread(self, url, download_dir):
        try:
            # Simulate progress updates (you can replace this with actual progress from yt-dlp)
            def progress_callback(progress_data):
                if progress_data.get("status") == "downloading":
                    percent = progress_data.get("_percent_str", "0%").replace("%", "")
                    try:
                        percent_value = float(percent)
                        self.root.after(0, self.update_progress, percent_value, f"Downloading... {percent}%")
                    except:
                        pass

            result = download_audio_from_youtube(
                url,
                output_dir=download_dir,
                convert_to_mp3=self.mp3_var.get(),
                keep_original=self.keep_original_var.get(),
                progress_hook=progress_callback
            )
            
            # Update UI in main thread
            self.root.after(0, self.on_download_complete, result, url, download_dir)
            
        except Exception as e:
            # Update UI in main thread
            self.root.after(0, self.on_download_error, str(e))

    def on_download_complete(self, result, original_url, download_dir):
        """Called in main thread when download completes successfully"""
        self.progress_var.set(100)
        self.progress_text.set("Download completed!")
        self.status_var.set("Download completed successfully")
        
        self.display_results(result, download_dir)
        
        # Clear the URL input field
        self.url_var.set("")
        
        # Reset download state
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="🚀 Download Audio")
        
        self.write_log("✅ URL field cleared. Ready for next download.", "success")
        self.write_log("💡 Tip: Paste a new YouTube URL and click Download Audio to start another download.", "info")

    def on_download_error(self, error_message):
        """Called in main thread when download fails"""
        self.progress_var.set(0)
        self.progress_text.set("Download failed")
        self.status_var.set("Download failed")
        
        self.write_log(f"❌ Error: {error_message}", "error")
        
        # Reset download state but don't clear URL (user might want to retry)
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="🚀 Download Audio")
        
        self.write_log("🔧 Please check the URL and try again.", "warning")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeAudioDownloaderGUI(root)
    root.mainloop()
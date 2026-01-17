import customtkinter as ctk
import uuid
from datetime import datetime
import threading
import json
import os
from agent import CompatibleAgent
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")
class SessionManager:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)
    
    def list_sessions(self):
        sessions = []
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                session_path = os.path.join(self.sessions_dir, filename)
                try:
                    with open(session_path, 'r') as f:
                        data = json.load(f)
                    sessions.append({
                        'id': filename[:-5],
                        'name': data.get('name', 'Unnamed Session'),
                        'timestamp': data.get('timestamp', ''),
                        'message_count': len(data.get('messages', []))
                    })
                except:
                    continue
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
    
    def save_session(self, session_id: str, chat_history, session_name: str = None):
        if not session_name:
            session_name = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        session_data = {
            'name': session_name,
            'timestamp': datetime.now().isoformat(),
            'messages': chat_history
        }
        
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return filepath
    
    def load_session(self, session_id: str):
        """Load a saved session"""
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data.get('messages', [])
        except:
            return []

class LibraryDeskGUI:
    def __init__(self, master):
        self.master = master
        master.title("AI Library Desk Agent")
        master.geometry("1200x700")
        
        # Initialize session manager
        self.session_manager = SessionManager()
        
        # Initialize agent
        self.current_session_id = str(uuid.uuid4())
        self.agent = CompatibleAgent(session_id=self.current_session_id)
        self.current_session_name = "New Session"
        
        # Setup GUI
        self.setup_gui()
        
        # Show agent status
    
    def setup_gui(self):
        """Setup the GUI layout"""
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self.master, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_propagate(False)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.sidebar,
            text="📚 Library Desk",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(20, 10), padx=20)
        
        # Session Controls
        self.session_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.session_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.new_session_btn = ctk.CTkButton(
            self.session_frame,
            text="🆕 New Session",
            command=self.new_session,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.new_session_btn.pack(fill="x", pady=(0, 5))
        
        self.save_session_btn = ctk.CTkButton(
            self.session_frame,
            text="💾 Save Session",
            command=self.save_current_session,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.save_session_btn.pack(fill="x", pady=5)
        
        # Session List
        self.session_list_label = ctk.CTkLabel(
            self.sidebar,
            text="📁 Saved Sessions",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.session_list_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.session_listbox = ctk.CTkScrollableFrame(self.sidebar, height=300)
        self.session_listbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Status
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=20)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="✅ Agent Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack()
        
        # ========== Main Chat Area ==========
        self.main_frame = ctk.CTkFrame(self.master, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Chat Header
        self.header_frame = ctk.CTkFrame(self.main_frame, height=60, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.session_title = ctk.CTkLabel(
            self.header_frame,
            text="New Session",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.session_title.grid(row=0, column=0, sticky="w")
        
        self.clear_chat_btn = ctk.CTkButton(
            self.header_frame,
            text="Clear Chat",
            command=self.clear_chat,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12)
        )
        self.clear_chat_btn.grid(row=0, column=1, sticky="e")
        
        # Chat Display
        self.chat_display = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.chat_display.grid_columnconfigure(0, weight=1)
        
        # Input Area
        self.input_frame = ctk.CTkFrame(self.main_frame, height=80, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.user_input = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Type your message to the library assistant...",
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.user_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.user_input.bind("<Return>", self.send_message)
        
        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self.send_message,
            width=100,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.send_btn.grid(row=0, column=1)
        
        # Initialize
        self.load_sessions_list()
        self.display_welcome()
    
    def show_warning(self, message):
        """Show a warning message"""
        warning_frame = ctk.CTkFrame(self.chat_display, corner_radius=10, fg_color="#8B4513")
        warning_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 10))
        
        warning_label = ctk.CTkLabel(
            warning_frame,
            text=f"⚠️ {message}",
            font=ctk.CTkFont(size=12),
            wraplength=800
        )
        warning_label.pack(padx=20, pady=15)
    
    def display_welcome(self):
        welcome_msg = """🤖 Welcome to AI Library Desk Assistant!

I can help you with:
• 📚 Finding books by title or author
• 🛒 Creating orders for customers
• 📦 Checking inventory levels
• 🔄 Restocking books
• 📊 Checking order status
• 💰 Updating book prices

Try asking:
"Find books about Python"
"Create an order for Clean Code for customer 1"
"Check inventory status"
"What's the status of order 1?"""
        
        self.add_message("assistant", welcome_msg, is_welcome=True)
    
    def add_message(self, sender, message, is_welcome=False):
        """Add a message to the chat display"""
        # Create message frame
        msg_frame = ctk.CTkFrame(
            self.chat_display,
            corner_radius=15,
            fg_color=("#2B2B2B" if sender == "assistant" else "#1F538D")
        )
        
        # Configure grid
        msg_frame.grid_columnconfigure(1, weight=1)
        
        # Avatar
        avatar_text = "🤖" if sender == "assistant" else "👤"
        avatar = ctk.CTkLabel(
            msg_frame,
            text=avatar_text,
            font=ctk.CTkFont(size=40),
            width=40
        )
        avatar.grid(row=0, column=0, sticky="nw", padx=40, pady=(15, 5))
        
        # Message text
        msg_text = ctk.CTkTextbox(
            msg_frame,
            wrap="word",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=0,
        )
        msg_text.grid(row=0, column=1, sticky="ew", padx=(40, 15), pady=(15, 15), ipady=5)
        
        # Insert text
        msg_text.insert("1.0", message)
        msg_text.configure(state="disabled")
        lines = message.count('\n') + 1
        
        # Set dynamic height: 30 pixels per line, no maximum limit
        # Add extra pixels for padding and readability
        height = max(4, lines) * 30
        
        # Apply the height
        msg_text.configure(height=height)
        
        # Time stamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = ctk.CTkLabel(
            msg_frame,
            text=timestamp,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        time_label.grid(row=1, column=1, sticky="e", padx=(0, 15), pady=(0, 10))
        
        # Add to chat display
        msg_frame.grid(row=self.chat_display.grid_size()[1], column=0, sticky="ew", padx=(0, 5), pady=(0, 10))
        msg_frame.grid_columnconfigure(1, weight=1)
    
    def send_message(self, event=None):
        """Send user message"""
        user_msg = self.user_input.get().strip()
        if not user_msg:
            return
        
        # Clear input
        self.user_input.delete(0, "end")
        
        # Add user message
        self.add_message("user", user_msg)
        
        # Disable input during processing
        self.user_input.configure(state="disabled")
        self.send_btn.configure(state="disabled")
        self.status_label.configure(text="🔄 Processing...")
        
        # Process in background
        thread = threading.Thread(target=self.process_message, args=(user_msg,))
        thread.daemon = True
        thread.start()
    
    def process_message(self, user_msg):
        """Process message in background thread"""
        try:
            response = self.agent.run(user_msg)
            self.master.after(0, self.display_response, response)
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.master.after(0, self.display_response, error_msg)
    
    def display_response(self, response):
        """Display agent response"""
        self.add_message("assistant", response)
        
        # Re-enable input
        self.user_input.configure(state="normal")
        self.send_btn.configure(state="normal")
        self.status_label.configure(text="✅ Agent Ready")
        
        # Scroll to bottom
        self.chat_display._parent_canvas.yview_moveto(1.0)
    
    def new_session(self):
        """Create new session"""
        self.current_session_id = str(uuid.uuid4())
        self.current_session_name = f"Session {datetime.now().strftime('%H:%M')}"
        self.session_title.configure(text=self.current_session_name)
        
        # Create new agent
        self.agent = CompatibleAgent(session_id=self.current_session_id)
        
        # Clear chat display
        for widget in self.chat_display.winfo_children():
            widget.destroy()
        
        self.display_welcome()
        self.status_label.configure(text="New Session Started")
    
    def save_current_session(self):
        """Save current session"""
        chat_history = self.agent.get_chat_history()
        
        # Ask for session name
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this session:",
            title="Save Session"
        )
        session_name = dialog.get_input()
        
        if session_name:
            self.current_session_name = session_name
            self.session_title.configure(text=session_name)
            
            # Save session
            self.session_manager.save_session(
                self.current_session_id,
                chat_history,
                session_name
            )
            
            # Update session list
            self.load_sessions_list()
            self.status_label.configure(text="💾 Session Saved")
    
    def load_sessions_list(self):
        """Load saved sessions list"""
        # Clear current list
        for widget in self.session_listbox.winfo_children():
            widget.destroy()
        
        # Get sessions
        sessions = self.session_manager.list_sessions()
        
        if not sessions:
            empty_label = ctk.CTkLabel(
                self.session_listbox,
                text="No saved sessions yet",
                text_color="gray",
                font=ctk.CTkFont(size=12)
            )
            empty_label.pack(pady=20)
            return
        
        # Add session buttons
        for session in sessions:
            session_btn = ctk.CTkButton(
                self.session_listbox,
                text=f"{session['name']}\n({session['message_count']} messages)",
                command=lambda s=session: self.load_session(s['id']),
                height=50,
                font=ctk.CTkFont(size=12),
                anchor="w",
                fg_color="transparent",
                hover_color="#2B2B2B"
            )
            session_btn.pack(fill="x", pady=2, padx=5)
    
    def load_session(self, session_id):
        """Load a saved session"""
        # Load messages
        messages = self.session_manager.load_session(session_id)
        if not messages:
            return
        
        # Update current session
        self.current_session_id = session_id
        sessions = self.session_manager.list_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session:
            self.current_session_name = session['name']
            self.session_title.configure(text=session['name'])
        
        # Clear chat display
        for widget in self.chat_display.winfo_children():
            widget.destroy()
        
        # Load messages
        for msg in messages:
            if msg['role'] == 'user':
                self.add_message("user", msg['content'])
            elif msg['role'] == 'assistant':
                self.add_message("assistant", msg['content'])
        
        # Update agent chat history
        self.agent.chat_history = messages.copy()
        self.status_label.configure(text=f"📂 Loaded: {self.current_session_name}")
    
    def clear_chat(self):
        """Clear current chat"""
        for widget in self.chat_display.winfo_children():
            widget.destroy()
        
        self.agent.reset_chat()
        self.display_welcome()
        self.status_label.configure(text="🗑️ Chat Cleared")

# Run the application
if __name__ == "__main__":
    root = ctk.CTk()
    app = LibraryDeskGUI(root)
    root.mainloop()
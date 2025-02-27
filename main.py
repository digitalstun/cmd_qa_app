import os
import streamlit as st
# Must be the first Streamlit command
st.set_page_config(
    page_title="Windows Command Helper",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on small screens
)

import google.generativeai as genai
import re
from dotenv import load_dotenv
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import random
import time
import webbrowser
from pathlib import Path

# Try to import winrm, but don't fail if it's not available
WINRM_AVAILABLE = False
try:
    import winrm
    WINRM_AVAILABLE = True
except ImportError:
    pass

# Load environment variables from .env file if it exists
load_dotenv()

# Get API key from environment variable or Streamlit secrets
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("No API key found. Please set GEMINI_API_KEY in environment variables or .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"Error accessing API key: {str(e)}")
    st.stop()

# Configure Gemini API key
genai.configure(api_key=api_key)

# Model configuration
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 512,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

# Network command templates and security patterns
NETWORK_COMMAND_TEMPLATES = {
    "ip_config": "ipconfig /all",
    "port_scan": "Test-NetConnection -ComputerName {target} -Port {port}",
    "dns_check": "Resolve-DnsName {hostname}",
    "traceroute": "tracert {target}"
}

SAFE_INPUT_REGEX = r"^[a-zA-Z0-9\-\.\:\/\s]{1,100}$"

# Add at the top with other constants
TROUBLESHOOTING_CATEGORIES = {
    "Network": {
        "Connectivity": ["ping", "tracert", "nslookup", "ipconfig", "netstat"],
        "WiFi": ["netsh wlan show", "netsh wlan connect", "netsh wlan disconnect"],
        "DNS": ["ipconfig /flushdns", "nslookup", "dig"],
        "Firewall": ["netsh advfirewall", "Get-NetFirewallRule"],
    },
    "System": {
        "Performance": ["tasklist", "perfmon", "systeminfo"],
        "Services": ["services.msc", "net start", "net stop"],
        "Updates": ["wuauclt", "UsoClient"],
        "Logs": ["eventvwr.msc", "Get-EventLog", "Get-WinEvent"],
    },
    "Storage": {
        "Disk": ["chkdsk", "diskpart", "defrag"],
        "File System": ["sfc /scannow", "DISM.exe"],
        "Permissions": ["icacls", "takeown"],
    },
    "Security": {
        "Malware": ["MRT.exe", "Windows Defender commands"],
        "Accounts": ["net user", "net localgroup"],
        "Auditing": ["auditpol", "secpol.msc"],
    }
}

# Add this near the top of your main.py file
st.markdown("""
<style>
    .diagnostic-tool {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .command-history-entry {
        border-left: 3px solid #0E1117;
        padding-left: 10px;
        margin: 10px 0;
    }
    .tool-category {
        font-weight: bold;
        color: #00FF00;
    }
    .copy-tooltip {
        display: inline-block;
        margin-left: 10px;
        padding: 5px;
        background: #2E7D32;
        border-radius: 4px;
    }
    .custom-container {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .app-header {
        text-align: center;
        padding: 1rem;
        margin-bottom: 2rem;
    }
    .app-title {
        font-size: 2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def get_gemini_response(question):
    try:
        # Validate input for network commands
        if not re.match(SAFE_INPUT_REGEX, question):
            return {"command": None, "explanation": "Invalid input detected. Only alphanumeric characters and common network symbols allowed."}
            
        chat_session = model.start_chat()
        
        # Enhanced prompt with network command context
        modified_question = f"""For Windows network/IP commands: {question}
        - Prioritize PowerShell over CMD
        - Include security warnings for dangerous commands
        - Suggest alternative GUI tools where applicable
        Format: [Command]\n[Explanation]\n[Security Note]\n[Alternatives]"""
        
        response = chat_session.send_message(modified_question)
        text = response.text
        
        # Enhanced parsing for network commands
        match = re.search(
            r"^((?:[A-Za-z0-9\-_]+\.exe\s)?[^\n`]+)(?:\n+)(.*?)(?:\n+Security Note:\s*(.*?))?(?:\n+Alternatives:\s*(.*))?$",
            text.lstrip(),
            re.DOTALL
        )
        if match:
            command = match.group(1).strip()
            explanation = match.group(2).strip()
            # Clean any remaining backticks from the command
            command = command.replace('`', '').strip()
            return {"command": command, "explanation": explanation}
        else:
            return {"command": None, "explanation": "Could not extract command from response."}
    except Exception as e:
        return {"command": None, "explanation": f"Error: {e}"}

def create_sidebar_menu():
    with st.sidebar:
        st.header("🔧 Troubleshooting Tools")
        
        selected_category = st.selectbox(
            "Select Category",
            list(TROUBLESHOOTING_CATEGORIES.keys())
        )
        
        if selected_category:
            selected_subcategory = st.selectbox(
                "Select Tool Type",
                list(TROUBLESHOOTING_CATEGORIES[selected_category].keys())
            )
            
            if selected_subcategory:
                commands = TROUBLESHOOTING_CATEGORIES[selected_category][selected_subcategory]
                selected_command = st.selectbox(
                    "Common Commands",
                    commands
                )
                
                if selected_command:
                    st.session_state.question_input = f"Explain how to use {selected_command} command"

def save_command_history(command, explanation):
    if 'command_history' not in st.session_state:
        st.session_state.command_history = []
    
    st.session_state.command_history.append({
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'command': command,
        'explanation': explanation
    })

# Add this function to show command history
def show_command_history():
    if 'command_history' not in st.session_state:
        st.session_state.command_history = []
    
    st.subheader("📜 Command History")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        if st.session_state.command_history:
            for entry in reversed(st.session_state.command_history):
                with st.expander(f"{entry['timestamp']} - {entry['command'][:40]}..."):
                    st.code(entry['command'], language="batch")
                    st.write(entry['explanation'])
        else:
            st.info("No commands in history yet. Try running some commands!")
    
    with col2:
        if st.session_state.command_history:
            if st.button("Export History"):
                history_text = "\n\n".join([
                    f"Time: {entry['timestamp']}\nCommand: {entry['command']}\nExplanation: {entry['explanation']}"
                    for entry in st.session_state.command_history
                ])
                st.download_button(
                    "Download History",
                    history_text,
                    "command_history.txt",
                    "text/plain"
                )
            if st.button("Clear History"):
                st.session_state.command_history = []
                st.experimental_rerun()

def generate_diagnostic_commands():
    return {
        "System Info": "systeminfo",
        "Network Status": "ipconfig /all && netstat -ano",
        "Disk Space": "wmic logicaldisk get size,freespace,caption",
        "Running Services": "net start",
        "Windows Updates": "wmic qfe list brief",
        "Event Logs": "wevtutil qe System /c:5 /f:text",
        "Memory Usage": "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value",
        "CPU Info": "wmic cpu get name,numberofcores,maxclockspeed",
    }

def create_diagnostic_report():
    st.subheader("🔍 System Diagnostic Report")
    
    diagnostic_commands = generate_diagnostic_commands()
    selected_diagnostics = st.multiselect(
        "Select Diagnostic Tools to Run",
        list(diagnostic_commands.keys())
    )
    
    if st.button("Generate Diagnostic Report"):
        with st.spinner("Generating diagnostic commands..."):
            st.markdown("### 📊 Diagnostic Commands")
            for diagnostic in selected_diagnostics:
                with st.expander(diagnostic):
                    st.code(diagnostic_commands[diagnostic], language="batch")
                    st.markdown("Copy and run these commands in PowerShell/CMD to generate the diagnostic information.")

def create_remote_management_tab():
    st.subheader("🌐 Remote Management")
    
    if not WINRM_AVAILABLE:
        st.warning("""
        Remote Management features require the pywinrm package. 
        To enable this feature, install it using:
        ```
        pip install pywinrm
        ```
        """)
        return
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        remote_host = st.text_input(
            "Remote Host",
            key="remote_host",
            help="Enter the hostname or IP address"
        )
        username = st.text_input(
            "Username",
            key="remote_username",
            help="Enter the remote system username"
        )
        password = st.text_input(
            "Password",
            type="password",
            key="remote_password",
            help="Enter the remote system password"
        )
        
    with col2:
        remote_commands = {
            "System Health": "Get-ComputerInfo | Select-Object WindowsVersion,OsHardwareAbstractionLayer,OsArchitecture",
            "Disk Space": "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace",
            "Running Services": "Get-Service | Where-Object {$_.Status -eq 'Running'}",
            "Active Users": "Get-WmiObject -Class Win32_ComputerSystem | Select-Object UserName",
            "Network Connections": "Get-NetTCPConnection | Where-Object State -eq 'Established'"
        }
        
        selected_command = st.selectbox("Select Remote Command", list(remote_commands.keys()))
        
        if st.button("Execute Remote Command"):
            try:
                session = winrm.Session(remote_host, auth=(username, password))
                result = session.run_ps(remote_commands[selected_command])
                st.code(result.std_out.decode())
            except Exception as e:
                st.error(f"Remote execution failed: {str(e)}")

def create_ad_management():
    st.subheader("👥 Active Directory Management")
    
    ad_operations = {
        "User Management": {
            "List Users": "Get-ADUser -Filter * | Select-Object Name,Enabled,LastLogonDate",
            "Locked Accounts": "Search-ADAccount -LockedOut | Select-Object Name,LastLogonDate",
            "Disabled Accounts": "Search-ADAccount -AccountDisabled | Select-Object Name"
        },
        "Group Management": {
            "List Groups": "Get-ADGroup -Filter * | Select-Object Name,GroupCategory",
            "Group Members": "Get-ADGroupMember -Identity '{group}' | Select-Object Name"
        },
        "Computer Management": {
            "List Computers": "Get-ADComputer -Filter * | Select-Object Name,Enabled",
            "Stale Computers": "Get-ADComputer -Filter {LastLogonDate -lt (Get-Date).AddDays(-90)}"
        }
    }
    
    category = st.selectbox("Select AD Category", list(ad_operations.keys()))
    operation = st.selectbox("Select Operation", list(ad_operations[category].keys()))
    
    if category == "Group Management" and "group" in ad_operations[category][operation]:
        group_name = st.text_input("Enter Group Name")
        command = ad_operations[category][operation].format(group=group_name)
    else:
        command = ad_operations[category][operation]
    
    if st.button("Execute AD Command"):
        st.code(command, language="powershell")

def create_network_topology():
    st.subheader("🌐 Network Topology Visualizer")
    
    discovery_commands = {
        "ARP Table": "arp -a",
        "Network Interfaces": "Get-NetAdapter | Select-Object Name,Status,LinkSpeed",
        "IP Configuration": "Get-NetIPConfiguration | Select-Object InterfaceAlias,IPv4Address",
        "Routing Table": "Get-NetRoute | Select-Object DestinationPrefix,NextHop,RouteMetric"
    }
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown("### Network Discovery Commands")
        for name, command in discovery_commands.items():
            with st.expander(name):
                st.code(command, language="powershell")
                if st.button(f"Copy {name} Command", key=f"copy_{name}"):
                    st.success("Command copied!")
    
    with col2:
        st.markdown("### Network Visualization")
        if st.button("Generate Network Map"):
            try:
                G = nx.Graph()
                
                # Add example network structure
                G.add_node("Local PC", type="computer")
                G.add_node("Gateway", type="router")
                G.add_node("Internet", type="cloud")
                G.add_edge("Local PC", "Gateway")
                G.add_edge("Gateway", "Internet")
                
                plt.figure(figsize=(10, 8))
                pos = nx.spring_layout(G)
                nx.draw(G, pos, with_labels=True, 
                       node_color='lightblue',
                       node_size=2000, 
                       font_size=10, 
                       font_weight='bold')
                
                st.pyplot(plt)
                plt.close()
            except Exception as e:
                st.error(f"Error generating network map: {str(e)}")

def create_system_monitor():
    st.subheader("📊 System Health Monitor")
    
    monitor_commands = {
        "CPU Usage": "Get-Counter '\\Processor(_Total)\\% Processor Time'",
        "Memory Usage": "Get-Counter '\\Memory\\Available MBytes'",
        "Disk IO": "Get-Counter '\\PhysicalDisk(_Total)\\Disk Reads/sec'",
        "Network": "Get-Counter '\\Network Interface(*)\\Bytes Total/sec'"
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        refresh_rate = st.slider("Refresh Rate (seconds)", 1, 60, 5)
        selected_metrics = st.multiselect("Select Metrics", list(monitor_commands.keys()))
    
    with col2:
        if 'monitoring' not in st.session_state:
            st.session_state.monitoring = False
            
        if st.button("Start Monitoring" if not st.session_state.monitoring else "Stop Monitoring"):
            st.session_state.monitoring = not st.session_state.monitoring
    
    placeholder = st.empty()
    
    if st.session_state.monitoring and selected_metrics:
        try:
            metrics_data = {}
            for metric in selected_metrics:
                # Simulate metric collection
                metrics_data[metric] = random.random() * 100
            
            with placeholder.container():
                cols = st.columns(len(metrics_data))
                for i, (metric, value) in enumerate(metrics_data.items()):
                    with cols[i]:
                        st.metric(metric, f"{value:.2f}%")
                        st.code(monitor_commands[metric], language="powershell")
            
            time.sleep(refresh_rate)
        except Exception as e:
            st.error(f"Monitoring error: {str(e)}")
            st.session_state.monitoring = False

def create_help_system():
    st.sidebar.markdown("---")
    st.sidebar.header("📚 Documentation")
    
    help_sections = {
        "Getting Started": "getting-started",
        "Command Assistant": "command-assistant",
        "Diagnostic Tools": "diagnostic-report",
        "Remote Management": "remote-management",
        "AD Management": "active-directory-management",
        "Network Tools": "network-topology",
        "System Monitor": "system-monitor",
        "Security Best Practices": "security-notes",
        "Troubleshooting": "troubleshooting"
    }
    
    selected_section = st.sidebar.selectbox(
        "Help Topics",
        list(help_sections.keys())
    )
    
    if selected_section:
        section_id = help_sections[selected_section]
        docs_path = Path("docs/user_guide.md")
        
        if st.sidebar.button("Open Documentation"):
            if docs_path.exists():
                with docs_path.open() as f:
                    content = f.read()
                    st.sidebar.markdown(content)
            else:
                st.sidebar.error("Documentation file not found!")

def add_command_favorites():
    if 'favorites' not in st.session_state:
        st.session_state.favorites = []
    
    def add_to_favorites(command, explanation):
        if command not in [f['command'] for f in st.session_state.favorites]:
            st.session_state.favorites.append({
                'command': command,
                'explanation': explanation,
                'added_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    def show_favorites():
        if st.session_state.favorites:
            for fav in st.session_state.favorites:
                with st.expander(f"⭐ {fav['command'][:40]}..."):
                    st.code(fav['command'], language="batch")
                    st.write(fav['explanation'])
                    if st.button("Remove", key=f"remove_{fav['command'][:20]}"):
                        st.session_state.favorites.remove(fav)
                        st.experimental_rerun()
        else:
            st.info("No favorite commands yet!")
    
    return add_to_favorites, show_favorites

def create_command_search():
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Command Search")
    
    search_term = st.sidebar.text_input(
        label="Search Commands",
        key="command_search",
        help="Enter keywords to search commands",
        placeholder="Search commands..."
    )

def create_troubleshooting_workflow():
    st.header("🔄 Automated Troubleshooting")
    
    workflows = {
        "Network Connectivity": [
            {"command": "ipconfig /all", "description": "Check network configuration"},
            {"command": "ping 8.8.8.8", "description": "Test internet connectivity"},
            {"command": "nslookup google.com", "description": "Test DNS resolution"},
            {"command": "tracert 8.8.8.8", "description": "Check network path"}
        ],
        "System Performance": [
            {"command": "tasklist", "description": "List running processes"},
            {"command": "wmic cpu get loadpercentage", "description": "Check CPU usage"},
            {"command": "wmic memorychip get capacity", "description": "Check memory"},
            {"command": "wmic diskdrive get status", "description": "Check disk health"}
        ],
        "Service Issues": [
            {"command": "net start", "description": "List running services"},
            {"command": "sc query", "description": "Check service status"},
            {"command": "eventvwr.msc", "description": "Check event logs"},
            {"command": "dism /online /cleanup-image /scanhealth", "description": "Check system health"}
        ]
    }
    
    workflow = st.selectbox("Select Troubleshooting Workflow", list(workflows.keys()))
    
    if workflow:
        steps = workflows[workflow]
        for i, step in enumerate(steps, 1):
            with st.expander(f"Step {i}: {step['description']}"):
                st.code(step['command'], language="batch")
                if st.button(f"Run Step {i}"):
                    st.info(f"Command copied: {step['command']}")
                    # Save to history
                    save_command_history(step['command'], step['description'])

def main():
    # Get favorites functions first
    add_to_favorites, show_favorites = add_command_favorites()
    
    # Create tabs after getting the functions
    tabs = st.tabs([
        "Command Assistant", 
        "Diagnostic Report", 
        "Command History",
        "Remote Management",
        "AD Management",
        "Network Topology",
        "System Monitor",
        "Favorites"
    ])
    
    with tabs[0]:
        create_sidebar_menu()
        
        col1, col2, col3 = st.columns([1, 8, 1])
        with col2:
            st.markdown("""
            <div class="app-header">
                <div class="app-title">
                    <span>🖥️ Windows Command Helper</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Fix: Add label and hide it
            user_question = st.text_input(
                label="Command Input",  # Add label
                key="question_input",
                placeholder="Ask a question about Windows commands...",
                help="Press Enter or click 'Get Answer' to submit",
                label_visibility="collapsed"  # Hide the label but keep it accessible
            )

            submit_button = st.button("Get Answer")
            
            if (user_question and submit_button) or (user_question and st.session_state.get('question_input') == user_question):
                with st.spinner("Getting response..."):
                    response = get_gemini_response(user_question)

                if response["command"]:
                    st.markdown("""
                    <div class='custom-container'>
                        <h3 style='margin-top: 0; color: white;'>Command:</h3>
                    """, unsafe_allow_html=True)
                    
                    st.code(response["command"], language="batch")
                    
                    # Updated copy button with inline tooltip
                    copy_button_key = f"copy_button_{response['command']}"
                    if st.button("📋 Copy command", key=copy_button_key):
                        st.session_state[f"copied_{copy_button_key}"] = True
                        st.session_state[f"show_tooltip_{copy_button_key}"] = True
                        
                    if st.session_state.get(f"show_tooltip_{copy_button_key}", False):
                        st.markdown("<span class='copy-tooltip show'>Copied!</span>", unsafe_allow_html=True)
                        
                        st.session_state[f"show_tooltip_{copy_button_key}"] = False
                        
                        import time
                        time.sleep(2)
                        
                        st.session_state[f"copied_{copy_button_key}"] = False
                        
                    
                    
                    st.markdown(f"""
                        <h3 style='color: white;'>Explanation:</h3>
                    """, unsafe_allow_html=True)
                    
                    st.write(response["explanation"])
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Save to command history
                    save_command_history(response["command"], response["explanation"])
                    
                    # Add favorite button
                    col1, col2 = st.columns([6, 1])
                    with col2:
                        if st.button("⭐ Favorite"):
                            add_to_favorites(response["command"], response["explanation"])
                            st.success("Added to favorites!")
    
    with tabs[1]:
        create_diagnostic_report()
    
    with tabs[2]:
        show_command_history()
    
    with tabs[3]:
        create_remote_management_tab()
    
    with tabs[4]:
        create_ad_management()
    
    with tabs[5]:
        create_network_topology()
    
    with tabs[6]:
        create_system_monitor()
    
    # Add new Favorites tab
    with tabs[7]:
        st.header("⭐ Favorite Commands")
        show_favorites()  # Now this will work because we have the function

    create_help_system()
    create_command_search()
    create_troubleshooting_workflow()

if __name__ == "__main__":
    main()


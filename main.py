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
        transition: opacity 0.3s;
    }
    .copy-tooltip.show {
        opacity: 1;
    }
    .copy-tooltip.hide {
        opacity: 0;
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
    
    for entry in reversed(st.session_state.command_history):
        with st.expander(f"{entry['timestamp']} - {entry['command'][:40]}..."):
            st.code(entry['command'], language="batch")
            st.write(entry['explanation'])

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
        remote_host = st.text_input("Remote Host")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
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
    
    # Network discovery commands
    discovery_commands = {
        "ARP Table": "arp -a",
        "Network Interfaces": "Get-NetAdapter | Select-Object Name,Status,LinkSpeed",
        "IP Configuration": "Get-NetIPConfiguration | Select-Object InterfaceAlias,IPv4Address",
        "Routing Table": "Get-NetRoute | Select-Object DestinationPrefix,NextHop,RouteMetric"
    }
    
    if st.button("Discover Network"):
        # Create a network graph
        G = nx.Graph()
        
        # Add nodes and edges based on network discovery
        # This is a placeholder - you'd need to parse actual network data
        G.add_node("Local PC")
        G.add_node("Gateway")
        G.add_edge("Local PC", "Gateway")
        
        # Draw the network graph
        plt.figure(figsize=(10, 8))
        nx.draw(G, with_labels=True, node_color='lightblue', 
                node_size=1500, font_size=10, font_weight='bold')
        
        # Display in Streamlit
        st.pyplot(plt)
        
        # Show discovery commands
        for name, command in discovery_commands.items():
            with st.expander(name):
                st.code(command, language="powershell")

def create_system_monitor():
    st.subheader("📊 System Health Monitor")
    
    # Monitor categories
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
        if st.button("Start Monitoring"):
            placeholder = st.empty()
            
            while True:
                metrics_data = {}
                for metric in selected_metrics:
                    # In practice, you'd execute the commands and parse results
                    metrics_data[metric] = random.random() * 100  # Placeholder data
                
                # Update the display
                with placeholder.container():
                    for metric, value in metrics_data.items():
                        st.metric(metric, f"{value:.2f}%")
                
                time.sleep(refresh_rate)

def main():
    tabs = st.tabs([
        "Command Assistant", 
        "Diagnostic Report", 
        "Command History",
        "Remote Management",
        "AD Management",
        "Network Topology",
        "System Monitor"
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
            
            user_question = st.text_input(
                "",
                key="question_input",
                placeholder="Ask a question about Windows commands...",
                help="Press Enter or click 'Get Answer' to submit",
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

if __name__ == "__main__":
    main()


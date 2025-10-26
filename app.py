import streamlit as st
import os
from datetime import date, timedelta
import traceback
import json

from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_ollama import OllamaLLM
from langchain_core.tools import tool 

# --- 1. CONFIGURATION AND INITIALIZATION ---

# Load environment variables
load_dotenv()

# Set Streamlit page configuration (Must be the very first Streamlit call)
st.set_page_config(
    page_title="Health AI Assistant", 
    page_icon="🧠", 
    layout="wide"
)

# Apply custom CSS for background
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFD1DC; /* Light Pink Background */
    }

    /* Target the main block that holds the title and chat history */
    .main [data-testid="stVerticalBlock"] {
        padding-top: 1rem; /* Reduced top padding */
    }

    /* Add margin to push the content down a bit (adjust the 15% value as needed) */
    .block-container {
        padding-top: 1rem !important;
        margin-top: 5vh; /* Shifts content down by 5% of viewport height */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY") 
if not supabase_key: 
    supabase_key = os.getenv("SUPABASE_KEY")
    
supabase: Client | None = None
supabase_available = False

if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        supabase_available = True
    except Exception as e:
        print(f"Error initializing Supabase: {e}")

# Initialize Ollama LLM
llm = None
ollama_available = False
try:
    llm = OllamaLLM(model="llama3:8b", base_url="http://localhost:11434")
    llm.invoke("Say OK") # Test connectivity
    ollama_available = True
except Exception as e:
    print(f"Error initializing Ollama: {e}")


# --- Load User Profile Data ---
USER_PROFILE = {}
try:
    # Load profile data from the polar_token.json file (where the registration info is)
    with open("polar_token.json", "r") as f:
        polar_token_data = json.load(f)
        # Assuming the initial registration data is stored in the token file
        USER_PROFILE = {
            'age': polar_token_data.get('age', 35),
            'weight': polar_token_data.get('weight', 59),
            'height': polar_token_data.get('height', 162),
            'gender': polar_token_data.get('gender', 'FEMALE'),
        }
    print(f"✓ User Profile Loaded: Age {USER_PROFILE['age']}, Weight {USER_PROFILE['weight']}kg.")
except Exception:
    print("! Warning: Could not load user profile from polar_token.json. Using default metrics.")


# --- 2. TOOL DEFINITIONS (Functions run by the LLM) ---

tools_dict = {}

if supabase_available:
    @tool
    def get_oura_sleep_score(day: str) -> str:
        """Retrieves the Oura sleep score and details for a specific date (YYYY-MM-DD)."""
        try:
            parsed_date = date.fromisoformat(day)
            response = supabase.table('oura_sleep').select('day, score').order('day', desc=True).limit(7).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                result = f"Sleep data for {day}:"
                result += f"\n- Score: {data.get('score', 'N/A')}"
                duration = data.get('total_sleep_duration')
                if duration:
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    result += f"\n- Total sleep: {hours}h {minutes}m"
                result += f"\n- Efficiency: {data.get('efficiency', 'N/A')}%"
                return result
            else:
                return f"No Oura sleep data found for {summary_date}."
        except Exception as e:
            return f"Error while fetching sleep data: {e}"

    @tool
    def get_oura_activity_steps(day: str) -> str:
        """Retrieves total steps and active calories for a specific date (YYYY-MM-DD)."""
        try:
            parsed_date = date.fromisoformat(day)
            response = supabase.table('oura_activity').select('steps, active_calories, score').eq('day', parsed_date.isoformat()).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                result = f"Activity data for {day}:"
                result += f"\n- Steps: {data.get('steps', 0):,}"
                result += f"\n- Active calories: {data.get('active_calories', 'N/A')}"
                result += f"\n- Activity score: {data.get('score', 'N/A')}"
                return result
            else:
                return f"No activity data found for {day}."
        except Exception as e:
            return f"Error while fetching activity data: {e}"

    @tool
    def log_gym_set(date_str: str, exercise: str, weight: float, reps: int, sets: int) -> str:
        """
        Logs a single set of a gym workout. Input requires date (YYYY-MM-DD), exercise name (text), weight (float), repetitions (int), and set number (int).
        Example: date_str='2025-10-25', exercise='Squat', weight=100.0, reps=5, sets=3
        """
        try:
            date.fromisoformat(date_str)
            if not (exercise and weight > 0 and reps > 0 and sets > 0):
                return "Error: Missing or invalid workout parameters. Please check exercise name, weight, reps, and set number."

            data = {
                'workout_date': date_str,
                'exercise_name': exercise,
                'weight_kg': weight,
                'repetitions': reps,
                'sets': sets,
            }

            response = supabase.table('manual_workouts').insert(data).execute()

            if hasattr(response, 'error') and response.error:
                 return f"Error: Failed to insert set. Details: {response.error}"

            return f"Successfully logged Set {sets} of {exercise} ({weight}kg x {reps} reps) for {date_str}."

        except Exception as e:
            print(f"Error logging gym set: {e}")
            return "An internal error occurred while trying to log the workout." 
    
    @tool
    def get_readiness_report(start_date: str = None, end_date: str = None) -> str:
        """
        Gathers a summary of recent sleep, steps, and maximal lifts for training advice.
        Automatically looks at the last 3 days if no dates are specified.
        """
        if not supabase:
            return "Database connection not available."
        
        # Use provided dates or default to last 3 days
        try:
            if end_date:
                end = date.fromisoformat(end_date)
            else:
                end = date.today()
        except:
            end = date.today()
        
        try:
            if start_date:
                start = date.fromisoformat(start_date)
            else:
                start = end - timedelta(days=3)
        except:
            start = end - timedelta(days=3)
        
        try:
            # 1. Fetch recent Oura data (Sleep and Activity)
            sleep_res = supabase.table('oura_sleep').select('day, score, total_sleep_duration, efficiency').gte('day', start.isoformat()).lte('day', end.isoformat()).order('day', desc=True).execute()
            activity_res = supabase.table('oura_activity').select('day, steps, active_calories, score').gte('day', start.isoformat()).lte('day', end.isoformat()).order('day', desc=True).execute()
            
            # 2. Fetch recent workouts (get the latest weight for each exercise)
            workout_res = supabase.table('manual_workouts').select('workout_date, exercise_name, weight_kg, repetitions, sets').gte('workout_date', start.isoformat()).lte('workout_date', end.isoformat()).order('workout_date', desc=True).execute()
            
            report = f"--- HEALTH READINESS REPORT ({start.isoformat()} to {end.isoformat()}) ---\n"
            
            # Format Sleep Data
            if sleep_res.data and len(sleep_res.data) > 0:
                report += "\nSLEEP SUMMARY:\n"
                for record in sleep_res.data:
                    duration = record.get('total_sleep_duration', 0)
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    report += f" - {record['day']}: Score {record.get('score', 'N/A')}, Duration {hours}h {minutes}m, Efficiency {record.get('efficiency', 'N/A')}%\n"
            else:
                report += "\nSLEEP SUMMARY: No data available\n"
            
            # Format Activity Data
            if activity_res.data and len(activity_res.data) > 0:
                report += "\nACTIVITY SUMMARY:\n"
                for record in activity_res.data:
                    report += f" - {record['day']}: Steps {record.get('steps', 0):,}, Calories {record.get('active_calories', 'N/A')}, Score {record.get('score', 'N/A')}\n"
            else:
                report += "\nACTIVITY SUMMARY: No data available\n"
                    
            # Format Workout Data - group by exercise and show max weight
            if workout_res.data and len(workout_res.data) > 0:
                report += "\nRECENT WORKOUTS:\n"
                # Group by exercise to show max lifts
                exercises = {}
                for record in workout_res.data:
                    ex_name = record['exercise_name']
                    weight = record.get('weight_kg', 0)
                    if ex_name not in exercises or weight > exercises[ex_name]['weight']:
                        exercises[ex_name] = {
                            'weight': weight,
                            'reps': record.get('repetitions', 0),
                            'date': record['workout_date']
                        }
                
                for ex_name, data in exercises.items():
                    report += f" - {ex_name}: Max {data['weight']}kg x {data['reps']} reps on {data['date']}\n"
            else:
                report += "\nRECENT WORKOUTS: No data available\n"

            if report == f"--- HEALTH READINESS REPORT ({start.isoformat()} to {end.isoformat()}) ---\n":
                 return "No recent Oura or manual workout data found to generate advice."
            
            return report
            
        except Exception as e:
            print(f"Error generating readiness report: {e}")
            traceback.print_exc()
            return f"An error occurred while accessing the aggregated data for the report: {e}"

    # Map tool names to functions
    tools_dict = {
        'get_oura_sleep_score': get_oura_sleep_score,
        'get_oura_activity_steps': get_oura_activity_steps,
        'log_gym_set': log_gym_set,
        'get_readiness_report': get_readiness_report
    }

# --- 3. CORE LOGIC (Custom Two-Stage LLM Processor) ---

def process_query(user_query: str) -> str:
    """Processes user query by asking LLM to choose a tool and executing it."""
    if not llm:
        return "AI model is not running. Please start Ollama."

    today = date.today()
    yesterday = (today - timedelta(days=1))
    
    # 1. Determine context for the LLM
    tools_desc = "\n".join([f"- {t.name}: {t.description.splitlines()[0].strip()}" for t in tools_dict.values()])

    decision_prompt = f"""You are a health assistant and decision-maker. Your sole task is to determine the appropriate action based on the user's request.

    Available tools:
    {tools_desc}
    
    Current Date Context:
    - Today's date: {today.isoformat()}
    - Yesterday's date: {yesterday.isoformat()}

    User Request: "{user_query}"

    ---
    Decide ONLY ONE of the following actions. DO NOT include any extra text.

    ACTION: TOOL_CALL | <tool_name> | <tool_input_1> | <tool_input_2> ...
    ACTION: DIRECT_ANSWER | <Your natural language response>

    If the request is a simple greeting (e.g., 'hi'), or non-data related, use DIRECT_ANSWER.
    If the tool needs a date but the user says 'yesterday', use the exact date {yesterday.isoformat()}.

    Example Output 1 (Log): ACTION: TOOL_CALL | log_gym_set | {today.isoformat()} | Bench Press | 80.5 | 5 | 1
    Example Output 2 (Query): ACTION: TOOL_CALL | get_oura_sleep_score | {yesterday.isoformat()}
    Example Output 3 (Greeting): ACTION: DIRECT_ANSWER | Hello there! How can I help you check your metrics today?

    Your concise response (start immediately with ACTION: TOOL_CALL or ACTION: DIRECT_ANSWER):
    """
    
    try:
        # Get LLM decision
        decision = llm.invoke(decision_prompt, stop=["\n"]).strip() 
        print(f"LLM Decision Output: {decision}")

        # 2. Execution Stage
        
        if decision.startswith("ACTION: TOOL_CALL"):
            try:
                # Parse Tool Call: ACTION: TOOL_CALL | <tool_name> | <param1> | <param2> ...
                parts = decision.split("|")
                tool_name = parts[1].strip()  # Fixed: tool name is in parts[1]
                tool_inputs = [part.strip() for part in parts[2:]]  # Fixed: inputs start at parts[2]

                tool_func = tools_dict.get(tool_name)
                
                if not tool_func:
                    return f"Error: Tool '{tool_name}' not found."

                clean_tool_inputs = [i for i in tool_inputs if i]

                tool_result = tool_func.func(*clean_tool_inputs)

                # Execute the tool using dynamic argument unpacking
                if tool_name == 'log_gym_set':
                    # Explicit type conversion for the log_gym_set tool
                    typed_inputs = [
                        tool_inputs[0], # date_str
                        tool_inputs[1], # exercise
                        float(tool_inputs[2]), # weight (float)
                        int(tool_inputs[3]), # reps (int)
                        int(tool_inputs[4]), # sets (int)
                    ]
                    tool_result = tool_func.func(*typed_inputs)
                elif tool_name == 'get_readiness_report':
    # This tool can optionally take date parameters or none at all
                    if len(tool_inputs) >= 2:
                        tool_result = tool_func.func(tool_inputs[0], tool_inputs[1])
                    elif len(tool_inputs) == 1:
                        tool_result = tool_func.func(tool_inputs[0])
                    else:
                        tool_result = tool_func.func()
                else:
    # For all other simple query tools (single string input)
                     tool_result = tool_func.func(*tool_inputs)
                
                # 3. Final Answer Stage (Second LLM call to format the answer)
                
                # Add specific coaching instructions if the report tool was used
                coaching_instruction = ""
                if tool_name == 'get_readiness_report':
                     coaching_instruction = (
                         f"\nUSER PROFILE: Age {USER_PROFILE['age']}, Weight {USER_PROFILE['weight']}kg, Height {USER_PROFILE['height']}cm. "
                         f"\nUse the data and this profile information to provide specific, actionable training advice: "
                         "1. Suggest a good training intensity (e.g., heavy, light, or rest day). 2. Recommend a focus (e.g., recovery or volume). "
                         "3. Base advice on low sleep scores (<70) or low total sleep duration (<7h) indicating a strong need for recovery."
                     )
                
                format_prompt = f"""Based on this data:
{tool_result}
Provide a friendly, natural, conversational answer to the user request: "{user_query}"
{coaching_instruction}
Be concise, warm, and helpful. Do not mention the word 'tool' or 'database'. Just give a natural response."""
                
                return llm.invoke(format_prompt)
            
            except Exception as e:
                # This catches errors during parsing or tool execution
                print(f"Error during Tool Execution: {e}")
                traceback.print_exc()
                return f"Sorry, I ran into an error trying to execute the action. Please check the date format or simplify your request. Error: {e}"
                
        elif decision.startswith("ACTION: DIRECT_ANSWER"):
            return decision.replace("ACTION: DIRECT_ANSWER |", "").strip()
            
        else:
            # Fallback if LLM output is garbled
            return f"Sorry, I couldn't understand the AI's response format. Try asking a specific question about sleep, activity, or logging a set."

    except Exception as e:
        print(f"Error in process_query: {e}")
        traceback.print_exc()
        return f"Sorry, I encountered a critical error: {str(e)}"

# --- 4. STREAMLIT UI EXECUTION ---

# Sidebar Status Display
st.sidebar.title("System Status")
if ollama_available and supabase_available:
    st.sidebar.success("✓ AI Agent Ready")
elif not ollama_available:
    st.sidebar.error("✗ Ollama Error (Check Terminal/Server)")
elif not supabase_available:
    st.sidebar.error("✗ Supabase Error (Check Terminal/Credentials)")


st.title("🧠 Personal Health AI Assistant")
st.markdown("Welcome! Use the tool below to check your sleep, activity, and health metrics.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Process user input
if user_input := st.chat_input("Ask about your health data (e.g., 'How did I sleep last night?')"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    assistant_response = "Sorry, the AI agent is not available or encountered an error."

    if ollama_available and supabase_available:
        with st.spinner("Thinking..."):
            try:
                assistant_response = process_query(user_input)

            except Exception as e:
                assistant_response = f"Sorry, an error occurred while the AI was processing: {e}"
                print(f"! Error invoking process_query: {e}")
                traceback.print_exc()
    else:
        assistant_response = "AI components are not initialized. Please check the System Status sidebar."

    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    with st.chat_message("assistant"):
        st.markdown(assistant_response)

# --- Sidebar: Quick Stats ---
st.sidebar.markdown("---")
st.sidebar.subheader("Quick Actions")

if st.sidebar.button("📊 View Recent Sleep"):
    if supabase_available:
        try:
            # Fetch score and date (order matters for charts)
            response = supabase.table('oura_sleep').select('day, score').order('day', desc=True).limit(7).execute()
            
            if response.data:
                import pandas as pd
                
                # 1. Convert data to a Pandas DataFrame
                df = pd.DataFrame(response.data)

                # 2. Rename columns and ensure correct types for charting
                df = df.rename(columns={'day': 'Date', 'score': 'Sleep Score'})
                
                df['Date'] = pd.to_datetime(df['Date'])
                
                # 3. Sort by Date ascending (required for correct line chart order)
                df = df.sort_values(by='Date')
                
                st.sidebar.write("**Last 7 Day Sleep Trend:**")
                
                # 4. Create a simple line chart using Streamlit's native function
                st.sidebar.line_chart(df, x='Date', y='Sleep Score')
                
                # 5. Display the detailed list (optional, but good for raw data view)
                st.sidebar.markdown("---")
                st.sidebar.write("**Raw Data:**")
                for index, record in df.iterrows():
                    st.sidebar.write(f"{record['Date'].strftime('%b %d')}: Score **{record['Sleep Score']}**")
                    
            else:
                st.sidebar.write("No sleep data found")
        except Exception as e:
            st.sidebar.error(f"Error fetching sleep data: {e}")
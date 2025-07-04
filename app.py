import os
import matplotlib.pyplot as plt
import io
os.environ["STREAMLIT_WATCHDOG_TYPE"] = "poll"
import streamlit as st
import pandas as pd
from openai import OpenAI
import ast
import json
import streamlit_mermaid as stmd

# Set custom page configuration including the "About" section
st.set_page_config(
    page_title="Bowtie Builder",  # Custom title in the browser tab
    page_icon="🤖",  # Custom icon for the browser tab
    layout="wide",  # Set the defaul layout for the app
    initial_sidebar_state="auto",  # Sidebar state when app loads
    menu_items={
        "About": """
        ## Bowtie Builder
        This application is a chatbot that helps build bowtie diagrams.
        """
    }
)

# Initialize session state variables:
# to store bowtie data generated by the agent or uploaded by the user
if "bowtie_data" not in st.session_state:
    st.session_state.bowtie_data = None
# to store diagram data which may be different than bowtie_data if the user inputs corrections
if "diagram_data" not in st.session_state:
    st.session_state.diagram_data = None

# Dashboard title
st.title("Bowtie Builder")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Agent", "Data", "Inputs", "Diagram","PDF"])
with tab1:
    # Define the bowtie process description and prompt to control the chatbot's behavior
    bowtie_process_description = """
    You are a risk management expert. Your primary role is to facilitate the bowtie workshop process.
    The purpose of a Major Hazard bowtie Bowtie workshop is to guide the workshop’s participants through the process of construction of the Bowtie diagram, making them to think as actively as possible about the potential hazards present in a given facility or operation, and the ways in which those hazards are controlled, and transform their input into the constitutive elements of the Bowtie diagram. The ultimate goal is to help users build bowtie diagrams to visually depict a hazardous scenario and the barriers in place to control it.
    
    You need to work with the user to understand the following elements of the operation that will define the bowtie diagram:
    1. **Hazard**: The hazard that is being analyzed. Each bowtie diagram has only one hazard. Hazards do not happen, they just exist. The hazard defines the context and scope of the bowtie diagram. The hazard is part of normal business operations and is often necessary for the business to function. It describes the desired or controlled state or activity. It has the potential to cause harm if control is lost. Harm is defined as any negative impact on people, assets, environment, finances, or reputation.
    2. **Top Event**: The event is the moment when the control over the hazard is lost. Each hazard can have multiple top events, however each Bowtie diagram has only a single top event. A Bowtie diagram represents a single pair of Hazard+Top Event. The top event is a deviation from a desired state or activity. It happens BEFORE major harm occurs and it is still possible to recover from.
    3. **Consequences**: The undesired hazardous outcome that can occur as the result of a top event. Each top event can have multiple consequences. There is no limit to the number of consequences a top event can have. The consequences are the outcomes that can cause harm to people, assets, environment, finances, or reputation; i.e. the direct cause for the harm.
    4. **Threats**: A possible cause of the top event. Each top event can have multiple threats. There is no limit to the number of threats a top event can have. Threats are specific, credible causes of a top event and must lead DIRECTLY AND INDEPENDENTLY to the top event occurring. Barrier failures are not threats. Human errors are not threats. Threats are not the same as causes of harm. Threats are the causes of the top event, not the consequences.
    5. **Barriers**: A barrier is a hardware measure, human measure, or a combination of hardware and human measure that is in place to prevent the top event from occurring or to mitigate the consequences of the top event. Barriers can be Preventative (eliminate or prevent a threat) or Mitigative (control or mitigate a consequence) upon undesired events. Barriers can be classified as: passive hardware, active hardware, active hardware + human, active human, or continous. Each threat can have multiple preventive barriers, but not more than five. Each consequence can have multiple mitigative barriers, but not more than five. Barriers are not the same as controls. Controls are the measures that are in place to manage the risk. Barriers are the specific controls that are in place to prevent the top event from occurring or to mitigate the consequences of the top event. A barrier to prevent or control a threat to avoid it leading to a top event is called a preventive barrier and exists between a threat and the top event. A barrier to control or mitigate the top event to minimize or prevent a consequence is called a mitigative barrier and exists between the top event and the consequence. Barriers can be active or passive. Active barriers require human intervention to function, while passive barriers do not require human intervention to function.

    The structure of a bowtie diagram is as follows:
    Threats → Preventive Barriers → Top Event → Mitigative Barriers → Consequences
    Top event is always at the center of the diagram, with threats on the left side and consequences on the right side. Preventive barriers are placed between threats and the top event, while mitigative barriers are placed between the top event and consequences.
    All of the above falls under the single defined Hazard.

    Your job is to parse the user's input and help them build a bowtie diagram by asking questions and providing guidance.
    You will need to ask the user for the hazard, top events, threats, consequences, and barriers.
    You will also need to help the user understand the relationships between these elements and how they fit together in the bowtie diagram. If the user provides a response that is not clear or does not fit the bowtie methodology, ask them to clarify their input and provide guidance on how to do so. You are allowed to ask the user follow up questions to clarify their input and to help them build the bowtie diagram. Each follow up response may contain enough questions to help the user clarify their input, but do not overwhelm them with too many questions at once.
    It is acceptable and desirable to make suggestions to the user based on their input, especially for barriers that might be missed, but do not assume that the user will accept your suggestions. If you make a suggestion, ask the user if they agree with it and if they would like to include it in the bowtie diagram.
    If you believe you have enough information to build the bowtie diagram, inform the user that the diagram is ready and output the bowtie_data dictionary as described below.

    You must output the user's responses in the following structured dictionary format:
    bowtie_data = { "hazard": "", "top_events": [ { "top_event": "<top_event_1>", "threats": [ { "threat": "<threat_1>", "preventive_barriers": ["<barrier_1>", "<barrier_2>"] }, ... ], "consequences": [ { "consequence": "<consequence_1>", "mitigative_barriers": ["<barrier_1>", "<barrier_2>"] }, ... ] }, ... ] }
    Format the text in the dictionary entries as follows: Capitalize the first letter of each word for hazard. Use sentence case for top_event, threat, consequence, preventive_barriers, and mitigative_barriers. Avoid using special characters, especially parentheses and brackets.
    Only include fields that the user has provided or suggestions the user has explicitly accepted. If the user hasn't provided a value yet, leave it blank or omit it. Ask follow-up questions to complete the structure.
    The output should be a valid Python dictionary that can be parsed using `ast.literal_eval()`.
    """

    # Create title and description
    st.header(":material/robot_2: Bowtie Facilitation Agent")
    st.write(
        "This is an AI Risk Management Agent that will assist your efforts to define a hazard chain using the bowtie methodology. "
        "To interact with this Agent, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
    )

    # Ask user for their OpenAI API key
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    
    # Once OpenAI API key is provided, initialize the chatbot.
    else:
        # Create an OpenAI client.
        client = OpenAI(api_key=openai_api_key)

        # Create a session state variable to store the chat messages. This ensures that the messages persist across reruns.
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Split the page into two columns: one for the chat messages and one for the chat input.
        column1, column2 = st.columns([2, 3])

        with column1:
            st.subheader("Chat with the Bowtie Bot")
            # Create a chat input field to allow the user to enter a message
            if prompt := st.chat_input("Tell me about your hazard operation."):

                # Store and display the current prompt.
                st.session_state.messages.append({"role": "user", "content": prompt})
                #with st.chat_message("user"):
                #    st.markdown(prompt)

                # Generate a response using the OpenAI API.
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": bowtie_process_description},
                        *[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                        ]
                    ],
                    stream=True,
                )

                # Stream the response to the chat using `st.write_stream`, then store it in session state.
                with st.chat_message("assistant"):
                    response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})

                if "bowtie_data" in response:
                    try:
                        # Extract the dictionary from the response
                        start = response.find("bowtie_data =")
                        code_block = response[start:].split("```")[0]
                        code = code_block.replace("bowtie_data =", "").strip()
                        st.session_state.bowtie_data = ast.literal_eval(code)
                    except Exception as e:
                        st.warning(f"Could not parse bowtie_data: {e}")

        with column2:
            st.subheader("Chat History (newest message at the top)")
            # Display the existing chat messages via `st.chat_message`.
            for message in reversed(st.session_state.messages):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
with tab2:
    st.header(":material/analytics: Bowtie Data")
    st.divider()
    st.subheader(":material/upload: Import From Excel")
    st.write("Upload an Excel file with `Threats`, `Consequences`, and optionally `Info` sheets.")

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"], key="excel_uploader")
    if excel_file:
        try:
            df_threats = pd.read_excel(excel_file, sheet_name="Threats")
            df_conseq = pd.read_excel(excel_file, sheet_name="Consequences")

            try:
                df_info = pd.read_excel(excel_file, sheet_name="Info", header=None)
                hazard = str(df_info.iloc[0, 1]) if not pd.isna(df_info.iloc[0, 1]) else "Enter the hazard here"
                top_event = str(df_info.iloc[1, 1]) if not pd.isna(df_info.iloc[1, 1]) else "Enter the top event here"
            except Exception:
                hazard = st.text_input("Hazard", value="Enter the hazard here", key="excel_hazard")
                top_event = st.text_input("Top Event", value="Enter the top event here", key="excel_top_event")

            threats = [
                {
                    "threat": str(row["Threat"]),
                    "preventive_barriers": [str(b).strip() for b in str(row["Preventive Barriers"]).split(";") if b.strip()]
                } for _, row in df_threats.iterrows()
            ]

            consequences = [
                {
                    "consequence": str(row["Consequence"]),
                    "mitigative_barriers": [str(b).strip() for b in str(row["Mitigative Barriers"]).split(";") if b.strip()]
                } for _, row in df_conseq.iterrows()
            ]

            bowtie_data_from_excel = {
                "hazard": hazard,
                "top_events": [
                    {
                        "top_event": top_event,
                        "threats": threats,
                        "consequences": consequences
                    }
                ]
            }

            st.session_state.bowtie_data = bowtie_data_from_excel
            st.session_state.diagram_data = bowtie_data_from_excel

            st.success("✅ Bowtie data successfully imported from Excel.")
            st.json(bowtie_data_from_excel)

        except Exception as e:
            st.error("❌ Failed to process Excel file.")
            st.code(str(e))

    st.divider()
    st.subheader(":material/save: Import from Json")
    st.write("You may upload a JSON file containing bowtie data to use in this app instead of using the chat agent.")
    uploaded_file = st.file_uploader(label=":material/upload: Upload Bowtie JSON", type="json")
    if uploaded_file is not None:
        try:
            uploaded_data = json.load(uploaded_file)
            st.session_state.bowtie_data = uploaded_data
            st.success("✅ bowtie_data has been successfully loaded from the uploaded file.")
        except Exception as e:
            st.error(f"❌ Failed to load JSON: {e}")

    st.divider()

    if st.session_state.bowtie_data is not None and isinstance(st.session_state.bowtie_data, dict):        
        st.subheader(":material/save: Export Bowtie Data")
        st.write("You can save the bowtie data to a JSON file for later use.")
        st.download_button(
            label="Save Bowtie Data",
            data=json.dumps(st.session_state.bowtie_data, indent=4),
            file_name='bowtie_data.json',
            mime='application/json',
            icon=":material/download:",
        )   
        st.divider()
        st.subheader(":material/data_object: Parsed Bowtie Data")
        st.json(st.session_state.bowtie_data, expanded=True)
        st.divider()
    else:
        st.warning("The response did not contain the expected bowtie_data dictionary. Please try again.")

with tab3:
    #####################################################################################################################
    # ACCEPT USER INPUTS TO DEFINE THE BOWTIE DIAGRAM ELEMENTS
    #####################################################################################################################

    # Initialize data dictionary to store diagram variables
    diagram_data = {
        "hazard": "",
        "top_events": [],
    }

    st.header(":material/variables: Diagram Inputs")
    st.warning("Avoid using special characters, especially parentheses, brackets, quotes, and dashes. Use of these characters may cause issues with the diagram rendering. Use of alphanumeric characters only is recommended.", icon="⚠️")
    # Prompt the user for the hazard and number of top events
    diagram_data["hazard"] = st.text_input(label="Hazard", value=st.session_state.bowtie_data["hazard"] if st.session_state.bowtie_data else "Enter the hazard here")

    num_top_events = st.number_input(
        "Number of Top Events",
        min_value=1,
        max_value=1,
        value=len(st.session_state.bowtie_data["top_events"]) if st.session_state.bowtie_data else 1
    )

    st.divider()

    # For each top event, prompt the user to define the top event, number of threats, and number of consequences
    # If data has already been parsed by the agent, pre-fill the inputs with the existing data.
    for i in range(num_top_events):
        with st.expander(f"Top Event {i+1}", expanded=True):
            st.subheader(f"Top Event {i+1}")
            top_event = st.text_input(label=f"Top Event {i+1}", 
                                      value=(
                                          st.session_state.bowtie_data["top_events"][i]["top_event"]
                                          if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"])
                                          else f"Enter Top Event {i+1} here"
                                      ),
                                      label_visibility="collapsed"
            )
            top_event_data = {
                "top_event": top_event,
                "threats": [],
                "consequences": [],
            }
            
            # Create two columns for the threats and consequences and prompt the user for the threats, consequences, and barriers
            threat_side, consequence_side = st.columns(2)
            
            # Threat side
            with threat_side:
                st.subheader(f"Top Event {i+1} | Threats")
                num_threats = st.number_input(
                    f"Number of Threats for Top Event {i+1}",
                    min_value=1,
                    max_value=None,
                    value=(
                        len(st.session_state.bowtie_data["top_events"][i]["threats"])
                        if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"])
                        else 1
                    )
                )
                for j in range(num_threats):
                    st.markdown(f"**Threat {j + 1} | Top Event {i+1}**")
                    threat = st.text_input(
                        label=f"Threat {j + 1} | Top Event {i+1}",
                        value=(
                            st.session_state.bowtie_data["top_events"][i]["threats"][j]["threat"]
                            if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"]) and j<len(st.session_state.bowtie_data["top_events"][i]["threats"])
                            else f"Enter Threat {j + 1} here"
                        )
                    )
                    threat_data = {
                        "threat": threat,
                        "preventive_barriers": []
                    }
                    num_preventive_barriers = st.number_input(
                        f"Number of Preventive Barriers for Threat {j + 1} | Top Event {i+1}",
                        min_value=1,
                        max_value=5,
                        value=(
                            len(st.session_state.bowtie_data["top_events"][i]["threats"][j]["preventive_barriers"])
                            if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"]) and j<len(st.session_state.bowtie_data["top_events"][i]["threats"])
                            else 1
                        )
                    )
                    for k in range(num_preventive_barriers):
                        preventive_barrier = st.text_input(
                            label=f"Preventive Barrier {k + 1} | Threat {j + 1} | Top Event {i+1}",
                            value=(
                                st.session_state.bowtie_data["top_events"][i]["threats"][j]["preventive_barriers"][k]
                                if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"]) and j<len(st.session_state.bowtie_data["top_events"][i]["threats"]) and k<len(st.session_state.bowtie_data["top_events"][i]["threats"][j]["preventive_barriers"])
                                else f"Enter Preventive Barrier {k + 1} here"
                            )
                        )
                        threat_data["preventive_barriers"].append(preventive_barrier)
                    top_event_data["threats"].append(threat_data)
            
            # Consequence side
            with consequence_side:
                st.subheader(f"Top Event {i+1} | Consequences")
                num_consequences = st.number_input(
                    f"Number of Consequences for Top Event {i+1}",
                    min_value=1,
                    max_value=None,
                    value=(
                        len(st.session_state.bowtie_data["top_events"][i]["consequences"])
                        if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"])
                        else 1
                    )
                )
                for j in range(num_consequences):
                    st.markdown(f"**Consequence {j+1} | Top Event {i+1}**")
                    consequence = st.text_input(
                        label=f"Consequence {j+1} | Top Event {i+1}",
                        value=(
                            st.session_state.bowtie_data["top_events"][i]["consequences"][j]["consequence"]
                            if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"]) and j<len(st.session_state.bowtie_data["top_events"][i]["consequences"])
                            else f"Enter Consequence {j + 1} here"
                        )
                    )
                    consequence_data = {
                        "consequence": consequence,
                        "mitigative_barriers": []
                    }
                    num_mitigative_barriers = st.number_input(
                        f"Number of Mitigative Barriers for Consequence {j+1} | Top Event {i+1}",
                        min_value=1,
                        max_value=5,
                        value=(
                            len(st.session_state.bowtie_data["top_events"][i]["consequences"][j]["mitigative_barriers"])
                            if st.session_state.bowtie_data and i<len(st.session_state.bowtie_data["top_events"]) and j<len(st.session_state.bowtie_data["top_events"][i]["consequences"])
                            else 1
                        )
                    )
                    for k in range(num_mitigative_barriers):
                        mitigative_barrier = st.text_input(
                            label=f"Mitigative Barrier {k+1}  | Consequence {j+1} | Top Event {i+1}",
                            value=(
                                st.session_state.bowtie_data["top_events"][i]["consequences"][j]["mitigative_barriers"][k]
                                if st.session_state.bowtie_data and j<len(st.session_state.bowtie_data["top_events"][i]["consequences"]) and k<len(st.session_state.bowtie_data["top_events"][i]["consequences"][j]["mitigative_barriers"])
                                else f"Enter Mitigative Barrier {k + 1} here"
                            )
                        )
                        consequence_data["mitigative_barriers"].append(mitigative_barrier)
                    top_event_data["consequences"].append(consequence_data)
            
            diagram_data["top_events"].append(top_event_data)

    # Store the diagram data in session state
    st.session_state.diagram_data = diagram_data

    st.divider()

    #####################################################################################################################
    # TROUBLESHOOTING AND DEBUGGING
    #####################################################################################################################

    #st.subheader("Bowtie Data Dictionary")
    #st.json(diagram_data)
    #st.divider()

    #st.subheader("Debugging")
    #st.write(num_top_events)
    #st.write(num_threats)
    ##st.write(num_preventive_barriers)
    #st.write(num_consequences)
    #st.write(num_mitigative_barriers)
    #st.divider()

with tab4:
    #####################################################################################################################
    # VISUALIZE THE BOWTIE DIAGRAM
    #####################################################################################################################

    # Display the bowtie diagram with dynamic Mermaid.js code
    st.header(":material/flowchart: Bowtie Diagram")

    # Define a function to wrap the text output to the diagram nodes to improve readability
    def wrap_text(text, num_words):
        words = text.split()
        wrapped_text = ""
        for w in range(0, len(words), num_words):
            wrapped_text += " ".join(words[w:w+num_words]) + "<br>"
        return wrapped_text.strip("<br>")
    # Set number of words per line for the diagram nodes
    words_per_line = st.number_input("Words per Line", min_value=1, max_value=10, value=3, help="Number of words to allow per line before wrapping text in the diagram nodes to improve readability.", step=1)

    mermaid_code = '''
        flowchart LR
    '''

    mermaid_code += f'''
        subgraph Hazard[Hazard]
            H({wrap_text(st.session_state.diagram_data["hazard"], words_per_line)})
            style H fill:#FFDE59,stroke:#000000,stroke-width:8px
    '''

    for i in range(num_top_events):
        mermaid_code += f'''
            subgraph TopEvents[Top Events]
                TE{i+1}(({wrap_text(st.session_state.diagram_data["top_events"][i]["top_event"], words_per_line)}))
                style TE{i+1} fill:#FEB84F
            end
        '''

    mermaid_code += f'''
        end
    '''

    for i in range(num_top_events-1, -1, -1):
        # Threats and preventive barriers
        for j in range(len(st.session_state.diagram_data["top_events"][i]["threats"])):
            # Add the threat and preventive barrier to the diagram
            mermaid_code += f'''
                subgraph Threats[Threats]
                    T{i+1}{j+1}({wrap_text(st.session_state.diagram_data["top_events"][i]["threats"][j]["threat"], words_per_line)})
                    style T{i+1}{j+1} fill:#504AFF,color:#FFFFFF
                end
            '''
            for k in range(len(st.session_state.diagram_data["top_events"][i]["threats"][j]["preventive_barriers"])):
                mermaid_code += f'''
                    subgraph PreventiveBarriers[Preventive Barriers]
                        PB{i+1}{j+1}{k+1}({wrap_text(st.session_state.diagram_data["top_events"][i]["threats"][j]["preventive_barriers"][k], words_per_line)})
                    end
                '''
            mermaid_code += f'''
                T{i+1}{j+1} --- PB{i+1}{j+1}{1}
            '''
            for k in range(1, len(st.session_state.diagram_data["top_events"][i]["threats"][j]["preventive_barriers"])):
                mermaid_code += f'''
                    PB{i+1}{j+1}{k} --- PB{i+1}{j+1}{k+1}
                '''
            mermaid_code += f'''
                PB{i+1}{j+1}{k+1} --- TE{i+1}
            '''

        # Consequences and mitigative barriers
        for j in range(len(st.session_state.diagram_data["top_events"][i]["consequences"])-1, -1, -1):
            # Add the consequence and mitigative barrier to the diagram
            mermaid_code += f'''
                subgraph Consequences[Consequences]
                    C{i+1}{j+1}({wrap_text(st.session_state.diagram_data["top_events"][i]["consequences"][j]["consequence"], words_per_line)})
                    style C{i+1}{j+1} fill:#D53638,color:#FFFFFF
                end
            '''
            for k in range(len(st.session_state.diagram_data["top_events"][i]["consequences"][j]["mitigative_barriers"])):
                mermaid_code += f'''
                    subgraph MitigativeBarriers[Mitigative Barriers]
                        MB{i+1}{j+1}{k+1}({wrap_text(st.session_state.diagram_data["top_events"][i]["consequences"][j]["mitigative_barriers"][k], words_per_line)})
                    end
                '''
            mermaid_code += f'''
                TE{i+1} --- MB{i+1}{j+1}{1}
            '''
            for k in range(1, len(st.session_state.diagram_data["top_events"][i]["consequences"][j]["mitigative_barriers"])):
                mermaid_code += f'''
                    MB{i+1}{j+1}{k} --- MB{i+1}{j+1}{k+1}
                '''
            mermaid_code += f'''
                MB{i+1}{j+1}{k+1} --- C{i+1}{j+1}
            '''

    mermaid_code = mermaid_code.strip() # strip any leading or trailing whitespace to ensure the mermaid code is clean to improve change of successful rendering

    # Add redraw button to force rendering of the diagram. This is to address behavior where the diagram is not rendered on initial load or changes of data.
    if st.button(label="Refresh Diagram", icon=":material/refresh:"):
        st.session_state["redraw"] = not st.session_state.get("redraw", False)
    # Use the redraw state to change the key and force a redraw of the diagram
    unique_key = f"mermaid_{st.session_state.get('redraw', False)}"
    stmd.st_mermaid(mermaid_code, key=unique_key)
    
    if st.button("Generate Downloadable Bowtie (Matplotlib)"):
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis("off")
        ax.text(0.5, 0.5, "Bowtie Diagram Export\n(from Excel or Agent Input)", 
                fontsize=18, ha="center", va="center", wrap=True)
    
        pdf_buffer = io.BytesIO()
        fig.savefig(pdf_buffer, format="pdf")
        pdf_buffer.seek(0)
    
        st.download_button(
            label="📄 Download Bowtie PDF",
            data=pdf_buffer,
            file_name="bowtie_diagram.pdf",
            mime="application/pdf"
        )

with tab5:
    import streamlit as st
    import networkx as nx
    import matplotlib.pyplot as plt
    import io
    import streamlit_mermaid as stmd
    
    st.header("Bowtie Diagram - Choose Visualization")
    
    # Option selection
    viz_option = st.radio("Select Diagram Type", ["Mermaid.js", "Matplotlib"])
    
    # Example fallback data structure
    diagram_data = st.session_state.get("diagram_data", {
        "hazard": "Flammable gas",
        "top_events": [
            {
                "top_event": "Gas leak",
                "threats": [
                    {"threat": "Corroded pipe", "preventive_barriers": ["Regular inspection", "Pipe coating"]},
                    {"threat": "Valve failure", "preventive_barriers": ["Maintenance schedule"]}
                ],
                "consequences": [
                    {"consequence": "Fire", "mitigative_barriers": ["Fire suppression system", "Emergency shutdown"]},
                    {"consequence": "Injury", "mitigative_barriers": ["Evacuation plan"]}
                ]
            }
        ]
    })
    
    if viz_option == "Mermaid.js":
        def wrap_text(text, num_words):
            words = text.split()
            return "<br>".join([" ".join(words[i:i+num_words]) for i in range(0, len(words), num_words)])
    
        words_per_line = st.number_input("Words per Line", min_value=1, max_value=10, value=3)
    
        mermaid_code = "flowchart LR\n"
        mermaid_code += f"H([{wrap_text(diagram_data['hazard'], words_per_line)}])\n"
        te = diagram_data["top_events"][0]["top_event"]
        mermaid_code += f"H --> TE[{wrap_text(te, words_per_line)}]\n"
    
        for t in diagram_data["top_events"][0]["threats"]:
            threat = wrap_text(t["threat"], words_per_line)
            for b in t["preventive_barriers"]:
                pb = wrap_text(b, words_per_line)
                mermaid_code += f"{pb} --> {threat}\n"
            mermaid_code += f"{threat} --> TE\n"
    
        for c in diagram_data["top_events"][0]["consequences"]:
            cons = wrap_text(c["consequence"], words_per_line)
            mermaid_code += f"TE --> {cons}\n"
            for b in c["mitigative_barriers"]:
                mb = wrap_text(b, words_per_line)
                mermaid_code += f"{cons} --> {mb}\n"
    
        stmd.st_mermaid(mermaid_code)
    
    else:
        G = nx.DiGraph()
        labels = {}
    
        hazard = diagram_data["hazard"]
        top_event = diagram_data["top_events"][0]["top_event"]
        G.add_edge(hazard, top_event)
        labels[hazard] = hazard
        labels[top_event] = top_event
    
        for threat_obj in diagram_data["top_events"][0]["threats"]:
            threat = threat_obj["threat"]
            G.add_edge(threat, top_event)
            labels[threat] = threat
            for pb in threat_obj["preventive_barriers"]:
                G.add_edge(pb, threat)
                labels[pb] = pb
    
        for cons_obj in diagram_data["top_events"][0]["consequences"]:
            cons = cons_obj["consequence"]
            G.add_edge(top_event, cons)
            labels[cons] = cons
            for mb in cons_obj["mitigative_barriers"]:
                G.add_edge(cons, mb)
                labels[mb] = mb
    
        fig, ax = plt.subplots(figsize=(14, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, labels=labels,
                node_size=3000, node_color="lightblue", font_size=9,
                font_weight='bold', edge_color='gray', ax=ax)
        st.pyplot(fig)
    
        # PDF download
        pdf_buffer = io.BytesIO()
        fig.savefig(pdf_buffer, format="pdf", bbox_inches="tight")
        pdf_buffer.seek(0)
    
        st.download_button(
            label="📄 Download Matplotlib Diagram as PDF",
            data=pdf_buffer,
            file_name="bowtie_diagram.pdf",
            mime="application/pdf"
        )

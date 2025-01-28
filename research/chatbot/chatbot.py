import os
import logging
from langchain_openai import ChatOpenAI
import streamlit as st
import os


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"
rits_api_url = os.environ["RITS_API_URL"]

# App title
st.set_page_config(page_title="💬 Blueberry Chatbot")

# Maximum_assistant_count
max_assistant_count = 2

def connect_to_llm(_assistant:int =0):
    try:
        if "llm" not in st.session_state:
            st.session_state.llm = [None] * max_assistant_count

        if _assistant == 0:
            model_name = st.session_state.selected_model
        else:
            model_name = st.session_state.granite_model

        model = model_name.split(
            '/')[1].replace('.', '-').lower()
        url = f"{rits_api_url}/{model}/v1"

        # If there are no changes in the llm, return existing one
        if ("llm" in st.session_state and
                st.session_state.llm[_assistant] is not None and
                st.session_state.llm[_assistant].model_name == model_name):
            return st.session_state.llm[_assistant]

        llm = ChatOpenAI(
            model=f"{model_name}",
            temperature=st.session_state.temperature,
            max_retries=2,
            api_key='/',
            base_url=url,
            default_headers={'RITS_API_KEY': st.session_state.rits_api_key},
        )
    except Exception as e:
        st.session_state.llm = None
        st.warning("Can't connect to LLM, please fix the credentials!", icon='⚠️')
        logger.error(e)
        return

    logger.info(f"Connected to LLM: {model_name}")
    st.session_state.llm[_assistant] = llm
    return


# Replicate Credentials
with st.sidebar:
    st.title('💬 Blueberry Chatbot')
    st.write('This chatbot is part of the Blueberry project.',
             'It works against various LLM models and',
             'can be used to generate responses to user prompts.')
    try:
        if 'RITS_API_TOKEN' in os.environ:
            st.session_state.rits_api_key = os.environ['RITS_API_TOKEN']
            st.success('API provided using environment variable!', icon='✅')
        else:
            key = st.text_input(
                'Enter RITS API token:', type='password')
            if not (len(key) >= 32):
                st.warning('Please enter your credentials!', icon='⚠️')
            else:
                st.session_state.rits_api_key = key
                st.success(
                    'Proceed to entering your prompt message!', icon='👉')
    except Exception as e:
        st.warning("Can't connect to LLM, please fix the credentials!", icon='⚠️')

    st.subheader('Models and parameters')
    selected_model = st.sidebar.selectbox(
        'Choose a model', ['meta-llama/Llama-3.1-8B-Instruct',
                           'meta-llama/llama-3-1-70b-instruct',
                           'meta-llama/llama-3-3-70b-instruct',
                           'ibm-granite/granite-3.1-8b-instruct',
                           'deepseek-ai/DeepSeek-R1',
                           'deepseek-ai/DeepSeek-V3'], key='selected_model')
    st.session_state.granite_model = 'ibm-granite/granite-3.1-8b-instruct'
    temperature = st.sidebar.slider("temperature", key="temperature",
                                    min_value=0.01, max_value=1.0, value=0.9, step=0.01)

    st.markdown(
        '''
    👉 For additional details contact: eranra@il.ibm.com  

    📄 RITS API token instructions [RITS docs](https://github.ibm.com/rits/rits/?tab=readme-ov-file#important-information)      
    ''')

    if "rits_api_key" in st.session_state and st.session_state.rits_api_key is not None:
        for _assistant in range(max_assistant_count):
            connect_to_llm(_assistant)

def clear_chat_history():
    st.session_state.messages=[None] * max_assistant_count
    for _assistant in range(max_assistant_count):
        st.session_state.messages[_assistant] = [
            {"role": "assistant", "content": "How may I assist you today?"}]
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    clear_chat_history()

left_col, right_col = st.columns(2)

# Display or clear chat messages
st.sidebar.checkbox("dual assistant (compare with granite)", key="dual_assistant", on_change=clear_chat_history)

if st.session_state.dual_assistant:
    left_col.header("Chosen Assistant")
    right_col.header("Granite")

current_assistant_count = 1 if not st.session_state.dual_assistant else 2

if not st.session_state.dual_assistant:
    for message in st.session_state.messages[0]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
else:
    for assistant in range(max_assistant_count):
        with left_col if assistant == 0 else right_col:
            for message in st.session_state.messages[assistant]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])


def generate_response(prompt_input,_assistant:int = 0):
    string_dialogue = ("You are a helpful assistant."
                       "You do not respond as 'User' or pretend to be 'User'."
                       "You only respond once as 'Assistant'.")
    for dict_message in st.session_state.messages[_assistant]:
        if dict_message["role"] == "user":
            string_dialogue += "User: " + dict_message["content"] + "\n\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"

    try:
        # use openai API to call the LLM model
        llm_response = st.session_state.llm[_assistant].invoke(
            string_dialogue + prompt_input + "Assistant: ")
        output = llm_response.content
    except Exception as e1:
        logger.error(f"Error: {e1}")
        output = "I'm sorry can't get response from the model. Please try again."
    return output


# User-provided prompt
if prompt := st.chat_input(disabled=not ("rits_api_key" in st.session_state and st.session_state.rits_api_key is not None)):
    if not st.session_state.dual_assistant:
        st.session_state.messages[0].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
    else:
        for assistant in range(max_assistant_count):
            st.session_state.messages[assistant].append({"role": "user", "content": prompt})
            with left_col if assistant == 0 else right_col:
                with st.chat_message("user"):
                    st.write(prompt)

# Generate a new response if the last message is not from assistant
if not st.session_state.dual_assistant:
     if st.session_state.messages[0][-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_response(prompt)
                placeholder = st.empty()
                full_response = ''
                for item in response:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        message = {"role": "assistant", "content": full_response}
        st.session_state.messages[0].append(message)
else:
    for assistant in range(max_assistant_count):
        if st.session_state.messages[assistant][-1]["role"] != "assistant":
            with left_col if assistant == 0 else right_col:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = generate_response(prompt, assistant)
                        placeholder = st.empty()
                        full_response = ''
                        for item in response:
                            full_response += item
                            placeholder.markdown(full_response)
                        placeholder.markdown(full_response)
                message = {"role": "assistant", "content": full_response}
                st.session_state.messages[assistant].append(message)

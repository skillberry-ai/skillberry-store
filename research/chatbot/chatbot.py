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

def connect_to_llm():
    try:
        model = st.session_state.selected_model.split('/')[1].replace('.', '-').lower()
        url = f"{rits_api_url}/{model}/v1"

        # If there are no changes in the llm, return existing one
        if ("llm" in st.session_state and
                st.session_state.llm is not None and
                st.session_state.llm.model_name == st.session_state.selected_model):
            return st.session_state.llm

        llm = ChatOpenAI(
            model=f"{st.session_state.selected_model}",
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

    logger.info(f"Connected to LLM: {st.session_state.selected_model}")
    st.session_state.llm = llm
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
                           'meta-llama/llama-3-3-70b-instruct'], key='selected_model')
    temperature = st.sidebar.slider("temperature",key="temperature",
                                    min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    st.markdown(
        '👉 For additional details contact: eranra@il.ibm.com')
    if "rits_api_key" in st.session_state and st.session_state.rits_api_key is not None:
        connect_to_llm()

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [
        {"role": "assistant", "content": "How may I assist you today?"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


def clear_chat_history():
    st.session_state.messages = [
        {"role": "assistant", "content": "How may I assist you today?"}]


st.sidebar.button('Clear Chat History', on_click=clear_chat_history)


def generate_response(prompt_input):
    string_dialogue = ("You are a helpful assistant."
                       "You do not respond as 'User' or pretend to be 'User'."
                       "You only respond once as 'Assistant'.")
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            string_dialogue += "User: " + dict_message["content"] + "\n\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"

    try:
        # use openai API to call the LLM model
        llm_response = st.session_state.llm.invoke(string_dialogue + prompt_input + "Assistant: ")
        output = llm_response.content
    except Exception as e1:
        logger.error(f"Error: {e1}")
        output = "I'm sorry can't get response from the model. Please try again."
    return output


# User-provided prompt
if prompt := st.chat_input(disabled= not ("rits_api_key" in st.session_state and st.session_state.rits_api_key is not None)):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if the last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
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
    st.session_state.messages.append(message)

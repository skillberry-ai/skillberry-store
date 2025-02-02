import os
import logging
import time

from langchain_openai import ChatOpenAI
import streamlit as st
import os

from cookies import set_cookie, get_cookie


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"
os.environ["RITS_PROXY_API_URL"] = "http://blueberry.sl.cloud9.ibm.com:4000"

rits_api_url = os.environ["RITS_API_URL"]
rits_proxy_api_url = os.environ["RITS_PROXY_API_URL"]

# App title
st.set_page_config(page_title="💬 Blueberry Chatbot")

# Maximum_assistant_count
max_assistant_count = 2

if "use_dual_assistant" in st.session_state and st.session_state.use_dual_assistant:
    left_col, right_col = st.columns(2)
    left_col.header("Selected model")
    right_col.header("IBM Granite")
    current_assistant_count = 2
    panels = [left_col, right_col]
else:
    panels = st.columns(1)
    current_assistant_count = 1


def clear_chat_history():
    st.session_state.messages = [None] * max_assistant_count
    for _assistant in range(max_assistant_count):
        st.session_state.messages[_assistant] = [
            {"role": "assistant", "content": "How may I assist you today?"}]


def connect_to_llm(_assistant: int = 0):
    try:
        if "llm" not in st.session_state:
            st.session_state.llm = [None] * max_assistant_count

        if _assistant == 0:
            model_name = st.session_state.selected_model
        else:
            model_name = st.session_state.granite_model

        if "use_rits_blueberry_proxy" in st.session_state and st.session_state.use_rits_blueberry_proxy is True:
            model_name = f"rits/{model_name}".replace('.', '-').lower()

        # If there are no changes in the llm, return existing one
        if ("llm" in st.session_state and
                st.session_state.llm[_assistant] is not None and
                st.session_state.llm[_assistant].model_name == model_name):
            return st.session_state.llm[_assistant]

        if "use_rits_blueberry_proxy" in st.session_state and st.session_state.use_rits_blueberry_proxy is False:
            model = model_name.split(
                '/')[1].replace('.', '-').lower()
            url = f"{rits_api_url}/{model}/v1"

            llm = ChatOpenAI(
                model=f"{model_name}",
                temperature=st.session_state.temperature,
                max_retries=2,
                api_key='/',
                base_url=url,
                default_headers={'RITS_API_KEY': st.session_state.rits_api_key}
            )
        else:
            llm = ChatOpenAI(
                model=f"{model_name}",
                temperature=st.session_state.temperature,
                max_retries=2,
                api_key=st.session_state.rits_api_key,
                base_url=rits_proxy_api_url
            )
    except Exception as e:
        st.session_state.llm = None
        st.warning("Can't connect to LLM, please fix the credentials!", icon='⚠️')
        logger.error(e)
        return

    logger.info(f"Connected to LLM: {model_name}")
    st.session_state.llm[_assistant] = llm
    if st.session_state.rits_api_key is not None and st.session_state.rits_api_key != "":
        try:
            set_cookie("rits_api_key", st.session_state.rits_api_key)
        except Exception as e:
            logger.error(e)
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
            st.session_state.saved_rits_api_key = get_cookie("rits_api_key")
            if st.session_state.saved_rits_api_key is None:
                st.session_state.saved_rits_api_key = ""
            key = st.text_input(
                'Enter RITS API token:',
                type='password',
                value=st.session_state.saved_rits_api_key)
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
        'Choose a model', ['meta-llama/llama-3-3-70b-instruct',
                           'meta-llama/llama-3-1-70b-instruct',
                           'meta-llama/Llama-3.1-8B-Instruct',
                           'ibm/granite-20b-code-instruct',
                           'deepseek-ai/DeepSeek-R1',
                           'deepseek-ai/DeepSeek-V3'],
        key='selected_model',
        on_change=clear_chat_history)
    st.session_state.granite_model = 'ibm/granite-20b-code-instruct'
    temperature = st.sidebar.slider("temperature", key="temperature",
                                    min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    timeout = st.sidebar.slider("timeout", key="timeout",
                                min_value=1, max_value=120, value=30, step=1)

    st.markdown(
        '''
    👉 For additional details contact: eranra@il.ibm.com  
    🛠️ For feedback and issues :[Blueberry github](https://github.ibm.com/Blueberry/blueberry/issues)
     
    📄 RITS API token instructions [RITS docs](https://github.ibm.com/rits/rits/?tab=readme-ov-file#important-information)      
    ''')

    if "rits_api_key" in st.session_state and st.session_state.rits_api_key is not None:
        for _assistant in range(max_assistant_count):
            connect_to_llm(_assistant)

    # Clean chat History button
    st.button('Clear Chat History', on_click=clear_chat_history)
    if "messages" not in st.session_state.keys():
        clear_chat_history()

    # Dual assistant checkbox
    st.checkbox("Use rits blueberry proxy", key="use_rits_blueberry_proxy", value= False, on_change=clear_chat_history)
    st.checkbox("dual assistant (compare with granite)", key="use_dual_assistant", on_change=clear_chat_history)

def generate_response(prompt_input, _assistant: int = 0):
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
            string_dialogue + prompt_input + "Assistant: ",
            timeout=st.session_state.timeout)
        output = llm_response.content
    except Exception as e1:
        logger.error(f"Error: {e1}")
        output = f"I'm sorry can't get response from the model. {e1}\n Please try again later."
    return output

# User-provided prompt
if prompt := st.chat_input(
        disabled=not ("rits_api_key" in st.session_state and st.session_state.rits_api_key is not None)):
    for assistant in range(current_assistant_count):
        st.session_state.messages[assistant].append({"role": "user", "content": prompt})

def styled_content(content:str) -> str:
    return content.replace("<think>", '<span style="color: gray; font-size: 12px;">').replace("</think>", "</span>")

# display the trajectory
for assistant in range(current_assistant_count):
    with (panels[assistant]):
        for message in st.session_state.messages[assistant]:
            with st.chat_message(message["role"]):
                st.markdown(styled_content(message["content"]), unsafe_allow_html=True)

# Generate a new response if the last message is not from assistant
for assistant in range(current_assistant_count):
    if st.session_state.messages[assistant][-1]["role"] != "assistant":
        with panels[assistant]:
            with st.chat_message("assistant"):
                with st.spinner(f'Waiting for rits response ... max: {st.session_state.timeout} secs'):
                    response = generate_response(prompt, assistant)
                    placeholder = st.empty()
                    full_response = ''
                    for item in response:
                        full_response += item
                        placeholder.markdown(styled_content(full_response), unsafe_allow_html=True)
                    placeholder.markdown(styled_content(full_response), unsafe_allow_html=True)
            message = {"role": "assistant", "content": full_response}
            st.session_state.messages[assistant].append(message)

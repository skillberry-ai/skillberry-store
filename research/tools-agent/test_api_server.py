from api_server import get_last_user_prompt


def test_get_last_user_prompt():
    text = """
            User: hi\n
            Assistant: <think> I think that there are tools that can help me to reduce hallucinations and be 
            more accurate. I think that the tools are: a tool that A simple function that prints \'Hello World\' to 
            the console. 
            I am not allowed to code new tools.  
            I don\'t have any tools to use. using the LLM model as-is to response. I am done. 
            Returning a response to the user.</think>\n
            It\'s nice to meet you. Is there something I can help you with or would you like to chat?\n
            User: what is the currency symbol for the text "Deal size: AUD$25M" ?\n
            what is the currency symbol for the text "Deal size: AUD$25M" ?Assistant: 
            """

    result = get_last_user_prompt(text)
    assert result == {'content': 'what is the currency symbol for the text "Deal size: AUD$25M" ?', 'role': 'user'}

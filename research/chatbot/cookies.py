from streamlit_js_eval import streamlit_js_eval


# Set a cookie
def set_cookie(cookie_name: str, cookie_value: str):
    js_code = f"document.cookie = '{cookie_name}={cookie_value}; path=/; max-age=8640000';"
    streamlit_js_eval(js_expressions=js_code, key="set_cookie")


def get_cookie(cookie_name: str):
    cookies = streamlit_js_eval(js_expressions="document.cookie", key="get_cookie")
    cookie_dict = dict(cookie.strip().split("=", 1) for cookie in cookies.split("; ") if "=" in cookie)
    if cookie_name in cookie_dict:
        return cookie_dict[cookie_name]
    else:
        return None

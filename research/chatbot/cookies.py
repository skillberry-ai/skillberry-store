from streamlit_cookies_controller import CookieController

controller = CookieController()

# Set a cookie
def set_cookie(cookie_name:str, value:str):
    controller.set(cookie_name, value)

def get_cookie(cookie_name:str):
    value = controller.get(cookie_name)
    return value

def remove_cookie(cookie_name:str):
    value = controller.remove(cookie_name)


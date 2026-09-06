"""Page Objects - one class per page, all inheriting BasePage."""

from ui.pages.base_page import BasePage
from ui.pages.edit_profile_page import EditProfilePage
from ui.pages.home_page import HomePage
from ui.pages.login_page import LoginPage
from ui.pages.profile_page import ProfilePage
from ui.pages.signup_page import SignupPage

__all__ = ["BasePage", "EditProfilePage", "HomePage", "LoginPage", "ProfilePage", "SignupPage"]

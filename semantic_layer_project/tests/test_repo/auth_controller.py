
from user_service import UserService

class AuthController:
    '''Authentication controller'''

    def __init__(self):
        self.user_service = UserService()

    def handle_login(self, username, password):
        '''Handle login request'''
        return self.user_service.validate_user(username, password)

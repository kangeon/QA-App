import cgi
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)
	
def header(self):
    if users.get_current_user():
	   user_logged_on = 1
	   log_url = users.create_logout_url(self.request.uri)
	   log_url_linktext = 'Logout'
    else:
	   user_logged_on = 0
	   log_url = users.create_login_url(self.request.uri)
	   log_url_linktext = 'Login'
	
    header_values = {
        'user_logged_on' : user_logged_on,
        'log_url' : log_url,
        'log_url_linktext' : log_url_linktext,
    }
	
    header_template = JINJA_ENVIRONMENT.get_template('header.html')
    self.response.write(header_template.render(header_values))
		
class MainPage(webapp2.RequestHandler):
    def get(self):
      header(self)

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)
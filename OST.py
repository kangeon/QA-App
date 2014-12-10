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

DEFAULT_QUESTIONLIST_NAME = 'default_questionlist'

def questionlist_key(questionlist_name=DEFAULT_QUESTIONLIST_NAME):
    return ndb.Key('Questionlist', questionlist_name)

class Question(ndb.Model):
    """Models an individual question."""
    author = ndb.UserProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty()
    creationtime = ndb.DateTimeProperty(auto_now_add=True)
    modifiedtime = ndb.DateTimeProperty(auto_now=True)
    tags = ndb.StringProperty(repeated=True)
	
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
      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.creationtime)
      questions = questions_query.fetch(10)

      main_values = {
        'questions' : questions,
      }
      
      main_template = JINJA_ENVIRONMENT.get_template('main.html')
      self.response.write(main_template.render(main_values))

    def post(self):
      header(self)
      question = Question(parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))
      question.author = users.get_current_user()
      question.title = cgi.escape(self.request.get('qtitle'))
      question.content = cgi.escape(self.request.get('qcontent'))
      #question.tags = cgi.escape(self.request.get('qtags'))
      question.put()

      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.creationtime)
      questions = questions_query.fetch(10)

      main_values = {
        'questions' : questions,
      }
      
      main_template = JINJA_ENVIRONMENT.get_template('main.html')
      self.response.write(main_template.render(main_values))



class Create(webapp2.RequestHandler):
    def get(self):
      header(self)
      if users.get_current_user():
        user_logged_on = 1
      else:
        user_logged_on = 0
      create_values = {
        'user_logged_on' : user_logged_on,
      }
      create_template = JINJA_ENVIRONMENT.get_template('create.html')
      self.response.write(create_template.render(create_values))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', Create),
], debug=True)
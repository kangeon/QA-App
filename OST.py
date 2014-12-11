import cgi
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

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
      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.creationtime)
      questions, next_curs, more = questions_query.fetch_page(10, start_cursor=curs)

      if more and next_curs:
        more_pages = 1
        next_page_cursor = next_curs.urlsafe()
      else:
        more_pages = 0
        next_page_cursor = ''
    
      main_values = {
        'questions' : questions,
        'next_page_cursor' : next_page_cursor,
        'more_pages' : more_pages,
      }

      main_template = JINJA_ENVIRONMENT.get_template('main.html')
      self.response.write(main_template.render(main_values))

    def post(self):
      header(self)
      if cgi.escape(self.request.get('submitq')):
        question = Question(parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))
        question.author = users.get_current_user()
        question.title = cgi.escape(self.request.get('qtitle'))
        question.content = cgi.escape(self.request.get('qcontent'))
        tagslist = cgi.escape(self.request.get('qtags')).split(',')
        for tag in tagslist:
          tag.strip()
        question.tags = tagslist;
        question.put()

      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.creationtime)
      questions, next_curs, more = questions_query.fetch_page(10, start_cursor=curs)

      if more and next_curs:
        more_pages = 1
        next_page_cursor = next_curs.urlsafe()
      else:
        more_pages = 0
        next_page_cursor = ''
    
      main_values = {
        'questions' : questions,
        'next_page_cursor' : next_page_cursor,
        'more_pages' : more_pages,
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
      create_values =  {
        'user_logged_on' : user_logged_on,
      }
      create_template = JINJA_ENVIRONMENT.get_template('create.html')
      self.response.write(create_template.render(create_values))

class ViewPermalink(webapp2.RequestHandler):
    def get(self):
      header(self)
      qid = cgi.escape(self.request.get('qid'))
      quest = Question.get_by_id(int(qid),parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))
      permalink_values = {
        'quest' : quest,
      }
      
      permalink_template = JINJA_ENVIRONMENT.get_template('permalink.html')
      self.response.write(permalink_template.render(permalink_values))
      

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', Create),
    ('/permalink', ViewPermalink),
], debug=True)
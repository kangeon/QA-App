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

"""Default Title for Question and Answer Entity when title is not specified"""
DEFAULT_QUESTION_TITLE = '(No Title)'
DEFAULT_ANSWER_TITLE = '(No Title)'

"""Questionlist and Answerlist entities for ancestor queries to ensure strong consistency"""
DEFAULT_QUESTIONLIST_NAME = 'default_questionlist'
DEFAULT_ANSWERLIST_NAME = 'default_answerlist'
DEFAULT_VOTELIST_NAME = 'default_votelist'

def questionlist_key(questionlist_name=DEFAULT_QUESTIONLIST_NAME):
    return ndb.Key('Questionlist', questionlist_name)

def answerlist_key(answerlist_name=DEFAULT_ANSWERLIST_NAME):
    return ndb.Key('Answerlist', answerlist_name)

def votelist_key(votelist_name=DEFAULT_VOTELIST_NAME):
    return ndb.Key('Votelist', votelist_name)

class Question(ndb.Model):
    """Models an individual question."""
    author = ndb.UserProperty()
    authorID = ndb.StringProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty()
    creationtime = ndb.DateTimeProperty(auto_now_add=True)
    modifiedtime = ndb.DateTimeProperty(auto_now=True)
    tags = ndb.StringProperty(repeated=True)

class Answer(ndb.Model):
    """Models an individual answer."""
    author = ndb.UserProperty()
    authorID = ndb.StringProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty()
    creationtime = ndb.DateTimeProperty(auto_now_add=True)
    modifiedtime = ndb.DateTimeProperty(auto_now=True)
    questionID = ndb.IntegerProperty()
    voteCount = ndb.IntegerProperty()

class Vote(ndb.Model):
    """Models an individual vote."""
    voter = ndb.UserProperty()
    entityID = ndb.IntegerProperty()
    voteNumber = ndb.IntegerProperty()
	
def header(self):
    if users.get_current_user():
	   user_logged_on = 1
	   log_url = users.create_logout_url("/")
	   log_url_linktext = 'Logout'
    else:
	   user_logged_on = 0
	   log_url = users.create_login_url("/")
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
      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.modifiedtime)
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
        question.authorID = users.get_current_user().user_id()
        if cgi.escape(self.request.get('qtitle')) == '':
          question.title = DEFAULT_QUESTION_TITLE
        else:
          question.title = cgi.escape(self.request.get('qtitle'))
        question.content = cgi.escape(self.request.get('qcontent'))
        tagslist = cgi.escape(self.request.get('qtags')).split(',')
        for idx in range(0, len(tagslist)):
          tagslist[idx] = tagslist[idx].strip()
        question.tags = tagslist;
        question.put()

      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.modifiedtime)
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

class CreateAnswer(webapp2.RequestHandler):
    def get(self):
      header(self)
      if users.get_current_user():
        user_logged_on = 1
      else:
        user_logged_on = 0
      
      qid = cgi.escape(self.request.get('qid'))
      create_answer_values =  {
        'user_logged_on' : user_logged_on,
        'qid' : qid
      }

      create_answer_template = JINJA_ENVIRONMENT.get_template('createanswer.html')
      self.response.write(create_answer_template.render(create_answer_values))      

class View(webapp2.RequestHandler):
    def get(self):
      header(self)
      current_userID = ''
      if users.get_current_user():
        user_logged_on = 1
        current_userID = users.get_current_user().user_id()
      else:
        user_logged_on = 0

      qid = cgi.escape(self.request.get('qid'))
      quest = Question.get_by_id(int(qid),parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))

      qvotes_query = Vote.query(Vote.entityID == int(qid), ancestor=votelist_key(DEFAULT_VOTELIST_NAME))
      qvotes = qvotes_query.fetch()
      qvoteCount = 0;  

      for qvote in qvotes:
        qvoteCount = qvoteCount + qvote.voteNumber
      
      answers_query = Answer.query(Answer.questionID == int(qid), ancestor=answerlist_key(DEFAULT_ANSWERLIST_NAME)).order(-Answer.voteCount)
      answers = answers_query.fetch()

      view_values = {
        'user_logged_on' : user_logged_on,
        'quest' : quest,
        'answers' : answers,
        'qvoteCount' : qvoteCount,
        'current_userID' : current_userID,
      }
      
      view_template = JINJA_ENVIRONMENT.get_template('view.html')
      self.response.write(view_template.render(view_values))     

    def post(self):
      header(self)
      current_userID = ''
      if users.get_current_user():
        user_logged_on = 1
        current_userID = users.get_current_user().user_id()
      else:
        user_logged_on = 0

      qid = cgi.escape(self.request.get('qid'))
      aid = cgi.escape(self.request.get('aid'))

      #Edited a Question
      if cgi.escape(self.request.get('submitq')):
        question = Question.get_by_id(int(qid),parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))
        if cgi.escape(self.request.get('qtitle')) == '':
          question.title = DEFAULT_QUESTION_TITLE
        else:
          question.title = cgi.escape(self.request.get('qtitle'))
        question.content = cgi.escape(self.request.get('qcontent'))
        tagslist = cgi.escape(self.request.get('qtags')).split(',')
        for idx in range(0, len(tagslist)):
          tagslist[idx] = tagslist[idx].strip()
        question.tags = tagslist;
        question.put()

      #Voted on Question
      if cgi.escape(self.request.get('qupvote')):
        if Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(qid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() == None:
          qvote = Vote(parent=votelist_key(DEFAULT_VOTELIST_NAME))
          qvote.voter = users.get_current_user()
          qvote.entityID = int(qid)
          qvote.voteNumber = 1
          qvote.put()
        else:
          qvote = Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(qid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() 
          if qvote.voteNumber != 1:
            qvote.voteNumber = 1
            qvote.put()

      if cgi.escape(self.request.get('qdownvote')):
        if Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(qid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() == None:
          qvote = Vote(parent=votelist_key(DEFAULT_VOTELIST_NAME))
          qvote.voter = users.get_current_user()
          qvote.entityID = int(qid)
          qvote.voteNumber = -1
          qvote.put()
        else:
          qvote = Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(qid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get()
          if qvote.voteNumber != -1:
            qvote.voteNumber = -1
            qvote.put()

      #Voted on answer
      if cgi.escape(self.request.get('aupvote')):
        if Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(aid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() == None:
          avote = Vote(parent=votelist_key(DEFAULT_VOTELIST_NAME))
          avote.voter = users.get_current_user()
          avote.entityID = int(aid)
          avote.voteNumber = 1
          avote.put()
        else:
          avote = Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(aid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() 
          if avote.voteNumber != 1:
            avote.voteNumber = 1
            avote.put()

      if cgi.escape(self.request.get('adownvote')):
        if Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(aid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get() == None:
          avote = Vote(parent=votelist_key(DEFAULT_VOTELIST_NAME))
          avote.voter = users.get_current_user()
          avote.entityID = int(aid)
          avote.voteNumber = -1
          avote.put()
        else:
          avote = Vote.query(ndb.AND(Vote.voter == users.get_current_user(), Vote.entityID == int(aid)),ancestor=votelist_key(DEFAULT_VOTELIST_NAME)).get()
          if avote.voteNumber != -1:
            avote.voteNumber = -1
            avote.put()

      #Created a new answer
      if cgi.escape(self.request.get('submita')):
        if aid:
          answer = Answer.get_by_id(int(aid),parent=answerlist_key(DEFAULT_ANSWERLIST_NAME))
        else:
          answer = Answer(parent=answerlist_key(DEFAULT_ANSWERLIST_NAME))
          answer.author = users.get_current_user()
          answer.authorID = users.get_current_user().user_id()
          answer.voteCount = 0
        if cgi.escape(self.request.get('atitle')) == '':
          answer.title = DEFAULT_ANSWER_TITLE
        else:
          answer.title = cgi.escape(self.request.get('atitle'))
        answer.content = cgi.escape(self.request.get('acontent'))
        answer.questionID = int(qid)
        answer.put()

      quest = Question.get_by_id(int(qid),parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))

      qvotes_query = Vote.query(Vote.entityID == int(qid), ancestor=votelist_key(DEFAULT_VOTELIST_NAME))
      qvotes = qvotes_query.fetch()
      qvoteCount = 0;      

      for qvote in qvotes:
        qvoteCount = qvoteCount + qvote.voteNumber

      if cgi.escape(self.request.get('adownvote')) or cgi.escape(self.request.get('aupvote')):
        avotes_query = Vote.query(Vote.entityID == int(aid), ancestor=votelist_key(DEFAULT_VOTELIST_NAME))
        avotes = avotes_query.fetch()
        avoteCount = 0;     

        for avote in avotes:
          avoteCount = avoteCount + avote.voteNumber

        answer_to_update = Answer.get_by_id(int(aid),parent=answerlist_key(DEFAULT_ANSWERLIST_NAME))
        answer_to_update.voteCount = avoteCount
        answer_to_update.put()

      answers_query = Answer.query(Answer.questionID == int(qid), ancestor=answerlist_key(DEFAULT_ANSWERLIST_NAME)).order(-Answer.voteCount)
      answers = answers_query.fetch()
            
      view_values = {
        'user_logged_on' : user_logged_on,
        'quest' : quest,
        'answers' : answers,
        'qvoteCount' : qvoteCount,
        'current_userID' : current_userID,
      }
      
      view_template = JINJA_ENVIRONMENT.get_template('view.html')
      self.response.write(view_template.render(view_values))    
       

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

class ViewTaggedQuestions(webapp2.RequestHandler):
    def get(self):
      header(self)
      tag = cgi.escape(self.request.get('tag'))
      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(Question.tags == tag, ancestor=questionlist_key(DEFAULT_QUESTIONLIST_NAME)).order(-Question.modifiedtime)
      questions, next_tag_curs, more = questions_query.fetch_page(10, start_cursor=curs)

      if more and next_tag_curs:
        more_pages = 1
        next_page_cursor = next_tag_curs.urlsafe()
      else:
        more_pages = 0
        next_page_cursor = ''
    
      taglist_values = {
        'questions' : questions,
        'next_page_cursor' : next_page_cursor,
        'more_pages' : more_pages,
        'current_tag' : tag,
      }

      taglist_template = JINJA_ENVIRONMENT.get_template('taglist.html')
      self.response.write(taglist_template.render(taglist_values))

class EditQuestion(webapp2.RequestHandler):
    def get(self):
      header(self)
      qid = cgi.escape(self.request.get('qid'))
      question = Question.get_by_id(int(qid),parent=questionlist_key(DEFAULT_QUESTIONLIST_NAME))
      question_tags = ''
      if users.get_current_user():
        if users.get_current_user().user_id() != question.authorID:
          user_has_permission = 0
        else:
          user_has_permission = 1
          question_tags = ','.join(question.tags)
      else:
          user_has_permission = 0

      editq_values =  {
        'user_has_permission' : user_has_permission,
        'question' : question,
        'question_tags' : question_tags,
        'qid' : qid
      }

      editq_template = JINJA_ENVIRONMENT.get_template('editq.html')
      self.response.write(editq_template.render(editq_values))

class EditAnswer(webapp2.RequestHandler):
    def get(self):
      header(self)
      aid = cgi.escape(self.request.get('aid'))
      qid = cgi.escape(self.request.get('qid'))
      answer = Answer.get_by_id(int(aid),parent=answerlist_key(DEFAULT_ANSWERLIST_NAME))
      if users.get_current_user():
        if users.get_current_user().user_id() != answer.authorID:
          user_has_permission = 0
        else:
          user_has_permission = 1
      else:
          user_has_permission = 0

      edita_values =  {
        'user_has_permission' : user_has_permission,
        'answer' : answer,
        'aid' : aid,
        'qid' : qid,
      }

      edita_template = JINJA_ENVIRONMENT.get_template('edita.html')
      self.response.write(edita_template.render(edita_values))
      

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', Create),
    ('/answer', CreateAnswer),
    ('/view', View),
    ('/permalink', ViewPermalink),
    ('/taglist', ViewTaggedQuestions),
    ('/editq', EditQuestion),
    ('/edita', EditAnswer),
], debug=True)
import cgi
import os
import urllib
import re
import datetime

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

def convertLinks(content):
  content = re.sub(r'(https?://\S+)', r'<a href="\g<1>">\g<1></a>', content)
  content = re.sub(r'<a href="(https?://\S+\.(jpg|png|gif))">\S+</a>', r'<img src="\g<1>", width=500>', content)
  return content

def unconvertLinks(content):
  content = re.sub(r'<a href="(https?://\S+)">\1</a>', r'\g<1>', content)
  content = re.sub(r'<img src="(https?://\S+\.(jpg|png|gif))", width=500>', r'\g<1>', content)
  return content

"""Default Title for Question and Answer Entity when title is not specified"""
DEFAULT_QUESTION_TITLE = '(No Title)'
DEFAULT_ANSWER_TITLE = '(No Title)'

"""Setup ancestors for ancestor queries to ensure strong consistency"""
DEFAULT_VOTELIST_NAME = 'default_votelist'
DEFAULT_QALIST_NAME = 'default_qalist'

def votelist_key(votelist_name=DEFAULT_VOTELIST_NAME):
    return ndb.Key('Votelist', votelist_name)

def qalist_key(qalist_name=DEFAULT_QALIST_NAME):
    return ndb.Key('QAlist', qalist_name)

class Question(ndb.Model):
    """Models an individual question."""
    author = ndb.UserProperty()
    authorID = ndb.StringProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty()
    creationtime = ndb.DateTimeProperty(auto_now_add=True)
    modifiedtime = ndb.DateTimeProperty(auto_now=False)
    lastactivetime = ndb.DateTimeProperty(auto_now=False)
    tags = ndb.StringProperty(repeated=True)

class Answer(ndb.Model):
    """Models an individual answer."""
    author = ndb.UserProperty()
    authorID = ndb.StringProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty()
    creationtime = ndb.DateTimeProperty(auto_now_add=True)
    modifiedtime = ndb.DateTimeProperty(auto_now=False)
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
	
    upload_url = blobstore.create_upload_url('/upload')    
    
    header_values = {
        'user_logged_on' : user_logged_on,
        'log_url' : log_url,
        'log_url_linktext' : log_url_linktext,
        'upload_url' : upload_url,
    }
	
    header_template = JINJA_ENVIRONMENT.get_template('header.html')
    self.response.write(header_template.render(header_values))
		
class MainPage(webapp2.RequestHandler):
    def get(self):
      header(self)
      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Question.lastactivetime)
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
        question = Question(parent=qalist_key(DEFAULT_QALIST_NAME))
        question.author = users.get_current_user()
        question.authorID = users.get_current_user().user_id()
        if cgi.escape(self.request.get('qtitle')) == '':
          question.title = DEFAULT_QUESTION_TITLE
        else:
          question.title = cgi.escape(self.request.get('qtitle'))
        content = cgi.escape(self.request.get('qcontent'))
        question.content = convertLinks(content)
        tagslist = cgi.escape(self.request.get('qtags')).split(',')
        for idx in range(0, len(tagslist)):
          tagslist[idx] = tagslist[idx].strip()
        question.tags = tagslist;
        question.modifiedtime = datetime.datetime.now()
        question.lastactivetime = datetime.datetime.now()
        question.put()

      curs = Cursor(urlsafe=self.request.get('cursor'))
      questions_query = Question.query(ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Question.lastactivetime)
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
      quest = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))

      qvotes_query = Vote.query(Vote.entityID == int(qid), ancestor=votelist_key(DEFAULT_VOTELIST_NAME))
      qvotes = qvotes_query.fetch()
      qvoteCount = 0;  

      for qvote in qvotes:
        qvoteCount = qvoteCount + qvote.voteNumber
      
      answers_query = Answer.query(Answer.questionID == int(qid), ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Answer.voteCount)
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

      #If cancelq is not empty something happened so update question's lastactivetime
      if not cgi.escape(self.request.get('cancelq')):
        question = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))
        question.lastactivetime = datetime.datetime.now()
        question.put()

      #Edited a Question
      if cgi.escape(self.request.get('submitq')):
        question = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))
        if cgi.escape(self.request.get('qtitle')) == '':
          question.title = DEFAULT_QUESTION_TITLE
        else:
          question.title = cgi.escape(self.request.get('qtitle'))
        content = cgi.escape(self.request.get('qcontent'))
        question.content = convertLinks(content)
        tagslist = cgi.escape(self.request.get('qtags')).split(',')
        for idx in range(0, len(tagslist)):
          tagslist[idx] = tagslist[idx].strip()
        question.tags = tagslist;
        question.modifiedtime = datetime.datetime.now()
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

      #Created or modified an answer
      if cgi.escape(self.request.get('submita')):
        #Modified an answer
        if aid:
          answer = Answer.get_by_id(int(aid),parent=qalist_key(DEFAULT_QALIST_NAME))
        #Created a new answer
        else:
          answer = Answer(parent=qalist_key(DEFAULT_QALIST_NAME))
          answer.author = users.get_current_user()
          answer.authorID = users.get_current_user().user_id()
          answer.voteCount = 0
        if cgi.escape(self.request.get('atitle')) == '':
          answer.title = DEFAULT_ANSWER_TITLE
        else:
          answer.title = cgi.escape(self.request.get('atitle'))
        content = cgi.escape(self.request.get('acontent'))
        answer.content = convertLinks(content)
        answer.questionID = int(qid)
        answer.modifiedtime = datetime.datetime.now()
        answer.put()

      quest = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))

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

        answer_to_update = Answer.get_by_id(int(aid),parent=qalist_key(DEFAULT_QALIST_NAME))
        answer_to_update.voteCount = avoteCount
        answer_to_update.put()

      answers_query = Answer.query(Answer.questionID == int(qid), ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Answer.voteCount)
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
      quest = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))
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
      questions_query = Question.query(Question.tags == tag, ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Question.lastactivetime)
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
      question = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))
      question_tags = ''
      question_content = unconvertLinks(question.content)
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
        'qid' : qid,
        'question_content' : question_content,
      }

      editq_template = JINJA_ENVIRONMENT.get_template('editq.html')
      self.response.write(editq_template.render(editq_values))

class EditAnswer(webapp2.RequestHandler):
    def get(self):
      header(self)
      aid = cgi.escape(self.request.get('aid'))
      qid = cgi.escape(self.request.get('qid'))
      answer = Answer.get_by_id(int(aid),parent=qalist_key(DEFAULT_QALIST_NAME))
      answer_content = unconvertLinks(answer.content)
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
        'answer_content' : answer_content,
      }

      edita_template = JINJA_ENVIRONMENT.get_template('edita.html')
      self.response.write(edita_template.render(edita_values))

class ImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
      header(self)
      upload_images = self.get_uploads('image')
      blob_info = upload_images[0]
      image_url = images.get_serving_url(blob_info.key())

      upload_values = { 
        'image_url' : image_url,
      }
    
      upload_template = JINJA_ENVIRONMENT.get_template('upload.html')
      self.response.write(upload_template.render(upload_values))
      
class RSSHandler(webapp2.RequestHandler):
    def get(self):
      self.response.headers['Content-Type'] = 'text/xml'
      qid = cgi.escape(self.request.get('qid'))
      question = Question.get_by_id(int(qid),parent=qalist_key(DEFAULT_QALIST_NAME))
      answers_query = Answer.query(Answer.questionID == int(qid), ancestor=qalist_key(DEFAULT_QALIST_NAME)).order(-Answer.voteCount)
      answers = answers_query.fetch()
      site_url = self.request.host_url

      qvotes_query = Vote.query(Vote.entityID == int(qid), ancestor=votelist_key(DEFAULT_VOTELIST_NAME))
      qvotes = qvotes_query.fetch()
      qvoteCount = 0;      

      for qvote in qvotes:
        qvoteCount = qvoteCount + qvote.voteNumber
      
      rss_values = {
        'question' : question,
        'answers' : answers,
        'qvoteCount' : qvoteCount,
        'site_url' : site_url,
      }

      rss_template = JINJA_ENVIRONMENT.get_template('rss.xml')
      self.response.write(rss_template.render(rss_values))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', Create),
    ('/answer', CreateAnswer),
    ('/view', View),
    ('/permalink', ViewPermalink),
    ('/taglist', ViewTaggedQuestions),
    ('/editq', EditQuestion),
    ('/edita', EditAnswer),
    ('/upload', ImageUploadHandler),
    ('/rss', RSSHandler),
], debug=True)
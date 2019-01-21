#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import jinja2
import re
import logging
from google.appengine.ext import db
from google.appengine.api import users
import urllib2
import time
import json
import cgi
from google.appengine.api import memcache

CLIENT_ID = "478095448209-ff2evbl57jb3rdbc0vl0fkfi5pv88t0j.apps.googleusercontent.com"
template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.out.write(*a,**kw)
    def render_str(self,template,**params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))
    def userin(self):
        id = self.request.cookies.get("name")
        if id:
            return True
        else:
            self.redirect('/login')
    def userdata(self):
        id = str(self.request.cookies.get("name"))
        user = memcache.get(id)
        return user


class MainHandler(Handler):
    def get(self):
        self.render("home.html")        
        
class Blog(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    name = db.StringProperty()
    picture = db.LinkProperty()
    comments = db.IntegerProperty(default=0)
    views = db.IntegerProperty(default=0)
    TitlePicture = db.StringProperty()
    BlogSubTitle = db.StringProperty()
    BlogFooterPicture = db.StringProperty()
    BlogFooter = db.StringProperty()

class Comments(db.Model):
    blogid = db.IntegerProperty(required = True)
    name = db.StringProperty(required = True)
    email = db.EmailProperty(required = True)
    picture = db.LinkProperty()
    comment = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
	
class BlogHandler(Handler):
    def get(self):
        self.userin()
        bloggql = Blog.gql("order by created desc limit 100")
        blogs = list(bloggql)
        memcache.add(key = "blogs", value = blogs, time=3600)
        self.response.set_cookie('blogs',str(len(blogs)),path='/')
        id = str(self.request.cookies.get("name"))
        user = memcache.get(id)
        p = re.compile(r'<.*?>')
        self.render('BlogFeed.html',blogs=blogs[:10],user=user,p=p)
        #temp = ""
        #for entry in q.run(limit=10):
        #    temp = temp + ("<a href=/blog/"+str(entry.key().id())+"><div>"+entry.subject+"<br>"+entry.content+"<br><hr></div></a><br>")
        #self.write(temp)
    def post(self):
         i = int(self.request.cookies.get("blogs"))
         #i = i -10;
         if i >0 :
             txt = '''<section class="panel panel-success"><div class="panel-heading"><h2>%(subject)s<small><br><img src=%(picture)s
                    class="img-thumbnail" alt="Profile Picture">&nbsp;By %(name)s</small></h2></div><div class="panel-body">%(content)s...
                    <br><a href="/blog/%(id)s">Read More</a></div><div class="panel-footer"><span class="glyphicon glyphicon-eye-open"></span><span class="badge">%(views)s</span>&nbsp;
                    &nbsp;&nbsp;&nbsp;&nbsp;<span class="glyphicon glyphicon-comment"><span class="badge">%(comments)s</span></span></div></section>'''
             blogs = memcache.get("blogs")
             temp = '';
             i = (i-10) if (i-10)>0 else 0
             start = len(blogs) - i 
             end = (start +10) if (start +10)<=len(blogs) else (len(blogs)) 
             for j in range(start,end):
                 temp =  temp + txt % {"subject":cgi.escape(blogs[j].subject,quote=True),
                                       "picture":blogs[j].picture,
                                       "name":blogs[j].name,
                                       "content":cgi.escape(blogs[j].content,quote=True),
                                       "views":blogs[j].views,
                                       "comments":blogs[j].comments,
                                       "id":blogs[j].key().id()}      
             self.response.set_cookie('blogs',str(i),path='/')
             self.response.out.write(temp)
             
    

class NewPostHandler(Handler):
    def get(self):
        self.userin()
        user = self.userdata()
        self.render("CreateBlog.html",user=user)
        #id = self.request.cookies.get("name")
        #if id:
        #    self.render("newpost.html")
        #else:
        #    self.redirect('/login')	
    def post(self):
        user = self.userdata()
        if user:
            if 'picture' in user.keys():
                picture = user['picture']
            else :
                picture = "https://placehold.it/150"
            name = user['name']
            subject = self.request.get('subject')
            content = self.request.get('content')
            if self.request.get('TitlePicture'):
                TitlePicture = self.request.get('TitlePicture')
            else:
                TitlePicture = "/images/Clocks.jpg"
            BlogSubTitle = self.request.get('BlogSubTitle')
            if self.request.get('BlogFooterPicture'):
                BlogFooterPicture = self.request.get('BlogFooterPicture')
            else:
                BlogFooterPicture = "/images/Clocks.jpg"
            BlogFooter = self.request.get('BlogFooter')
            b = Blog(subject = subject, content = content, 
                picture = picture, name = name,
                TitlePicture = TitlePicture,
                BlogSubTitle = BlogSubTitle,
                BlogFooterPicture = BlogFooterPicture,
                BlogFooter = BlogFooter)
            b.put()
            self.redirect('/blog/'+ str(b.key().id()))


class PostHandler(Handler):
    def get(self,post_id):
        data = Blog.get_by_id(int(post_id))
        data.views = data.views + 1
        data.put()
        #id = str(self.request.cookies.get("name"))
        user = self.userdata()
        #if user:
        comments = Comments.gql('where blogid = '+ post_id)
        self.render("BlogTemplatenew.html",data = data, comments = comments, user=user)
        #else:
         #   self.render("BlogTemplate.html",user = None, data = data)
    def post(self,post_id):
        #name = self.request.get('name')
        #email = self.request.get('email')
        comment = self.request.get('comment')
        id = str(self.request.cookies.get("name"))
        user = memcache.get(id)
        blogid = int(post_id)
        if 'picture' in user.keys():
            picture = user['picture']
        else :
            picture = "https://placehold.it/150"
        c = Comments(blogid = blogid, name = user['name'], email = db.Email(user['email']), comment = comment, picture=picture)
        c.put()
        data = Blog.get_by_id(int(post_id))
        data.comments = data.comments + 1
        data.put()
        self.redirect('/blog/'+ post_id)

class LoginHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.render("Login.html",name = user.nickname())
        else:
            self.render("Login.html",name = "None")
    def post(self):
        token = self.request.get('idtoken')
        gurl = "https://www.googleapis.com/oauth2/v3/tokeninfo?id_token="
        check = urllib2.urlopen(gurl+token)
        if check.getcode() == 200:
            user = json.loads(check.read())
            try:
                if user["aud"] != CLIENT_ID:
                    raise "Invalid!!"
                if user['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise "Invalid!!"
                if user['exp'] < time.time():
                    raise "Invalid!!"
            except "Invalid!!":
                self.response.out.write("not valid")
            else:
                self.response.set_cookie('name',user['sub'],path='/')
                self.response.out.write(user['given_name'])
                memcache.add(key = user['sub'], value = user, time=3600)
        

class AboutPageHandler(Handler):
    def get(self):
        self.render("about.html")
		
class AboutPageHandler2(Handler):
	def get(self):
		self.render("about2.html")

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about',AboutPageHandler),
    ('/blog',BlogHandler),
    ('/blog/newpost',NewPostHandler),
    ('/login', LoginHandler),
	('/about2',AboutPageHandler2),	
    (r'/blog/(\d+)',PostHandler)
], debug=True)

# import os library to enable path function
import os
# import url library to enable sign query
import urllib
# import jinja library to enable html template
import jinja2
# import webapp2 to enable Google App Engine
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb

# Define directory of HTML templates
template_dir = os.path.join(os.path.dirname(__file__), "templates")

# Setup JinJa environment
# Use JinJa built-in function, autoescape = Ture instead of cgi.escape function
# Prevents unintended HTML code from rendering on the browser,
# stopping malicious users from abusing the site.
jinja_env = jinja2.Environment(
    loader = jinja2.FileSystemLoader(template_dir),
    autoescape = True)

# Set default forum as "Public"
DEFAULT_FORUM = "Public"

# Sent default error as ""
DEFAULT_ERROR = ""

# We set a parent key on the 'Post' to ensure each Post is
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.
# Constructs a Datastore key for a Forum entity.
# Use forum_name as the key.
def forum_key(forum_name = DEFAULT_FORUM):
    return ndb.Key("Forum", forum_name)

# These are the objects that will represent our Author and our Post. We're using
# Object Oriented Programming to create objects in order to put them in Google's
# Database. These objects inherit Googles ndb.Model class.
# Define Author Class to store information of author
# Following link shows other types of data we can create in an ndb class
# https://cloud.google.com/appengine/docs/python/ndb/properties
class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed = True)
    name = ndb.StringProperty(indexed = False)
    email = ndb.StringProperty(indexed = False)

# Define Post Class to store information of post
class Post(ndb.Model):
    """A main model for representing an individual post entry."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed = False)
    date = ndb.DateTimeProperty(auto_now_add = True)

# Define class Handler for write and render the page
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.headers["Content-Type"] = "text/html"
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):
    def get(self):
        # Get name of forum
        forum_name = self.request.get("forum_name", DEFAULT_FORUM)
        if forum_name == DEFAULT_FORUM.lower():
            forum_name = DEFAULT_FORUM

        # Detect error
        error = self.request.get("error", DEFAULT_ERROR)

        # Ancestor Queries, as shown here, are strongly consistent 
        # with the High Replication Datastore. Queries that span
        # entity groups are eventually consistent. If we omitted the
        # ancestor from this query there would be a slight chance that
        # COMMENTS that had just been written would not show up in a query.

        # [START query]
        posts_query = Post.query(ancestor = forum_key(forum_name)).order(-Post.date)
        # The function fetch() returns all posts that satisfy our query.
        # The function returns a list of post objects.
        posts =  posts_query.fetch()
        # [END query]

        # When the person is making the post, check to see
        # whether a person is logged into Google's Services
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = "Logout"
            user_name = user.nickname()
            user_id_no = user.user_id()
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Login"
            user_name = "Anonymous Poster"
            user_id_no = ""

        # Define sign query parameters
        sign_query_params = urllib.urlencode({"forum_name": forum_name})

        # Render comment.html
        # pass variables to html file
        self.render("comment.html",
            html_sign = "/sign?" + sign_query_params,
            html_forum_name = forum_name,
            html_user_name = user_name,
            html_url = url,
            html_url_linktext = url_linktext,
            html_posts = posts,
            html_user_id = user_id_no,
            html_error = error
            )

class PostForum(Handler):
    def post(self):
        # get name of forum
        forum_name = self.request.get("forum_name", DEFAULT_FORUM)
        if forum_name == DEFAULT_FORUM.lower():
            forum_name = DEFAULT_FORUM

        # Get content of post
        # We set a parent key on the 'Post' to ensure each Post is
        # in the same entity group. Queries across the single entity group
        # will be consistent.  However, the write rate should be limited to
        # ~1/second.
        post = Post(parent = forum_key(forum_name))

        # When the person is making the post, check to see
        # whether a person is logged into Google's Services
        user = users.get_current_user()
        if user:
            post.author = Author(
                identity = users.get_current_user().user_id(),
                name = users.get_current_user().nickname(),
                email = users.get_current_user().email()
                )
        else:
            post.author = Author(
                name = 'anonymous@anonymous.com',
                email = 'anonymous@anonymous.com'
                )

        # Get the content from our request parameters, in this case,
        # The message is in the parameter "forum_content"
        # Assign "forum_content" to content under Post Class
        if self.request.get("forum_content"):
            post.content = self.request.get("forum_content")
            # Write to the Google Datastore
            # Save the object to the database
            post.put()
            self.redirect("/?forum_name=" + forum_name)
        else:
            self.redirect("/?forum_name=" + forum_name + "&error=PLEASE TYPE IN YOUR COMMENTS!")

app = webapp2.WSGIApplication([
    ("/", MainPage),
    ("/sign", PostForum),
    ], debug = True)

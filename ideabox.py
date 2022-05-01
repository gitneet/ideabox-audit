#! /usr/bin/python3.8

import os
import time
import re
import requests
import lxml.html
import json
import threading
from queue import Queue

QLIMIT = 100
RETRY_MAX = 10
RETRY_INTERVAL = 1
BASEDIR = "%s/ideabox-jsons" % (os.getcwd(),)
DATADIR = "%s/data" % (BASEDIR,)
RAWSDIR = "%s/raws" % (BASEDIR,)

class Idea:
  def __init__(self, uuid, title, body, author, posted_at, comments, authors):
    self.uuid = uuid
    self.title = title
    self.body = body
    self.author = author
    self.posted_at = posted_at
    self.comments = list(map(lambda j: Comment.new(j, self, authors), comments))

  @classmethod
  def new(cls, idea_json, comments_json, ideas, authors):
    uuid = idea_json["id"]
    if(uuid in ideas):
      return(ideas[uuid])
    idea = Idea(uuid, idea_json["name"], idea_json["contents"], Author.new(idea_json["user"], authors), idea_json["date_modified"], comments_json, authors)
    ideas[idea.uuid] = idea
    return(idea)

class Comment:
  def __init__(self, uuid, message, author, posted_at, index, idea):
    self.uuid = uuid
    self.message = message
    self.author = author
    self.posted_at = posted_at
    self.index = index
    self.idea = idea

  @classmethod
  def new(cls, comment_json, idea, authors):
    j = comment_json
    return(Comment(j["id"], j["contents"], Author.new(j["user"], authors), j["date_entered"], int(j["serial_number"]), idea))

class Author:
  def __init__(self, uuid, name):
    self.uuid = uuid
    self.name = name

  @classmethod
  def new(cls, author_json, authors):
    if(not author_json):
      return(authors["deadbeef-dead-beef-dead-beefdeadbe"])
    uuid = author_json["id"]
    if(uuid in authors):
      return(authors[uuid])
    author = Author(uuid, author_json["portal_name"])
    authors[author.uuid] = author
    return(author)

class JsonNotFoundException(Exception):
  pass

def get_json_part(url):
  for i in range(RETRY_MAX):
    print("DL[%d]: collecting %s" % (i, url))
    res = requests.get(url)
    if(res.status_code != 200):
      time.sleep(RETRY_INTERVAL)
      continue
    return(json.loads(res.text))
  raise Exception("retry max")

def get_json_count(url):
  for i in range(RETRY_MAX):
    print("DL[%d]: counting %s" % (i, url))
    res = requests.get("%s&limit=%d&offset=%d" % (url, 1, 0))
    if(res.status_code != 200):
      continue
    j = json.loads(res.text)
    return(int(j["resultset"]["count"]))

def get_json(url):
  total = get_json_count(url)
  results = []
  for offset in range(0, total, QLIMIT):
    j = get_json_part("%s&limit=%d&offset=%d" % (url, QLIMIT, offset))
    if(isinstance(j["results"], list)):
      results.extend(j["results"])
    elif(isinstance(j["results"], dict)):
      results.append(j["results"])
    else:
      print(j)
      raise Exception("ERR: unknown json format.")
  return(results)

def save_rawjson(uuid, js):
  path = "%s/%s/%s" % (RAWSDIR, uuid[0], uuid[1])
  if(not os.path.exists(path)):
    os.makedirs(path)
  with open("%s/%s.json" % (path, uuid), "w") as f:
    f.write(json.dumps(js))

def load_rawjson(uuid):
  path = "%s/%s/%s" % (RAWSDIR, uuid[0], uuid[1])
  filepath = "%s/%s.json" % (path, uuid)
  if(not os.path.exists(filepath)):
    raise JsonNotFoundException()
  with open(filepath, "r") as f:
    return(json.loads(f.read()))

def get_json_wc(url, uuid, suffix=""):
  cachename = uuid + suffix
  try:
    return(load_rawjson(cachename))
  except JsonNotFoundException as err:
    json = get_json(url)
    save_rawjson(cachename, json)
    return(json)

def get_idea(uuid):
  return(get_json_wc("https://demo-api.ideabox.cloud/v1/ideas/%s?lang=ja" % (uuid,), uuid))

def get_comments(uuid):
  return(get_json_wc("https://demo-api.ideabox.cloud/v1/ideas/%s/comments?%s" % (uuid, "fields%5B%5D=id&fields%5B%5D=idea&fields%5B%5D=user&fields%5B%5D=serial_number&fields%5B%5D=contents&fields%5B%5D=comments&fields%5B%5D=vote_rate_avarage&fields%5B%5D=my_vote&fields%5B%5D=date_entered&order=desc&lang=ja"), uuid, "-comments"))

def main():
  ideas = {}
  authors = {}
  authors["deadbeef-dead-beef-dead-beefdeadbe"] = Author("deadbeef-dead-beef-dead-beefdeadbe", "DELETED")
  ideas_json = get_json("https://demo-api.ideabox.cloud/v1/ideas?sort=date_entered&order=DESC&lang=ja")
  idea_uuids = list(map(lambda idea: idea["id"], ideas_json))
  for idea_uuid in idea_uuids:
    idea_json = get_idea(idea_uuid)
    comments_json = get_comments(idea_uuid)
    idea = Idea.new(idea_json[0], comments_json, ideas, authors)

main()

